import asyncio
import logging

from sqlalchemy.orm import Session

from app.core.logging import setup_logging
from app.database import SessionLocal
from app.domain.events import DELIVERY_FAILED
from app.messaging.idempotency import claim_event
from app.messaging.rabbitmq import consume
from app.modules.orders.repository import SqlAlchemyOrderRepository
from app.modules.orders.service import OrderService

logger = logging.getLogger("orders.saga")

CONSUMER = "orders"
QUEUE = "orders_queue"


def handle(db: Session, routing_key: str, payload: dict) -> None:
    if not claim_event(db, CONSUMER, payload["event_id"]):
        logger.info("[Orders] Событие %s уже обработано, пропуск", payload["event_id"])
        return

    order = OrderService(SqlAlchemyOrderRepository(db)).compensate_failed_delivery(
        payload["order_id"], payload["reason"]
    )
    if order is None:
        logger.info("[Orders] Заказ %s не в статусе paid, компенсация не нужна", payload["order_id"])
    else:
        logger.info("[Orders] Компенсация: заказ %s отменён, возвращено %s", order.id, order.total_cost)
    db.commit()


def on_event(routing_key: str, payload: dict) -> None:
    with SessionLocal() as db:
        handle(db, routing_key, payload)


if __name__ == "__main__":
    setup_logging()
    asyncio.run(consume(QUEUE, [DELIVERY_FAILED], on_event))
