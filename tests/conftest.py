"""
Общие фикстуры.

Фикстура repos параметризована: каждый тест, который её использует,
выполняется дважды — на in-memory репозиториях и на SQLAlchemy-репозиториях
поверх SQLite в памяти. Сервер PostgreSQL для тестов не нужен.
"""
import os

# Переменные окружения важнее .env, поэтому локальный .env на тесты не влияет.
os.environ.update(
    STORAGE_BACKEND="memory",
    SECRET_KEY="test-secret-key-for-pytest-only-0123456789",
    DATABASE_URL="postgresql://sirius:sirius@localhost:5432/sirius_food",
    DEBUG="False",
    ALLOWED_ORIGINS='["https://sirius-food.ru"]',
    BCRYPT_ROUNDS="4",
)

from typing import NamedTuple

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.memory_storage import InMemoryStorage
from app.modules.delivery.repository import (
    DeliveryRepository,
    InMemoryDeliveryRepository,
    SqlAlchemyDeliveryRepository,
)
from app.modules.menu.repository import InMemoryMenuRepository, MenuRepository, SqlAlchemyMenuRepository
from app.modules.orders.repository import InMemoryOrderRepository, OrderRepository, SqlAlchemyOrderRepository
from app.modules.users.repository import InMemoryUserRepository, SqlAlchemyUserRepository, UserRepository


class Repos(NamedTuple):
    users: UserRepository
    menu: MenuRepository
    orders: OrderRepository
    delivery: DeliveryRepository


@pytest.fixture
def sqlite_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture(params=["memory", "sqlalchemy"])
def repos(request) -> Repos:
    if request.param == "memory":
        storage = InMemoryStorage()
        return Repos(
            InMemoryUserRepository(storage),
            InMemoryMenuRepository(storage),
            InMemoryOrderRepository(storage),
            InMemoryDeliveryRepository(storage),
        )
    session = request.getfixturevalue("sqlite_session")
    return Repos(
        SqlAlchemyUserRepository(session),
        SqlAlchemyMenuRepository(session),
        SqlAlchemyOrderRepository(session),
        SqlAlchemyDeliveryRepository(session),
    )
