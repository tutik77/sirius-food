"""
Точка входа приложения: инициализация FastAPI и подключение модулей.

Схема БД создаётся и обновляется миграциями Alembic (alembic upgrade head),
а не через Base.metadata.create_all.
"""
from fastapi import FastAPI

from app.modules.users.router import router as users_router
from app.modules.menu.router import router as menu_router
from app.modules.orders.router import router as orders_router
from app.modules.delivery.router import router as delivery_router

app = FastAPI(title="Sirius.Food API")

app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(menu_router, prefix="/menu", tags=["menu"])
app.include_router(orders_router, prefix="/orders", tags=["orders"])
app.include_router(delivery_router, prefix="/delivery", tags=["delivery"])
