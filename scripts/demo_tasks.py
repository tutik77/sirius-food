import time

import httpx
import redis

from app.tasks.orders import generate_order_pdf

BASE_URL = "http://127.0.0.1:8000"
STUDENT = ("load-student@sirius.ru", "StudentPass123")

api = httpx.Client(base_url=BASE_URL, timeout=30)
cache = redis.Redis(host="127.0.0.1", decode_responses=True)


def login() -> dict:
    r = api.post("/auth/token", data={"username": STUDENT[0], "password": STUDENT[1]})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def create_order(headers: dict, item_id: int) -> tuple[int, float]:
    start = time.perf_counter()
    r = api.post("/orders/create", json={"item_id": item_id, "quantity": 1}, headers=headers)
    r.raise_for_status()
    return r.json()["order_id"], (time.perf_counter() - start) * 1000


def main() -> None:
    headers = login()
    item_id = api.get("/menu/items").json()[0]["id"]

    order_id, ms = create_order(headers, item_id)
    print(f"1) Заказ {order_id} создан за {ms:.0f} мс, PDF/email/SMS ушли в очередь")

    time.sleep(3)
    generate_order_pdf.delay(order_id)
    print(f"2) Повторно поставлен generate_order_pdf({order_id}): в логе воркера — 'PDF already generated'")

    dlq_before = cache.llen("dlq")
    while order_id % 5:
        order_id, _ = create_order(headers, item_id)
    print(f"3) Заказ {order_id} кратен 5: send_order_email падает, ретраи через 1, 2, 4 с, затем DLQ")
    while cache.llen("dlq") == dlq_before:
        time.sleep(1)
    print(f"   DLQ: {dlq_before} -> {cache.llen('dlq')} (redis-cli lrange dlq 0 -1)")

    print(f"4) Статистика Celery Beat: {cache.hgetall('stats:orders:daily')}")


if __name__ == "__main__":
    main()
