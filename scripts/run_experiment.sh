#!/bin/bash
# run_experiment.sh
#
# Compiles manhattan.cpp, euclidean.cpp, chebyshev.cpp, dijkstra.cpp (all in
# algorithms/, sharing helpers/astar_common.h) and runs the three HEURISTIC
# binaries against every test case (N = 0 to 20), 10 times per (algorithm, N)
# pair, one run after another. That's 21 x 3 x 10 = 630 runs total.
#
# Each heuristic now runs under the movement rule its own formula assumes:
#   manhattan  -> 4-directional
#   euclidean  -> 8-directional
#   chebyshev  -> 8-directional
# This is handled internally by each binary -- nothing to configure here.
#
# Every run is logged as its own row in results.csv: algorithm, N, run
# index, time in ms, nodes explored, and path cost.
#
# dijkstra is compiled too but NOT included in the main loop -- it's a
# validation baseline (see validate_results.sh), not one of the three
# heuristics being compared.
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

RUNS_PER_CASE=10
N_MIN=0
N_MAX=20

ALL_BINARIES=("manhattan" "euclidean" "chebyshev" "dijkstra")
ALGORITHMS=("manhattan" "euclidean" "chebyshev")

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
echo "algorithm,n,run,time_ms,nodes_explored,path_cost" > "$RESULTS_FILE"

total_runs=$(( (N_MAX - N_MIN + 1) * ${#ALGORITHMS[@]} * RUNS_PER_CASE ))
completed=0

for n in $(seq "$N_MIN" "$N_MAX"); do
    testcase_file="$TESTCASE_DIR/testcase_n_${n}.txt"

    if [[ ! -f "$testcase_file" ]]; then
        echo "WARNING: missing test case file $testcase_file, skipping N=$n"
        continue
    fi

    for algo in "${ALGORITHMS[@]}"; do
        bin="$BIN_DIR/$algo"

        for run in $(seq 1 "$RUNS_PER_CASE"); do
            (
                ulimit -v "$MEM_LIMIT_KB" 2>/dev/null || true
                "$bin" "$testcase_file" "$n" "$run"
            ) >> "$RESULTS_FILE"

            completed=$((completed + 1))
        done
    done

    echo "Completed N=$n  ($completed / $total_runs runs so far)"
done

echo ""
echo "=== Done ==="
echo "Total runs: $completed"
echo "Results written to: $RESULTS_FILE"