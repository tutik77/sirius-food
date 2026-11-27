import uuid
from contextvars import ContextVar

import sentry_sdk
import structlog
from fastapi import Request

HEADER = "X-Correlation-ID"

correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def bind_correlation_id(value: str | None) -> str:
    value = value or str(uuid.uuid4())
    correlation_id.set(value)
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(correlation_id=value)
    sentry_sdk.set_tag("correlation_id", value)
    return value


async def correlation_id_middleware(request: Request, call_next):
    value = bind_correlation_id(request.headers.get(HEADER))
    request.state.correlation_id = value
    response = await call_next(request)
    response.headers[HEADER] = value
    return response
