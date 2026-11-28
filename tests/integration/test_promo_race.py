from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.domain.errors import DomainError
from app.modules.loyalty.repository import SqlAlchemyLoyaltyRepository
from app.modules.loyalty.service import LoyaltyService
from app.modules.orders.repository import SqlAlchemyOrderRepository
from app.modules.orders.service import OrderService
from app.modules.promo.repository import SqlAlchemyPromoRepository
from app.modules.promo.service import PromoService

CLIENTS = 30


def add_promo(db, code: str, max_uses: int) -> None:
    now = datetime.utcnow()
    db.add(models.PromoCode(code=code, discount_type="percent", discount_value=50, valid_from=now - timedelta(days=1),
                            valid_until=now + timedelta(days=1), max_uses=max_uses, current_uses=0,
                            min_order_amount=0, is_active=True))
    db.commit()


def order_concurrently(postgres_url: str, student_ids: list[int], item_id: int, code: str) -> list[str]:
    sessions = sessionmaker(bind=create_engine(postgres_url, pool_size=len(student_ids)))

    def order_with_promo(student_id: int) -> str:
        with sessions() as session:
            service = OrderService(
                SqlAlchemyOrderRepository(session),
                PromoService(SqlAlchemyPromoRepository(session)),
                LoyaltyService(SqlAlchemyLoyaltyRepository(session)),
            )
            try:
                service.create_order(student_id, item_id, quantity=1, promo_code=code)
                return "applied"
            except DomainError as e:
                session.rollback()
                return type(e).__name__

    with ThreadPoolExecutor(len(student_ids)) as pool:
        return list(pool.map(order_with_promo, student_ids))


def test_single_use_promo_is_applied_exactly_once_under_concurrency(postgres_url, db, make_user, make_item):
    add_promo(db, "ONCE", max_uses=1)
    students = [make_user(balance=1000).id for _ in range(CLIENTS)]

    results = order_concurrently(postgres_url, students, make_item(price=200).id, "ONCE")

    assert results.count("applied") == 1
    assert set(results) == {"applied", "PromoCodeExhaustedError"}
    db.expire_all()
    assert db.query(models.PromoCode).filter_by(code="ONCE").one().current_uses == 1
    assert db.query(models.PromoCodeUsage).count() == 1
    assert db.query(models.Order).count() == 1


def test_client_applies_promo_once_even_with_parallel_orders(postgres_url, db, make_user, make_item):
    add_promo(db, "MANY", max_uses=100)
    student_id = make_user(balance=10_000).id

    results = order_concurrently(postgres_url, [student_id] * 10, make_item(price=200).id, "MANY")

    assert results.count("applied") == 1
    assert set(results) == {"applied", "PromoCodeAlreadyUsedError"}
    db.expire_all()
    assert db.query(models.PromoCode).filter_by(code="MANY").one().current_uses == 1
    assert db.query(models.PromoCodeUsage).count() == 1
