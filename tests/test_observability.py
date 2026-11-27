import json
import logging

from fastapi.testclient import TestClient

from app.core.correlation import HEADER, bind_correlation_id
from app.core.logging import setup_logging
from app.domain.events import OrderPaid
from app.main import app
from app.messaging.context import continue_trace
from app.messaging.outbox import to_outbox_row

client = TestClient(app)


def test_correlation_id_is_echoed():
    response = client.get("/menu/items", headers={HEADER: "demo-42"})

    assert response.headers[HEADER] == "demo-42"


def test_correlation_id_is_generated_when_missing():
    response = client.get("/menu/items")

    assert len(response.headers[HEADER]) == 36


def test_outbox_event_carries_correlation_id():
    bind_correlation_id("demo-42")

    row = to_outbox_row(OrderPaid(order_id=1, user_id=1, amount=1))

    assert row.headers[HEADER] == "demo-42"


def test_consumer_logs_contain_correlation_id_from_message(capsys):
    setup_logging("test")

    with continue_trace({HEADER: b"demo-42"}, "kitchen_queue process"):
        logging.getLogger("kitchen").info("kitchen_order_accepted")

    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["correlation_id"] == "demo-42"
    assert record["service"] == "test"


def test_metrics_endpoint_exposes_red_metrics():
    client.get("/menu/items")

    body = client.get("/metrics").text

    assert "http_requests_total" in body
    assert "http_request_duration_seconds_bucket" in body
