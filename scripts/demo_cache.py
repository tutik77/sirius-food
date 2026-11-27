"""
Демонстрация кеша меню для защиты ЛР № 4 (сервер и Redis должны быть запущены).

    python scripts/demo_cache.py --admin-email admin@sirius.ru --admin-password AdminPass123

1. Сброс ключа menu:all, первый GET /menu/items — miss (идёт в PostgreSQL).
2. Второй GET — hit (из Redis), видно TTL ключа.
3. POST /menu/items — событийная инвалидация: ключ удалён, новое блюдо сразу в меню.
"""
import argparse
import time
import uuid

import httpx
import redis

parser = argparse.ArgumentParser()
parser.add_argument("--base-url", default="http://127.0.0.1:8000")
parser.add_argument("--redis-url", default="redis://127.0.0.1:6379")
parser.add_argument("--admin-email", default="admin@sirius.ru")
parser.add_argument("--admin-password", default="AdminPass123")
args = parser.parse_args()

cache = redis.from_url(args.redis_url, decode_responses=True)
api = httpx.Client(base_url=args.base_url, timeout=30)


def get_menu(label: str) -> list:
    start = time.perf_counter()
    items = api.get("/menu/items").json()
    ms = (time.perf_counter() - start) * 1000
    print(f"{label}: {len(items)} блюд за {ms:.1f} мс, TTL menu:all = {cache.ttl('menu:all')} с")
    return items


cache.delete("menu:all")
print("Ключ menu:all удалён")
get_menu("1) miss, чтение из PostgreSQL")
get_menu("2) hit, чтение из Redis    ")

token = api.post(
    "/auth/token", data={"username": args.admin_email, "password": args.admin_password}
).json()["access_token"]
name = f"Демо-блюдо {uuid.uuid4().hex[:6]}"
api.post("/menu/items", json={"name": name, "price": 199}, headers={"Authorization": f"Bearer {token}"})
print(f"3) POST /menu/items «{name}», ключ menu:all есть: {bool(cache.exists('menu:all'))}")
items = get_menu("4) после инвалидации       ")
print(f"   новое блюдо в меню: {any(i['name'] == name for i in items)}")
