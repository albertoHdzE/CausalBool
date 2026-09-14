"""Exact one-step behaviour adapters over the Wolfram full-behaviour owners.

This module does not implement the compressed full-behaviour machinery itself.
It delegates to the base Wolfram owners already present in ``src/integration/Alpha.m``
and ``src/Packages/Integration/Experiments.m``:

  * ``CreateRepertoiresDispatch`` for the exhaustive full behaviour,
  * ``calculatingPattsInDivisionsOfCM`` for compressed per-division behaviour,
  * ``calculatingAttractors`` for reconstructing the full output-pattern map,
  * ``compute_full_behaviour_encoding`` for the canonical additive encoding.

The purpose of this adapter is experimental and contractual: expose those
owners to the ``doppel-challenge`` package without editing the root. Position
unfolding is opt-in because it can be exponentially larger than the additive
representation.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .compression import (
    decimal_sumandos_cardinality,
    full_behaviour_encoding_metadata,
    one_step_statistics_from_encoding,
    unfold_decimal_sumandos,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
WOLFRAM_KERNEL = "/Applications/Wolfram.app/Contents/MacOS/WolframKernel"
WL_SCRIPT = REPO_ROOT / "doppel-challenge" / "src" / "doppel_challenge" / "full_behaviour_compare.wl"
WL_INSPECT_SCRIPT = REPO_ROOT / "doppel-challenge" / "src" / "doppel_challenge" / "inspect_full_pattern.wl"
WL_DIAGNOSE_SCRIPT = REPO_ROOT / "doppel-challenge" / "src" / "doppel_challenge" / "diagnose_full_behaviour_mismatch.wl"
WL_ENCODING_SCRIPT = REPO_ROOT / "doppel-challenge" / "src" / "doppel_challenge" / "full_behaviour_encoding.wl"


def _run_wolfram_json(
    script_path: Path,
    payload: dict[str, Any],
    *,
    empty_stdout_message: str,
    invalid_json_message: str,
    timeout_seconds: float | None = 300.0,
) -> dict[str, Any]:
    """Run one Wolfram JSON-emitting script and attach timing metadata."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(payload, f, sort_keys=True)
        f.write("\n")
        input_path = f.name
    started_at = time.perf_counter()
    try:
        env = os.environ.copy()
        env["CB_REPO"] = str(REPO_ROOT)
        env["DOPPEL_INPUT_JSON"] = input_path
        try:
            proc = subprocess.run(
                [WOLFRAM_KERNEL, "-script", str(script_path)], cwd=REPO_ROOT, env=env,
                check=False, text=True, capture_output=True, timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return {"process_status": "timeout", "kernel_exit_code": None,
                    "payload_valid": False, "exact_match": False,
                    "kernel_stdout": (exc.stdout or ""), "kernel_stderr": (exc.stderr or ""),
                    "elapsed_seconds": time.perf_counter() - started_at}
        except OSError as exc:
            return {"process_status": "crash", "kernel_exit_code": None,
                    "payload_valid": False, "exact_match": False,
                    "kernel_stderr": str(exc), "elapsed_seconds": time.perf_counter() - started_at}
    finally:
        elapsed_seconds = time.perf_counter() - started_at
        try:
            os.unlink(input_path)
        except FileNotFoundError:
            pass

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    if not stdout:
        return {"process_status": "crash" if proc.returncode else "malformed_payload",
                "kernel_exit_code": proc.returncode, "payload_valid": False,
                "exact_match": False, "kernel_stderr": stderr,
                "elapsed_seconds": elapsed_seconds}
    json_payload = stdout
    if not stdout.startswith("{"):
        network_key = stdout.find("\"network\"")
        if network_key != -1:
            first_brace = stdout.rfind("{", 0, network_key)
        else:
            first_brace = stdout.find("{")
        last_brace = stdout.rfind("}")
        if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
            json_payload = stdout[first_brace:last_brace + 1]
    try:
        decoder = json.JSONDecoder()
        result, _ = decoder.raw_decode(json_payload)
    except json.JSONDecodeError as exc:
        return {"process_status": "malformed_payload", "kernel_exit_code": proc.returncode,
                "payload_valid": False, "exact_match": False,
                "kernel_stdout": stdout, "kernel_stderr": stderr,
                "elapsed_seconds": elapsed_seconds, "parse_error": str(exc)}
    if not isinstance(result, dict):
        return {"process_status": "malformed_payload", "kernel_exit_code": proc.returncode,
                "payload_valid": False, "exact_match": False,
                "kernel_stdout": stdout, "kernel_stderr": stderr,
                "elapsed_seconds": elapsed_seconds}
    result["kernel_exit_code"] = proc.returncode
    result["elapsed_seconds"] = elapsed_seconds
    result["payload_valid"] = isinstance(result, dict)
    result["process_status"] = "normal_exit" if proc.returncode == 0 else "crash"
    result["warning_status"] = "warning" if stderr else "none"
    required = {"exact_match", "dispatch_rows", "reconstructed_patterns"}
    result["accepted_validation"] = bool(
        proc.returncode == 0 and required.issubset(result) and
        result.get("exact_match") is True and not stderr
    )
    if stderr:
        result["kernel_stderr"] = stderr
    if json_payload != stdout:
        result["kernel_stdout_prefix"] = stdout[: stdout.find("{")].strip()
    return result


def compare_full_behaviour_owners(
    cm: list[list[int]],
    dyn: list[str],
    *,
    division_size: int = 2,
    timeout_seconds: float | None = 300.0,
) -> dict[str, Any]:
    """Compare exhaustive and compressed full-behaviour owners in Wolfram.

    Returns the parsed JSON emitted by ``full_behaviour_compare.wl``.
    """
    payload = {
        "cm": cm,
        "dyn": dyn,
        "division_size": division_size,
    }
    return _run_wolfram_json(
        WL_SCRIPT,
        payload,
        empty_stdout_message="Wolfram full-behaviour comparison produced no stdout",
        invalid_json_message="Wolfram full-behaviour comparison did not emit JSON",
        timeout_seconds=timeout_seconds,
    )


def inspect_full_behaviour_pattern(
    cm: list[list[int]],
    dyn: list[str],
    *,
    division_size: int = 2,
    pattern: list[int] | None = None,
) -> dict[str, Any]:
    """Inspect one full output pattern through the compressed owner.

    The returned JSON includes:
    - the chosen full output pattern,
    - its positions in the exhaustive owner,
    - its positions in the reconstructed compressed owner,
    - the per-division chunks,
    - the local DecimalRepertoire / Sumandos pairs,
    - the explicit local unfolding via ``givePlaces``.
    """
    payload: dict[str, Any] = {
        "cm": cm,
        "dyn": dyn,
        "division_size": division_size,
    }
    if pattern is not None:
        payload["pattern"] = pattern
    return _run_wolfram_json(
        WL_INSPECT_SCRIPT,
        payload,
        empty_stdout_message="Wolfram full-pattern inspection produced no stdout",
        invalid_json_message="Wolfram full-pattern inspection did not emit JSON",
    )


def diagnose_full_behaviour_mismatch(
    cm: list[list[int]],
    dyn: list[str],
    *,
    division_size: int = 2,
    max_examples: int = 5,
    max_positions: int = 20,
) -> dict[str, Any]:
    """Diagnose divergence between exhaustive and compressed full behaviour."""
    payload: dict[str, Any] = {
        "cm": cm,
        "dyn": dyn,
        "division_size": division_size,
        "max_examples": max_examples,
        "max_positions": max_positions,
    }
    return _run_wolfram_json(
        WL_DIAGNOSE_SCRIPT,
        payload,
        empty_stdout_message="Wolfram full-behaviour mismatch diagnosis produced no stdout",
        invalid_json_message="Wolfram full-behaviour mismatch diagnosis did not emit JSON",
    )


def _full_behaviour_failure(n: int, division_size: int, owner: dict[str, Any]) -> dict[str, Any]:
    """Return a stable explicit failure record for an unavailable owner."""
    return {
        "network_size": n,
        "division_size": division_size,
        "input_enumeration": "decimal_0_to_2^N-1",
        "output_bit_order": "LSB_first_node_0_to_N_minus_1",
        "position_convention": "zero_based",
        "representations": [],
        "one_step_output_distribution": [],
        "raw_bit_length": None,
        "encoded_bit_length": None,
        "scientific_digest": None,
        "validation": {
            "status": owner.get("process_status", "malformed_payload"),
            "exact_match": False,
            "failure": owner.get("parse_error") or owner.get("kernel_stderr") or "owner failure",
        },
        "process_status": owner.get("process_status", "malformed_payload"),
        "kernel_exit_code": owner.get("kernel_exit_code"),
        "payload_valid": owner.get("payload_valid", False),
        "accepted_validation": False,
        "elapsed_seconds": owner.get("elapsed_seconds"),
        "owner_metadata": owner,
    }


def compute_full_behaviour_encoding(
    cm: list[list[int]],
    dyn: list[str],
    division_size: int = 2,
    *,
    materialize_positions: bool = False,
    validate_exhaustive: bool | None = None,
    timeout_seconds: float | None = 300.0,
) -> dict[str, Any]:
    """Compute the exact complete one-step DecimalRepertoire/Sumandos encoding.

    The fixed input order is decimal state ``0 ... 2**N-1`` and output bits
    are LSB-first.  By default this requests the compressed owner and its
    algebraic counts only.  Set ``materialize_positions=True`` for small-N
    explanations and round-trip validation; that option is intentionally not
    needed by the production statistics path.
    """
    n = len(cm)
    if any(len(row) != n for row in cm):
        raise ValueError("cm must be square")
    if len(dyn) != n:
        raise ValueError("dyn must contain one gate per node")
    if division_size < 1:
        raise ValueError("division_size must be positive")
    if validate_exhaustive is None:
        validate_exhaustive = materialize_positions
    owner = _run_wolfram_json(
        WL_ENCODING_SCRIPT,
        {
            "cm": cm,
            "dyn": dyn,
            "division_size": division_size,
            "materialize_positions": materialize_positions,
            "validate_exhaustive": bool(validate_exhaustive),
        },
        empty_stdout_message="Wolfram full-behaviour encoding produced no stdout",
        invalid_json_message="Wolfram full-behaviour encoding did not emit JSON",
        timeout_seconds=timeout_seconds,
    )
    if owner.get("process_status") == "normal_exit" and not isinstance(
        owner.get("representations"), list
    ):
        owner = {
            **owner,
            "process_status": "malformed_payload",
            "payload_valid": False,
            "parse_error": "payload missing representations list",
        }
    if owner.get("process_status") != "normal_exit" or not isinstance(owner.get("representations"), list):
        return _full_behaviour_failure(n, division_size, owner)
    if validate_exhaustive and owner.get("validation", {}).get("exact_match") is False:
        return _full_behaviour_failure(
            n, division_size,
            {
                **owner,
                "process_status": "representation_mismatch",
                "payload_valid": True,
                "kernel_stderr": "compressed representation disagrees with exhaustive owner",
            },
        )

    representations: list[dict[str, Any]] = []
    for raw in owner["representations"]:
        pattern = list(raw["output_pattern"])
        decimals = list(raw.get("DecimalRepertoire", []))
        offsets = list(raw.get("Sumandos", []))
        count = int(raw.get("occurrence_count", 0))
        row: dict[str, Any] = {
            "output_pattern": pattern,
            "DecimalRepertoire": decimals,
            "Sumandos": offsets,
            "occurrence_count": count,
            "pair_is_disjoint": bool(raw.get("pair_is_disjoint", False)),
        }
        if materialize_positions:
            positions = list(raw.get("reconstructed_output_positions", []))
            decoded = unfold_decimal_sumandos(decimals, offsets, n)
            if decoded != sorted(set(positions)) or count != len(decoded):
                return _full_behaviour_failure(
                    n, division_size,
                    {
                        **owner,
                        "process_status": "representation_mismatch",
                        "payload_valid": True,
                        "kernel_stderr": "DecimalRepertoire/Sumandos unfolding mismatch",
                    },
                )
            row["reconstructed_output_positions"] = decoded
        elif row["pair_is_disjoint"]:
            expected_count = decimal_sumandos_cardinality(decimals, offsets, disjoint=True)
            if expected_count != count:
                return _full_behaviour_failure(
                    n, division_size,
                    {
                        **owner,
                        "process_status": "representation_mismatch",
                        "payload_valid": True,
                        "kernel_stderr": "algebraic cardinality mismatch",
                    },
                )
        row["one_step_probability"] = {"numerator": count, "denominator": 1 << n}
        representations.append(row)

    statistics = one_step_statistics_from_encoding({
        "network_size": n,
        "division_size": division_size,
        "representations": representations,
    })
    total_count = statistics["total_occurrences"]
    result: dict[str, Any] = {
        "network_size": n,
        "division_size": division_size,
        "input_enumeration": "decimal_0_to_2^N-1",
        "output_bit_order": "LSB_first_node_0_to_N_minus_1",
        "position_convention": "zero_based",
        "representations": representations,
        "output_repertoire": {
            "".join(str(bit) for bit in row["output_pattern"]): [
                row["DecimalRepertoire"], row["Sumandos"]
            ]
            for row in representations
        },
        "reconstructed_output_positions": (
            [
                {"output_pattern": row["output_pattern"],
                 "positions": row["reconstructed_output_positions"]}
                for row in representations
                if "reconstructed_output_positions" in row
            ] if materialize_positions else None
        ),
        "one_step_output_distribution": [
            {"output_pattern": row["output_pattern"],
             "count": row["occurrence_count"],
             "probability": row["one_step_probability"]}
            for row in representations
        ],
        "raw_bit_length": (1 << n) * n,
        "positions_materialized": materialize_positions,
        "owner_materialization": {
            "owner": "calculatingPattsInDivisionsOfCM+calculatingAttractors",
            "owner_constructs_reconstructed_position_map": True,
            "python_positions_returned": materialize_positions,
            "exhaustive_dispatch_called": bool(validate_exhaustive),
            "scope": (
                "compressed_api_with_algebraic_counts"
                if not materialize_positions else
                "compressed_api_plus_explicit_small_n_positions"
            ),
        },
        "process_status": owner.get("process_status"),
        "kernel_exit_code": owner.get("kernel_exit_code"),
        "payload_valid": owner.get("payload_valid", False),
        "elapsed_seconds": owner.get("elapsed_seconds"),
        "validation": {
            **owner.get("validation", {}),
            "counts_sum": total_count,
            "expected_count": 1 << n,
            "probabilities_sum_numerator": total_count,
            "probabilities_sum_denominator": 1 << n,
            "all_output_patterns_explicit": len(representations) == 1 << n,
            "positions_materialized": materialize_positions,
            "statistics_owner": "algebraic_decimal_sumandos_cardinality",
            "certified_pair_rows": sum(
                bool(row["pair_is_disjoint"]) for row in representations
            ),
        },
        "accepted_validation": bool(
            owner.get("process_status") == "normal_exit"
            and len(representations) == 1 << n
            and total_count == 1 << n
            and (not validate_exhaustive or owner.get("validation", {}).get("exact_match") is True)
        ),
    }
    result.update(full_behaviour_encoding_metadata(result))
    result["scientific_digest"] = result["canonical_serialization_sha256"]
    return result


def unfold_full_behaviour_encoding(encoding: dict[str, Any]) -> list[dict[str, Any]]:
    """Materialize the ordered output repertoire from every additive pair."""
    n = int(encoding["network_size"])
    rows = encoding.get("representations", [])
    result = []
    for row in sorted(rows, key=lambda item: _pattern_value(item["output_pattern"], n)):
        positions = unfold_decimal_sumandos(
            row.get("DecimalRepertoire", []), row.get("Sumandos", []), n
        )
        result.append({"output_pattern": list(row["output_pattern"]), "positions": positions})
    return result


def _pattern_value(pattern: list[int], n: int) -> int:
    return sum(int(bit) << index for index, bit in enumerate(pattern))


decode_full_behaviour = unfold_full_behaviour_encoding


def chapter4_network_7() -> tuple[list[list[int]], list[str]]:
    """The 7-node example written in Chapter 4 of the thesis text."""
    cm = [
        [0, 0, 1, 0, 0, 0, 1],
        [0, 0, 1, 0, 0, 1, 0],
        [1, 0, 0, 0, 1, 0, 1],
        [1, 0, 1, 0, 1, 0, 1],
        [0, 0, 1, 1, 0, 1, 1],
        [1, 1, 1, 0, 0, 0, 0],
        [0, 1, 0, 1, 1, 1, 0],
    ]
    dyn = ["AND", "OR", "OR", "AND", "OR", "OR", "AND"]
    return cm, dyn
