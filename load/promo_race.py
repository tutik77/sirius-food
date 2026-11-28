import os

from locust import HttpUser, constant, task

from app.core.jwt import create_access_token

FIRST_STUDENT_ID = int(os.environ.get("RACE_FIRST_STUDENT_ID", "1000"))
STUDENTS = int(os.environ.get("RACE_STUDENTS", "1000"))
ITEM_ID = int(os.environ.get("RACE_ITEM_ID", "1"))
PROMO_CODE = os.environ.get("RACE_PROMO_CODE", "RACE1")


class PromoHunter(HttpUser):
    wait_time = constant(1)
    student_ids = iter(range(FIRST_STUDENT_ID, FIRST_STUDENT_ID + STUDENTS))

    def on_start(self):
        student_id = next(self.student_ids, None)
        self.answered = student_id is None
        if student_id is not None:
            self.client.headers["Authorization"] = f"Bearer {create_access_token(student_id)}"

    @task
    def apply_promo(self):
        if self.answered:
            return
        with self.client.post(
            "/orders/create",
            json={"item_id": ITEM_ID, "quantity": 1, "promo_code": PROMO_CODE},
            name="/orders/create [promo]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                outcome = "applied"
            elif response.status_code == 400:
                outcome = response.json()["detail"]
            else:
                response.failure(f"HTTP {response.status_code}")
                return
            response.request_meta["name"] = f"/orders/create [promo: {outcome}]"
            response.success()
            self.answered = True
