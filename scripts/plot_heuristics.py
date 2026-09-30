from os import WCOREDUMP
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
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
#
# Styled per Jiro Doke / matplotlib "great plots" conventions: a fixed
# categorical palette instead of default colors, the box reduced to just
# the axes a reader needs (Tufte data-ink ratio), and series labelled
# directly at the line's end (colour-matched, bold text) instead of a
# legend box the reader has to glance back and forth to.

# Categorical palette, slots 1-3 of the validated default (see
# references/palette.md in the dataviz skill): worst all-pairs CVD deltaE
# 9.2, worst normal-vision deltaE 24.0 on a light surface.
COLORS = {"manhattan": "#2a78d6", "euclidean": "#eb6834", "chebyshev": "#1baf7a"}

# On the cost chart, every heuristic lands on the exact same path cost as
# Dijkstra at every N (0 admissibility violations in this dataset) -- the
# lines are not merely close, they are numerically identical, so no axis
# transform (log included) can pull them apart. Distinct, phase-offset
# dash patterns let all four colors show through instead of the
# last-drawn line hiding the rest, without fabricating a data difference
# that doesn't exist.
COST_LINESTYLES = {
    "manhattan": (0, (8, 4)),
    "euclidean": (4, (8, 4)),   # same period as manhattan, offset half a cycle
    "chebyshev": (0, (2, 2)),   # finer dash, threads through both above
}
BASELINE_LINESTYLE_COST = (0, (1, 2))

BASELINE_COLOR = "#c3c2b7"   # palette "Baseline / axis" token
INK_PRIMARY = "#0b0b0b"      # palette "Primary ink"
INK_MUTED = "#898781"        # palette "Muted (axis/labels)"
SURFACE = "#ffffff"          # chart background (pure white)
MOVEMENT_TITLES = {"4dir": "4-Directional", "8dir": "8-Directional"}

SIZE_DEFAULT = 13
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = SIZE_DEFAULT
plt.rcParams["axes.titlesize"] = SIZE_DEFAULT + 1
plt.rcParams["axes.labelsize"] = SIZE_DEFAULT
plt.rcParams["xtick.labelsize"] = SIZE_DEFAULT - 1
plt.rcParams["ytick.labelsize"] = SIZE_DEFAULT - 1
plt.rcParams["text.color"] = INK_PRIMARY
plt.rcParams["axes.labelcolor"] = INK_PRIMARY


def compute_end_label_positions(y_lo, y_hi, entries, min_gap_frac=0.05):
    """Stack colliding end-labels apart within a *fixed* (y_lo, y_hi) range.
    Taking the range as an argument (rather than re-reading ax.get_ylim()
    per call) matters when two panels share a y-axis: computing from a
    live, already-mutated ylim would let each panel's expansion feed into
    the next and inflate the range without bound."""
    min_gap = (y_hi - y_lo) * min_gap_frac
    ordered = sorted(entries, key=lambda e: e["y"])
    placed = [e["y"] for e in ordered]
    for i in range(1, len(placed)):
        if placed[i] - placed[i - 1] < min_gap:
            placed[i] = placed[i - 1] + min_gap
    return ordered, placed, min_gap


def draw_end_labels(ax, ordered, placed):
    """Render each entry's bold, colour-matched label at its (possibly
    nudged) position, with a thin leader line back to the true y where it
    was moved to avoid a collision."""
    for e, ly in zip(ordered, placed):
        label_x = e["x"] * 1.02 if e["x"] else e["x"] + 0.4
        if abs(ly - e["y"]) > 1e-9:
            ax.plot([e["x"], label_x], [e["y"], ly], color=e["color"], linewidth=0.8, alpha=0.6, zorder=1)
        ax.text(
            label_x, ly, e["text"],
            color=e["color"], fontweight="bold", fontsize=SIZE_DEFAULT - 1,
            horizontalalignment="left", verticalalignment="center",
        )


def style_axis(ax, xlabel, ylabel, title, x_min, x_max):
    ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.set_title(title, fontweight="bold", pad=10)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(2))

    # Ditch the box (Tufte data-ink ratio) -- keep only the axes a reader
    # needs to read values off of.
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["bottom"].set_color(INK_MUTED)
    ax.spines["bottom"].set_bounds(x_min, x_max)
    ax.yaxis.set_ticks_position("left")
    ax.xaxis.set_ticks_position("bottom")
    ax.tick_params(colors=INK_MUTED)


x_min, x_max = per_n["n"].min(), per_n["n"].max()

MOVEMENTS = ["4dir", "8dir"]

for metric, label, fname in [("time_ms", "Mean execution time (ms)", "results/fig_time.png"),
                             ("nodes", "Nodes explored", "results/fig_nodes.png"),
                             ("cost", "Path cost (weight units)", "results/fig_cost.png")]:
    # Path cost is on a fundamentally different scale between movement
    # rules (diagonal steps let 8-directional paths cut corners, so their
    # optimal cost is ~20% lower) -- sharing a y-axis there would squeeze
    # the 8-directional panel's data into an invisible sliver. Time and
    # nodes-expanded are comparable across movement rules, so those two
    # keep a shared axis for direct visual comparison.
    share_y = metric != "cost"
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=share_y)
    fig.patch.set_facecolor(SURFACE)

    panel_labels = {}
    for ax, mv in zip(axes, MOVEMENTS):
        ax.set_facecolor(SURFACE)
        labels = []

        if metric == "cost":
            baseline_style = BASELINE_LINESTYLE_COST
            d = dij[dij.movement == mv].sort_values("n")
            ax.plot(d["n"], d["dijkstra_cost"], color=BASELINE_COLOR, linestyle=baseline_style, linewidth=1.5, zorder=1)
            labels.append({
                "x": d["n"].iloc[-1], "y": d["dijkstra_cost"].iloc[-1],
                "text": "Dijkstra (optimal)", "color": BASELINE_COLOR,
            })

        for i, h in enumerate(["manhattan", "euclidean", "chebyshev"]):
            d = per_n[(per_n.heuristic == h) & (per_n.movement == mv)].sort_values("n")
            linestyle = COST_LINESTYLES[h] if metric == "cost" else "-"
            linewidth = 2.4 if metric == "cost" else 2
            ax.plot(d["n"], d[metric], color=COLORS[h], linewidth=linewidth, linestyle=linestyle, zorder=2 + i)
            labels.append({"x": d["n"].iloc[-1], "y": d[metric].iloc[-1], "text": h.capitalize(), "color": COLORS[h]})

        style_axis(
            ax, "Number of obstacles (N)", label if mv == "4dir" else None,
            MOVEMENT_TITLES[mv], x_min, x_max,
        )
        panel_labels[mv] = labels

    # Compute label placement from a fixed range per panel (or one shared
    # range, for the two metrics that share a y-axis) so that placing one
    # panel's labels never feeds into and inflates the other's.
    fig.canvas.draw()
    if share_y:
        y_lo, y_hi = axes[0].get_ylim()
        placements = {}
        max_top = y_hi
        for mv in MOVEMENTS:
            ordered, placed, min_gap = compute_end_label_positions(y_lo, y_hi, panel_labels[mv])
            placements[mv] = (ordered, placed)
            max_top = max(max_top, placed[-1] + min_gap * 0.6)
        if max_top > y_hi:
            axes[0].set_ylim(y_lo, max_top)
        for ax, mv in zip(axes, MOVEMENTS):
            draw_end_labels(ax, *placements[mv])
    else:
        for ax, mv in zip(axes, MOVEMENTS):
            y_lo, y_hi = ax.get_ylim()
            ordered, placed, min_gap = compute_end_label_positions(y_lo, y_hi, panel_labels[mv])
            if placed[-1] > y_hi:
                ax.set_ylim(y_lo, placed[-1] + min_gap * 0.6)
            draw_end_labels(ax, ordered, placed)

    fig.suptitle(label, fontweight="bold", fontsize=SIZE_DEFAULT + 3, y=1.04)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(fname, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"Saved {fname}")
