"""
Снимает «слепок» поведения API: прогоняет фиксированный сценарий запросов
по всем модулям и печатает JSON со статусами и телами ответов.

Нужен, чтобы доказать, что рефакторинг не изменил внешнее поведение:
слепок до рефакторинга и после должен совпадать.

Запуск (БД из docker-compose должна быть поднята, данные в ней будут удалены):
    python scripts/api_contract.py docs/contract.json   # сохранить слепок
    python scripts/api_contract.py --check              # сравнить с docs/contract_mvp.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import Base, engine
from app.main import app

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)
log = []


def call(method, url, **kwargs):
    r = client.request(method, url, **kwargs)
    log.append({"request": f"{method} {url}", "status": r.status_code, "body": r.json()})


def sql(statement):
    with engine.begin() as conn:
        conn.execute(text(statement))


# users
call("POST", "/users/register", json={"email": "anna@sirius.ru", "phone": "89990000001"})
call("POST", "/users/register", json={"email": "anna@sirius.ru"})
call("POST", "/users/register", json={"email": "short@sirius.ru", "phone": "123"})
call("POST", "/users/register", json={"email": "courier@sirius.ru"})
call("POST", "/users/register", json={"email": "blocked@sirius.ru"})
call("POST", "/users/1/topup", params={"amount": 1000})
call("POST", "/users/1/topup", params={"amount": -5})
call("POST", "/users/1/topup", params={"amount": 60000})
call("POST", "/users/999/topup", params={"amount": 100})
sql("UPDATE users SET is_blocked = true WHERE email = 'blocked@sirius.ru'")
call("POST", "/users/3/topup", params={"amount": 100})

# menu
call("POST", "/menu/items", json={"name": "Борщ", "price": 250})
call("POST", "/menu/items", json={"name": "Компот", "price": 0})
call("POST", "/menu/items", json={"name": "Я", "price": 10})
call("POST", "/menu/items", json={"name": "Борщ", "price": 300})
call("POST", "/menu/items", json={"name": "Стейк", "price": 900})
call("PATCH", "/menu/items/2", json={"is_available": False})
call("PATCH", "/menu/items/1", json={"price": -1})
call("PATCH", "/menu/items/999", json={"price": 100})
call("PATCH", "/menu/items/1", json={"name": "Борщ украинский", "price": 270})

# orders
call("POST", "/orders/create", json={"user_id": 1, "item_id": 1, "quantity": 2})
call("POST", "/orders/create", json={"user_id": 1, "item_id": 1, "quantity": 0})
call("POST", "/orders/create", json={"user_id": 999, "item_id": 1, "quantity": 1})
call("POST", "/orders/create", json={"user_id": 1, "item_id": 999, "quantity": 1})
call("POST", "/orders/create", json={"user_id": 1, "item_id": 2, "quantity": 1})
call("POST", "/orders/create", json={"user_id": 1, "item_id": 1, "quantity": 10})
call("POST", "/users/1/topup", params={"amount": 1})

# delivery
call("POST", "/delivery/assign", json={"order_id": 1, "courier_id": 2})
sql("UPDATE orders SET status = 'paid' WHERE id = 1")
call("POST", "/delivery/assign", json={"order_id": 999, "courier_id": 2})
call("POST", "/delivery/assign", json={"order_id": 1, "courier_id": 999})
call("POST", "/delivery/assign", json={"order_id": 1, "courier_id": 3})
call("POST", "/delivery/assign", json={"order_id": 1, "courier_id": 2})
call("POST", "/delivery/assign", json={"order_id": 1, "courier_id": 2})
call("PATCH", "/delivery/1/complete")
call("PATCH", "/delivery/1/complete")
call("PATCH", "/delivery/999/complete")
sql("INSERT INTO deliveries (order_id, courier_id, status) VALUES (1, 2, 'cancelled')")
call("PATCH", "/delivery/2/complete")

with engine.connect() as conn:
    state = {
        "user_1_balance": conn.execute(text("SELECT balance FROM users WHERE id = 1")).scalar(),
        "order_1_status": conn.execute(text("SELECT status FROM orders WHERE id = 1")).scalar(),
    }

snapshot = {"responses": log, "db_state": state}
result = json.dumps(snapshot, ensure_ascii=False, indent=2)
if sys.argv[1:] == ["--check"]:
    reference_path = Path(__file__).resolve().parent.parent / "docs" / "contract_mvp.json"
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    diff = [(a, b) for a, b in zip(reference["responses"], log) if a != b]
    if reference["db_state"] != state:
        diff.append((reference["db_state"], state))
    if len(reference["responses"]) != len(log):
        diff.append(("количество запросов", len(reference["responses"]), len(log)))
    for item in diff:
        print("РАСХОЖДЕНИЕ:", item)
    print(f"Проверено запросов: {len(log)}. " + ("Ответы идентичны MVP." if not diff else "Есть расхождения!"))
    sys.exit(1 if diff else 0)
elif len(sys.argv) > 1:
    Path(sys.argv[1]).write_text(result + "\n", encoding="utf-8")
else:
    print(result)
