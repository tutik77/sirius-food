from celery import Celery
from kombu import Exchange, Queue

from app.core.config import settings

celery_app = Celery(
    "sirius_food",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.orders", "app.tasks.stats", "app.tasks.promo"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("dlq", Exchange("dlq"), routing_key="dlq"),
    ),
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    beat_schedule={
        "update-daily-order-stats": {
            "task": "app.tasks.stats.update_daily_order_stats",
            "schedule": 60.0,
        },
        "deactivate-expired-promo-codes": {
            "task": "app.tasks.promo.deactivate_expired_promo_codes",
            "schedule": 3600.0,
        },
    },
)
