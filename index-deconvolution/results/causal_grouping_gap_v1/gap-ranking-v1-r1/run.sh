#!/bin/zsh
# gap-ranking-v1-r1 -- reproduce the production, join and audit into a FRESH destination.
# Usage (from anywhere): zsh run.sh <fresh destination directory>
# Uses only the delivered sources in this run directory (src/, dependency/isolated/src).
set -eu
RUN=${0:A:h}
REPO=${RUN:h:h:h:h}
DEST=${1:?destination required}
[[ -e $DEST ]] && { echo "refusing: $DEST exists"; exit 2 }
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$REPO/index-deconvolution/src:$REPO/index-deconvolution/results/causal_abstraction_validation/abstraction-validation-v1-r1-source-r2:$RUN/dependency/isolated/src"
PY=$REPO/venv/bin/python
$PY $RUN/src/produce.py $DEST/production
$PY $RUN/src/join.py $DEST/production
$PY $RUN/src/audit.py $DEST/production $DEST/audit
