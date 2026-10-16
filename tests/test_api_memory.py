"""
API целиком на in-memory репозиториях (STORAGE_BACKEND=memory).

Показывает, что реализацию хранилища можно заменить, не трогая
ни service.py, ни router.py: роутеры отвечают так же, как на PostgreSQL.
"""
import pytest
from fastapi.testclient import TestClient

import app.container as container
from app.main import app
from app.memory_storage import InMemoryStorage


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(container, "memory_storage", InMemoryStorage())
    return TestClient(app)


def test_full_order_flow(client):
    r = client.post("/users/register", json={"email": "anna@sirius.ru", "phone": "89990000001"})
    assert r.status_code == 200
    assert r.json() == {"status": "success", "user_id": 1, "email": "anna@sirius.ru"}

    r = client.post("/users/1/topup", params={"amount": 1000})
    assert r.json() == {"status": "success", "new_balance": 1000.0}

    r = client.post("/menu/items", json={"name": "Борщ", "price": 250})
    assert r.json() == {"status": "success", "item_id": 1}

    r = client.post("/orders/create", json={"user_id": 1, "item_id": 1, "quantity": 2})
    assert r.json() == {"status": "success", "order_id": 1}

    r = client.post("/users/1/topup", params={"amount": 1})
    assert r.json()["new_balance"] == 501.0


@pytest.mark.parametrize(
    "method, url, kwargs, status, detail",
    [
        ("POST", "/users/999/topup", {"params": {"amount": 10}}, 404, "Пользователь не найден"),
        ("POST", "/orders/create", {"json": {"user_id": 1, "item_id": 1, "quantity": 0}}, 400,
         "Количество должно быть больше нуля"),
        ("PATCH", "/menu/items/999", {"json": {"price": 10}}, 404, "Блюдо не найдено"),
        ("POST", "/menu/items", {"json": {"name": "Компот", "price": 0}}, 400, "Цена должна быть положительной"),
        ("PATCH", "/delivery/999/complete", {}, 404, "Доставка не найдена"),
    ],
)
def test_domain_errors_are_translated_to_http(client, method, url, kwargs, status, detail):
    r = client.request(method, url, **kwargs)

    assert r.status_code == status
    assert r.json() == {"detail": detail}
