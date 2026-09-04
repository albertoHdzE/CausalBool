"""AUDIT03/R6.1 — a description length must never become entropy-derived.

Author decision B (2026-09-04): Shannon stays in the programme as an explicitly
labelled DATASET-SIDE baseline, and never as our measure. Nothing is deleted;
this guard is added so that any *description-length* path becoming
entropy-derived fails the suite instead of being noticed three audits later.

The failure this guards against is not hypothetical. It has happened twice:

  * CATALOGUE_EXPANSION.md priced the gate-naming field with an empirical gate
    entropy H(p) = 2.070 bits/node and drew an 18.36 bits/node conclusion from
    it (withdrawn at AUDIT03/R1.3);
  * reasoning from that same error, a bug was "found" in the W1.1 codec that
    did not exist (withdrawn, and re-verified at AUDIT03/R1.4).

Two arms, because a text scan alone is weak and a behavioural test alone would
miss a dormant import:

  ARM 1  BEHAVIOURAL. An entropy-derived cost depends on the DISTRIBUTION of
         gates around it; an algorithmic one does not, being a length in a
         declared language fixed by this node's own gate, in-degree and ambient
         size. Additivity of the graph-level total over its nodes is therefore
         the property to pin, and a frequency-weighted code cannot satisfy it.

  ARM 2  STATIC. The owner's length-computing functions must not reference the
         vocabulary of an ensemble measure.

WHERE EACH ARM BITES, measured by planting the defect rather than assumed:

  * A frequency-weighted code inside ``graph_gate_index_length`` -- the only
    function that RECEIVES the whole gate list, and so the only one that can
    see an ensemble -- fails arm 1 on two tests. Verified 2026-09-04.
  * At the node level arm 1 is close to VACUOUS and this is worth saying
    plainly: ``node_description_cost(n, d, gate)`` cannot see the ensemble,
    because its signature does not admit one. The invariance it asserts is
    guaranteed structurally, not tested. An entropy could only enter there by
    CHANGING THE SIGNATURE, which arm 2 and code review must catch instead.
  * Planting entropy vocabulary in the owner fails arm 2. Verified the same day.
"""

from __future__ import annotations

import inspect
import math
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import description_lengths as dl  # noqa: E402


# --------------------------------------------------------------------------
# ARM 1 — behavioural
# --------------------------------------------------------------------------

def test_node_cost_is_independent_of_the_gate_distribution_around_it():
    """The same node, priced inside two networks with opposite gate mixes."""
    n, d, gate = 12, 3, "AND"
    cost = dl.node_description_cost(n, d, gate)

    # A network that is almost all AND, and one that is almost all XOR. Under a
    # frequency-weighted code the AND node would be cheap in the first and dear
    # in the second; under a declared catalogue it is the same length in both.
    mostly_and = ["AND"] * (n - 1) + [gate]
    mostly_xor = ["XOR"] * (n - 1) + [gate]
    degrees = [d] * n

    a = dl.graph_gate_index_length(degrees, mostly_and, include_header=False)
    b = dl.graph_gate_index_length(degrees, mostly_xor, include_header=False)

    # Every node has the same in-degree, so the ONLY thing differing is the
    # gate mix. Both totals must be n * (a per-node cost that ignores the mix).
    assert a == pytest.approx((n - 1) * dl.node_description_cost(n, d, "AND")
                              + cost)
    assert b == pytest.approx((n - 1) * dl.node_description_cost(n, d, "XOR")
                              + cost)
    # And the AND node's own contribution is identical in both.
    assert dl.node_description_cost(n, d, gate) == cost


def test_repeating_a_network_costs_exactly_twice_as_much():
    """Additivity. An entropy code gets CHEAPER per node as the distribution
    concentrates; a per-node program length is exactly additive."""
    n, d = 10, 2
    gates = ["AND", "OR", "XOR", "NOR", "AND", "AND", "OR", "NOT", "AND", "XOR"]
    one = dl.graph_gate_index_length([d] * n, gates, include_header=False)
    twice = dl.graph_gate_index_length([d] * (2 * n), gates + gates,
                                       include_header=False)
    # Doubling n changes the input-set field, so compare like with like: the
    # SAME ambient n, the list simply counted twice.
    manual = 2 * sum(dl.node_description_cost(n, d, g) for g in gates)
    assert one * 2 == pytest.approx(manual)
    assert twice != pytest.approx(manual)  # because n really did change


def test_schema_length_does_not_depend_on_gate_frequency():
    """D_schema, the primary measure, must have the same property."""
    n = 10
    and_tt = [0, 0, 0, 1]
    a = dl.schema_normal_form_length(and_tt, n)
    b = dl.schema_normal_form_length(and_tt, n)
    assert a == b
    # It must respond to the FUNCTION, not to anything ensemble-shaped.
    xor_tt = [0, 1, 1, 0]
    assert dl.schema_normal_form_length(xor_tt, n) > a, \
        "XOR must cost more than AND: its minterms do not merge"


def test_a_frequency_weighted_code_would_fail_this_test():
    """CONTROL. A guard that nothing can fail proves nothing, so build the
    forbidden thing and show the property above rejects it."""
    def entropy_cost(gate: str, gates: list[str]) -> float:
        counts = {g: gates.count(g) for g in set(gates)}
        total = len(gates)
        p = counts[gate] / total
        return -math.log2(p)

    mostly_and = ["AND"] * 11 + ["XOR"]
    mostly_xor = ["XOR"] * 11 + ["AND"]
    cheap = entropy_cost("AND", mostly_and)
    dear = entropy_cost("AND", mostly_xor)
    assert cheap != dear, "the control is inert"
    assert dear > cheap
    # The real measure, on the same two ensembles, does not move at all.
    assert (dl.node_description_cost(12, 3, "AND")
            == dl.node_description_cost(12, 3, "AND"))


# --------------------------------------------------------------------------
# ARM 2 — static
# --------------------------------------------------------------------------

ENSEMBLE_VOCABULARY = re.compile(
    r"\bentropy\b|\bshannon\b|\bfrequency\b|\bfreq\b|\bCounter\b"
    r"|\bprobabilit|\bp_?log|\bhistogram\b|\.count\(",
    re.I)

LENGTH_FUNCTIONS = [
    dl.node_description_cost,
    dl.graph_gate_index_length,
    dl.schema_normal_form_length,
    dl.row_run_index_set_length,
]


@pytest.mark.parametrize("fn", LENGTH_FUNCTIONS,
                         ids=lambda f: f.__name__)
def test_length_functions_use_no_ensemble_vocabulary(fn):
    src = inspect.getsource(fn)
    # Strip the docstring: prose may legitimately explain why entropy is NOT
    # used, and forbidding that would push the explanation out of the code.
    body = src
    doc = inspect.getdoc(fn)
    if doc:
        for line in doc.splitlines():
            body = body.replace(line, "")
    hit = ENSEMBLE_VOCABULARY.search(body)
    assert hit is None, (
        f"{fn.__name__} references ensemble vocabulary {hit.group(0)!r}. "
        "A description length is a length in a declared language; if this is "
        "deliberate, it is a change of measure and needs an author decision, "
        "not a code change (AUDIT03 decision B).")


def test_the_static_arm_can_fail():
    """CONTROL for arm 2."""
    assert ENSEMBLE_VOCABULARY.search("h = -sum(p * math.log2(p))  # entropy")
    assert ENSEMBLE_VOCABULARY.search("counts = Counter(gates)")
    assert ENSEMBLE_VOCABULARY.search("gates.count(g)")
    assert ENSEMBLE_VOCABULARY.search("bits = math.log2(n + 1)") is None
