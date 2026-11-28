import asyncio
from decimal import Decimal

import structlog
from sqlalchemy.orm import Session

from app.core.logging import setup_logging
from app.core.sentry import setup_sentry
from app.core.tracing import setup_tracing
from app.database import SessionLocal
from app.domain.events import ORDER_CANCELLED, ORDER_PAID
from app.messaging.idempotency import claim_event
from app.messaging.rabbitmq import consume
from app.modules.loyalty.repository import SqlAlchemyLoyaltyRepository
from app.modules.loyalty.service import LoyaltyService

logger = structlog.get_logger("loyalty")

CONSUMER = "loyalty"
QUEUE = "loyalty_queue"


def handle(db: Session, routing_key: str, payload: dict) -> None:
    order_id = payload["order_id"]
    if not claim_event(db, CONSUMER, payload["event_id"]):
        logger.info("event_duplicate_skipped", event_id=payload["event_id"], order_id=order_id)
        return

    service = LoyaltyService(SqlAlchemyLoyaltyRepository(db))
    if routing_key == ORDER_PAID:
        earned = service.earn(payload["user_id"], order_id, Decimal(str(payload["amount"])))
        logger.info("points_earned", order_id=order_id, points=str(earned.amount) if earned else "0")
    elif routing_key == ORDER_CANCELLED:
        for transaction in service.compensate_order(order_id):
            logger.info("points_compensated", order_id=order_id, type=transaction.type, points=str(transaction.amount))
    db.commit()


def on_event(routing_key: str, payload: dict) -> None:
    with SessionLocal() as db:
        handle(db, routing_key, payload)


if __name__ == "__main__":
    setup_logging("loyalty")
    setup_tracing("loyalty")
    setup_sentry("loyalty")
    asyncio.run(consume(QUEUE, [ORDER_PAID, ORDER_CANCELLED], on_event))
