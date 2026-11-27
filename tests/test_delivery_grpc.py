import pytest
from fastapi.testclient import TestClient

from app import container
from app.core.config import settings
from app.core.jwt import create_access_token
from app.domain.entities import Delivery, DeliveryStatus, Order, OrderStatus, Role, User
from app.domain.errors import ForbiddenError, NotFoundError, ServiceUnavailableError
from app.main import app
from app.memory_storage import InMemoryStorage
from app.modules.delivery.grpc_client import DeliveryGrpcClient
from delivery_service import server as delivery_server


@pytest.fixture
def storage(monkeypatch):
    storage = InMemoryStorage()
    monkeypatch.setattr(container, "memory_storage", storage)
    return storage


@pytest.fixture
def client(delivery_grpc_server):
    return DeliveryGrpcClient(delivery_grpc_server)


def add_user(storage, role) -> User:
    user = User(id=storage.next_id("users"), email=f"{role}@sirius.ru", role=role)
    storage.users[user.id] = user
    return user


@pytest.fixture
def paid_order(storage):
    student = add_user(storage, Role.STUDENT)
    order = Order(id=storage.next_id("orders"), user_id=student.id, item_id=1, quantity=1, status=OrderStatus.PAID)
    storage.orders[order.id] = order
    return order


def test_assign_and_complete_over_grpc(client, storage, paid_order):
    courier = add_user(storage, Role.COURIER)

    delivery = client.assign_courier(paid_order.id, courier.id)
    assert delivery.status == DeliveryStatus.IN_PROGRESS
    assert client.list_courier_deliveries(courier) == [delivery]

    completed = client.complete_delivery(delivery.id, courier)
    assert completed.status == DeliveryStatus.COMPLETED
    assert storage.orders[paid_order.id].status == OrderStatus.DELIVERED


def test_domain_errors_cross_the_network(client, storage, paid_order):
    courier = add_user(storage, Role.COURIER)
    stranger = add_user(storage, Role.STUDENT)
    delivery = client.assign_courier(paid_order.id, courier.id)

    with pytest.raises(NotFoundError):
        client.get_delivery(999, courier)
    with pytest.raises(ForbiddenError):
        client.get_delivery(delivery.id, stranger)


def test_unavailable_service_raises_service_unavailable():
    client = DeliveryGrpcClient("127.0.0.1:1")

    with pytest.raises(ServiceUnavailableError):
        client.list_courier_deliveries(User(id=1, email=""))


def test_track_delivery_streams_statuses(client, storage, monkeypatch):
    monkeypatch.setattr(delivery_server, "TRACK_STEP_SECONDS", 0)
    courier = add_user(storage, Role.COURIER)
    delivery = Delivery(id=storage.next_id("deliveries"), order_id=1, courier_id=courier.id)
    storage.deliveries[delivery.id] = delivery

    assert list(client.track_delivery(delivery.id, courier)) == ["in_progress", "on_the_way", "delivered"]


def test_chat_with_courier_answers_every_message(client):
    replies = list(client.chat_with_courier(1, iter(["Где заказ?", "Жду у входа"])))

    assert len(replies) == 2
    assert "Где заказ?" in replies[0]


def test_http_returns_503_when_delivery_service_is_down(storage, monkeypatch):
    courier = add_user(storage, Role.COURIER)
    monkeypatch.setattr(settings, "DELIVERY_GRPC_ADDR", "127.0.0.1:1")
    headers = {"Authorization": f"Bearer {create_access_token(courier.id)}"}

    response = TestClient(app).get("/delivery/my", headers=headers)

    assert response.status_code == 503
