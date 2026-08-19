#!/usr/bin/env python3
"""Reduce results.csv into per-heuristic CSVs, 5 representative trials per N."""
import csv
from collections import defaultdict

INPUT = "results/results.csv"
OUTPUT_TEMPLATE = "results/results_{heuristic}_5trials.csv"

# 5 evenly-spaced ranks out of 20 sorted-by-time_ms runs: min, ~25th pct, median, ~75th pct, max
RANKS = [0, 5, 10, 14, 19]
LABELS = ["lowest", "low-mid", "median", "high-mid", "highest"]

groups = defaultdict(list)
with open(INPUT, newline="") as f:
    for row in csv.DictReader(f):
        row["n"] = int(row["n"])
        row["time_ms"] = float(row["time_ms"])
        groups[(row["n"], row["algorithm"])].append(row)

by_heuristic = defaultdict(list)
for (n, algorithm), rows in groups.items():
    rows.sort(key=lambda r: r["time_ms"])
    for rank, label in zip(RANKS, LABELS):
        r = rows[rank]
        by_heuristic[algorithm].append({
            "n": n,
            "trial": label,
            "time_ms": r["time_ms"],
            "nodes_explored": r["nodes_explored"],
            "path_cost": r["path_cost"],
        })

fieldnames = ["n", "trial", "time_ms", "nodes_explored", "path_cost"]
for algorithm, out_rows in by_heuristic.items():
    out_rows.sort(key=lambda r: (r["n"], RANKS[LABELS.index(r["trial"])]))
    path = OUTPUT_TEMPLATE.format(heuristic=algorithm)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"Wrote {len(out_rows)} rows to {path}")
