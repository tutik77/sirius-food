import asyncio

import structlog
from sqlalchemy.orm import Session

from app.core.logging import setup_logging
from app.core.sentry import setup_sentry
from app.core.tracing import setup_tracing
from app.database import SessionLocal
from app.domain.events import ORDER_CANCELLED
from app.messaging.idempotency import claim_event
from app.messaging.rabbitmq import consume
from app.modules.promo.repository import SqlAlchemyPromoRepository
from app.modules.promo.service import PromoService

logger = structlog.get_logger("promo")

CONSUMER = "promo"
QUEUE = "promo_queue"


def restore_key(order_id: int) -> str:
    return f"restore_promo_order_{order_id}"


def handle(db: Session, routing_key: str, payload: dict) -> None:
    order_id = payload["order_id"]
    if not claim_event(db, CONSUMER, restore_key(order_id)):
        logger.info("promo_restore_skipped", order_id=order_id)
        return

    restored = PromoService(SqlAlchemyPromoRepository(db)).restore_for_order(order_id)
    logger.info("promo_restored" if restored else "promo_not_used", order_id=order_id)
    db.commit()


def on_event(routing_key: str, payload: dict) -> None:
    with SessionLocal() as db:
        handle(db, routing_key, payload)


if __name__ == "__main__":
    setup_logging("promo")
    setup_tracing("promo")
    setup_sentry("promo")
    asyncio.run(consume(QUEUE, [ORDER_CANCELLED], on_event))
