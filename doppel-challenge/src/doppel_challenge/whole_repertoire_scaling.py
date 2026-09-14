"""Scaling benchmark for the whole ordered output-repertoire owner."""
from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .compression import (
    bdm_full_behaviour,
    whole_repertoire_encoding_metadata,
)
from .execution import source_provenance
from .full_behaviour_scaling import _failure_status, make_full_behaviour_benchmark_cases
from .io import atomic_write_json
from .records import make_envelope, seal
from .schema import validate_record
from .whole_repertoire import compute_whole_repertoire_encoding


def run_whole_repertoire_scaling_benchmark(
    cases: Iterable[dict[str, Any]] | None = None,
    *,
    sizes: Iterable[int] = (8, 10, 12),
    bases: Iterable[str] = ("ring", "hub"),
    edge_kinds: Iterable[str] = ("base", "edge_add", "edge_remove"),
    timeout_seconds: float | None = 300.0,
    validate_sizes: Iterable[int] = (8,),
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    cases = list(cases) if cases is not None else make_full_behaviour_benchmark_cases(
        sizes=sizes, bases=bases, edge_kinds=edge_kinds
    )
    validate_set = {int(size) for size in validate_sizes}
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    for case in cases:
        validate = int(case["network_size"]) in validate_set
        try:
            result = compute_whole_repertoire_encoding(
                case["cm"], case["dyn"],
                validate_exhaustive=validate,
                timeout_seconds=timeout_seconds,
            )
        except Exception as error:
            result = {
                "process_status": "owner_failure",
                "accepted_validation": False,
                "validation": {"failure": f"{type(error).__name__}: {error}"},
            }
        status = _failure_status(result)
        completed = status == "completed"
        metadata = whole_repertoire_encoding_metadata(result) if completed else {}
        bdm = (
            bdm_full_behaviour(result, input_mode="whole_index")
            if completed else
            {"status": "not_run_owner_failure", "value": None,
             "failure": "BDM not run because the owner did not complete",
             "provenance": None}
        )
        representations = result.get("column_representations", [])
        decimal_cards = [len(row.get("DecimalRepertoire", [])) for row in representations]
        sumando_cards = [len(row.get("Sumandos", [])) for row in representations]
        topology_digest = hashlib.sha256(json.dumps(
            {"cm": case["cm"], "dyn": case["dyn"]},
            sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        rows.append({
            "label": case["label"], "network_size": case["network_size"],
            "base_label": case.get("base_label", case.get("topology")),
            "topology": case["topology"], "seed": case["seed"],
            "edge_kind": case["edge_kind"], "edge_mutation": case["edge_mutation"],
            "topology_digest": topology_digest,
            "elapsed_seconds": result.get("elapsed_seconds"),
            "process_status": result.get("process_status"),
            "status": status,
            "accepted_validation": completed,
            "failure": None if completed else (
                result.get("validation", {}).get("failure")
                or result.get("kernel_stderr")
                or result.get("parse_error")
                or "owner failure"
            ),
            "owner_scope": {
                "representation": "one DecimalRepertoire/Sumandos pair per output column",
                "input_repertoire_implicit": True,
                "full_output_pattern_enumeration": False,
                "exhaustive_validation_requested": validate,
                "validation_owner_materializes_exhaustive_matrix": validate,
                "positions_materialized": False,
            },
            "representation_count": len(representations),
            "decimal_repertoire_cardinality": {
                "total": sum(decimal_cards),
                "min": min(decimal_cards) if decimal_cards else 0,
                "max": max(decimal_cards) if decimal_cards else 0,
            },
            "sumandos_cardinality": {
                "total": sum(sumando_cards),
                "min": min(sumando_cards) if sumando_cards else 0,
                "max": max(sumando_cards) if sumando_cards else 0,
            },
            "raw_bit_length": result.get("raw_bit_length"),
            "flat_index_content_bit_length": metadata.get("flat_index_content_bit_length"),
            "flat_index_content_sha256": metadata.get("flat_index_content_sha256"),
            "wire_serialization_bit_length": metadata.get("encoded_bit_length"),
            "data_bit_length": metadata.get("data_bit_length"),
            "total_declared_program_length_bits": metadata.get(
                "total_declared_program_length_bits"
            ),
            "wire_serialization_sha256": metadata.get("canonical_serialization_sha256"),
            "canonical_serialization_sha256": metadata.get("canonical_serialization_sha256"),
            "scientific_digest": metadata.get("canonical_serialization_sha256"),
            "bdm_whole_index": bdm,
            "materialize_positions_requested": False,
        })
    failures = [row for row in rows if not row["accepted_validation"]]
    process_failures = [row for row in rows if row["process_status"] != "normal_exit"]
    config = {"sizes": sorted({int(row["network_size"]) for row in rows}),
              "bases": sorted({str(row["base_label"]) for row in rows}) if rows else [],
              "edge_kinds": sorted({str(row["edge_kind"]) for row in cases}) if cases else [],
              "validate_sizes": sorted(validate_set),
              "cases": [(row["label"], row["topology_digest"]) for row in rows]}
    config_id = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]
    record = make_envelope("whole_repertoire_scaling_benchmark", config_id=config_id, sweep_id=None)
    record.update({
        "observable": "whole_ordered_output_repertoire_column_encoding",
        "approximation": "none_exact_analytic_column_owner",
        "estimator_parameters": {**config, "timeout_seconds": timeout_seconds},
        "uncertainty": None,
        "process_status": "normal_exit" if not process_failures else "completed_with_failures",
        "scientific_status": "complete" if not failures else "completed_with_failures",
        "accepted_validation": not failures,
        "large_n_claim_scope": {
            "N=8": "exhaustively_validated_against_output_columns",
            "N=10/12": "analytic_column_pairs_without_full_output_pattern_enumeration",
            "input_repertoire_implicit": True,
        },
        "cases": rows, "n_cases": len(rows), "n_failures": len(failures),
        "failure_counts": {
            status: sum(row["status"] == status for row in rows)
            for status in ("timeout", "malformed_payload", "process_failure",
                           "representation_mismatch", "owner_failure")
        },
        "provenance": {**source_provenance(), "owner": "Integration`Gates`IndexSetAnalytic"},
        "runtime_seconds": time.perf_counter() - started,
    })
    record = seal(record)
    if out_dir is not None:
        root = Path(out_dir)
        atomic_write_json(root / "whole_repertoire_scaling_benchmark.json", record)
        atomic_write_json(root / "benchmark_summary.json", {
            "record_kind": record["record_kind"], "config_id": record["config_id"],
            "scientific_status": record["scientific_status"],
            "accepted_validation": record["accepted_validation"],
            "cases": rows, "scientific_digest": record["scientific_digest"],
        })
    return record


def validate_whole_repertoire_scaling_benchmark(record: dict[str, Any]) -> dict[str, Any]:
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


__all__ = ["run_whole_repertoire_scaling_benchmark", "validate_whole_repertoire_scaling_benchmark"]
