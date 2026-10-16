"""
Транспортный слой модуля доставки (круг Frameworks & Drivers).
"""
from fastapi import APIRouter, Depends

from app.container import get_delivery_service
from app.domain.errors import DomainError
from app.http_errors import to_http
from app.modules.delivery.service import DeliveryService
from app.schemas import DeliveryAssign

router = APIRouter()


@router.post("/assign")
def assign_courier(payload: DeliveryAssign, service: DeliveryService = Depends(get_delivery_service)):
    try:
        delivery = service.assign_courier(order_id=payload.order_id, courier_id=payload.courier_id)
    except DomainError as e:
        raise to_http(e)

    return {"status": "success", "delivery_id": delivery.id}


@router.patch("/{delivery_id}/complete")
def complete_delivery(delivery_id: int, service: DeliveryService = Depends(get_delivery_service)):
    try:
        service.complete_delivery(delivery_id)
    except DomainError as e:
        raise to_http(e)

    return {"status": "success"}
