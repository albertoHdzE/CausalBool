"""The Python half of the paper companion, pinned.

AUDIT04 Phase C. ``tools/check_core_loading.py`` found that
``papers/method/code/`` re-implements three owned concepts in Python:

    complexity_analysis._eval_gate            gate dispatch, twelve families
    complexity_analysis.build_output_table    the 2^n repertoire enumeration
    worked_example_7node.base_and_offsets     the offset family Omega

Those re-implementations are DELIBERATE and must stay. ``GOVERNANCE/CORE.md``
declares the companion self-contained because a reader reproducing the paper
runs it from a clean checkout, so it may not import the packaged core.

What was missing is the other half of that bargain. ``tools/run_crosscheck_parity.sh``
pins exactly one file --

    CB_CORE="$REPO/papers/method/code/lib/CausalBoolCore.wl"

-- so the WOLFRAM half of the companion is held at 135/135 and the PYTHON half
was held by nothing at all, while feeding published numbers on the flagship
path. A declared divergence without a measurement is an assertion, not evidence.

This fixture supplies the missing pin. It needs no kernel, so it runs in the
pure tier and cannot be skipped for want of Wolfram.

EACH ASSERTION PRINTS ITS DENOMINATOR and refuses on an empty case set: a
parity test that compares zero cases is the failure this audit keeps removing.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
COMPANION = REPO / "papers" / "method" / "code"

for _p in (
    COMPANION / "complexity_analysis",
    COMPANION / "worked_example_7node",
    REPO / "index-deconvolution" / "src",
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import causalbool as owner  # noqa: E402  the declared Python owner of gate dispatch
import complexity_analysis as ca  # noqa: E402
import worked_example_7node as wex  # noqa: E402


# --------------------------------------------------------------------------
# 1. Gate dispatch: the companion copy against the owner, elementwise.
# --------------------------------------------------------------------------

def _params_for(gate: str, width: int) -> dict:
    """Parameters the two families need. KOFN and CANALISING are parameterised;
    the rest ignore this."""
    if gate == "KOFN":
        return {"k": max(1, width // 2)}
    if gate == "CANALISING":
        return {"canalisingInput": 1, "canalisingValue": 1, "canalisedValue": 1}
    return {}


def test_companion_gate_dispatch_matches_the_owner_elementwise() -> None:
    """Every one of the twelve families, on every input vector up to width 4.

    This is the collapse protocol's elementwise measurement, made permanent:
    a disagreement count of zero is what licenses the two copies to coexist.
    """
    compared = 0
    disagreements: list[tuple[str, tuple[int, ...], int, int]] = []

    for gate in ca.GATE_LABELS:
        widths = [1] if gate == "NOT" else [2, 3, 4]
        for width in widths:
            params = _params_for(gate, width)
            for inputs in itertools.product([0, 1], repeat=width):
                got = ca._eval_gate(gate, list(inputs), params)
                want = owner.apply_gate(gate, list(inputs), params)
                compared += 1
                if got != want:
                    disagreements.append((gate, inputs, got, want))

    assert compared > 0, "refusing to pass on zero compared cases"
    assert not disagreements, (
        f"{len(disagreements)} of {compared} disagree with the owner: "
        f"{disagreements[:8]}"
    )
    print(f"gate dispatch: 0 disagreements over {compared} (gate, input) cases")


# --------------------------------------------------------------------------
# 2. The offset family, against an independent derivation.
# --------------------------------------------------------------------------
#
# Omega is the set of subset sums of the bit weights of the DISCONNECTED
# coordinates. Written out here from that definition rather than by calling the
# companion and recording what it returned.

def _independent_offsets(n: int, connected: list[int]) -> list[int]:
    free = [j for j in range(n) if j not in connected]
    weights = [1 << j for j in free]
    sums = {0}
    for w in weights:
        sums |= {s + w for s in sums}
    return sorted(sums)


@pytest.mark.parametrize("n", [3, 4, 5, 6, 7])
def test_offset_family_is_the_full_subset_sum_family(n: int) -> None:
    """Over every connected set of every size, for n up to the flagship's 7."""
    checked = 0
    for size in range(n + 1):
        for connected in itertools.combinations(range(n), size):
            cm = [[0] * n for _ in range(n)]
            for j in connected:
                cm[0][j] = 1
            dyn = ["AND"] * n
            _c, _d, _l, omega = wex.base_and_offsets(cm, dyn, 0)

            want = _independent_offsets(n, list(connected))
            assert omega == want, (
                f"n={n} connected={connected}: {omega} != {want}"
            )
            # A family of the right size and the wrong members is also wrong,
            # so the exact set is asserted above and the count below is a
            # second, independent handle on it.
            assert len(omega) == 2 ** (n - len(connected))
            checked += 1

    assert checked > 0, "refusing to pass on zero connected sets"
    print(f"n={n}: offset family exact on {checked} connected sets")


def test_the_empty_free_set_yields_a_single_zero_offset() -> None:
    """Every coordinate connected means no free ones, and the correct answer is
    the single offset {0}, not an empty family. CORE.md records that one of the
    three Wolfram copies lacked exactly this guard."""
    n = 4
    cm = [[1] * n for _ in range(n)]
    _c, _d, _l, omega = wex.base_and_offsets(cm, ["AND"] * n, 0)
    assert omega == [0]


# --------------------------------------------------------------------------
# 3. The repertoire enumeration, against an independent construction.
# --------------------------------------------------------------------------

def test_output_table_matches_an_independent_enumeration() -> None:
    """LSB-first ordering, 2^n rows, each node's inputs read from its own row of
    the connectivity matrix. Rebuilt here from that statement of the ordering
    rather than from the companion's own loop."""
    cm = [
        [0, 1, 1, 0],
        [1, 0, 0, 0],
        [0, 0, 0, 1],
        [1, 1, 0, 0],
    ]
    dyn = ["AND", "NOT", "OR", "XOR"]
    n = len(dyn)

    table = ca.build_output_table(cm, dyn, {})

    expected = []
    for idx in range(2 ** n):
        state = [(idx >> i) & 1 for i in range(n)]
        row = []
        for i in range(n):
            ins = [state[j] for j, v in enumerate(cm[i]) if v == 1]
            row.append(owner.apply_gate(dyn[i], ins, {}))
        expected.append(row)

    assert len(table) == 2 ** n, f"expected {2 ** n} rows, got {len(table)}"
    disagreeing = sum(1 for a, b in zip(table, expected) if a != b)
    assert disagreeing == 0, f"{disagreeing} of {2 ** n} rows disagree"
    print(f"repertoire: 0 disagreements over {2 ** n} rows")
