"""
Ограничение частоты запросов (rate limiting) на Redis.

Почему Redis, а не память процесса: при нескольких репликах приложения
у каждой был бы свой счётчик, и лимит умножался бы на число реплик.
Redis хранит общий счётчик для всех.
"""
import logging

from fastapi import HTTPException, Request
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client = Redis.from_url(settings.REDIS_URL)


def rate_limit(max_requests: int = 5, window: int = 60):
    """
    Dependency: не больше max_requests запросов за window секунд
    с одного IP на один путь. При превышении — 429 Too Many Requests.
    """

    def checker(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{ip}:{request.url.path}"
        try:
            pipe = redis_client.pipeline()
            pipe.incr(key)
            # Окно ставится только при создании ключа (nx), счётчик не продлевается.
            pipe.expire(key, window, nx=True)
            current, _ = pipe.execute()
        except RedisError:
            # Если Redis недоступен, не блокируем вход полностью: пароль
            # всё равно проверяется. Сбой фиксируем в логе для мониторинга.
            logger.warning("Rate limiting отключён: Redis недоступен")
            return
        if current > max_requests:
            raise HTTPException(
                status_code=429,
                detail="Слишком много запросов, попробуйте позже",
                headers={"Retry-After": str(window)},
            )

    return checker
