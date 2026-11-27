import structlog
from fastapi import HTTPException, Request
from redis.exceptions import RedisError

from app.core.redis import redis_client

logger = structlog.get_logger(__name__)


def rate_limit(max_requests: int = 5, window: int = 60):
    def checker(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{ip}:{request.url.path}"
        try:
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window, nx=True)
            current, _ = pipe.execute()
        except RedisError:
            logger.warning("rate_limit_disabled_redis_unavailable")
            return
        if current > max_requests:
            raise HTTPException(
                status_code=429,
                detail="Слишком много запросов, попробуйте позже",
                headers={"Retry-After": str(window)},
            )

    return checker
