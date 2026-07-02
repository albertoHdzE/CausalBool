#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"
STEP="${1:-help}"

ensure_venv() {
  if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "[run.sh] creating Python 3.11 virtual environment"
    PYENV_VERSION=3.11.10 pyenv exec python -m venv "$VENV_DIR"
  fi
}

ensure_deps() {
  ensure_venv
  "$PIP_BIN" install --upgrade pip 'setuptools<81'
  "$PIP_BIN" install -r "$ROOT_DIR/requirements.txt"
  "$PIP_BIN" install -e "$ROOT_DIR"
}

case "$STEP" in
  setup)
    ensure_deps
    ;;
  test)
    ensure_deps
    "$PYTHON_BIN" -m pytest
    ;;
  graphs)
    ensure_deps
    "$PYTHON_BIN" -m imp_causal_paper.cli graphs --output-dir "$ROOT_DIR/results/graphs" --plots-dir "$ROOT_DIR/plots/graphs"
    ;;
  ca)
    ensure_deps
    "$PYTHON_BIN" -m imp_causal_paper.cli ca --output-dir "$ROOT_DIR/results/ca" --plots-dir "$ROOT_DIR/plots/ca"
    ;;
  boolean)
    ensure_deps
    "$PYTHON_BIN" -m imp_causal_paper.cli boolean --output-dir "$ROOT_DIR/results/boolean" --plots-dir "$ROOT_DIR/plots/boolean"
    ;;
  th17)
    ensure_deps
    "$PYTHON_BIN" -m imp_causal_paper.cli th17-prepare --raw-dir "$ROOT_DIR/data/raw/th17_geo" --supp-dir "$ROOT_DIR/data/raw/th17_geo_supp" --output-dir "$ROOT_DIR/data/processed/th17"
    ;;
  all)
    ensure_deps
    "$PYTHON_BIN" -m imp_causal_paper.cli all --output-dir "$ROOT_DIR/results" --plots-dir "$ROOT_DIR/plots"
    ;;
  help|--help|-h)
    cat <<'EOF'
Usage: ./run.sh <step>

Steps:
  setup    Create or update the isolated virtual environment and install dependencies
  test     Run the full correctness and integration test suite
  graphs   Run graph perturbation, MILS, MARPA, and reprogrammability experiments
  ca       Run the cellular automaton reconstruction experiment
  boolean  Run Boolean-network perturbation experiments
  th17     Parse public Th17 array and perturbation RNA-seq assets into processed tables
  all      Run every experiment and write outputs under results/
EOF
    ;;
  *)
    echo "Unknown step: $STEP" >&2
    exit 1
    ;;
esac
