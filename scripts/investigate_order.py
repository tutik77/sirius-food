import json
import subprocess
import sys
import time

import httpx

BASE_URL = "http://127.0.0.1:8000"
STUDENT = ("load-student@sirius.ru", "StudentPass123")
CONTAINERS = ["sirius_app", "sirius_outbox_relay", "sirius_kitchen", "sirius_delivery_worker"]


def place_and_pay(correlation_id: str) -> int:
    api = httpx.Client(base_url=BASE_URL, timeout=30, headers={"X-Correlation-ID": correlation_id})
    token = api.post("/auth/token", data={"username": STUDENT[0], "password": STUDENT[1]}).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    item_id = api.get("/menu/items").json()[0]["id"]
    order = api.post("/orders/create", json={"item_id": item_id, "quantity": 1}, headers=auth)
    order_id = order.json()["order_id"]
    paid = api.post(f"/orders/{order_id}/pay", headers=auth)
    print(f"Заказ {order_id}: create -> {order.headers['X-Correlation-ID']}, pay -> {paid.headers['X-Correlation-ID']}")
    return order_id


def logs_with(container: str, correlation_id: str) -> list[dict]:
    output = subprocess.run(["docker", "logs", container], capture_output=True, text=True, encoding="utf-8").stdout
    records = []
    for line in output.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("correlation_id") == correlation_id:
            records.append(record)
    return records


def main(correlation_id: str) -> None:
    place_and_pay(correlation_id)
    time.sleep(3)
    for container in CONTAINERS:
        print(f"\n{container}:")
        for record in logs_with(container, correlation_id):
            fields = {k: v for k, v in record.items() if k not in ("timestamp", "logger", "level", "correlation_id")}
            print(f"  {record['timestamp']} {fields}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "demo-42")
