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
  if [[ "$verdict" == "PASS" && $rc -eq 0 ]]; then
    OK=$((OK+1))
    echo "OK: $bn"
  else
    FAIL=$((FAIL+1))
    FAILED_NAMES+=("$bn")
    echo "FAIL: $bn -> $verdict$kmsg"
  fi
done
SUMMARY_DIR="$REPO_DIR/results/tests/runall"
mkdir -p "$SUMMARY_DIR"
echo "OK=$OK FAIL=$FAIL TOTAL=$((${#FILTERED[@]}))" | tee "$SUMMARY_DIR/Status.txt"
if [[ ${#FAILED_NAMES[@]} -gt 0 ]]; then
  printf 'TRUE DETAIL: FAILED=%s\n' "${(j:, :)FAILED_NAMES}" | tee -a "$SUMMARY_DIR/Status.txt"
fi
# T0.1b: sections carrying SKIP_REASON.txt are reported, never silent
for sr in "$ROOT_DIR"/*/SKIP_REASON.txt(N); do
  sec="${sr:h:t}"
  echo "SKIPPED SECTION: $sec — $(head -n1 "$sr")" | tee -a "$SUMMARY_DIR/Status.txt"
done
[[ $FAIL -eq 0 ]]
