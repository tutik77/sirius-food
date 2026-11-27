from datetime import UTC, datetime

from app.core.celery_app import celery_app
from app.core.redis import redis_client
from app.database import SessionLocal
from app.modules.orders.repository import SqlAlchemyOrderRepository
from app.modules.orders.service import OrderService

DAILY_STATS_KEY = "stats:orders:daily"


@celery_app.task
def update_daily_order_stats() -> int:
    today = datetime.now(UTC).date()
    with SessionLocal() as db:
        count = OrderService(SqlAlchemyOrderRepository(db)).count_orders_for_day(today)
    redis_client.hset(DAILY_STATS_KEY, today.isoformat(), count)
    return count
