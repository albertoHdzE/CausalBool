from __future__ import annotations

import argparse
from pathlib import Path

from .bio_ingestion import prepare_th17_series
from .experiments import run_boolean_experiment, run_ca_experiment, run_graph_experiments


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone implementation of the Zenil causal-calculus paper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ["graphs", "ca", "boolean", "all"]:
        sub = subparsers.add_parser(name)
        sub.add_argument("--output-dir", type=Path, required=True)
        sub.add_argument("--plots-dir", type=Path, required=False)

    th17 = subparsers.add_parser("th17-prepare")
    th17.add_argument("--raw-dir", type=Path, required=True)
    th17.add_argument("--output-dir", type=Path, required=True)
    th17.add_argument("--supp-dir", type=Path, required=False)

    args = parser.parse_args()
    if args.command == "graphs":
        run_graph_experiments(args.output_dir, args.plots_dir)
    elif args.command == "ca":
        run_ca_experiment(args.output_dir, args.plots_dir)
    elif args.command == "boolean":
        run_boolean_experiment(args.output_dir, args.plots_dir)
    elif args.command == "th17-prepare":
        prepare_th17_series(args.raw_dir, args.output_dir, args.supp_dir)
    elif args.command == "all":
        root = args.output_dir
        plots_root = args.plots_dir if args.plots_dir is not None else root / "plots"
        run_graph_experiments(root / "graphs", plots_root / "graphs")
        run_ca_experiment(root / "ca", plots_root / "ca")
        run_boolean_experiment(root / "boolean", plots_root / "boolean")
    else:
        raise ValueError(f"Unsupported command {args.command!r}")


if __name__ == "__main__":
    main()
