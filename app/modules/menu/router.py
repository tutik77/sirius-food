"""
Транспортный слой модуля меню (круг Frameworks & Drivers).

Смотреть меню может кто угодно, менять — только повар или администратор.
"""
from fastapi import APIRouter, Depends

from app.container import get_menu_service
from app.core.dependencies import require_role
from app.domain.entities import Role, User
from app.domain.errors import DomainError
from app.http_errors import to_http
from app.modules.menu.service import MenuService
from app.schemas import MenuItemCreate, MenuItemResponse, MenuItemUpdate

router = APIRouter()

menu_editor = require_role(Role.COOK, Role.ADMIN)


@router.get("/items", response_model=list[MenuItemResponse])
def list_menu_items(service: MenuService = Depends(get_menu_service)):
    return service.list_items()


@router.get("/items/{item_id}", response_model=MenuItemResponse)
def get_menu_item(item_id: int, service: MenuService = Depends(get_menu_service)):
    try:
        return service.get_item(item_id)
    except DomainError as e:
        raise to_http(e)


@router.post("/items")
def create_menu_item(
    payload: MenuItemCreate,
    current_user: User = Depends(menu_editor),
    service: MenuService = Depends(get_menu_service),
):
    try:
        item = service.create_item(name=payload.name, price=payload.price)
    except DomainError as e:
        raise to_http(e)

    return {"status": "success", "item_id": item.id}


@router.patch("/items/{item_id}")
def update_menu_item(
    item_id: int,
    payload: MenuItemUpdate,
    current_user: User = Depends(menu_editor),
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
