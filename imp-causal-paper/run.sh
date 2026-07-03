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
    echo "[run.sh] virtual environment created successfully"
  else
    echo "[run.sh] using existing virtual environment at $VENV_DIR"
  fi
}

ensure_deps() {
  ensure_venv
  
  echo "[run.sh] upgrading pip and setuptools"
  "$PIP_BIN" install --upgrade pip 'setuptools<81'
  
  echo "[run.sh] installing dependencies from requirements.txt"
  "$PIP_BIN" install -r "$ROOT_DIR/requirements.txt"
  
  echo "[run.sh] installing project in editable mode"
  "$PIP_BIN" install -e "$ROOT_DIR"
  
  echo "[run.sh] installing IPython kernel for Jupyter"
  "$PYTHON_BIN" -m ipykernel install \
    --prefix "$VENV_DIR" \
    --name "imp-causal-paper" \
    --display-name "Python (.venv imp-causal-paper)" \
    >/dev/null
  echo "[run.sh] dependencies and environment setup complete"
}

case "$STEP" in
  setup)
    echo "[run.sh] starting setup step"
    ensure_deps
    echo "[run.sh] setup step completed successfully"
    ;;
  test)
    echo "[run.sh] starting test step"
    ensure_deps
    echo "[run.sh] running pytest test suite"
    "$PYTHON_BIN" -m pytest
    echo "[run.sh] test step completed successfully"
    ;;
  graphs)
    echo "[run.sh] starting graphs experiment step"
    ensure_deps
    echo "[run.sh] running graph perturbation, MILS, MARPA, and reprogrammability experiments"
    "$PYTHON_BIN" -m imp_causal_paper.cli graphs --output-dir "$ROOT_DIR/results/graphs" --plots-dir "$ROOT_DIR/plots/graphs"
    echo "[run.sh] graphs experiment step completed successfully"
    ;;
  ca)
    echo "[run.sh] starting cellular automaton experiment step"
    ensure_deps
    echo "[run.sh] running cellular automaton reconstruction experiment"
    "$PYTHON_BIN" -m imp_causal_paper.cli ca --output-dir "$ROOT_DIR/results/ca" --plots-dir "$ROOT_DIR/plots/ca"
    echo "[run.sh] cellular automaton experiment step completed successfully"
    ;;
  boolean)
    echo "[run.sh] starting Boolean network experiment step"
    ensure_deps
    echo "[run.sh] running Boolean-network perturbation experiments"
    "$PYTHON_BIN" -m imp_causal_paper.cli boolean --output-dir "$ROOT_DIR/results/boolean" --plots-dir "$ROOT_DIR/plots/boolean"
    echo "[run.sh] Boolean network experiment step completed successfully"
    ;;
  th17)
    echo "[run.sh] starting Th17 data processing step"
    ensure_deps
    echo "[run.sh] parsing public Th17 array and perturbation RNA-seq assets"
    "$PYTHON_BIN" -m imp_causal_paper.cli th17-prepare --raw-dir "$ROOT_DIR/data/raw/th17_geo" --supp-dir "$ROOT_DIR/data/raw/th17_geo_supp" --output-dir "$ROOT_DIR/data/processed/th17"
    echo "[run.sh] Th17 data processing step completed successfully"
    ;;
  yosef-perturb)
    echo "[run.sh] starting Yosef Th17 BDM perturbation step"
    ensure_deps
    echo "[run.sh] running BDM node perturbation on EarlyNet/IntermediateNet/FinalNet with per-network ordering"
    "$PYTHON_BIN" "$ROOT_DIR/scripts/run_yosef_perturbation.py"
    echo "[run.sh] Yosef Th17 BDM perturbation step completed successfully"
    ;;
  ecoli)
    echo "[run.sh] starting E. coli BDM perturbation step"
    ensure_deps
    echo "[run.sh] parsing RegulonDB network and running BDM node perturbation"
    CONFIDENCE="${2:-C}"
    "$PYTHON_BIN" "$ROOT_DIR/scripts/run_ecoli_perturbation.py" --confidence "$CONFIDENCE"
    echo "[run.sh] E. coli BDM perturbation step completed successfully"
    ;;
  cellnet)
    echo "[run.sh] starting CellNet Waddington landscape step"
    ensure_deps
    echo "[run.sh] step 1: extract GRN edge lists from grnAll RDA files (requires Rscript + igraph)"
    Rscript "$ROOT_DIR/scripts/extract_cellnet_grns.R" "$ROOT_DIR"
    echo "[run.sh] step 2: compute BDM complexity and reprogrammability"
    NODE_LIMIT="${2:-1000}"
    "$PYTHON_BIN" "$ROOT_DIR/scripts/run_cellnet_complexity.py" --node-limit "$NODE_LIMIT"
    echo "[run.sh] CellNet Waddington landscape step completed successfully"
    ;;
  all)
    echo "[run.sh] starting full experiment suite"
    ensure_deps
    echo "[run.sh] running all experiments"
    "$PYTHON_BIN" -m imp_causal_paper.cli all --output-dir "$ROOT_DIR/results" --plots-dir "$ROOT_DIR/plots"
    echo "[run.sh] all experiments completed successfully"
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
  th17           Parse public Th17 array and perturbation RNA-seq assets into processed tables
  yosef-perturb  Run BDM node perturbation on EarlyNet/IntermediateNet/FinalNet (per-network ordering)
  ecoli [C|CS|all]  Run BDM node perturbation on RegulonDB E. coli TF->gene network
  cellnet [N]    Extract CellNet GRNs and compute BDM landscape (node-limit N, default 1000)
  all            Run every experiment and write outputs under results/
EOF
    ;;
  *)
    echo "Unknown step: $STEP" >&2
    exit 1
    ;;
esac
