import asyncio
import logging

from sqlalchemy.orm import Session

from app import models
from app.core.logging import setup_logging
from app.database import SessionLocal
from app.domain.events import ORDER_CANCELLED, ORDER_PAID
from app.messaging.idempotency import claim_event
from app.messaging.rabbitmq import consume

logger = logging.getLogger("kitchen")

CONSUMER = "kitchen"
QUEUE = "kitchen_queue"


def handle(db: Session, routing_key: str, payload: dict) -> None:
    order_id = payload["order_id"]
    if not claim_event(db, CONSUMER, payload["event_id"]):
        logger.info("[Kitchen] Событие %s уже обработано, пропуск", payload["event_id"])
        return

    if routing_key == ORDER_PAID:
        db.add(models.KitchenOrder(order_id=order_id, status="pending"))
        logger.info("[Kitchen] Принят заказ %s", order_id)
    elif routing_key == ORDER_CANCELLED:
        kitchen_order = db.query(models.KitchenOrder).filter_by(order_id=order_id).first()
        if kitchen_order is not None:
            kitchen_order.status = "cancelled"
        logger.info("[Kitchen] Заказ %s отменён: %s", order_id, payload["reason"])
    db.commit()


def on_event(routing_key: str, payload: dict) -> None:
    with SessionLocal() as db:
        handle(db, routing_key, payload)


if __name__ == "__main__":
    setup_logging()
    asyncio.run(consume(QUEUE, [ORDER_PAID, ORDER_CANCELLED], on_event))
