from fastapi import APIRouter, Depends

from app.container import get_delivery_gateway
from app.core.dependencies import get_current_user, require_role
from app.domain.entities import Role, User
from app.domain.errors import DomainError
from app.http_errors import to_http
from app.modules.delivery.gateway import DeliveryGateway
from app.schemas import DeliveryAssign, DeliveryResponse

router = APIRouter()


@router.post("/assign")
def assign_courier(
    payload: DeliveryAssign,
    current_user: User = Depends(require_role(Role.ADMIN)),
    gateway: DeliveryGateway = Depends(get_delivery_gateway),
):
    try:
        delivery = gateway.assign_courier(order_id=payload.order_id, courier_id=payload.courier_id)
    except DomainError as e:
        raise to_http(e) from e

    return {"status": "success", "delivery_id": delivery.id}


@router.get("/my", response_model=list[DeliveryResponse])
def my_deliveries(
    current_user: User = Depends(require_role(Role.COURIER)),
    gateway: DeliveryGateway = Depends(get_delivery_gateway),
):
    try:
        return gateway.list_courier_deliveries(current_user)
    except DomainError as e:
        raise to_http(e) from e


@router.get("/{delivery_id}", response_model=DeliveryResponse)
def get_delivery(
    delivery_id: int,
    current_user: User = Depends(get_current_user),
    gateway: DeliveryGateway = Depends(get_delivery_gateway),
):
    try:
        return gateway.get_delivery(delivery_id, current_user)
    except DomainError as e:
        raise to_http(e) from e


@router.patch("/{delivery_id}/complete")
def complete_delivery(
    delivery_id: int,
    current_user: User = Depends(require_role(Role.COURIER, Role.ADMIN)),
    gateway: DeliveryGateway = Depends(get_delivery_gateway),
):
    try:
        gateway.complete_delivery(delivery_id, current_user)
    except DomainError as e:
        raise to_http(e) from e

    return {"status": "success"}
