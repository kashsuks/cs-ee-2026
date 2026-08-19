#!/usr/bin/env python3
"""Export per-heuristic CSVs: Trial 1-20 time_ms + Average + nodes_explored + path_cost."""
import csv
from collections import defaultdict

INPUT = "results/results.csv"
NUM_TRIALS = 20

groups = defaultdict(dict)  # (n, algorithm) -> {run: time_ms}
meta = {}  # (n, algorithm) -> (nodes_explored, path_cost)
with open(INPUT, newline="") as f:
    for row in csv.DictReader(f):
        n = int(row["n"])
        run = int(row["run"])
        key = (n, row["algorithm"])
        if run <= NUM_TRIALS:
            groups[key][run] = float(row["time_ms"])
        meta[key] = (row["nodes_explored"], row["path_cost"])

ns_by_heuristic = defaultdict(set)
for (n, algorithm) in groups:
    ns_by_heuristic[algorithm].add(n)

fieldnames = ["n"] + [f"trial_{i}_time_ms" for i in range(1, NUM_TRIALS + 1)] + \
             ["average_time_ms", "nodes_explored", "path_cost"]

for algorithm, ns in ns_by_heuristic.items():
    out_path = f"results/{algorithm}_trials.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for n in sorted(ns):
            key = (n, algorithm)
            times = groups[key]
            trial_vals = [f"{times[i]:.5f}" for i in range(1, NUM_TRIALS + 1)]
            avg = sum(times[i] for i in range(1, NUM_TRIALS + 1)) / NUM_TRIALS
            nodes_explored, path_cost = meta[key]
            writer.writerow([n] + trial_vals + [f"{avg:.5f}", nodes_explored, path_cost])
    print(f"Wrote {out_path}")
