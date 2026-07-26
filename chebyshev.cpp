#include "helpers/astar_common.h"
#include <chrono>
#include <cstdlib>

int main(int argc, char* argv[]) {
    if (argc < 4) {
        std::cerr << "usage: " << argv[0] << " <testcase_file> <n> <run_index>\n";
        return 1;
    }

    std::string testcase_file = argv[1];
    int n = std::atoi(argv[2]);
    int run_index = std::atoi(argv[3]);

    test_case tc = parse_test_case(testcase_file);

    // Chebyshev distance: h(n) = max(|dx|, |dy|).
    // Note: this graph only allows 4-directional movement (see get_neighbours
    // in astar_common.h) -- there is no diagonal movement between nodes.
    // Chebyshev distance assumes diagonal movement is possible, so on this
    // graph it can overestimate the true cost and is therefore NOT admissible.
    // It's included purely as a comparison point, not because it's expected
    // to perform optimally here.
    auto heuristic = [](const point& a, const point& b) -> double {
        int dx = std::abs(a.x - b.x);
        int dy = std::abs(a.y - b.y);
        return std::max(dx, dy);
    };

    auto t0 = std::chrono::high_resolution_clock::now();
    search_result result = run_search(tc, heuristic);
    auto t1 = std::chrono::high_resolution_clock::now();

    double time_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    std::cout << "chebyshev," << n << "," << run_index << ","
              << time_ms << "," << result.nodes_explored << ","
              << (result.found ? result.path_cost : -1) << "\n";

    return 0;
}
