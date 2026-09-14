"""Exact compressed full-behaviour scaling benchmark.

This is deliberately separate from :mod:`doppel_challenge.scaling`, whose
``run_scale_benchmark`` measures an approximate long-run attractor estimator.
The benchmark here measures the one-step DecimalRepertoire/Sumandos owner and
records the boundary between a fully materialised N=8 proof and compressed-only
N=10/N=12 runs.
"""
from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .compression import bdm_full_behaviour
from .execution import source_provenance
from .full_behaviour import compute_full_behaviour_encoding
from .io import atomic_write_json
from .pilot_runner import make_network
from .records import make_envelope, seal
from .schema import validate_record


DEFAULT_FULL_BEHAVIOUR_SIZES = (8, 10, 12)
DEFAULT_FULL_BEHAVIOUR_BASES = ("ring", "hub")
DEFAULT_FULL_BEHAVIOUR_EDGE_KINDS = ("base", "edge_add", "edge_remove")


def _topology_digest(cm: list[list[int]], dyn: list[str]) -> str:
    payload = json.dumps({"cm": cm, "dyn": dyn}, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _edge_variant(cm: list[list[int]], kind: str) -> tuple[list[list[int]], dict[str, int] | None]:
    """Apply one deterministic admissible-looking edge change.

    The benchmark is about the owner, not perturbation admissibility.  For
    removals we nevertheless keep every node with at least one input so that
    the two edge directions remain comparable across sizes.
    """
    result = [list(row) for row in cm]
    n = len(result)
    if kind == "base":
        return result, None
    if kind == "edge_add":
        candidates = ((target, source) for target in range(n)
                      for source in range(n) if target != source and not result[target][source])
    elif kind == "edge_remove":
        candidates = ((target, source) for target in range(n)
                      for source in range(n) if result[target][source]
                      and sum(result[target]) > 1)
    else:
        raise ValueError(f"unknown edge kind: {kind!r}")
    try:
        target, source = next(candidates)
    except StopIteration:
        return result, None
    result[target][source] = 1 if kind == "edge_add" else 0
    return result, {"target": target, "source": source,
                    "old_value": 0 if kind == "edge_add" else 1,
                    "new_value": 1 if kind == "edge_add" else 0}


def make_full_behaviour_benchmark_cases(
    *,
    sizes: Iterable[int] = DEFAULT_FULL_BEHAVIOUR_SIZES,
    bases: Iterable[str] = DEFAULT_FULL_BEHAVIOUR_BASES,
    edge_kinds: Iterable[str] = DEFAULT_FULL_BEHAVIOUR_EDGE_KINDS,
    seeds: Mapping[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Create deterministic base, edge-addition, and edge-removal cases."""
    sizes = tuple(int(size) for size in sizes)
    bases = tuple(str(base) for base in bases)
    edge_kinds = tuple(str(kind).lower() for kind in edge_kinds)
    if not sizes or any(size <= 0 for size in sizes):
        raise ValueError("sizes must contain positive integers")
    if not bases or not edge_kinds:
        raise ValueError("bases and edge_kinds must not be empty")
    allowed = set(DEFAULT_FULL_BEHAVIOUR_EDGE_KINDS)
    unknown = set(edge_kinds) - allowed
    if unknown:
        raise ValueError(f"unknown edge kinds: {sorted(unknown)}")
    seeds = dict(seeds or {})
    cases: list[dict[str, Any]] = []
    for base in bases:
        for size in sizes:
            seed = int(seeds.get(base, 0))
            cm, dyn = make_network(base, size, seed=seed)
            for edge_kind in edge_kinds:
                variant, mutation = _edge_variant(cm, edge_kind)
                label = f"{base}_n{size}_s{seed}_{edge_kind}"
                cases.append({
                    "label": label,
                    "base_label": base,
                    "topology": base,
                    "network_size": size,
                    "seed": seed,
                    "edge_kind": edge_kind,
                    "edge_mutation": mutation,
                    "cm": variant,
                    "dyn": list(dyn),
                    "division_size": 2,
                })
    return cases


def _failure_status(result: dict[str, Any]) -> str:
    process_status = result.get("process_status")
    if process_status == "timeout":
        return "timeout"
    if process_status == "malformed_payload":
        return "malformed_payload"
    if process_status in {"crash", "process_failure"}:
        return "process_failure"
    if process_status == "representation_mismatch":
        return "representation_mismatch"
    validation = result.get("validation", {})
    if validation.get("exact_match") is False:
        return "representation_mismatch"
    if result.get("accepted_validation") is True:
        return "completed"
    return "owner_failure"


def _case_record(case: dict[str, Any], result: dict[str, Any], *, materialize: bool) -> dict[str, Any]:
    rows = result.get("representations", [])
    validation = result.get("validation", {})
    completed = _failure_status(result) == "completed"
    if completed:
        bdm_result = bdm_full_behaviour(result, input_mode="flat_index")
        bdm_flat_index = {
            "status": bdm_result.get("status"),
            "value": bdm_result.get("value"),
            "failure": bdm_result.get("failure"),
            "provenance": bdm_result.get("provenance"),
        }
    else:
        bdm_flat_index = {
            "status": "not_run_owner_failure",
            "value": None,
            "failure": "BDM not run because the owner did not complete",
            "provenance": None,
        }
    decimal_cardinalities = [len(row.get("DecimalRepertoire", [])) for row in rows]
    sumandos_cardinalities = [len(row.get("Sumandos", [])) for row in rows]
    return {
        "label": case["label"],
        "network_size": case["network_size"],
        "topology": case["topology"],
        "seed": case["seed"],
        "edge_kind": case["edge_kind"],
        "edge_mutation": case["edge_mutation"],
        "topology_digest": _topology_digest(case["cm"], case["dyn"]),
        "node_count": case["network_size"],
        "edge_count": sum(sum(row) for row in case["cm"]),
        "gate_types": list(case["dyn"]),
        "division_size": case["division_size"],
        "elapsed_seconds": result.get("elapsed_seconds"),
        "process_status": result.get("process_status"),
        "status": _failure_status(result),
        "accepted_validation": completed,
        "failure": None if completed else (
            validation.get("failure") or result.get("kernel_stderr") or
            result.get("parse_error") or "owner failure"
        ),
        "owner_scope": {
            "api": "compressed DecimalRepertoire/Sumandos",
            "production_default_materialize_positions": False,
            "positions_materialized": bool(materialize),
            "owner_constructs_reconstructed_position_map": result.get(
                "owner_materialization", {}
            ).get("owner_constructs_reconstructed_position_map"),
            "statistics_owner": validation.get("statistics_owner"),
            "distribution_codec_separate": True,
            "bdm_separate": True,
        },
        "representation_count": len(rows) if isinstance(rows, list) else 0,
        "decimal_repertoire_cardinality": {
            "total": sum(decimal_cardinalities),
            "min": min(decimal_cardinalities) if decimal_cardinalities else 0,
            "max": max(decimal_cardinalities) if decimal_cardinalities else 0,
        },
        "sumandos_cardinality": {
            "total": sum(sumandos_cardinalities),
            "min": min(sumandos_cardinalities) if sumandos_cardinalities else 0,
            "max": max(sumandos_cardinalities) if sumandos_cardinalities else 0,
        },
        "certified_pair_rows": validation.get("certified_pair_rows", 0),
        "counts_and_probabilities": {
            "derived_without_unfolding": validation.get("statistics_owner") ==
                "algebraic_decimal_sumandos_cardinality",
            "counts_sum": validation.get("counts_sum"),
            "expected_count": validation.get("expected_count"),
            "counts_sum_exact": validation.get("counts_sum") == validation.get("expected_count"),
            "probabilities_sum": {
                "numerator": validation.get("probabilities_sum_numerator"),
                "denominator": validation.get("probabilities_sum_denominator"),
            },
        },
        "raw_bit_length": result.get("raw_bit_length"),
        "encoded_bit_length": result.get("encoded_bit_length"),
        "data_bit_length": result.get("data_bit_length"),
        "flat_index_content_bit_length": result.get("flat_index_content_bit_length"),
        "flat_index_content_sha256": result.get("flat_index_content_sha256"),
        "wire_serialization_bit_length": result.get("encoded_bit_length"),
        "wire_serialization_sha256": result.get("canonical_serialization_sha256"),
        "bdm_flat_index": bdm_flat_index,
        "total_declared_program_length_bits": result.get("total_declared_program_length_bits"),
        "canonical_serialization_sha256": result.get("canonical_serialization_sha256"),
        "scientific_digest": result.get("scientific_digest"),
        "materialize_positions_requested": bool(materialize),
    }


def run_full_behaviour_scaling_benchmark(
    cases: Iterable[dict[str, Any]] | None = None,
    *,
    sizes: Iterable[int] = DEFAULT_FULL_BEHAVIOUR_SIZES,
    bases: Iterable[str] = DEFAULT_FULL_BEHAVIOUR_BASES,
    edge_kinds: Iterable[str] = DEFAULT_FULL_BEHAVIOUR_EDGE_KINDS,
    timeout_seconds: float | None = 300.0,
    materialize_sizes: Iterable[int] = (8,),
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run the exact owner at N=8/10/12 with explicit failure taxonomy."""
    sizes = tuple(int(size) for size in sizes)
    bases = tuple(str(base) for base in bases)
    edge_kinds = tuple(str(kind).lower() for kind in edge_kinds)
    cases = list(cases) if cases is not None else make_full_behaviour_benchmark_cases(
        sizes=sizes, bases=bases, edge_kinds=edge_kinds
    )
    if not cases:
        raise ValueError("at least one benchmark case is required")
    materialize_set = {int(size) for size in materialize_sizes}
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    for case in cases:
        materialize = int(case["network_size"]) in materialize_set
        try:
            result = compute_full_behaviour_encoding(
                case["cm"], case["dyn"], case.get("division_size", 2),
                materialize_positions=materialize,
                validate_exhaustive=materialize,
                timeout_seconds=timeout_seconds,
            )
        except Exception as error:  # a benchmark row must preserve owner failure
            result = {
                "process_status": "owner_failure",
                "accepted_validation": False,
                "elapsed_seconds": None,
                "validation": {"failure": f"{type(error).__name__}: {error}"},
            }
        rows.append(_case_record(case, result, materialize=materialize))
    failures = [row for row in rows if not row["accepted_validation"]]
    process_failures = [row for row in rows if row["process_status"] != "normal_exit"]
    config_payload = {
        "sizes": list(map(int, sizes)), "bases": list(map(str, bases)),
        "edge_kinds": list(map(str, edge_kinds)), "materialize_sizes": sorted(materialize_set),
        "timeout_seconds": timeout_seconds,
        "cases": [(row["label"], row["topology_digest"]) for row in rows],
    }
    config_id = hashlib.sha256(json.dumps(config_payload, sort_keys=True,
                                          separators=(",", ":")).encode()).hexdigest()[:20]
    record = make_envelope("full_behaviour_scaling_benchmark", config_id=config_id, sweep_id=None)
    record.update({
        "observable": "complete_one_step_output_encoding",
        "approximation": "none_exact_compressed_owner",
        "estimator_parameters": {
            "sizes": list(map(int, sizes)), "bases": list(map(str, bases)),
            "edge_kinds": list(map(str, edge_kinds)),
            "materialize_sizes": sorted(materialize_set),
            "production_default_materialize_positions": False,
            "timeout_seconds": timeout_seconds,
        },
        "uncertainty": None,
        "process_status": "normal_exit" if not process_failures else "completed_with_failures",
        "scientific_status": "complete" if not failures else "completed_with_failures",
        "accepted_validation": not failures,
        "large_n_claim_scope": {
            "N=8": "fully_materialized_and_exhaustively_verified",
            "N=10/12": "compressed_only_api_path_with_algebraic_counts_and_probabilities",
            "claim_requires_normal_owner_completion": True,
            "universal_kolmogorov_complexity_claim": False,
        },
        "cases": rows,
        "n_cases": len(rows),
        "n_failures": len(failures),
        "failure_counts": {
            status: sum(row["status"] == status for row in rows)
            for status in ("timeout", "malformed_payload", "process_failure",
                           "representation_mismatch", "owner_failure")
        },
        "provenance": {**source_provenance(), "exact_state_space": True,
                        "owner": "Wolfram Alpha.m Locations/Sumandos pipeline"},
        "runtime_seconds": time.perf_counter() - started,
    })
    record = seal(record)
    if out_dir is not None:
        root = Path(out_dir)
        atomic_write_json(root / "full_behaviour_scaling_benchmark.json", record)
        atomic_write_json(root / "benchmark_summary.json", {
            "record_kind": record["record_kind"], "config_id": record["config_id"],
            "scientific_status": record["scientific_status"],
            "accepted_validation": record["accepted_validation"],
            "cases": rows, "scientific_digest": record["scientific_digest"],
        })
    return record


def validate_full_behaviour_scaling_benchmark(record: dict[str, Any]) -> dict[str, Any]:
    """Validate the generic record plus the exact benchmark acceptance gate."""
    result = validate_record(record)
    errors = list(result["errors"])
    for row in record.get("cases", []):
        if row.get("accepted_validation") and row.get("status") != "completed":
            errors.append(f"accepted_case_not_completed:{row.get('label')}")
        if row.get("status") == "completed" and row.get("process_status") != "normal_exit":
            errors.append(f"completed_case_non_normal_exit:{row.get('label')}")
    if record.get("accepted_validation") and record.get("n_failures"):
        errors.append("accepted_benchmark_has_failures")
    return {"valid": not errors, "errors": errors}


__all__ = [
    "DEFAULT_FULL_BEHAVIOUR_BASES", "DEFAULT_FULL_BEHAVIOUR_EDGE_KINDS",
    "DEFAULT_FULL_BEHAVIOUR_SIZES", "make_full_behaviour_benchmark_cases",
    "run_full_behaviour_scaling_benchmark", "validate_full_behaviour_scaling_benchmark",
]
