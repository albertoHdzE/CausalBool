#!/usr/bin/env zsh
# AUDIT02/P4e — single-engine guard.
#
# The repository carried two near-copies of a ~6,300-line engine for months:
# src/integration/Alpha.m (live, loaded by src/Packages/Integration/Alpha.m and
# Experiments.m) and src/causal/CausalBool.m (loaded by nothing). They shared
# ancestry, then received DIFFERENT later fixes, so neither was a superset. The
# second copy has been retired to archive/causal-exploratory/.
#
# This guard stops a second engine reappearing silently. It asserts that the
# defining occurrences of the core repertoire/dynamics entry points live in
# exactly one file outside archive/.
#
#   exit 0  single engine
#   exit 1  a second definition site appeared

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1

CANONICAL="src/integration/Alpha.m"
STATUS=0

for sym in createRepertoires runDynamic; do
  # definition sites only: "name[args] :=" at the start of a line
  files=$(grep -rlE "^[[:space:]]*${sym}\[[^]]*\][[:space:]]*:=" \
            --include='*.m' --include='*.wl' . 2>/dev/null \
          | sed 's|^\./||' \
          | grep -vE '^(archive|venv|.*/\.venv)/' \
          | sort -u)
  count=$(printf '%s\n' "$files" | grep -c . || true)
  if [[ "$count" -eq 0 ]]; then
    echo "SINGLE-ENGINE: WARN  no definition site found for ${sym}"
    STATUS=1
  elif [[ "$count" -eq 1 && "$files" == "$CANONICAL" ]]; then
    echo "SINGLE-ENGINE: ok    ${sym} defined only in ${CANONICAL}"
  else
    echo "SINGLE-ENGINE: FAIL  ${sym} defined in ${count} files:"
    printf '  %s\n' ${(f)files}
    STATUS=1
  fi
done

if [[ "$STATUS" -eq 0 ]]; then
  echo "SINGLE-ENGINE: clean"
else
  echo "SINGLE-ENGINE: a second engine definition site exists — reconcile or archive it"
fi
exit $STATUS
