"""Contract checks used before a result can enter a scientific denominator."""
from __future__ import annotations

import math
from typing import Any

from .adapters import Network
from .attractors import enumerate_attractors
from .compression import decode_repertoire, encode_repertoire, ncd
from .oracle import exact_repertoire_equal, independent_repertoire
from .perturbations import index, perturbation_id
from .repertoire import compute_repertoire
from .stats import kl
from .schema import validate_record


def validate_repertoire(net: Network, rep: dict[str, Any] | None = None) -> dict[str, Any]:
    rep = rep or compute_repertoire(net)
    errors: list[str] = []
    if rep.get("rows") != 1 << net.n or rep.get("cols") != net.n:
        errors.append("dimension_mismatch")
    if sum(rep.get("counts", [])) != rep.get("probability_denominator"):
        errors.append("probability_mass_not_one")
    if sorted(rep.get("support", [])) != rep.get("support", []):
        errors.append("support_not_sorted")
    if len(rep.get("transition_map", [])) != 1 << net.n:
        errors.append("transition_map_length")
    if rep.get("observable") != "basin_weighted_attractor_repertoire":
        errors.append("wrong_observable")
    support = rep.get("support", [])
    probs = rep.get("probs", [])
    if len(support) != len(probs) or any(p < 0 for p in probs) or abs(sum(probs) - 1.0) > 1e-12:
        errors.append("probability_vector_invalid")
    cycles = rep.get("attractor_cycles", [])
    basin_sizes = rep.get("basin_sizes", [])
    phase_weights = rep.get("phase_weights", [])
    if len(cycles) != len(basin_sizes) or len(cycles) != len(phase_weights):
        errors.append("attractor_metadata_length")
    elif sum(basin_sizes) != 1 << net.n or any(
        item.get("denominator") != (1 << net.n) * len(cycle)
        or item.get("numerator") != basin
        for cycle, basin, item in zip(cycles, basin_sizes, phase_weights)
    ):
        errors.append("phase_weights_invalid")
    oracle = independent_repertoire(net)
    if not exact_repertoire_equal(rep, oracle):
        errors.append("independent_oracle_mismatch")
    return {"valid": not errors, "errors": errors, "oracle_match": not errors,
            "transition_map_equal": rep.get("transition_map") == oracle.get("transition_map"),
            "attractor_cycles_equal": rep.get("attractor_cycles") == oracle.get("attractor_cycles"),
            "basin_sizes_equal": rep.get("basin_sizes") == oracle.get("basin_sizes"),
            "phase_weights_equal": rep.get("phase_weights") == oracle.get("phase_weights"),
            "exact_probabilities_equal": all(
                rep.get(key) == oracle.get(key)
                for key in ("support", "counts", "probability_denominator",
                            "probability_fractions")
            )}


def validate_codec(rep: dict[str, Any]) -> dict[str, Any]:
    encoded = encode_repertoire(rep, include_schema=False)
    decoded = decode_repertoire(encoded["decimal_str"], encoded["summandos_str"], rep["cols"])
    exact = all(decoded.get(key) == rep.get(key) for key in
                ("support", "counts", "probability_denominator"))
    return {"valid": exact, "exact_round_trip": exact,
            "encoded_bits": encoded["L_CB_bits"]}


def validate_ncd(rep: dict[str, Any], other: dict[str, Any] | None = None,
                 tolerance: float = 1e-12) -> dict[str, Any]:
    other = rep if other is None else other
    forward, reverse, self_value = ncd(rep, other), ncd(other, rep), ncd(rep, rep)
    symmetric = abs(forward["NCD"] - reverse["NCD"]) <= tolerance
    return {"valid": symmetric, "symmetric": symmetric,
            "self_distance": self_value["NCD"],
            "self_distance_overhead_bits": self_value["self_distance_overhead_bits"]}


def validate_perturbation_ids(A0: list[list[int]], max_k: int = 3) -> dict[str, Any]:
    from .perturbations import ball
    results: dict[str, Any] = {}
    all_valid = True
    for kind in ("EDGE_FLIP", "EDGE_ADD", "EDGE_REMOVE"):
        for k in range(1, max_k + 1):
            matrices = ball(A0, k, kind)
            ids = [perturbation_id(A0, matrix, kind) for matrix in matrices]
            ranks = [index(A0, matrix, kind) for matrix in matrices]
            unique = len(ids) == len(set(ids)) and len(ranks) == len(set(ranks))
            results[f"{kind}_k{k}"] = {"n": len(matrices), "unique_ids": unique,
                                        "ids": ids, "ranks": ranks}
            all_valid = all_valid and unique
    return {"valid": all_valid, "by_kind_and_k": results}


def compare_long_run_owners(net: Network) -> dict[str, Any]:
    """Cross-engine contract for the primary observable.

    The independent owner is intentionally separate from production caching;
    this check compares transition maps, cycles, and exact basin probabilities.
    """
    production = compute_repertoire(net)
    oracle = independent_repertoire(net)
    attractors = enumerate_attractors(net)
    return {"transition_map_equal": production["transition_map"] == oracle["transition_map"],
            "attractor_cycles_equal": sorted(production["attractor_cycles"]) == sorted(oracle["attractor_cycles"]),
            "basin_sizes_equal": production["basin_sizes"] == oracle["basin_sizes"],
            "phase_weights_equal": production["phase_weights"] == oracle["phase_weights"],
            "exact_probabilities_equal": all(
                production.get(key) == oracle.get(key)
                for key in ("support", "counts", "probability_denominator",
                            "probability_fractions")
            ),
            "basin_repertoire_equal": exact_repertoire_equal(production, oracle),
            "support_equal": production["support"] == attractors["support"],
            "accepted": exact_repertoire_equal(production, oracle) and
                        production["support"] == attractors["support"]}


def validate_standard_kl_edges() -> dict[str, Any]:
    q = {"support": [0], "probs": [1.0]}
    p = {"support": [0, 1], "probs": [0.01, 0.99]}
    metric = kl(p, q)
    return {"infinite": math.isinf(metric["D_KL_nats"]),
            "outside_mass": metric["p_mass_outside_q_support"],
            "status": metric["divergence_status"]}


def validate_catalogue_manifest(manifest: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate that a catalogue manifest covers the latest accepted records."""
    errors: list[str] = []
    record_check = validate_record(manifest)
    if not record_check["valid"]:
        errors.extend(f"manifest:{error}" for error in record_check["errors"])
    ids = [row.get("perturbation_id") for row in rows]
    expected = manifest.get("expected_perturbation_ids", [])
    if sorted(ids) != sorted(manifest.get("latest_perturbation_ids", [])):
        errors.append("latest_ids_do_not_match_rows")
    if sorted(expected) != sorted(ids):
        errors.append("expected_ids_do_not_match_rows")
    if len(ids) != len(set(ids)):
        errors.append("duplicate_latest_ids")
    if manifest.get("n_latest_records") != len(rows):
        errors.append("latest_record_count_mismatch")
    accepted = sum(bool(row.get("accepted_validation")) for row in rows)
    if manifest.get("n_accepted") != accepted:
        errors.append("accepted_count_mismatch")
    if any(row.get("approximation") != "none_exact_full_state_space" for row in rows):
        errors.append("approximate_row_in_exact_manifest")
    return {"valid": not errors, "errors": errors,
            "n_rows": len(rows), "n_accepted": accepted}
