"""
Транспортный слой модуля заказов (круг Frameworks & Drivers).

Принимает HTTP-запрос, проверяет токен и роль, делает техническую валидацию,
вызывает сервис и переводит доменные исключения в HTTP-статусы.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.container import get_order_service
from app.core.dependencies import get_current_user, require_role
from app.domain.entities import Role, User
from app.domain.errors import DomainError
from app.http_errors import to_http
from app.modules.orders.service import OrderService
from app.schemas import OrderCreate, OrderResponse

router = APIRouter()


@router.post("/create")
def create_order(
    payload: OrderCreate,
    current_user: User = Depends(require_role(Role.STUDENT)),
    service: OrderService = Depends(get_order_service),
):
    # Техническая валидация уровня транспортного протокола.
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Количество должно быть больше нуля")

    try:
        order = service.create_order(
            user_id=current_user.id,
            item_id=payload.item_id,
            quantity=payload.quantity,
        )
    except DomainError as e:
        raise to_http(e)

    return {"status": "success", "order_id": order.id}


@router.get("/my", response_model=list[OrderResponse])
def my_orders(
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    return service.list_user_orders(current_user)


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    try:
        service.cancel_order(order_id, current_user)
    except DomainError as e:
        raise to_http(e)

    return {"status": "success"}


@router.get("/kitchen/orders", response_model=list[OrderResponse])
def kitchen_orders(
    current_user: User = Depends(require_role(Role.COOK, Role.ADMIN)),
    service: OrderService = Depends(get_order_service),
):
    return service.get_kitchen_orders()
