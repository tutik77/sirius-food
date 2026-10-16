"""
Демонстрация сценариев проверки из раздела 5 ЛР № 3 на запущенном сервере.

Подготовка:
    docker compose up -d db redis
    alembic upgrade head
    python -m app.cli create-user admin@sirius.ru AdminPass123 --role admin
    uvicorn app.main:app

Запуск:
    python scripts/demo_security.py [--base-url http://127.0.0.1:8000]
"""
import argparse
import uuid

import httpx

PASSWORD = "StrongPass123"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--admin-email", default="admin@sirius.ru")
    parser.add_argument("--admin-password", default="AdminPass123")
    args = parser.parse_args()

    api = httpx.Client(base_url=args.base_url)
    run = uuid.uuid4().hex[:6]

    def show(title: str, response: httpx.Response) -> None:
        print(f"{title}\n    -> {response.status_code} {response.text}\n")

    def login(email: str, password: str = PASSWORD) -> dict:
        # Подготовительные входы идут через /auth/token: лимит считается на пару
        # «IP + путь», и сценарий 5 на /auth/login начнётся с чистого счётчика.
        r = api.post("/auth/token", data={"username": email, "password": password})
        r.raise_for_status()
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    # Подготовка данных: два студента и блюдо.
    admin = login(args.admin_email, args.admin_password)
    anna, boris = f"anna_{run}@sirius.ru", f"boris_{run}@sirius.ru"
    anna_id = api.post("/users/register", json={"email": anna, "password": PASSWORD}).json()["user_id"]
    api.post("/users/register", json={"email": boris, "password": PASSWORD})
    item_id = api.post("/menu/items", json={"name": f"Борщ {run}", "price": 250}, headers=admin).json()["item_id"]
    anna_auth, boris_auth = login(anna), login(boris)
    api.post(f"/users/{anna_id}/topup", params={"amount": 1000}, headers=anna_auth)

    show("Сценарий 1. POST /orders/create без токена",
         api.post("/orders/create", json={"item_id": item_id, "quantity": 1}))

    r = api.post("/orders/create", json={"item_id": item_id, "quantity": 2}, headers=anna_auth)
    show("Сценарий 2. Студент Анна создаёт заказ", r)
    order_id = r.json()["order_id"]

    show(f"Сценарий 3. Студент Борис отменяет заказ Анны #{order_id}",
         api.post(f"/orders/{order_id}/cancel", headers=boris_auth))

    show("Сценарий 4. Студент открывает GET /orders/kitchen/orders",
         api.get("/orders/kitchen/orders", headers=anna_auth))

    print("Сценарий 5. 6 попыток входа с неверным паролем")
    for attempt in range(1, 7):
        r = api.post("/auth/login", json={"email": boris, "password": "wrong-password"})
        print(f"    попытка {attempt}: {r.status_code} {r.text}")


if __name__ == "__main__":
    main()
