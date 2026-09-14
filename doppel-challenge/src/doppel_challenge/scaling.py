"""Step 3.5 feasibility gate for the approximate large-network track."""
from __future__ import annotations

import hashlib
import json
import math
import multiprocessing as mp
import os
import statistics
import time
import tracemalloc
from collections.abc import Iterable, Mapping
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .adapters import Network
from .estimator import APPROXIMATION, CONVERGENCE_POLICY, estimate_repertoire
from .execution import source_provenance
from .io import atomic_write_json, read_json
from .records import make_envelope, seal
from .repertoire import compute_repertoire
from .schema import validate_record
from .stats import total_variation


DEFAULT_THRESHOLDS: dict[str, float] = {
    "max_mean_total_variation": 0.05,
    "max_p95_total_variation": 0.10,
    "min_uncertainty_coverage": 0.90,
    "max_truncated_fraction": 0.01,
    "max_mean_runtime_seconds": 60.0,
    "max_mean_peak_memory_bytes": 512.0 * 1024.0 * 1024.0,
    "max_mean_peak_rss_bytes": 1024.0 * 1024.0 * 1024.0,
}
DEFAULT_SCALE_SIZES = (4, 8, 12, 20, 25, 30, 35, 40, 45, 50, 55, 60,
                       70, 80, 100, 120, 160)
DEFAULT_SCALE_FAMILIES = ("ring", "sparse_random", "modular", "hub")
DEFAULT_SCALE_SEEDS = (0, 1)


def _as_cases(networks: Any) -> list[tuple[str, Network]]:
    if isinstance(networks, Network):
        return [(f"network_n{networks.n}", networks)]
    if isinstance(networks, Mapping):
        cases = list(networks.items())
    else:
        cases = list(networks)
    result: list[tuple[str, Network]] = []
    for index, case in enumerate(cases):
        if isinstance(case, Network):
            label, net = f"network_{index}_n{case.n}", case
        elif isinstance(case, tuple) and len(case) == 2 and isinstance(case[1], Network):
            label, net = str(case[0]), case[1]
        else:
            raise TypeError("networks must be a Network, mapping, or (label, Network) iterable")
        result.append((label, net))
    if not result:
        raise ValueError("at least one network is required")
    return result


def make_scale_benchmark_cases(
    *,
    sizes: Iterable[int] = tuple(range(4, 9)),
    families: Iterable[str] = DEFAULT_SCALE_FAMILIES,
    seeds: Iterable[int] = (0,),
) -> dict[str, Network]:
    """Build the exact-reference matrix used before large-N work.

    The family builders enforce their own minimum sizes.  A requested case
    that cannot be constructed is omitted rather than silently changing the
    topology; callers can compare the returned labels with their plan.
    """
    from .pilot_runner import make_network

    result: dict[str, Network] = {}
    for family in families:
        for size in sizes:
            for seed in seeds:
                try:
                    matrix, gates = make_network(family, int(size), seed=int(seed))
                except ValueError:
                    continue
                label = f"{family}_n{int(size)}_s{int(seed)}"
                result[label] = Network(int(size), matrix, gates, [{} for _ in gates])
    if not result:
        raise ValueError("no valid exact benchmark cases could be constructed")
    return result


def _distribution_record(rep: dict[str, Any]) -> dict[str, Any]:
    return {"support": rep["support"], "probs": rep["probs"]}


def _measure_exact(net: Network) -> tuple[dict[str, Any], float, int]:
    started = time.perf_counter()
    tracing_before = tracemalloc.is_tracing()
    if not tracing_before:
        tracemalloc.start()
    current_before, _ = tracemalloc.get_traced_memory()
    rep = compute_repertoire(net)
    _, peak = tracemalloc.get_traced_memory()
    if not tracing_before:
        tracemalloc.stop()
    return rep, time.perf_counter() - started, max(0, peak - current_before)


def _coverage(exact: dict[str, Any], estimate: dict[str, Any]) -> float:
    intervals = estimate["uncertainty"]["confidence_intervals"]
    covered = 0
    for state, probability in zip(exact["support"], exact["probs"]):
        interval = intervals.get(str(state), [0.0, 0.0])
        covered += int(interval[0] <= probability <= interval[1])
    return covered / len(exact["support"]) if exact["support"] else 1.0


def _thresholds(value: Mapping[str, float] | None) -> dict[str, float]:
    result = dict(DEFAULT_THRESHOLDS)
    if value:
        unknown = set(value) - set(result)
        if unknown:
            raise ValueError(f"unknown feasibility thresholds: {sorted(unknown)}")
        result.update(value)
    if not 0.0 <= result["min_uncertainty_coverage"] <= 1.0:
        raise ValueError("min_uncertainty_coverage must be in [0, 1]")
    return result


def run_scale_benchmark(
    networks: Any,
    *,
    samples: int = 1000,
    max_steps: int = 1000,
    seed: int = 0,
    repeats: int = 5,
    exact_max_n: int = 8,
    thresholds: Mapping[str, float] | None = None,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Benchmark restart estimates against exact small-network repertoires.

    Every network with ``N <= exact_max_n`` is enumerated exactly and compared
    with independent seeded estimates.  Larger networks are recorded as
    ``exact_unavailable`` and do not contribute to the gate.  The gate passes
    only if every benchmark case meets all declared thresholds.  A failed gate
    returns status ``stop_large_network_track``.
    """
    if not isinstance(repeats, int) or repeats <= 0:
        raise ValueError("repeats must be a positive integer")
    if not isinstance(exact_max_n, int) or exact_max_n < 0:
        raise ValueError("exact_max_n must be a non-negative integer")
    limits = _thresholds(thresholds)
    normalized_cases = _as_cases(networks)
    cases: list[dict[str, Any]] = []
    started = time.perf_counter()
    for label, net in normalized_cases:
        if net.n > exact_max_n:
            cases.append({"label": label, "N": net.n, "status": "exact_unavailable",
                          "accepted_validation": False,
                          "reason": f"N>{exact_max_n}; no exact comparison attempted"})
            continue
        exact, exact_runtime, exact_memory = _measure_exact(net)
        replicate_rows: list[dict[str, Any]] = []
        tv_values: list[float] = []
        truncations: list[float] = []
        coverages: list[float] = []
        probability_vectors: list[dict[int, float]] = []
        for repeat in range(repeats):
            estimate = estimate_repertoire(net, samples, max_steps, seed + repeat)
            tv = total_variation(_distribution_record(estimate), _distribution_record(exact))
            tv_values.append(tv)
            probability_vectors.append(dict(zip(estimate["support"], estimate["probs"])))
            truncations.append(estimate["convergence"]["truncated_fraction"])
            coverage = _coverage(exact, estimate)
            coverages.append(coverage)
            replicate_rows.append({
                "repeat": repeat,
                "seed": seed + repeat,
                "total_variation": tv,
                "support_jaccard": 1.0 - len(set(estimate["support"]) & set(exact["support"])) /
                                   len(set(estimate["support"]) | set(exact["support"]))
                                   if set(estimate["support"]) | set(exact["support"]) else 0.0,
                "truncated_fraction": truncations[-1],
                "uncertainty_coverage": coverage,
                "runtime_seconds": estimate["runtime_seconds"],
                "peak_memory_bytes": estimate["peak_memory_bytes"],
                "peak_rss_bytes": estimate["resource_usage"]["process_max_rss_bytes"],
            })
        mean_tv = statistics.fmean(tv_values)
        p95_tv = sorted(tv_values)[min(len(tv_values) - 1, math.ceil(0.95 * len(tv_values)) - 1)]
        mean_truncated = statistics.fmean(truncations)
        mean_coverage = statistics.fmean(coverages)
        all_states = sorted(set(exact["support"]) | set().union(*[set(v) for v in probability_vectors]))
        coordinate_bias = {
            state: statistics.fmean(vector.get(state, 0.0) for vector in probability_vectors) -
            dict(zip(exact["support"], exact["probs"])).get(state, 0.0)
            for state in all_states
        }
        mean_absolute_bias = statistics.fmean(abs(value) for value in coordinate_bias.values()) if coordinate_bias else 0.0
        accepted = (mean_tv <= limits["max_mean_total_variation"] and
                    p95_tv <= limits["max_p95_total_variation"] and
                    mean_coverage >= limits["min_uncertainty_coverage"] and
                    mean_truncated <= limits["max_truncated_fraction"] and
                    statistics.fmean(r["runtime_seconds"] for r in replicate_rows) <= limits["max_mean_runtime_seconds"] and
                    statistics.fmean(r["peak_memory_bytes"] for r in replicate_rows) <= limits["max_mean_peak_memory_bytes"] and
                    statistics.fmean(r["peak_rss_bytes"] for r in replicate_rows) <= limits["max_mean_peak_rss_bytes"])
        failures = []
        if mean_tv > limits["max_mean_total_variation"]:
            failures.append("mean_total_variation")
        if p95_tv > limits["max_p95_total_variation"]:
            failures.append("p95_total_variation")
        if mean_coverage < limits["min_uncertainty_coverage"]:
            failures.append("uncertainty_coverage")
        if mean_truncated > limits["max_truncated_fraction"]:
            failures.append("trajectory_convergence")
        mean_runtime = statistics.fmean(r["runtime_seconds"] for r in replicate_rows)
        mean_memory = statistics.fmean(r["peak_memory_bytes"] for r in replicate_rows)
        mean_rss = statistics.fmean(r["peak_rss_bytes"] for r in replicate_rows)
        if mean_runtime > limits["max_mean_runtime_seconds"]:
            failures.append("runtime_budget")
        if mean_memory > limits["max_mean_peak_memory_bytes"]:
            failures.append("memory_budget")
        if mean_rss > limits["max_mean_peak_rss_bytes"]:
            failures.append("rss_budget")
        cases.append({
            "label": label,
            "N": net.n,
            "status": "passed" if accepted else "failed",
            "accepted_validation": accepted,
            "exact": {"runtime_seconds": exact_runtime, "peak_memory_bytes": exact_memory,
                       "support_size": len(exact["support"])},
            "approximate": {
                "samples": samples, "max_steps": max_steps, "repeats": repeats,
                "mean_total_variation": mean_tv,
                "variance_total_variation": statistics.pvariance(tv_values),
                "p95_total_variation": p95_tv,
                "bias": {
                    "mean_signed_coordinate_bias": statistics.fmean(coordinate_bias.values()) if coordinate_bias else 0.0,
                    "mean_absolute_coordinate_bias": mean_absolute_bias,
                    "coordinate_bias": {str(state): value for state, value in coordinate_bias.items()},
                },
                "variance": {"total_variation": statistics.pvariance(tv_values)},
                "mean_truncated_fraction": mean_truncated,
                "mean_uncertainty_coverage": mean_coverage,
                "mean_runtime_seconds": mean_runtime,
                "mean_peak_memory_bytes": mean_memory,
                "mean_peak_rss_bytes": mean_rss,
            },
            "failure_reasons": failures,
            "replicates": replicate_rows,
        })

    benchmark_passed = bool(cases) and all(
        case["accepted_validation"] for case in cases if case["status"] != "exact_unavailable"
    ) and any(case["status"] != "exact_unavailable" for case in cases)
    config_payload = {"samples": samples, "max_steps": max_steps, "seed": seed,
                      "repeats": repeats, "exact_max_n": exact_max_n, "thresholds": limits,
                      "cases": [(label, net.n) for label, net in normalized_cases]}
    config_id = hashlib.sha256(json.dumps(config_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]
    record = make_envelope("scaling_benchmark", config_id=config_id, sweep_id=None)
    record.update({
        "observable": "basin_weighted_attractor_repertoire",
        "approximation": APPROXIMATION,
        "estimator_parameters": {"samples": samples, "max_steps": max_steps, "seed": seed,
                                  "repeats": repeats, "exact_max_n": exact_max_n},
        "uncertainty": {"method": "replicate_error_and_coverage", "confidence_level": 0.95},
        "process_status": "normal_exit",
        "accepted_validation": benchmark_passed,
        "gate": {"passed": benchmark_passed,
                  "status": "proceed_exploratory_only" if benchmark_passed else "stop_large_network_track",
                  "thresholds": limits,
                  "failed_cases": [case["label"] for case in cases if case["status"] == "failed"],
                  "unavailable_cases": [case["label"] for case in cases
                                        if case["status"] == "exact_unavailable"]},
        "cases": cases,
        "provenance": {**source_provenance(), "exact_state_space": False},
        "runtime_seconds": time.perf_counter() - started,
    })
    record = seal(record)
    if out_dir is not None:
        root = Path(out_dir)
        atomic_write_json(root / "scaling_benchmark.json", record)
    return record


def _pilot_case_id(*, config_id: str, family: str, size: int, seed: int,
                   samples: int, max_steps: int) -> str:
    payload = {"config_id": config_id, "family": family, "N": size, "seed": seed,
               "samples": samples, "max_steps": max_steps}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:24]


def _run_pilot_worker(case: tuple[str, int, int, int, int]) -> dict[str, Any]:
    """Process-pool worker; all inputs are serializable and deterministic."""
    family, size, seed, samples, max_steps = case
    from .pilot_runner import make_network

    matrix, gates = make_network(family, size, seed=seed)
    net = Network(size, matrix, gates, [{} for _ in gates])
    return estimate_repertoire(net, samples, max_steps, seed)


def _pilot_case_record(
    *,
    config_id: str,
    case_id: str,
    family: str,
    size: int,
    seed: int,
    samples: int,
    max_steps: int,
    result: dict[str, Any],
) -> dict[str, Any]:
    convergence = result.get("convergence", {})
    truncated_fraction = convergence.get("truncated_fraction", 1.0)
    invalid_starts = convergence.get("invalid_starts", 0)
    convergence_complete = (result.get("process_status") == "normal_exit" and
                            isinstance(truncated_fraction, (int, float)) and
                            truncated_fraction <= 0.01 and invalid_starts == 0)
    failure_reasons = [] if convergence_complete else ["incomplete_cycle_convergence"]
    if convergence.get("tail_unstable_samples", 0):
        failure_reasons.append("unstable_finite_horizon_tail")
    if result.get("process_status") != "normal_exit":
        failure_reasons.insert(0, "process_failure")
    record = make_envelope("scale_pilot_case", config_id=config_id, sweep_id=None)
    record.update({
        "case_id": case_id,
        "network_family": family,
        "N": size,
        "seed": seed,
        "observable": "basin_weighted_attractor_repertoire",
        "approximation": APPROXIMATION,
        "estimator_parameters": {"samples": samples, "max_steps": max_steps, "seed": seed,
                                  "convergence_policy": CONVERGENCE_POLICY},
        "uncertainty": result.get("uncertainty"),
        "process_status": result.get("process_status", "crash"),
        "accepted_validation": False,
        "convergence_status": "complete" if convergence_complete else "incomplete",
        "failure_reasons": failure_reasons,
        "provenance": result.get("provenance"),
        "observed_payoff_is_lower_bound": True,
        "headline_scientific_claims_permitted": False,
        "result": result,
    })
    return seal(record)


def _pilot_failure_record(*, config_id: str, case_id: str, family: str, size: int,
                          seed: int, samples: int, max_steps: int, error: BaseException) -> dict[str, Any]:
    result = make_envelope("diagnostic", config_id=config_id, sweep_id=None)
    result.update({"observable": "basin_weighted_attractor_repertoire",
                   "approximation": APPROXIMATION,
                   "estimator_parameters": {"samples": samples, "max_steps": max_steps, "seed": seed},
                   "uncertainty": None, "process_status": "crash", "accepted_validation": False,
                   "provenance": {"exact_state_space": False},
                   "failure": f"{type(error).__name__}: {error}"})
    result = seal(result)
    return _pilot_case_record(config_id=config_id, case_id=case_id, family=family, size=size,
                              seed=seed, samples=samples, max_steps=max_steps, result=result)


def run_scale_pilot(
    *,
    sizes: Iterable[int] = DEFAULT_SCALE_SIZES,
    families: Iterable[str] = DEFAULT_SCALE_FAMILIES,
    seeds: Iterable[int] = DEFAULT_SCALE_SEEDS,
    samples: int = 1000,
    max_steps: int = 1000,
    seed: int = 0,
    max_workers: int | None = None,
    resume: bool = True,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run exploratory approximate pilots at the declared scaling sizes.

    These pilots intentionally have no exact baseline and never report an
    optimum.  Their outputs are marked as lower-bound observations and are
    permitted only as a follow-up after a passing small-N benchmark.
    """
    sizes = tuple(int(size) for size in sizes)
    families = tuple(str(family) for family in families)
    seeds = tuple(int(case_seed) for case_seed in seeds)
    if not sizes or any(size <= 0 for size in sizes):
        raise ValueError("sizes must contain positive integers")
    if not families or not seeds:
        raise ValueError("families and seeds must not be empty")
    if not isinstance(samples, int) or samples <= 0 or not isinstance(max_steps, int) or max_steps <= 0:
        raise ValueError("samples and max_steps must be positive integers")
    if max_workers is None:
        max_workers = min(16, os.cpu_count() or 1)
    if not isinstance(max_workers, int) or max_workers <= 0:
        raise ValueError("max_workers must be a positive integer or None")
    requested_cases = [(family, size, seed + case_seed)
                       for family in families for size in sizes for case_seed in seeds]
    valid_cases: list[tuple[str, int, int]] = []
    exclusions: list[dict[str, Any]] = []
    from .pilot_runner import make_network
    for family, size, case_seed in requested_cases:
        try:
            make_network(family, size, seed=case_seed)
        except ValueError as error:
            exclusions.append({"network_family": family, "N": size, "seed": case_seed,
                               "reason": f"inadmissible_family_size: {error}"})
            continue
        valid_cases.append((family, size, case_seed))
    cases = valid_cases
    if not cases:
        raise ValueError("no valid scale pilot cases could be constructed")
    config_payload = {"sizes": sizes, "families": families, "seeds": seeds,
                      "samples": samples, "max_steps": max_steps, "seed": seed,
                      "exclusions": exclusions, "convergence_policy": CONVERGENCE_POLICY,
                      "tail_fallback": True}
    config_id = hashlib.sha256(json.dumps(config_payload, sort_keys=True).encode()).hexdigest()[:20]
    root = Path(out_dir) if out_dir is not None else None
    checkpoint_dir = root / "cases" if root is not None else None
    if checkpoint_dir is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

    rows_by_id: dict[str, dict[str, Any]] = {}
    pending: list[tuple[str, int, int]] = []
    for family, size, case_seed in cases:
        case_id = _pilot_case_id(config_id=config_id, family=family, size=size, seed=case_seed,
                                 samples=samples, max_steps=max_steps)
        checkpoint = checkpoint_dir / f"{case_id}.json" if checkpoint_dir is not None else None
        if resume and checkpoint is not None and checkpoint.exists():
            try:
                cached = read_json(checkpoint)
                if (cached.get("record_kind") == "scale_pilot_case" and cached.get("config_id") == config_id
                        and cached.get("case_id") == case_id and validate_record(cached)["valid"]):
                    if "convergence_status" not in cached and isinstance(cached.get("result"), dict):
                        # Migrate pre-convergence-classification checkpoints
                        # without recomputing their scientific result.
                        cached = _pilot_case_record(
                            config_id=config_id, case_id=case_id, family=family,
                            size=size, seed=case_seed, samples=samples,
                            max_steps=max_steps, result=cached["result"],
                        )
                        atomic_write_json(checkpoint, cached)
                    rows_by_id[case_id] = cached
                    continue
            except (OSError, ValueError):
                pass
        pending.append((family, size, case_seed))

    started = time.perf_counter()
    total = len(cases)
    if root is not None:
        atomic_write_json(root / "progress.json", {"completed": len(rows_by_id), "total": total,
                                                     "remaining": total - len(rows_by_id), "status": "running"})

    def save_result(family: str, size: int, case_seed: int, result: dict[str, Any]) -> None:
        case_id = _pilot_case_id(config_id=config_id, family=family, size=size, seed=case_seed,
                                 samples=samples, max_steps=max_steps)
        wrapped = _pilot_case_record(config_id=config_id, case_id=case_id, family=family,
                                     size=size, seed=case_seed, samples=samples,
                                     max_steps=max_steps, result=result)
        rows_by_id[case_id] = wrapped
        if checkpoint_dir is not None:
            atomic_write_json(checkpoint_dir / f"{case_id}.json", wrapped)

    def save_failure(family: str, size: int, case_seed: int, error: BaseException) -> None:
        case_id = _pilot_case_id(config_id=config_id, family=family, size=size, seed=case_seed,
                                 samples=samples, max_steps=max_steps)
        wrapped = _pilot_failure_record(config_id=config_id, case_id=case_id, family=family,
                                        size=size, seed=case_seed, samples=samples,
                                        max_steps=max_steps, error=error)
        rows_by_id[case_id] = wrapped
        if checkpoint_dir is not None:
            atomic_write_json(checkpoint_dir / f"{case_id}.json", wrapped)

    if pending:
        if max_workers == 1:
            for family, size, case_seed in pending:
                try:
                    save_result(family, size, case_seed,
                                _run_pilot_worker((family, size, case_seed, samples, max_steps)))
                except Exception as error:  # preserve a diagnostic case and continue
                    save_failure(family, size, case_seed, error)
        else:
            context = mp.get_context("spawn")
            with ProcessPoolExecutor(max_workers=min(max_workers, len(pending)), mp_context=context) as pool:
                futures = {pool.submit(_run_pilot_worker, (family, size, case_seed, samples, max_steps)):
                           (family, size, case_seed) for family, size, case_seed in pending}
                for future in as_completed(futures):
                    family, size, case_seed = futures[future]
                    try:
                        save_result(family, size, case_seed, future.result())
                    except Exception as error:  # preserve a diagnostic case and continue
                        save_failure(family, size, case_seed, error)
                    if root is not None:
                        atomic_write_json(root / "progress.json", {
                            "completed": len(rows_by_id), "total": total,
                            "remaining": total - len(rows_by_id), "status": "running",
                        })

    rows = [rows_by_id[case_id] for case_id in sorted(rows_by_id)]
    failures = [row for row in rows if (
        row.get("process_status") != "normal_exit" or
        row.get("convergence_status") != "complete"
    )]
    process_failures = [row for row in rows if row.get("process_status") != "normal_exit"]
    incomplete_cases = [row for row in rows if row.get("convergence_status") != "complete"]
    record = make_envelope("scale_pilot", config_id=config_id, sweep_id=None)
    record.update({
        "observable": "basin_weighted_attractor_repertoire",
        "approximation": APPROXIMATION,
        "estimator_parameters": {"samples": samples, "max_steps": max_steps, "seed": seed,
                                  "sizes": list(sizes), "families": list(families), "seeds": list(seeds),
                                  "convergence_policy": CONVERGENCE_POLICY,
                                  "max_workers": max_workers, "parallel_backend": "process_pool_spawn"},
        "uncertainty": {"method": "per_restart_hoeffding_intervals", "confidence_level": 0.95},
        "process_status": "completed_with_process_failures" if process_failures else "normal_exit",
        "scientific_status": "completed_with_incomplete_cases" if incomplete_cases else "complete",
        "accepted_validation": False,
        "exploratory": True,
        "observed_payoff_is_lower_bound": True,
        "headline_scientific_claims_permitted": False,
        "cases": rows,
        "n_cases": len(rows),
        "n_failures": len(failures),
        "n_process_failures": len(process_failures),
        "n_incomplete_cases": len(incomplete_cases),
        "requested_sizes": list(sizes),
        "requested_families": list(families),
        "exclusions": exclusions,
        "provenance": {**source_provenance(), "exact_state_space": False},
        "runtime_seconds": time.perf_counter() - started,
    })
    record = seal(record)
    if root is not None:
        atomic_write_json(root / "scale_pilot.json", record)
        atomic_write_json(root / "progress.json", {"completed": len(rows), "total": total,
                                                     "remaining": total - len(rows),
                                                     "status": record["process_status"]})
    return record


__all__ = ["DEFAULT_SCALE_FAMILIES", "DEFAULT_SCALE_SEEDS", "DEFAULT_SCALE_SIZES",
           "DEFAULT_THRESHOLDS", "make_scale_benchmark_cases", "run_scale_benchmark", "run_scale_pilot"]
