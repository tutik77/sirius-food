from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.container import warm_up_menu_cache
from app.core.config import settings
from app.core.correlation import HEADER, correlation_id_middleware
from app.core.logging import setup_logging
from app.core.sentry import setup_sentry
from app.core.tracing import setup_tracing
from app.modules.assistant.router import router as assistant_router
from app.modules.auth.router import router as auth_router
from app.modules.delivery.router import router as delivery_router
from app.modules.loyalty.router import router as loyalty_router
from app.modules.menu.router import router as menu_router
from app.modules.orders.router import router as orders_router
from app.modules.promo.router import router as promo_router
from app.modules.users.router import router as users_router

setup_logging("api")
setup_tracing("api")
setup_sentry("api")

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        warm_up_menu_cache()
    except (RedisError, SQLAlchemyError):
        logger.warning("menu_cache_warm_up_skipped")
    yield


app = FastAPI(
    title="Sirius.Food API",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

app.middleware("http")(correlation_id_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type", HEADER],
    expose_headers=[HEADER],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(menu_router, prefix="/menu", tags=["menu"])
app.include_router(orders_router, prefix="/orders", tags=["orders"])
app.include_router(delivery_router, prefix="/delivery", tags=["delivery"])
app.include_router(promo_router, prefix="/promo-codes", tags=["promo"])
app.include_router(loyalty_router, prefix="/loyalty", tags=["loyalty"])
app.include_router(assistant_router, prefix="/assistant", tags=["assistant"])

Instrumentator().instrument(app).expose(app, include_in_schema=False)
FastAPIInstrumentor.instrument_app(app)

if settings.DEBUG:

    @app.get("/debug/error", include_in_schema=False)
    def debug_error():
        raise RuntimeError("Проверка Sentry: необработанная ошибка")
