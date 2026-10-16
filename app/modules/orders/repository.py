"""
Инфраструктурный слой модуля заказов (круг Interface Adapters).

OrderRepository — абстрактный интерфейс, от которого зависит сервис.
SqlAlchemyOrderRepository — его реализация поверх PostgreSQL.
"""
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app import models
from app.domain.entities import MenuItem, Order, User
from app.mappers import to_menu_item, to_order, to_user


class OrderRepository(ABC):
    """Операции хранения, нужные сценариям заказов. Бизнес-правил здесь нет."""

    @abstractmethod
    def get_user_by_id(self, user_id: int) -> User | None:
        """Пользователь по идентификатору или None."""

    @abstractmethod
    def get_menu_item_by_id(self, item_id: int) -> MenuItem | None:
        """Блюдо по идентификатору или None."""

    @abstractmethod
    def save_order(self, order: Order, payer: User) -> Order:
        """
        Сохраняет новый заказ и новый баланс покупателя одной транзакцией.
        Возвращает заказ с присвоенным идентификатором.
        """


class SqlAlchemyOrderRepository(OrderRepository):
    """Реализация репозитория заказов на SQLAlchemy ORM."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: int) -> User | None:
        row = self.db.get(models.User, user_id)
        return to_user(row) if row else None

    def get_menu_item_by_id(self, item_id: int) -> MenuItem | None:
        row = self.db.get(models.MenuItem, item_id)
        return to_menu_item(row) if row else None

    def save_order(self, order: Order, payer: User) -> Order:
        user_row = self.db.get(models.User, payer.id)
        user_row.balance = payer.balance

        order_row = models.Order(
            user_id=order.user_id,
            item_id=order.item_id,
            quantity=order.quantity,
            status=order.status,
        )
        self.db.add(order_row)
        self.db.commit()
        self.db.refresh(order_row)
        return to_order(order_row)
