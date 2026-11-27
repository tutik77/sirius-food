from datetime import datetime, timedelta

import fakeredis
import pytest

from app.domain.entities import MenuItem, User
from app.modules.orders.service import OrderService
from app.tasks import orders as order_tasks
from app.tasks import reliability
from app.tasks.reliability import DLQ


@pytest.fixture
def service(repos):
    return OrderService(repos.orders)


@pytest.fixture
def borsch(repos):
    return repos.menu.add(MenuItem(id=None, name="Борщ", price=250))


def add_student(repos, phone):
    return repos.users.add(
        User(id=None, email=f"s{phone}@sirius.ru", phone=phone, balance=1000, password_hash="!")
    )


@pytest.fixture
def fast_tasks(monkeypatch):
    monkeypatch.setattr(reliability, "redis_client", fakeredis.FakeRedis(decode_responses=True))
    monkeypatch.setattr(order_tasks.time, "sleep", lambda seconds: None)


def test_create_order_schedules_pdf_email_and_sms(service, repos, borsch, scheduled_tasks):
    student = add_student(repos, "+79990000001")

    order = service.create_order(student.id, borsch.id, quantity=1)

    assert scheduled_tasks == [
        (order_tasks.generate_order_pdf.name, (order.id,)),
        (order_tasks.send_order_email.name, (order.id, student.email)),
        (order_tasks.send_order_sms.name, (order.id, student.phone)),
    ]


def test_no_sms_without_phone(service, repos, borsch, scheduled_tasks):
    student = add_student(repos, None)

    service.create_order(student.id, borsch.id, quantity=1)

    assert order_tasks.send_order_sms.name not in [name for name, _ in scheduled_tasks]


def test_pdf_is_generated_once(fast_tasks):
    assert order_tasks.generate_order_pdf(7) == "PDF generated for order 7"
    assert order_tasks.generate_order_pdf(7) == "PDF already generated for order 7"


def test_email_is_sent_once(fast_tasks):
    assert order_tasks.send_order_email(7, "a@sirius.ru").startswith("Email sent")
    assert order_tasks.send_order_email(7, "a@sirius.ru") == "Email already sent for order 7"


def test_email_fails_for_every_fifth_order(fast_tasks):
    with pytest.raises(ConnectionError):
        order_tasks.send_order_email.run(5, "a@sirius.ru")


def test_retry_policy_is_exponential_with_three_retries():
    task = order_tasks.send_order_email
    assert task.autoretry_for == (Exception,)
    assert task.retry_backoff is True
    assert task.max_retries == 3


def test_failed_task_goes_to_dlq(monkeypatch):
    sent = []
    task = order_tasks.send_order_email
    monkeypatch.setattr(task, "apply_async", lambda **kwargs: sent.append(kwargs))

    task.on_failure(ConnectionError("down"), "task-id", (5, "a@sirius.ru"), {}, None)

    assert sent == [{"args": (5, "a@sirius.ru"), "kwargs": {}, "queue": DLQ}]


def test_count_orders_for_day(service, repos, borsch):
    student = add_student(repos, None)
    service.create_order(student.id, borsch.id, quantity=1)
    service.create_order(student.id, borsch.id, quantity=1)
    today = datetime.utcnow().date()

    assert service.count_orders_for_day(today) == 2
    assert service.count_orders_for_day(today - timedelta(days=1)) == 0
