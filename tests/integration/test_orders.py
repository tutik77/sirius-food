from app import models
from tests.integration.conftest import auth


def test_create_order_saves_to_db(client, db, make_user, make_item):
    student = make_user(balance=1000)
    item = make_item(price=150)

    response = client.post("/orders/create", json={"item_id": item.id, "quantity": 2}, headers=auth(student))

    assert response.status_code == 200
    order = db.get(models.Order, response.json()["order_id"])
    assert (order.user_id, order.quantity, order.total_cost, order.status) == (student.id, 2, 300, "processing")
    db.refresh(student)
    assert student.balance == 700


def test_insufficient_funds_does_not_create_order(client, db, make_user, make_item):
    student = make_user(balance=100)
    item = make_item(price=150)

    response = client.post("/orders/create", json={"item_id": item.id, "quantity": 1}, headers=auth(student))

    assert response.status_code == 400
    assert db.query(models.Order).count() == 0


def test_pay_order_writes_outbox_event_in_same_transaction(client, db, make_user, make_item):
    student = make_user(balance=1000)
    item = make_item()
    order_id = client.post("/orders/create", json={"item_id": item.id, "quantity": 1}, headers=auth(student)).json()[
        "order_id"
    ]

    response = client.post(f"/orders/{order_id}/pay", headers=auth(student))

    assert response.status_code == 200
    assert db.get(models.Order, order_id).status == "paid"
    [event] = db.query(models.OutboxEvent).all()
    assert (event.routing_key, event.payload["order_id"], event.published_at) == ("order.paid", order_id, None)


def test_menu_item_is_read_from_postgres(client, make_item):
    item = make_item(name="Борщ", price=250)

    assert client.get(f"/menu/items/{item.id}").json()["name"] == "Борщ"
    assert client.get("/menu/items/999").status_code == 404
