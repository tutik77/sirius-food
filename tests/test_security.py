from datetime import UTC, datetime, timedelta

import fakeredis
import pytest
from fastapi.testclient import TestClient
from jose import jwt

import app.container as container
import app.core.rate_limit as rate_limit_module
from app.core.config import settings
from app.core.jwt import create_access_token, create_refresh_token
from app.core.security import hash_password
from app.domain.entities import Delivery, DeliveryStatus, MenuItem, Order, OrderStatus, Role, User
from app.main import app
from app.memory_storage import InMemoryStorage

PASSWORD = "StrongPass123"


@pytest.fixture
def storage(monkeypatch):
    storage = InMemoryStorage()
    monkeypatch.setattr(container, "memory_storage", storage)
    return storage


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    monkeypatch.setattr(rate_limit_module, "redis_client", fakeredis.FakeRedis())


@pytest.fixture
def client(storage):
    return TestClient(app)


@pytest.fixture
def make_user(storage):
    counter = iter(range(1, 1000))

    def factory(role=Role.STUDENT, balance=0.0, is_blocked=False, email=None) -> User:
        user_id = storage.next_id("users")
        user = User(
            id=user_id,
            email=email or f"{role}{next(counter)}@sirius.ru",
            balance=balance,
            is_blocked=is_blocked,
            password_hash=hash_password(PASSWORD),
            role=role,
        )
        storage.users[user_id] = user
        return user

    return factory


@pytest.fixture
def borsch(storage):
    item = MenuItem(id=storage.next_id("menu_items"), name="Борщ", price=250)
    storage.menu_items[item.id] = item
    return item


def auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def place_order(client, user, item, quantity=1) -> int:
    r = client.post("/orders/create", json={"item_id": item.id, "quantity": quantity}, headers=auth(user))
    assert r.status_code == 200, r.text
    return r.json()["order_id"]


@pytest.mark.parametrize(
    "method, url",
    [
        ("POST", "/orders/create"),
        ("GET", "/orders/my"),
        ("GET", "/users/me"),
        ("POST", "/users/1/topup?amount=10"),
        ("POST", "/menu/items"),
        ("GET", "/delivery/1"),
    ],
)
def test_without_token_returns_401(client, method, url):
    r = client.request(method, url, json={})

    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_tokens_return_401(client, make_user):
    user = make_user()
    now = datetime.now(UTC)
    expired = jwt.encode(
        {"sub": str(user.id), "type": "access", "exp": now - timedelta(minutes=1)},
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    forged = jwt.encode(
        {"sub": str(user.id), "type": "access", "exp": now + timedelta(minutes=5)},
        "attacker-does-not-know-the-real-secret-key",
        algorithm="HS256",
    )
    refresh_as_access = create_refresh_token(user.id)

    for token in ("garbage", expired, forged, refresh_as_access):
        r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, token


def test_blocked_user_token_returns_403(client, make_user):
    blocked = make_user(is_blocked=True)

    assert client.get("/users/me", headers=auth(blocked)).status_code == 403


def test_order_is_created_for_token_owner_not_payload_user(client, storage, make_user, borsch):
    attacker = make_user(balance=1000)
    victim = make_user(balance=1000)

    r = client.post(
        "/orders/create",
        json={"user_id": victim.id, "item_id": borsch.id, "quantity": 1},
        headers=auth(attacker),
    )

    assert r.status_code == 200
    order = storage.orders[r.json()["order_id"]]
    assert order.user_id == attacker.id
    assert storage.users[victim.id].balance == 1000
    assert storage.users[attacker.id].balance == 750


@pytest.mark.parametrize(
    "method, url, body, allowed, denied",
    [
        ("GET", "/orders/kitchen/orders", None, Role.COOK, Role.STUDENT),
        ("POST", "/menu/items", {"name": "Плов", "price": 300}, Role.COOK, Role.STUDENT),
        ("PATCH", "/menu/items/1", {"price": 270}, Role.ADMIN, Role.COURIER),
        ("POST", "/orders/create", {"item_id": 1, "quantity": 1}, Role.STUDENT, Role.COOK),
        ("PATCH", "/users/1/role", {"role": "cook"}, Role.ADMIN, Role.STUDENT),
        ("GET", "/delivery/my", None, Role.COURIER, Role.STUDENT),
    ],
)
def test_role_based_access(client, make_user, borsch, method, url, body, allowed, denied):
    denied_user = make_user(role=denied, balance=1000)
    allowed_user = make_user(role=allowed, balance=1000)

    r_denied = client.request(method, url, json=body, headers=auth(denied_user))
    r_allowed = client.request(method, url, json=body, headers=auth(allowed_user))

    assert r_denied.status_code == 403
    assert r_denied.json() == {"detail": "Доступ запрещён"}
    assert r_allowed.status_code == 200, r_allowed.text


def test_student_cannot_cancel_foreign_order(client, storage, make_user, borsch):
    owner = make_user(balance=1000)
    attacker = make_user()
    order_id = place_order(client, owner, borsch)

    r = client.post(f"/orders/{order_id}/cancel", headers=auth(attacker))

    assert r.status_code == 403
    assert storage.orders[order_id].status == OrderStatus.PROCESSING


def test_owner_can_cancel_own_order(client, storage, make_user, borsch):
    owner = make_user(balance=1000)
    order_id = place_order(client, owner, borsch)

    r = client.post(f"/orders/{order_id}/cancel", headers=auth(owner))

    assert r.status_code == 200
    assert storage.users[owner.id].balance == 1000


def test_student_cannot_top_up_foreign_balance(client, make_user):
    victim, attacker = make_user(), make_user()

    r = client.post(f"/users/{victim.id}/topup", params={"amount": 100}, headers=auth(attacker))

    assert r.status_code == 403


def test_my_orders_returns_only_own_orders(client, make_user, borsch):
    anna, boris = make_user(balance=1000), make_user(balance=1000)
    mine = place_order(client, anna, borsch)
    place_order(client, boris, borsch)

    r = client.get("/orders/my", headers=auth(anna))

    assert [o["id"] for o in r.json()] == [mine]


def test_delivery_access_is_checked_per_object(client, storage, make_user, borsch):
    owner = make_user(balance=1000)
    courier = make_user(role=Role.COURIER)
    other_courier = make_user(role=Role.COURIER)
    stranger = make_user()
    order = Order(id=storage.next_id("orders"), user_id=owner.id, item_id=borsch.id, quantity=1,
                  status=OrderStatus.PAID, total_cost=250)
    storage.orders[order.id] = order
    delivery = Delivery(id=storage.next_id("deliveries"), order_id=order.id, courier_id=courier.id,
                        status=DeliveryStatus.IN_PROGRESS)
    storage.deliveries[delivery.id] = delivery

    assert client.get(f"/delivery/{delivery.id}", headers=auth(stranger)).status_code == 403
    assert client.get(f"/delivery/{delivery.id}", headers=auth(owner)).status_code == 200
    assert client.patch(f"/delivery/{delivery.id}/complete", headers=auth(other_courier)).status_code == 403
    assert client.patch(f"/delivery/{delivery.id}/complete", headers=auth(courier)).status_code == 200
    assert storage.orders[order.id].status == OrderStatus.DELIVERED


def test_register_login_and_me(client):
    r = client.post("/users/register", json={"email": "anna@sirius.ru", "password": PASSWORD})
    assert r.json() == {"status": "success", "user_id": 1, "email": "anna@sirius.ru"}

    r = client.post("/auth/token", data={"username": "anna@sirius.ru", "password": PASSWORD})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.json() == {"id": 1, "email": "anna@sirius.ru", "balance": 0.0, "role": "student"}


def test_registration_cannot_choose_role(client, storage):
    client.post("/users/register", json={"email": "evil@sirius.ru", "password": PASSWORD, "role": "admin"})

    assert storage.users[1].role == Role.STUDENT


def test_register_requires_strong_enough_password(client):
    r = client.post("/users/register", json={"email": "anna@sirius.ru", "password": "123"})

    assert r.status_code == 422


def test_login_does_not_reveal_whether_email_exists(client, make_user):
    make_user(email="anna@sirius.ru")

    wrong_password = client.post("/auth/login", json={"email": "anna@sirius.ru", "password": "wrong-pass"})
    unknown_email = client.post("/auth/login", json={"email": "nobody@sirius.ru", "password": PASSWORD})

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_refresh_rotation_and_reuse_detection(client, make_user):
    make_user(email="anna@sirius.ru")
    first = client.post("/auth/login", json={"email": "anna@sirius.ru", "password": PASSWORD}).json()

    second = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert second.status_code == 200
    second = second.json()

    reused = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert reused.status_code == 401

    after_reset = client.post("/auth/refresh", json={"refresh_token": second["refresh_token"]})
    assert after_reset.status_code == 401


def test_logout_revokes_refresh_token(client, make_user):
    make_user(email="anna@sirius.ru")
    tokens = client.post("/auth/login", json={"email": "anna@sirius.ru", "password": PASSWORD}).json()

    assert client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_blocked_user_cannot_login(client, make_user):
    make_user(email="blocked@sirius.ru", is_blocked=True)

    r = client.post("/auth/login", json={"email": "blocked@sirius.ru", "password": PASSWORD})

    assert r.status_code == 403


def test_login_rate_limit(client, make_user):
    make_user(email="anna@sirius.ru")
    statuses = [
        client.post("/auth/login", json={"email": "anna@sirius.ru", "password": "wrong-pass"}).status_code
        for _ in range(6)
    ]

    assert statuses == [401] * 5 + [429]


def test_rate_limit_blocks_even_correct_password(client, make_user):
    make_user(email="anna@sirius.ru")
    for _ in range(5):
        client.post("/auth/login", json={"email": "anna@sirius.ru", "password": "wrong-pass"})

    r = client.post("/auth/login", json={"email": "anna@sirius.ru", "password": PASSWORD})

    assert r.status_code == 429
    assert r.headers["Retry-After"] == "60"


def test_swagger_and_openapi_disabled_in_production(client):
    assert settings.DEBUG is False
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_cors_allows_only_configured_origin(client):
    preflight = {"Access-Control-Request-Method": "POST"}

    allowed = client.options("/auth/login", headers={"Origin": "https://sirius-food.ru", **preflight})
    denied = client.options("/auth/login", headers={"Origin": "https://evil.example", **preflight})

    assert allowed.headers.get("access-control-allow-origin") == "https://sirius-food.ru"
    assert "access-control-allow-origin" not in denied.headers
