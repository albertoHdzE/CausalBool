"""Reproduction command: ``python -m doppel_challenge --out-dir ...``."""
from __future__ import annotations

import argparse

from .study import run_prespecified_study


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the exact small doppel-challenge study")
    parser.add_argument("--out-dir", default="doppel-challenge/results/exact_small")
    parser.add_argument("--fresh", action="store_true",
                        help="regenerate the output namespace instead of resuming it")
    args = parser.parse_args()
    result = run_prespecified_study(args.out_dir, resume=not args.fresh)
    print(f"completed {result['n_runs']} study runs; all_cases_accepted={result['all_cases_accepted']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
