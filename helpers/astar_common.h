#pragma once

// Tightest admissible per-grid-step cost: must equal
// min(MIN_WEIGHT_H, MIN_WEIGHT_V) from generate_testcases.py. Each
// heuristic multiplies its raw grid-unit distance by this constant so it
// stays a valid (and informative) lower bound now that edge weights are
// realistic block lengths in metres rather than small integers -- without
// this scaling, h(n) would still be technically admissible but would
// underestimate true cost by ~60-150x, making A* degenerate toward
// Dijkstra's expansion pattern for every heuristic.
constexpr double MIN_EDGE_WEIGHT = 60.0;

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <queue>
#include <cmath>
#include <algorithm>
#include <functional>

struct point {
    int x, y;
    bool operator==(const point& o) const { return x == o.x && y == o.y; }
};

struct point_hash {
    std::size_t operator()(const point& p) const {
        return std::hash<int>()(p.x) ^ (std::hash<int>()(p.y) << 16);
    }
};

struct test_case {
    int width, height;
    point start, target;
    std::unordered_set<point, point_hash> obstacles;

    // orthogonal edges
    // h_weights[(x,y)] = weight of edge between (x,y) and (x+1,y)
    // v_weights[(x,y)] = weight of edge between (x,y) and (x,y+1)
    std::unordered_map<point, int, point_hash> h_weights;
    std::unordered_map<point, int, point_hash> v_weights;

    // diagonal edges (only used when a search runs in 8-directional mode)
    // d1_weights[(x,y)] = weight of edge between (x,y) and (x+1,y+1)   ("down-right")
    // d2_weights[(x,y)] = weight of edge between (x,y) and (x+1,y-1)   ("up-right")
    std::unordered_map<point, int, point_hash> d1_weights;
    std::unordered_map<point, int, point_hash> d2_weights;
};

// splits a "x,y" style token into a point
inline point parse_point(const std::string& s) {
    auto comma = s.find(',');
    point p;
    p.x = std::stoi(s.substr(0, comma));
    p.y = std::stoi(s.substr(comma + 1));
    return p;
}

inline test_case parse_test_case(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        throw std::runtime_error("could not open test case file: " + path);
    }

    test_case tc;
    std::string line;
    std::string section;

    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue;

        std::istringstream iss(line);
        std::string first;
        iss >> first;

        if (first == "GRID_WIDTH") { iss >> tc.width; continue; }
        if (first == "GRID_HEIGHT") { iss >> tc.height; continue; }
        if (first == "START") { std::string v; iss >> v; tc.start = parse_point(v); continue; }
        if (first == "TARGET") { std::string v; iss >> v; tc.target = parse_point(v); continue; }
        if (first == "OBSTACLE_COUNT") { continue; } // informational only
        if (first == "OBSTACLES") { section = "OBSTACLES"; continue; }
        if (first == "EDGE_WEIGHTS_HORIZONTAL") { section = "H"; continue; }
        if (first == "EDGE_WEIGHTS_VERTICAL") { section = "V"; continue; }
        if (first == "EDGE_WEIGHTS_DIAGONAL_DOWN_RIGHT") { section = "D1"; continue; }
        if (first == "EDGE_WEIGHTS_DIAGONAL_UP_RIGHT") { section = "D2"; continue; }

        // otherwise, this line is data belonging to the current section
        if (section == "OBSTACLES") {
            tc.obstacles.insert(parse_point(first));
        } else if (section == "H" || section == "V" || section == "D1" || section == "D2") {
            // format: x,y,weight
            std::stringstream ss(first);
            std::string tok;
            std::vector<int> parts;
            while (std::getline(ss, tok, ',')) parts.push_back(std::stoi(tok));
            point p{parts[0], parts[1]};
            int w = parts[2];
            if (section == "H") tc.h_weights[p] = w;
            else if (section == "V") tc.v_weights[p] = w;
            else if (section == "D1") tc.d1_weights[p] = w;
            else if (section == "D2") tc.d2_weights[p] = w;
        }
    }

    return tc;
}

// returns neighbours of a node along with the cost of moving to each one.
// obstacle nodes are skipped entirely, so edges leading into a wall never exist.
// allow_diagonal controls whether the 4 diagonal neighbours are included --
// pass false for heuristics that assume 4-directional movement (Manhattan),
// and true for heuristics that assume 8-directional movement (Euclidean, Chebyshev).
inline std::vector<std::pair<point, int>> get_neighbours(const test_case& tc, const point& n, bool allow_diagonal) {
    std::vector<std::pair<point, int>> result;

    // right
    if (n.x + 1 < tc.width) {
        point nb{n.x + 1, n.y};
        if (!tc.obstacles.count(nb)) result.push_back({nb, tc.h_weights.at({n.x, n.y})});
    }
    // left
    if (n.x - 1 >= 0) {
        point nb{n.x - 1, n.y};
        if (!tc.obstacles.count(nb)) result.push_back({nb, tc.h_weights.at({n.x - 1, n.y})});
    }
    // down
    if (n.y + 1 < tc.height) {
        point nb{n.x, n.y + 1};
        if (!tc.obstacles.count(nb)) result.push_back({nb, tc.v_weights.at({n.x, n.y})});
    }
    // up
    if (n.y - 1 >= 0) {
        point nb{n.x, n.y - 1};
        if (!tc.obstacles.count(nb)) result.push_back({nb, tc.v_weights.at({n.x, n.y - 1})});
    }

    if (!allow_diagonal) return result;

    // down-right: (x,y) -> (x+1,y+1), stored at key (x,y) in d1_weights
    if (n.x + 1 < tc.width && n.y + 1 < tc.height) {
        point nb{n.x + 1, n.y + 1};
        if (!tc.obstacles.count(nb)) result.push_back({nb, tc.d1_weights.at({n.x, n.y})});
    }
    // up-left: (x,y) -> (x-1,y-1), same edge as down-right stored at (x-1,y-1)
    if (n.x - 1 >= 0 && n.y - 1 >= 0) {
        point nb{n.x - 1, n.y - 1};
        if (!tc.obstacles.count(nb)) result.push_back({nb, tc.d1_weights.at({n.x - 1, n.y - 1})});
    }
    // up-right: (x,y) -> (x+1,y-1), stored at key (x,y-1) in d2_weights
    if (n.x + 1 < tc.width && n.y - 1 >= 0) {
        point nb{n.x + 1, n.y - 1};
        if (!tc.obstacles.count(nb)) result.push_back({nb, tc.d2_weights.at({n.x, n.y - 1})});
    }
    // down-left: (x,y) -> (x-1,y+1), same edge as up-right stored at (x-1,y)
    if (n.x - 1 >= 0 && n.y + 1 < tc.height) {
        point nb{n.x - 1, n.y + 1};
        if (!tc.obstacles.count(nb)) result.push_back({nb, tc.d2_weights.at({n.x - 1, n.y})});
    }

    return result;
}

struct search_result {
    bool found;
    int path_cost;
    long long nodes_explored;
};

struct open_entry {
    point n;
    double f;
    bool operator>(const open_entry& o) const { return f > o.f; }
};

// generic search: pass h = [](point,point){ return 0.0; } to get plain Dijkstra.
// allow_diagonal controls the movement rule the search runs under -- this should
// match the assumption baked into the heuristic being used (see get_neighbours).
inline search_result run_search(const test_case& tc, const std::function<double(const point&, const point&)>& h, bool allow_diagonal) {
    std::priority_queue<open_entry, std::vector<open_entry>, std::greater<open_entry>> open_queue;
    std::unordered_map<point, int, point_hash> g_score;
    std::unordered_set<point, point_hash> closed_set;

    g_score[tc.start] = 0;
    open_queue.push({tc.start, h(tc.start, tc.target)});

    long long nodes_explored = 0;

    while (!open_queue.empty()) {
        point current = open_queue.top().n;
        open_queue.pop();

        if (closed_set.count(current)) continue;
        closed_set.insert(current);
        nodes_explored++;

        if (current == tc.target) {
            return { true, g_score[current], nodes_explored };
        }

        for (const auto& [neighbour, cost] : get_neighbours(tc, current, allow_diagonal)) {
            if (closed_set.count(neighbour)) continue;

            int tentative_g = g_score[current] + cost;

            auto it = g_score.find(neighbour);
            if (it == g_score.end() || tentative_g < it->second) {
                g_score[neighbour] = tentative_g;
                open_queue.push({neighbour, tentative_g + h(neighbour, tc.target)});
            }
        }
    }

    return { false, -1, nodes_explored };
}