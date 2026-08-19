import random
from collections import deque

GRID_WIDTH = 10
GRID_HEIGHT = 10
START = (0, 0)
TARGET = (9, 9)
MIN_WEIGHT = 1
MAX_WEIGHT = 8

def gen_weights(rng):
    h_weights = {}   # (x, y) -> weight of edge (x,y)-(x+1,y)
    v_weights = {}   # (x, y) -> weight of edge (x,y)-(x,y+1)
    d1_weights = {}  # (x, y) -> weight of edge (x,y)-(x+1,y+1)  "down-right"
    d2_weights = {}  # (x, y) -> weight of edge (x,y)-(x+1,y-1)  "up-right"

    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if x < GRID_WIDTH - 1:
                h_weights[(x, y)] = rng.randint(MIN_WEIGHT, MAX_WEIGHT)
            if y < GRID_HEIGHT - 1:
                v_weights[(x, y)] = rng.randint(MIN_WEIGHT, MAX_WEIGHT)
            if x < GRID_WIDTH - 1 and y < GRID_HEIGHT - 1:
                d1_weights[(x, y)] = rng.randint(MIN_WEIGHT, MAX_WEIGHT)
            if x < GRID_WIDTH - 1 and y > 0:
                d2_weights[(x, y - 1)] = rng.randint(MIN_WEIGHT, MAX_WEIGHT)

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

def gen_obstacles(rng, n):
    all_cells = [(x, y) for x in range(GRID_WIDTH) for y in range(GRID_HEIGHT)
                 if (x, y) != START and (x, y) != TARGET]
    for attempt in range(2000):
        candidate = set(rng.sample(all_cells, n))
        if is_connected(candidate):
            return candidate
    raise RuntimeError(f"Could not find connected obstacle layout for n={n}")

def write_testcase(n, path):
    seed = 1000 + n  # fixed per-N seed for reproducibility
    rng = random.Random(seed)

    h_weights, v_weights, d1_weights, d2_weights = gen_weights(rng)
    obstacles = gen_obstacles(rng, n)

    lines = []
    lines.append(f"# Test case N={n}")
    lines.append(f"# Seed used: {seed}")
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
    for n in range(0, 21):
        path = os.path.join(out_dir, f"testcase_n_{n}.txt")
        write_testcase(n, path)
        print(f"wrote {path}")