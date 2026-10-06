#!/bin/zsh
# task-compaction-v1-r1 -- reproduce every deterministic scientific output into a FRESH directory.
# Usage: zsh run.sh <fresh destination directory>
# Uses only delivered sources: isolated/ (owner revision, adopted study, mirrored inputs) and src/.
set -eu
RUN=${0:A:h}
REPO=${RUN:h:h:h:h}
DEST=${1:?destination required}
[[ -e $DEST ]] && { echo "refusing: $DEST exists"; exit 2 }
export PYTHONDONTWRITEBYTECODE=1
unset PYTHONPATH
PY=$REPO/venv/bin/python
mkdir -p $DEST
$PY $RUN/src/freeze.py verify $DEST/freeze_verify.json
$PY $RUN/src/produce.py $DEST/production
$PY $RUN/src/audit.py $DEST/production $DEST/audit
