from __future__ import annotations

import networkx as nx
import numpy as np

from imp_causal_paper.complexity import BDMComplexityEstimator
from imp_causal_paper.marpa import MARPABuilder
from imp_causal_paper.mils import MILSReducer
from imp_causal_paper.perturbation import GraphPerturbationAnalyzer
from imp_causal_paper.reprogrammability import combined_reprogrammability, relative_reprogrammability


def test_signature_is_sorted_descending() -> None:
    estimator = BDMComplexityEstimator()
    analyzer = GraphPerturbationAnalyzer(estimator)
    signature = analyzer.signature(nx.path_graph(5), what="edges")
    deltas = signature["delta"].to_numpy()
    assert np.all(deltas[:-1] >= deltas[1:])


def test_mils_greedy_hits_requested_edge_count() -> None:
    estimator = BDMComplexityEstimator()
    reducer = MILSReducer(estimator)
    graph = nx.complete_graph(5)
    result = reducer.reduce(graph, target_edge_count=6, method="greedy")
    assert result.graph.number_of_edges() == 6
    assert len(result.removed_edges) == graph.number_of_edges() - 6


def test_marpa_reaches_target_edge_count_without_duplicates() -> None:
    estimator = BDMComplexityEstimator()
    builder = MARPABuilder(estimator)
    result = builder.build(node_count=5, target_edge_count=4)
    assert result.graph.number_of_edges() == 4
    assert len(result.added_edges) == len(set(result.added_edges)) == 4


def test_reprogrammability_indices_are_finite() -> None:
    estimator = BDMComplexityEstimator()
    analyzer = GraphPerturbationAnalyzer(estimator)
    signature = analyzer.signature(nx.cycle_graph(6), what="edges")
    assert np.isfinite(relative_reprogrammability(signature))
    assert np.isfinite(combined_reprogrammability(signature))
