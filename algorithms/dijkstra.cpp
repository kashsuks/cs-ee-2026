#include "helpers/astar_common.h"
#include <chrono>
#include <cstdlib>
#include <string>

int main(int argc, char* argv[]) {
    if (argc < 4) {
        std::cerr << "usage: " << argv[0] << " <testcase_file> <n> <run_index> [diagonal]\n";
        std::cerr << "  pass 'diagonal' as a 4th arg to run on the 8-directional graph\n";
        return 1;
    }

    std::string testcase_file = argv[1];
    int n = std::atoi(argv[2]);
    int run_index = std::atoi(argv[3]);

    // Dijkstra's algorithm is A* with h(n) = 0 -- no directional guidance,
    // pure g(n) expansion. It's the ground-truth optimal-cost baseline for
    // whichever movement rule it's run under.
    bool allow_diagonal = (argc >= 5 && std::string(argv[4]) == "diagonal");

    test_case tc = parse_test_case(testcase_file);

    auto heuristic = [](const point&, const point&) -> double {
        return 0.0;
    };

    // Average over many in-process searches to reduce timer/scheduler
    // noise, which is otherwise comparable in magnitude to a single
    // ~40us search. One warm-up run is discarded first.
    const int REPS = 1000;
    search_result result = run_search(tc, heuristic, allow_diagonal);
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int r = 0; r < REPS; ++r) {
        result = run_search(tc, heuristic, allow_diagonal);
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double time_ms = std::chrono::duration<double, std::milli>(t1 - t0).count() / REPS;

    std::cout << "dijkstra," << (allow_diagonal ? "8dir" : "4dir") << ","
              << n << "," << run_index << ","
              << time_ms << "," << result.nodes_explored << ","
              << (result.found ? result.path_cost : -1) << "\n";

    return 0;
}
