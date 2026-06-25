#!/usr/bin/env bash
# run_all.sh — CausalBool companion code, master runner
#
# Runs all three experiments in order.
# Requires: Wolfram (for .wl scripts) and Python 3 (for .py scripts)
#
# Usage:
#   bash run_all.sh
#   WOLFRAM=wolframscript bash run_all.sh
#   WOLFRAM=/Applications/Wolfram.app/Contents/MacOS/WolframKernel bash run_all.sh
#   PYTHON=python3.11 bash run_all.sh

set -euo pipefail

WOLFRAM="${WOLFRAM:-wolframscript}"
PYTHON="${PYTHON:-python3}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_wl() {
    local script="$1"
    local name
    name="$(basename "$script")"
    echo "    [wl]  $name"
    if command -v "$WOLFRAM" &>/dev/null || [[ -x "$WOLFRAM" ]]; then
        "$WOLFRAM" -file "$script"
    else
        echo "    SKIP: Wolfram command not found ('$WOLFRAM'). Set WOLFRAM env var to proceed."
    fi
}

run_py() {
    local script="$1"
    local name
    name="$(basename "$script")"
    echo "    [py]  $name"
    "$PYTHON" "$script"
}

echo "================================================================="
echo "  CausalBool companion code — reproducibility suite"
echo "================================================================="

echo ""
echo "--- Experiment 1: 6-node corroboration ---"
run_wl "$ROOT/corroboration_6node/corroboration_6node.wl"
run_wl "$ROOT/corroboration_6node/ordering_invariance_6node.wl"
run_py "$ROOT/corroboration_6node/ordering_invariance_6node.py"

echo ""
echo "--- Experiment 2: 10-node mixed interaction ---"
run_wl "$ROOT/mixed_interaction_10node/mixed_interaction_10node.wl"
run_wl "$ROOT/mixed_interaction_10node/dynamical_landscape_10node.wl"
run_py "$ROOT/mixed_interaction_10node/dynamical_landscape_10node.py"

echo ""
echo "--- Experiment 3: Scalability resource envelope ---"
run_py "$ROOT/scalability_resource_envelope/scalability_resource_envelope.py"

echo ""
echo "================================================================="
echo "  All experiments completed."
echo "================================================================="
