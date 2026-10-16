"""
Unit-тесты OrderService без СУБД.
"""
import pytest

from app.domain.entities import MenuItem, OrderStatus, Role
from app.modules.orders.exceptions import (
    AccessDeniedError,
    InsufficientFundsError,
    MenuItemNotFoundError,
    MenuItemUnavailableError,
    OrderCannotBeCancelledError,
    OrderNotFoundError,
    UserNotFoundError,
)
from app.modules.orders.service import OrderService


@pytest.fixture
def service(repos):
    return OrderService(repos.orders)


@pytest.fixture
def student(make_user):
    return make_user(balance=1000)


@pytest.fixture
def borsch(repos):
    return repos.menu.add(MenuItem(id=None, name="Борщ", price=250))


def test_create_order_charges_balance(service, repos, student, borsch):
    order = service.create_order(student.id, borsch.id, quantity=2)

    assert order.id is not None
    assert order.status == OrderStatus.PROCESSING
    assert order.total_cost == 500
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


def test_cancel_own_order_refunds_money(service, repos, student, borsch):
    order = service.create_order(student.id, borsch.id, quantity=2)

    service.cancel_order(order.id, student)

    assert repos.orders.get_order(order.id).status == OrderStatus.CANCELLED
    assert repos.users.get_by_id(student.id).balance == 1000


def test_cancel_foreign_order_is_forbidden(service, repos, make_user, student, borsch):
    """IDOR: студент Б подставляет id заказа студента А."""
    order = service.create_order(student.id, borsch.id, quantity=1)
    attacker = make_user()

    with pytest.raises(AccessDeniedError):
        service.cancel_order(order.id, attacker)

    assert repos.orders.get_order(order.id).status == OrderStatus.PROCESSING
    assert repos.users.get_by_id(student.id).balance == 750


def test_admin_can_cancel_any_order(service, repos, make_user, student, borsch):
    order = service.create_order(student.id, borsch.id, quantity=1)

    service.cancel_order(order.id, make_user(role=Role.ADMIN))

    assert repos.orders.get_order(order.id).status == OrderStatus.CANCELLED


def test_cancel_unknown_order(service, student):
    with pytest.raises(OrderNotFoundError):
        service.cancel_order(999, student)


def test_cancel_only_processing_order(service, student, borsch):
    order = service.create_order(student.id, borsch.id, quantity=1)
    service.cancel_order(order.id, student)

    with pytest.raises(OrderCannotBeCancelledError):
        service.cancel_order(order.id, student)


def test_user_sees_only_own_orders(service, make_user, student, borsch):
    other = make_user(balance=1000)
    mine = service.create_order(student.id, borsch.id, quantity=1)
    service.create_order(other.id, borsch.id, quantity=1)

    assert [o.id for o in service.list_user_orders(student)] == [mine.id]


def test_kitchen_sees_only_processing_orders(service, student, borsch):
    first = service.create_order(student.id, borsch.id, quantity=1)
    second = service.create_order(student.id, borsch.id, quantity=1)
    service.cancel_order(second.id, student)

    assert [o.id for o in service.get_kitchen_orders()] == [first.id]
