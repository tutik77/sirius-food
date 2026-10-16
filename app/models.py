"""
Определение ORM-моделей предметной области «Сириус.Еда».
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class Role(Base):
    """Роль пользователя: student, cook, courier, admin."""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    balance = Column(Float, default=0.0)
    is_blocked = Column(Boolean, default=False)
    # bcrypt-хеш пароля; сам пароль нигде не хранится.
    password_hash = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    role = relationship("Role", lazy="joined")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    is_available = Column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    item_id = Column(Integer, ForeignKey("menu_items.id"))
    quantity = Column(Integer, nullable=False)
    status = Column(String, default="processing")
    # Сколько списано с баланса при оформлении — столько и вернётся при отмене.
    total_cost = Column(Float, nullable=True)

    user = relationship("User")
    item = relationship("MenuItem")


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    courier_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="pending")

    order = relationship("Order")
    courier = relationship("User")


class RefreshToken(Base):
    """Выданный refresh-токен. Храним хеш токена, а не сам токен — на случай утечки БД."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
