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

    // Dijkstra's algorithm is equivalent to A* with h(n) = 0 for every node,
    // i.e. no directional guidance -- it expands purely by g(n).
    auto heuristic = [](const point&, const point&) -> double {
        return 0.0;
    };

    auto t0 = std::chrono::high_resolution_clock::now();
    search_result result = run_search(tc, heuristic);
    auto t1 = std::chrono::high_resolution_clock::now();

    double time_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    std::cout << "dijkstra," << n << "," << run_index << ","
              << time_ms << "," << result.nodes_explored << ","
              << (result.found ? result.path_cost : -1) << "\n";

    return 0;
}
