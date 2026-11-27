import json
import statistics
import sys
import time
from pathlib import Path

import httpx

N = 20
BASE_URL = "http://127.0.0.1:8000"
ADMIN = ("admin@sirius.ru", "AdminPass123")
STUDENT = ("load-student@sirius.ru", "StudentPass123", "+79990000000")
OUT = Path(__file__).resolve().parent.parent / "docs" / "pr5"


def token(api: httpx.Client, email: str, password: str) -> dict:
    r = api.post("/auth/token", data={"username": email, "password": password})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def prepare_student(api: httpx.Client) -> dict:
    api.post("/users/register", json={"email": STUDENT[0], "password": STUDENT[1], "phone": STUDENT[2]})
    student = token(api, STUDENT[0], STUDENT[1])
    student_id = api.get("/users/me", headers=student).json()["id"]
    api.post(f"/users/{student_id}/topup", params={"amount": 50_000}, headers=token(api, *ADMIN)).raise_for_status()
    return student


def measure(label: str) -> None:
    api = httpx.Client(base_url=BASE_URL, timeout=60)
    student = prepare_student(api)
    order = {"item_id": api.get("/menu/items").json()[0]["id"], "quantity": 1}
    api.post("/orders/create", json=order, headers=student).raise_for_status()

    times = []
    for _ in range(N):
        start = time.perf_counter()
        api.post("/orders/create", json=order, headers=student).raise_for_status()
        times.append(round((time.perf_counter() - start) * 1000, 1))

    result = {
        "requests": N,
        "avg_ms": round(statistics.mean(times), 1),
        "median_ms": round(statistics.median(times), 1),
        "p95_ms": sorted(times)[int(N * 0.95) - 1],
        "max_ms": max(times),
        "times_ms": times,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{label}.json").write_text(json.dumps(result, indent=2))
    print({k: v for k, v in result.items() if k != "times_ms"})


if __name__ == "__main__":
    measure(sys.argv[1])
