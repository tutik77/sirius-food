from decimal import Decimal

import pytest

from app.domain.entities import LoyaltyTier, MenuItem, Order
from app.modules.loyalty.exceptions import NotEnoughPointsError, PointsLimitExceededError
from app.modules.loyalty.service import LoyaltyService


@pytest.fixture
def service(repos):
    return LoyaltyService(repos.loyalty)


@pytest.fixture
def new_order(repos, make_user):
    def factory(user) -> int:
        item = repos.menu.add(MenuItem(id=None, name=f"Блюдо {user.id}-{len(repos.orders.list_by_user(user.id))}", price=100))
        order = Order(id=None, user_id=user.id, item_id=item.id, quantity=1, total_cost=100)
        return repos.orders.save_order(order, payer=user).id

    return factory


def test_bronze_earns_three_percent_once(service, make_user, new_order):
    student = make_user()
    order = new_order(student)

    assert service.earn(student.id, order, Decimal("1000")).amount == Decimal("30.00")
    assert service.earn(student.id, order, Decimal("1000")) is None

    account = service.account_for(student.id)
    assert (account.balance, account.total_earned) == (Decimal("30.00"), Decimal("30.00"))


def test_tier_grows_with_total_earned(service, make_user, new_order):
    student = make_user()

    service.earn(student.id, new_order(student), Decimal("33400"))
    assert service.account_for(student.id).tier == LoyaltyTier.SILVER

    service.earn(student.id, new_order(student), Decimal("80000"))
    account = service.account_for(student.id)
    assert account.tier == LoyaltyTier.GOLD
    assert account.points_for(Decimal("100")) == Decimal("7.00")


def test_spend_at_most_half_of_order(service, make_user, new_order):
    student = make_user()
    service.earn(student.id, new_order(student), Decimal("10000"))

    with pytest.raises(PointsLimitExceededError):
        service.spend(student.id, new_order(student), Decimal("150.01"), order_amount=Decimal("300"))
    assert service.spend(student.id, new_order(student), Decimal("150"), order_amount=Decimal("300")).amount == Decimal("-150.00")
    assert service.account_for(student.id).balance == Decimal("150.00")


def test_spend_needs_enough_points(service, make_user, new_order):
    student = make_user()

    with pytest.raises(NotEnoughPointsError):
        service.spend(student.id, new_order(student), Decimal("10"), order_amount=Decimal("300"))


def test_compensation_refunds_spent_and_revokes_earned_once(service, make_user, new_order):
    student = make_user()
    service.earn(student.id, new_order(student), Decimal("10000"))
    order = new_order(student)
    service.spend(student.id, order, Decimal("100"), order_amount=Decimal("300"))
    service.earn(student.id, order, Decimal("200"))

    compensations = service.compensate_order(order)

    assert [(t.type, t.amount) for t in compensations] == [("refund", Decimal("100.00")), ("revoke", Decimal("-6.00"))]
    assert service.compensate_order(order) == []
    account = service.account_for(student.id)
    assert (account.balance, account.total_earned) == (Decimal("300.00"), Decimal("300.00"))


def test_revoke_does_not_make_balance_negative(service, make_user, new_order):
    student = make_user()
    order = new_order(student)
    service.earn(student.id, order, Decimal("1000"))
    service.spend(student.id, new_order(student), Decimal("30"), order_amount=Decimal("100"))

    [revoke] = service.compensate_order(order)

    assert revoke.amount == Decimal("0")
    assert service.account_for(student.id).balance == Decimal("0")
