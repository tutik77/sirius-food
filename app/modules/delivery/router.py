"""
Транспортный слой модуля доставки (круг Frameworks & Drivers).

Роль проверяется здесь (require_role), права на конкретную доставку —
в DeliveryService.
"""
from fastapi import APIRouter, Depends

from app.container import get_delivery_service
from app.core.dependencies import get_current_user, require_role
from app.domain.entities import Role, User
from app.domain.errors import DomainError
from app.http_errors import to_http
from app.modules.delivery.service import DeliveryService
from app.schemas import DeliveryAssign, DeliveryResponse

router = APIRouter()


@router.post("/assign")
def assign_courier(
    payload: DeliveryAssign,
    current_user: User = Depends(require_role(Role.ADMIN)),
    service: DeliveryService = Depends(get_delivery_service),
):
    try:
        delivery = service.assign_courier(order_id=payload.order_id, courier_id=payload.courier_id)
    except DomainError as e:
        raise to_http(e)

    return {"status": "success", "delivery_id": delivery.id}


@router.get("/my", response_model=list[DeliveryResponse])
def my_deliveries(
    current_user: User = Depends(require_role(Role.COURIER)),
    service: DeliveryService = Depends(get_delivery_service),
):
    return service.list_courier_deliveries(current_user)


@router.get("/{delivery_id}", response_model=DeliveryResponse)
def get_delivery(
    delivery_id: int,
    current_user: User = Depends(get_current_user),
    service: DeliveryService = Depends(get_delivery_service),
):
    try:
        return service.get_delivery(delivery_id, current_user)
    except DomainError as e:
        raise to_http(e)


@router.patch("/{delivery_id}/complete")
def complete_delivery(
    delivery_id: int,
    current_user: User = Depends(require_role(Role.COURIER, Role.ADMIN)),
    service: DeliveryService = Depends(get_delivery_service),
):
    try:
        service.complete_delivery(delivery_id, current_user)
    except DomainError as e:
        raise to_http(e)

    return {"status": "success"}
