"""
Клиент Redis для кеширования (ЛР № 4).

decode_responses=True: из Redis приходят строки, а не байты — удобно для JSON.
"""
import redis

from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def check_redis_connection() -> bool:
    """Проверка соединения с Redis."""
    try:
        return redis_client.ping()
    except redis.ConnectionError:
        return False
