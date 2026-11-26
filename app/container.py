"""
Composition root: здесь собираются слои.

Роутеры получают готовые сервисы через Depends и не знают, какая
реализация репозитория под ними работает. Реализация выбирается
переменной окружения STORAGE_BACKEND (postgres | memory), при этом
service.py и router.py не меняются.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.redis import redis_client
from app.database import SessionLocal, get_db
from app.memory_storage import InMemoryStorage
from app.modules.auth.repository import AuthRepository, InMemoryAuthRepository, SqlAlchemyAuthRepository
from app.modules.auth.service import AuthService
from app.modules.delivery.repository import (
    DeliveryRepository,
    InMemoryDeliveryRepository,
    SqlAlchemyDeliveryRepository,
)
from app.modules.delivery.service import DeliveryService
from app.modules.menu.repository import InMemoryMenuRepository, MenuRepository, SqlAlchemyMenuRepository
from app.modules.menu.service import MenuService
from app.modules.orders.repository import InMemoryOrderRepository, OrderRepository, SqlAlchemyOrderRepository
from app.modules.orders.service import OrderService
from app.modules.users.repository import InMemoryUserRepository, SqlAlchemyUserRepository, UserRepository
from app.modules.users.service import UserService

memory_storage = InMemoryStorage()


def get_session():
    """Сессия БД для SQLAlchemy-репозиториев; в режиме memory сессия не открывается."""
    if settings.STORAGE_BACKEND == "memory":
        yield None
    else:
        yield from get_db()


def get_auth_repository(db: Session | None = Depends(get_session)) -> AuthRepository:
    if settings.STORAGE_BACKEND == "memory":
        return InMemoryAuthRepository(memory_storage)
    return SqlAlchemyAuthRepository(db)


def get_auth_service(repository: AuthRepository = Depends(get_auth_repository)) -> AuthService:
    return AuthService(repository)


def get_user_repository(db: Session | None = Depends(get_session)) -> UserRepository:
    if settings.STORAGE_BACKEND == "memory":
        return InMemoryUserRepository(memory_storage)
    return SqlAlchemyUserRepository(db)


def get_user_service(repository: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repository)


def get_menu_repository(db: Session | None = Depends(get_session)) -> MenuRepository:
    if settings.STORAGE_BACKEND == "memory":
        return InMemoryMenuRepository(memory_storage)
    return SqlAlchemyMenuRepository(db, cache=redis_client)


def warm_up_menu_cache() -> None:
    """Заполняет кеш меню при старте приложения (cache warm-up)."""
    if settings.STORAGE_BACKEND == "memory":
        return
    with SessionLocal() as db:
        SqlAlchemyMenuRepository(db, cache=redis_client).warm_up()


def get_menu_service(repository: MenuRepository = Depends(get_menu_repository)) -> MenuService:
    return MenuService(repository)


def get_order_repository(db: Session | None = Depends(get_session)) -> OrderRepository:
    if settings.STORAGE_BACKEND == "memory":
        return InMemoryOrderRepository(memory_storage)
    return SqlAlchemyOrderRepository(db)


def get_order_service(repository: OrderRepository = Depends(get_order_repository)) -> OrderService:
    return OrderService(repository)


def get_delivery_repository(db: Session | None = Depends(get_session)) -> DeliveryRepository:
    if settings.STORAGE_BACKEND == "memory":
        return InMemoryDeliveryRepository(memory_storage)
    return SqlAlchemyDeliveryRepository(db)


def get_delivery_service(
    repository: DeliveryRepository = Depends(get_delivery_repository),
) -> DeliveryService:
    return DeliveryService(repository)
