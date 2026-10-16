"""
Composition root: здесь собираются слои.

Роутеры получают готовые сервисы через Depends и не знают, какая
реализация репозитория под ними работает.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.menu.repository import MenuRepository, SqlAlchemyMenuRepository
from app.modules.menu.service import MenuService
from app.modules.orders.repository import OrderRepository, SqlAlchemyOrderRepository
from app.modules.orders.service import OrderService
from app.modules.users.repository import SqlAlchemyUserRepository, UserRepository
from app.modules.users.service import UserService


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return SqlAlchemyUserRepository(db)


def get_user_service(repository: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repository)


def get_menu_repository(db: Session = Depends(get_db)) -> MenuRepository:
    return SqlAlchemyMenuRepository(db)


def get_menu_service(repository: MenuRepository = Depends(get_menu_repository)) -> MenuService:
    return MenuService(repository)


def get_order_repository(db: Session = Depends(get_db)) -> OrderRepository:
    return SqlAlchemyOrderRepository(db)


def get_order_service(repository: OrderRepository = Depends(get_order_repository)) -> OrderService:
    return OrderService(repository)
