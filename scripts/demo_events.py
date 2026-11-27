import json
import subprocess
import sys
import time

import httpx
import psycopg2

from app.core.config import settings

BASE_URL = "http://127.0.0.1:8000"
RABBIT_API = "http://127.0.0.1:15672/api"
RABBIT_AUTH = ("sirius", "sirius")
STUDENT = ("load-student@sirius.ru", "StudentPass123")
COURIER = ("courier@sirius.ru", "CourierPass123")

api = httpx.Client(base_url=BASE_URL, timeout=30)
rabbit = httpx.Client(base_url=RABBIT_API, auth=RABBIT_AUTH, timeout=10)


def login(email: str, password: str) -> dict:
    r = api.post("/auth/token", data={"username": email, "password": password})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def query(sql: str, *params):
    with psycopg2.connect(settings.DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def wait_for(condition, timeout: float = 15) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if condition():
            return True
        time.sleep(0.5)
    return False


def place_and_pay(student: dict) -> int:
    item_id = api.get("/menu/items").json()[0]["id"]
    order_id = api.post("/orders/create", json={"item_id": item_id, "quantity": 1}, headers=student).json()["order_id"]
    api.post(f"/orders/{order_id}/pay", headers=student).raise_for_status()
    return order_id


def order_status(order_id: int) -> str:
    return query("SELECT status FROM orders WHERE id = %s", order_id)[0][0]


def queue_depth(name: str) -> int:
    return rabbit.get(f"/queues/%2F/{name}").json().get("messages", 0)


def publish_raw(routing_key: str, body: str, message_id: str = "manual") -> None:
    rabbit.post("/exchanges/%2F/sirius_events/publish", json={
        "properties": {"message_id": message_id, "content_type": "application/json", "delivery_mode": 2},
        "routing_key": routing_key,
        "payload": body,
        "payload_encoding": "string",
    }).raise_for_status()


def happy_path(student: dict) -> int:
    order_id = place_and_pay(student)
    wait_for(lambda: query("SELECT 1 FROM deliveries WHERE order_id = %s", order_id))
    kitchen = query("SELECT status FROM kitchen_orders WHERE order_id = %s", order_id)
    courier = query("SELECT courier_id FROM deliveries WHERE order_id = %s", order_id)
    print(f"1) Заказ {order_id} оплачен: кухня {kitchen}, доставка — курьер {courier}")
    return order_id


def saga(student: dict) -> None:
    order_id = place_and_pay(student)
    charged = api.get("/users/me", headers=student).json()["balance"]
    wait_for(lambda: query("SELECT 1 FROM kitchen_orders WHERE order_id = %s AND status = 'cancelled'", order_id))
    refunded = api.get("/users/me", headers=student).json()["balance"]
    print(f"2) Saga: курьер занят -> delivery.failed -> заказ {order_id} {order_status(order_id)}, "
          f"кухня отменила заказ, баланс после списания {charged} -> после возврата {refunded}")


def idempotency(order_id: int) -> None:
    [(event_id, payload)] = query(
        "SELECT id, payload FROM outbox_events WHERE routing_key = 'order.paid' AND payload->>'order_id' = %s",
        str(order_id),
    )
    publish_raw("order.paid", json.dumps(payload), event_id)
    time.sleep(2)
    count = query("SELECT count(*) FROM kitchen_orders WHERE order_id = %s", order_id)[0][0]
    print(f"3) Повтор события {event_id}: записей кухни для заказа {order_id} = {count}")


def dead_letters() -> None:
    before = queue_depth("kitchen_dlq"), queue_depth("delivery_dlq")
    publish_raw("order.paid", "not-json")
    wait_for(lambda: queue_depth("kitchen_dlq") > before[0])
    after = queue_depth("kitchen_dlq"), queue_depth("delivery_dlq")
    print(f"4) Битое сообщение: kitchen_dlq {before[0]} -> {after[0]}, delivery_dlq {before[1]} -> {after[1]}")


def outbox(student: dict) -> None:
    subprocess.run(["docker", "stop", "sirius_rabbitmq"], capture_output=True, check=True)
    order_id = place_and_pay(student)
    pending = query("SELECT count(*) FROM outbox_events WHERE published_at IS NULL")[0][0]
    print(f"5) RabbitMQ остановлен, заказ {order_id} оплачен, неопубликованных событий в outbox: {pending}")
    subprocess.run(["docker", "start", "sirius_rabbitmq"], capture_output=True, check=True)
    wait_for(lambda: query("SELECT 1 FROM kitchen_orders WHERE order_id = %s", order_id), timeout=90)
    [(published_at,)] = query(
        "SELECT published_at FROM outbox_events WHERE routing_key = 'order.paid' AND payload->>'order_id' = %s",
        str(order_id),
    )
    print(f"   RabbitMQ запущен: order.paid заказа {order_id} опубликован в {published_at}, кухня получила заказ")


def free_courier(order_id: int) -> None:
    [(delivery_id,)] = query("SELECT id FROM deliveries WHERE order_id = %s", order_id)
    api.patch(f"/delivery/{delivery_id}/complete", headers=login(*COURIER)).raise_for_status()


def main() -> None:
    student = login(*STUDENT)
    order_id = happy_path(student)
    saga(student)
    idempotency(order_id)
    dead_letters()
    free_courier(order_id)
    if "--outbox" in sys.argv:
        outbox(student)


if __name__ == "__main__":
    main()
