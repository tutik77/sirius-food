"""
Инфраструктурный слой модуля заказов (круг Interface Adapters).

OrderRepository — абстрактный интерфейс, от которого зависит сервис.
Реализации: SqlAlchemyOrderRepository (PostgreSQL) и InMemoryOrderRepository.
"""
from abc import ABC, abstractmethod
from dataclasses import replace
from datetime import datetime

from sqlalchemy.orm import Session

from app import models
from app.domain.entities import MenuItem, Order, User
from app.domain.events import Event
from app.mappers import to_menu_item, to_order, to_user
from app.memory_storage import InMemoryStorage, copy
from app.messaging.outbox import to_outbox_row


class OrderRepository(ABC):
    """Операции хранения, нужные сценариям заказов. Бизнес-правил здесь нет."""

    @abstractmethod
    def get_user_by_id(self, user_id: int) -> User | None:
        """Пользователь по идентификатору или None."""

    @abstractmethod
    def get_menu_item_by_id(self, item_id: int) -> MenuItem | None:
        """Блюдо по идентификатору или None."""

    @abstractmethod
    def get_order(self, order_id: int) -> Order | None:
        """Заказ по идентификатору или None."""

    @abstractmethod
    def list_by_user(self, user_id: int) -> list[Order]:
        """Заказы пользователя."""

    @abstractmethod
    def list_by_status(self, status: str) -> list[Order]:
        """Заказы в указанном статусе."""

    @abstractmethod
    def save_order(self, order: Order, payer: User) -> Order:
        """
        Сохраняет новый заказ и новый баланс покупателя одной транзакцией.
        Возвращает заказ с присвоенным идентификатором.
        """

    @abstractmethod
    def save_cancellation(self, order: Order, payer: User) -> None:
        """Сохраняет отменённый заказ и возврат денег покупателю одной транзакцией."""

    @abstractmethod
    def count_created_between(self, start: datetime, end: datetime) -> int: ...

    @abstractmethod
    def save_payment(self, order: Order, event: Event) -> None: ...

    @abstractmethod
    def save_compensation(self, order: Order, payer: User, event: Event) -> None: ...


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

    def get_order(self, order_id: int) -> Order | None:
        row = self.db.get(models.Order, order_id)
        return to_order(row) if row else None

    def list_by_user(self, user_id: int) -> list[Order]:
        rows = self.db.query(models.Order).filter(models.Order.user_id == user_id).order_by(models.Order.id)
        return [to_order(row) for row in rows]

    def list_by_status(self, status: str) -> list[Order]:
        rows = self.db.query(models.Order).filter(models.Order.status == status).order_by(models.Order.id)
        return [to_order(row) for row in rows]

    def save_order(self, order: Order, payer: User) -> Order:
        user_row = self.db.get(models.User, payer.id)
        user_row.balance = payer.balance

        order_row = models.Order(
            user_id=order.user_id,
            item_id=order.item_id,
            quantity=order.quantity,
            status=order.status,
            total_cost=order.total_cost,
        )
        self.db.add(order_row)
        self.db.commit()
        self.db.refresh(order_row)
        return to_order(order_row)

    def save_cancellation(self, order: Order, payer: User) -> None:
        self.db.get(models.Order, order.id).status = order.status
        self.db.get(models.User, payer.id).balance = payer.balance
        self.db.commit()

    def count_created_between(self, start: datetime, end: datetime) -> int:
        return (
            self.db.query(models.Order)
            .filter(models.Order.created_at >= start, models.Order.created_at < end)
            .count()
        )

    def save_payment(self, order: Order, event: Event) -> None:
        self.db.get(models.Order, order.id).status = order.status
        self.db.add(to_outbox_row(event))
        self.db.commit()

    def save_compensation(self, order: Order, payer: User, event: Event) -> None:
        self.db.get(models.Order, order.id).status = order.status
        self.db.get(models.User, payer.id).balance = payer.balance
        self.db.add(to_outbox_row(event))
        self.db.commit()


class InMemoryOrderRepository(OrderRepository):
    """Реализация репозитория заказов в памяти процесса."""

    def __init__(self, storage: InMemoryStorage):
        self.storage = storage

    def get_user_by_id(self, user_id: int) -> User | None:
        return copy(self.storage.users.get(user_id))

    def get_menu_item_by_id(self, item_id: int) -> MenuItem | None:
        return copy(self.storage.menu_items.get(item_id))

    def get_order(self, order_id: int) -> Order | None:
        return copy(self.storage.orders.get(order_id))

    def list_by_user(self, user_id: int) -> list[Order]:
        return [copy(o) for o in self.storage.orders.values() if o.user_id == user_id]

    def list_by_status(self, status: str) -> list[Order]:
        return [copy(o) for o in self.storage.orders.values() if o.status == status]

    def save_order(self, order: Order, payer: User) -> Order:
        saved = replace(order, id=self.storage.next_id("orders"), created_at=datetime.utcnow())
        self.storage.users[payer.id] = copy(payer)
        self.storage.orders[saved.id] = saved
        return copy(saved)

    def save_cancellation(self, order: Order, payer: User) -> None:
        self.storage.orders[order.id] = copy(order)
        self.storage.users[payer.id] = copy(payer)

    def count_created_between(self, start: datetime, end: datetime) -> int:
        return sum(1 for o in self.storage.orders.values() if start <= o.created_at < end)

    def save_payment(self, order: Order, event: Event) -> None:
        self.storage.orders[order.id] = copy(order)
        self.storage.outbox.append(event)

    def save_compensation(self, order: Order, payer: User, event: Event) -> None:
        self.storage.orders[order.id] = copy(order)
        self.storage.users[payer.id] = copy(payer)
        self.storage.outbox.append(event)
