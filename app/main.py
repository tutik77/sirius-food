"""
Точка входа приложения: инициализация FastAPI и подключение модулей.

Схема БД создаётся и обновляется миграциями Alembic (alembic upgrade head),
а не через Base.metadata.create_all.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.container import warm_up_menu_cache
from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.menu.router import router as menu_router
from app.modules.orders.router import router as orders_router
from app.modules.delivery.router import router as delivery_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Прогрев кеша меню. Если Redis или БД ещё не поднялись, приложение
    # всё равно стартует: кеш заполнится при первом запросе.
    try:
        warm_up_menu_cache()
    except (RedisError, SQLAlchemyError):
        logger.warning("Прогрев кеша меню пропущен: Redis или БД недоступны")
    yield


# В продакшене (DEBUG=False) документация API не публикуется:
# Swagger и openapi.json раскрывают всю структуру API.
app = FastAPI(
    title="Sirius.Food API",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# CORS: браузерные запросы разрешены только с доменов из ALLOWED_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(menu_router, prefix="/menu", tags=["menu"])
app.include_router(orders_router, prefix="/orders", tags=["orders"])
app.include_router(delivery_router, prefix="/delivery", tags=["delivery"])
