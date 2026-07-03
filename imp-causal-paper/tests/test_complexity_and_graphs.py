from __future__ import annotations

import json

import networkx as nx
import numpy as np
import pandas as pd

from imp_causal_paper.complexity import BDMComplexityEstimator
from imp_causal_paper.experiments import run_graph_experiments
from imp_causal_paper.marpa import MARPABuilder
from imp_causal_paper.mils import MILSReducer
from imp_causal_paper.perturbation import GraphPerturbationAnalyzer
from imp_causal_paper.reprogrammability import (
    absolute_reprogrammability,
    absolute_reprogrammability_trapezoid_proxy,
    combined_reprogrammability,
    combined_reprogrammability_trapezoid_proxy,
    median_absolute_deviation,
    relative_reprogrammability,
    relative_reprogrammability_algodyn_reference,
)


def test_signature_is_sorted_descending() -> None:
    estimator = BDMComplexityEstimator()
    analyzer = GraphPerturbationAnalyzer(estimator)
    signature = analyzer.signature(nx.path_graph(5), what="edges")
    deltas = signature["delta"].to_numpy()
    assert np.all(deltas[:-1] >= deltas[1:])


def test_inforank_uses_descending_min_ties() -> None:
    estimator = BDMComplexityEstimator()
    analyzer = GraphPerturbationAnalyzer(estimator)
    ranked = analyzer.inforank(nx.cycle_graph(6), what="edges")
    expected = ranked["delta"].rank(method="min", ascending=False)
    assert np.allclose(ranked["inforank"].to_numpy(dtype=float), expected.to_numpy(dtype=float))


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


def test_reprogrammability_boundary_preserves_only_relative_as_canonical() -> None:
    estimator = BDMComplexityEstimator()
    analyzer = GraphPerturbationAnalyzer(estimator)
    signature = analyzer.signature(nx.cycle_graph(6), what="edges")
    maximum = float(np.max(np.abs(signature["delta"].to_numpy(dtype=float))))
    expected_relative = (
        median_absolute_deviation(signature["delta"].to_numpy(dtype=float)) / maximum if maximum != 0.0 else 0.0
    )
    assert relative_reprogrammability(signature) == expected_relative
    assert absolute_reprogrammability(signature) is None
    assert combined_reprogrammability(signature) is None
    assert np.isfinite(absolute_reprogrammability_trapezoid_proxy(signature))
    assert np.isfinite(combined_reprogrammability_trapezoid_proxy(signature))


def test_relative_reprogrammability_paper_formula_uses_absolute_normalizer() -> None:
    signature = pd.DataFrame({"delta": [1.0, -4.0, 0.0]})
    paper_value = relative_reprogrammability(signature)
    reference_value = relative_reprogrammability_algodyn_reference(signature)
    assert paper_value >= 0.0
    assert paper_value <= reference_value
    assert paper_value < reference_value


def test_graph_experiment_summary_carries_definition_statuses(tmp_path) -> None:
    output_dir = tmp_path / "graphs"
    plots_dir = tmp_path / "plots"
    run_graph_experiments(output_dir, plots_dir)
    summary = json.loads((output_dir / "summary.json").read_text())
    assert summary["relative_reprogrammability_definition_status"] == "exact_to_paper_supplement"
    assert summary["relative_reprogrammability_reference_discrepancy_status"] == (
        "local_algodyn_reference_disagrees_with_paper"
    )
    assert summary["absolute_reprogrammability_definition_status"] == "unresolved_no_operational_definition_recovered"
    assert summary["absolute_reprogrammability"] is None
    assert summary["absolute_reprogrammability_proxy_status"] == "noncanonical_proxy_for_audit_only"
    assert np.isfinite(summary["absolute_reprogrammability_trapezoid_proxy"])
    assert summary["combined_reprogrammability_definition_status"] == (
        "unresolved_inherits_absolute_reprogrammability_gap"
    )
    assert summary["combined_reprogrammability"] is None
    assert summary["combined_reprogrammability_proxy_status"] == "noncanonical_proxy_for_audit_only"
    assert np.isfinite(summary["combined_reprogrammability_trapezoid_proxy"])
    assert summary["relative_reprogrammability"] <= summary["relative_reprogrammability_algodyn_reference_variant"]
