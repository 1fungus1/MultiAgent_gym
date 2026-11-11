from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import Database
from app.core.responses import success
from app.schemas import ApiResponse, HealthVO

router = APIRouter(prefix="/health", tags=["系统"])


@router.get("", response_model=ApiResponse[HealthVO])
def health(db: Session = Depends(Database)) -> dict:
    db.execute(text("SELECT 1"))
    return success(HealthVO(status="ok", database="connected"))

