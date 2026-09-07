#!/usr/bin/env zsh
# MUnit runner — AUDIT01/T0.1a
# Judgement is now parsed from each test's exported Status.txt, NOT kernel exit code.
# Verdict grammar (inventoried 2026-08-23 across results/tests/*/Status.txt):
#   first line "OK" or "PASS"            -> pass
#   first line "FAIL"                    -> fail
#   missing file                         -> NO STATUS EXPORTED (fail)
#   anything else (incl. unevaluated WL) -> UNPARSEABLE STATUS (fail)
# Timestamp lines after the verdict are ignored.
# Scope guard (T0.1a): the seven known sections only. Section discovery lands in T0.1b.
SECTION=""
GATE=""
MODE="all"
TESTMODE=""
TIMEOUT_SECS=900
LIST_ONLY=0
while (( "$#" )); do
  case "$1" in
    --section)
      SECTION="$2"; shift 2;;
    --gate)
      GATE="$2"; shift 2;;
    --all)
      MODE="all"; shift;;
    --mode)
      TESTMODE="$2"; shift 2;;
    --timeout)
      TIMEOUT_SECS="$2"; shift 2;;
    # AUDIT04-E: print the selection and exit, executing nothing.
    #
    # The bilingual-manifest defect reached a push because the only thing that
    # could contradict the runner's selection was a rollup, and a rollup costs a
    # 40-minute suite run. tools/check_test_manifest.sh calls this instead, so
    # the SELECTION is checked against the manifest in under a second, by asking
    # the runner rather than by re-implementing its filter in a second place.
    --list)
      LIST_ONLY=1; shift;;
    *)
      shift;;
  esac
done
ROOT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_DIR="$ROOT_DIR/../.."
SEARCH_DIRS=()
if [[ -n "$SECTION" ]]; then
  SEARCH_DIRS=("$ROOT_DIR/$SECTION")
else
  # AUDIT01/T0.1b: root recursion alone discovers every section exactly once
  # (the old root+7-section list double-counted). Skipped sections must carry
  # a SKIP_REASON.txt, which is reported below — never silent.
  SEARCH_DIRS=("$ROOT_DIR")
fi
# AUDIT03 — membership is DECLARED in MANIFEST.tsv, not inferred from a glob.
#
# The old rule was `find -name "*Tests.m"`, which silently excluded 23 of the 78
# .m files in this tree. Ten of them were real conditional checks whose coverage
# was simply lost; eleven export a literal "OK" and cannot fail; two are artefact
# producers. A glob cannot tell those apart, so it collected the wrong set in
# both directions.
#
# Renaming the excluded files was ruled out on evidence: TSK-ALGO-004 and
# TSK-MIXED-001 are cited by name in both manuscripts.
#
# tools/check_test_manifest.sh asserts that every .m in this tree is classified
# exactly once, so a new file is red until someone declares what it is.
MANIFEST="$ROOT_DIR/MANIFEST.tsv"
if [[ ! -f "$MANIFEST" ]]; then
  echo "REFUSED: $MANIFEST is missing. Test membership is declared, not discovered."
  exit 2
fi
TEST_FILES=()
# The loop variable is `entry`, never `path`: zsh TIES the array `path` to $PATH,
# so `read -r kind path` destroys PATH for the remainder of the script.
while IFS=$'\t' read -r kind entry _rest; do
  [[ -z "$kind" || "$kind" == \#* ]] && continue
  [[ "$kind" != "test" ]] && continue
  # AUDIT04-E: THIS RUNNER IS THE WOLFRAM RUNNER, so it takes the Wolfram half
  # of the manifest and nothing else.
  #
  # The manifest became bilingual on 2026-09-07, and this loop did not. It fed
  # 24 Python files to the WolframKernel, which reported `Syntax::sntx: Invalid
  # syntax` on each and scored them FAIL -- OK=72 FAIL=24 TOTAL=96. The pre-push
  # hook refused the push, which is the gate working: the defect was caught by
  # the tier CI cannot run, exactly where it was supposed to be caught.
  #
  # The Python half is run by pytest, whose membership comes from the same
  # manifest via the root conftest.py. One declaration, two runners, and each
  # runner takes only what it can execute.
  [[ "$entry" != *.m ]] && continue
  [[ -n "$SECTION" && "$entry" != tests/MUnit/"$SECTION"/* ]] && continue
  TEST_FILES+="$REPO_DIR/$entry"
done < "$MANIFEST"
if [[ ${#TEST_FILES[@]} -eq 0 ]]; then
  if [[ -n "$SECTION" ]]; then
    echo "NO_TESTS: no manifest entry of kind 'test' under section '$SECTION'"
  else
    echo "REFUSED: the manifest declared 0 tests. A run over zero tests is not a pass."
  fi
  exit 1
fi
FILTERED=()
for f in $TEST_FILES; do
  bn=$(basename "$f")
  if [[ "$bn" == "RunTests.m" ]]; then
    continue
  fi
  if [[ -n "$GATE" ]]; then
    echo "$bn" | grep -qi "$GATE" || continue
  fi
  FILTERED+="$f"
done
# AUDIT04-E: --list reports the SELECTION and executes nothing. Placed after
# FILTERED so it reports what would actually run, not an earlier approximation.
if [[ "$LIST_ONLY" -eq 1 ]]; then
  for f in $FILTERED; do
    print -r -- "${f#$REPO_DIR/}"
  done
  echo "SELECTED=${#FILTERED[@]}" >&2
  exit 0
fi
if [[ ${#FILTERED[@]} -eq 0 ]]; then
  echo "NO_TESTS"; exit 1
fi

KERNEL="/Applications/Wolfram.app/Contents/MacOS/WolframKernel"

# Locate the Status.txt a test exports by reading its own hardcoded path.
# Handles: (i) contiguous "results/tests/<name>/Status.txt";
#          (ii) FileNameJoin[{"results","tests","<name>"}] + "Status*.txt" variants
#               (e.g. TSK-MIXED-001, NOTNetworkTests -> Status_network_not.txt).
status_path_for() {
  local f="$1" dir fname
  # Directory: contiguous "results/..." first, then any FileNameJoin[{"results",<x>,<y>}] list
  dir=$(grep -o 'results/[A-Za-z0-9_.-]*/[A-Za-z0-9_.-]*' "$f" 2>/dev/null | sort -u | head -1)
  if [[ -z "$dir" ]]; then
    dir=$(grep -o '[{]"results", *"[A-Za-z0-9_.-]*", *"[A-Za-z0-9_.-]*"' "$f" 2>/dev/null | head -1 \
          | sed 's|.*"results", *"\([A-Za-z0-9_.-]*\)", *"\([A-Za-z0-9_.-]*\)".*|results/\1/\2|')
  fi
  [[ -z "$dir" ]] && return 1
  # Filename: any quoted "*status*.txt" written by this script; default Status.txt
  fname=$(grep -io '"[A-Za-z0-9_.-]*status[A-Za-z0-9_.-]*\.txt"' "$f" 2>/dev/null | head -1 | tr -d '"')
  [[ -z "$fname" ]] && fname="Status.txt"
  print -r -- "$REPO_DIR/${dir}/${fname}"
}

# AUDIT04-D: the sentinel lives beside the status file, so the same resolution
# serves both and they cannot drift to different directories.
done_path_for() {
  local sp
  sp=$(status_path_for "$1") || return 1
  [[ -z "$sp" ]] && return 1
  print -r -- "${sp:h}/Done.txt"
}

classify_status() {
  local sp="$1" first
  if [[ ! -f "$sp" ]]; then
    print -r -- "NO STATUS EXPORTED"; return
  fi
  first=$(head -n 1 "$sp" | tr -d '[:space:]')
  case "$first" in
    OK|PASS) print -r -- "PASS";;
    FAIL)    print -r -- "FAIL";;
    *)       print -r -- "UNPARSEABLE STATUS";;
  esac
}

OK=0; FAIL=0
FAILED_NAMES=()
CRASHED_NAMES=()
for f in $FILTERED; do
  bn=$(basename "$f")
  # AUDIT03 — clear the status BEFORE running.
  #
  # results/ is not cleaned between runs, so a test that crashed or exported
  # nothing was scored by the Status.txt left behind by its LAST SUCCESSFUL run.
  # That is how three files stayed green after a collapse in this audit left
  # them unable to run at all: they wrote no status, and the runner read a stale
  # pass. A missing status must read as a failure, which it can only do if the
  # old one is gone first.
  sp_pre=$(status_path_for "$f")
  [[ -n "$sp_pre" && -f "$sp_pre" ]] && rm -f "$sp_pre"
  # AUDIT04-D: the completion sentinel is cleared on the same principle.
  done_pre=$(done_path_for "$f")
  [[ -n "$done_pre" && -f "$done_pre" ]] && rm -f "$done_pre"
  if [[ -n "$TESTMODE" ]]; then
    perl -e 'alarm shift @ARGV; exec @ARGV or die "exec failed: $!"' "$TIMEOUT_SECS" "$KERNEL" -script "$f" mode="$TESTMODE"
  else
    perl -e 'alarm shift @ARGV; exec @ARGV or die "exec failed: $!"' "$TIMEOUT_SECS" "$KERNEL" -script "$f"
  fi
  rc=$?
  kmsg=""
  if [[ $rc -ne 0 ]]; then
    kmsg=" (kernel exit=$rc, timeout>${TIMEOUT_SECS}s?)"
  fi
  sp=$(status_path_for "$f")
  if [[ -z "$sp" ]]; then
    verdict="NO STATUS EXPORTED (no results/tests/<name> path in script)"
  else
    verdict="$(classify_status "$sp")"
  fi
  # AUDIT04-D: three-way judgement, because a non-zero kernel exit was conflating
  # two different events and blocking roughly one push in three.
  #
  # Measured 2026-09-06: 3 crashes in ~9 full-suite runs, on THREE DIFFERENT
  # tests (TSK-ARCH-006, NANDTests, TSK-GATES-001), with and without competing
  # load, each clean 3/3 standalone, and in every case the test had already
  # written OK. The kernel dies at SHUTDOWN, after the verdict.
  #
  # A fresh verdict alone does not prove completion -- Status.txt is followed by
  # further exports in most tests, so a kernel dying between them leaves a
  # plausible OK beside incomplete artefacts. The sentinel does prove it: it is
  # deleted before the run and written as the test's LAST expression, so its
  # presence means every line above it evaluated.
  #
  # The sentinel is therefore REQUIRED in all cases, not only on a crash. That
  # also closes the older AUDIT03 hole from the other side: a kernel that skips a
  # malformed expression and exits 0 now fails here, where before it was scored
  # by whatever status happened to be on disk.
  dp=$(done_path_for "$f")
  if [[ -z "$dp" || ! -f "$dp" ]]; then
    FAIL=$((FAIL+1))
    FAILED_NAMES+=("$bn")
    echo "FAIL: $bn -> $verdict$kmsg [NO COMPLETION SENTINEL: the test did not reach its last line]"
  elif [[ "$verdict" == "PASS" && $rc -eq 0 ]]; then
    OK=$((OK+1))
    echo "OK: $bn"
  elif [[ "$verdict" == "PASS" && $rc -ne 0 ]]; then
    # Verdict written, sentinel written, kernel died on the way out.
    OK=$((OK+1))
    CRASHED_NAMES+=("$bn (exit $rc)")
    echo "OK: $bn  [KERNEL CRASHED AFTER COMPLETING, exit=$rc -- counted as a pass because the completion sentinel is present; recorded, not hidden]"
  else
    FAIL=$((FAIL+1))
    FAILED_NAMES+=("$bn")
    echo "FAIL: $bn -> $verdict$kmsg"
  fi
done
# AUDIT04 — the rollup file must not be writable by a run that is not a rollup.
#
# Until now every invocation wrote results/tests/runall/Status.txt, so
# `--section Compare` (2 tests) overwrote the record of `--all` (69 tests) and
# left a TRACKED file whose name claims a denominator it does not have. Two
# documents cite that file as the whole-suite rollup, so the overwrite silently
# rewrote the evidence they rest on. This is the comfortable-denominator defect
# this audit exists to remove, sitting inside the runner itself.
#
# A partial run now writes its OWN file and states its scope on the line; only a
# full run may touch the rollup.
if [[ -n "$SECTION" ]]; then
  SCOPE="section:$SECTION"
  [[ -n "$GATE" ]] && SCOPE="$SCOPE gate:$GATE"
  SUMMARY_DIR="$REPO_DIR/results/tests/section-$SECTION${GATE:+-$GATE}"
else
  SCOPE="all"
  SUMMARY_DIR="$REPO_DIR/results/tests/runall"
fi
mkdir -p "$SUMMARY_DIR"
echo "OK=$OK FAIL=$FAIL TOTAL=$((${#FILTERED[@]})) SCOPE=$SCOPE" | tee "$SUMMARY_DIR/Status.txt"
if [[ ${#CRASHED_NAMES[@]} -gt 0 ]]; then
  printf 'KERNEL CRASHED AFTER COMPLETING (counted as passes, sentinel present): %s\n' "${(j:, :)CRASHED_NAMES}" | tee -a "$SUMMARY_DIR/Status.txt"
fi
if [[ ${#FAILED_NAMES[@]} -gt 0 ]]; then
  printf 'TRUE DETAIL: FAILED=%s\n' "${(j:, :)FAILED_NAMES}" | tee -a "$SUMMARY_DIR/Status.txt"
fi
# T0.1b: sections carrying SKIP_REASON.txt are reported, never silent
for sr in "$ROOT_DIR"/*/SKIP_REASON.txt(N); do
  sec="${sr:h:t}"
  echo "SKIPPED SECTION: $sec — $(head -n1 "$sr")" | tee -a "$SUMMARY_DIR/Status.txt"
done
[[ $FAIL -eq 0 ]]
