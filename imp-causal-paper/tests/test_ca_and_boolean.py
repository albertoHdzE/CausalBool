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
