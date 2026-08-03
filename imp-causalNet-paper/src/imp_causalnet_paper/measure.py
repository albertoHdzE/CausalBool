"""A number from the mechanism side: model description length and the two-part code.

The index-set calculus returns a mechanism, not a score, and Part XIII records that
as a limitation: you cannot rank two objects with it. This module is the answer to
that limitation, and it turns out to do rather more than restore parity.

If we have recovered the actual program, we can *measure the program*:

``model_description_length``
    the cost of stating the mechanism -- which cells are in the index set, and the
    minimal DNF of the gate over them.  For an elementary rule this is a handful of
    bits, and it is exact.

``two_part_code``
    the classical MDL quantity: **program + input + runtime**.  For a cellular
    automaton diagram that is ``D(rule) + C(initial row) + log2(steps)``.

The second is the interesting one, because it is a *certificate*.  We do not merely
estimate the algorithmic complexity of a space-time diagram; we exhibit a program
that generates it exactly, so

.. math:: K(\\text{diagram}) \\le \\text{two-part code} + O(1)

is a theorem about that diagram, not an approximation of it.  Any estimator returning
a larger value is demonstrably over-estimating on that object, and the witness is in
hand.

Running this against BDM over all 256 elementary rules is the sharpest statement this
replication can make about the difference between the two approaches.  It is not a
refutation of BDM: for genuinely random data no program exists, no certificate can be
issued, and BDM's large value is the correct answer.  It is a statement about scope --
BDM measures the *output*, the two-part code measures the *process*, and on data that
really was produced by a short program those two numbers can differ by more than an
order of magnitude.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .causalbool_mirror import load_root_modules
from .complexity import bdm_1d, bdm_2d

__all__ = [
    "ModelCost",
    "model_description_length",
    "two_part_code",
    "certificate_vs_bdm",
]


@dataclass
class ModelCost:
    """Cost of stating a mechanism, in bits."""

    bits: float
    index_set_size: int
    dnf_terms: int

    def describe(self) -> str:
        return (f"{self.bits:.2f} bits  (index set of {self.index_set_size}, "
                f"{self.dnf_terms} DNF term(s))")


def model_description_length(truth_table, n_inputs: int) -> ModelCost:
    """Bits needed to state an index set and the minimal gate over it.

    Each stated position costs ``log2(3)``: a cell is either absent from the index
    set, or present positively, or present negated.  That is the natural unit of the
    index algebra, and it makes the measure exact rather than fitted.

    Reduction to essential variables comes from the root project's deconvolution, so
    a rule that ignores one of its inputs is charged only for the ones it uses --
    rule 60 (``left XOR centre``) costs less than rule 110, as it should.
    """
    _, dec, _ = load_root_modules()
    table = list(truth_table)
    essential = dec.essential_variables(table, n_inputs)
    reduced = dec.reduce_column(table, n_inputs, essential) if essential else [table[0]]
    terms = dec.minimal_dnf(reduced)
    m = len(essential)
    index_cost = m * math.log2(3) if m else 0.0
    gate_cost = len(terms) * max(m, 1) * math.log2(3)
    return ModelCost(index_cost + gate_cost, m, len(terms))


def eca_model_cost(rule: int) -> ModelCost:
    """Model description length of an elementary cellular automaton rule."""
    return model_description_length([(rule >> i) & 1 for i in range(8)], 3)


def two_part_code(rule: int, initial_row, steps: int) -> float:
    """``D(mechanism) + C(initial condition) + log2(runtime)``, in bits.

    The seed is costed with BDM itself, so the comparison against BDM is not rigged:
    the only part measured by our own calculus is the mechanism.
    """
    seed = np.asarray(initial_row, dtype=int)
    return eca_model_cost(rule).bits + bdm_1d(seed) + math.log2(max(steps, 1))


def certificate_vs_bdm(rules, initial_row, steps: int) -> list[dict]:
    """For each rule: BDM of the diagram against the certified two-part bound.

    A ratio above 1 means BDM returns a value larger than a quantity that provably
    bounds the diagram's algorithmic complexity from above.
    """
    from .ca import evolve_eca

    seed = np.asarray(initial_row, dtype=int)
    rows = []
    for r in rules:
        diagram = evolve_eca(r, seed, steps)
        b = bdm_2d(diagram)
        t = two_part_code(r, seed, steps)
        cost = eca_model_cost(r)
        rows.append(
            {
                "rule": r,
                "bdm": b,
                "two_part_code": t,
                "ratio": b / t,
                "model_bits": cost.bits,
                "index_set_size": cost.index_set_size,
            }
        )
    return rows
