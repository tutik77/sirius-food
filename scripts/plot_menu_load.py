import csv
from pathlib import Path

import matplotlib.pyplot as plt

DIR = Path(__file__).resolve().parent.parent / "docs" / "pr4"


def history(label: str) -> tuple[list[int], list[float], list[float]]:
    with open(DIR / f"{label}_stats_history.csv", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r and r["Name"] == "Aggregated"]
    t0 = int(rows[0]["Timestamp"])
    t = [int(r["Timestamp"]) - t0 for r in rows]
    rps = [float(r["Requests/s"]) for r in rows]
    p95 = [float(r["95%"]) if r["95%"] != "N/A" else 0.0 for r in rows]
    return t, rps, p95


fig, (ax_rps, ax_p95) = plt.subplots(1, 2, figsize=(12, 4))
for label, title, color in (("before", "До (без кеша)", "tab:red"), ("after", "После (Redis)", "tab:green")):
    t, rps, p95 = history(label)
    ax_rps.plot(t, rps, label=title, color=color)
    ax_p95.plot(t, [v / 1000 for v in p95], label=title, color=color)

ax_rps.set(title="RPS, GET /menu/items (500 пользователей)", xlabel="секунды", ylabel="запросов/с")
ax_p95.set(title="95-й перцентиль времени ответа", xlabel="секунды", ylabel="секунды")
for ax in (ax_rps, ax_p95):
    ax.grid(alpha=0.3)
    ax.legend()
fig.tight_layout()
fig.savefig(DIR / "before_after.png", dpi=110)
print(DIR / "before_after.png")
