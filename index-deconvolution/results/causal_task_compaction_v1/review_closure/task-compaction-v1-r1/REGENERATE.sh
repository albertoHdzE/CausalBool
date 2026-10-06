#!/bin/zsh
# task-compaction-v1-r1 review closure -- regenerate the closure evidence from SAVED inputs only.
# No produce.py and no M1-M4 minimization; the original run directory is only read.
# Usage: zsh REGENERATE.sh <fresh destination directory>
set -eu
CL=${0:A:h}
REPO=${CL:h:h:h:h:h}
ORIG=${CL:h:h}/task-compaction-v1-r1
DEST=${1:?destination required}
[[ -e $DEST ]] && { echo "refusing: $DEST exists"; exit 2 }
export PYTHONDONTWRITEBYTECODE=1
unset PYTHONPATH
PY=$REPO/venv/bin/python
mkdir -p $DEST
$PY $CL/src/audit_r2.py $ORIG/production $DEST/audit                       # saved-data audit
$PY $CL/src/probe_matrix.py $DEST/matrix_scratch $DEST/matrix              # R1 items 1-10 on copies
cp -Rp $CL/isolated $DEST/layout                                           # layout without the run folder
[[ ! -e $DEST/layout/index-deconvolution/results/causal_task_compaction_v1 ]]
( cd $DEST/layout/index-deconvolution && $PY -m pytest -q -p no:cacheprovider \
    tests/test_deconvolution.py tests/test_abstraction.py \
    results/causal_abstraction_validation/abstraction-validation-v1-r1-source-r2/test_study.py \
    tests/test_task_compaction.py ) > $DEST/pytest_layout.log
( cd /tmp && $PY -m pytest -q -p no:cacheprovider $CL/tests/test_audit_r2.py $ORIG/tests/test_audit_labels.py ) > $DEST/pytest_run_local.log
$PY $CL/src/owner_check_r2.py > $DEST/owner_check.json
( cd $REPO && git apply --check $CL/patches/*.patch ) && echo "patches apply --check: ok" > $DEST/patch_check.log
tail -1 $DEST/pytest_layout.log $DEST/pytest_run_local.log
