#!/bin/bash
# validate_results.sh
#
# Runs Dijkstra's algorithm (h(n) = 0, guaranteed optimal) once against each
# of the 21 test cases to establish the true shortest path cost for each N.
# Then cross-checks that baseline against results.csv (produced by
# run_experiment.sh) to confirm two things for every heuristic, at every N:
#
#   1. OPTIMAL   -- did the heuristic's path cost match Dijkstra's true
#                   shortest path cost? (if not, the heuristic found a
#                   suboptimal path, which matters most for chebyshev since
#                   it is not admissible on a 4-directional-only grid)
#   2. CONSISTENT -- did all 20 repeated runs of that heuristic on that same
#                    test case return the same path cost? (A* is
#                    deterministic given a fixed graph, so any variation
#                    here would indicate a bug, not real randomness)
#
# Output: validation_report.csv, one row per (n, algorithm) pair, plus a
# plain-text summary printed to the terminal.
#
# Usage: ./validate_results.sh [path/to/results.csv]
#   (defaults to ./results.csv if no argument is given)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
TESTCASE_DIR="$SCRIPT_DIR/testcases"
RESULTS_FILE="${1:-$SCRIPT_DIR/results.csv}"
DIJKSTRA_BASELINE_FILE="$SCRIPT_DIR/dijkstra_baseline.csv"
REPORT_FILE="$SCRIPT_DIR/validation_report.csv"

N_MIN=0
N_MAX=20

if [[ ! -f "$RESULTS_FILE" ]]; then
    echo "ERROR: results file not found at $RESULTS_FILE"
    echo "Pass its path explicitly: ./validate_results.sh path/to/results.csv"
    exit 1
fi

# make sure dijkstra is compiled
if [[ ! -x "$BIN_DIR/dijkstra" ]]; then
    echo "dijkstra binary not found, compiling it now..."
    mkdir -p "$BIN_DIR"
    g++ -O2 -std=c++17 -o "$BIN_DIR/dijkstra" "$SCRIPT_DIR/dijkstra.cpp"
fi

echo "=== Running Dijkstra baseline (ground truth optimal cost per N) ==="
echo "algorithm,n,run,time_ms,nodes_explored,path_cost" > "$DIJKSTRA_BASELINE_FILE"

for n in $(seq "$N_MIN" "$N_MAX"); do
    testcase_file="$TESTCASE_DIR/testcase_n_${n}.txt"
    if [[ ! -f "$testcase_file" ]]; then
        echo "WARNING: missing test case file $testcase_file, skipping N=$n"
        continue
    fi
    # Dijkstra's path cost is deterministic, so one run per N is sufficient
    # -- this is a correctness baseline, not a timing benchmark.
    "$BIN_DIR/dijkstra" "$testcase_file" "$n" 1 >> "$DIJKSTRA_BASELINE_FILE"
done
echo "Baseline written to $DIJKSTRA_BASELINE_FILE"
echo ""

echo "=== Cross-checking $RESULTS_FILE against the baseline ==="
awk -F',' '
    # --- pass 1: read the dijkstra baseline into optimal_cost[n] ---
    FNR==NR {
        if (FNR == 1) next  # skip header
        n = $2
        cost = $6
        optimal_cost[n] = cost
        next
    }

    # --- pass 2: read results.csv, grouping by (algorithm, n) ---
    FNR==1 { next }  # skip header of results.csv
    {
        algo = $1
        n = $2
        cost = $6
        key = algo SUBSEP n

        if (!(key in seen)) {
            seen[key] = 1
            min_cost[key] = cost
            max_cost[key] = cost
            algos_by_n[n] = algos_by_n[n] " " algo
            all_ns[n] = 1
            all_keys[key] = 1
        } else {
            if (cost < min_cost[key]) min_cost[key] = cost
            if (cost > max_cost[key]) max_cost[key] = cost
        }
    }

    END {
        print "n,algorithm,algorithm_cost,dijkstra_optimal_cost,is_optimal,is_consistent" > "'"$REPORT_FILE"'"

        total = 0
        optimal_count = 0
        consistent_count = 0

        for (key in all_keys) {
            split(key, parts, SUBSEP)
            algo = parts[1]
            n = parts[2]

            lo = min_cost[key]
            hi = max_cost[key]
            dcost = (n in optimal_cost) ? optimal_cost[n] : "NA"

            is_consistent = (lo == hi) ? "yes" : "no"
            is_optimal = (dcost != "NA" && lo == dcost) ? "yes" : "no"

            print n","algo","lo","dcost","is_optimal","is_consistent >> "'"$REPORT_FILE"'"

            total++
            if (is_optimal == "yes") optimal_count++
            if (is_consistent == "yes") consistent_count++

            if (is_optimal == "no") {
                printf "  MISMATCH: N=%s %s found cost %s, optimal is %s\n", n, algo, lo, dcost
            }
            if (is_consistent == "no") {
                printf "  INCONSISTENT: N=%s %s returned costs ranging %s-%s across its 20 runs\n", n, algo, lo, hi
            }
        }

        print ""
        print "=== Summary ==="
        printf "Total (n, algorithm) pairs checked: %d\n", total
        printf "Found the optimal path: %d / %d\n", optimal_count, total
        printf "Consistent across all 20 runs: %d / %d\n", consistent_count, total
    }
' "$DIJKSTRA_BASELINE_FILE" "$RESULTS_FILE"

# sort the report numerically by n, then by algorithm (header stays on top)
{
    head -n 1 "$REPORT_FILE"
    tail -n +2 "$REPORT_FILE" | sort -t',' -k1,1n -k2,2
} > "${REPORT_FILE}.sorted" && mv "${REPORT_FILE}.sorted" "$REPORT_FILE"

echo ""
echo "Full report written to: $REPORT_FILE"
