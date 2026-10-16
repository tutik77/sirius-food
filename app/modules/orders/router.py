"""
Транспортный слой модуля заказов (круг Frameworks & Drivers).

Принимает HTTP-запрос, делает техническую валидацию, вызывает сервис
и переводит доменные исключения в HTTP-статусы.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.container import get_order_service
from app.domain.errors import DomainError
from app.http_errors import to_http
from app.modules.orders.service import OrderService
from app.schemas import OrderCreate

router = APIRouter()


@router.post("/create")
def create_order(payload: OrderCreate, service: OrderService = Depends(get_order_service)):
    # Техническая валидация уровня транспортного протокола.
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Количество должно быть больше нуля")

    try:
        order = service.create_order(
            user_id=payload.user_id,
            item_id=payload.item_id,
            quantity=payload.quantity,
        )
    except DomainError as e:
        raise to_http(e)

    return {"status": "success", "order_id": order.id}
