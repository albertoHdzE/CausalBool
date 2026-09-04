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

on_disk=$(find tests/MUnit -type f -name '*.m' ! -name 'RunTests.m' | sed 's|^\./||' | sort)
n_disk=$(printf '%s\n' "$on_disk" | grep -c . || true)
if [[ "$n_disk" -eq 0 ]]; then
  echo "TEST-MANIFEST: REFUSED  found 0 .m files under tests/MUnit."
  echo "  A pass over zero files is not a pass."
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

echo "TEST-MANIFEST: ${n_decl}/${n_disk} files classified — ${n_test} test, ${n_quar} quarantine, ${n_prod} producer"
if [[ "$n_quar" -gt 0 ]]; then
  echo "TEST-MANIFEST: note — ${n_quar} quarantined file(s) export a literal status and cannot fail."
  echo "  They are excluded ON PURPOSE. Give one a predicate to promote it to 'test'."
fi
[[ "$STATUS" -eq 0 ]] || echo "TEST-MANIFEST: the manifest does not account for the tree"
exit $STATUS
