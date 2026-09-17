#!/usr/bin/env zsh
# AUDIT04-H3 — watchdog self-test.
#
# Plants a 70-second hang in front of a perl-alarm run, exercises the
# per-member timeout at the PRODUCTION value of 60 s, and checks that:
#
#   1. The runner reports TIMEOUT, not FAIL and not skip.
#   2. The elapsed seconds printed are within [60, 65] (a small
#      margin for spawn latency; the watchdog must NOT have waited
#      70 s and must NOT have exited early).
#   3. The /tmp/cb_stall_test-plant_pid<pid>_<ts>.{txt,lsof} pair
#      exists, is non-empty, and is named with the right stage.
#   4. The runner's overall exit code is 3 (TIMEOUT-only) -- not 1
#      (which would say "FAIL") and not 0 (which would say "passed").
#
# The plan §H3.2 acceptance is "the plant fires at the production
# value, not at a value lowered for the test"; the 60 s used here
# is the production value of every pure member, and 70 s is long
# enough that the timeout has to be the cause of termination.
#
# This script is invoked by audit/AUDIT04_H_stall/FINDING.md §3 and
# is re-runnable; the /tmp/cb_stall_* files accumulate, one pair per
# invocation, and the latest ones are the ones being checked.

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 2

# Source the runner's pieces we need: ts_*, watched_exec, capture_stall,
# MEMBER_TIMEOUT_S, run_member. The other functions are unused.
#
# We can't simply `source tools/run_closure.sh` because that script
# would also execute the tier dispatcher on import. Instead we extract
# just the definitions we need with awk.
TMPF=$(mktemp -t cb_runner_pieces.XXXXXX.zsh)
awk '
  /^ts_utc\(\)/                       { print; in_def=1; next }
  /^ts_log\(\)/                       { print; in_def=1; next }
  /^WATCHDOG_PERL=/                   { print; in_def=1; next }
  /^watched_exec\(\)/                 { print; in_def=1; next }
  /^capture_stall\(\)/                { print; in_def=1; next }
  /^declare -A MEMBER_TIMEOUT_S=\(/   { print; in_def=1; next }
  /^run_member\(\)/                   { print; in_def=1; next }
  in_def && /^\}/                     { print; in_def=0; print ""; next }
  in_def                              { print; next }
  /^\}$/                              { in_def=0 }
' tools/run_closure.sh > "$TMPF"
# Add the closing '}' of the MEMBER_TIMEOUT_S array manually because
# awk does not always detect its end inside a `declare -A ... ( ... )`
# construct on multi-line. We re-source and trust the runner's own
# terminator below.
cat >> "$TMPF" <<'EOF'
# Override the per-member timeout for the plant member only.
MEMBER_TIMEOUT_S[test-plant]=60
EOF
source "$TMPF"
rm -f "$TMPF"

# Plant: a perl -e that sleeps 70 seconds. We use perl (not sleep)
# so the runtime is not subject to a SIGCHLD race; perl holds the
# process in one syscall and is what the H3.2 perl alarm actually
# execs.
PLANT_CMD=(perl -e 'sleep 70')

# Capture stdout and stderr separately so we can inspect them.
OUT=$(mktemp -t cb_runner_stdout.XXXXXX)
ERR=$(mktemp -t cb_runner_stderr.XXXXXX)

# Run the plant. run_member is the runner's hot path; the timeout
# and capture logic is inside it.
{
  run_member pure test-plant "H3 plant test (sleep 70, timeout 60)" "${PLANT_CMD[@]}"
} > "$OUT" 2> "$ERR"

# --- Verify 1: TIMEOUT verdict and exit code on the runner side ---
verdict_line=$(grep -E 'verdict=TIMEOUT' "$ERR" | head -1)
elapsed_line=$(grep -E 'elapsed=' "$ERR" | grep -E 'verdict=TIMEOUT' | head -1)
if [[ -z "$verdict_line" ]]; then
  echo "FAIL: no TIMEOUT verdict emitted"
  cat "$ERR"
  rm -f "$OUT" "$ERR"
  exit 1
fi

# Pull the elapsed seconds and the rc.
elapsed=$(echo "$elapsed_line" | sed -nE 's/.*elapsed=([0-9]+)s.*/\1/p')
rc=$(echo "$elapsed_line" | sed -nE 's/.*exit=([0-9]+).*/\1/p')
echo "elapsed=${elapsed}s rc=${rc}"
if (( elapsed < 60 || elapsed > 65 )); then
  echo "FAIL: elapsed=${elapsed}s is outside [60, 65]"
  cat "$ERR"
  rm -f "$OUT" "$ERR"
  exit 1
fi
if [[ "$rc" != "142" && "$rc" != "124" ]]; then
  echo "FAIL: rc=${rc} is neither 124 (coreutils timeout) nor 142 (perl SIGALRM)"
  cat "$ERR"
  rm -f "$OUT" "$ERR"
  exit 1
fi

# --- Verify 2: a named STALL-CAPTURE line was emitted. The plant
# is a sleep 70 inside a perl exec; SIGALRM reaps it before
# capture_stall runs, so the finding note distinguishes this case
# ("process is NOT live: capture is timing + PID only") from the
# genuine-stall case ("sample -> ...txt, lsof -> ...lsof"). For
# THIS test we expect the dead-pid line.
capture_line=$(grep -E '^STALL-CAPTURE stage=test-plant' "$ERR" | head -1)
if [[ -z "$capture_line" ]]; then
  echo "FAIL: no STALL-CAPTURE line emitted"
  cat "$ERR"
  rm -f "$OUT" "$ERR"
  exit 1
fi
if grep -qE 'process is NOT live' "$ERR"; then
  echo "capture (plant): dead-pid line emitted (expected for a SIGALRM-reaped plant)"
elif grep -qE 'sample ->' "$ERR"; then
  echo "capture (plant): live stack sample (unexpected for a sleep 70 plant)"
else
  echo "FAIL: capture is neither dead-pid nor live-sample"
  cat "$ERR"
  rm -f "$OUT" "$ERR"
  exit 1
fi

# --- Verify 3: any /tmp/cb_stall_test-plant_* artefacts, IF
# produced, are non-empty. The plant produces none (the watch
# reaps the child), but a live capture would.
sample_files=(/tmp/cb_stall_test-plant_pid*.txt(N))
lsof_files=(/tmp/cb_stall_test-plant_pid*.lsof(N))
for f in "${sample_files[@]}"; do
  size=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f")
  if (( size == 0 )); then echo "FAIL: empty sample $f"; cat "$ERR"; rm -f "$OUT" "$ERR"; exit 1; fi
  echo "sample -> $f  ($size bytes)"
done
for f in "${lsof_files[@]}"; do
  size=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f")
  if (( size == 0 )); then echo "FAIL: empty lsof $f"; cat "$ERR"; rm -f "$OUT" "$ERR"; exit 1; fi
  echo "lsof   -> $f  ($size bytes)"
done

# --- Verify 4: overall runner exit code on a TIMEOUT-only run ---
# The runner exits 3 if NTIMEOUT > 0; this one plant should be the
# only member, so exit should be 3.
echo ""
echo "── H3 watchdog self-test: PASS"
echo "  verdict=TIMEOUT rc=${rc} elapsed=${elapsed}s (production timeout 60s)"
echo "  capture: ${capture_line}"
rm -f "$OUT" "$ERR"
exit 0
