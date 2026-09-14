"""pilot_runner -- family-based multi-N pilot experiments with ETA reporting."""
from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any

from .add_edge_catalogue import run_add_edge_catalogue
from .full_behaviour import compare_full_behaviour_owners
from .io import write_json

PilotFamily = str


def _gate_cycle(n: int, seed: int | None = None) -> list[str]:
    cycle = ["AND", "OR", "MAJORITY", "XOR"]
    if seed is None:
        return [cycle[i % len(cycle)] for i in range(n)]
    rng = random.Random(seed)
    return [rng.choice(cycle) for _ in range(n)]


def _ensure_nonempty_inputs(cm: list[list[int]]) -> None:
    """Ensure every node has at least one input by patching the predecessor edge."""
    n = len(cm)
    for target in range(n):
        indegree = sum(cm[target][source] for source in range(n))
        if indegree == 0:
            cm[target][(target - 1) % n] = 1


def make_mixed_ring_network(n: int, *, seed: int | None = None) -> tuple[list[list[int]], list[str]]:
    """Deterministic ring-like family with short and medium-range inputs."""
    if n < 4:
        raise ValueError("pilot network family requires n >= 4")
    cm = [[0 for _ in range(n)] for _ in range(n)]
    for target in range(n):
        cm[target][(target - 1) % n] = 1
        if target % 3 == 0:
            cm[target][(target - 3) % n] = 1
        if target % 5 == 0:
            cm[target][(target - 5) % n] = 1
    _ensure_nonempty_inputs(cm)
    return cm, _gate_cycle(n, seed)


def make_sparse_random_network(
    n: int,
    *,
    seed: int = 0,
    mean_indegree: int = 2,
) -> tuple[list[list[int]], list[str]]:
    """Seeded sparse random directed graph with controlled mean indegree."""
    if n < 4:
        raise ValueError("pilot network family requires n >= 4")
    if mean_indegree < 1:
        raise ValueError("mean_indegree must be >= 1")
    rng = random.Random((seed + 1) * 1009 + n * 9176 + mean_indegree)
    cm = [[0 for _ in range(n)] for _ in range(n)]
    edge_prob = min(0.95, mean_indegree / max(1, n - 1))
    for source in range(n):
        for target in range(n):
            if source == target:
                continue
            if rng.random() < edge_prob:
                cm[target][source] = 1
    _ensure_nonempty_inputs(cm)
    return cm, _gate_cycle(n, seed + 100003)


def make_modular_network(
    n: int,
    *,
    seed: int = 0,
    modules: int = 3,
) -> tuple[list[list[int]], list[str]]:
    """Seeded modular directed graph with dense internal and sparse external edges."""
    if n < 6:
        raise ValueError("modular family requires n >= 6")
    if modules < 2:
        raise ValueError("modules must be >= 2")
    rng = random.Random((seed + 3) * 4021 + n * 149)
    cm = [[0 for _ in range(n)] for _ in range(n)]
    for source in range(n):
        for target in range(n):
            if source == target:
                continue
            same_module = ((source * modules) // n) == ((target * modules) // n)
            threshold = 0.55 if same_module else 0.08
            if rng.random() < threshold:
                cm[target][source] = 1
    _ensure_nonempty_inputs(cm)
    return cm, _gate_cycle(n, seed + 200003)


def make_hub_network(n: int, *, seed: int | None = None) -> tuple[list[list[int]], list[str]]:
    """Deterministic hub-dominated family with a few strong regulators."""
    if n < 5:
        raise ValueError("hub family requires n >= 5")
    cm = [[0 for _ in range(n)] for _ in range(n)]
    hubs = [0, n // 2]
    for target in range(n):
        cm[target][(target - 1) % n] = 1
        for hub in hubs:
            if hub != target and (target + hub) % 2 == 0:
                cm[target][hub] = 1
        if target % 4 == 0:
            cm[target][(target - 2) % n] = 1
    _ensure_nonempty_inputs(cm)
    return cm, _gate_cycle(n, None if seed is None else seed + 300007)


def make_network(
    family: PilotFamily,
    n: int,
    *,
    seed: int = 0,
) -> tuple[list[list[int]], list[str]]:
    """Generate one network from a named structural family."""
    if family == "ring":
        return make_mixed_ring_network(n, seed=seed)
    if family == "sparse_random":
        return make_sparse_random_network(n, seed=seed)
    if family == "modular":
        return make_modular_network(n, seed=seed)
    if family == "hub":
        return make_hub_network(n, seed=seed)
    raise ValueError(f"unknown pilot family: {family!r}")


def _write_suite_progress(
    *,
    root: Path,
    completed_runs: int,
    total_runs: int,
    started_at: float,
    last_completed: dict[str, Any] | None,
) -> dict[str, Any]:
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
        "completed_runs": completed_runs,
        "total_runs": total_runs,
        "remaining_runs": remaining_runs,
        "last_completed": last_completed,
        "elapsed_seconds": elapsed_seconds,
        "mean_seconds_per_run": mean_seconds_per_run,
        "estimated_remaining_seconds": estimated_remaining_seconds,
        "fraction_complete": (completed_runs / total_runs if total_runs else 1.0),
    }
    write_json(root / "pilot_progress.json", progress)
    return progress


def run_add_edge_pilot(
    sizes: list[int],
    *,
    out_dir: str,
    families: list[PilotFamily] | None = None,
    seeds: list[int] | None = None,
    require_base_exact_match: bool = True,
) -> dict[str, Any]:
    """Run the family-based multi-N add-edge pilot with suite-level ETA."""
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    families = families or ["ring", "sparse_random", "modular", "hub"]
    seeds = seeds or [0]
    planned_runs: list[tuple[str, int, int]] = []
    for family in families:
        if family in {"ring", "hub"}:
            for n in sizes:
                planned_runs.append((family, n, 0))
        else:
            for n in sizes:
                for seed in seeds:
                    planned_runs.append((family, n, seed))

    started_at = time.perf_counter()
    _write_suite_progress(
        root=root,
        completed_runs=0,
        total_runs=len(planned_runs),
        started_at=started_at,
        last_completed=None,
    )

    runs: list[dict[str, Any]] = []
    for idx, (family, n, seed) in enumerate(planned_runs, start=1):
        cm, dyn = make_network(family, n, seed=seed)
        label = f"pilot_{family}_n{n}" + (
            "" if family in {"ring", "hub"} else f"_s{seed}"
        )
        base_validation = compare_full_behaviour_owners(cm, dyn, division_size=2)
        if require_base_exact_match and not base_validation["exact_match"]:
            summary = {
                "family": family,
                "seed": seed,
                "n": n,
                "network_label": label,
                "perturbation_kind": "EDGE_ADD",
                "n_runs": 0,
                "all_exact_match": False,
                "base_exact_match": False,
                "status": "skipped_invalid_base",
                "skip_reason": "base_full_behaviour_owner_mismatch",
                "base_validation": {
                    "exact_match": base_validation["exact_match"],
                    "kernel_exit_code": base_validation["kernel_exit_code"],
                    "elapsed_seconds": base_validation["elapsed_seconds"],
                    "dispatch_rows": base_validation["dispatch_rows"],
                    "unique_output_patterns_dispatch": base_validation[
                        "unique_output_patterns_dispatch"
                    ],
                    "reconstructed_patterns": base_validation["reconstructed_patterns"],
                },
            }
            write_json(root / label / "summary.json", summary)
        else:
            summary = run_add_edge_catalogue(
                cm,
                dyn,
                network_label=label,
                out_dir=root / label,
            )
            summary["base_exact_match"] = base_validation.get("accepted_validation", False)
            summary["status"] = "completed" if summary["n_failures"] == 0 else "completed_with_failures"
        summary["family"] = family
        summary["seed"] = seed
        runs.append(summary)
        _write_suite_progress(
            root=root,
            completed_runs=idx,
            total_runs=len(planned_runs),
            started_at=started_at,
            last_completed={"family": family, "n": n, "seed": seed},
        )

    suite = {
        "sizes": sizes,
        "families": families,
        "seeds": seeds,
        "require_base_exact_match": require_base_exact_match,
        "n_runs": len(runs),
        "elapsed_seconds_total": time.perf_counter() - started_at,
        "all_exact_match": all(
            run.get("status") == "completed" and run["all_exact_match"] for run in runs
        ),
        "runs": runs,
    }
    write_json(root / "pilot_summary.json", suite)
    _write_suite_progress(
        root=root,
        completed_runs=len(planned_runs),
        total_runs=len(planned_runs),
        started_at=started_at,
        last_completed=(
            {
                "family": planned_runs[-1][0],
                "n": planned_runs[-1][1],
                "seed": planned_runs[-1][2],
            }
            if planned_runs
            else None
        ),
    )
    return suite
