"""
Бизнес-сущности предметной области «Сириус.Еда» (круг Entities).

Обычные dataclass-ы без зависимостей от фреймворков и ORM.
Именно с ними работает слой бизнес-логики; репозитории переводят
их в строки таблиц и обратно.
"""
from dataclasses import dataclass
from enum import StrEnum


class OrderStatus(StrEnum):
    PROCESSING = "processing"
    PAID = "paid"
    DELIVERED = "delivered"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class User:
    id: int | None
    email: str
    phone: str | None = None
    balance: float = 0.0
    is_blocked: bool = False


@dataclass
class MenuItem:
    id: int | None
    name: str
    price: float
    is_available: bool = True


@dataclass
class Order:
    id: int | None
    user_id: int
    item_id: int
    quantity: int
    status: str = OrderStatus.PROCESSING


@dataclass
class Delivery:
    id: int | None
    order_id: int
    courier_id: int | None
    status: str = DeliveryStatus.PENDING
