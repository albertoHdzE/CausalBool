"""add_edge_catalogue -- first proper add-edge catalogue for the challenge.

This module operationalises the first scientifically clean perturbation family:
single-edge additions that remain inside the admissible network class.

For each admissible perturbation, it computes:

* the exact attractor repertoire,
* the compressed length surrogate,
* KL / Jaccard / NCD relative to the base network,
* a simple target loss,
* an exactness validation flag against the Wolfram full-behaviour owners.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from .adapters import Network
from .attractors import enumerate_attractors
from .compression import encode_repertoire, ncd as ncd_pair
from .full_behaviour import compare_full_behaviour_owners
from .io import write_json, write_jsonl
from .perturbations import admissible_ball, graph_distance, index as perturbation_index
from .records import make_envelope, new_ids, seal
from .repertoire import compute_repertoire
from .stats import expected_loss, jaccard, kl


def _base_record(
    *,
    cm: list[list[int]],
    dyn: list[str],
    config_id: str,
    network_label: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    net = Network(n=len(cm), C=cm, gates=dyn, params=[{} for _ in range(len(cm))])
    rep = compute_repertoire(net)
    att = enumerate_attractors(net)
    cab = encode_repertoire(rep, include_schema=True)
    record = make_envelope("base_network", config_id=config_id, sweep_id=None)
    record.update(
        {
            "label": network_label,
            "A": cm,
            "theta": dyn,
            "params": [{} for _ in range(len(cm))],
            "N": len(cm),
            "n_attractors": att["n_attractors"],
            "attractor_sizes": att["attractor_sizes"],
            "n_attractor_states": len(att["support"]),
            "repertoire": rep,
            "compressed": {
                "decimal_bits": cab["decimal_bits"],
                "summandos_bits": cab["summandos_bits"],
                "L_CB_bits": cab["L_CB_bits"],
                "schema_length": cab["schema_length"],
            },
        }
    )
    return seal(record), rep


def _config_record(
    *,
    config_id: str,
    n: int,
    target_state: int,
    network_label: str,
) -> dict[str, Any]:
    record = make_envelope("configuration", config_id=config_id, sweep_id=None)
    record.update(
        {
            "network_label": network_label,
            "N": n,
            "k": 1,
            "perturbation_kind": "EDGE_ADD",
            "forbid_zero_indegree_nodes": True,
            "loss_id": "L_SINGLE_TARGET",
            "loss_params": {"targets": [target_state]},
            "division_size": 2,
        }
    )
    return seal(record)


def _catalogue_row(
    *,
    cm: list[list[int]],
    dyn: list[str],
    base_cm: list[list[int]],
    config_id: str,
    validation: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    net = Network(n=len(cm), C=cm, gates=dyn, params=[{} for _ in range(len(cm))])
    rep = compute_repertoire(net)
    att = enumerate_attractors(net)
    cab = encode_repertoire(rep, include_schema=False)
    row = make_envelope("catalogue_row", config_id=config_id, sweep_id=None)
    row.update(
        {
            "A": cm,
            "graph_distance": graph_distance(base_cm, cm),
            "perturbation_kind": "EDGE_ADD",
            "perturbation_index": perturbation_index(base_cm, cm, "EDGE_ADD"),
            "repertoire": rep,
            "n_attractors": att["n_attractors"],
            "attractor_sizes": att["attractor_sizes"],
            "compressed": {
                "decimal_bits": cab["decimal_bits"],
                "summandos_bits": cab["summandos_bits"],
                "L_CB_bits": cab["L_CB_bits"],
                "schema_length": cab["schema_length"],
            },
            "owner_validation": {
                "exact_match": validation["exact_match"],
                "kernel_exit_code": validation["kernel_exit_code"],
                "elapsed_seconds": validation["elapsed_seconds"],
                "dispatch_rows": validation["dispatch_rows"],
                "unique_output_patterns_dispatch": validation[
                    "unique_output_patterns_dispatch"
                ],
                "reconstructed_patterns": validation["reconstructed_patterns"],
            },
        }
    )
    return seal(row), rep


def _joint_row(
    *,
    catalogue_row: dict[str, Any],
    rep: dict[str, Any],
    base_rep: dict[str, Any],
    config_id: str,
    target_state: int,
) -> dict[str, Any]:
    k = kl(rep, base_rep)
    j = jaccard(rep, base_rep)
    n = ncd_pair(rep, base_rep)
    ell = expected_loss(
        rep,
        "L_SINGLE_TARGET",
        {"targets": [target_state]},
        q_dict=base_rep,
    )
    row = make_envelope("joint_row", config_id=config_id, sweep_id=None)
    row.update(
        {
            "A": catalogue_row["A"],
            "graph_distance": catalogue_row["graph_distance"],
            "perturbation_kind": "EDGE_ADD",
            "perturbation_index": catalogue_row["perturbation_index"],
            "ell": ell,
            "D_KL_nats": k["D_KL_nats"],
            "support_disjoint": k["support_disjoint"],
            "support_jaccard": j["support_jaccard"],
            "support_size_A": j["support_size_A"],
            "support_size_0": j["support_size_0"],
            "L_CB_A": n["L_CB_A"],
            "L_CB_0": n["L_CB_0"],
            "L_CB_concat": n["L_CB_concat"],
            "NCD": n["NCD"],
            "n_attractors": catalogue_row["n_attractors"],
            "attractor_sizes": catalogue_row["attractor_sizes"],
            "owner_validation_exact_match": catalogue_row["owner_validation"]["exact_match"],
            "owner_validation_elapsed_seconds": catalogue_row["owner_validation"][
                "elapsed_seconds"
            ],
        }
    )
    return seal(row)


def _write_progress(
    *,
    root: Path,
    network_label: str,
    n: int,
    completed_runs: int,
    total_runs: int,
    started_at: float,
) -> dict[str, Any]:
    """Write a live progress snapshot with elapsed time and ETA."""
    elapsed_seconds = time.perf_counter() - started_at
    mean_seconds_per_run = (
        elapsed_seconds / completed_runs if completed_runs > 0 else None
    )
    remaining_runs = total_runs - completed_runs
    estimated_remaining_seconds = (
        mean_seconds_per_run * remaining_runs
        if mean_seconds_per_run is not None
        else None
    )
    progress = {
        "network_label": network_label,
        "n": n,
        "completed_runs": completed_runs,
        "total_runs": total_runs,
        "remaining_runs": remaining_runs,
        "elapsed_seconds": elapsed_seconds,
        "mean_seconds_per_run": mean_seconds_per_run,
        "estimated_remaining_seconds": estimated_remaining_seconds,
        "fraction_complete": (completed_runs / total_runs if total_runs else 1.0),
    }
    write_json(root / "progress.json", progress)
    return progress


def _legacy_run_add_edge_catalogue(
    cm: list[list[int]],
    dyn: list[str],
    *,
    network_label: str,
    out_dir: os.PathLike[str],
    division_size: int = 2,
) -> dict[str, Any]:
    """Run the first proper add-edge catalogue and write its artefacts."""
    root = Path(out_dir)
    config_id, _ = new_ids()
    started_at = time.perf_counter()

    base_record, base_rep = _base_record(
        cm=cm,
        dyn=dyn,
        config_id=config_id,
        network_label=network_label,
    )
    target_state = base_rep["support"][0]
    config_record = _config_record(
        config_id=config_id,
        n=len(cm),
        target_state=target_state,
        network_label=network_label,
    )

    matrices = admissible_ball(
        cm,
        k=1,
        kind="EDGE_ADD",
        forbid_zero_indegree_nodes=True,
    )
    total_runs = len(matrices)
    _write_progress(
        root=root,
        network_label=network_label,
        n=len(cm),
        completed_runs=0,
        total_runs=total_runs,
        started_at=started_at,
    )

    catalogue_rows: list[dict[str, Any]] = []
    joint_rows: list[dict[str, Any]] = []
    for run_index, perturbed_cm in enumerate(matrices, start=1):
        validation = compare_full_behaviour_owners(
            perturbed_cm,
            dyn,
            division_size=division_size,
        )
        row, rep = _catalogue_row(
            cm=perturbed_cm,
            dyn=dyn,
            base_cm=cm,
            config_id=config_id,
            validation=validation,
        )
        catalogue_rows.append(row)
        joint_rows.append(
            _joint_row(
                catalogue_row=row,
                rep=rep,
                base_rep=base_rep,
                config_id=config_id,
                target_state=target_state,
            )
        )
        _write_progress(
            root=root,
            network_label=network_label,
            n=len(cm),
            completed_runs=run_index,
            total_runs=total_runs,
            started_at=started_at,
        )

    summary = {
        "config_id": config_id,
        "network_label": network_label,
        "perturbation_kind": "EDGE_ADD",
        "n": len(cm),
        "n_runs": len(catalogue_rows),
        "target_state": target_state,
        "all_exact_match": all(
            row["owner_validation"]["exact_match"] for row in catalogue_rows
        ),
        "elapsed_seconds_total": time.perf_counter() - started_at,
        "elapsed_seconds_mean_validation": (
            sum(row["owner_validation"]["elapsed_seconds"] for row in catalogue_rows)
            / len(catalogue_rows)
            if catalogue_rows
            else 0.0
        ),
        "D_KL_min": min(row["D_KL_nats"] for row in joint_rows),
        "D_KL_max": max(row["D_KL_nats"] for row in joint_rows),
        "NCD_min": min(row["NCD"] for row in joint_rows),
        "NCD_max": max(row["NCD"] for row in joint_rows),
        "support_jaccard_min": min(row["support_jaccard"] for row in joint_rows),
        "support_jaccard_max": max(row["support_jaccard"] for row in joint_rows),
        "ell_max": max(row["ell"] for row in joint_rows),
    }

    write_json(root / "config.json", config_record)
    write_json(root / "base.json", base_record)
    write_jsonl(root / "catalogue.jsonl", catalogue_rows)
    write_jsonl(root / "joint.jsonl", joint_rows)
    write_json(root / "summary.json", summary)
    _write_progress(
        root=root,
        network_label=network_label,
        n=len(cm),
        completed_runs=total_runs,
        total_runs=total_runs,
        started_at=started_at,
    )
    summary["artefacts"] = {
        "config": str(root / "config.json"),
        "base": str(root / "base.json"),
        "catalogue": str(root / "catalogue.jsonl"),
        "joint": str(root / "joint.jsonl"),
        "summary": str(root / "summary.json"),
        "progress": str(root / "progress.json"),
    }
    return summary


# Compatibility name: all new executions use the durable runner.  The legacy
# implementation above remains available only to reproduce historical pilot
# layouts and is deliberately not used by the prespecified study.
from .execution import run_catalogue as run_add_edge_catalogue  # noqa: F401
