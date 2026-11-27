import os
import subprocess
import sys
from pathlib import Path

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from app import container, models
from app.container import get_session
from app.core import rate_limit
from app.core.config import settings
from app.core.jwt import create_access_token
from app.core.security import hash_password
from app.main import app

ROOT = Path(__file__).resolve().parents[2]
TABLES = "outbox_events, processed_events, kitchen_orders, deliveries, orders, refresh_tokens, menu_items, users"


@pytest.fixture(scope="session")
def postgres_url():
    with PostgresContainer("postgres:15", driver="psycopg2") as postgres:
        url = postgres.get_connection_url()
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env={**os.environ, "DATABASE_URL": url},
            check=True,
        )
        yield url


@pytest.fixture
def db(postgres_url):
    engine = create_engine(postgres_url)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    engine.dispose()


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "postgres")
    monkeypatch.setattr(container, "redis_client", fakeredis.FakeRedis(decode_responses=True))
    monkeypatch.setattr(rate_limit, "redis_client", fakeredis.FakeRedis())
    app.dependency_overrides[get_session] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db):
    def factory(role: str = "student", balance: float = 0.0) -> models.User:
        role_row = db.query(models.Role).filter_by(name=role).one()
        user = models.User(
            email=f"{role}{db.query(models.User).count()}@sirius.ru",
            balance=balance,
            password_hash=hash_password("StrongPass123"),
            role=role_row,
        )
        db.add(user)
        db.commit()
        return user

    return factory


@pytest.fixture
def make_item(db):
    def factory(name: str = "Сырники", price: float = 150.0) -> models.MenuItem:
        item = models.MenuItem(name=name, price=price, is_available=True)
        db.add(item)
        db.commit()
        return item

    return factory


def auth(user: models.User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}
