"""
Unit-тесты DeliveryService без СУБД.
"""
import pytest

from app.domain.entities import Delivery, DeliveryStatus, MenuItem, Order, OrderStatus, Role
from app.modules.delivery.exceptions import (
    CourierBlockedError,
    CourierBusyError,
    CourierNotFoundError,
    DeliveryAccessDeniedError,
    DeliveryAlreadyCompletedError,
    DeliveryCancelledError,
    DeliveryNotFoundError,
    NotACourierError,
    OrderNotFoundError,
    OrderNotPaidError,
)
from app.modules.delivery.service import DeliveryService


@pytest.fixture
def service(repos):
    return DeliveryService(repos.delivery)


@pytest.fixture
def courier(make_user):
    return make_user(role=Role.COURIER)


@pytest.fixture
def admin(make_user):
    return make_user(role=Role.ADMIN)


@pytest.fixture
def make_order(repos, make_user):
    def factory(status=OrderStatus.PAID, owner=None) -> Order:
        owner = owner or make_user(balance=1000)
        item = repos.menu.get_by_name("Борщ") or repos.menu.add(MenuItem(id=None, name="Борщ", price=250))
        order = Order(id=None, user_id=owner.id, item_id=item.id, quantity=1, status=status, total_cost=250)
        return repos.orders.save_order(order, payer=owner)

    return factory


def test_assign_courier_to_paid_order(service, make_order, courier):
    delivery = service.assign_courier(make_order().id, courier.id)

    assert delivery.id is not None
    assert delivery.status == DeliveryStatus.IN_PROGRESS


def test_unknown_order(service, courier):
    with pytest.raises(OrderNotFoundError):
        service.assign_courier(999, courier.id)


def test_order_must_be_paid(service, make_order, courier):
    with pytest.raises(OrderNotPaidError):
        service.assign_courier(make_order(status=OrderStatus.PROCESSING).id, courier.id)


def test_unknown_courier(service, make_order):
    with pytest.raises(CourierNotFoundError):
        service.assign_courier(make_order().id, 999)


def test_blocked_courier(service, make_order, make_user):
    blocked = make_user(role=Role.COURIER, is_blocked=True)

    with pytest.raises(CourierBlockedError):
        service.assign_courier(make_order().id, blocked.id)


def test_only_courier_role_can_be_assigned(service, make_order, make_user):
    with pytest.raises(NotACourierError):
        service.assign_courier(make_order().id, make_user(role=Role.STUDENT).id)


def test_courier_has_only_one_active_delivery(service, make_order, courier):
    order = make_order()
    service.assign_courier(order.id, courier.id)

    with pytest.raises(CourierBusyError):
        service.assign_courier(order.id, courier.id)


def test_complete_delivery_marks_order_delivered(service, repos, make_order, courier):
    order = make_order()
    delivery = service.assign_courier(order.id, courier.id)

    service.complete_delivery(delivery.id, courier)

    assert repos.delivery.get_delivery(delivery.id).status == DeliveryStatus.COMPLETED
    assert repos.delivery.get_order(order.id).status == OrderStatus.DELIVERED


def test_foreign_courier_cannot_complete_delivery(service, repos, make_order, make_user, courier):
    """IDOR: другой курьер подставляет id чужой доставки."""
    delivery = service.assign_courier(make_order().id, courier.id)

    with pytest.raises(DeliveryAccessDeniedError):
        service.complete_delivery(delivery.id, make_user(role=Role.COURIER))

    assert repos.delivery.get_delivery(delivery.id).status == DeliveryStatus.IN_PROGRESS


def test_complete_unknown_delivery(service, courier):
    with pytest.raises(DeliveryNotFoundError):
        service.complete_delivery(999, courier)


def test_complete_twice(service, make_order, courier):
    delivery = service.assign_courier(make_order().id, courier.id)
    service.complete_delivery(delivery.id, courier)

    with pytest.raises(DeliveryAlreadyCompletedError):
        service.complete_delivery(delivery.id, courier)


def test_cancelled_delivery_cannot_be_completed(service, repos, make_order, admin, courier):
    cancelled = repos.delivery.add(
        Delivery(id=None, order_id=make_order().id, courier_id=courier.id, status=DeliveryStatus.CANCELLED)
    )

    with pytest.raises(DeliveryCancelledError):
        service.complete_delivery(cancelled.id, admin)


def test_delivery_visible_to_courier_owner_and_admin(service, make_order, make_user, courier, admin):
    owner = make_user(balance=1000)
    delivery = service.assign_courier(make_order(owner=owner).id, courier.id)

    for viewer in (courier, owner, admin):
        assert service.get_delivery(delivery.id, viewer).id == delivery.id


def test_student_cannot_see_foreign_delivery(service, make_order, make_user, courier):
    delivery = service.assign_courier(make_order().id, courier.id)

    with pytest.raises(DeliveryAccessDeniedError):
        service.get_delivery(delivery.id, make_user())


def test_courier_sees_only_own_deliveries(service, make_order, make_user, courier):
    other_courier = make_user(role=Role.COURIER)
    mine = service.assign_courier(make_order().id, courier.id)
    service.assign_courier(make_order().id, other_courier.id)

    assert [d.id for d in service.list_courier_deliveries(courier)] == [mine.id]
