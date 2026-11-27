from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.entities import DiscountType, LoyaltyTier, Role


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    phone: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    balance: float
    role: str


class RoleUpdate(BaseModel):
    role: Role


class MenuItemCreate(BaseModel):
    name: str
    price: float


class MenuItemUpdate(BaseModel):
    name: str | None = None
    price: float | None = None
    is_available: bool | None = None


class OrderCreate(BaseModel):
    item_id: int
    quantity: int
    promo_code: str | None = None


class OrderPay(BaseModel):
    points: Decimal = Field(default=Decimal("0"), ge=0)


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    quantity: int
    status: str
    total_cost: float | None
    discount: float = 0.0
    points_spent: float = 0.0


class MenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: float
    is_available: bool


class DeliveryAssign(BaseModel):
    order_id: int
    courier_id: int


class DeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    courier_id: int | None
    status: str


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class RefreshSchema(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class PromoCodeCreate(BaseModel):
    code: str = Field(min_length=3, max_length=50)
    discount_type: DiscountType
    discount_value: Decimal = Field(gt=0)
    valid_from: datetime
    valid_until: datetime
    max_uses: int = Field(ge=1)
    min_order_amount: Decimal = Field(default=Decimal("0"), ge=0)


class PromoCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    discount_type: str
    discount_value: Decimal
    valid_from: datetime
    valid_until: datetime
    max_uses: int
    current_uses: int
    min_order_amount: Decimal
    is_active: bool


class LoyaltyTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    amount: Decimal
    type: str
    order_id: int
    idempotency_key: str


class LoyaltySummary(BaseModel):
    balance: Decimal
    total_earned: Decimal
    tier: LoyaltyTier
    earn_rate: Decimal
    transactions: list[LoyaltyTransactionResponse]


class AssistantQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


class AssistantFeedback(BaseModel):
    helpful: bool


class AssistantAnswer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    answer: str
    latency_ms: int
    is_fallback: bool
    helpful: bool | None
