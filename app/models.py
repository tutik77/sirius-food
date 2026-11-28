from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Role(Base):
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
    total_cost = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    promo_code_id = Column(Integer, ForeignKey("promo_codes.id"), nullable=True)
    discount = Column(Float, nullable=False, server_default="0")
    points_spent = Column(Float, nullable=False, server_default="0")

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
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(String(36), primary_key=True)
    routing_key = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    headers = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    published_at = Column(DateTime, nullable=True, index=True)


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    consumer = Column(String(50), primary_key=True)
    event_id = Column(String(36), primary_key=True)
    processed_at = Column(DateTime, nullable=False, server_default=func.now())


class KitchenOrder(Base):
    __tablename__ = "kitchen_orders"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    discount_type = Column(String(10), nullable=False)
    discount_value = Column(Numeric(12, 2), nullable=False)
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False, index=True)
    max_uses = Column(Integer, nullable=False)
    current_uses = Column(Integer, nullable=False, default=0)
    min_order_amount = Column(Numeric(12, 2), nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)


class PromoCodeUsage(Base):
    __tablename__ = "promo_code_usages"
    __table_args__ = (UniqueConstraint("promo_code_id", "user_id", name="uq_promo_code_usages_promo_user"),)

    id = Column(Integer, primary_key=True)
    promo_code_id = Column(Integer, ForeignKey("promo_codes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    discount = Column(Numeric(12, 2), nullable=False)


class LoyaltyAccount(Base):
    __tablename__ = "loyalty_accounts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    balance = Column(Numeric(12, 2), nullable=False, default=0)
    total_earned = Column(Numeric(12, 2), nullable=False, default=0)
    tier = Column(String(10), nullable=False, default="bronze")


class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("loyalty_accounts.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    type = Column(String(10), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    idempotency_key = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    is_fallback = Column(Boolean, nullable=False, default=False)
    helpful = Column(Boolean, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
