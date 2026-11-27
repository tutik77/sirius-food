import json
import statistics
import subprocess
import sys
import threading
from pathlib import Path

import psycopg2

USERS, SPAWN_RATE, RUN_TIME = 500, 10, "90s"
OUT = Path(__file__).resolve().parent.parent / "docs" / "pr4"
DSN = "postgresql://sirius:sirius@127.0.0.1:5432/sirius_food"


def db_counters() -> tuple[int, int]:
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT xact_commit + xact_rollback, tup_returned "
            "FROM pg_stat_database WHERE datname = current_database()"
        )
        return cur.fetchone()


def sample_db_cpu(samples: list[float], stop: threading.Event) -> None:
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
            sys.executable, "-m", "locust", "-f", "load/menu_peak.py", "--headless",
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
