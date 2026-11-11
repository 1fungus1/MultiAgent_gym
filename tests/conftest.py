import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-key-with-at-least-thirty-two-characters"
os.environ["AUTO_CREATE_TABLES"] = "false"
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["RAG_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.seed import seed_demo_data
from app.db.session import SessionLocal, engine
from app.main import app


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo_data(db)
        db.commit()
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, username: str, password: str = "123456") -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    return payload["data"]["token"]
