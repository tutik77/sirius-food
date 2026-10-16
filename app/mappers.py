"""
Преобразование ORM-моделей в доменные сущности.

Используется только SQLAlchemy-репозиториями: наружу из инфраструктурного
слоя ORM-объекты не выходят.
"""
from app import models
from app.domain.entities import Delivery, MenuItem, Order, RefreshToken, User


def to_user(row: models.User) -> User:
    return User(
        id=row.id,
        email=row.email,
        phone=row.phone,
        balance=row.balance,
        is_blocked=row.is_blocked,
        password_hash=row.password_hash,
        role=row.role.name,
    )


def to_menu_item(row: models.MenuItem) -> MenuItem:
    return MenuItem(
        id=row.id,
        name=row.name,
        price=row.price,
        is_available=row.is_available,
    )


def to_order(row: models.Order) -> Order:
    return Order(
        id=row.id,
        user_id=row.user_id,
        item_id=row.item_id,
        quantity=row.quantity,
        status=row.status,
        total_cost=row.total_cost,
    )


def to_delivery(row: models.Delivery) -> Delivery:
    return Delivery(
        id=row.id,
        order_id=row.order_id,
        courier_id=row.courier_id,
        status=row.status,
    )


def to_refresh_token(row: models.RefreshToken) -> RefreshToken:
    return RefreshToken(
        id=row.id,
        user_id=row.user_id,
        token_hash=row.token_hash,
        expires_at=row.expires_at,
        is_revoked=row.is_revoked,
    )
