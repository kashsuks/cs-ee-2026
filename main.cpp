#include <iostream>
#include <vector>
#include <queue>
#include <unordered_map>
#include <cmath>
#include <algorithm>

// ---------- basic types ----------

struct node {
    int x, y;

    bool operator==(const node& other) const {
        return x == other.x && y == other.y;
    }
};

// hash function so node can be used as a key in unordered_map
struct node_hash {
    std::size_t operator()(const node& n) const {
        return std::hash<int>()(n.x) ^ (std::hash<int>()(n.y) << 1);
    }
};

// ---------- heuristic helpers ----------
// each of these estimates h(n): the cost from the current node to the target node.
// swap whichever one is called in the main loop to compare heuristics.

double manhattan_distance(const node& a, const node& b) {
    return std::abs(a.x - b.x) + std::abs(a.y - b.y);
}

double euclidean_distance(const node& a, const node& b) {
    return std::sqrt(std::pow(a.x - b.x, 2) + std::pow(a.y - b.y, 2));
}

double diagonal_distance(const node& a, const node& b) {
    int dx = std::abs(a.x - b.x);
    int dy = std::abs(a.y - b.y);
    return std::max(dx, dy);
}

// ---------- grid setup ----------

const int grid_width = 10;
const int grid_height = 10;

// obstacles representing buildings, marked as blocked cells
std::vector<std::vector<bool>> is_blocked(grid_height, std::vector<bool>(grid_width, false));

bool is_valid(const node& n) {
    if (n.x < 0 || n.x >= grid_width || n.y < 0 || n.y >= grid_height) return false;
    if (is_blocked[n.y][n.x]) return false;
    return true;
}

// returns the neighbours of a node, along with the cost to move to each one.
// this is where diagonal movement is either included or excluded depending on your test case.
std::vector<std::pair<node, double>> get_neighbours(const node& current) {
    std::vector<std::pair<node, double>> neighbours;

    // four-directional moves (up, down, left, right), cost 1
    std::vector<node> orthogonal = {
        {current.x + 1, current.y},
        {current.x - 1, current.y},
        {current.x, current.y + 1},
        {current.x, current.y - 1}
    };

    // diagonal moves, cost sqrt(2) — comment out this block if diagonal movement isn't allowed
    std::vector<node> diagonal = {
        {current.x + 1, current.y + 1},
        {current.x + 1, current.y - 1},
        {current.x - 1, current.y + 1},
        {current.x - 1, current.y - 1}
    };

    for (const auto& n : orthogonal) {
        if (is_valid(n)) neighbours.push_back({n, 1.0});
    }
    for (const auto& n : diagonal) {
        if (is_valid(n)) neighbours.push_back({n, std::sqrt(2)});
    }

    return neighbours;
}

// ---------- priority queue setup ----------

struct open_set_entry {
    node n;
    double f_score;

    // priority_queue is a max-heap by default, so we invert the comparison
    // to get the lowest f_score out first
    bool operator>(const open_set_entry& other) const {
        return f_score > other.f_score;
    }
};

// ---------- a* search ----------

std::vector<node> reconstruct_path(std::unordered_map<node, node, node_hash>& came_from, node current) {
    std::vector<node> path = {current};
    while (came_from.find(current) != came_from.end()) {
        current = came_from[current];
        path.push_back(current);
    }
    std::reverse(path.begin(), path.end());
    return path;
}

std::vector<node> a_star_search(node start, node target) {
    // swap this line to test a different heuristic
    auto heuristic = manhattan_distance;

    std::priority_queue<open_set_entry, std::vector<open_set_entry>, std::greater<open_set_entry>> open_queue;

    std::unordered_map<node, double, node_hash> g_score;
    std::unordered_map<node, node, node_hash> came_from;
    std::unordered_map<node, bool, node_hash> in_closed_set;

    g_score[start] = 0.0;
    open_queue.push({start, heuristic(start, target)});

    while (!open_queue.empty()) {
        node current = open_queue.top().n;
        open_queue.pop();

        if (current == target) {
            return reconstruct_path(came_from, current);
        }

        if (in_closed_set[current]) continue;
        in_closed_set[current] = true;

        for (const auto& [neighbour, move_cost] : get_neighbours(current)) {
            if (in_closed_set[neighbour]) continue;

            double tentative_g = g_score[current] + move_cost;

            if (g_score.find(neighbour) == g_score.end() || tentative_g < g_score[neighbour]) {
                came_from[neighbour] = current;
                g_score[neighbour] = tentative_g;
                double f_score = tentative_g + heuristic(neighbour, target);
                open_queue.push({neighbour, f_score});
            }
        }
    }

    // no path found
    return {};
}

// ---------- driver ----------

int main() {
    // example obstacle placement that represent a couple of "buildings"
    is_blocked[3][4] = true;
    is_blocked[3][5] = true;
    is_blocked[4][4] = true;

    node start = {0, 0};
    node target = {9, 9};

    std::vector<node> path = a_star_search(start, target);

    if (path.empty()) {
        std::cout << "no path found\n";
        return 0;
    }

    std::cout << "path found (" << path.size() << " nodes):\n";
    for (const auto& n : path) {
        std::cout << "(" << n.x << ", " << n.y << ")\n";
    }

    return 0;
}
