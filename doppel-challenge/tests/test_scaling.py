from __future__ import annotations

import math

import pytest

from doppel_challenge import Network, estimate_repertoire
from doppel_challenge.benchmark import run_scale_benchmark, run_scale_pilot
from doppel_challenge.estimator import _make_successor, _successor
from doppel_challenge.repertoire import compute_repertoire
from doppel_challenge.schema import validate_record


@pytest.fixture
def small_network() -> Network:
    return Network(2, [[0, 1], [1, 1]], ["AND", "AND"])


def test_estimator_is_seeded_and_keeps_approximation_contract(small_network):
    left = estimate_repertoire(small_network, samples=100, max_steps=20, seed=7)
    right = estimate_repertoire(small_network, samples=100, max_steps=20, seed=7)
    assert left["probs"] == right["probs"]
    assert left["estimator_parameters"]["seed"] == 7
    assert left["approximation"] == "restart_trajectory_sampling"
    assert left["accepted_validation"] is False
    assert left["resource_usage"]["process_max_rss_bytes"] > 0
    assert validate_record(left)["valid"]
    assert math.isclose(sum(left["probs"]), 1.0)


def test_estimator_matches_exact_when_restarts_cover_all_initial_states(small_network):
    exact = compute_repertoire(small_network)
    estimate = estimate_repertoire(
        small_network, samples=4, max_steps=20, seed=11,
        initial_states=[0, 1, 2, 3],
    )
    assert estimate["support"] == exact["support"]
    assert estimate["probs"] == pytest.approx(exact["probs"])
    assert estimate["convergence"]["truncated_fraction"] == 0.0


@pytest.mark.parametrize(
    ("gate", "sources", "params"),
    [
        ("AND", [0, 1, 2, 3], {}),
        ("OR", [0, 1, 2, 3], {}),
        ("XOR", [0, 1, 2, 3], {}),
        ("NAND", [0, 1, 2, 3], {}),
        ("NOR", [0, 1, 2, 3], {}),
        ("XNOR", [0, 1, 2, 3], {}),
        ("NOT", [2], {}),
        ("IMPLIES", [1, 3], {}),
        ("NIMPLIES", [1, 3], {}),
        ("MAJORITY", [0, 1, 2, 3], {}),
        ("MAJORITY", [0, 1, 2, 3], {"tiePolicy": "atOrAbove"}),
        ("KOFN", [0, 1, 2, 3], {"k": 2}),
        ("KOFN", [0, 1, 2, 3], {"k": 2, "strict": True}),
        ("CANALISING", [0, 1, 2, 3], {"canalisingIndex": 1,
                                         "canalisingValue": 0,
                                         "canalisedOutput": 1}),
        ("TRUE", [], {}),
        ("FALSE", [], {}),
        ("LUT", [0, 1, 2, 3], {"table": [0, 1, 1, 0, 1, 0, 0, 1,
                                         1, 0, 0, 1, 0, 1, 1, 0]}),
        ("REGULATORY", [0, 1, 2, 3], {"activators": [0, 2]}),
        ("REGULATORY_DNF", [0, 1, 2, 3], {"clauses": [
            {"activators": [0], "inhibitors": [1]},
            {"activators": [2, 3], "inhibitors": []},
        ]}),
    ],
)
def test_compiled_successor_matches_reference_for_every_small_state(gate, sources, params):
    matrix = [[0] * 4 for _ in range(4)]
    for source in sources:
        matrix[0][source] = 1
    net = Network(4, matrix, [gate, "TRUE", "FALSE", "TRUE"], [params, {}, {}, {}])
    compiled = _make_successor(net)
    assert [compiled(state) for state in range(16)] == [_successor(net, state)
                                                       for state in range(16)]


def test_short_trajectory_budget_is_recorded_as_incomplete(small_network):
    result = estimate_repertoire(small_network, samples=10, max_steps=1, seed=0)
    assert result["convergence"]["truncated_samples"] > 0
    assert result["convergence"]["truncated_fraction"] > 0
    assert result["convergence"]["estimated_samples"] == 10
    assert math.isclose(sum(result["probs"]), 1.0)


def test_scale_benchmark_has_gate_and_resource_diagnostics(small_network, tmp_path):
    result = run_scale_benchmark(
        [("tiny", small_network)], samples=1000, max_steps=20, repeats=2,
        out_dir=tmp_path,
    )
    assert result["gate"]["passed"] is True
    assert result["cases"][0]["approximate"]["variance_total_variation"] >= 0
    assert (tmp_path / "scaling_benchmark.json").exists()
    assert validate_record(result)["valid"]


def test_scientific_digest_excludes_nested_resource_timings(small_network):
    first = run_scale_benchmark(small_network, samples=1000, max_steps=20, repeats=2)
    second = run_scale_benchmark(small_network, samples=1000, max_steps=20, repeats=2)
    assert first["scientific_digest"] == second["scientific_digest"]


def test_scale_benchmark_stops_when_exact_reference_is_unavailable():
    net = Network(9, [[1 if i == j else 0 for j in range(9)] for i in range(9)], ["NOT"] * 9)
    result = run_scale_benchmark(net, samples=2, max_steps=2, repeats=1, exact_max_n=8)
    assert result["accepted_validation"] is False
    assert result["gate"]["status"] == "stop_large_network_track"
    assert result["cases"][0]["status"] == "exact_unavailable"
    assert result["gate"]["failed_cases"] == []
    assert result["gate"]["unavailable_cases"] == ["network_n9"]


def test_scale_pilot_is_explicitly_exploratory():
    result = run_scale_pilot(sizes=(4,), families=("ring",), samples=10, max_steps=20,
                             seed=1, max_workers=1)
    assert result["exploratory"] is True
    assert result["headline_scientific_claims_permitted"] is False
    assert result["cases"][0]["observed_payoff_is_lower_bound"] is True


def test_scale_pilot_parallel_cases_are_checkpointed_and_resumable(tmp_path):
    first = run_scale_pilot(
        sizes=(6,), families=("ring", "sparse_random", "modular", "hub"), seeds=(0,),
        samples=20, max_steps=40, max_workers=2, out_dir=tmp_path,
    )
    assert first["n_cases"] == 4
    assert first["n_failures"] == 0
    assert first["estimator_parameters"]["parallel_backend"] == "process_pool_spawn"
    assert len(list((tmp_path / "cases").glob("*.json"))) == 4
    second = run_scale_pilot(
        sizes=(6,), families=("ring", "sparse_random", "modular", "hub"), seeds=(0,),
        samples=20, max_steps=40, max_workers=2, resume=True, out_dir=tmp_path,
    )
    assert [row["case_id"] for row in first["cases"]] == [row["case_id"] for row in second["cases"]]
    assert validate_record(second)["valid"]


def test_scale_pilot_records_unsupported_family_sizes_as_exclusions(tmp_path):
    result = run_scale_pilot(
        sizes=(4,), families=("ring", "modular", "hub"), seeds=(0,), samples=5,
        max_steps=20, max_workers=1, out_dir=tmp_path,
    )
    assert result["n_cases"] == 1
    assert len(result["exclusions"]) == 2
    assert result["n_failures"] == 0


def test_scale_pilot_distinguishes_process_exit_from_convergence(tmp_path):
    result = run_scale_pilot(
        sizes=(4,), families=("ring",), seeds=(0,), samples=5, max_steps=1,
        max_workers=1, out_dir=tmp_path,
    )
    assert result["process_status"] == "normal_exit"
    assert result["scientific_status"] == "completed_with_incomplete_cases"
    assert result["n_failures"] == 1
    assert result["n_process_failures"] == 0
    assert result["cases"][0]["process_status"] == "normal_exit"
    assert result["cases"][0]["convergence_status"] == "incomplete"
