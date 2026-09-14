"""Whole ordered output-repertoire encoding.

The input repertoire is an implicit contract: rows are the ordered states
``0 ... 2**N-1`` in the declared LSB-first convention.  The whole output
repertoire is therefore represented by its N output columns.  Each column is
an exact one-set of implicit row indices, represented by one
DecimalRepertoire/Sumandos pair.  No possible full output pattern is
enumerated by this owner.
"""
from __future__ import annotations

from typing import Any

from .full_behaviour import (
    REPO_ROOT,
    _run_wolfram_json,
)

WL_WHOLE_REPERTOIRE_SCRIPT = (
    REPO_ROOT / "doppel-challenge" / "src" / "doppel_challenge"
    / "whole_repertoire_encoding.wl"
)


def compute_whole_repertoire_encoding(
    cm: list[list[int]],
    dyn: list[str],
    *,
    params: dict[str, Any] | None = None,
    validate_exhaustive: bool = False,
    timeout_seconds: float | None = 300.0,
) -> dict[str, Any]:
    """Compute one exact D/S pair per output column, not per output pattern.

    The returned ``column_representations`` are ordered by output column.  A
    column's one-set is the exact set of implicit input-row indices at which
    that output bit is one.  The complete binary output matrix is recovered by
    placing those one-sets in their columns; input rows and their order are not
    serialized.
    """
    n = len(cm)
    if any(len(row) != n for row in cm):
        raise ValueError("cm must be square")
    if len(dyn) != n:
        raise ValueError("dyn must contain one gate per node")
    result = _run_wolfram_json(
        WL_WHOLE_REPERTOIRE_SCRIPT,
        {
            "cm": cm,
            "dyn": dyn,
            "params": params or {},
            "validate_exhaustive": bool(validate_exhaustive),
        },
        empty_stdout_message="Wolfram whole-repertoire owner produced no stdout",
        invalid_json_message="Wolfram whole-repertoire owner did not emit JSON",
        timeout_seconds=timeout_seconds,
    )
    if result.get("process_status") != "normal_exit":
        return {
            "network_size": n,
            "input_enumeration": "implicit_decimal_0_to_2^N-1",
            "output_bit_order": "LSB_first_node_0_to_N_minus_1",
            "column_representations": [],
            "raw_bit_length": None,
            "flat_index_content_bit_length": None,
            "process_status": result.get("process_status"),
            "accepted_validation": False,
            "validation": result,
        }
    rows = result.get("column_representations")
    if not isinstance(rows, list) or len(rows) != n:
        return {
            **result,
            "process_status": "malformed_payload",
            "accepted_validation": False,
            "parse_error": "payload missing one representation per output column",
        }
    if (result.get("process_status") == "normal_exit"
            and result.get("validation", {}).get("exact_match") is False):
        result["process_status"] = "representation_mismatch"
    value_count = sum(
        len(row.get("DecimalRepertoire", [])) + len(row.get("Sumandos", []))
        for row in rows
    )
    result.update({
        "network_size": n,
        "input_enumeration": "implicit_decimal_0_to_2^N-1",
        "output_bit_order": "LSB_first_node_0_to_N_minus_1",
        "column_representations": rows,
        "raw_bit_length": n * (1 << n),
        "flat_value_count": value_count,
        "flat_index_content_bit_length": n * value_count,
        "positions_materialized": False,
        "owner_materialization": {
            "owner": "Integration`Gates`IndexSetAnalytic",
            "owner_constructs_full_output_pattern_map": False,
            "python_positions_returned": False,
            "exhaustive_dispatch_called": bool(validate_exhaustive),
            "validation_owner_materializes_exhaustive_matrix": bool(validate_exhaustive),
            "scope": "whole_ordered_output_repertoire_by_output_column",
        },
        "accepted_validation": bool(
            result.get("process_status") == "normal_exit"
            and result.get("warning_status") == "none"
            and result.get("validation", {}).get("exact_match", True) is True
        ),
    })
    return result


__all__ = ["compute_whole_repertoire_encoding"]
