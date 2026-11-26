"""
Замер нагрузки на GET /menu/items для ЛР № 4 (до и после кеша).

Запускает Locust без UI (500 пользователей, spawn rate 10) и параллельно
снимает нагрузку на PostgreSQL: сколько транзакций он выполнил за прогон
и загрузку CPU контейнера db. Сервер приложения должен быть запущен.

    python scripts/measure_menu_load.py before
    python scripts/measure_menu_load.py after

Результаты: docs/pr4/<label>_stats.csv, <label>_stats_history.csv,
<label>.html (отчёт Locust с графиками) и <label>_db.json.
"""
import json
import statistics
import subprocess
import sys
import threading
from pathlib import Path

import psycopg2

USERS, SPAWN_RATE, RUN_TIME = 500, 10, "90s"
OUT = Path(__file__).resolve().parent.parent / "docs" / "pr4"
DSN = "postgresql://sirius:sirius@localhost:5432/sirius_food"


def db_counters() -> tuple[int, int]:
    """Число завершённых транзакций и прочитанных строк в БД sirius_food."""
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT xact_commit + xact_rollback, tup_returned "
            "FROM pg_stat_database WHERE datname = current_database()"
        )
        return cur.fetchone()


def sample_db_cpu(samples: list[float], stop: threading.Event) -> None:
    """Загрузка CPU контейнера с PostgreSQL (docker stats), % от одного ядра."""
    while not stop.is_set():
        out = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{.CPUPerc}}", "sirius_food-db-1"],
            capture_output=True, text=True,
        ).stdout.strip().rstrip("%")
        if out:
            samples.append(float(out))


def main(label: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tx_before, rows_before = db_counters()

    cpu: list[float] = []
    stop = threading.Event()
    sampler = threading.Thread(target=sample_db_cpu, args=(cpu, stop))
    sampler.start()
    subprocess.run(
        [
            sys.executable, "-m", "locust", "-f", "locustfile.py", "--headless",
            "--host", "http://127.0.0.1:8000",
            "-u", str(USERS), "-r", str(SPAWN_RATE), "--run-time", RUN_TIME,
            "--csv", str(OUT / label), "--csv-full-history", "--html", str(OUT / f"{label}.html"),
            "--only-summary",
        ],
        check=False,
    )
    stop.set()
    sampler.join()

    tx_after, rows_after = db_counters()
    db = {
        "db_transactions": tx_after - tx_before,
        "db_rows_returned": rows_after - rows_before,
        "db_cpu_avg_percent": round(statistics.mean(cpu), 1) if cpu else None,
        "db_cpu_max_percent": max(cpu) if cpu else None,
    }
    (OUT / f"{label}_db.json").write_text(json.dumps(db, indent=2))
    print(json.dumps(db, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
