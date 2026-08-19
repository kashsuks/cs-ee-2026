#include "helpers/astar_common.h"
#include <chrono>
#include <cstdlib>
#include <string>

int main(int argc, char* argv[]) {
    if (argc < 4) {
        std::cerr << "usage: " << argv[0] << " <testcase_file> <n> <run_index> [diagonal]\n";
        std::cerr << "  pass 'diagonal' as a 4th arg to validate Euclidean/Chebyshev instead of Manhattan\n";
        return 1;
    }

    std::string testcase_file = argv[1];
    int n = std::atoi(argv[2]);
    int run_index = std::atoi(argv[3]);

    // Dijkstra's algorithm is A* with h(n) = 0 -- no directional guidance,
    // pure g(n) expansion. Since Manhattan runs 4-directional and
    // Euclidean/Chebyshev run 8-directional, "optimal" means something
    // different for each group, so this baseline can run in either mode:
    //   (no 4th arg)      -> 4-directional baseline, validates Manhattan
    //   (4th arg "diagonal") -> 8-directional baseline, validates Euclidean/Chebyshev
    bool allow_diagonal = (argc >= 5 && std::string(argv[4]) == "diagonal");

    test_case tc = parse_test_case(testcase_file);

    auto heuristic = [](const point&, const point&) -> double {
        return 0.0;
    };

    auto t0 = std::chrono::high_resolution_clock::now();
    search_result result = run_search(tc, heuristic, allow_diagonal);
    auto t1 = std::chrono::high_resolution_clock::now();

    double time_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    std::cout << "dijkstra," << n << "," << run_index << ","
              << time_ms << "," << result.nodes_explored << ","
              << (result.found ? result.path_cost : -1) << "\n";

    return 0;
}