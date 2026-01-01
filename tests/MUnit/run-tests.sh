#!/usr/bin/env zsh
SECTION=""
GATE=""
MODE="all"
TESTMODE=""
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
    *)
      shift;;
  esac
done
ROOT_DIR=$(cd "$(dirname "$0")" && pwd)
SEARCH_DIRS=()
if [[ -n "$SECTION" ]]; then
  SEARCH_DIRS=("$ROOT_DIR/$SECTION")
else
  SEARCH_DIRS=("$ROOT_DIR" "$ROOT_DIR/Analysis" "$ROOT_DIR/Gates" "$ROOT_DIR/Pattern" "$ROOT_DIR/Theory" "$ROOT_DIR/Algo" "$ROOT_DIR/Mixed")
fi
TEST_FILES=()
for d in $SEARCH_DIRS; do
  if [[ -d "$d" ]]; then
    while IFS= read -r f; do TEST_FILES+="$f"; done < <(find "$d" -type f -name "*Tests.m")
  fi
done
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
OK=0; FAIL=0
for f in $FILTERED; do
  if [[ -n "$TESTMODE" ]]; then
    "$KERNEL" -script "$f" mode="$TESTMODE"
  else
    "$KERNEL" -script "$f"
  fi
  rc=$?
  if [[ $rc -eq 0 ]]; then
    OK=$((OK+1))
    echo "OK: $f"
  else
    FAIL=$((FAIL+1))
    echo "FAIL: $f"
  fi
done
SUMMARY_DIR="$ROOT_DIR/../../results/tests/runall"
mkdir -p "$SUMMARY_DIR"
echo "OK=$OK FAIL=$FAIL TOTAL=$((${#FILTERED[@]}))" | tee "$SUMMARY_DIR/Status.txt"
[[ $FAIL -eq 0 ]]