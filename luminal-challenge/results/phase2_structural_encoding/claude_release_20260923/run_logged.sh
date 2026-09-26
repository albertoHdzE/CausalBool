#!/bin/zsh
# Operator evidence wrapper: run_logged.sh <label> <command...>
# Retains argv, cwd, selected environment, UTC start/end, full stdout/stderr
# and the terminal exit code under logs/<label>.*; appends to COMMANDS.jsonl.
# It never alters the command. Refuses to overwrite an existing label.
set -u
AUDIT=${0:A:h}
label=$1; shift
base=$AUDIT/logs/$label
if [[ -e $base.meta.json ]]; then echo "refusing: $base exists" >&2; exit 97; fi
start=$(date -u +%Y-%m-%dT%H:%M:%S.%NZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)
t0=$(python3 -c 'import time;print(time.time())')
"$@" > $base.stdout 2> $base.stderr
rc=$?
t1=$(python3 -c 'import time;print(time.time())')
end=$(date -u +%Y-%m-%dT%H:%M:%SZ)
python3 - "$base.meta.json" "$AUDIT/COMMANDS.jsonl" "$label" "$rc" "$start" "$end" "$t0" "$t1" "$PWD" "$@" <<'EOF'
import json, os, sys
meta, journal, label, rc, start, end, t0, t1, cwd, *argv = sys.argv[1:]
rec = {"label": label, "argv": argv, "cwd": cwd, "exit_code": int(rc),
       "start_utc": start, "end_utc": end, "elapsed_seconds": round(float(t1) - float(t0), 3),
       "env": {k: os.environ.get(k) for k in ("PYTHONPATH", "PATH", "HOME", "VIRTUAL_ENV", "PYTHONHASHSEED")},
       "stdout": label + ".stdout", "stderr": label + ".stderr"}
open(meta, "x").write(json.dumps(rec, indent=2) + "\n")
with open(journal, "a") as f:
    f.write(json.dumps(rec) + "\n"); f.flush(); os.fsync(f.fileno())
EOF
echo "[$label] exit=$rc elapsed=$(python3 -c "print(round($t1-$t0,1))")s"
exit $rc
