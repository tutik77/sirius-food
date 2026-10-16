"""
Инфраструктурный слой модуля доставки (круг Interface Adapters).

DeliveryRepository — абстрактный интерфейс, от которого зависит сервис.
Реализации: SqlAlchemyDeliveryRepository (PostgreSQL) и InMemoryDeliveryRepository.
"""
from abc import ABC, abstractmethod
from dataclasses import replace

from sqlalchemy.orm import Session

from app import models
from app.domain.entities import Delivery, DeliveryStatus, Order, User
from app.mappers import to_delivery, to_order, to_user
from app.memory_storage import InMemoryStorage, copy


class DeliveryRepository(ABC):
    """Хранилище доставок и данные, нужные для назначения курьера."""

    @abstractmethod
    def get_order(self, order_id: int) -> Order | None:
        """Заказ по идентификатору или None."""

    @abstractmethod
    def get_user(self, user_id: int) -> User | None:
        """Пользователь (курьер) по идентификатору или None."""

    @abstractmethod
    def get_delivery(self, delivery_id: int) -> Delivery | None:
        """Доставка по идентификатору или None."""

    @abstractmethod
    def find_active_by_courier(self, courier_id: int) -> Delivery | None:
        """Доставка курьера в статусе in_progress или None."""

    @abstractmethod
    def list_by_courier(self, courier_id: int) -> list[Delivery]:
        """Все доставки курьера."""

    @abstractmethod
    def add(self, delivery: Delivery) -> Delivery:
        """Сохраняет новую доставку, возвращает её с идентификатором."""

    @abstractmethod
    def save_completion(self, delivery: Delivery, order: Order | None) -> None:
        """Сохраняет новые статусы доставки и заказа одной транзакцией."""


class SqlAlchemyDeliveryRepository(DeliveryRepository):
    """Реализация репозитория доставки на SQLAlchemy ORM."""

    def __init__(self, db: Session):
        self.db = db

    def get_order(self, order_id: int) -> Order | None:
        row = self.db.get(models.Order, order_id)
        return to_order(row) if row else None

    def get_user(self, user_id: int) -> User | None:
        row = self.db.get(models.User, user_id)
        return to_user(row) if row else None

    def get_delivery(self, delivery_id: int) -> Delivery | None:
        row = self.db.get(models.Delivery, delivery_id)
        return to_delivery(row) if row else None

    def find_active_by_courier(self, courier_id: int) -> Delivery | None:
        row = (
            self.db.query(models.Delivery)
            .filter(
                models.Delivery.courier_id == courier_id,
                models.Delivery.status == DeliveryStatus.IN_PROGRESS,
            )
            .first()
        )
        return to_delivery(row) if row else None

    def list_by_courier(self, courier_id: int) -> list[Delivery]:
        rows = (
            self.db.query(models.Delivery)
            .filter(models.Delivery.courier_id == courier_id)
            .order_by(models.Delivery.id)
        )
        return [to_delivery(row) for row in rows]

    def add(self, delivery: Delivery) -> Delivery:
        row = models.Delivery(
            order_id=delivery.order_id,
            courier_id=delivery.courier_id,
            status=delivery.status,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return to_delivery(row)

    def save_completion(self, delivery: Delivery, order: Order | None) -> None:
        self.db.get(models.Delivery, delivery.id).status = delivery.status
        if order is not None:
            self.db.get(models.Order, order.id).status = order.status
        self.db.commit()


class InMemoryDeliveryRepository(DeliveryRepository):
    """Реализация репозитория доставки в памяти процесса."""

    def __init__(self, storage: InMemoryStorage):
        self.storage = storage

    def get_order(self, order_id: int) -> Order | None:
        return copy(self.storage.orders.get(order_id))

    def get_user(self, user_id: int) -> User | None:
        return copy(self.storage.users.get(user_id))

    def get_delivery(self, delivery_id: int) -> Delivery | None:
        return copy(self.storage.deliveries.get(delivery_id))

    def find_active_by_courier(self, courier_id: int) -> Delivery | None:
        found = next(
            (
                d
                for d in self.storage.deliveries.values()
                if d.courier_id == courier_id and d.status == DeliveryStatus.IN_PROGRESS
            ),
            None,
        )
        return copy(found)

    def list_by_courier(self, courier_id: int) -> list[Delivery]:
        return [copy(d) for d in self.storage.deliveries.values() if d.courier_id == courier_id]

    def add(self, delivery: Delivery) -> Delivery:
        saved = replace(delivery, id=self.storage.next_id("deliveries"))
        self.storage.deliveries[saved.id] = saved
        return copy(saved)

    def save_completion(self, delivery: Delivery, order: Order | None) -> None:
        self.storage.deliveries[delivery.id] = copy(delivery)
        if order is not None:
            self.storage.orders[order.id] = copy(order)
