"""boundary_sweep -- targeted validation sweeps around structural boundaries.

This module is intentionally narrow: it characterises whether exact
agreement between the exhaustive owner and the compressed full-behaviour
owner depends on simple graph-side boundary conditions such as creating a
zero in-degree node.
"""
from __future__ import annotations

from typing import Any

from .full_behaviour import compare_full_behaviour_owners
from .perturbations import ball, graph_distance, index as perturbation_index


def indegrees(cm: list[list[int]]) -> list[int]:
    """Column sums of the adjacency matrix."""
    n = len(cm)
    return [sum(cm[row][col] for row in range(n)) for col in range(n)]


def sweep_single_edge_boundary(
    cm: list[list[int]],
    dyn: list[str],
    *,
    perturbation_kind: str,
    division_size: int = 2,
) -> dict[str, Any]:
    """Run all k=1 perturbations of one kind and classify the outcomes.

    The returned structure is designed for quick scientific interpretation:
    it aggregates exactness by whether the perturbation introduces at least
    one zero in-degree node.
    """
    matrices = ball(cm, k=1, kind=perturbation_kind)
    base_indegrees = indegrees(cm)
    rows: list[dict[str, Any]] = []
    for perturbed_cm in matrices:
        perturbed_indegrees = indegrees(perturbed_cm)
        comparison = compare_full_behaviour_owners(
            perturbed_cm,
            dyn,
            division_size=division_size,
        )
        rows.append(
            {
                "graph_distance": graph_distance(cm, perturbed_cm),
                "perturbation_index": perturbation_index(cm, perturbed_cm, perturbation_kind),
                "zero_indegree_nodes_before": sum(d == 0 for d in base_indegrees),
                "zero_indegree_nodes_after": sum(d == 0 for d in perturbed_indegrees),
                "created_zero_indegree_node": (
                    sum(d == 0 for d in perturbed_indegrees)
                    > sum(d == 0 for d in base_indegrees)
                ),
                "exact_match": comparison.get("exact_match"),
                "dispatch_rows": comparison.get("dispatch_rows"),
                "reconstructed_patterns": comparison.get("reconstructed_patterns"),
                "elapsed_seconds": comparison.get("elapsed_seconds"),
                "kernel_exit_code": comparison.get("kernel_exit_code"),
                "has_stdout_prefix": "kernel_stdout_prefix" in comparison,
            }
        )

    def _group(predicate: bool) -> list[dict[str, Any]]:
        return [r for r in rows if r["created_zero_indegree_node"] == predicate]

    false_group = _group(False)
    true_group = _group(True)

    def _summarise(group: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "n_cases": len(group),
            "n_exact_match_true": sum(r["exact_match"] is True for r in group),
            "n_exact_match_false": sum(r["exact_match"] is False for r in group),
            "n_with_stdout_prefix": sum(r["has_stdout_prefix"] for r in group),
            "mean_elapsed_seconds": (
                sum(r["elapsed_seconds"] for r in group) / len(group) if group else None
            ),
        }

    return {
        "perturbation_kind": perturbation_kind,
        "n_total": len(rows),
        "rows": rows,
        "created_zero_indegree_false": _summarise(false_group),
        "created_zero_indegree_true": _summarise(true_group),
    }
