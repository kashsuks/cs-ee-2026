#!/bin/bash
# validate_results.sh
#
# Runs Dijkstra's algorithm as a ground-truth baseline against each of the
# 21 test cases -- but now in TWO modes, since Manhattan runs 4-directional
# while Euclidean and Chebyshev run 8-directional, so "optimal" means a
# different number for each group:
#
#   4-directional baseline -> validates Manhattan
#   8-directional baseline -> validates Euclidean and Chebyshev
#
# For every heuristic, at every N, this checks:
#   1. OPTIMAL     -- did the heuristic's path cost match the baseline that
#                      matches ITS OWN movement rule?
#   2. CONSISTENT  -- did all 10 repeated runs of that heuristic on that
#                      same test case return the same path cost?
#
# Output: validation_report.csv, one row per (n, algorithm) pair, plus a
# plain-text summary printed to the terminal.
#
# Usage: ./validate_results.sh [path/to/results.csv]
#   (defaults to results/results.csv if no argument is given)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BIN_DIR="$ROOT_DIR/bin"
ALGO_DIR="$ROOT_DIR/algorithms"
TESTCASE_DIR="$ROOT_DIR/testcases"
RESULTS_DIR="$ROOT_DIR/results"
RESULTS_FILE="${1:-$RESULTS_DIR/results.csv}"
DIJKSTRA_4DIR_FILE="$RESULTS_DIR/dijkstra_baseline_4dir.csv"
DIJKSTRA_8DIR_FILE="$RESULTS_DIR/dijkstra_baseline_8dir.csv"
REPORT_FILE="$RESULTS_DIR/validation_report.csv"

N_MIN=0
N_MAX=20

if [[ ! -f "$RESULTS_FILE" ]]; then
    echo "ERROR: results file not found at $RESULTS_FILE"
    echo "Pass its path explicitly: ./validate_results.sh path/to/results.csv"
    exit 1
fi

if [[ ! -x "$BIN_DIR/dijkstra" ]]; then
    echo "dijkstra binary not found, compiling it now..."
    mkdir -p "$BIN_DIR"
    g++ -O2 -std=c++17 -I"$ROOT_DIR" -o "$BIN_DIR/dijkstra" "$ALGO_DIR/dijkstra.cpp"
fi

echo "=== Running Dijkstra baselines (4-dir for Manhattan, 8-dir for Euclidean/Chebyshev) ==="
mkdir -p "$RESULTS_DIR"
echo "algorithm,n,run,time_ms,nodes_explored,path_cost" > "$DIJKSTRA_4DIR_FILE"
echo "algorithm,n,run,time_ms,nodes_explored,path_cost" > "$DIJKSTRA_8DIR_FILE"

for n in $(seq "$N_MIN" "$N_MAX"); do
    testcase_file="$TESTCASE_DIR/testcase_n_${n}.txt"
    if [[ ! -f "$testcase_file" ]]; then
        echo "WARNING: missing test case file $testcase_file, skipping N=$n"
        continue
    fi
    # path cost is deterministic per mode, so one run per N per mode is enough
    "$BIN_DIR/dijkstra" "$testcase_file" "$n" 1 >> "$DIJKSTRA_4DIR_FILE"
    "$BIN_DIR/dijkstra" "$testcase_file" "$n" 1 diagonal >> "$DIJKSTRA_8DIR_FILE"
done
echo "Baselines written to $DIJKSTRA_4DIR_FILE and $DIJKSTRA_8DIR_FILE"
echo ""

echo "=== Cross-checking $RESULTS_FILE against the matching baseline ==="
awk -F',' '
    # pass 1: 4-dir baseline (this file)
    FNR==NR {
        if (FNR == 1) next
        optimal_4dir[$2] = $6
        next
    }
    # pass 2: 8-dir baseline
    FILENAME=="'"$DIJKSTRA_8DIR_FILE"'" {
        if (FNR == 1) next
        optimal_8dir[$2] = $6
        next
    }
    # pass 3: results.csv
    FILENAME=="'"$RESULTS_FILE"'" {
        if (FNR == 1) next
        algo = $1; n = $2; cost = $6
        key = algo SUBSEP n
        if (!(key in seen)) {
            seen[key] = 1
            min_cost[key] = cost
            max_cost[key] = cost
            all_keys[key] = 1
        } else {
            if (cost < min_cost[key]) min_cost[key] = cost
            if (cost > max_cost[key]) max_cost[key] = cost
        }
    }

    END {
        print "n,algorithm,algorithm_cost,expected_optimal_cost,movement_rule,is_optimal,is_consistent" > "'"$REPORT_FILE"'"

        total = 0
        optimal_count = 0
        consistent_count = 0

        for (key in all_keys) {
            split(key, parts, SUBSEP)
            algo = parts[1]
            n = parts[2]

            lo = min_cost[key]
            hi = max_cost[key]

            if (algo == "manhattan") {
                dcost = (n in optimal_4dir) ? optimal_4dir[n] : "NA"
                rule = "4-directional"
            } else {
                dcost = (n in optimal_8dir) ? optimal_8dir[n] : "NA"
                rule = "8-directional"
            }

            is_consistent = (lo == hi) ? "yes" : "no"
            is_optimal = (dcost != "NA" && lo == dcost) ? "yes" : "no"

            print n","algo","lo","dcost","rule","is_optimal","is_consistent >> "'"$REPORT_FILE"'"

            total++
            if (is_optimal == "yes") optimal_count++
            if (is_consistent == "yes") consistent_count++

            if (is_optimal == "no") {
                printf "  MISMATCH: N=%s %s (%s) found cost %s, expected %s\n", n, algo, rule, lo, dcost
            }
            if (is_consistent == "no") {
                printf "  INCONSISTENT: N=%s %s returned costs ranging %s-%s across its 10 runs\n", n, algo, lo, hi
            }
        }

        print ""
        print "=== Summary ==="
        printf "Total (n, algorithm) pairs checked: %d\n", total
        printf "Found the optimal path (under their own movement rule): %d / %d\n", optimal_count, total
        printf "Consistent across all 10 runs: %d / %d\n", consistent_count, total
    }
' "$DIJKSTRA_4DIR_FILE" "$DIJKSTRA_8DIR_FILE" "$RESULTS_FILE"

# sort the report numerically by n, then by algorithm (header stays on top)
{
    head -n 1 "$REPORT_FILE"
    tail -n +2 "$REPORT_FILE" | sort -t',' -k1,1n -k2,2
} > "${REPORT_FILE}.sorted" && mv "${REPORT_FILE}.sorted" "$REPORT_FILE"

echo ""
echo "Full report written to: $REPORT_FILE"