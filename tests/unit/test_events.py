import asyncio

import pytest

from app import models
from app.domain.entities import MenuItem, OrderStatus, Role, User
from app.domain.events import DELIVERY_FAILED, ORDER_CANCELLED, ORDER_PAID, DeliveryFailed, OrderCancelled, OrderPaid
from app.memory_storage import InMemoryStorage
from app.modules.orders.exceptions import AccessDeniedError, OrderCannotBePaidError
from app.modules.orders.repository import InMemoryOrderRepository, SqlAlchemyOrderRepository
from app.modules.orders.service import OrderService
from app.workers import kitchen_consumer, order_saga_consumer
from app.workers.outbox_relay import publish_pending
from delivery_service import worker as delivery_worker


@pytest.fixture
def storage():
    return InMemoryStorage()


@pytest.fixture
def memory_service(storage):
    return OrderService(InMemoryOrderRepository(storage))


def place_order(storage, service, balance=1000, price=250) -> tuple[User, int]:
    user = User(id=storage.next_id("users"), email="s@sirius.ru", balance=balance)
    storage.users[user.id] = user
    item = MenuItem(id=storage.next_id("menu_items"), name="Борщ", price=price)
    storage.menu_items[item.id] = item
    return user, service.create_order(user.id, item.id, quantity=1).id


def test_pay_order_writes_order_paid_to_outbox(storage, memory_service):
    student, order_id = place_order(storage, memory_service)

    order = memory_service.pay_order(order_id, student)

    assert order.status == OrderStatus.PAID
    [event] = storage.outbox
    assert isinstance(event, OrderPaid)
    assert (event.order_id, event.user_id, event.amount) == (order_id, student.id, 250)


def test_pay_order_rules(storage, memory_service):
    student, order_id = place_order(storage, memory_service)
    stranger = User(id=999, email="x@sirius.ru")

    with pytest.raises(AccessDeniedError):
        memory_service.pay_order(order_id, stranger)
    memory_service.pay_order(order_id, student)
    with pytest.raises(OrderCannotBePaidError):
        memory_service.pay_order(order_id, student)


def test_compensation_refunds_once(storage, memory_service):
    student, order_id = place_order(storage, memory_service)
    memory_service.pay_order(order_id, student)

    assert memory_service.compensate_failed_delivery(order_id, "Нет свободного курьера") is not None
    assert memory_service.compensate_failed_delivery(order_id, "Нет свободного курьера") is None

    assert storage.orders[order_id].status == OrderStatus.CANCELLED
    assert storage.users[student.id].balance == 1000
    assert isinstance(storage.outbox[-1], OrderCancelled)


def add_user(db, role: str, balance: float = 0) -> models.User:
    role_row = db.query(models.Role).filter_by(name=role).one()
    user = models.User(email=f"{role}{db.query(models.User).count()}@sirius.ru", balance=balance,
                       password_hash="!", role=role_row)
    db.add(user)
    db.commit()
    return user


def add_paid_order(db, user: models.User, total: float = 250) -> models.Order:
    item = models.MenuItem(name=f"Блюдо {db.query(models.MenuItem).count()}", price=total)
    db.add(item)
    db.flush()
    order = models.Order(user_id=user.id, item_id=item.id, quantity=1, status=OrderStatus.PAID, total_cost=total)
    db.add(order)
    db.commit()
    return order


def outbox(db) -> list[models.OutboxEvent]:
    return db.query(models.OutboxEvent).all()


def test_kitchen_accepts_paid_order_once(sqlite_session):
    order = add_paid_order(sqlite_session, add_user(sqlite_session, Role.STUDENT))
    event = OrderPaid(order_id=order.id, user_id=order.user_id, amount=250).payload()

    kitchen_consumer.handle(sqlite_session, ORDER_PAID, event)
    kitchen_consumer.handle(sqlite_session, ORDER_PAID, event)

    assert sqlite_session.query(models.KitchenOrder).filter_by(order_id=order.id).count() == 1


def test_kitchen_cancels_order(sqlite_session):
    order = add_paid_order(sqlite_session, add_user(sqlite_session, Role.STUDENT))
    kitchen_consumer.handle(sqlite_session, ORDER_PAID, OrderPaid(order_id=order.id, user_id=1, amount=1).payload())

    kitchen_consumer.handle(
        sqlite_session, ORDER_CANCELLED, OrderCancelled(order_id=order.id, refund=1, reason="тест").payload()
    )

    assert sqlite_session.query(models.KitchenOrder).filter_by(order_id=order.id).one().status == "cancelled"


def test_delivery_worker_assigns_free_courier(sqlite_session):
    courier = add_user(sqlite_session, Role.COURIER)
    order = add_paid_order(sqlite_session, add_user(sqlite_session, Role.STUDENT))

    delivery_worker.handle(sqlite_session, ORDER_PAID, OrderPaid(order_id=order.id, user_id=1, amount=1).payload())

    delivery = sqlite_session.query(models.Delivery).filter_by(order_id=order.id).one()
    assert delivery.courier_id == courier.id
    assert outbox(sqlite_session) == []


def test_delivery_worker_publishes_failure_without_couriers(sqlite_session):
    order = add_paid_order(sqlite_session, add_user(sqlite_session, Role.STUDENT))
    event = OrderPaid(order_id=order.id, user_id=1, amount=1).payload()

    delivery_worker.handle(sqlite_session, ORDER_PAID, event)
    delivery_worker.handle(sqlite_session, ORDER_PAID, event)

    [row] = outbox(sqlite_session)
    assert row.routing_key == DELIVERY_FAILED
    assert row.payload["order_id"] == order.id


def test_saga_cancels_order_and_refunds_once(sqlite_session):
    student = add_user(sqlite_session, Role.STUDENT, balance=750)
    order = add_paid_order(sqlite_session, student)
    failed = DeliveryFailed(order_id=order.id, reason="Нет свободного курьера").payload()

    order_saga_consumer.handle(sqlite_session, DELIVERY_FAILED, failed)
    order_saga_consumer.handle(sqlite_session, DELIVERY_FAILED, failed)
    order_saga_consumer.handle(
        sqlite_session, DELIVERY_FAILED, DeliveryFailed(order_id=order.id, reason="повтор").payload()
    )

    sqlite_session.refresh(student)
    sqlite_session.refresh(order)
    assert order.status == OrderStatus.CANCELLED
    assert student.balance == 1000
    assert [row.routing_key for row in outbox(sqlite_session)] == [ORDER_CANCELLED]


class FakeExchange:
    def __init__(self):
        self.published = []

    async def publish(self, message, routing_key):
        self.published.append((routing_key, message.message_id))


def test_outbox_relay_publishes_and_marks_events(sqlite_session):
    event = OrderPaid(order_id=1, user_id=1, amount=1)
    sqlite_session.add(models.OutboxEvent(id=event.event_id, routing_key=event.routing_key, payload=event.payload()))
    sqlite_session.commit()
    exchange = FakeExchange()

    assert asyncio.run(publish_pending(sqlite_session, exchange)) == 1
    assert asyncio.run(publish_pending(sqlite_session, exchange)) == 0

    assert exchange.published == [(ORDER_PAID, event.event_id)]
    assert outbox(sqlite_session)[0].published_at is not None
