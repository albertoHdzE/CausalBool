"""Command-line entry point for the Step 3.5 benchmark and scale pilot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .scaling import (
    DEFAULT_SCALE_FAMILIES,
    DEFAULT_SCALE_SEEDS,
    DEFAULT_SCALE_SIZES,
    make_scale_benchmark_cases,
    run_scale_benchmark,
    run_scale_pilot,
)
from .full_behaviour_scaling import (
    DEFAULT_FULL_BEHAVIOUR_BASES,
    DEFAULT_FULL_BEHAVIOUR_EDGE_KINDS,
    DEFAULT_FULL_BEHAVIOUR_SIZES,
    make_full_behaviour_benchmark_cases,
    run_full_behaviour_scaling_benchmark,
)


def _ints(value: str) -> tuple[int, ...]:
    try:
        values = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected comma-separated integers") from error
    if not values:
        raise argparse.ArgumentTypeError("expected at least one integer")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Step 3.5 exact gate or scale pilot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    benchmark = subparsers.add_parser("benchmark", help="run exact-vs-approximate small-N gate")
    benchmark.add_argument("--out-dir", default="doppel-challenge/results/step35_exact_benchmark")
    benchmark.add_argument("--samples", type=int, default=5000)
    benchmark.add_argument("--max-steps", type=int, default=256)
    benchmark.add_argument("--repeats", type=int, default=5)
    benchmark.add_argument("--seed", type=int, default=20260909)

    pilot = subparsers.add_parser("pilot", help="run exploratory approximate scaling pilot")
    pilot.add_argument("--out-dir", default="doppel-challenge/results/step35_approximate_pilot")
    pilot.add_argument("--sizes", type=_ints, default=DEFAULT_SCALE_SIZES)
    pilot.add_argument("--families", default=",".join(DEFAULT_SCALE_FAMILIES))
    pilot.add_argument("--seeds", type=_ints, default=DEFAULT_SCALE_SEEDS)
    pilot.add_argument("--samples", type=int, default=1000)
    pilot.add_argument("--max-steps", type=int, default=1000)
    pilot.add_argument("--seed", type=int, default=20260909)
    pilot.add_argument("--workers", type=int, default=20)
    pilot.add_argument("--no-resume", action="store_true",
                       help="recompute all pilot cases, replacing checkpoints")

    exact = subparsers.add_parser(
        "full-behaviour",
        help="benchmark the exact compressed DecimalRepertoire/Sumandos owner",
    )
    exact.add_argument("--out-dir", default="doppel-challenge/results/full_behaviour_scaling")
    exact.add_argument("--sizes", type=_ints, default=DEFAULT_FULL_BEHAVIOUR_SIZES)
    exact.add_argument("--bases", default=",".join(DEFAULT_FULL_BEHAVIOUR_BASES))
    exact.add_argument("--edge-kinds", default=",".join(DEFAULT_FULL_BEHAVIOUR_EDGE_KINDS))
    exact.add_argument("--timeout", type=float, default=300.0)

    args = parser.parse_args()
    if args.command == "benchmark":
        result = run_scale_benchmark(
            make_scale_benchmark_cases(), samples=args.samples, max_steps=args.max_steps,
            repeats=args.repeats, seed=args.seed, out_dir=Path(args.out_dir),
        )
        print(json.dumps(result["gate"], sort_keys=True))
        return 0 if result["gate"]["passed"] else 2

    if args.command == "full-behaviour":
        result = run_full_behaviour_scaling_benchmark(
            make_full_behaviour_benchmark_cases(
                sizes=args.sizes,
                bases=tuple(item.strip() for item in args.bases.split(",") if item.strip()),
                edge_kinds=tuple(item.strip() for item in args.edge_kinds.split(",") if item.strip()),
            ),
            timeout_seconds=args.timeout,
            out_dir=Path(args.out_dir),
        )
        print(json.dumps({
            "scientific_status": result["scientific_status"],
            "accepted_validation": result["accepted_validation"],
            "n_cases": result["n_cases"],
            "n_failures": result["n_failures"],
            "failure_counts": result["failure_counts"],
        }, sort_keys=True))
        return 0 if result["accepted_validation"] else 1

    result = run_scale_pilot(
        sizes=args.sizes,
        families=tuple(item.strip() for item in args.families.split(",") if item.strip()),
        seeds=args.seeds,
        samples=args.samples,
        max_steps=args.max_steps,
        seed=args.seed,
        max_workers=args.workers,
        resume=not args.no_resume,
        out_dir=Path(args.out_dir),
    )
    print(json.dumps({"process_status": result["process_status"], "n_cases": result["n_cases"],
                      "n_failures": result["n_failures"],
                      "parallel_backend": result["estimator_parameters"]["parallel_backend"]},
                     sort_keys=True))
    return 0 if result["n_failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
