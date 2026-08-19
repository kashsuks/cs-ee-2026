#!/usr/bin/env python3
"""
visualize_testcase.py

Renders a testcase_n_N.txt file into a PNG image: nodes as circles,
obstacles shaded dark, start/target coloured, and edge weights labelled
(including diagonal edges now that Euclidean and Chebyshev use them).

Optionally runs a chosen heuristic and overlays the resulting path. Each
heuristic runs under the movement rule its own formula assumes:
    manhattan  -> 4-directional
    euclidean  -> 8-directional
    chebyshev  -> 8-directional
    dijkstra   -> 4-directional by default; pass --diagonal to run it
                  in 8-directional mode instead (to match euclidean/chebyshev)

Usage:
    python3 visualize_testcase.py testcases/testcase_n_5.txt
    python3 visualize_testcase.py testcases/testcase_n_5.txt --heuristic manhattan
    python3 visualize_testcase.py testcases/testcase_n_5.txt --heuristic chebyshev -o out.png
"""

import argparse
import heapq
import math
import os

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


# ---------- parsing ----------

def parse_testcase(path):
    width = height = None
    start = target = None
    obstacles = set()
    h_weights = {}
    v_weights = {}
    d1_weights = {}  # (x,y) -> (x+1,y+1)
    d2_weights = {}  # (x,y) -> (x+1,y-1)

    section = None

    with open(path) as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("GRID_WIDTH"):
                width = int(line.split()[1]); continue
            if line.startswith("GRID_HEIGHT"):
                height = int(line.split()[1]); continue
            if line.startswith("START"):
                x, y = map(int, line.split()[1].split(",")); start = (x, y); continue
            if line.startswith("TARGET"):
                x, y = map(int, line.split()[1].split(",")); target = (x, y); continue
            if line.startswith("OBSTACLE_COUNT"):
                continue
            if line == "OBSTACLES":
                section = "OBSTACLES"; continue
            if line == "EDGE_WEIGHTS_HORIZONTAL":
                section = "H"; continue
            if line == "EDGE_WEIGHTS_VERTICAL":
                section = "V"; continue
            if line == "EDGE_WEIGHTS_DIAGONAL_DOWN_RIGHT":
                section = "D1"; continue
            if line == "EDGE_WEIGHTS_DIAGONAL_UP_RIGHT":
                section = "D2"; continue

            if section == "OBSTACLES":
                x, y = map(int, line.split(","))
                obstacles.add((x, y))
            elif section == "H":
                x, y, w = map(int, line.split(",")); h_weights[(x, y)] = w
            elif section == "V":
                x, y, w = map(int, line.split(",")); v_weights[(x, y)] = w
            elif section == "D1":
                x, y, w = map(int, line.split(",")); d1_weights[(x, y)] = w
            elif section == "D2":
                x, y, w = map(int, line.split(",")); d2_weights[(x, y)] = w

    return {
        "width": width, "height": height,
        "start": start, "target": target,
        "obstacles": obstacles,
        "h_weights": h_weights, "v_weights": v_weights,
        "d1_weights": d1_weights, "d2_weights": d2_weights,
    }


# ---------- search (for optional path overlay) ----------

def neighbours(tc, node, allow_diagonal):
    x, y = node
    obstacles = tc["obstacles"]
    result = []

    if x + 1 < tc["width"] and (x + 1, y) not in obstacles:
        result.append(((x + 1, y), tc["h_weights"][(x, y)]))
    if x - 1 >= 0 and (x - 1, y) not in obstacles:
        result.append(((x - 1, y), tc["h_weights"][(x - 1, y)]))
    if y + 1 < tc["height"] and (x, y + 1) not in obstacles:
        result.append(((x, y + 1), tc["v_weights"][(x, y)]))
    if y - 1 >= 0 and (x, y - 1) not in obstacles:
        result.append(((x, y - 1), tc["v_weights"][(x, y - 1)]))

    if not allow_diagonal:
        return result

    if x + 1 < tc["width"] and y + 1 < tc["height"] and (x + 1, y + 1) not in obstacles:
        result.append(((x + 1, y + 1), tc["d1_weights"][(x, y)]))
    if x - 1 >= 0 and y - 1 >= 0 and (x - 1, y - 1) not in obstacles:
        result.append(((x - 1, y - 1), tc["d1_weights"][(x - 1, y - 1)]))
    if x + 1 < tc["width"] and y - 1 >= 0 and (x + 1, y - 1) not in obstacles:
        result.append(((x + 1, y - 1), tc["d2_weights"][(x, y - 1)]))
    if x - 1 >= 0 and y + 1 < tc["height"] and (x - 1, y + 1) not in obstacles:
        result.append(((x - 1, y + 1), tc["d2_weights"][(x - 1, y)]))

    return result


def heuristic_fn(name):
    if name == "manhattan":
        return lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
    if name == "euclidean":
        return lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
    if name == "chebyshev":
        return lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
    if name == "dijkstra":
        return lambda a, b: 0
    raise ValueError(f"unknown heuristic: {name}")


# each heuristic runs under the movement rule its own formula assumes
MOVEMENT_RULE = {
    "manhattan": False,   # 4-directional
    "euclidean": True,    # 8-directional
    "chebyshev": True,    # 8-directional
    "dijkstra": False,    # 4-directional by default (see --diagonal flag)
}


def a_star(tc, heuristic_name, allow_diagonal):
    h = heuristic_fn(heuristic_name)
    start, target = tc["start"], tc["target"]

    open_heap = [(h(start, target), start)]
    g_score = {start: 0}
    came_from = {}
    closed = set()
    explored_order = []

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        closed.add(current)
        explored_order.append(current)

        if current == target:
            path = [current]
            while path[-1] in came_from:
                path.append(came_from[path[-1]])
            path.reverse()
            return path, explored_order, g_score[current]

        for nb, cost in neighbours(tc, current, allow_diagonal):
            if nb in closed:
                continue
            tentative_g = g_score[current] + cost
            if nb not in g_score or tentative_g < g_score[nb]:
                g_score[nb] = tentative_g
                came_from[nb] = current
                heapq.heappush(open_heap, (tentative_g + h(nb, target), nb))

    return None, explored_order, None


# ---------- rendering ----------

def render(tc, testcase_path, heuristic_name, allow_diagonal, output_path):
    width, height = tc["width"], tc["height"]
    obstacles = tc["obstacles"]
    start, target = tc["start"], tc["target"]

    fig, ax = plt.subplots(figsize=(width * 0.7, height * 0.7))

    # orthogonal edges
    for (x, y), w in tc["h_weights"].items():
        if (x, y) in obstacles or (x + 1, y) in obstacles:
            continue
        ax.plot([x, x + 1], [y, y], color="#c9c5bd", zorder=1, linewidth=1)
        ax.text(x + 0.5, y - 0.18, str(w), ha="center", va="center",
                 fontsize=7, color="#8a857c")

    for (x, y), w in tc["v_weights"].items():
        if (x, y) in obstacles or (x, y + 1) in obstacles:
            continue
        ax.plot([x, x], [y, y + 1], color="#c9c5bd", zorder=1, linewidth=1)
        ax.text(x + 0.22, y + 0.5, str(w), ha="center", va="center",
                 fontsize=7, color="#8a857c")

    # diagonal edges -- drawn lighter/thinner so the grid doesn't get too busy
    for (x, y), w in tc["d1_weights"].items():
        if (x, y) in obstacles or (x + 1, y + 1) in obstacles:
            continue
        ax.plot([x, x + 1], [y, y + 1], color="#ddd9d0", zorder=0, linewidth=0.7)

    for (x, y), w in tc["d2_weights"].items():
        if (x, y) in obstacles or (x + 1, y - 1) in obstacles:
            continue
        ax.plot([x, x + 1], [y, y - 1], color="#ddd9d0", zorder=0, linewidth=0.7)

    path = explored = cost = None
    if heuristic_name != "none":
        path, explored, cost = a_star(tc, heuristic_name, allow_diagonal)

        if explored:
            ex_x = [p[0] for p in explored]
            ex_y = [p[1] for p in explored]
            ax.scatter(ex_x, ex_y, s=260, color="#a9c4e0", alpha=0.55, zorder=2)

        if path:
            path_x = [p[0] for p in path]
            path_y = [p[1] for p in path]
            ax.plot(path_x, path_y, color="#BA7517", linewidth=3, zorder=3,
                     solid_capstyle="round")

    for x in range(width):
        for y in range(height):
            if (x, y) in obstacles:
                color = "#5F5E5A"
            elif (x, y) == start:
                color = "#639922"
            elif (x, y) == target:
                color = "#D85A30"
            else:
                color = "#e8e6e1"
            ax.scatter(x, y, s=180, color=color, edgecolors="#3a3833",
                        linewidths=0.8, zorder=4)

    ax.set_xlim(-0.6, width - 0.4)
    ax.set_ylim(-0.6, height - 0.4)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.set_xticks(range(width))
    ax.set_yticks(range(height))
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    legend_handles = [
        mpatches.Patch(color="#639922", label="start"),
        mpatches.Patch(color="#D85A30", label="target"),
        mpatches.Patch(color="#5F5E5A", label="obstacle"),
    ]
    if heuristic_name != "none":
        legend_handles.append(mpatches.Patch(color="#a9c4e0", label="explored"))
        legend_handles.append(mpatches.Patch(color="#BA7517", label="path"))
    ax.legend(handles=legend_handles, loc="upper center",
              bbox_to_anchor=(0.5, -0.06), ncol=len(legend_handles), frameon=False,
              fontsize=8)

    title = os.path.basename(testcase_path)
    if heuristic_name != "none":
        rule = "8-directional" if allow_diagonal else "4-directional"
        cost_str = cost if cost is not None else "no path found"
        title += f"  —  {heuristic_name} ({rule})  (cost: {cost_str}, nodes explored: {len(explored)})"
    ax.set_title(title, fontsize=10)

    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    print(f"saved: {output_path}")
    if heuristic_name != "none":
        if path:
            print(f"path cost: {cost}, nodes explored: {len(explored)}")
        else:
            print("no path found")


def main():
    parser = argparse.ArgumentParser(description="Visualize a testcase_n_N.txt file")
    parser.add_argument("testcase_file", help="path to testcase_n_N.txt")
    parser.add_argument("--heuristic", default="none",
                         choices=["none", "manhattan", "euclidean", "chebyshev", "dijkstra"],
                         help="overlay the path found by this algorithm (default: none)")
    parser.add_argument("--diagonal", action="store_true",
                         help="force 8-directional movement (only meaningful with --heuristic dijkstra, "
                              "since manhattan/euclidean/chebyshev already use their own fixed movement rule)")
    parser.add_argument("-o", "--output", default=None,
                         help="output PNG path (default: <testcase_name>.png next to the input file)")
    args = parser.parse_args()

    tc = parse_testcase(args.testcase_file)

    if args.heuristic == "dijkstra":
        allow_diagonal = args.diagonal
    else:
        allow_diagonal = MOVEMENT_RULE.get(args.heuristic, False)

    if args.output:
        output_path = args.output
    else:
        base = os.path.splitext(os.path.basename(args.testcase_file))[0]
        suffix = f"_{args.heuristic}" if args.heuristic != "none" else ""
        output_path = os.path.join(os.path.dirname(args.testcase_file) or ".", f"{base}{suffix}.png")

    render(tc, args.testcase_file, args.heuristic, allow_diagonal, output_path)


if __name__ == "__main__":
    main()