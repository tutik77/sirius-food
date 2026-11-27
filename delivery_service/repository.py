from abc import ABC, abstractmethod
from dataclasses import replace

from sqlalchemy.orm import Session

from app import models
from app.domain.entities import Delivery, DeliveryStatus, Order, Role, User
from app.mappers import to_delivery, to_order, to_user
from app.memory_storage import InMemoryStorage, copy


class DeliveryRepository(ABC):
    @abstractmethod
    def get_order(self, order_id: int) -> Order | None:
        ...

    @abstractmethod
    def get_user(self, user_id: int) -> User | None:
        ...

    @abstractmethod
    def get_delivery(self, delivery_id: int) -> Delivery | None:
        ...

    @abstractmethod
    def find_active_by_courier(self, courier_id: int) -> Delivery | None:
        ...

    @abstractmethod
    def find_free_courier(self) -> User | None: ...

    @abstractmethod
    def list_by_courier(self, courier_id: int) -> list[Delivery]:
        ...

    @abstractmethod
    def add(self, delivery: Delivery) -> Delivery:
        ...

    @abstractmethod
    def save_completion(self, delivery: Delivery, order: Order | None) -> None:
        ...


class SqlAlchemyDeliveryRepository(DeliveryRepository):
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

    def find_free_courier(self) -> User | None:
        busy = self.db.query(models.Delivery.courier_id).filter(
            models.Delivery.status == DeliveryStatus.IN_PROGRESS,
            models.Delivery.courier_id.is_not(None),
        )
        row = (
            self.db.query(models.User)
            .join(models.Role)
            .filter(
                models.Role.name == Role.COURIER,
                models.User.is_blocked.is_(False),
                models.User.id.not_in(busy),
            )
            .order_by(models.User.id)
            .first()
        )
        return to_user(row) if row else None

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

    def find_free_courier(self) -> User | None:
        busy = {d.courier_id for d in self.storage.deliveries.values() if d.status == DeliveryStatus.IN_PROGRESS}
        found = next(
            (
                u
                for u in sorted(self.storage.users.values(), key=lambda u: u.id)
                if u.role == Role.COURIER and not u.is_blocked and u.id not in busy
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
