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

from itertools import count
from typing import NamedTuple

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base
from app.domain.entities import Role, User
from app.memory_storage import InMemoryStorage
from app.modules.auth.repository import AuthRepository, InMemoryAuthRepository, SqlAlchemyAuthRepository
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
    auth: AuthRepository


@pytest.fixture
def sqlite_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    # В PostgreSQL роли заводит миграция, здесь — вручную.
    session.add_all(models.Role(name=role.value) for role in Role)
    session.commit()
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
            InMemoryAuthRepository(storage),
        )
    session = request.getfixturevalue("sqlite_session")
    return Repos(
        SqlAlchemyUserRepository(session),
        SqlAlchemyMenuRepository(session),
        SqlAlchemyOrderRepository(session),
        SqlAlchemyDeliveryRepository(session),
        SqlAlchemyAuthRepository(session),
    )


_emails = count(1)


@pytest.fixture
def make_user(repos):
    """Создаёт пользователя напрямую через репозиторий, минуя регистрацию."""

    def factory(role: str = Role.STUDENT, balance: float = 0.0, is_blocked: bool = False) -> User:
        return repos.users.add(
            User(
                id=None,
                email=f"user{next(_emails)}@sirius.ru",
                balance=balance,
                is_blocked=is_blocked,
                password_hash="!",
                role=role,
            )
        )

    return factory


@pytest.fixture(autouse=True)
def scheduled_tasks(monkeypatch):
    from app.tasks import orders

    calls = []
    for task in (orders.generate_order_pdf, orders.send_order_email, orders.send_order_sms):
        monkeypatch.setattr(task, "delay", lambda *args, name=task.name: calls.append((name, args)))
    return calls
