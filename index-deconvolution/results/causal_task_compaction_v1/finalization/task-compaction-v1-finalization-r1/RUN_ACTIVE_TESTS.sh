#!/bin/zsh
# task-compaction-v1 finalization -- ONE command for the scoped ACTIVE tests:
# 73 accepted regressions + 52 owner tests (125) and the TASK_COMPACTION_V1.md examples,
# against the active owner. No result directory is needed; root collection is not involved
# (empty configuration, local rootdir). Writes nothing (no bytecode, no pytest cache).
# Usage: zsh RUN_ACTIVE_TESTS.sh
set -eu
REPO=${0:A:h:h:h:h:h:h}
export PYTHONDONTWRITEBYTECODE=1
unset PYTHONPATH
cd $REPO/index-deconvolution
$REPO/venv/bin/python -m pytest -q -p no:cacheprovider -c /dev/null --rootdir=. \
    tests/test_deconvolution.py tests/test_abstraction.py \
    results/causal_abstraction_validation/abstraction-validation-v1-r1-source-r2/test_study.py \
    tests/test_task_compaction.py
$REPO/venv/bin/python -m doctest TASK_COMPACTION_V1.md && echo "TASK_COMPACTION_V1.md examples: pass"
