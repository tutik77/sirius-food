import os
import random

from locust import HttpUser, between, task

from app.core.jwt import create_access_token

STUDENT_IDS = [int(i) for i in os.environ.get("LOAD_STUDENT_IDS", "6").split(",")]


class SiriusUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        token = create_access_token(random.choice(STUDENT_IDS))
        self.client.headers["Authorization"] = f"Bearer {token}"
        self.item_ids = [item["id"] for item in self.client.get("/menu/items").json()]

    @task(7)
    def get_menu(self):
        self.client.get("/menu/items")

    @task(2)
    def get_menu_item(self):
        self.client.get(f"/menu/items/{random.choice(self.item_ids)}", name="/menu/items/{id}")

    @task(1)
    def create_order(self):
        self.client.post("/orders/create", json={"item_id": random.choice(self.item_ids), "quantity": 1})
