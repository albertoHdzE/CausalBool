"""The three `src/` copies collapsed onto their owners (AUDIT04-D).

The core-loading guard was extended to scan `src/` on 2026-09-06 and immediately
found three modules implementing an owned concept privately. All three were
measured elementwise BEFORE anything moved, and the measurements decided what
happened to each:

    bio_D_experiment.encode_node_cost          0 of 180 -> drift, collapsed
    LogicParser._standard_gate_outputs         0 of 180 -> drift, collapsed
    phase_transition_experiment.step          27 of 124 -> TWO CONCEPTS, split

A forwarder can be quietly reverted and a rename can quietly drift back, so each
is pinned here. These tests fail the moment a copy stops coming from its owner.
"""

import itertools
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "index-deconvolution" / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "index-deconvolution" / "src"))

import causalbool  # noqa: E402

from src.description_lengths import node_description_cost  # noqa: E402
from src.integration.bio_D_experiment import encode_node_cost  # noqa: E402
from src.integration.LogicParser import LogicParser  # noqa: E402
from src.integration.phase_transition_experiment import (  # noqa: E402
    _OWNED_GATES,
)

TWELVE_FAMILIES = ("AND", "OR", "XOR", "NAND", "NOR", "XNOR",
                   "NOT", "IMPLIES", "NIMPLIES", "MAJORITY", "KOFN", "CANALISING")


def test_bio_d_experiment_cost_comes_from_the_owner():
    """0 of 180 was the measurement that justified collapsing; assert it holds.

    The copy had drifted before. The AUDIT03/R3.1 note records that the
    `log2(n + 1)` in-degree field went missing, which made the Kraft sum `n + 1`
    instead of 1 -- so the quantity was not a description length at all and every
    DeltaD built from it was a difference of two invalid lengths. Nothing caught
    that; this does.
    """
    disagreements = 0
    cases = 0
    for n in (4, 6, 8):
        for degree in range(0, min(4, n) + 1):
            row = np.array([1] * degree + [0] * (n - degree))
            for gate in TWELVE_FAMILIES:
                cases += 1
                if abs(encode_node_cost(row, gate, n)
                       - node_description_cost(n, degree, gate)) > 1e-12:
                    disagreements += 1
    assert cases == 180
    assert disagreements == 0


def test_logic_parser_reference_tables_come_from_the_owner():
    """The reference used to classify a truth table is the owner's semantics.

    This is not circular: the table being classified comes from EVALUATING A RULE
    STRING, and the reference comes from the gate semantics. Two independent
    sources, so the comparison is a real test.
    """
    disagreements = 0
    rows_seen = 0
    for arity in (1, 2, 3, 4):
        rows = np.array(list(itertools.product((0, 1), repeat=arity)))
        for name in ("AND", "OR", "XOR", "NAND", "NOR", "XNOR"):
            mine = LogicParser._standard_gate_outputs(name, rows)
            owner = np.array([causalbool.apply_gate(name, [int(b) for b in r], {})
                              for r in rows])
            rows_seen += len(rows)
            disagreements += int((mine != owner).sum())
    assert rows_seen == 180
    assert disagreements == 0


@pytest.mark.parametrize("gate", ["AND", "OR", "XOR"])
def test_phase_transition_delegates_the_owned_gates(gate):
    assert gate in _OWNED_GATES


def test_the_simplified_canalising_is_not_the_owner_s_canalising():
    """The rename must stay meaningful: these two must DISAGREE.

    27 of 124 cases disagreed, every one of them this gate. The owner's
    CANALISING takes canalisingIndex, canalisingValue and canalisedOutput; the
    experiment hard-codes "the first input decides". If they ever agree
    everywhere, the two names have collapsed into one concept and the split
    recorded here is no longer true.
    """
    def first_input_dominates(inputs):
        return 1 if (inputs and inputs[0] == 1) else 0

    disagreements = 0
    cases = 0
    for arity in (1, 2, 3):
        for bits in itertools.product((0, 1), repeat=arity):
            cases += 1
            owner = int(causalbool.apply_gate("CANALISING", list(bits), {}))
            if first_input_dominates(list(bits)) != owner:
                disagreements += 1
    assert cases == 14
    assert disagreements > 0, (
        "the private gate now matches the owner's CANALISING everywhere tested; "
        "if that is deliberate it should be collapsed, not kept under a "
        "different name"
    )


def test_an_unsupported_gate_refuses_rather_than_returning_zero():
    """AUDIT02/P1: a silent 0 is indistinguishable from a legitimate FALSE."""
    from src.integration import phase_transition_experiment as mod

    cls = next(v for v in vars(mod).values()
               if isinstance(v, type) and hasattr(v, "step"))
    net = cls(n=4, k=2, p_xor=0.0)
    net.dynamic = ["NOT_A_GATE"] * net.n
    with pytest.raises(ValueError):
        net.step([0, 0, 0, 0])


def test_bio_d_experiment_gate_dispatch_comes_from_the_owner():
    """The twelve families are the owner's; INPUT and IDENTITY are not gates.

    Measured 0 of 168 before collapsing. Two of those cases raise on BOTH sides
    (a one-input IMPLIES), which counts as agreement -- the first version of this
    check did not catch exceptions and mistook matching refusals for a defect.

    This file was briefly INVISIBLE to the core-loading guard: the ledger listed
    `import description_lengths` among the GATE owner's references, so collapsing
    the cost function onto the description-length owner silently cleared the gate
    flag on a file that still held a private twelve-family catalogue. The
    cross-concept credit has been removed; this test does not depend on it.
    """
    from src.integration.bio_D_experiment import apply_gate

    def evaluate(fn, gate, bits):
        try:
            return int(fn(gate, list(bits), {}))
        except Exception as exc:                      # noqa: BLE001
            return f"raised:{type(exc).__name__}"

    disagreements = 0
    cases = 0
    for gate in TWELVE_FAMILIES:
        for arity in (1, 2, 3):
            for bits in itertools.product((0, 1), repeat=arity):
                cases += 1
                if evaluate(apply_gate, gate, bits) != evaluate(
                        causalbool.apply_gate, gate, bits):
                    disagreements += 1
    assert cases == 168
    assert disagreements == 0

    # The corpus sentinels stay local, and refuse rather than answering 0.
    assert apply_gate("INPUT", [1], {}) == 1
    assert apply_gate("IDENTITY", [0], {}) == 0
    with pytest.raises(ValueError):
        apply_gate("INPUT", [], {})
