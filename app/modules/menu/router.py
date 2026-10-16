"""
Транспортный слой модуля меню (круг Frameworks & Drivers).
"""
from fastapi import APIRouter, Depends

from app.container import get_menu_service
from app.domain.errors import DomainError
from app.http_errors import to_http
from app.modules.menu.service import MenuService
from app.schemas import MenuItemCreate, MenuItemUpdate

router = APIRouter()


@router.post("/items")
def create_menu_item(payload: MenuItemCreate, service: MenuService = Depends(get_menu_service)):
    try:
        item = service.create_item(name=payload.name, price=payload.price)
    except DomainError as e:
        raise to_http(e)

    return {"status": "success", "item_id": item.id}


@router.patch("/items/{item_id}")
def update_menu_item(
    item_id: int,
    payload: MenuItemUpdate,
    service: MenuService = Depends(get_menu_service),
):
    try:
        item = service.update_item(
            item_id,
            name=payload.name,
            price=payload.price,
            is_available=payload.is_available,
        )
    except DomainError as e:
        raise to_http(e)

    return {"status": "success", "item_id": item.id}
