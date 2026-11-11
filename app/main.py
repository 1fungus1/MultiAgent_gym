import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, agent, auth, health, member, notifications
from app.core.config import BASE_DIR, settings
from app.core.responses import register_exception_handlers
from app.db.seed import seed_demo_data
from app.db.session import SessionLocal, create_tables
from app.rag import initialize_knowledge_index
from app.tasks import maintenance_worker, stop_maintenance_worker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.auto_create_tables:
        create_tables()
    if settings.seed_demo_data:
        with SessionLocal() as db:
            try:
                seed_demo_data(db)
                db.commit()
            except Exception:
                db.rollback()
                raise
    await asyncio.to_thread(initialize_knowledge_index)
    maintenance_stop = asyncio.Event()
    maintenance_task = asyncio.create_task(
        maintenance_worker(maintenance_stop),
        name="gym-maintenance-worker",
    )
    if settings.jwt_secret.startswith("change-me"):
        logger.warning("JWT_SECRET 仍是开发默认值，正式部署前必须更换")
    try:
        yield
    finally:
        await stop_maintenance_worker(maintenance_task, maintenance_stop)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="MultiAgent_gym 多智能体健身房管理系统 API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(member.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(health.router, prefix="/api")


frontend_dist = BASE_DIR / "frontend" / "dist"
if frontend_dist.exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API 不存在")
        requested_file = frontend_dist / full_path
        if full_path and requested_file.is_file():
            return FileResponse(requested_file)
        return FileResponse(frontend_dist / "index.html")
