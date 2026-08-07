#!/usr/bin/env python3
"""
visualize_testcase.py

Renders a testcase_n_N.txt file (as produced for the A* / weighted-grid
experiment) into a PNG image: nodes as circles, obstacles shaded dark,
start/target coloured, and edge weights labelled.

Optionally runs a chosen heuristic (or plain Dijkstra) and overlays the
resulting path, so you can visually confirm what a given algorithm actually
does on a specific test case.

Usage:
    python3 visualize_testcase.py testcases/testcase_n_5.txt
    python3 visualize_testcase.py testcases/testcase_n_5.txt --heuristic manhattan
    python3 visualize_testcase.py testcases/testcase_n_5.txt --heuristic chebyshev -o out.png

Heuristic options: manhattan, euclidean, chebyshev, dijkstra, none (default: none)
"""

import argparse # noqa
import heapq
import math
import os
import re
import sys # noqa

import matplotlib.pyplot as plt # noqa
import matplotlib.patches as mpatches # noqa


# ---------- parsing ----------

def parse_testcase(path):
    width = height = None
    start = target = None
    obstacles = set()
    h_weights = {}  # (x, y) -> weight of edge (x,y)-(x+1,y)
    v_weights = {}  # (x, y) -> weight of edge (x,y)-(x,y+1)

    section = None

    with open(path) as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("GRID_WIDTH"):
                width = int(line.split()[1])
                continue
            if line.startswith("GRID_HEIGHT"):
                height = int(line.split()[1])
                continue
            if line.startswith("START"):
                x, y = map(int, line.split()[1].split(","))
                start = (x, y)
                continue
            if line.startswith("TARGET"):
                x, y = map(int, line.split()[1].split(","))
                target = (x, y)
                continue
            if line.startswith("OBSTACLE_COUNT"):
                continue
            if line == "OBSTACLES":
                section = "OBSTACLES"
                continue
            if line == "EDGE_WEIGHTS_HORIZONTAL":
                section = "H"
                continue
            if line == "EDGE_WEIGHTS_VERTICAL":
                section = "V"
                continue

            # data line belonging to current section
            if section == "OBSTACLES":
                x, y = map(int, line.split(","))
                obstacles.add((x, y))
            elif section == "H":
                x, y, w = map(int, line.split(","))
                h_weights[(x, y)] = w
            elif section == "V":
                x, y, w = map(int, line.split(","))
                v_weights[(x, y)] = w

    return {
        "width": width, "height": height,
        "start": start, "target": target,
        "obstacles": obstacles,
        "h_weights": h_weights, "v_weights": v_weights,
    }


# ---------- search (for optional path overlay) ----------

def neighbours(tc, node):
    x, y = node
    result = []
    if x + 1 < tc["width"] and (x + 1, y) not in tc["obstacles"]:
        result.append(((x + 1, y), tc["h_weights"][(x, y)]))
    if x - 1 >= 0 and (x - 1, y) not in tc["obstacles"]:
        result.append(((x - 1, y), tc["h_weights"][(x - 1, y)]))
    if y + 1 < tc["height"] and (x, y + 1) not in tc["obstacles"]:
        result.append(((x, y + 1), tc["v_weights"][(x, y)]))
    if y - 1 >= 0 and (x, y - 1) not in tc["obstacles"]:
        result.append(((x, y - 1), tc["v_weights"][(x, y - 1)]))
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


def a_star(tc, heuristic_name):
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

        for nb, cost in neighbours(tc, current):
            if nb in closed:
                continue
            tentative_g = g_score[current] + cost
            if nb not in g_score or tentative_g < g_score[nb]:
                g_score[nb] = tentative_g
                came_from[nb] = current
                heapq.heappush(open_heap, (tentative_g + h(nb, target), nb))

    return None, explored_order, None


# ---------- rendering ----------

def render(tc, testcase_number, heuristic_name, output_path):
    width, height = tc["width"], tc["height"]
    obstacles = tc["obstacles"]
    start, target = tc["start"], tc["target"]

    fig, ax = plt.subplots(figsize=(width * 0.7, height * 0.7))

    # draw edges (skip any edge touching an obstacle -- it doesn't exist)
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

    path = explored = cost = None
    if heuristic_name != "none":
        path, explored, cost = a_star(tc, heuristic_name)

        if explored:
            ex_x = [p[0] for p in explored]
            ex_y = [p[1] for p in explored]
            ax.scatter(ex_x, ex_y, s=260, color="#a9c4e0", alpha=0.55, zorder=2)

        if path:
            path_x = [p[0] for p in path]
            path_y = [p[1] for p in path]
            ax.plot(path_x, path_y, color="#BA7517", linewidth=3, zorder=3,
                     solid_capstyle="round")

    # draw nodes on top
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
    ax.invert_yaxis()  # (0,0) at top-left, matching how the grid is described
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

    title = f"Visualization of Testcase {testcase_number} (N = {testcase_number})"
    if heuristic_name != "none":
        cost_str = cost if cost is not None else "no path found"
        title += f"  —  {heuristic_name}  (cost: {cost_str}, nodes explored: {len(explored)})"
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
    parser.add_argument("-o", "--output", default=None,
                         help="output PNG path (default: <testcase_name>.png next to the input file)")
    args = parser.parse_args()

    tc = parse_testcase(args.testcase_file)

    base = os.path.splitext(os.path.basename(args.testcase_file))[0]
    match = re.match(r"testcase_n_(\d+)", base)
    testcase_number = match.group(1) if match else base

    if args.output:
        output_path = args.output
    else:
        suffix = f"_{args.heuristic}" if args.heuristic != "none" else ""
        output_path = os.path.join(os.path.dirname(args.testcase_file) or ".", f"{base}{suffix}.png")

    render(tc, testcase_number, args.heuristic, output_path)


if __name__ == "__main__":
    main()
