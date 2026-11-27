import asyncio

import structlog
from sqlalchemy.orm import Session

from app import models
from app.core.logging import setup_logging
from app.core.tracing import setup_tracing
from app.database import SessionLocal
from app.domain.events import ORDER_CANCELLED, ORDER_PAID
from app.messaging.idempotency import claim_event
from app.messaging.rabbitmq import consume

logger = structlog.get_logger("kitchen")

CONSUMER = "kitchen"
QUEUE = "kitchen_queue"


def handle(db: Session, routing_key: str, payload: dict) -> None:
    order_id = payload["order_id"]
    if not claim_event(db, CONSUMER, payload["event_id"]):
        logger.info("event_duplicate_skipped", event_id=payload["event_id"], order_id=order_id)
        return

    if routing_key == ORDER_PAID:
        db.add(models.KitchenOrder(order_id=order_id, status="pending"))
        logger.info("kitchen_order_accepted", order_id=order_id)
    elif routing_key == ORDER_CANCELLED:
        kitchen_order = db.query(models.KitchenOrder).filter_by(order_id=order_id).first()
        if kitchen_order is not None:
            kitchen_order.status = "cancelled"
        logger.info("kitchen_order_cancelled", order_id=order_id, reason=payload["reason"])
    db.commit()


def on_event(routing_key: str, payload: dict) -> None:
    with SessionLocal() as db:
        handle(db, routing_key, payload)


if __name__ == "__main__":
    setup_logging("kitchen")
    setup_tracing("kitchen")
    asyncio.run(consume(QUEUE, [ORDER_PAID, ORDER_CANCELLED], on_event))
