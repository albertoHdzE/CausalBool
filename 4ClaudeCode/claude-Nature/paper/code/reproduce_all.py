#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]

def _paper_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(cmd, cwd=str(cwd))
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> None:
    paper_root = _paper_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--figures-dir", type=str, default=str(paper_root / "figures"))
    parser.add_argument("--results-dir", type=str, default=str(paper_root / "results"))
    parser.add_argument("--update-manifest", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--skip-depmap", action="store_true")
    args = parser.parse_args()

    repo = _repo_root()
    pipeline = paper_root / "code" / "analysis_pipeline.py"
    if not pipeline.exists():
        raise SystemExit(f"Missing analysis pipeline: {pipeline}")

    figures_dir = str(Path(args.figures_dir))
    results_dir = str(Path(args.results_dir))

    depmap_ready = (repo / "data" / "DepMap" / "CRISPRGeneEffect.csv").exists()
    do_depmap = depmap_ready and (not bool(args.skip_depmap))

    if not args.verify_only:
        _run([sys.executable, str(pipeline), "--bias-tests", "--figures-dir", figures_dir], cwd=repo)
        _run([sys.executable, str(pipeline), "--cellcollective-cohort", "--figures-dir", figures_dir, "--null-samples", "250"], cwd=repo)
        _run([sys.executable, str(pipeline), "--human-vs-evolved", "--figures-dir", figures_dir, "--null-samples", "120", "--hv-pairs", "60"], cwd=repo)
        _run([sys.executable, str(pipeline), "--massive-test-matrix", "--figures-dir", figures_dir], cwd=repo)
        _run([sys.executable, str(pipeline), "--scaling-report", "--figures-dir", figures_dir, "--repro-nets", "30"], cwd=repo)
        _run([sys.executable, str(pipeline), "--wetlab-pack", "--figures-dir", results_dir], cwd=repo)

        if do_depmap:
            _run([sys.executable, str(pipeline), "--figures-dir", figures_dir, "--null-samples", "50"], cwd=repo)
        else:
            _run([sys.executable, str(pipeline), "--figures-dir", figures_dir, "--null-samples", "50", "--skip-depmap"], cwd=repo)

    manifest = Path(figures_dir) / "repro_lock_manifest.json"
    if args.update_manifest or (not manifest.exists()) or (not args.verify_only):
        _run([sys.executable, str(pipeline), "--repro-lock", "--figures-dir", figures_dir], cwd=repo)

    _run([sys.executable, str(pipeline), "--repro-verify", str(manifest)], cwd=repo)


if __name__ == "__main__":
    main()
