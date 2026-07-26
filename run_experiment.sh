#!/bin/bash
# run_experiment.sh
#
# Compiles manhattan.cpp, euclidean.cpp, chebyshev.cpp, dijkstra.cpp (all at
# repo root, sharing helpers/astar_common.h) and runs the three HEURISTIC
# binaries -- manhattan, euclidean, chebyshev -- against every test case
# (N = 0 to 20), 20 times per (algorithm, N) pair, one run after another.
# That's 21 x 3 x 20 = 1260 runs total. Every single run is logged as its
# own row in results.csv: algorithm, N, run index, time in ms, nodes
# explored, and path cost.
#
# dijkstra is compiled too but NOT included in the main loop -- it's a plain
# shortest-path baseline (h(n) = 0), not one of the three heuristics being
# compared. Run it manually if you want an optimality check, e.g.:
#   ./bin/dijkstra testcases/testcase_n_5.txt 5 1
#
# Usage: ./run_experiment.sh   (run from the cs-ee-2026 root)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
TESTCASE_DIR="$SCRIPT_DIR/testcases"
RESULTS_FILE="$SCRIPT_DIR/results.csv"

RUNS_PER_CASE=20
N_MIN=0
N_MAX=20

# all binaries that need to be compiled (source files live at repo root)
ALL_BINARIES=("manhattan" "euclidean" "chebyshev" "dijkstra")

# only these run as part of the main experiment (dijkstra is a baseline,
# run separately if needed -- see note above)
ALGORITHMS=("manhattan" "euclidean" "chebyshev")

# 4GB memory ceiling per run, expressed in KB for ulimit -v.
# This is a safety cap, not a requirement -- a 10x10 grid search uses a
# negligible amount of memory, so this just guards against runaway behaviour.
# Note: ulimit -v is Linux-only; on macOS this silently no-ops.
MEM_LIMIT_KB=$((4 * 1024 * 1024))

echo "=== Compiling binaries ==="
mkdir -p "$BIN_DIR"
for algo in "${ALL_BINARIES[@]}"; do
    echo "Compiling $algo..."
    g++ -O2 -std=c++17 -o "$BIN_DIR/$algo" "$SCRIPT_DIR/$algo.cpp"
done
echo "All binaries compiled."
echo ""

echo "=== Running experiment ==="
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

        # same test case run RUNS_PER_CASE times in a row, one after another,
        # so timing noise from one run doesn't bleed into a different N or algorithm
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
