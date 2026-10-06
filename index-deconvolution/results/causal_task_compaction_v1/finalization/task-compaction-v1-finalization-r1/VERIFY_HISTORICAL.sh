#!/bin/zsh
# task-compaction-v1 finalization -- ONE command verifying the SAVED v1 evidence against its
# HISTORICAL identities. Reads only; writes into a fresh destination.
#   1. the immutable historical_inputs snapshot equals its manifest and the original freeze;
#   2. audit_r3 on the original production with --inputs-root historical_inputs must be
#      VALID_COMPLETE, and its deterministic audit.json byte-identical to the saved one;
#   3. the run-local audit tests (r3 8, r2 7, frozen 5) pass.
# Timings go to stdout only; the deterministic output is <dest>/audit/audit.json.
# Usage: zsh VERIFY_HISTORICAL.sh <fresh destination directory>
set -eu
FIN=${0:A:h}
REPO=${FIN:h:h:h:h:h}
B=${FIN:h:h}
DEST=${1:?destination required}
[[ -e $DEST ]] && { echo "refusing: $DEST exists"; exit 2 }
export PYTHONDONTWRITEBYTECODE=1
unset PYTHONPATH
PY=$REPO/venv/bin/python
mkdir -p $DEST
$PY - $FIN $B <<'PYEOF'
import hashlib, json, os, sys
fin, b = sys.argv[1], sys.argv[2]
m = json.load(open(os.path.join(fin, "historical_inputs_manifest.json")))["files"]
fz = json.load(open(os.path.join(b, "task-compaction-v1-r1", "freeze.json")))["inputs"]
root = os.path.join(fin, "historical_inputs")
have = sorted(os.path.relpath(os.path.join(d, f), root) for d, _, fs in os.walk(root) for f in fs)
bad = [k for k in fz if k not in m or hashlib.sha256(open(os.path.join(root, k), "rb").read()).hexdigest() != fz[k]]
ok = have == sorted(fz) == sorted(m) and not bad and len(fz) > 0
print(f"historical snapshot: {len(have)} files, {len(fz)} declared by the original freeze, mismatches {bad}")
sys.exit(0 if ok else 1)
PYEOF
( cd /tmp && $PY $FIN/src/audit_r3.py $B/task-compaction-v1-r1/production $DEST/audit --inputs-root $FIN/historical_inputs )
cmp $DEST/audit/audit.json $FIN/audit/post_adoption_historical_root/audit.json && echo "audit.json byte-identical to the saved historical-root audit"
( cd /tmp && $PY -m pytest -q -p no:cacheprovider -c /dev/null --rootdir=/tmp $FIN/tests/test_audit_r3.py \
    $B/review_closure/task-compaction-v1-r1/tests/test_audit_r2.py $B/task-compaction-v1-r1/tests/test_audit_labels.py )
