import httpx
import psycopg2

from app.core.config import settings
from app.domain.entities import Role, User
from app.modules.delivery.grpc_client import DeliveryGrpcClient

BASE_URL = "http://127.0.0.1:8000"
ADMIN = ("admin@sirius.ru", "AdminPass123")
STUDENT = ("load-student@sirius.ru", "StudentPass123")
COURIER = ("courier@sirius.ru", "CourierPass123")

api = httpx.Client(base_url=BASE_URL, timeout=30)


def login(email: str, password: str) -> dict:
    r = api.post("/auth/token", data={"username": email, "password": password})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def prepare_courier(admin: dict) -> User:
    api.post("/users/register", json={"email": COURIER[0], "password": COURIER[1]})
    courier = api.get("/users/me", headers=login(*COURIER)).json()
    api.patch(f"/users/{courier['id']}/role", json={"role": Role.COURIER}, headers=admin).raise_for_status()
    return User(id=courier["id"], email=COURIER[0], role=Role.COURIER)


def create_paid_order(student: dict) -> int:
    item_id = api.get("/menu/items").json()[0]["id"]
    order_id = api.post("/orders/create", json={"item_id": item_id, "quantity": 1}, headers=student).json()["order_id"]
    with psycopg2.connect(settings.DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute("UPDATE orders SET status = 'paid' WHERE id = %s", (order_id,))
    return order_id


def main() -> None:
    admin = login(*ADMIN)
    courier = prepare_courier(admin)
    order_id = create_paid_order(login(*STUDENT))

    r = api.post("/delivery/assign", json={"order_id": order_id, "courier_id": courier.id}, headers=admin)
    delivery_id = r.json()["delivery_id"]
    print(f"1) HTTP POST /delivery/assign -> монолит -> gRPC AssignCourier: доставка {delivery_id}")

    courier_headers = login(*COURIER)
    print(f"2) HTTP GET /delivery/{delivery_id}: {api.get(f'/delivery/{delivery_id}', headers=courier_headers).json()}")

    grpc_client = DeliveryGrpcClient(settings.DELIVERY_GRPC_ADDR)
    print("3) Server Streaming TrackDelivery:")
    for status in grpc_client.track_delivery(delivery_id, courier):
        print(f"   статус: {status}")

    print("4) Bidirectional Streaming ChatWithCourier:")
    questions = ["Где мой заказ?", "Жду у входа"]
    for question, answer in zip(questions, grpc_client.chat_with_courier(delivery_id, iter(questions))):
        print(f"   клиент: {question}\n   курьер: {answer}")

    r = api.patch(f"/delivery/{delivery_id}/complete", headers=courier_headers)
    print(f"5) HTTP PATCH /delivery/{delivery_id}/complete: {r.status_code} {r.json()}")


if __name__ == "__main__":
    main()
