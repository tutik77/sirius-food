import asyncio

import structlog
from opentelemetry.trace import SpanKind
from sqlalchemy.orm import Session

from app.core.logging import setup_logging
from app.core.tracing import setup_tracing
from app.database import SessionLocal
from app.messaging.context import continue_trace, outgoing_headers
from app.messaging.outbox import OutboxRepository
from app.messaging.rabbitmq import connect, declare_exchange, publish

logger = structlog.get_logger("outbox_relay")

POLL_SECONDS = 1


async def publish_pending(db: Session, exchange) -> int:
    outbox = OutboxRepository(db)
    rows = outbox.fetch_unpublished()
    for row in rows:
        with continue_trace(row.headers, f"publish {row.routing_key}", SpanKind.PRODUCER):
            await publish(exchange, row.routing_key, row.payload, outgoing_headers())
            outbox.mark_published(row)
            db.commit()
            logger.info("event_published", routing_key=row.routing_key, event_id=row.id)
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
            logger.warning("rabbitmq_unavailable", error=repr(e))
            await asyncio.sleep(POLL_SECONDS * 5)


if __name__ == "__main__":
    setup_logging("outbox_relay")
    setup_tracing("outbox_relay")
    asyncio.run(run())
