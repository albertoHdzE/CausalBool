#!/usr/bin/env zsh
# AUDIT03-C — the closure set, run as one command, WITH A REAL EXIT CODE.
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
# Usage:  run_closure.sh [pure|wolfram|all]      (default: all)
#
#   exit 0  every member passed (UNKNOWNs allowed, and named)
#   exit 1  at least one member failed
#   exit 2  refused: nothing to run

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 2

TIER="${1:-all}"
KERNEL=/Applications/Wolfram.app/Contents/MacOS/WolframKernel

names=(); verdicts=(); tiers=()
NFAIL=0; NUNKNOWN=0; NPASS=0

run_member() {
  local tier="$1" label="$2"; shift 2
  echo ""
  echo "── ${label}"
  "$@"
  local rc=$?
  local verdict
  case $rc in
    0) verdict=PASS;    NPASS=$((NPASS+1));;
    2) verdict=UNKNOWN; NUNKNOWN=$((NUNKNOWN+1));;
    *) verdict=FAIL;    NFAIL=$((NFAIL+1));;
  esac
  names+=("$label"); verdicts+=("$verdict"); tiers+=("$tier")
  echo "   -> ${verdict} (exit ${rc})"
}

# ── PURE TIER — no WolframKernel required; this is what CI runs ──────────────
run_pure() {
  run_member pure "paper-number gate (manuscript CHANGE detector, not a correctness check)" \
    python3 tools/snapshot_paper_numbers.py --check
  run_member pure "GLOSSARY sync (document mirroring vs the sibling; does NOT check code)" \
    zsh tools/check_glossary_sync.sh
  run_member pure "GLOSSARY conformance (the code side the sync check cannot see)" \
    zsh tools/check_glossary_conformance.sh
  run_member pure "single-engine guard (one owner per concept)" \
    zsh tools/check_single_engine.sh
  run_member pure "core index (every owner named in GOVERNANCE/CORE.md still exists)" \
    zsh tools/check_core_index.sh
  run_member pure "test manifest (every tests/ file classified; no silent exclusions)" \
    zsh tools/check_test_manifest.sh
  # No pipe. The previous `| head -8` returned head's status, not the script's.
  run_member pure "table coverage (how much of the manuscripts a producer is wired to)" \
    venv/bin/python tools/enumerate_paper_tables.py
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
  run_member wolfram "Wolfram syntax (every .m/.wl parses; the suite cannot see a syntax error)" \
    env CB_REPO="$PWD" HOME="$HOME" "$KERNEL" -script tools/check_wolfram_syntax.wl
  run_member wolfram "paper artefacts (the only member that ties a number to its producer)" \
    python3 tools/verify_paper_artefacts.py
  # AUDIT03-C: both of these existed and neither was run by any routine command.
  run_member wolfram "cross-language parity (Python forward model == CausalBoolCore.wl)" \
    zsh tools/run_crosscheck_parity.sh
  run_member wolfram "description-length parity (executes the WL producer, not a stored number)" \
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
echo "CLOSURE (${TIER}): ${NPASS} pass, ${NFAIL} fail, ${NUNKNOWN} unknown, of ${total}"
echo "════════════════════════════════════════════════════════════════════"
for i in {1..$total}; do
  printf '  %-8s %-8s %s\n' "${verdicts[$i]}" "${tiers[$i]}" "${names[$i]}"
done

if [[ "$NUNKNOWN" -gt 0 ]]; then
  echo ""
  echo "UNKNOWN is not a pass. It means a member could not do the work it claims,"
  echo "usually an absent sibling repository or an absent WolframKernel."
fi

if [[ "$TIER" != "wolfram" && "$NFAIL" -eq 0 ]]; then
  echo ""
  echo "NOTE: the pure tier does NOT cover the Wolfram tier or the MUnit suite."
  echo "      Green here is not green overall. Run: make ci-local"
fi

[[ "$NFAIL" -eq 0 ]] || exit 1
