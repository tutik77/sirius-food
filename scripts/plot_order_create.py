import json
from pathlib import Path

import matplotlib.pyplot as plt

DIR = Path(__file__).resolve().parent.parent / "docs" / "pr5"

runs = {label: json.loads((DIR / f"{label}.json").read_text()) for label in ("before", "after")}

fig, (ax_bars, ax_line) = plt.subplots(1, 2, figsize=(12, 4))

metrics = ["avg_ms", "median_ms", "p95_ms"]
x = range(len(metrics))
ax_bars.bar([i - 0.2 for i in x], [runs["before"][m] for m in metrics], 0.4, label="До (синхронно)", color="tab:red")
ax_bars.bar([i + 0.2 for i in x], [runs["after"][m] for m in metrics], 0.4, label="После (Celery)", color="tab:green")
ax_bars.set_xticks(list(x), ["среднее", "медиана", "p95"])
ax_bars.set(title="POST /orders/create, мс", yscale="log")

for label, title, color in (("before", "До (синхронно)", "tab:red"), ("after", "После (Celery)", "tab:green")):
    ax_line.plot(range(1, len(runs[label]["times_ms"]) + 1), runs[label]["times_ms"], marker="o", label=title, color=color)
ax_line.set(title="Время каждого из 20 запросов", xlabel="запрос", ylabel="мс", yscale="log")

for ax in (ax_bars, ax_line):
    ax.grid(alpha=0.3)
    ax.legend()
fig.tight_layout()
fig.savefig(DIR / "before_after.png", dpi=110)
print(DIR / "before_after.png")
