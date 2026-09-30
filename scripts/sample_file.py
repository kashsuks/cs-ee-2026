# 1. Tukey's fences, computed separately for each heuristic, movement rule and N
from os import wait


groups = ["heuristic", "movement", "n"]
g = df.groupby(groups)["time_ms"]
q1 = g.transform(lambda x: x.quantile(0.25))
q3 = g.transform(lambda x: x.quantile(0.75))
iqr = q3 - q1
keep = (df["time_ms"] >= q1 - 1.5 * iqr) & (df["time_ms"] <= q3 + 1.5 * iqr)
clean = df[keep]

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
