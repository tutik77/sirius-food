"""
Pydantic-схемы для валидации входных и выходных данных.
"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.entities import Role


class UserCreate(BaseModel):
    email: EmailStr
    # bcrypt учитывает только первые 72 байта пароля.
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
    # user_id больше не принимается от клиента: сервер берёт его из JWT.
    item_id: int
    quantity: int


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    quantity: int
    status: str
    total_cost: float | None


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
