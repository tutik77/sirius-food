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


def test_single_use_promo_is_applied_exactly_once_under_concurrency(postgres_url, db, make_user, make_item):
    now = datetime.utcnow()
    db.add(models.PromoCode(code="ONCE", discount_type="percent", discount_value=50, valid_from=now - timedelta(days=1),
                            valid_until=now + timedelta(days=1), max_uses=1, current_uses=0, min_order_amount=0, is_active=True))
    db.commit()
    students = [make_user(balance=1000).id for _ in range(CLIENTS)]
    item_id = make_item(price=200).id
    sessions = sessionmaker(bind=create_engine(postgres_url, pool_size=CLIENTS))

    def order_with_promo(student_id: int) -> str:
        with sessions() as session:
            service = OrderService(
                SqlAlchemyOrderRepository(session),
                PromoService(SqlAlchemyPromoRepository(session)),
                LoyaltyService(SqlAlchemyLoyaltyRepository(session)),
            )
            try:
                service.create_order(student_id, item_id, quantity=1, promo_code="ONCE")
                return "applied"
            except DomainError as e:
                session.rollback()
                return type(e).__name__

    with ThreadPoolExecutor(CLIENTS) as pool:
        results = list(pool.map(order_with_promo, students))

    assert results.count("applied") == 1
    assert set(results) == {"applied", "PromoCodeExhaustedError"}
    db.expire_all()
    assert db.query(models.PromoCode).filter_by(code="ONCE").one().current_uses == 1
    assert db.query(models.PromoCodeUsage).count() == 1
    assert db.query(models.Order).count() == 1
