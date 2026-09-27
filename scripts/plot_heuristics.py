from os import WCOREDUMP
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import wilcoxon

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", None)

df = pd.read_csv("results/results.csv")
dij = pd.read_csv("results/dijkstra.csv")[["movement", "n", "path_cost"]]
dij = dij.rename(columns={"path_cost": "dijkstra_cost"})

# 1. Tukey's fences, computed separately for each heuristic, movement rule and N
groups = ["heuristic", "movement", "n"]
g = df.groupby(groups)["time_ms"]
q1 = g.transform(lambda x: x.quantile(0.25))
q3 = g.transform(lambda x: x.quantile(0.75))
iqr = q3 - q1
keep = (df["time_ms"] >= q1 - 1.5 * iqr) & (df["time_ms"] <= q3 + 1.5 * iqr)
clean = df[keep]
excluded = len(df) - len(clean)
print(f"Runs: {len(df)}, excluded as outliers: {excluded}, used: {len(clean)}")
print(clean.groupby(["heuristic", "movement"]).size().rename("runs used"))

# 2. One row per heuristic, movement rule and N (nodes and cost do not vary between runs)
per_n = clean.groupby(groups).agg(time_ms=("time_ms", "mean"),
                                  nodes=("nodes_explored", "first"),
                                  cost=("path_cost", "first")).reset_index()
per_n = per_n.merge(dij, on=["movement", "n"])
per_n["optimal"] = per_n["cost"] == per_n["dijkstra_cost"]

# 3. Summary table for Section 5.1
summary = per_n.groupby(["heuristic", "movement"]).agg(
    mean_time_ms=("time_ms", "mean"),
    mean_nodes=("nodes", "mean"),
    mean_cost=("cost", "mean"),
    optimal_cases=("optimal", "sum"))
summary["time_per_node_us"] = summary["mean_time_ms"] / summary["mean_nodes"] * 1000
print(summary.round(4))
summary.round(4).to_csv("results/summary_table.csv")

# 4. Significance test, paired by N (same graph): Wilcoxon signed-rank
def compare(h1, m1, h2, m2, metric="time_ms"):
    a = per_n[(per_n.heuristic == h1) & (per_n.movement == m1)].sort_values("n")[metric]
    b = per_n[(per_n.heuristic == h2) & (per_n.movement == m2)].sort_values("n")[metric]
    stat, p = wilcoxon(a.values, b.values)
    print(f"{metric}: {h1}/{m1} vs {h2}/{m2}: W = {stat:.0f}, p = {p:.4f}")

compare("manhattan", "4dir", "euclidean", "4dir")
compare("euclidean", "8dir", "chebyshev", "8dir")
compare("manhattan", "8dir", "euclidean", "8dir")
compare("manhattan", "4dir", "manhattan", "8dir")

# 5. Charts
for metric, label, fname in [("time_ms", "Mean execution time (ms)", "results/fig_time.png"),
                             ("nodes", "Nodes explored", "results/fig_nodes.png"),
                             ("cost", "Path cost (weight units)", "results/fig_cost.png")]:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, mv in zip(axes, ["4dir", "8dir"]):
        for h in ["manhattan", "euclidean", "chebyshev"]:
            d = per_n[(per_n.heuristic == h) & (per_n.movement == mv)]
            ax.plot(d["n"], d[metric], marker="o", label=h.capitalize())
        if metric == "cost":
            d = dij[dij.movement == mv]
            ax.plot(d["n"], d["dijkstra_cost"], "k--", label="Dijkstra (optimal)")
        ax.set_title("4-directional" if mv == "4dir" else "8-directional")
        ax.set_xlabel("Number of obstacles N")
        ax.set_xticks(range(0, 21, 2))
    axes[0].set_ylabel(label)
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(fname, dpi=200)
