from app import models
from app.domain.entities import (
    AssistantMessage,
    Delivery,
    LoyaltyAccount,
    LoyaltyTransaction,
    MenuItem,
    Order,
    PromoCode,
    PromoUsage,
    RefreshToken,
    User,
)


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
        created_at=row.created_at,
        promo_code_id=row.promo_code_id,
        discount=row.discount or 0.0,
        points_spent=row.points_spent or 0.0,
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


def to_promo_code(row: models.PromoCode) -> PromoCode:
    return PromoCode(
        id=row.id,
        code=row.code,
        discount_type=row.discount_type,
        discount_value=row.discount_value,
        valid_from=row.valid_from,
        valid_until=row.valid_until,
        max_uses=row.max_uses,
        current_uses=row.current_uses,
        min_order_amount=row.min_order_amount,
        is_active=row.is_active,
    )


def to_promo_usage(row: models.PromoCodeUsage) -> PromoUsage:
    return PromoUsage(
        id=row.id,
        promo_code_id=row.promo_code_id,
        user_id=row.user_id,
        order_id=row.order_id,
        discount=row.discount,
    )


def to_loyalty_account(row: models.LoyaltyAccount) -> LoyaltyAccount:
    return LoyaltyAccount(
        id=row.id,
        user_id=row.user_id,
        balance=row.balance,
        total_earned=row.total_earned,
        tier=row.tier,
    )


def to_loyalty_transaction(row: models.LoyaltyTransaction) -> LoyaltyTransaction:
    return LoyaltyTransaction(
        id=row.id,
        account_id=row.account_id,
        amount=row.amount,
        type=row.type,
        order_id=row.order_id,
        idempotency_key=row.idempotency_key,
        created_at=row.created_at,
    )


def to_assistant_message(row: models.AssistantMessage) -> AssistantMessage:
    return AssistantMessage(
        id=row.id,
        user_id=row.user_id,
        question=row.question,
        answer=row.answer,
        latency_ms=row.latency_ms,
        is_fallback=row.is_fallback,
        helpful=row.helpful,
        created_at=row.created_at,
    )
