"""serial_validation -- small, auditable perturbation runs on validated owners.

This module is intentionally narrow in scope:

* enumerate deterministic connectivity perturbations,
* call the validated Wolfram owner comparison for each perturbed network,
* record correctness and elapsed time per perturbation,
* write JSONL traces that can later seed the larger experimental runner.

For now this is a *validation* runner, not the final production pipeline.
It is designed for small and medium networks where exhaustive comparison
against ``CreateRepertoiresDispatch`` remains feasible.

Current active policy:

* ``EDGE_ADD`` is the primary perturbation family.
* ``EDGE_REMOVE`` remains available for guarded studies.
* ``EDGE_FLIP`` is kept as a low-level combinatorial helper but is not part
  of the default experimental workflow, because it mixes addition with
  removal and therefore muddies interpretation.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from .full_behaviour import compare_full_behaviour_owners
from .io import write_json, write_jsonl
from .perturbations import (
    admissible_ball,
    ball,
    graph_distance,
    index as perturbation_index,
)
from .records import make_envelope, new_ids, seal


def sample_network_10_a() -> tuple[list[list[int]], list[str]]:
    """First 10-node hand-picked network for the doppel challenge."""
    cm = [
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    ]
    dyn = [
        "AND",
        "OR",
        "MAJORITY",
        "XOR",
        "AND",
        "OR",
        "MAJORITY",
        "XOR",
        "AND",
        "OR",
    ]
    return cm, dyn


def sample_network_10_b() -> tuple[list[list[int]], list[str]]:
    """Second 10-node hand-picked network for the doppel challenge."""
    cm = [
        [0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]
    dyn = ["OR", "AND", "OR", "AND", "OR", "AND", "OR", "AND", "OR", "XOR"]
    return cm, dyn


def _runtime_trace_record(
    *,
    config_id: str,
    network_label: str,
    cm: list[list[int]],
    perturbed_cm: list[list[int]],
    dyn: list[str],
    graph_dist: int,
    perturb_idx: int,
    comparison: dict[str, Any],
) -> dict[str, Any]:
    record = make_envelope("runtime_trace", config_id=config_id, sweep_id=None)
    record.update(
        {
            "network_label": network_label,
            "n": len(cm),
            "division_size": comparison.get("network", {}).get("division_size"),
            "graph_distance": graph_dist,
            "perturbation_index": perturb_idx,
            "base_cm": cm,
            "perturbed_cm": perturbed_cm,
            "dyn": dyn,
            "dispatch_rows": comparison.get("dispatch_rows"),
            "unique_output_patterns_dispatch": comparison.get("unique_output_patterns_dispatch"),
            "reconstructed_patterns": comparison.get("reconstructed_patterns"),
            "division_count": comparison.get("division_count"),
            "division_decimal_keys": comparison.get("division_decimal_keys"),
            "division_sumandos_keys": comparison.get("division_sumandos_keys"),
            "exact_match": comparison.get("exact_match"),
            "kernel_exit_code": comparison.get("kernel_exit_code"),
            "process_status": comparison.get("process_status"),
            "accepted_validation": comparison.get("accepted_validation", False),
            "elapsed_seconds": comparison.get("elapsed_seconds"),
        }
    )
    return seal(record)


def run_validation_series(
    cm: list[list[int]],
    dyn: list[str],
    *,
    network_label: str,
    division_size: int = 2,
    perturbation_kind: str = "EDGE_FLIP",
    k: int = 1,
    limit: int | None = None,
    forbid_zero_indegree_nodes: bool = True,
    out_dir: os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Run a small deterministic perturbation series with exact owner checks.

    ``limit`` applies after the identity case is included, so ``limit=3``
    means: base network plus the first two perturbations in deterministic
    order.
    """
    config_id, _ = new_ids()
    started_at = time.perf_counter()

    raw_matrices = ball(cm, k=k, kind=perturbation_kind)
    matrices = admissible_ball(
        cm,
        k=k,
        kind=perturbation_kind,
        forbid_zero_indegree_nodes=forbid_zero_indegree_nodes,
    )
    n_excluded = len(raw_matrices) - len(matrices)
    if limit is not None:
        matrices = matrices[:limit]

    traces: list[dict[str, Any]] = []
    for perturbed_cm in matrices:
        graph_dist = graph_distance(cm, perturbed_cm)
        perturb_idx = perturbation_index(cm, perturbed_cm, perturbation_kind)
        comparison = compare_full_behaviour_owners(
            perturbed_cm,
            dyn,
            division_size=division_size,
        )
        traces.append(
            _runtime_trace_record(
                config_id=config_id,
                network_label=network_label,
                cm=cm,
                perturbed_cm=perturbed_cm,
                dyn=dyn,
                graph_dist=graph_dist,
                perturb_idx=perturb_idx,
                comparison=comparison,
            )
        )

    summary: dict[str, Any] = {
        "config_id": config_id,
        "network_label": network_label,
        "n": len(cm),
        "division_size": division_size,
        "perturbation_kind": perturbation_kind,
        "k": k,
        "forbid_zero_indegree_nodes": forbid_zero_indegree_nodes,
        "n_candidates_before_filter": len(raw_matrices),
        "n_runs": len(traces),
        "n_excluded": n_excluded,
        "all_exact_match": all(t["accepted_validation"] for t in traces),
        "elapsed_seconds_total": time.perf_counter() - started_at,
        "elapsed_seconds_mean": (
            sum(t["elapsed_seconds"] for t in traces) / len(traces) if traces else 0.0
        ),
        "dispatch_rows_set": sorted({t["dispatch_rows"] for t in traces}),
        "reconstructed_patterns_min": (
            min(t["reconstructed_patterns"] for t in traces) if traces else None
        ),
        "reconstructed_patterns_max": (
            max(t["reconstructed_patterns"] for t in traces) if traces else None
        ),
    }

    if out_dir is not None:
        root = Path(out_dir)
        write_json(root / f"{network_label}_summary.json", summary)
        write_jsonl(root / f"{network_label}_runtime_trace.jsonl", traces)
        summary["artefacts"] = {
            "summary": str(root / f"{network_label}_summary.json"),
            "runtime_trace": str(root / f"{network_label}_runtime_trace.jsonl"),
        }

    return summary


def run_guarded_experiment_suite(
    cm: list[list[int]],
    dyn: list[str],
    *,
    network_label: str,
    division_size: int = 2,
    k: int = 1,
    perturbation_kinds: tuple[str, ...] = ("EDGE_ADD",),
    forbid_zero_indegree_nodes: bool = True,
    out_dir: os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Run the first guarded experiment suite over selected perturbation kinds.

    This is the first bridge between surgical validation and a real
    catalogue-style experiment: every admissible perturbation in the chosen
    kinds is evaluated, timed, and written to disk.

    By default the suite runs ``EDGE_ADD`` only. This is deliberate:
    additions are currently the cleanest validated perturbation family for
    the challenge. Removals can be studied separately under explicit guards.
    """
    suite: dict[str, Any] = {
        "network_label": network_label,
        "n": len(cm),
        "division_size": division_size,
        "k": k,
        "forbid_zero_indegree_nodes": forbid_zero_indegree_nodes,
        "kinds": {},
    }
    for perturbation_kind in perturbation_kinds:
        kind_label = perturbation_kind.lower()
        kind_out_dir = None
        if out_dir is not None:
            kind_out_dir = Path(out_dir) / kind_label
        summary = run_validation_series(
            cm,
            dyn,
            network_label=f"{network_label}_{kind_label}",
            division_size=division_size,
            perturbation_kind=perturbation_kind,
            k=k,
            limit=None,
            forbid_zero_indegree_nodes=forbid_zero_indegree_nodes,
            out_dir=kind_out_dir,
        )
        suite["kinds"][perturbation_kind] = summary

    suite["all_exact_match"] = all(
        summary["all_exact_match"] for summary in suite["kinds"].values()
    )
    suite["elapsed_seconds_total"] = sum(
        summary["elapsed_seconds_total"] for summary in suite["kinds"].values()
    )
    if out_dir is not None:
        root = Path(out_dir)
        write_json(root / f"{network_label}_guarded_suite_summary.json", suite)
        suite["artefacts"] = {
            "suite_summary": str(root / f"{network_label}_guarded_suite_summary.json")
        }
    return suite
