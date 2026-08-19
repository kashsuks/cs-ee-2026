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

    // Chebyshev distance (h(n) = max(|dx|,|dy|)) explicitly assumes a
    // diagonal step covers both axes at once for the same cost as an
    // orthogonal step, so this search runs in 8-directional mode --
    // matching the heuristic's own assumption. Under this movement rule
    // Chebyshev is admissible, unlike when forced onto a 4-directional grid.
    const bool allow_diagonal = true;

    auto heuristic = [](const point& a, const point& b) -> double {
        int dx = std::abs(a.x - b.x);
        int dy = std::abs(a.y - b.y);
        return std::max(dx, dy);
    };

    auto t0 = std::chrono::high_resolution_clock::now();
    search_result result = run_search(tc, heuristic, allow_diagonal);
    auto t1 = std::chrono::high_resolution_clock::now();

    double time_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    std::cout << "chebyshev," << n << "," << run_index << ","
              << time_ms << "," << result.nodes_explored << ","
              << (result.found ? result.path_cost : -1) << "\n";

    return 0;
}