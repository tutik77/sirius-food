"""
Бизнес-сущности предметной области «Сириус.Еда» (круг Entities).

Обычные dataclass-ы без зависимостей от фреймворков и ORM.
Именно с ними работает слой бизнес-логики; репозитории переводят
их в строки таблиц и обратно.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Role(StrEnum):
    STUDENT = "student"
    COOK = "cook"
    COURIER = "courier"
    ADMIN = "admin"


class OrderStatus(StrEnum):
    PROCESSING = "processing"
    PAID = "paid"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


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
    password_hash: str | None = None
    role: str = Role.STUDENT

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN


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
    total_cost: float | None = None

    def belongs_to(self, user: User) -> bool:
        return self.user_id == user.id


@dataclass
class Delivery:
    id: int | None
    order_id: int
    courier_id: int | None
    status: str = DeliveryStatus.PENDING


@dataclass
class RefreshToken:
    """Запись о выданном refresh-токене (хранится хеш, не сам токен)."""

    id: int | None
    user_id: int
    token_hash: str
    expires_at: datetime
    is_revoked: bool = False
