import os

from locust import HttpUser, constant, task
from locust.exception import StopUser

from app.core.jwt import create_access_token

FIRST_STUDENT_ID = int(os.environ.get("RACE_FIRST_STUDENT_ID", "1000"))
STUDENTS = int(os.environ.get("RACE_STUDENTS", "1000"))
ITEM_ID = int(os.environ.get("RACE_ITEM_ID", "1"))
PROMO_CODE = os.environ.get("RACE_PROMO_CODE", "RACE1")


class PromoHunter(HttpUser):
    wait_time = constant(0)
    student_ids = iter(range(FIRST_STUDENT_ID, FIRST_STUDENT_ID + STUDENTS))

    def on_start(self):
        student_id = next(self.student_ids, None)
        if student_id is None:
            raise StopUser()
        self.client.headers["Authorization"] = f"Bearer {create_access_token(student_id)}"

    @task
    def apply_promo(self):
        with self.client.post(
            "/orders/create",
            json={"item_id": ITEM_ID, "quantity": 1, "promo_code": PROMO_CODE},
            name="/orders/create [promo]",
            catch_response=True,
        ) as response:
            outcome = "applied" if response.status_code == 200 else response.json().get("detail", response.status_code)
            response.request_meta["name"] = f"/orders/create [promo: {outcome}]"
            response.success() if response.status_code in (200, 400) else response.failure(outcome)
        raise StopUser()
