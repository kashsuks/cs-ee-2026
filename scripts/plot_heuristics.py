#!/usr/bin/env python3
"""
Usage:
    python3 scripts/plot_heuristics.py
    python3 scripts/plot_heuristics.py -o figures/heuristics.pdf
"""

import argparse
import csv
from collections import defaultdict
from statistics import mean, pstdev

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

COLORS = {
    "manhattan": "#2a78d6",
    "euclidean": "#eb6834",
    "chebyshev": "#1baf7a",
}
LABELS = {
    "manhattan": "Manhattan",
    "euclidean": "Euclidean",
    "chebyshev": "Chebyshev",
}
ORDER = ["manhattan", "euclidean", "chebyshev"]


def load_results(path):
    # (algorithm, n) -> {"nodes": int, "cost": int, "times": [float, ...]}
    data = defaultdict(lambda: {"nodes": None, "cost": None, "times": []})
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            key = (row["algorithm"], int(row["n"]))
            entry = data[key]
            entry["nodes"] = int(row["nodes_explored"])
            entry["cost"] = int(row["path_cost"])
            entry["times"].append(float(row["time_ms"]))
    return data


def series_for(data, algorithm, field):
    ns = sorted(n for (alg, n) in data if alg == algorithm)
    if field == "time_mean_std":
        means = [mean(data[(algorithm, n)]["times"]) for n in ns]
        stds = [pstdev(data[(algorithm, n)]["times"]) for n in ns]
        return ns, means, stds
    values = [data[(algorithm, n)][field] for n in ns]
    return ns, values


def style_axis(ax, xlabel, ylabel, title):
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.grid(True, which="major", linewidth=0.6, alpha=0.35)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(2))
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#888888")
    ax.tick_params(colors="#333333", labelsize=9.5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-i", "--input", default="results/results.csv",
        help="path to results.csv (default: results/results.csv)",
    )
    parser.add_argument(
        "-o", "--output", default="results/heuristics_comparison.png",
        help="output image path (default: results/heuristics_comparison.png)",
    )
    args = parser.parse_args()

    data = load_results(args.input)

    plt.rcParams.update({
        "font.family": "serif",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })

    fig, (ax_nodes, ax_time) = plt.subplots(1, 2, figsize=(11, 4.5))

    for algo in ORDER:
        ns, nodes = series_for(data, algo, "nodes")
        ax_nodes.plot(
            ns, nodes,
            label=LABELS[algo], color=COLORS[algo],
            linewidth=2, marker="o", markersize=4.5,
        )
    style_axis(
        ax_nodes,
        xlabel="Number of obstacles (N)",
        ylabel="Nodes expanded",
        title="(a) Search Efficiency",
    )

    for algo in ORDER:
        ns, means, stds = series_for(data, algo, "time_mean_std")
        lo = [m - s for m, s in zip(means, stds)]
        hi = [m + s for m, s in zip(means, stds)]
        ax_time.plot(
            ns, means,
            label=LABELS[algo], color=COLORS[algo],
            linewidth=2, marker="o", markersize=4.5,
        )
        ax_time.fill_between(ns, lo, hi, color=COLORS[algo], alpha=0.15, linewidth=0)
    style_axis(
        ax_time,
        xlabel="Number of obstacles (N)",
        ylabel="Runtime (ms)",
        title="(b) Runtime (mean ± 1 std, 20 runs)",
    )

    handles, labels = ax_nodes.get_legend_handles_labels()
    fig.legend(
        handles, labels, loc="lower center", ncol=3,
        frameon=False, bbox_to_anchor=(0.5, -0.02), fontsize=10.5,
    )

    fig.suptitle(
        "A* Heuristic Comparison on 10×10 Weighted Grids",
        fontsize=13.5, fontweight="bold", y=1.02,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(args.output, dpi=300, bbox_inches="tight")
    print(f"Saved figure to {args.output}")


if __name__ == "__main__":
    main()
