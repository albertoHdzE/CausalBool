#!/usr/bin/env zsh
# AUDIT03 — every Wolfram file under tests/MUnit must be CLASSIFIED.
#
# The defect this closes: the runner discovered tests with the glob `*Tests.m`,
# so 23 of 78 files were never executed and nobody knew. Ten of them were real
# conditional checks. A file that is neither collected nor declared missing is
# invisible, and invisible files rot -- one of them (TSK-ALGO-003) had been left
# syntactically broken by an earlier collapse in this very audit, and nothing
# went red.
#
# So membership is declared in tests/MUnit/MANIFEST.tsv and this asserts the
# declaration is complete and honest:
#
#   * every .m in the tree appears exactly once in the manifest
#   * every manifest path exists on disk
#   * every kind is one of test / quarantine / producer
#   * quarantine and producer entries carry a reason
#
#   exit 0  the manifest accounts for every file
#   exit 1  something is unclassified, missing, or unexplained
#   exit 2  refused: nothing to check
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
MANIFEST="tests/MUnit/MANIFEST.tsv"

[[ -f "$MANIFEST" ]] || { echo "TEST-MANIFEST: REFUSED  $MANIFEST is missing"; exit 2; }

# AUDIT03-B: the scan covers the WHOLE tests/ tree, not just tests/MUnit.
# Restricting it to MUnit is how tests/SelfTest.m, tests/MasterRunner.m and the
# two tests/Nature Level-3 tests stayed invisible -- an entire second suite,
# with its own runner, that no command in the repository invoked.
#
# AUDIT04-E: ...and it covers BOTH LANGUAGES. Until 2026-09-07 this line read
# `-name '*.m'`, so the denominator was 85 Wolfram files and the 24 Python test
# files under tests/ were declared by nothing -- while CLAUDE.md, CORE.md and
# VERIFICATION.md ("85 / 85") all stated the manifest covered ALL of tests/.
# The lint ledger in VERIFICATION.md had even counted "tests/ Lev4-7 runners 12"
# for F401 purposes, so one ledger knew about files the other could not see.
# That is the same invisible class as 2020's `*Tests.m` glob, one language over.
on_disk=$(find tests -type f \( -name '*.m' -o -name '*.py' \) \
            ! -name 'RunTests.m' ! -path '*__pycache__*' | sed 's|^\./||' | sort)
n_disk=$(printf '%s\n' "$on_disk" | grep -c . || true)
n_disk_m=$(printf '%s\n' "$on_disk" | grep -c '\.m$' || true)
n_disk_py=$(printf '%s\n' "$on_disk" | grep -c '\.py$' || true)
if [[ "$n_disk" -eq 0 ]]; then
  echo "TEST-MANIFEST: REFUSED  found 0 test files under tests/."
  echo "  A pass over zero files is not a pass."
  exit 2
fi
if [[ "$n_disk_m" -eq 0 || "$n_disk_py" -eq 0 ]]; then
  echo "TEST-MANIFEST: REFUSED  one language scanned 0 files (.m=$n_disk_m, .py=$n_disk_py)."
  echo "  A per-language zero is how the Python half stayed invisible; refuse rather than pass."
  exit 2
fi

STATUS=0

declared=$(grep -v '^[[:space:]]*#' "$MANIFEST" | grep -v '^[[:space:]]*$' | cut -f2 | sort)
n_decl=$(printf '%s\n' "$declared" | grep -c . || true)

# 1. unclassified files
missing_from_manifest=$(comm -23 <(printf '%s\n' "$on_disk") <(printf '%s\n' "$declared"))
if [[ -n "$missing_from_manifest" ]]; then
  echo "TEST-MANIFEST: FAIL  these files are NOT classified:"
  printf '  %s\n' ${(f)missing_from_manifest}
  echo "  -> add each to $MANIFEST as test / quarantine / producer, with a reason"
  STATUS=1
fi

# 2. manifest entries with no file
ghosts=$(comm -13 <(printf '%s\n' "$on_disk") <(printf '%s\n' "$declared"))
if [[ -n "$ghosts" ]]; then
  echo "TEST-MANIFEST: FAIL  these manifest entries have no file on disk:"
  printf '  %s\n' ${(f)ghosts}
  STATUS=1
fi

# 3. duplicates
dupes=$(printf '%s\n' "$declared" | uniq -d)
if [[ -n "$dupes" ]]; then
  echo "TEST-MANIFEST: FAIL  declared more than once:"
  printf '  %s\n' ${(f)dupes}
  STATUS=1
fi

# 4. kinds and reasons
while IFS=$'\t' read -r kind entry reason; do
  [[ -z "$kind" || "$kind" == \#* ]] && continue
  case "$kind" in
    test) ;;
    quarantine|producer)
      if [[ -z "${reason// /}" ]]; then
        echo "TEST-MANIFEST: FAIL  $entry is '$kind' with no reason given"
        STATUS=1
      fi;;
    *)
      echo "TEST-MANIFEST: FAIL  $entry has unknown kind '$kind'"
      STATUS=1;;
  esac
done < "$MANIFEST"
# NOTE: the loop variable is `entry`, never `path`. zsh TIES the array `path`
# to $PATH, so `read -r kind path` silently destroys PATH for the rest of the
# script and every later command becomes "command not found".

n_test=$(awk -F'\t' '$1=="test"{c++} END{print c+0}' "$MANIFEST")
n_quar=$(awk -F'\t' '$1=="quarantine"{c++} END{print c+0}' "$MANIFEST")
n_prod=$(awk -F'\t' '$1=="producer"{c++} END{print c+0}' "$MANIFEST")

# Split by language. The rollup below is written by the WOLFRAM runner, so it
# must be compared against the Wolfram test count alone -- comparing it against
# a mixed total would go red for the wrong reason the moment a Python test is
# declared, and "the gate is red so loosen the gate" is how gates die.
n_test_m=$(awk -F'\t'  '$1=="test" && $2 ~ /\.m$/  {c++} END{print c+0}' "$MANIFEST")
n_test_py=$(awk -F'\t' '$1=="test" && $2 ~ /\.py$/ {c++} END{print c+0}' "$MANIFEST")

echo "TEST-MANIFEST: ${n_decl}/${n_disk} files classified — ${n_test} test, ${n_quar} quarantine, ${n_prod} producer"
echo "TEST-MANIFEST: by language — ${n_disk_m} Wolfram (${n_test_m} test), ${n_disk_py} Python (${n_test_py} test)"
if [[ "$n_quar" -gt 0 ]]; then
  # AUDIT04-E: this note used to say quarantined files "export a literal status
  # and cannot fail", which was true of the Wolfram quarantines it was written
  # for. Every quarantine entry today is Python and RED or blocked, so the old
  # wording would have described a failing test as an inert one.
  echo "TEST-MANIFEST: note — ${n_quar} quarantined file(s), excluded ON PURPOSE with a reason each."
  echo "  Quarantine never means passing. Read the reason column: some are RED"
  echo "  against real code and are carried as open items in GOVERNANCE/VERIFICATION.md."
fi

# ------------------------------------------------------------------
# AUDIT04 — the manifest was CLASSIFICATION-only, which is half the honesty.
#
# Declaring 72 tests does not mean 72 tests RAN, and nothing compared the two.
# Both halves of that gap were live in this repository at once, and both were
# found by hand rather than by a gate:
#
#   1. The tracked rollup read OK=69 FAIL=0 TOTAL=69 against a manifest
#      declaring 72. Three tests added in Phase A (TSK-ARCH-005, TSK-ARCH-006,
#      TSK-BIO-METRICS-002) were never counted, because the rollup had not been
#      regenerated by a full run since. A suite can shrink by three and the
#      number still looks like a pass.
#
#   2. results/tests/arch6/Status.txt was committed reading FAIL while that same
#      rollup read FAIL=0. The commit message for f2c2f77 states "OK on restore",
#      and the full run of 2026-09-06 confirms the test does pass -- so the CLAIM
#      was true and the ARTEFACT was the one left behind by the last planted
#      mutant. Nothing contradicted it, because the only thing that could have
#      was a rollup that predated the test's existence.
#
# So the scope of this gate is now the test suite's BOOKKEEPING, not just its
# membership: what is declared, what ran, and what each verdict artefact says
# must be three views of one state.
# ------------------------------------------------------------------

ROLLUP="results/tests/runall/Status.txt"
if [[ ! -f "$ROLLUP" ]]; then
  echo "TEST-MANIFEST: FAIL  the rollup $ROLLUP is missing"
  echo "  It is a TRACKED artefact; regenerate with: zsh tests/MUnit/run-tests.sh --all"
  STATUS=1
else
  rollup_line=$(head -1 "$ROLLUP")
  r_total=$(printf '%s\n' "$rollup_line" | sed -n 's/.*TOTAL=\([0-9]*\).*/\1/p')
  r_fail=$(printf '%s\n' "$rollup_line" | sed -n 's/.*FAIL=\([0-9]*\).*/\1/p')
  r_scope=$(printf '%s\n' "$rollup_line" | sed -n 's/.*SCOPE=\([A-Za-z0-9:_-]*\).*/\1/p')

  if [[ -z "$r_scope" ]]; then
    echo "TEST-MANIFEST: FAIL  the rollup carries no SCOPE= field: '$rollup_line'"
    echo "  It predates the scope fix, so it cannot be shown to be a FULL run."
    echo "  Regenerate with: zsh tests/MUnit/run-tests.sh --all"
    STATUS=1
  elif [[ "$r_scope" != "all" ]]; then
    echo "TEST-MANIFEST: FAIL  the rollup was written by a PARTIAL run (SCOPE=$r_scope)"
    echo "  Only a full run may stand as the whole-suite record."
    STATUS=1
  elif [[ -z "$r_total" ]]; then
    echo "TEST-MANIFEST: FAIL  the rollup has no TOTAL= field: '$rollup_line'"
    STATUS=1
  elif [[ "$r_total" -ne "$n_test_m" ]]; then
    echo "TEST-MANIFEST: FAIL  the runner scored ${r_total} tests, the manifest declares ${n_test_m} Wolfram tests"
    echo "  A declared test that never ran is exactly the invisible class this manifest exists to end."
    echo "  Regenerate with: zsh tests/MUnit/run-tests.sh --all"
    STATUS=1
  else
    echo "TEST-MANIFEST: rollup agrees — ${r_total} scored / ${n_test_m} declared Wolfram, SCOPE=${r_scope}"
  fi

  # Verdict artefacts must not contradict the rollup. Scanned over EVERY status
  # file under results/tests, so the denominator is printed and cannot be read
  # as zero.
  n_status=0
  orphan_fails=""
  while IFS= read -r sf; do
    [[ "$sf" == "$ROLLUP" ]] && continue
    n_status=$((n_status + 1))
    case "$(head -1 "$sf")" in
      FAIL*) orphan_fails="${orphan_fails}${sf}"$'\n' ;;
    esac
  done < <(find results/tests -type f -name 'Status*.txt' | sort)

  if [[ "$n_status" -eq 0 ]]; then
    echo "TEST-MANIFEST: REFUSED  found 0 status artefacts under results/tests."
    echo "  A scan over zero files is not a pass."
    exit 2
  fi

  if [[ -n "$orphan_fails" && "${r_fail:-0}" -eq 0 ]]; then
    echo "TEST-MANIFEST: FAIL  these artefacts read FAIL while the rollup reads FAIL=0:"
    printf '  %s\n' ${(f)orphan_fails}
    echo "  Either the rollup is stale, or a planted-mutant artefact was committed"
    echo "  in place of the restored run. Regenerate: zsh tests/MUnit/run-tests.sh --all"
    STATUS=1
  else
    echo "TEST-MANIFEST: verdict artefacts consistent — ${n_status} scanned, 0 contradict the rollup"
  fi
fi
# ------------------------------------------------------------------
# AUDIT04-E — the Python analogue of the rollup check.
#
# Declaring a Python file `test` must mean pytest COLLECTS it. Both halves of
# that could fail silently before: pytest.ini set `testpaths = tests/analysis`,
# and the TSK-...-Test.py naming matches neither `test_*.py` nor `*_test.py`, so
# pointing pytest at the other directories collected ZERO while every command
# still reported a pass. Comparing the two numbers is what makes "declared"
# and "ran" one statement instead of two.
#
# conftest.py builds its collect_ignore FROM this manifest, so a file declared
# quarantine or producer cannot be collected and a file declared test cannot be
# skipped -- there is no second list to drift.
# ------------------------------------------------------------------
PY=venv/bin/python
if [[ ! -x "$PY" ]]; then
  echo "TEST-MANIFEST: SKIPPED python collection check — no $PY"
  echo "  This is a REPORTED gap, not a pass: create the venv to close it."
else
  collected=$("$PY" -m pytest --collect-only -q -p no:cacheprovider 2>/dev/null \
              | sed -n 's|^\(tests/[^:]*\.py\)::.*|\1|p' | sort -u)
  n_coll=$(printf '%s\n' "$collected" | grep -c . || true)
  if [[ "$n_coll" -eq 0 ]]; then
    echo "TEST-MANIFEST: FAIL  pytest collected 0 files under tests/."
    echo "  A suite that collects nothing reports a pass; that is the defect this closes."
    STATUS=1
  else
    declared_py=$(grep -v '^[[:space:]]*#' "$MANIFEST" | awk -F'\t' '$1=="test" && $2 ~ /\.py$/ {print $2}' | sort -u)
    only_declared=$(comm -23 <(printf '%s\n' "$declared_py") <(printf '%s\n' "$collected"))
    only_collected=$(comm -13 <(printf '%s\n' "$declared_py") <(printf '%s\n' "$collected"))
    if [[ -n "$only_declared" ]]; then
      echo "TEST-MANIFEST: FAIL  declared 'test' but NOT collected by pytest:"
      printf '  %s\n' ${(f)only_declared}
      STATUS=1
    fi
    if [[ -n "$only_collected" ]]; then
      echo "TEST-MANIFEST: FAIL  collected by pytest but NOT declared 'test':"
      printf '  %s\n' ${(f)only_collected}
      STATUS=1
    fi
    [[ -z "$only_declared$only_collected" ]] && \
      echo "TEST-MANIFEST: pytest agrees — ${n_coll} files collected / ${n_test_py} declared Python"
  fi
fi

[[ "$STATUS" -eq 0 ]] || echo "TEST-MANIFEST: the manifest does not account for the tree"
exit $STATUS
