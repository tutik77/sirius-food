import json
from pathlib import Path

import pytest
from pact import Pact, Verifier, match

from app import models
from app.domain.events import ORDER_PAID, OrderPaid
from app.workers import kitchen_consumer

PACT_DIR = Path(__file__).parent / "pacts"
PACT_FILE = PACT_DIR / "kitchen-orders.json"
MESSAGE = "an order.paid event"


def kitchen_handles(body, metadata, db) -> None:
    payload = json.loads(body)
    kitchen_consumer.handle(db, ORDER_PAID, payload)
    assert db.query(models.KitchenOrder).filter_by(order_id=payload["order_id"]).count() == 1


@pytest.fixture
def pact_file(sqlite_session) -> Path:
    pact = Pact("kitchen", "orders").with_specification("V4")
    pact.upon_receiving(MESSAGE, "Async").with_body(
        {"event_id": match.uuid(), "order_id": match.int(42)},
        content_type="application/json",
    )
    pact.verify(lambda body, metadata: kitchen_handles(body, metadata, sqlite_session), "Async")
    pact.write_file(PACT_DIR, overwrite=True)
    return PACT_FILE


def produce(payload: dict) -> dict:
    return {"contents": json.dumps(payload).encode(), "content_type": "application/json", "metadata": None}


def verify_provider(pact_file: Path, payload: dict) -> None:
    Verifier("orders").message_handler({MESSAGE: lambda *args, **kwargs: produce(payload)}).add_source(pact_file).verify()


def test_orders_produce_order_paid_matching_kitchen_contract(pact_file):
    verify_provider(pact_file, OrderPaid(order_id=7, user_id=3, amount=250).payload())


def test_renamed_field_breaks_contract(pact_file):
    payload = OrderPaid(order_id=7, user_id=3, amount=250).payload()
    payload["id"] = payload.pop("order_id")

    with pytest.raises(RuntimeError, match="Failed to execute verifier"):
        verify_provider(pact_file, payload)
