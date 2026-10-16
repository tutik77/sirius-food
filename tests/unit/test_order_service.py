"""
Unit-тесты OrderService без СУБД.
"""
import pytest

from app.domain.entities import MenuItem, OrderStatus, User
from app.modules.orders.exceptions import (
    InsufficientFundsError,
    MenuItemNotFoundError,
    MenuItemUnavailableError,
    UserNotFoundError,
)
from app.modules.orders.service import OrderService


@pytest.fixture
def service(repos):
    return OrderService(repos.orders)


@pytest.fixture
def student(repos):
    return repos.users.add(User(id=None, email="anna@sirius.ru", balance=1000))


@pytest.fixture
def borsch(repos):
    return repos.menu.add(MenuItem(id=None, name="Борщ", price=250))


def test_create_order_charges_balance(service, repos, student, borsch):
    order = service.create_order(student.id, borsch.id, quantity=2)

    assert order.id is not None
    assert order.status == OrderStatus.PROCESSING
    assert repos.users.get_by_id(student.id).balance == 500


def test_unknown_user(service, borsch):
    with pytest.raises(UserNotFoundError):
        service.create_order(999, borsch.id, quantity=1)


def test_unknown_menu_item(service, student):
    with pytest.raises(MenuItemNotFoundError):
        service.create_order(student.id, 999, quantity=1)


def test_unavailable_menu_item(service, repos, student):
    item = repos.menu.add(MenuItem(id=None, name="Стейк", price=900, is_available=False))

    with pytest.raises(MenuItemUnavailableError):
        service.create_order(student.id, item.id, quantity=1)


def test_insufficient_funds_keeps_balance(service, repos, student, borsch):
    with pytest.raises(InsufficientFundsError):
        service.create_order(student.id, borsch.id, quantity=5)

    assert repos.users.get_by_id(student.id).balance == 1000
