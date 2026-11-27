import asyncio

import structlog
from sqlalchemy.orm import Session

from app.core.logging import setup_logging
from app.core.tracing import setup_tracing
from app.database import SessionLocal
from app.domain.events import DELIVERY_FAILED
from app.messaging.idempotency import claim_event
from app.messaging.rabbitmq import consume
from app.modules.orders.repository import SqlAlchemyOrderRepository
from app.modules.orders.service import OrderService

logger = structlog.get_logger("orders.saga")

CONSUMER = "orders"
QUEUE = "orders_queue"


def handle(db: Session, routing_key: str, payload: dict) -> None:
    order_id = payload["order_id"]
    if not claim_event(db, CONSUMER, payload["event_id"]):
        logger.info("event_duplicate_skipped", event_id=payload["event_id"], order_id=order_id)
        return

    order = OrderService(SqlAlchemyOrderRepository(db)).compensate_failed_delivery(order_id, payload["reason"])
    if order is None:
        logger.info("compensation_not_needed", order_id=order_id)
    else:
        logger.info("order_compensated", order_id=order.id, refund=order.total_cost)
    db.commit()


def on_event(routing_key: str, payload: dict) -> None:
    with SessionLocal() as db:
        handle(db, routing_key, payload)


if __name__ == "__main__":
    setup_logging("orders_saga")
    setup_tracing("orders_saga")
    asyncio.run(consume(QUEUE, [DELIVERY_FAILED], on_event))
