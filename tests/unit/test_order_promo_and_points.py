from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.entities import DiscountType, MenuItem, OrderStatus, PromoCode, User
from app.domain.events import OrderCancelled, OrderPaid
from app.memory_storage import InMemoryStorage
from app.modules.loyalty.repository import InMemoryLoyaltyRepository
from app.modules.loyalty.service import LoyaltyService
from app.modules.orders.repository import InMemoryOrderRepository
from app.modules.orders.service import OrderService
from app.modules.promo.exceptions import PromoCodeExhaustedError
from app.modules.promo.repository import InMemoryPromoRepository
from app.modules.promo.service import PromoService
from app.modules.users.repository import InMemoryUserRepository


@pytest.fixture
def storage():
    return InMemoryStorage()


@pytest.fixture
def promo(storage):
    return PromoService(InMemoryPromoRepository(storage))


@pytest.fixture
def loyalty(storage):
    return LoyaltyService(InMemoryLoyaltyRepository(storage))


@pytest.fixture
def service(storage, promo, loyalty):
    return OrderService(InMemoryOrderRepository(storage), promo, loyalty)


@pytest.fixture
def student(storage):
    return InMemoryUserRepository(storage).add(User(id=None, email="s@sirius.ru", balance=1000))


@pytest.fixture
def borsch(storage):
    item = MenuItem(id=storage.next_id("menu_items"), name="Борщ", price=250)
    storage.menu_items[item.id] = item
    return item


def add_promo(promo: PromoService, max_uses: int = 10) -> PromoCode:
    now = datetime.utcnow()
    return promo.create(
        PromoCode(
            id=None,
            code="STUDENT10",
            discount_type=DiscountType.PERCENT,
            discount_value=Decimal("10"),
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=1),
            max_uses=max_uses,
        )
    )


def test_promo_code_lowers_order_cost_and_is_recorded(service, promo, storage, student, borsch):
    created = add_promo(promo)

    order = service.create_order(student.id, borsch.id, quantity=2, promo_code="STUDENT10")

    assert (order.total_cost, order.discount, order.promo_code_id) == (450, 50, created.id)
    assert storage.users[student.id].balance == 550
    assert storage.promo_codes[created.id].current_uses == 1
    [usage] = storage.promo_usages.values()
    assert (usage.order_id, usage.user_id, usage.discount) == (order.id, student.id, Decimal("50.00"))


def test_exhausted_promo_does_not_charge_money(service, promo, storage, student, borsch):
    add_promo(promo, max_uses=1)
    service.create_order(student.id, borsch.id, quantity=1, promo_code="STUDENT10")
    other = InMemoryUserRepository(storage).add(User(id=None, email="o@sirius.ru", balance=1000))

    with pytest.raises(PromoCodeExhaustedError):
        service.create_order(other.id, borsch.id, quantity=1, promo_code="STUDENT10")
    assert storage.users[other.id].balance == 1000


def test_paying_with_points_returns_money_and_event_has_money_part(service, loyalty, storage, student, borsch):
    order = service.create_order(student.id, borsch.id, quantity=2)
    loyalty.earn(student.id, 999, Decimal("10000"))

    paid = service.pay_order(order.id, student, points=Decimal("200"))

    assert (paid.status, paid.points_spent, paid.paid_with_money) == (OrderStatus.PAID, 200, 300)
    assert storage.users[student.id].balance == 700
    event = storage.outbox[-1]
    assert isinstance(event, OrderPaid)
    assert event.amount == 300


def test_cancel_publishes_order_cancelled(service, storage, student, borsch):
    order = service.create_order(student.id, borsch.id, quantity=1)

    service.cancel_order(order.id, student)

    event = storage.outbox[-1]
    assert isinstance(event, OrderCancelled)
    assert (event.order_id, event.refund) == (order.id, 250)


def test_failed_delivery_refunds_only_money_part(service, loyalty, storage, student, borsch):
    order = service.create_order(student.id, borsch.id, quantity=2)
    loyalty.earn(student.id, 999, Decimal("10000"))
    service.pay_order(order.id, student, points=Decimal("200"))

    service.compensate_failed_delivery(order.id, "Нет свободного курьера")

    assert storage.users[student.id].balance == 1000
    assert storage.outbox[-1].refund == 300
