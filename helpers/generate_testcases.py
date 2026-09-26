import random
from collections import deque
from math import sqrt

GRID_WIDTH = 10
GRID_HEIGHT = 10
START = (0, 0)
TARGET = (9, 9)

# Edge weights model city-block lengths in metres: horizontal edges run
# along avenues, vertical edges along the (shorter) cross streets. This
# also defines the tightest admissible per-step bound any heuristic can
# assume -- see MIN_EDGE_WEIGHT in astar_common.h, which must be kept in
# sync with min(MIN_WEIGHT_H, MIN_WEIGHT_V) below.
MIN_WEIGHT_H, MAX_WEIGHT_H = 100, 150  # avenues
MIN_WEIGHT_V, MAX_WEIGHT_V = 60, 100   # streets

# Weights are generated ONCE, from their own RNG, independent of N and of
# the obstacle layout. Obstacles are drawn from a separate RNG. Without this
# split, changing N also silently changed every edge weight (the old code
# reseeded a single RNG with 1000+N and drew weights then obstacles from
# it), so path-cost differences across N were confounded between "more
# obstacles" and "different graph entirely".
WEIGHT_SEED = 999
OBSTACLE_SEED = 500

def gen_weights(rng):
    h_weights = {}   # (x, y) -> weight of edge (x,y)-(x+1,y)
    v_weights = {}   # (x, y) -> weight of edge (x,y)-(x,y+1)
    d1_weights = {}  # (x, y) -> weight of edge (x,y)-(x+1,y+1)  "down-right"
    d2_weights = {}  # (x, y) -> weight of edge (x,y)-(x+1,y-1)  "up-right"

    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if x < GRID_WIDTH - 1:
                h_weights[(x, y)] = rng.randint(MIN_WEIGHT_H, MAX_WEIGHT_H)
            if y < GRID_HEIGHT - 1:
                v_weights[(x, y)] = rng.randint(MIN_WEIGHT_V, MAX_WEIGHT_V)

    # Diagonal edges aren't sampled independently -- a diagonal cuts across
    # one avenue block and one street block, so its physical length is the
    # hypotenuse of the H/V block it cuts across (Pythagorean distance),
    # not an arbitrary number.
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if x < GRID_WIDTH - 1 and y < GRID_HEIGHT - 1:
                h, v = h_weights[(x, y)], v_weights[(x, y)]
                d1_weights[(x, y)] = round(sqrt(h * h + v * v))
            if x < GRID_WIDTH - 1 and y > 0:
                h, v = h_weights[(x, y - 1)], v_weights[(x, y - 1)]
                d2_weights[(x, y - 1)] = round(sqrt(h * h + v * v))

    return h_weights, v_weights, d1_weights, d2_weights

def is_connected(obstacles):
    # BFS from START to TARGET over non-obstacle nodes only, using
    # 4-directional adjacency. This is a deliberately conservative check:
    # 8-directional connectivity can only add more paths, never fewer, so
    # a layout that's connected under 4-directional movement is guaranteed
    # connected under 8-directional movement too.
    if START in obstacles or TARGET in obstacles:
        return False
    visited = {START}
    queue = deque([START])
    while queue:
        x, y = queue.popleft()
        if (x, y) == TARGET:
            return True
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                if (nx, ny) not in obstacles and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
    return TARGET in visited

def build_nested_obstacle_sequence(max_n):
    # Shuffle every candidate cell once under a fixed seed, then take cells
    # in that order, skipping any that would disconnect START from TARGET.
    # The obstacle set for a given n is exactly the first n cells of this
    # sequence, so the layout at N+1 is always the layout at N plus one
    # obstacle -- any change in a search result between N and N+1 comes
    # from exactly one new obstacle, never a reshuffled graph.
    all_cells = [(x, y) for x in range(GRID_WIDTH) for y in range(GRID_HEIGHT)
                 if (x, y) != START and (x, y) != TARGET]
    order_rng = random.Random(OBSTACLE_SEED)
    order_rng.shuffle(all_cells)

    obstacles = set()
    sequence = []
    for cell in all_cells:
        if len(sequence) == max_n:
            break
        candidate = obstacles | {cell}
        if is_connected(candidate):
            obstacles = candidate
            sequence.append(cell)

    if len(sequence) < max_n:
        raise RuntimeError(
            f"Could not build a nested connected obstacle layout of size {max_n} "
            f"(only reached {len(sequence)})"
        )
    return sequence

def write_testcase(n, path, weights, obstacle_sequence):
    h_weights, v_weights, d1_weights, d2_weights = weights
    obstacles = obstacle_sequence[:n]

    lines = []
    lines.append(f"# Test case N={n}")
    lines.append(f"# Weight seed: {WEIGHT_SEED} (fixed across all N)")
    lines.append(f"# Obstacle seed: {OBSTACLE_SEED} (nested: first {n} of one shuffled order)")
    lines.append(f"GRID_WIDTH {GRID_WIDTH}")
    lines.append(f"GRID_HEIGHT {GRID_HEIGHT}")
    lines.append(f"START {START[0]},{START[1]}")
    lines.append(f"TARGET {TARGET[0]},{TARGET[1]}")
    lines.append(f"OBSTACLE_COUNT {n}")
    lines.append("OBSTACLES")
    for (x, y) in sorted(obstacles):
        lines.append(f"{x},{y}")

    lines.append("EDGE_WEIGHTS_HORIZONTAL")
    lines.append("# format: x,y,weight  -- edge between (x,y) and (x+1,y)")
    for (x, y), w in sorted(h_weights.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        lines.append(f"{x},{y},{w}")

    lines.append("EDGE_WEIGHTS_VERTICAL")
    lines.append("# format: x,y,weight  -- edge between (x,y) and (x,y+1)")
    for (x, y), w in sorted(v_weights.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        lines.append(f"{x},{y},{w}")

    lines.append("EDGE_WEIGHTS_DIAGONAL_DOWN_RIGHT")
    lines.append("# format: x,y,weight  -- edge between (x,y) and (x+1,y+1)")
    for (x, y), w in sorted(d1_weights.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        lines.append(f"{x},{y},{w}")

    lines.append("EDGE_WEIGHTS_DIAGONAL_UP_RIGHT")
    lines.append("# format: x,y,weight  -- edge between (x,y) and (x+1,y-1)")
    for (x, y), w in sorted(d2_weights.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        lines.append(f"{x},{y},{w}")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    import os
    out_dir = "testcases"
    os.makedirs(out_dir, exist_ok=True)

    weight_rng = random.Random(WEIGHT_SEED)
    weights = gen_weights(weight_rng)

    obstacle_sequence = build_nested_obstacle_sequence(20)

    for n in range(0, 21):
        path = os.path.join(out_dir, f"testcase_n_{n}.txt")
        write_testcase(n, path, weights, obstacle_sequence)
        print(f"wrote {path}")
