from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from .boolean_network import BooleanNetwork, analyze_boolean_perturbations
from .causal_reconstruction import CAReconstructor, evolve_elementary_ca
from .complexity import BDMComplexityEstimator
from .marpa import MARPABuilder
from .mils import MILSReducer
from .perturbation import GraphPerturbationAnalyzer
from .reprogrammability import (
    absolute_reprogrammability,
    absolute_reprogrammability_trapezoid_proxy,
    combined_reprogrammability,
    combined_reprogrammability_trapezoid_proxy,
    relative_reprogrammability,
    relative_reprogrammability_algodyn_reference,
)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def draw_adjacency(ax: plt.Axes, matrix: np.ndarray, title: str) -> None:
    ax.imshow(matrix, cmap="binary", interpolation="nearest", aspect="auto")
    ax.set_title(title)
    ax.set_xlabel("Column")
    ax.set_ylabel("Row")


def draw_graph(ax: plt.Axes, graph: nx.Graph, title: str) -> None:
    pos = nx.spring_layout(graph, seed=7)
    nx.draw_networkx(
        graph,
        pos=pos,
        ax=ax,
        node_size=450,
        with_labels=True,
        font_size=8,
        width=1.5,
    )
    ax.set_title(title)
    ax.set_axis_off()


def run_graph_experiments(output_dir: Path, plot_dir: Path | None = None) -> dict:
    ensure_dir(output_dir)
    if plot_dir is None:
        plot_dir = output_dir
    ensure_dir(plot_dir)
    estimator = BDMComplexityEstimator()
    analyzer = GraphPerturbationAnalyzer(estimator)
    reducer = MILSReducer(estimator)
    marpa = MARPABuilder(estimator)

    graph = nx.complete_graph(6)
    signature = analyzer.signature(graph, what="edges")
    signature.to_csv(output_dir / "complete_graph_signature.csv", index=False)

    mils_result = reducer.reduce(graph, target_edge_count=10, method="greedy")
    nx.write_edgelist(mils_result.graph, output_dir / "mils_graph.edgelist", data=False)

    marpa_result = marpa.build(node_count=6, target_edge_count=7)
    nx.write_edgelist(marpa_result.graph, output_dir / "marpa_graph.edgelist", data=False)

    payload = {
        "graph_name": "complete_graph_6",
        "relative_reprogrammability": relative_reprogrammability(signature),
        "relative_reprogrammability_definition_status": "exact_to_paper_supplement",
        "relative_reprogrammability_algodyn_reference_variant": relative_reprogrammability_algodyn_reference(signature),
        "relative_reprogrammability_reference_discrepancy_status": "local_algodyn_reference_disagrees_with_paper",
        "absolute_reprogrammability": absolute_reprogrammability(signature),
        "absolute_reprogrammability_definition_status": "unresolved_no_operational_definition_recovered",
        "absolute_reprogrammability_trapezoid_proxy": absolute_reprogrammability_trapezoid_proxy(signature),
        "absolute_reprogrammability_proxy_status": "noncanonical_proxy_for_audit_only",
        "combined_reprogrammability": combined_reprogrammability(signature),
        "combined_reprogrammability_definition_status": "unresolved_inherits_absolute_reprogrammability_gap",
        "combined_reprogrammability_trapezoid_proxy": combined_reprogrammability_trapezoid_proxy(signature),
        "combined_reprogrammability_proxy_status": "noncanonical_proxy_for_audit_only",
        "mils_removed_edges": [list(edge) for edge in mils_result.removed_edges],
        "marpa_added_edges": [list(edge) for edge in marpa_result.added_edges],
    }
    write_json(output_dir / "summary.json", payload)

    plt.figure(figsize=(8, 4))
    plt.plot(signature.index, signature["delta"], marker="o")
    plt.title("Information Signature of K6")
    plt.xlabel("Sorted element rank")
    plt.ylabel("C(G) - C(G-e)")
    plt.tight_layout()
    plt.savefig(plot_dir / "paper_fig4_graph_signature.png")
    plt.close()

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    draw_graph(axes[0], graph, "Original K6")
    draw_graph(axes[1], mils_result.graph, "MILS Reduced Graph")
    draw_graph(axes[2], marpa_result.graph, "MARPA Graph")
    fig.tight_layout()
    fig.savefig(plot_dir / "graph_transformations.png")
    plt.close(fig)

    manifest = {
        "paper_figure_reference": "Figure 4A-4C and the MILS discussion in the paper body",
        "status": "qualitative_correspondence",
        "notes": [
            "The saved signature plot is an analogous information-signature visualization for a smaller synthetic graph.",
            "The MILS and MARPA graph drawings correspond to the same algorithmic interventions discussed in the paper.",
            "These are not the exact original paper panels, which used larger graph families and broader benchmark sets.",
        ],
        "plots": [
            "paper_fig4_graph_signature.png",
            "graph_transformations.png",
        ],
    }
    write_json(plot_dir / "plot_manifest.json", manifest)
    return payload


def run_ca_experiment(output_dir: Path, plot_dir: Path | None = None) -> dict:
    ensure_dir(output_dir)
    if plot_dir is None:
        plot_dir = output_dir
    ensure_dir(plot_dir)
    estimator = BDMComplexityEstimator()
    reconstructor = CAReconstructor(estimator)
    initial = np.array([0, 0, 0, 1, 0, 0, 0], dtype=int)
    evolution = evolve_elementary_ca(initial, rule=254, steps=6)
    permutation = np.array([2, 5, 0, 4, 1, 3])
    scrambled = evolution[permutation, :]
    reconstruction = reconstructor.reconstruct(scrambled)

    np.savetxt(output_dir / "original.csv", evolution, fmt="%d", delimiter=",")
    np.savetxt(output_dir / "scrambled.csv", scrambled, fmt="%d", delimiter=",")
    np.savetxt(output_dir / "reconstructed.csv", reconstruction.ordered_rows, fmt="%d", delimiter=",")
    reconstruction.ranking.to_csv(output_dir / "row_ranking.csv", index=False)

    payload = {
        "rule": 254,
        "scramble_permutation": permutation.tolist(),
        "recovered_permutation": list(reconstruction.permutation),
        "reconstruction_complexity": reconstruction.complexity,
        "inferred_rule": reconstruction.inferred_rule,
        "transition_matches": reconstruction.transition_matches,
        "exact_match": bool(np.array_equal(reconstruction.ordered_rows, evolution)),
    }
    write_json(output_dir / "summary.json", payload)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    draw_adjacency(axes[0], evolution, "Original CA Evolution")
    draw_adjacency(axes[1], scrambled, "Scrambled Observations")
    draw_adjacency(axes[2], reconstruction.ordered_rows, "Reconstructed Order")
    fig.tight_layout()
    fig.savefig(plot_dir / "paper_fig3_ca_reconstruction.png")
    plt.close(fig)

    plt.figure(figsize=(7, 4))
    plt.bar(reconstruction.ranking["row_index"], reconstruction.ranking["delta"])
    plt.title("Row Perturbation Ranking")
    plt.xlabel("Row Index in Reconstructed Order")
    plt.ylabel("C(S) - C(S without row)")
    plt.tight_layout()
    plt.savefig(plot_dir / "paper_fig3_row_perturbation_ranking.png")
    plt.close()

    manifest = {
        "paper_figure_reference": "Figure 3A-3C",
        "status": "qualitative_correspondence",
        "notes": [
            "The original paper used 9! order searches and larger trajectories including 200- and 280-step cases.",
            "This implementation reproduces the same reconstruction idea on a deterministic smaller rule-254 example.",
            "The saved plots therefore correspond to the paper's CA reconstruction panels in method, not in exact scale.",
        ],
        "plots": [
            "paper_fig3_ca_reconstruction.png",
            "paper_fig3_row_perturbation_ranking.png",
        ],
    }
    write_json(plot_dir / "plot_manifest.json", manifest)
    return payload


def run_boolean_experiment(output_dir: Path, plot_dir: Path | None = None) -> dict:
    ensure_dir(output_dir)
    if plot_dir is None:
        plot_dir = output_dir
    ensure_dir(plot_dir)
    graph = nx.complete_graph(4)
    network = BooleanNetwork(graph.to_directed(), "xor")
    attractors = network.attractors()
    perturbations = analyze_boolean_perturbations(graph, "xor")
    perturbations.to_csv(output_dir / "xor_complete_graph_perturbations.csv", index=False)

    payload = {
        "graph_name": "complete_graph_4",
        "operator": "xor",
        "attractor_count": len(attractors),
        "attractors": [list(map(list, attractor)) for attractor in attractors],
        "mean_delta_attractors": float(perturbations["delta_attractors"].mean()),
    }
    write_json(output_dir / "summary.json", payload)

    plt.figure(figsize=(8, 4))
    edge_labels = [f"{u}-{v}" for u, v in perturbations["edge"]]
    plt.bar(edge_labels, perturbations["delta_attractors"])
    plt.axhline(0.0, color="black", linewidth=1.0)
    plt.title("Boolean-Network Perturbation Effect")
    plt.xlabel("Perturbed Directed Edge")
    plt.ylabel("Delta Attractor Count")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(plot_dir / "paper_fig4_boolean_perturbations.png")
    plt.close()

    manifest = {
        "paper_figure_reference": "Figure 4D-4G",
        "status": "qualitative_correspondence",
        "notes": [
            "The paper reports distributions and perturbation trends across complete, ER, and scale-free Boolean networks.",
            "This implementation currently plots the perturbation response of a deterministic complete-graph Boolean network only.",
            "The saved plot is therefore a reduced analogue of the Boolean-network perturbation figures, not the exact paper panel.",
        ],
        "plots": [
            "paper_fig4_boolean_perturbations.png",
        ],
    }
    write_json(plot_dir / "plot_manifest.json", manifest)
    return payload
