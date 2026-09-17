#!/usr/bin/env zsh
# AUDIT04-H3.4 -- licence-contention hypothesis test.
#
# The pre-push hang recorded in plan G was three hours. Plan G did
# not investigate; the AUDIT04-H3 acceptance criterion demands a
# measurement that either (a) reproduces the stall and gives a
# mechanism or (b) does not, in which case the per-invocation stall
# probability is bounded by 1 - 0.05^(1/30) = 9.5 % at 95 % confidence.
# A bare "0/30" is not acceptable; the bound must be stated.
#
# The hypothesis under test: the stall is caused by licence
# contention between two kernels (WolframEngine single-seat licence
# on this machine; the CI runner never sees it because the
# GitHub-hosted runner has no kernel). Plan G noted that the hang
# always occurred during the pre-push hook, which runs the MUnit
# suite -- many kernels launched by a Makefile in series, with the
# licence arbitrated between them. A second kernel started while
# the first is parsing may block indefinitely on a licence IPC.
#
# The experiment: start a second kernel that holds Pause[Infinity]
# for the duration, then run the syntax member 30 times in series
# with an open stdin pipe. Time and record the exit of each. The
# production timeout is 600 s, and the SAME watchdog/capture path
# from tools/run_closure.sh is used here: same perl alarm, same
# PIDFILE, same `sample`/`lsof` capture on a live timeout. Per the
# plan, the bare 0/30 reading must be reported with the
# per-invocation bound, NOT as "hypothesis unsupported".
#
# Output: /tmp/cb_h34_licence_contention.tsv
#   columns: ISO-8601-UTC  run_index  verdict  rc  elapsed_seconds
# Plus:    /tmp/cb_h34_concurrent.{out,err}
# Plus:    per-run /tmp/cb_h34_run_NN.{out,err}
#
# Usage:  zsh tools/run_h3_4_licence_contention.sh
#   exit 0  experiment completed; the .tsv is the artefact
#   exit 1  could not start the concurrent kernel (named in stderr)

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 2
KERNEL=/Applications/Wolfram.app/Contents/MacOS/WolframKernel
if [[ ! -x "$KERNEL" ]]; then
  echo "REFUSED: no kernel at $KERNEL"
  exit 1
fi

RESULTS=/tmp/cb_h34_licence_contention.tsv
: > "$RESULTS" || exit 1

# Extract the production watchdog pieces from run_closure.sh so the
# experiment uses the SAME watchdog and capture path as H3.1-H3.3.
TMPF=$(mktemp -t cb_h34_runner.XXXXXX.zsh)
awk '
  /^ts_utc\(\)/                     { print; in_def=1; next }
  /^ts_log\(\)/                     { print; in_def=1; next }
  /^WATCHDOG_PERL=/                 { print; in_def=1; next }
  /^watched_exec\(\)/               { print; in_def=1; next }
  /^LAST_PIDFILE=/                  { print; next }
  /^capture_stall\(\)/              { print; in_def=1; next }
  /^declare -A MEMBER_TIMEOUT_S=\(/ { print; in_array=1; next }
  in_def && /^\}/                   { print; in_def=0; print ""; next }
  in_def                            { print; next }
  in_array                          { print; if ($0 == ")") in_array=0; next }
' tools/run_closure.sh > "$TMPF"
source "$TMPF"
rm -f "$TMPF"

PROD_TIMEOUT_S="${MEMBER_TIMEOUT_S[wolfram-syntax]:-600}"
RUNS="${CB_H34_RUNS:-30}"
BOUND=$(awk -v n="$RUNS" 'BEGIN { printf "%.1f", (1 - exp(log(0.05)/n)) * 100 }')
CONCURRENT_PID=""
FIFO_KEEPER=""
STDIN_FIFO=""
CONCURRENT_WL="/tmp/cb_h34_concurrent.wl"

cleanup() {
  if [[ -n "$CONCURRENT_PID" ]]; then
    kill "$CONCURRENT_PID" 2>/dev/null || true
    sleep 1
    kill -9 "$CONCURRENT_PID" 2>/dev/null || true
  fi
  if [[ -n "$FIFO_KEEPER" ]]; then
    kill "$FIFO_KEEPER" 2>/dev/null || true
  fi
  rm -f "$CONCURRENT_WL"
  [[ -n "$STDIN_FIFO" ]] && rm -f "$STDIN_FIFO"
  [[ -n "$LAST_PIDFILE" ]] && rm -f "$LAST_PIDFILE"
}
trap cleanup EXIT INT TERM

# ── Concurrent kernel: hold a second licence for the full run ──────
# `Pause[Infinity]` is rejected on this machine, so we hold the
# kernel with an explicit infinite loop of long pauses instead.
printf '%s\n%s\n' 'While[True, Pause[3600]]' 'Exit[]' > "$CONCURRENT_WL"

echo "[$(ts_utc)] starting concurrent kernel"
env CB_REPO="$REPO" HOME="$HOME" "$KERNEL" -script "$CONCURRENT_WL" \
  </dev/null > /tmp/cb_h34_concurrent.out 2> /tmp/cb_h34_concurrent.err &
CONCURRENT_PID=$!
echo "[$(ts_utc)] concurrent kernel pid=${CONCURRENT_PID}"
sleep 5
if ! kill -0 "$CONCURRENT_PID" 2>/dev/null; then
  echo "REFUSED: concurrent kernel exited before the experiment began"
  exit 1
fi

# ── 30 sequential runs of the syntax member with open stdin ────────
# The plan says "under an open stdin pipe". We therefore keep a fifo's
# write end open in a sleeping helper so each syntax run reads from an
# open pipe rather than an already-closed stdin.
STDIN_FIFO=/tmp/cb_h34_stdin_fifo
rm -f "$STDIN_FIFO"
mkfifo "$STDIN_FIFO"
perl -e 'sleep 9999' > "$STDIN_FIFO" &
FIFO_KEEPER=$!

echo "[$(ts_utc)] starting ${RUNS} syntax runs (timeout=${PROD_TIMEOUT_S}s each)"
for i in $(seq 1 "$RUNS"); do
  start_s=$(date +%s)
  ts_start=$(ts_utc)
  out_file=$(printf '/tmp/cb_h34_run_%02d.out' "$i")
  err_file=$(printf '/tmp/cb_h34_run_%02d.err' "$i")

  ts_log "h34 start run=${i} member=wolfram-syntax timeout=${PROD_TIMEOUT_S}s"
  watched_exec "$PROD_TIMEOUT_S" zsh -c '
    env CB_REPO="$1" HOME="$2" "$3" -script "$4" < "$5" > "$6" 2> "$7"
  ' _ "$REPO" "$HOME" "$KERNEL" tools/check_wolfram_syntax.wl "$STDIN_FIFO" "$out_file" "$err_file"
  rc=$?
  end_s=$(date +%s)
  dt=$(( end_s - start_s ))

  case "$rc" in
    0)   verdict=PASS ;;
    2)   verdict=UNKNOWN ;;
    124|142)
      verdict=TIMEOUT
      if [[ -n "$LAST_PIDFILE" && -r "$LAST_PIDFILE" ]]; then
        child_pid=$(cat "$LAST_PIDFILE" 2>/dev/null || true)
        if [[ -n "$child_pid" ]]; then
          capture_stall "wolfram-syntax" "$child_pid"
        else
          echo "STALL-CAPTURE wolfram-syntax: PIDFILE present but empty" >&2
        fi
        rm -f "$LAST_PIDFILE"
        LAST_PIDFILE=""
      else
        echo "STALL-CAPTURE wolfram-syntax: no PIDFILE from watchdog" >&2
      fi
      ;;
    *)   verdict=FAIL ;;
  esac

  ts_log "h34 end   run=${i} member=wolfram-syntax elapsed=${dt}s verdict=${verdict} exit=${rc}"
  printf '%s\t%d\t%s\t%d\t%d\n' "$ts_start" "$i" "$verdict" "$rc" "$dt" >> "$RESULTS"
  printf '  run %2d: %-7s rc=%3d elapsed=%3ds  (%s)\n' "$i" "$verdict" "$rc" "$dt" "$ts_start"
done

# ── Summary ────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "H3.4 licence-contention experiment: ${RUNS} runs complete"
echo "════════════════════════════════════════════════════════════════════"
awk -F'\t' 'NR>0 {
  if (NR == 1 || $5 < min) min=$5
  if ($5 > max) max=$5
  sum += $5
  sumsq += $5 * $5
  verdicts[$3]++
  n++
}
END {
  if (n == 0) { print "no runs recorded"; exit 1 }
  mean = sum / n
  var = sumsq / n - mean * mean
  sd = (var > 0) ? sqrt(var) : 0
  printf "  n=%d  mean=%.2fs  sd=%.2fs  min=%ds  max=%ds\n", n, mean, sd, min, max
  printf "  verdicts: PASS=%d  FAIL=%d  UNKNOWN=%d  TIMEOUT=%d\n", verdicts["PASS"], verdicts["FAIL"], verdicts["UNKNOWN"], verdicts["TIMEOUT"]
}' "$RESULTS"
echo "  full table: $RESULTS"
echo ""
echo "STATISTICAL NOTE: if 0 of ${RUNS} stalled (no run > 60s), this bounds"
echo "  the per-invocation stall probability below 1 - 0.05^(1/${RUNS}) = ${BOUND}%"
echo "  at 95% confidence. The plan §H3.4 acceptance requires this bound"
echo "  to be reported, not a bare '0/30'."
