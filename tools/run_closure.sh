#!/usr/bin/env zsh
# AUDIT03-C — the closure set, run as one command, WITH A REAL EXIT CODE.
# AUDIT04-H3 — per-member timeline and stall capture; the wolf3
# pre-push hang is bounded here, not by the hook.
#
# THE DEFECT THIS FIXES. The Makefile invoked every member with a `-@` recipe
# prefix, which tells make to ignore the error. `make closure` therefore exited
# 0 EVEN IF ALL NINE MEMBERS FAILED. One member was worse still:
#
#     -@venv/bin/python tools/enumerate_paper_tables.py | head -8
#
# a pipe, so the status was `head`'s, not the script's. Putting that in CI would
# have produced a permanently green badge -- the exact "gate that cannot go red"
# failure this audit exists to remove, sitting in the aggregator itself.
#
# The `-` prefix did buy something real: one red must not hide the other eight.
# That property is kept here by RUNNING EVERY MEMBER, recording each verdict,
# and failing at the end.
#
# THREE-STATE, not two. tools/check_glossary_sync.sh exits 2 (SYNC-UNKNOWN) when
# the sibling repository is absent, which is correct refusal behaviour and is
# what CI will see. UNKNOWN is reported as UNKNOWN: never folded into a pass,
# never counted as a failure of this repository.
#
# AUDIT04-H3 ADDITIONS:
#   - Per-member ISO-8601 timestamp and elapsed seconds are written to stderr,
#     so a future stall names the stage it is in. Required for H3.1.
#   - Per-member watchdog fires a named red, never a skip. The kernel has been
#     observed to spin for hours during the pre-push hook with no macOS
#     diagnostic report; the watchdog is the only bounded termination. The
#     perl idiom is `perl -e 'alarm shift @ARGV; exec @ARGV or die'` -- the
#     near-identical `perl -e 'alarm $ARGV[0]; exec @ARGV'` SILENTLY NO-OPS the
#     exec on this platform and has already produced a superseded baseline in
#     this repository. Required for H3.2.
#   - On watchdog kill, a stack sample (`sample <pid> 10`) and an `lsof -p`
#     capture are taken into /tmp/cb_stall_<stage>_pid<pid>_<ts>.{txt,lsof}.
#     This is the only evidence path that exists when a kernel blocks silently.
#     Required for H3.3.
#
# The timeout PER MEMBER is set in PER_MEMBER_TIMEOUT_P99 below. The accepted
# production value is `MAX(measured_p99 * 4, 60s)` for pure members and
# `MAX(measured_p99 * 4, 600s)` for the Wolfram members, where the
# measurement is named. The plant (a Pause[9999] injected into a sandboxed
# syntax pass) fires at the production value, not at a value lowered for the
# test. H3.4 uses the same watchdog on the licence-contention experiment.
#
# Usage:  run_closure.sh [pure|wolfram|all]      (default: all)
#
#   exit 0  every member passed (UNKNOWNs allowed, and named)
#   exit 1  at least one member failed
#   exit 2  refused: nothing to run
#   exit 3  at least one member timed out (named, with /tmp/cb_stall_*)

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 2

TIER="${1:-all}"
KERNEL=/Applications/Wolfram.app/Contents/MacOS/WolframKernel

# AUDIT04-H3.1: per-member timestamps. ISO-8601 UTC, prefixed
# `STALL-CLOCK` so a `tail -f` of an arbitrary run picks them out of the
# noise. Written to stderr (terminal-merged by default) so they are
# separable from the member's own output stream and so a future
# `run_closure.sh 2>stall_clock.log` records only the clock.
ts_utc() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
ts_log() { print -r -- "STALL-CLOCK $(ts_utc) $*" >&2; }

# AUDIT04-H3.2: per-member watchdog. The chosen perl idiom is the one the
# plan §H3.2 calls out as the working form on this platform; the `$ARGV[0]`
# variant silently no-ops. The wrapper is a perl one-liner that:
#   1. shifts the first arg off @ARGV (the timeout in seconds);
#   2. sets a SIGALRM that dies after that many seconds;
#   3. writes its own PID to $CB_WATCHDOG_PIDFILE BEFORE the exec, so
#      that the H3.3 capture can find the spawned process even after
#      SIGALRM reaps it (the exec'd child inherits the same PID);
#   4. execs the remaining args -- if exec returns, the spawn failed.
# If SIGALRM fires, perl dies (exit 142) and the spawned child, which
# is the same process by PID, dies with it; the PIDFILE is the only
# evidence of what was running. If the child process is a real
# WolframKernel started by an `env` wrapper, the kernel may or may
# not honour SIGALRM; in either case the PIDFILE tells us what to
# sample. Without the PIDFILE the H3.3 capture finds nothing.
WATCHDOG_PERL='alarm shift @ARGV; if ($ENV{CB_WATCHDOG_PIDFILE}) { open(my $f, ">", $ENV{CB_WATCHDOG_PIDFILE}); print $f $$; close($f) } exec @ARGV or die $! || 142'

watched_exec() {
  # $1 = timeout seconds (integer), $2.. = command.
  local to="$1"; shift
  # Fresh PIDFILE per invocation. The file is in /tmp so capture_stall
  # and the finding note can find it from anywhere.
  local pidfile="/tmp/cb_watchdog_pid_$$.${RANDOM}"
  CB_WATCHDOG_PIDFILE="$pidfile" perl -e "$WATCHDOG_PERL" -- "$to" "$@"
  local rc=$?
  # Stash the pidfile path for capture_stall to read; we use a
  # well-known env var that run_member can pick up after TIMEOUT.
  if [[ $rc -ne 0 ]]; then
    LAST_PIDFILE="$pidfile"
  else
    rm -f "$pidfile"
  fi
  return $rc
}

# Track the most recent PIDFILE so run_member can pass it on to
# capture_stall without re-deriving the path.
LAST_PIDFILE=""

# AUDIT04-H3.3: stall capture. `sample` (macOS) produces a 10-second stack
# sample; `lsof -p` lists open files and sockets. Together they are the
# only artefact a live kernel leaves. The output is written into
# /tmp/cb_stall_<stage>_pid<pid>_<unix-ts>.{txt,lsof}, one pair per
# watchdog kill, with the file paths printed to stderr so the finding
# note can attach them. A NULL capture is itself evidence and is
# named: the watchdog fired, but the process was already gone when
# the capture reached it. The finding note distinguishes the two.
capture_stall() {
  local stage="$1" pid="$2"
  local stamp; stamp=$(date -u +"%Y%m%dT%H%M%SZ")
  local base="/tmp/cb_stall_${stage}_pid${pid}_${stamp}"
  {
    echo "STALL-CAPTURE stage=${stage} pid=${pid} ts=${stamp}"
    # Is the pid alive? `kill -0` returns 0 on a live process we are
    # allowed to signal, non-zero otherwise. The watch has already
    # reaped the child in most cases (perl SIGALRM -> exec'd child
    # dies with it, because exec preserves the PID), so a live
    # capture is the EXCEPTIONAL case -- the finding note treats it
    # as a real stall, the dead-pid case as a confirmed timeout.
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "  process is NOT live: capture is timing + PID only"
      echo "  evidence: watch fired at timeout=${MEMBER_TIMEOUT_S[$stage]:-?}s; pid=${pid} was the spawned child"
      return
    fi
    if command -v sample >/dev/null 2>&1; then
      if sample "$pid" 10 -file "${base}.txt" 2>/dev/null; then
        echo "  sample -> ${base}.txt"
      else
        echo "  sample: FAILED for pid=${pid} (process exited mid-sample?)"
        rm -f "${base}.txt"
      fi
    else
      echo "  sample: NOT AVAILABLE on this platform"
    fi
    if command -v lsof >/dev/null 2>&1; then
      if lsof -p "$pid" > "${base}.lsof" 2>/dev/null; then
        if [[ -s "${base}.lsof" ]]; then
          echo "  lsof   -> ${base}.lsof"
        else
          echo "  lsof:   empty (process had no open fds at capture time)"
          rm -f "${base}.lsof"
        fi
      else
        echo "  lsof:   FAILED for pid=${pid}"
        rm -f "${base}.lsof"
      fi
    else
      echo "  lsof:   NOT AVAILABLE on this platform"
    fi
  } 1>&2
}

# Per-member timeout, in seconds. Each row is `member_label -> timeout`.
# The values are the production values used by the runner on every
# invocation, including H3.4. They are stated in seconds and named in
# the finding note; the plant fires at this value, not a lowered test
# value. AUDIT04-H3.2 acceptance: "a stated multiple of the measured
# p99 wall-clock for that member, the measurement is named".
#
# Measured 2026-09-08 on the AUDIT04-H3.4 baseline -- 5 runs of
# `zsh tools/run_closure.sh pure` and 3 runs of
# `zsh tools/run_closure.sh wolfram`, with the timestamp log captured
# by H3.1. The pure tier's slowest member across 5 runs was
# `coverage ratchet` at p99 = 4.5 s; the wolfram tier's slowest
# member across 3 runs was `Wolfram syntax` at p99 = 38.0 s (with
# `paper artefacts` at p99 = 35.0 s and the two parity members below
# 30 s). The factor is 4, matching the plan §H3.2 ("a stated
# multiple"). The lower bounds (60 s pure, 600 s wolfram) protect
# against an unrealistically small p99 from a slow machine.
declare -A MEMBER_TIMEOUT_S=(
  # PURE TIER
  [paper-number]="${CB_TIMEOUT_PAPER_NUMBER:-60}"
  [glossary-sync]="${CB_TIMEOUT_GLOSSARY_SYNC:-60}"
  [glossary-conformance]="${CB_TIMEOUT_GLOSSARY_CONFORMANCE:-60}"
  [single-engine]="${CB_TIMEOUT_SINGLE_ENGINE:-60}"
  [core-index]="${CB_TIMEOUT_CORE_INDEX:-60}"
  [test-manifest]="${CB_TIMEOUT_TEST_MANIFEST:-60}"
  [table-coverage]="${CB_TIMEOUT_TABLE_COVERAGE:-60}"
  [verification-numbers]="${CB_TIMEOUT_VERIFICATION_NUMBERS:-60}"
  [import-safety]="${CB_TIMEOUT_IMPORT_SAFETY:-60}"
  [core-loading]="${CB_TIMEOUT_CORE_LOADING:-60}"
  [coverage-ratchet]="${CB_TIMEOUT_COVERAGE_RATCHET:-60}"
  # WOLFRAM TIER
  [wolfram-syntax]="${CB_TIMEOUT_WOLFRAM_SYNTAX:-600}"
  [paper-artefacts]="${CB_TIMEOUT_PAPER_ARTEFACTS:-600}"
  [cross-language-parity]="${CB_TIMEOUT_CROSS_LANGUAGE_PARITY:-600}"
  [description-length-parity]="${CB_TIMEOUT_DESCRIPTION_LENGTH_PARITY:-600}"
)

names=(); verdicts=(); tiers=(); elapsed_s=()
NFAIL=0; NUNKNOWN=0; NPASS=0; NTIMEOUT=0

# run_member is the single hot path. It:
#   1. logs start ts and stage name (H3.1);
#   2. runs the member under a perl alarm (H3.2) at the per-member timeout;
#   3. on a 124 exit (alarm) it finds the spawned child, samples it, and
#      captures lsof (H3.3), then records the stage as TIMEOUT;
#   4. logs the elapsed seconds and the verdict.
#
# The label passed in is the human-readable member name; the slabel is
# the slug used to look up the timeout in MEMBER_TIMEOUT_S. The pure
# members pass one slabel; the wolfram members pass another.
run_member() {
  local tier="$1" slabel="$2" label="$3"; shift 3
  local to="${MEMBER_TIMEOUT_S[$slabel]:-300}"
  local t0; t0=$(date +%s)
  ts_log "start tier=${tier} member=${slabel} timeout=${to}s label=${label}"
  echo "── ${label}  (timeout ${to}s)"

  # AUDIT04-H3.2: spawn the member under a perl alarm. The subshell
  # ensures the member's own $? is what we see; perl returns 124 on
  # SIGALRM (the conventional `timeout` exit) and the original spawn
  # status on a normal exit.
  local rc=0
  watched_exec "$to" "$@"
  rc=$?

  local t1; t1=$(date +%s)
  local dt=$(( t1 - t0 ))
  local verdict
  case $rc in
    0)   verdict=PASS;    NPASS=$((NPASS+1));;
    2)   verdict=UNKNOWN; NUNKNOWN=$((NUNKNOWN+1));;
    124) verdict=TIMEOUT; NTIMEOUT=$((NTIMEOUT+1));;  # GNU coreutils `timeout`
    142) verdict=TIMEOUT; NTIMEOUT=$((NTIMEOUT+1));;  # perl die on SIGALRM
    *)   verdict=FAIL;    NFAIL=$((NFAIL+1));;
  esac
  names+=("$label"); verdicts+=("$verdict"); tiers+=("$tier"); elapsed_s+=("$dt")

  ts_log "end   tier=${tier} member=${slabel} elapsed=${dt}s verdict=${verdict} exit=${rc}"

  # AUDIT04-H3.3: on a timeout, capture the spawned child. The PID was
  # written to $LAST_PIDFILE by the perl wrapper BEFORE its exec
  # (see WATCHDOG_PERL); we read it from there. pgrep cannot find the
  # child because perl execs into the member and inherits the same
  # PID, so by the time the watch returns SIGCHLD has reaped the
  # process and there is nothing for pgrep to match against. A NULL
  # capture is named, not silent.
  if [[ $verdict == TIMEOUT ]]; then
    if [[ -n "$LAST_PIDFILE" && -r "$LAST_PIDFILE" ]]; then
      local child_pid
      child_pid=$(cat "$LAST_PIDFILE" 2>/dev/null || true)
      if [[ -n "$child_pid" ]]; then
        capture_stall "$slabel" "$child_pid"
      else
        echo "STALL-CAPTURE ${slabel}: PIDFILE present but empty" 1>&2
      fi
      # Capture done. The pidfile is the only place that knew the
      # exec'd child PID; the capture files in /tmp/cb_stall_* are
      # named with the PID directly, so the pidfile can be removed.
      rm -f "$LAST_PIDFILE"
      LAST_PIDFILE=""
    else
      echo "STALL-CAPTURE ${slabel}: no PIDFILE from watchdog" 1>&2
    fi
  fi
  echo "   -> ${verdict} (exit ${rc}, ${dt}s)"
}

# ── PURE TIER — no WolframKernel required; this is what CI runs ──────────────
run_pure() {
  run_member pure paper-number "paper-number gate (manuscript CHANGE detector, not a correctness check)" \
    python3 tools/snapshot_paper_numbers.py --check
  run_member pure glossary-sync "GLOSSARY sync (document mirroring vs the sibling; does NOT check code)" \
    zsh tools/check_glossary_sync.sh
  run_member pure glossary-conformance "GLOSSARY conformance (the code side the sync check cannot see)" \
    zsh tools/check_glossary_conformance.sh
  run_member pure single-engine "single-engine guard (one owner per concept)" \
    zsh tools/check_single_engine.sh
  run_member pure core-index "core index (every owner named in GOVERNANCE/CORE.md still exists)" \
    zsh tools/check_core_index.sh
  run_member pure test-manifest "test manifest (every tests/ file classified; no silent exclusions)" \
    zsh tools/check_test_manifest.sh
  # No pipe. The previous `| head -8` returned head's status, not the script's.
  run_member pure table-coverage "table coverage (how much of the manuscripts a producer is wired to)" \
    venv/bin/python tools/enumerate_paper_tables.py
  # AUDIT03-C: the governance page claimed 36/36 owners while its own guard
  # printed 40/40. Nothing compared the page to the tools it names, so the
  # sentence "none of these numbers is typed by hand" was itself typed by hand.
  run_member pure verification-numbers "verification numbers (VERIFICATION.md against the tools it cites)" \
    venv/bin/python tools/check_verification_numbers.py
  # AUDIT04 Phase 2: importing a module must not DO anything. Two modules
  # reseeded the global RNG on import and two created directories, so a test
  # that merely imported them changed the process it ran in.
  run_member pure import-safety "import safety (no module does work when imported)" \
    venv/bin/python tools/check_import_safety.py
  # AUDIT04-D: joins the closure only now that it is green AND its matches mean
  # something. It was red by design while 8 accusations awaited adjudication,
  # and 7 of those turned out to be its own false positives -- a guard admitted
  # on the strength of an unmeasured detector would have put a number on a page.
  # It ships a control corpus that runs before every scan and exits 2 rather
  # than emit a count it cannot stand behind.
  run_member pure core-loading "core loading (every file implementing an owned concept reaches its owner)" \
    venv/bin/python tools/check_core_loading.py
  # AUDIT04-D: the ratchet guards a floor that RISES and never falls, per module
  # and globally. It needs a fresh coverage.json and refuses on a stale one.
  run_member pure coverage-ratchet "coverage ratchet (per-module and global floors; refuses on a stale report)" \
    venv/bin/python tools/check_coverage_ratchet.py
}

# ── WOLFRAM TIER — needs a licensed local kernel; NOT run by CI ──────────────
run_wolfram() {
  if [[ ! -x "$KERNEL" ]]; then
    echo ""
    echo "── WOLFRAM TIER REFUSED: no kernel at $KERNEL"
    echo "   This tier is deliberately local-only. CI covers the pure tier and"
    echo "   says so; the pre-push hook is what stops this tier being skipped."
    names+=("wolfram tier"); verdicts+=("UNKNOWN"); tiers+=("wolfram")
    NUNKNOWN=$((NUNKNOWN+1))
    return
  fi
  run_member wolfram wolfram-syntax "Wolfram syntax (every .m/.wl parses; the suite cannot see a syntax error)" \
    env CB_REPO="$PWD" HOME="$HOME" "$KERNEL" -script tools/check_wolfram_syntax.wl
  run_member wolfram paper-artefacts "paper artefacts (the only member that ties a number to its producer)" \
    python3 tools/verify_paper_artefacts.py
  # AUDIT03-C: both of these existed and neither was run by any routine command.
  run_member wolfram cross-language-parity "cross-language parity (Python forward model == CausalBoolCore.wl)" \
    zsh tools/run_crosscheck_parity.sh
  run_member wolfram description-length-parity "description-length parity (executes the WL producer, not a stored number)" \
    venv/bin/python tools/test_description_length_parity.py
}

case "$TIER" in
  pure)    run_pure ;;
  wolfram) run_wolfram ;;
  all)     run_pure; run_wolfram ;;
  *) echo "REFUSED: unknown tier '$TIER' (expected pure|wolfram|all)"; exit 2 ;;
esac

total=${#names[@]}
if [[ "$total" -eq 0 ]]; then
  echo "REFUSED: ran 0 members. A closure run over nothing is not a pass."
  exit 2
fi

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "CLOSURE (${TIER}): ${NPASS} pass, ${NFAIL} fail, ${NUNKNOWN} unknown, ${NTIMEOUT} timeout, of ${total}"
echo "════════════════════════════════════════════════════════════════════"
for i in {1..$total}; do
  printf '  %-8s %-8s %6ss  %s\n' "${verdicts[$i]}" "${tiers[$i]}" "${elapsed_s[$i]}" "${names[$i]}"
done

if [[ "$NUNKNOWN" -gt 0 ]]; then
  echo ""
  echo "UNKNOWN is not a pass. It means a member could not do the work it claims,"
  echo "usually an absent sibling repository or an absent WolframKernel."
fi

if [[ "$NTIMEOUT" -gt 0 ]]; then
  echo ""
  echo "TIMEOUT is a named red. ${NTIMEOUT} member(s) exceeded its per-member budget."
  echo "Stack samples and lsof captures are in /tmp/cb_stall_*; see the H3 finding note."
fi

if [[ "$TIER" != "wolfram" && "$NFAIL" -eq 0 ]]; then
  echo ""
  echo "NOTE: the pure tier does NOT cover the Wolfram tier or the MUnit suite."
  echo "      Green here is not green overall. Run: make ci-local"
fi

[[ "$NFAIL" -eq 0 ]] || exit 1
[[ "$NTIMEOUT" -eq 0 ]] || exit 3
