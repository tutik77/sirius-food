from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

CENT = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


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
    created_at: datetime | None = None
    promo_code_id: int | None = None
    discount: float = 0.0
    points_spent: float = 0.0

    @property
    def paid_with_money(self) -> float:
        return (self.total_cost or 0.0) - self.points_spent

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
    id: int | None
    user_id: int
    token_hash: str
    expires_at: datetime
    is_revoked: bool = False


class DiscountType(StrEnum):
    PERCENT = "percent"
    FIXED = "fixed"


@dataclass
class PromoCode:
    id: int | None
    code: str
    discount_type: str
    discount_value: Decimal
    valid_from: datetime
    valid_until: datetime
    max_uses: int
    current_uses: int = 0
    min_order_amount: Decimal = Decimal("0")
    is_active: bool = True

    def is_valid_at(self, moment: datetime) -> bool:
        return self.is_active and self.valid_from <= moment <= self.valid_until

    def has_uses_left(self) -> bool:
        return self.current_uses < self.max_uses

    def discount_for(self, amount: Decimal) -> Decimal:
        if self.discount_type == DiscountType.PERCENT:
            discount = amount * self.discount_value / 100
        else:
            discount = self.discount_value
        return money(min(discount, amount))


@dataclass
class PromoUsage:
    id: int | None
    promo_code_id: int
    user_id: int
    order_id: int | None
    discount: Decimal


class LoyaltyTier(StrEnum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


TIER_RATES = {LoyaltyTier.BRONZE: Decimal("0.03"), LoyaltyTier.SILVER: Decimal("0.05"), LoyaltyTier.GOLD: Decimal("0.07")}
TIER_THRESHOLDS = ((LoyaltyTier.GOLD, Decimal("5000")), (LoyaltyTier.SILVER, Decimal("1000")))


class LoyaltyTransactionType(StrEnum):
    EARN = "earn"
    SPEND = "spend"
    REFUND = "refund"
    REVOKE = "revoke"


@dataclass
class LoyaltyAccount:
    id: int | None
    user_id: int
    balance: Decimal = Decimal("0")
    total_earned: Decimal = Decimal("0")
    tier: str = LoyaltyTier.BRONZE

    def points_for(self, amount: Decimal) -> Decimal:
        return money(amount * TIER_RATES[LoyaltyTier(self.tier)])

    def update_tier(self) -> None:
        self.tier = next((tier for tier, threshold in TIER_THRESHOLDS if self.total_earned >= threshold), LoyaltyTier.BRONZE)


@dataclass
class LoyaltyTransaction:
    id: int | None
    account_id: int
    amount: Decimal
    type: str
    order_id: int
    idempotency_key: str
    created_at: datetime | None = None


@dataclass
class AssistantMessage:
    id: int | None
    user_id: int
    question: str
    answer: str
    latency_ms: int
    is_fallback: bool = False
    helpful: bool | None = None
    created_at: datetime | None = None
