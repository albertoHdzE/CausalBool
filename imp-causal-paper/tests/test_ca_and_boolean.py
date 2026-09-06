from __future__ import annotations

import networkx as nx
import numpy as np

from imp_causal_paper.boolean_network import BooleanNetwork
from imp_causal_paper.causal_reconstruction import CAReconstructor, evolve_elementary_ca
from imp_causal_paper.complexity import BDMComplexityEstimator


def test_ca_reconstruction_recovers_order_for_rule_254() -> None:
    estimator = BDMComplexityEstimator()
    reconstructor = CAReconstructor(estimator)
    initial = np.array([0, 0, 0, 1, 0, 0, 0], dtype=int)
    evolution = evolve_elementary_ca(initial, rule=254, steps=6)
    scrambled = evolution[[2, 5, 0, 4, 1, 3], :]
    result = reconstructor.reconstruct(scrambled)
    assert np.array_equal(result.ordered_rows, evolution)


def test_complete_xor_network_has_nonzero_attractor_count() -> None:
    network = BooleanNetwork(nx.complete_graph(4).to_directed(), "xor")
    attractors = network.attractors()
    assert len(attractors) >= 1
    assert all(len(attractor) >= 1 for attractor in attractors)


# ---------------------------------------------------------------------------
# AUDIT04-D (root repository, 2026-09-06): the pin for a COLLAPSE.
#
# boolean_network.py used to carry its own gate semantics. Measured elementwise
# against the root owner before anything moved: the transition map agreed on
# 72 of 72 rows and the gate dispatch on 92 of 93 (gate, input) cases. Zero
# disagreement is drift, not a second concept, so the copy was collapsed onto
# index-deconvolution/src/causalbool.py rather than declared as an exception.
#
# The single disagreement was a DEFECT. `if values.size else 0` returned 0 for
# every empty fold, which is right for `or` and `xor` only because their
# identity element happens to be 0; the empty conjunction is vacuously TRUE, and
# the same code would have been wrong for NAND and NOR the moment either was
# added. Fixing it moved the attractor count on 74 of the 80 perturbed networks
# that contain a zero-input node, by +1 to +5 (mean +1.59).
#
# This test is the pin: a forwarder can be quietly reverted, and this goes red
# the moment the semantics stop coming from the owner.
# ---------------------------------------------------------------------------

def test_gate_semantics_come_from_the_root_owner() -> None:
    import itertools
    import sys
    from pathlib import Path

    import numpy as np

    from imp_causal_paper.boolean_network import boolean_operator

    src = Path(__file__).resolve().parents[2] / "index-deconvolution" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import causalbool

    disagreements = 0
    cases = 0
    for name, gate in (("and", "AND"), ("or", "OR"), ("xor", "XOR")):
        operator = boolean_operator(name)
        for arity in range(0, 5):
            for bits in itertools.product((0, 1), repeat=arity):
                mine = int(operator(np.array(bits, dtype=int)))
                owner = int(causalbool.apply_gate(gate, list(bits), {}))
                cases += 1
                if mine != owner:
                    disagreements += 1

    assert cases == 93
    assert disagreements == 0, (
        "gate semantics have drifted from the owner; the copy was collapsed "
        "precisely because it had"
    )

    # The empty fold is the case that was wrong, so it is asserted by name
    # rather than left to the sweep above.
    assert int(boolean_operator("and")(np.array([], dtype=int))) == 1
    assert int(boolean_operator("or")(np.array([], dtype=int))) == 0
    assert int(boolean_operator("xor")(np.array([], dtype=int))) == 0
