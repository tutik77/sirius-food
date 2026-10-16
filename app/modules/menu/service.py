"""
Слой бизнес-логики модуля меню (круги Entities и Use Cases).

Положительная цена и минимальная длина названия — инварианты блюда.
Они проверяются здесь, а не в роутере, чтобы правило «цена > 0» жило
в одном месте и для создания, и для изменения блюда.
"""
from app.domain.entities import MenuItem
from app.modules.menu.exceptions import (
    DuplicateMenuItemError,
    InvalidPriceError,
    MenuItemNameTooShortError,
    MenuItemNotFoundError,
)
from app.modules.menu.repository import MenuRepository

MIN_NAME_LENGTH = 2


class MenuService:
    """Бизнес-правила ведения меню столовой."""

    def __init__(self, repository: MenuRepository):
        self.repository = repository

    def list_items(self) -> list[MenuItem]:
        """Меню целиком."""
        return self.repository.list_all()

    def create_item(self, name: str, price: float) -> MenuItem:
        """Добавляет блюдо. Название должно быть уникальным."""
        self._check_price(price)
        if len(name) < MIN_NAME_LENGTH:
            raise MenuItemNameTooShortError()
        if self.repository.get_by_name(name) is not None:
            raise DuplicateMenuItemError()

        return self.repository.add(MenuItem(id=None, name=name, price=price, is_available=True))

    def update_item(
        self,
        item_id: int,
        name: str | None = None,
        price: float | None = None,
        is_available: bool | None = None,
    ) -> MenuItem:
        """Частично изменяет блюдо: применяются только переданные поля."""
        item = self.repository.get_by_id(item_id)
        if item is None:
            raise MenuItemNotFoundError()
        if price is not None:
            self._check_price(price)

        if name is not None:
            item.name = name
        if price is not None:
            item.price = price
        if is_available is not None:
            item.is_available = is_available

        return self.repository.update(item)

    @staticmethod
    def _check_price(price: float) -> None:
        if price <= 0:
            raise InvalidPriceError()
