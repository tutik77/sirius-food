import pytest

from app.modules.menu.exceptions import (
    DuplicateMenuItemError,
    InvalidPriceError,
    MenuItemNameTooShortError,
    MenuItemNotFoundError,
)
from app.modules.menu.service import MenuService


@pytest.fixture
def service(repos):
    return MenuService(repos.menu)


def test_create_item_is_available_by_default(service):
    item = service.create_item("Борщ", 250)

    assert item.id is not None
    assert item.is_available is True


@pytest.mark.parametrize("price", [0, -10])
def test_create_item_requires_positive_price(service, price):
    with pytest.raises(InvalidPriceError):
        service.create_item("Борщ", price)


def test_create_item_requires_name_of_two_chars(service):
    with pytest.raises(MenuItemNameTooShortError):
        service.create_item("Я", 100)


def test_name_of_exactly_two_chars_and_price_of_one_are_allowed(service):
    item = service.create_item("Чай"[:2], 1)

    assert (item.name, item.price) == ("Ча", 1)


def test_update_renames_item(service, repos):
    item = service.create_item("Борщ", 250)

    service.update_item(item.id, name="Борщ украинский")

    assert repos.menu.get_by_id(item.id).name == "Борщ украинский"


def test_create_item_name_must_be_unique(service):
    service.create_item("Борщ", 250)

    with pytest.raises(DuplicateMenuItemError):
        service.create_item("Борщ", 300)


def test_update_changes_only_passed_fields(service, repos):
    item = service.create_item("Борщ", 250)

    service.update_item(item.id, is_available=False)

    stored = repos.menu.get_by_id(item.id)
    assert stored.is_available is False
    assert stored.name == "Борщ"
    assert stored.price == 250


def test_update_unknown_item(service):
    with pytest.raises(MenuItemNotFoundError):
        service.update_item(999, price=100)


def test_update_with_invalid_price_changes_nothing(service, repos):
    item = service.create_item("Борщ", 250)

    with pytest.raises(InvalidPriceError):
        service.update_item(item.id, name="Щи", price=-1)

    assert repos.menu.get_by_id(item.id).name == "Борщ"


def test_get_item_returns_item_or_raises(repos):
    service = MenuService(repos.menu)
    item = service.create_item("Сырники", 150)

    assert service.get_item(item.id).name == "Сырники"
    with pytest.raises(MenuItemNotFoundError):
        service.get_item(999)
