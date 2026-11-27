import asyncio

import structlog
from sqlalchemy.orm import Session

from app.core.logging import setup_logging
from app.core.tracing import setup_tracing
from app.database import SessionLocal
from app.domain.errors import DomainError
from app.domain.events import ORDER_PAID, DeliveryFailed
from app.messaging.idempotency import claim_event
from app.messaging.outbox import OutboxRepository
from app.messaging.rabbitmq import consume
from delivery_service.repository import SqlAlchemyDeliveryRepository
from delivery_service.service import DeliveryService

logger = structlog.get_logger("delivery_worker")

CONSUMER = "delivery"
QUEUE = "delivery_queue"


def handle(db: Session, routing_key: str, payload: dict) -> None:
    order_id = payload["order_id"]
    if not claim_event(db, CONSUMER, payload["event_id"]):
        logger.info("event_duplicate_skipped", event_id=payload["event_id"], order_id=order_id)
        return

    try:
        delivery = DeliveryService(SqlAlchemyDeliveryRepository(db)).assign_free_courier(order_id)
        logger.info("courier_assigned", order_id=order_id, courier_id=delivery.courier_id)
    except DomainError as e:
        OutboxRepository(db).add(DeliveryFailed(order_id=order_id, reason=e.message))
        logger.warning("delivery_failed", order_id=order_id, reason=e.message)
    db.commit()


def on_event(routing_key: str, payload: dict) -> None:
    with SessionLocal() as db:
        handle(db, routing_key, payload)


if __name__ == "__main__":
    setup_logging("delivery_worker")
    setup_tracing("delivery_worker")
    asyncio.run(consume(QUEUE, [ORDER_PAID], on_event))
