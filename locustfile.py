"""
Нагрузочный тест меню (ЛР № 4): «обеденный перерыв» — 500 пользователей
одновременно открывают меню.

    locust -f locustfile.py --host=http://127.0.0.1:8000
    # http://localhost:8089: 500 пользователей, spawn rate 10
"""
from locust import HttpUser, between, task


class MenuUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def get_menu(self):
        # GET /menu/items публичный (ЛР № 3), токен не нужен.
        self.client.get("/menu/items")
