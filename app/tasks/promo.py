from app.core.celery_app import celery_app
from app.database import SessionLocal
from app.modules.promo.repository import SqlAlchemyPromoRepository
from app.modules.promo.service import PromoService


@celery_app.task
def deactivate_expired_promo_codes() -> int:
    with SessionLocal() as db:
        return PromoService(SqlAlchemyPromoRepository(db)).deactivate_expired()
