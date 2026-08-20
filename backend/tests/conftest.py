import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app import models  # noqa: F401
from app.database import Base, engine
from app.main import app
from app.redis_client import get_redis_client


@pytest.fixture(autouse=True)
def _reset_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def redis_client():
    return fakeredis.FakeStrictRedis(decode_responses=True)


@pytest.fixture()
def client(redis_client):
    app.dependency_overrides[get_redis_client] = lambda: redis_client
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    client.post("/auth/register", json={"email": "trader@example.com", "password": "correcthorse"})
    response = client.post(
        "/auth/login",
        data={"username": "trader@example.com", "password": "correcthorse"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
