#!/bin/zsh
# task-compaction-v1 final audit closure -- ONE command verifying the SAVED v1 evidence with audit
# revision r4 against its HISTORICAL identities. It does NOT replace or extend VERIFY_HISTORICAL.sh
# (r3), whose checks are unchanged. Reads only; writes into a fresh destination.
#   1. the immutable finalization historical_inputs snapshot equals its manifest and the original freeze;
#   2. audit_r4 on the original production with --inputs-root historical_inputs must be
#      VALID_COMPLETE, with 60/60 seal entries agreeing with the pinned authority, 60 hashes compared
#      and the FX1 fixture's two certificate checks completed; its deterministic audit.json must be
#      byte-identical to the saved one;
#   3. the run-local tests (r4 9, r3 8, r2 7, frozen 5) pass.
# Usage: zsh VERIFY_R4.sh <fresh destination directory>      (any working directory)
set -eu
RUN=${0:A:h}
REPO=${RUN:h:h:h:h:h}
B=${RUN:h:h}
FIN=$B/finalization/task-compaction-v1-finalization-r1
DEST=${1:?destination required}
[[ -e $DEST ]] && { echo "refusing: $DEST exists"; exit 2 }
export PYTHONDONTWRITEBYTECODE=1
unset PYTHONPATH
PY=$REPO/venv/bin/python
mkdir -p $DEST
DEST=${DEST:A}
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
( cd /tmp && $PY $RUN/src/audit_r4.py $B/task-compaction-v1-r1/production $DEST/audit --inputs-root $FIN/historical_inputs )
$PY - $DEST/audit/audit.json <<'PYEOF'
import json, sys
a = json.load(open(sys.argv[1]))
i, f = a["integrity"], a["fixture_FX1"]
print(f"seal: intended {i['intended_entries']}, candidate entries agreeing {i['candidate_entries_agreeing']}, "
      f"hashes compared {i['hashes_compared']}, mismatches {len(i['hash_mismatch'])}; "
      f"FX1: intended {f['intended']}, certificate checks {f['certificate_checks_completed']}/2, "
      f"validity {f['validity']}, minimality {f['minimality']}")
ok = (a["audit_revision"] == "r4" and a["status"] == "VALID_COMPLETE" and i["intended_entries"] == 60
      and i["candidate_entries_agreeing"] == 60 and i["hashes_compared"] == 60 and not i["hash_mismatch"]
      and f["certificate_checks_completed"] == 2 and f["validity"] is True and f["minimality"] is True)
sys.exit(0 if ok else 1)
PYEOF
cmp $DEST/audit/audit.json $RUN/audit/historical_root/audit.json && echo "audit.json byte-identical to the saved r4 historical-root audit"
( cd /tmp && $PY -m pytest -q -p no:cacheprovider -c /dev/null --rootdir=/tmp $RUN/tests/test_audit_r4.py \
    $FIN/tests/test_audit_r3.py $B/review_closure/task-compaction-v1-r1/tests/test_audit_r2.py \
    $B/task-compaction-v1-r1/tests/test_audit_labels.py )
