"""
Unit-тесты DeliveryService без СУБД.
"""
from itertools import count

import pytest

from app.domain.entities import Delivery, DeliveryStatus, MenuItem, Order, OrderStatus, User
from app.modules.delivery.exceptions import (
    CourierBlockedError,
    CourierBusyError,
    CourierNotFoundError,
    DeliveryAlreadyCompletedError,
    DeliveryCancelledError,
    DeliveryNotFoundError,
    OrderNotFoundError,
    OrderNotPaidError,
)
from app.modules.delivery.service import DeliveryService


@pytest.fixture
def service(repos):
    return DeliveryService(repos.delivery)


@pytest.fixture
def courier(repos):
    return repos.users.add(User(id=None, email="courier@sirius.ru"))


_emails = count(1)


def make_order(repos, status=OrderStatus.PAID) -> Order:
    student = repos.users.add(User(id=None, email=f"student{next(_emails)}@sirius.ru", balance=1000))
    item = repos.menu.get_by_name("Борщ") or repos.menu.add(MenuItem(id=None, name="Борщ", price=250))
    order = Order(id=None, user_id=student.id, item_id=item.id, quantity=1, status=status)
    return repos.orders.save_order(order, payer=student)


def test_assign_courier_to_paid_order(service, repos, courier):
    order = make_order(repos)

    delivery = service.assign_courier(order.id, courier.id)

    assert delivery.id is not None
    assert delivery.status == DeliveryStatus.IN_PROGRESS


def test_unknown_order(service, courier):
    with pytest.raises(OrderNotFoundError):
        service.assign_courier(999, courier.id)


def test_order_must_be_paid(service, repos, courier):
    order = make_order(repos, status=OrderStatus.PROCESSING)

    with pytest.raises(OrderNotPaidError):
        service.assign_courier(order.id, courier.id)


def test_unknown_courier(service, repos):
    with pytest.raises(CourierNotFoundError):
        service.assign_courier(make_order(repos).id, 999)


def test_blocked_courier(service, repos):
    blocked = repos.users.add(User(id=None, email="blocked@sirius.ru", is_blocked=True))

    with pytest.raises(CourierBlockedError):
        service.assign_courier(make_order(repos).id, blocked.id)


def test_courier_has_only_one_active_delivery(service, repos, courier):
    order = make_order(repos)
    service.assign_courier(order.id, courier.id)

    with pytest.raises(CourierBusyError):
        service.assign_courier(order.id, courier.id)


def test_complete_delivery_marks_order_delivered(service, repos, courier):
    order = make_order(repos)
    delivery = service.assign_courier(order.id, courier.id)

    service.complete_delivery(delivery.id)

    assert repos.delivery.get_delivery(delivery.id).status == DeliveryStatus.COMPLETED
    assert repos.delivery.get_order(order.id).status == OrderStatus.DELIVERED


def test_complete_unknown_delivery(service):
    with pytest.raises(DeliveryNotFoundError):
        service.complete_delivery(999)


def test_complete_twice(service, repos, courier):
    delivery = service.assign_courier(make_order(repos).id, courier.id)
    service.complete_delivery(delivery.id)

    with pytest.raises(DeliveryAlreadyCompletedError):
        service.complete_delivery(delivery.id)


def test_cancelled_delivery_cannot_be_completed(service, repos, courier):
    order = make_order(repos)
    cancelled = repos.delivery.add(
        Delivery(id=None, order_id=order.id, courier_id=courier.id, status=DeliveryStatus.CANCELLED)
    )

    with pytest.raises(DeliveryCancelledError):
        service.complete_delivery(cancelled.id)
