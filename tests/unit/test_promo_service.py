from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.entities import DiscountType, MenuItem, Order, PromoCode, PromoUsage
from app.modules.promo.exceptions import (
    InvalidPromoCodeError,
    PromoCodeAlreadyUsedError,
    PromoCodeDuplicateError,
    PromoCodeExhaustedError,
    PromoCodeInactiveError,
    PromoCodeMinAmountError,
    PromoCodeNotFoundError,
)
from app.modules.promo.service import PromoService

NOW = datetime(2026, 11, 28, 12, 0)


@pytest.fixture
def service(repos):
    return PromoService(repos.promo, clock=lambda: NOW)


@pytest.fixture
def order_with_promo(repos, make_user):
    def factory(promo_id: int, user=None) -> int:
        user = user or make_user(balance=1000)
        item = repos.menu.add(MenuItem(id=None, name=f"Блюдо {user.id}", price=250))
        order = Order(id=None, user_id=user.id, item_id=item.id, quantity=1, total_cost=225, promo_code_id=promo_id, discount=25)
        usage = PromoUsage(id=None, promo_code_id=promo_id, user_id=user.id, order_id=None, discount=Decimal("25"))
        return repos.orders.save_order(order, payer=user, promo_usage=usage).id

    return factory


def promo(code="STUDENT10", kind=DiscountType.PERCENT, value="10", max_uses=100, min_amount="0", **dates) -> PromoCode:
    return PromoCode(
        id=None,
        code=code,
        discount_type=kind,
        discount_value=Decimal(value),
        valid_from=dates.get("valid_from", NOW - timedelta(days=1)),
        valid_until=dates.get("valid_until", NOW + timedelta(days=30)),
        max_uses=max_uses,
        min_order_amount=Decimal(min_amount),
    )


def test_percent_discount(service):
    service.create(promo(value="10"))

    assert service.quote("STUDENT10", user_id=1, amount=Decimal("250")).discount == Decimal("25.00")


def test_fixed_discount_is_not_bigger_than_order(service):
    service.create(promo(code="MINUS300", kind=DiscountType.FIXED, value="300"))

    assert service.quote("MINUS300", user_id=1, amount=Decimal("250")).discount == Decimal("250.00")


@pytest.mark.parametrize(
    "dates",
    [
        {"valid_until": NOW - timedelta(minutes=1), "valid_from": NOW - timedelta(days=2)},
        {"valid_from": NOW + timedelta(minutes=1)},
    ],
    ids=["expired", "not_started"],
)
def test_promo_outside_validity_period(service, dates):
    service.create(promo(**dates))

    with pytest.raises(PromoCodeInactiveError):
        service.quote("STUDENT10", user_id=1, amount=Decimal("250"))


def test_unknown_promo(service):
    with pytest.raises(PromoCodeNotFoundError):
        service.quote("NOPE", user_id=1, amount=Decimal("250"))


def test_min_order_amount(service):
    service.create(promo(min_amount="300"))

    with pytest.raises(PromoCodeMinAmountError):
        service.quote("STUDENT10", user_id=1, amount=Decimal("299.99"))
    assert service.quote("STUDENT10", user_id=1, amount=Decimal("300")).discount == Decimal("30.00")


def test_promo_is_single_use_per_client(service, repos, make_user, order_with_promo):
    created = service.create(promo())
    student, other = make_user(balance=1000), make_user(balance=1000)
    repos.promo.reserve_use(created.id)
    order_with_promo(created.id, student)

    with pytest.raises(PromoCodeAlreadyUsedError):
        service.quote("STUDENT10", user_id=student.id, amount=Decimal("250"))
    assert service.quote("STUDENT10", user_id=other.id, amount=Decimal("250"))


def test_reserve_respects_max_uses(service):
    service.create(promo(max_uses=1))
    quote = service.quote("STUDENT10", user_id=1, amount=Decimal("250"))

    service.reserve(quote)

    with pytest.raises(PromoCodeExhaustedError):
        service.reserve(quote)
    with pytest.raises(PromoCodeExhaustedError):
        service.quote("STUDENT10", user_id=2, amount=Decimal("250"))


def test_restore_for_order_releases_use_once(service, repos, make_user, order_with_promo):
    created = service.create(promo(max_uses=1))
    student = make_user(balance=1000)
    repos.promo.reserve_use(created.id)
    order_id = order_with_promo(created.id, student)

    assert service.restore_for_order(order_id) is True
    assert service.restore_for_order(order_id) is False
    assert repos.promo.get_by_code("STUDENT10").current_uses == 0
    assert service.quote("STUDENT10", user_id=student.id, amount=Decimal("250"))


def test_deactivate_expired(service, repos):
    service.create(promo(code="OLD", valid_from=NOW - timedelta(days=10), valid_until=NOW - timedelta(days=1)))
    service.create(promo(code="FRESH"))

    assert service.deactivate_expired() == 1
    assert repos.promo.get_by_code("OLD").is_active is False
    assert repos.promo.get_by_code("FRESH").is_active is True


@pytest.mark.parametrize(
    "bad",
    [
        promo(value="0"),
        promo(value="101"),
        promo(max_uses=0),
        promo(valid_from=NOW, valid_until=NOW - timedelta(days=1)),
    ],
    ids=["zero_value", "percent_over_100", "no_uses", "ends_before_start"],
)
def test_invalid_promo_is_rejected(service, bad):
    with pytest.raises(InvalidPromoCodeError):
        service.create(bad)


def test_duplicate_code_is_rejected(service):
    service.create(promo())

    with pytest.raises(PromoCodeDuplicateError):
        service.create(promo())
