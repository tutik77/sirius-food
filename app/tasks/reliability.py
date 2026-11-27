import logging

from celery import Task

from app.core.redis import redis_client

logger = logging.getLogger(__name__)

DLQ = "dlq"
IDEMPOTENCY_TTL = 3600


class ReliableTask(Task):
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = False
    max_retries = 3

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("Задача %s[%s] исчерпала ретраи и отправлена в DLQ: %s", self.name, task_id, exc)
        self.apply_async(args=args, kwargs=kwargs, queue=DLQ)


def already_done(key: str) -> bool:
    return bool(redis_client.exists(key))


def mark_done(key: str) -> None:
    redis_client.set(key, "1", ex=IDEMPOTENCY_TTL)
