import asyncio
import json
import logging
from collections.abc import Callable, Iterable

import aio_pika
from aio_pika import DeliveryMode, ExchangeType

from app.core.config import settings

logger = logging.getLogger(__name__)

EXCHANGE = "sirius_events"
DLX = "dlx_exchange"

EventHandler = Callable[[str, dict], None]


def dlq_name(queue: str) -> str:
    return queue.removesuffix("_queue") + "_dlq"


async def connect() -> aio_pika.abc.AbstractRobustConnection:
    return await aio_pika.connect_robust(settings.RABBITMQ_URL)


async def declare_exchange(channel: aio_pika.abc.AbstractChannel) -> aio_pika.abc.AbstractExchange:
    return await channel.declare_exchange(EXCHANGE, ExchangeType.TOPIC, durable=True)


async def declare_queue(
    channel: aio_pika.abc.AbstractChannel, queue_name: str, routing_keys: Iterable[str]
) -> aio_pika.abc.AbstractQueue:
    dlx = await channel.declare_exchange(DLX, ExchangeType.DIRECT, durable=True)
    dlq = await channel.declare_queue(dlq_name(queue_name), durable=True)
    await dlq.bind(dlx, routing_key=queue_name)

    queue = await channel.declare_queue(
        queue_name,
        durable=True,
        arguments={"x-dead-letter-exchange": DLX, "x-dead-letter-routing-key": queue_name},
    )
    exchange = await declare_exchange(channel)
    for routing_key in routing_keys:
        await queue.bind(exchange, routing_key=routing_key)
    return queue


async def publish(exchange: aio_pika.abc.AbstractExchange, routing_key: str, payload: dict) -> None:
    message = aio_pika.Message(
        body=json.dumps(payload, ensure_ascii=False).encode(),
        content_type="application/json",
        message_id=payload["event_id"],
        delivery_mode=DeliveryMode.PERSISTENT,
    )
    await exchange.publish(message, routing_key=routing_key)


async def consume(queue_name: str, routing_keys: Iterable[str], handler: EventHandler) -> None:
    connection = await connect()
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    queue = await declare_queue(channel, queue_name, routing_keys)

    async def on_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            try:
                handler(message.routing_key, json.loads(message.body))
            except Exception:
                logger.exception("Сообщение %s отправлено в %s", message.message_id, dlq_name(queue_name))
                raise

    await queue.consume(on_message)
    logger.info("%s ждёт событий %s", queue_name, ", ".join(routing_keys))
    await asyncio.Future()
