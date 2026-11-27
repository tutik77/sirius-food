import asyncio
import logging

from sqlalchemy.orm import Session

from app.core.logging import setup_logging
from app.database import SessionLocal
from app.messaging.outbox import OutboxRepository
from app.messaging.rabbitmq import connect, declare_exchange, publish

logger = logging.getLogger("outbox_relay")

POLL_SECONDS = 1


async def publish_pending(db: Session, exchange) -> int:
    outbox = OutboxRepository(db)
    rows = outbox.fetch_unpublished()
    for row in rows:
        await publish(exchange, row.routing_key, row.payload)
        outbox.mark_published(row)
        db.commit()
        logger.info("Опубликовано %s %s", row.routing_key, row.id)
    return len(rows)


async def run() -> None:
    while True:
        try:
            connection = await connect()
            async with connection:
                exchange = await declare_exchange(await connection.channel())
                while True:
                    with SessionLocal() as db:
                        await publish_pending(db, exchange)
                    await asyncio.sleep(POLL_SECONDS)
        except Exception as e:
            logger.warning("RabbitMQ недоступен (%r), события ждут в outbox", e)
            await asyncio.sleep(POLL_SECONDS * 5)


if __name__ == "__main__":
    setup_logging()
    asyncio.run(run())
