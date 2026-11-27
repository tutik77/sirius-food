import os

os.environ.update(
    STORAGE_BACKEND="memory",
    SECRET_KEY="test-secret-key-for-pytest-only-0123456789",
    DATABASE_URL="postgresql://sirius:sirius@localhost:5432/sirius_food",
    DEBUG="False",
    ALLOWED_ORIGINS='["https://sirius-food.ru"]',
    BCRYPT_ROUNDS="4",
    TESTCONTAINERS_RYUK_DISABLED="true",
    SENTRY_DSN="",
    OTEL_EXPORTER_OTLP_ENDPOINT="",
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
from app.modules.loyalty.repository import InMemoryLoyaltyRepository, LoyaltyRepository, SqlAlchemyLoyaltyRepository
from app.modules.menu.repository import InMemoryMenuRepository, MenuRepository, SqlAlchemyMenuRepository
from app.modules.orders.repository import InMemoryOrderRepository, OrderRepository, SqlAlchemyOrderRepository
from app.modules.promo.repository import InMemoryPromoRepository, PromoRepository, SqlAlchemyPromoRepository
from app.modules.users.repository import InMemoryUserRepository, SqlAlchemyUserRepository, UserRepository
from delivery_service.repository import (
    DeliveryRepository,
    InMemoryDeliveryRepository,
    SqlAlchemyDeliveryRepository,
)


class Repos(NamedTuple):
    users: UserRepository
    menu: MenuRepository
    orders: OrderRepository
    delivery: DeliveryRepository
    auth: AuthRepository
    promo: PromoRepository
    loyalty: LoyaltyRepository


@pytest.fixture
def sqlite_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
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
            InMemoryPromoRepository(storage),
            InMemoryLoyaltyRepository(storage),
        )
    session = request.getfixturevalue("sqlite_session")
    return Repos(
        SqlAlchemyUserRepository(session),
        SqlAlchemyMenuRepository(session),
        SqlAlchemyOrderRepository(session),
        SqlAlchemyDeliveryRepository(session),
        SqlAlchemyAuthRepository(session),
        SqlAlchemyPromoRepository(session),
        SqlAlchemyLoyaltyRepository(session),
    )


_emails = count(1)


@pytest.fixture
def make_user(repos):
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


@pytest.fixture(scope="session", autouse=True)
def delivery_grpc_server():
    from contextlib import nullcontext

    from app import container
    from app.core.config import settings
    from delivery_service.repository import InMemoryDeliveryRepository
    from delivery_service.server import create_server
    from delivery_service.service import DeliveryService

    def memory_scope():
        return nullcontext(DeliveryService(InMemoryDeliveryRepository(container.memory_storage)))

    server, port = create_server("127.0.0.1:0", memory_scope)
    server.start()
    settings.DELIVERY_GRPC_ADDR = f"127.0.0.1:{port}"
    yield settings.DELIVERY_GRPC_ADDR
    server.stop(0)
