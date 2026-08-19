#!/usr/bin/env python3
"""
plot_runtime_summary.py

Builds the two root-level runtime summary artifacts from results/results.csv:

  1. runtime_summary_table.csv / .png -- per-heuristic mean/std runtime,
     computed after excluding outliers (values outside 1.5 * IQR of that
     heuristic's pooled run times -- a standard Tukey fence, applied per
     heuristic across all N and all runs).
  2. runtime_scatter.png -- runtime vs. N (obstacle count), one jittered
     point per run, colored by heuristic, with a best-fit line per
     heuristic. Points above the highest upper Tukey fence across the three
     heuristics are clipped from the plot (annotated with a count) so a few
     extreme runs don't wreck the y-axis scale.

Usage:
    python3 scripts/plot_runtime_summary.py
"""
import csv
from collections import defaultdict
from statistics import mean, pstdev

import matplotlib.pyplot as plt
import numpy as np

INPUT = "results/results.csv"
TABLE_CSV = "runtime_summary_table.csv"
TABLE_PNG = "runtime_summary_table.png"
SCATTER_PNG = "runtime_scatter.png"

COLORS = {
    "manhattan": ("#a6c8f0", "#2a5db0"),   # (point, best-fit line)
    "euclidean": ("#f5c39a", "#d9762f"),
    "chebyshev": ("#a8dfc4", "#2f9e63"),
}
LABELS = {"manhattan": "Manhattan", "euclidean": "Euclidean", "chebyshev": "Chebyshev"}
ORDER = ["manhattan", "euclidean", "chebyshev"]


def load(path):
    by_algo = defaultdict(list)       # algorithm -> [time_ms, ...]
    by_algo_n = defaultdict(list)     # algorithm -> [(n, time_ms), ...]
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            algo = row["algorithm"]
            t = float(row["time_ms"])
            by_algo[algo].append(t)
            by_algo_n[algo].append((int(row["n"]), t))
    return by_algo, by_algo_n


def tukey_bounds(values):
    q1, q3 = np.percentile(values, [25, 75])
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def build_summary_table(by_algo):
    rows = []
    for algo in ORDER:
        values = by_algo[algo]
        lo, hi = tukey_bounds(values)
        kept = [v for v in values if lo <= v <= hi]
        excluded = len(values) - len(kept)
        rows.append({
            "Heuristic": LABELS[algo],
            "Mean Runtime (ms)": round(mean(kept), 4),
            "Std Dev (ms)": round(pstdev(kept), 4),
            "Runs Used": len(kept),
            "Outliers Excluded": excluded,
        })
    return rows


def write_table_csv(rows, path):
    fieldnames = ["Heuristic", "Mean Runtime (ms)", "Std Dev (ms)", "Runs Used", "Outliers Excluded"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {path}")


def render_table_png(rows, path):
    fieldnames = ["Heuristic", "Mean Runtime (ms)", "Std Dev (ms)", "Runs Used", "Outliers Excluded"]
    table_data = [fieldnames] + [[str(r[c]) for c in fieldnames] for r in rows]

    fig, ax = plt.subplots(figsize=(11, 0.7 * (len(rows) + 1) + 0.4))
    ax.axis("off")
    table = ax.table(cellText=table_data, cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 2.0)
    table.auto_set_column_width(col=list(range(len(fieldnames))))

    for col in range(len(fieldnames)):
        cell = table[0, col]
        cell.set_facecolor("#2b2b2b")
        cell.set_text_props(color="white", weight="bold")

    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print(f"Wrote {path}")


def render_scatter(by_algo, by_algo_n, path):
    all_upper = [tukey_bounds(by_algo[a])[1] for a in ORDER]
    y_cap = max(all_upper)

    fig, ax = plt.subplots(figsize=(11, 8))
    rng = np.random.default_rng(0)

    hidden_count = 0
    for algo in ORDER:
        point_color, line_color = COLORS[algo]
        pts = by_algo_n[algo]
        ns = np.array([n for n, _ in pts], dtype=float)
        ts = np.array([t for _, t in pts])

        visible = ts <= y_cap
        hidden_count += int((~visible).sum())

        jitter = rng.uniform(-0.15, 0.15, size=len(ns))
        ax.scatter(ns[visible] + jitter[visible], ts[visible], s=28, alpha=0.55,
                   color=point_color, edgecolors=line_color, linewidths=0.4,
                   label=f"{LABELS[algo]} (runs)")

        coeffs = np.polyfit(ns, ts, 1)
        xs = np.linspace(ns.min(), ns.max(), 100)
        ax.plot(xs, np.polyval(coeffs, xs), color=line_color, linewidth=2.2,
                label=f"{LABELS[algo]} (best fit)")

    ax.set_xlabel("Number of obstacles (N)", fontsize=13)
    ax.set_ylabel("Runtime (ms)", fontsize=13)
    ax.set_title("Runtime vs. Obstacle Density", fontsize=16, fontweight="bold")
    ax.set_ylim(0, y_cap * 1.02)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10, loc="upper right")

    if hidden_count:
        ax.text(0.01, 0.03,
                f"{hidden_count} point(s) above {y_cap:.3f} ms not shown\n"
                f"(beyond 1.5x IQR -- likely OS scheduling noise, not algorithmic)",
                transform=ax.transAxes, fontsize=10, color="#555555")

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Wrote {path}")


def main():
    by_algo, by_algo_n = load(INPUT)
    rows = build_summary_table(by_algo)
    write_table_csv(rows, TABLE_CSV)
    render_table_png(rows, TABLE_PNG)
    render_scatter(by_algo, by_algo_n, SCATTER_PNG)


if __name__ == "__main__":
    main()
