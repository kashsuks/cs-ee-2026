#!/bin/bash
# run_experiment.sh
#
# Compiles manhattan.cpp, euclidean.cpp, chebyshev.cpp, dijkstra.cpp (all in
# algorithms/, sharing helpers/astar_common.h) and runs the three HEURISTIC
# binaries against every test case (N = 0 to 20), under BOTH the 4- and
# 8-directional graph, 10 times per (heuristic, movement, N) triple.
#
# Movement used to be baked into which graph each heuristic ran on
# (Manhattan always 4-dir, Euclidean/Chebyshev always 8-dir), which
# confounded any speed or path-cost gap between heuristics with a
# difference in graph connectivity rather than heuristic quality. Movement
# is now a runtime switch (4th CLI arg, "diagonal" or omitted) so every
# heuristic runs on both graphs -- see astar_common.h and the individual
# algorithm files.
#
# That's 21 x 3 x 2 x 10 = 1260 heuristic runs total, written to
# results.csv with columns: heuristic,movement,n,run,time_ms,
# nodes_explored,path_cost.
#
# dijkstra is compiled too but NOT included in results.csv -- it's a
# ground-truth baseline (see validate_results.sh), not one of the three
# heuristics being compared. It's run once per (N, movement) into
# dijkstra.csv, since its path cost is deterministic under a fixed graph.
#
# The run index sits as the loop OUTSIDE the heuristic/movement loop on
# purpose: interleaving manhattan/euclidean/chebyshev x 4dir/8dir runs
# within each (N, run) pair spreads background OS/scheduler noise evenly
# across heuristics, instead of letting a noisy stretch of the machine's
# schedule land entirely inside one heuristic's block of runs.
#
# Usage: ./run_experiment.sh   (can be run from anywhere)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BIN_DIR="$ROOT_DIR/bin"
ALGO_DIR="$ROOT_DIR/algorithms"
TESTCASE_DIR="$ROOT_DIR/testcases"
RESULTS_DIR="$ROOT_DIR/results"
RESULTS_FILE="$RESULTS_DIR/results.csv"
DIJKSTRA_FILE="$RESULTS_DIR/dijkstra.csv"

RUNS_PER_CASE=10
N_MIN=0
N_MAX=20

ALL_BINARIES=("manhattan" "euclidean" "chebyshev" "dijkstra")
ALGORITHMS=("manhattan" "euclidean" "chebyshev")
MOVEMENTS=("" "diagonal")   # "" = 4-directional, "diagonal" = 8-directional

# 4GB memory ceiling per run (safety cap, not a requirement -- a 10x10 grid
# search uses a negligible amount of memory). Linux-only; no-ops on macOS.
MEM_LIMIT_KB=$((4 * 1024 * 1024))

echo "=== Compiling binaries ==="
mkdir -p "$BIN_DIR"
for algo in "${ALL_BINARIES[@]}"; do
    echo "Compiling $algo..."
    g++ -O2 -std=c++17 -I"$ROOT_DIR" -o "$BIN_DIR/$algo" "$ALGO_DIR/$algo.cpp"
done
echo "All binaries compiled."
echo ""

echo "=== Running experiment ==="
mkdir -p "$RESULTS_DIR"
echo "heuristic,movement,n,run,time_ms,nodes_explored,path_cost" > "$RESULTS_FILE"
echo "heuristic,movement,n,run,time_ms,nodes_explored,path_cost" > "$DIJKSTRA_FILE"

total_runs=$(( (N_MAX - N_MIN + 1) * ${#ALGORITHMS[@]} * ${#MOVEMENTS[@]} * RUNS_PER_CASE ))
completed=0

for n in $(seq "$N_MIN" "$N_MAX"); do
    testcase_file="$TESTCASE_DIR/testcase_n_${n}.txt"

    if [[ ! -f "$testcase_file" ]]; then
        echo "WARNING: missing test case file $testcase_file, skipping N=$n"
        continue
    fi

    for run in $(seq 1 "$RUNS_PER_CASE"); do
        for algo in "${ALGORITHMS[@]}"; do
            bin="$BIN_DIR/$algo"

            for movement in "${MOVEMENTS[@]}"; do
                (
                    ulimit -v "$MEM_LIMIT_KB" 2>/dev/null || true
                    "$bin" "$testcase_file" "$n" "$run" $movement
                ) >> "$RESULTS_FILE"

                completed=$((completed + 1))
            done
        done
    done

    # Dijkstra baselines are deterministic per (N, movement), so one run
    # each is enough -- see validate_results.sh for how these are used.
    for movement in "${MOVEMENTS[@]}"; do
        (
            ulimit -v "$MEM_LIMIT_KB" 2>/dev/null || true
            "$BIN_DIR/dijkstra" "$testcase_file" "$n" 1 $movement
        ) >> "$DIJKSTRA_FILE"
    done

    echo "Completed N=$n  ($completed / $total_runs heuristic runs so far)"
done

echo ""
echo "=== Done ==="
echo "Total heuristic runs: $completed"
echo "Results written to: $RESULTS_FILE"
echo "Dijkstra baselines written to: $DIJKSTRA_FILE"
