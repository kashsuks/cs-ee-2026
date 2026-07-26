#pragma once
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
    // h_weights[(x,y)] = weight of edge between (x,y) and (x+1,y)
    // v_weights[(x,y)] = weight of edge between (x,y) and (x,y+1)
    std::unordered_map<point, int, point_hash> h_weights;
    std::unordered_map<point, int, point_hash> v_weights;
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

        // otherwise, this line is data belonging to the current section
        if (section == "OBSTACLES") {
            tc.obstacles.insert(parse_point(first));
        } else if (section == "H" || section == "V") {
            // format: x,y,weight
            std::stringstream ss(first);
            std::string tok;
            std::vector<int> parts;
            while (std::getline(ss, tok, ',')) parts.push_back(std::stoi(tok));
            point p{parts[0], parts[1]};
            int w = parts[2];
            if (section == "H") tc.h_weights[p] = w;
            else tc.v_weights[p] = w;
        }
    }

    return tc;
}

// returns neighbours of a node along with the cost of moving to each one.
// obstacle nodes are skipped entirely, so edges leading into a wall never exist.
inline std::vector<std::pair<point, int>> get_neighbours(const test_case& tc, const point& n) {
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

// generic search: pass h = [](point,point){ return 0.0; } to get plain Dijkstra
inline search_result run_search(const test_case& tc, const std::function<double(const point&, const point&)>& h) {
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

        for (const auto& [neighbour, cost] : get_neighbours(tc, current)) {
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
