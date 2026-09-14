from __future__ import annotations

import math
import json

import pytest

from doppel_challenge.adapters import Network
from doppel_challenge.compression import (
    canonical_serialize_full_behaviour,
    canonical_serialize_whole_repertoire,
    decode_repertoire,
    decimal_sumandos_cardinality,
    flat_index_content_bitstring,
    flat_index_content_metadata,
    flat_whole_repertoire_content_bitstring,
    encode_repertoire,
    full_behaviour_encoding_metadata,
    ncd,
    one_step_statistics_from_encoding,
    unfold_decimal_sumandos,
    whole_repertoire_encoding_metadata,
)
from doppel_challenge.full_behaviour import (
    compute_full_behaviour_encoding,
    unfold_full_behaviour_encoding,
)
from doppel_challenge.full_behaviour_scaling import (
    _failure_status,
    run_full_behaviour_scaling_benchmark,
    validate_full_behaviour_scaling_benchmark,
)
from doppel_challenge.whole_repertoire import compute_whole_repertoire_encoding
from doppel_challenge.whole_repertoire_scaling import (
    run_whole_repertoire_scaling_benchmark,
    validate_whole_repertoire_scaling_benchmark,
)
from doppel_challenge.oracle import exact_repertoire_equal, independent_repertoire
from doppel_challenge.perturbations import (ball, indegrees, index,
                                             perturbation_id, is_admissible_perturbation)
from doppel_challenge.repertoire import compute_repertoire
from doppel_challenge.stats import (constrained_optimum, cross_entropy,
                                    kl, kl_ball_upper_bound)
from doppel_challenge.validation import (compare_long_run_owners,
                                         validate_catalogue_manifest)
from doppel_challenge.release import run_release_gate
from doppel_challenge.execution import run_catalogue
from doppel_challenge.io import read_jsonl
from doppel_challenge.schema import validate_record


@pytest.mark.parametrize(
    ("gate", "sources", "params"),
    [
        ("AND", [0, 1], {}), ("OR", [0, 1], {}), ("XOR", [0, 1], {}),
        ("NAND", [0, 1], {}), ("NOR", [0, 1], {}), ("XNOR", [0, 1], {}),
        ("NOT", [0], {}), ("IMPLIES", [0, 1], {}), ("NIMPLIES", [0, 1], {}),
        ("MAJORITY", [0, 1], {}), ("KOFN", [0, 1], {"k": 1}),
        ("CANALISING", [0, 1], {"canalisingIndex": 1}),
        ("TRUE", [], {}), ("FALSE", [], {}),
        ("LUT", [0, 1], {"table": [0, 1, 1, 0]}),
        ("REGULATORY", [0, 1], {"activators": [0]}),
        ("REGULATORY_DNF", [0, 1], {"clauses": [{"activators": [0], "inhibitors": [1]}]}),
    ],
)
def test_exact_owner_agrees_for_all_declared_gate_families(gate, sources, params):
    matrix = [[0] * 3 for _ in range(3)]
    for source in sources:
        matrix[0][source] = 1
    matrix[1][1] = 1
    matrix[2][2] = 1
    net = Network(3, matrix, [gate, "AND", "AND"], [params, {}, {}])
    assert exact_repertoire_equal(compute_repertoire(net), independent_repertoire(net))


def test_row_input_orientation_is_asymmetric():
    A = [[0, 1], [0, 0]]
    assert indegrees(A) == [1, 0]
    net = Network(2, A, ["NOT", "TRUE"])
    assert net.connected_inputs(0) == [1]
    assert net.connected_inputs(1) == []
    assert not is_admissible_perturbation(A, forbid_zero_indegree_nodes=True)
    assert not is_admissible_perturbation([[1, 1], [0, 1]], gates=["NOT", "AND"])


def test_long_run_oracle_and_one_step_are_distinct():
    net = Network(2, [[0, 1], [1, 1]], ["AND", "AND"])
    rep = compute_repertoire(net)
    oracle = independent_repertoire(net)
    assert exact_repertoire_equal(rep, oracle)
    assert rep["one_step_output_distribution"]["probs"] != rep["probs"]
    assert compare_long_run_owners(net)["accepted"]


def test_exact_owner_records_phase_weights_and_rational_probabilities():
    net = Network(2, [[0, 1], [1, 1]], ["AND", "AND"])
    rep = compute_repertoire(net)
    oracle = independent_repertoire(net)
    assert rep["phase_weights"] == [
        {"numerator": 3, "denominator": 4},
        {"numerator": 1, "denominator": 4},
    ]
    assert rep["probability_fractions"] == [
        {"numerator": 3, "denominator": 4},
        {"numerator": 1, "denominator": 4},
    ]
    assert exact_repertoire_equal(rep, oracle)
    assert compare_long_run_owners(net)["phase_weights_equal"]


def test_standard_forward_kl_marks_unseen_mass_infinite():
    p = {"support": [0, 1], "probs": [0.01, 0.99]}
    q = {"support": [0], "probs": [1.0]}
    result = kl(p, q)
    assert math.isinf(result["D_KL_nats"])
    assert result["infinite_kl"] is True
    assert result["p_mass_outside_q_support"] == 0.99
    assert math.isinf(cross_entropy(p, q))


def test_codec_round_trip_and_symmetric_ncd():
    rep = compute_repertoire(Network(2, [[0, 1], [1, 1]], ["AND", "AND"]))
    other = compute_repertoire(Network(2, [[1, 1], [1, 1]], ["AND", "AND"]))
    encoded = encode_repertoire(rep, include_schema=False)
    decoded = decode_repertoire(encoded["decimal_str"], encoded["summandos_str"], 2)
    assert decoded["support"] == rep["support"]
    assert decoded["counts"] == rep["counts"]
    assert abs(ncd(rep, other)["NCD"] - ncd(other, rep)["NCD"]) <= 1e-12
    assert ncd(rep, rep)["self_distance_overhead_bits"] >= 0
    assert encoded["encoding_sensitivity"]["canonical_distribution_bits"] == encoded["L_CB_bits"]
    assert encoded["encoding_sensitivity"]["json_distribution_bits"] > 0


def test_decimal_sumandos_exact_decoder_and_collision_boundary():
    assert unfold_decimal_sumandos([11], [0, 1, 4, 5]) == [11, 12, 15, 16]
    # The pair is deliberately colliding; the algebraic fast path must not
    # silently claim |D|*|S| for an uncertified representation.
    assert unfold_decimal_sumandos([1, 2, 3, 4], [2, 3]) == [3, 4, 5, 6, 7]
    assert decimal_sumandos_cardinality([11], [0, 1, 4, 5], disjoint=True) == 4


def test_full_behaviour_encoding_is_exact_and_unfolding_is_optional():
    cm = [[0, 1, 0], [1, 0, 1], [0, 1, 0]]
    dyn = ["AND", "OR", "XOR"]
    compressed = compute_full_behaviour_encoding(cm, dyn, materialize_positions=False)
    assert compressed["process_status"] == "normal_exit"
    assert compressed["accepted_validation"] is True
    assert compressed["reconstructed_output_positions"] is None
    assert compressed["output_repertoire"]["000"] == [[0], [0]]
    assert compressed["validation"]["counts_sum"] == 8
    assert one_step_statistics_from_encoding(compressed)["counts_sum_exact"] is True
    assert all("one_step_probability" in row for row in compressed["representations"])
    assert any(row["occurrence_count"] == 0 for row in compressed["representations"])

    unfolded = compute_full_behaviour_encoding(
        cm, dyn, materialize_positions=True, validate_exhaustive=True
    )
    assert unfolded["accepted_validation"] is True
    assert unfolded["validation"]["exact_match"] is True
    assert sum(len(row["positions"]) for row in unfold_full_behaviour_encoding(unfolded)) == 8
    compressed_metadata = full_behaviour_encoding_metadata(compressed)
    unfolded_metadata = full_behaviour_encoding_metadata(unfolded)
    assert canonical_serialize_full_behaviour(compressed) == canonical_serialize_full_behaviour(unfolded)
    assert unfolded_metadata["canonical_serialization_sha256"] == unfolded["scientific_digest"]
    assert compressed["scientific_digest"] == unfolded["scientific_digest"]
    assert compressed["encoded_bit_length"] == unfolded["encoded_bit_length"]
    assert compressed_metadata["flat_index_content_bit_length"] == unfolded_metadata["flat_index_content_bit_length"]
    assert compressed_metadata["flat_index_content_sha256"] == unfolded_metadata["flat_index_content_sha256"]
    reordered = dict(unfolded)
    reordered["representations"] = list(reversed(unfolded["representations"]))
    assert canonical_serialize_full_behaviour(reordered) == canonical_serialize_full_behaviour(unfolded)
    assert full_behaviour_encoding_metadata(reordered)["canonical_serialization_sha256"] == unfolded_metadata["canonical_serialization_sha256"]
    flat_bits = flat_index_content_bitstring(unfolded)
    flat_metadata = flat_index_content_metadata(unfolded)
    assert len(flat_bits) == flat_metadata["flat_index_content_bit_length"]
    assert flat_metadata["flat_index_content_bit_length"] < unfolded["encoded_bit_length"]
    assert flat_metadata["flat_index_content_is_standalone_stream"] is False


def test_full_behaviour_scaling_record_separates_materialization_scope(tmp_path):
    case = {
        "label": "test_n3_base",
        "base_label": "test",
        "topology": "test",
        "network_size": 3,
        "seed": 0,
        "edge_kind": "base",
        "edge_mutation": None,
        "cm": [[0, 1, 0], [1, 0, 1], [0, 1, 0]],
        "dyn": ["AND", "OR", "XOR"],
        "division_size": 2,
    }
    record = run_full_behaviour_scaling_benchmark(
        [case], materialize_sizes=(3,), timeout_seconds=30, out_dir=tmp_path
    )
    row = record["cases"][0]
    assert record["accepted_validation"] is True
    assert row["status"] == "completed"
    assert row["representation_count"] == 8
    assert row["materialize_positions_requested"] is True
    assert row["owner_scope"]["owner_constructs_reconstructed_position_map"] is True
    assert row["counts_and_probabilities"]["counts_sum_exact"] is True
    assert row["counts_and_probabilities"]["probabilities_sum"] == {
        "numerator": 8, "denominator": 8
    }
    assert validate_full_behaviour_scaling_benchmark(record)["valid"]
    assert (tmp_path / "full_behaviour_scaling_benchmark.json").exists()


def test_whole_repertoire_owner_is_one_global_column_object(tmp_path):
    cm = [[0, 1, 0], [1, 0, 1], [0, 1, 0]]
    dyn = ["AND", "OR", "XOR"]
    result = compute_whole_repertoire_encoding(
        cm, dyn, validate_exhaustive=True, timeout_seconds=30
    )
    assert result["process_status"] == "normal_exit"
    assert result["accepted_validation"] is True
    assert result["owner_materialization"]["owner_constructs_full_output_pattern_map"] is False
    assert result["owner_materialization"]["python_positions_returned"] is False
    assert "output_repertoire" not in result
    assert len(result["column_representations"]) == 3
    assert result["validation"]["exact_match"] is True
    assert result["raw_bit_length"] == 3 * (1 << 3)

    for row in result["column_representations"]:
        unfolded = unfold_decimal_sumandos(
            row["DecimalRepertoire"], row["Sumandos"], network_size=3
        )
        assert len(unfolded) == row["one_count"]
        assert row["pair_is_disjoint"] is True
        assert row["unfolded_count"] == row["one_count"]

    metadata = whole_repertoire_encoding_metadata(result)
    flat_bits = flat_whole_repertoire_content_bitstring(result)
    expected_values = sum(
        len(row["DecimalRepertoire"]) + len(row["Sumandos"])
        for row in result["column_representations"]
    )
    assert len(flat_bits) == 3 * expected_values
    assert metadata["flat_index_content_bit_length"] == len(flat_bits)
    assert canonical_serialize_whole_repertoire(result) == canonical_serialize_whole_repertoire(result)
    assert metadata["canonical_serialization_sha256"] == whole_repertoire_encoding_metadata(result)["canonical_serialization_sha256"]

    case = {
        "label": "test_n3_whole_base",
        "base_label": "test",
        "topology": "test",
        "network_size": 3,
        "seed": 0,
        "edge_kind": "base",
        "edge_mutation": None,
        "cm": cm,
        "dyn": dyn,
        "division_size": 2,
    }
    record = run_whole_repertoire_scaling_benchmark(
        [case], timeout_seconds=30, validate_sizes=(3,), out_dir=tmp_path
    )
    assert record["record_kind"] == "whole_repertoire_scaling_benchmark"
    assert record["accepted_validation"] is True
    assert record["cases"][0]["owner_scope"]["input_repertoire_implicit"] is True
    assert record["cases"][0]["owner_scope"]["full_output_pattern_enumeration"] is False
    assert validate_whole_repertoire_scaling_benchmark(record)["valid"]
    assert (tmp_path / "whole_repertoire_scaling_benchmark.json").exists()


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        ({"process_status": "timeout"}, "timeout"),
        ({"process_status": "malformed_payload"}, "malformed_payload"),
        ({"process_status": "crash"}, "process_failure"),
        ({"process_status": "representation_mismatch"}, "representation_mismatch"),
        ({"process_status": "normal_exit", "accepted_validation": False}, "owner_failure"),
    ],
)
def test_full_behaviour_scaling_failure_taxonomy_is_explicit(result, expected):
    assert _failure_status(result) == expected


def test_kl_frontier_and_relaxation_boundary_cases():
    q = {"support": [0, 1], "probs": [0.75, 0.25], "cols": 2}
    rows = [
        {"perturbation_id": "EDGE_ADD:identity", "graph_distance": 0,
         "repertoire": q},
        {"perturbation_id": "EDGE_ADD:0,0:add", "graph_distance": 1,
         "repertoire": {"support": [0, 1], "probs": [0.25, 0.75], "cols": 2}},
    ]
    result = constrained_optimum(rows, q, 1.0, loss_params={"targets": [1]})
    assert result["n_feasible"] == 1
    assert result["V_k_C"] == pytest.approx(0.75)
    assert kl_ball_upper_bound(q, 0.0, "L_SINGLE_TARGET", {"targets": [1]})["upper_bound"] == pytest.approx(0.25)
    assert kl_ball_upper_bound(q, 10.0, "L_SINGLE_TARGET", {"targets": [1]})["upper_bound"] == 1.0
    assert kl_ball_upper_bound(q, 0.1, "L_LINEAR", {"weights": [0.0, 0.0]})["upper_bound"] == 0.0


def test_perturbation_ids_and_ranks_are_unique_across_shells():
    A = [[1, 0], [0, 1]]
    for kind in ("EDGE_FLIP", "EDGE_ADD", "EDGE_REMOVE"):
        matrices = ball(A, 3, kind)
        ids = [perturbation_id(A, matrix, kind) for matrix in matrices]
        ranks = [index(A, matrix, kind) for matrix in matrices]
        assert len(ids) == len(set(ids))
        assert len(ranks) == len(set(ranks))
        for matrix in matrices:
            assert perturbation_id(A, matrix, kind)


def test_durable_run_resume_and_record_validation(tmp_path):
    A = [[1, 0], [1, 1]]
    run_catalogue(A, ["OR", "AND"], out_dir=tmp_path, kind="EDGE_ADD", k=1,
                  allow_self_loops=True, C=0.25)
    first = (tmp_path / "catalogue.jsonl").read_bytes()
    run_catalogue(A, ["OR", "AND"], out_dir=tmp_path, kind="EDGE_ADD", k=1,
                  allow_self_loops=True, C=0.25)
    assert first == (tmp_path / "catalogue.jsonl").read_bytes()
    rows = list(read_jsonl(tmp_path / "catalogue.jsonl"))
    assert rows and all(validate_record(row)["valid"] for row in rows)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert validate_catalogue_manifest(manifest, rows)["valid"]
    assert run_release_gate(tmp_path)["status"] == "failed"  # nested study layout is required


def test_resume_replays_a_valid_checkpoint_after_interrupted_append(tmp_path):
    A = [[1, 0], [1, 1]]
    run_catalogue(A, ["OR", "AND"], out_dir=tmp_path, kind="EDGE_ADD", k=1,
                  allow_self_loops=True, C=0.25)
    path = tmp_path / "catalogue.jsonl"
    complete = list(read_jsonl(path))
    path.write_text("\n".join(json.dumps(row, sort_keys=True, separators=(",", ":"))
                              for row in complete[:-1]) + "\n")
    resumed = run_catalogue(A, ["OR", "AND"], out_dir=tmp_path, kind="EDGE_ADD", k=1,
                            allow_self_loops=True, C=0.25)
    latest = {}
    for row in read_jsonl(path):
        latest[row["perturbation_id"]] = row
    assert len(latest) == resumed["n_candidates_before_filter"]
    assert all(row["accepted_validation"] for row in latest.values())
    assert {pid: row["scientific_digest"] for pid, row in latest.items()} == {
        row["perturbation_id"]: row["scientific_digest"] for row in complete
    }
    assert resumed["n_attempt_records"] == len(complete)
