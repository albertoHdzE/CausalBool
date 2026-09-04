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

STATUS=0

# One canonical owner per concept. AUDIT03/R2a.2 added the second group: weights,
# allOffsets and givePlaces had three independent definitions across the producer
# scripts. They were functionally identical (126/126 cases, verified in the kernel
# by audit/AUDIT03_R2_collapse/probe_alloffsets_parity.wl) but textually divergent
# -- corroboration_6node.wl lacked the empty-ws guard. Collapsed to one owner.
#
# audit/ is exempt: probe_alloffsets_parity.wl deliberately reproduces BOTH
# variants side by side in order to compare them, which is the one place a second
# definition is the point rather than the defect.
check_owner() {
  local canonical="$1"; shift
  for sym in "$@"; do
    files=$(grep -rlE "^[[:space:]]*${sym}\[[^]]*\][[:space:]]*:=" \
              --include='*.m' --include='*.wl' . 2>/dev/null \
            | sed 's|^\./||' \
            | grep -vE '^(archive|venv|audit|.*/\.venv)/' \
            | sort -u)
    count=$(printf '%s\n' "$files" | grep -c . || true)
    if [[ "$count" -eq 0 ]]; then
      echo "SINGLE-ENGINE: WARN  no definition site found for ${sym}"
      STATUS=1
    elif [[ "$count" -eq 1 && "$files" == "$canonical" ]]; then
      echo "SINGLE-ENGINE: ok    ${sym} defined only in ${canonical}"
    else
      echo "SINGLE-ENGINE: FAIL  ${sym} defined in ${count} files:"
      printf '  %s\n' ${(f)files}
      STATUS=1
    fi
  done
}

check_owner "src/integration/Alpha.m" createRepertoires runDynamic
check_owner "papers/method/code/lib/CausalBoolCore.wl" weights allOffsets

# givePlaces is DELIBERATELY not guarded, and the reason is recorded rather than
# left for someone to rediscover. Three definition sites exist and they are not
# one concept:
#   papers/method/code/lib/CausalBoolCore.wl  Sort@Flatten[Table[loc + sumandos]]
#   src/integration/Alpha.m:2732              -> unfoldLocationsAndSumandos, which
#       computes Sort[Flatten[Table[locations[[w]] + sumandos]]] -- COMPUTATIONALLY
#       IDENTICAL, but it lives in the engine, and CausalBoolCore.wl is standalone
#       by design ("No external packages required"). Collapsing across that
#       boundary would break the companion code's self-containment, which is a
#       deliberate property, not an accident.
#   tests/MUnit/Mixed/TSK-MIXED-001-OnPossibleBehaviour.m:28
#       givePlaces[beh_Association] := beh["Summands"] + 1 -- a DIFFERENT function
#       sharing the name, distinguished only by its argument pattern. Recorded as
#       a name collision; harmless at runtime, confusing to a reader.
# Revisit under AUDIT03/R2b if the standalone constraint is ever relaxed.

# AUDIT03/R2b — the per-node description length had EIGHT definition sites, four
# of which charged the log2(n+1) in-degree field and four of which did not, so
# "D" named two different quantities and only one of them was decodable. The
# Wolfram copies are collapsed onto Integration`BioMetrics`; the Python side onto
# src/description_lengths.py.
#
# The signature guarded is the input-set field, log2(Binomial[n, d]), which every
# copy of the cost model carries and nothing else in the tree does.
dl_files=$(grep -rlE 'log2Int\[Max\[1, *Binomial\[n, *d\]\]\]' \
             --include='*.m' --include='*.wl' . 2>/dev/null \
           | sed 's|^\./||' \
           | grep -vE '^(archive|venv|audit)/' \
           | sort -u)
dl_count=$(printf '%s\n' "$dl_files" | grep -c . || true)
if [[ "$dl_count" -eq 1 && "$dl_files" == "src/Packages/Integration/BioMetrics.m" ]]; then
  echo "SINGLE-ENGINE: ok    per-node description length defined only in src/Packages/Integration/BioMetrics.m"
else
  echo "SINGLE-ENGINE: FAIL  per-node description length defined in ${dl_count} Wolfram files:"
  printf '  %s\n' ${(f)dl_files}
  echo "  -> collapse onto Integration\`BioMetrics\`ComputeDescriptionLength (AUDIT03/R2b)"
  STATUS=1
fi

# Python side. imp-pathinfo-paper is a DOCUMENTED EXCEPTION, not an oversight:
# its mirror omits the in-degree field and its published tables depend on that,
# so it is pinned by the T4.5 fixture (B_legacy_pathinfo_no_indegree_bits) rather
# than silently corrected. See GOVERNANCE/DESCRIPTION_LENGTHS.md.
py_files=$(grep -rlE 'math\.log2\(len\(GATE_LABELS\)\)' \
             --include='*.py' . 2>/dev/null \
           | sed 's|^\./||' \
           | grep -vE '^(archive|venv|audit|.*/\.venv|.*/venv)/' \
           | sort -u)
py_expected="imp-pathinfo-paper/src/imp_pathinfo/causalbool_mirror.py
src/description_lengths.py"
if [[ "$py_files" == "$py_expected" ]]; then
  echo "SINGLE-ENGINE: ok    python description length: owner + 1 documented exception"
else
  echo "SINGLE-ENGINE: FAIL  python description-length sites changed:"
  printf '  %s\n' ${(f)py_files}
  echo "  -> expected exactly src/description_lengths.py plus the pinned"
  echo "     imp-pathinfo mirror; add a new site to DESCRIPTION_LENGTHS.md first"
  STATUS=1
fi

if [[ "$STATUS" -eq 0 ]]; then
  echo "SINGLE-ENGINE: clean"
else
  echo "SINGLE-ENGINE: a second engine definition site exists — reconcile or archive it"
fi
exit $STATUS
