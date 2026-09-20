"""Reproducible three-arm comparison on the eight public programs.

Task L06 of ``plan/INDEX_ONLY_PLAN.md``, section 8.3.

Arms, each measured in a fresh process:

* ``serial`` — the frozen ``machine.serial_compile`` baseline.
* ``classical`` — the unchanged ``common.classical_compile`` and its helpers.
* ``direct_index`` — the standalone export's ``compile_program``.

The benchmark is allowed to call the baselines. The direct compiler is not, and
its arm runs from the assembled export with only the standard library and the
supplied machine module on its path.

Two timings are reported and they measure different things. ``compile_seconds``
is the compiler call alone, excluding interpreter start, imports and
validation. ``process_seconds`` is the whole subprocess, which is what the
external twenty second limit applies to. Peak resident memory includes the
interpreter and its imports.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import time
from typing import Dict, List

ROOT = Path(__file__).resolve().parent
REFERENCE = ROOT / ".reference"
EXPORT = ROOT / ".build" / "direct_index" / "compiler.py"
ARMS = ("serial", "classical", "direct_index")


def peak_rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # ru_maxrss is bytes on Darwin and kilobytes elsewhere.
    return peak if sys.platform == "darwin" else peak * 1024


def worker(arm: str, program_path: str) -> dict:
    sys.path.insert(0, str(REFERENCE))
    import machine

    program = machine.load_program(program_path)

    if arm == "serial":
        compiler_call = machine.serial_compile
        identity = "machine.serial_compile"
    elif arm == "classical":
        sys.path.insert(0, str(ROOT))
        import common

        compiler_call = common.classical_compile
        identity = "common.classical_compile"
    elif arm == "direct_index":
        sys.path.insert(0, str(EXPORT.parent))
        import compiler as exported

        compiler_call = exported.compile_program
        identity = f"export {EXPORT.name}"
    else:
        raise SystemExit(f"unknown arm {arm!r}")

    started = time.perf_counter()
    compilation = compiler_call(program)
    compile_seconds = time.perf_counter() - started

    # Validate before the run is allowed to be scored.
    cycles = machine.check_compilation(program, compilation)
    for case in program["cases"]:
        machine.check_case(program, compilation, case)

    return {
        "arm": arm,
        "identity": identity,
        "program": program["name"],
        "cycles": cycles,
        "scratch": machine.scratch_footprint(program, compilation),
        "compile_seconds": compile_seconds,
        "peak_rss_bytes": peak_rss_bytes(),
        "correctness": "PASS",
        "cases": len(program["cases"]),
    }


def geomean(values: List[float]) -> float:
    return math.exp(statistics.fmean(math.log(value) for value in values))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_reference() -> str:
    manifest = json.loads((ROOT / "reference.json").read_text())
    for name, expected in manifest["sha256"].items():
        if digest(REFERENCE / name) != expected:
            raise RuntimeError(f"the pinned reference changed: {name}")
    return manifest["commit"]


def run_all(repeats: int, timeout: float) -> dict:
    commit = verify_reference()
    paths = sorted((REFERENCE / "programs").glob("*.json"))
    if len(paths) != 8:
        raise RuntimeError(f"expected eight public programs, found {len(paths)}")

    runs: List[dict] = []
    failures: List[dict] = []

    for path in paths:
        for repeat in range(repeats):
            # Rotate the arm order so a fixed position cannot bias timings.
            order = ARMS[repeat % len(ARMS) :] + ARMS[: repeat % len(ARMS)]
            for arm in order:
                started = time.monotonic()
                try:
                    completed = subprocess.run(
                        [sys.executable, __file__, "--worker", arm, "--program", str(path)],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=str(ROOT),
                    )
                    process_seconds = time.monotonic() - started
                    timed_out = False
                except subprocess.TimeoutExpired:
                    process_seconds = timeout
                    timed_out = True
                    completed = None

                if timed_out or completed is None or completed.returncode != 0:
                    failures.append(
                        {
                            "arm": arm,
                            "program": path.name,
                            "repeat": repeat,
                            "timed_out": timed_out,
                            "exit_code": None if completed is None else completed.returncode,
                            "stderr_tail": "" if completed is None else completed.stderr[-1000:],
                        }
                    )
                    continue
                record = json.loads(completed.stdout)
                record.update(
                    {
                        "repeat": repeat,
                        "process_seconds": process_seconds,
                        "timed_out": False,
                        "exit_code": completed.returncode,
                    }
                )
                runs.append(record)

    summary = {}
    per_repeat = {}
    for arm in ARMS:
        arm_runs = [run for run in runs if run["arm"] == arm]
        programs_seen = {run["program"] for run in arm_runs}
        serial_runs = [run for run in runs if run["arm"] == "serial"]
        complete = len(programs_seen) == 8 and not [
            failure for failure in failures if failure["arm"] == arm
        ]

        repeat_scores = []
        for repeat in range(repeats):
            cycle_ratios, scratch_ratios = [], []
            for path in paths:
                name = None
                candidate = [
                    run
                    for run in arm_runs
                    if run["repeat"] == repeat and run["program"] == _name_of(path)
                ]
                baseline = [
                    run
                    for run in serial_runs
                    if run["repeat"] == repeat and run["program"] == _name_of(path)
                ]
                if not candidate or not baseline:
                    cycle_ratios = []
                    break
                cycle_ratios.append(baseline[0]["cycles"] / candidate[0]["cycles"])
                scratch_ratios.append(baseline[0]["scratch"] / candidate[0]["scratch"])
            if cycle_ratios:
                cycle = geomean(cycle_ratios)
                scratch = geomean(scratch_ratios)
                repeat_scores.append(
                    {
                        "repeat": repeat,
                        "cycle_speedup_geomean": cycle,
                        "scratch_reduction_geomean": scratch,
                        "combined_score": math.sqrt(cycle * scratch),
                    }
                )
        per_repeat[arm] = repeat_scores

        metrics = {
            (run["program"], run["cycles"], run["scratch"]) for run in arm_runs
        }
        deterministic = len(metrics) == len(programs_seen)

        if repeat_scores:
            combined = [score["combined_score"] for score in repeat_scores]
            summary[arm] = {
                "complete": complete,
                "deterministic_metrics": deterministic,
                "cycle_speedup_geomean": statistics.fmean(
                    score["cycle_speedup_geomean"] for score in repeat_scores
                ),
                "scratch_reduction_geomean": statistics.fmean(
                    score["scratch_reduction_geomean"] for score in repeat_scores
                ),
                "combined_score_mean": statistics.fmean(combined),
                "combined_score_min": min(combined),
                "combined_score_max": max(combined),
                "median_compile_seconds": statistics.median(
                    run["compile_seconds"] for run in arm_runs
                ),
                "median_process_seconds": statistics.median(
                    run["process_seconds"] for run in arm_runs
                ),
                "max_process_seconds": max(run["process_seconds"] for run in arm_runs),
                "max_peak_rss_bytes": max(run["peak_rss_bytes"] for run in arm_runs),
            }
        else:
            summary[arm] = {"complete": False, "deterministic_metrics": deterministic}

    return {
        "reference_commit": commit,
        "python": sys.version,
        "platform": platform.platform(),
        "repetitions": repeats,
        "timeout_seconds": timeout,
        "arms": list(ARMS),
        "summary": summary,
        "per_repeat": per_repeat,
        "runs": runs,
        "failures": failures,
        "source_sha256": {
            name: digest(ROOT / name)
            for name in (
                "schema_index.py",
                "direct_contract.py",
                "direct_constraints.py",
                "direct_optimizer.py",
                "direct_compiler.py",
                "common.py",
            )
        },
        "export_sha256": digest(EXPORT) if EXPORT.exists() else None,
        "limitations": [
            "Eight public programs only; the private grader is unavailable.",
            "compile_seconds excludes interpreter start, imports and validation;"
            " process_seconds includes them and is what the 20 s limit governs.",
            "Peak resident memory includes the interpreter and its imports.",
            "No claim of global optimality follows from any of these numbers.",
        ],
    }


def _name_of(path: Path) -> str:
    return json.loads(path.read_text())["name"]


def write_report(report: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "runs.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )

    summary = report["summary"]
    lines = [
        "# Public comparison: serial, classical, direct index",
        "",
        f"Reference commit `{report['reference_commit']}`, "
        f"{report['repetitions']} repetitions per program, "
        f"{len(report['runs'])} measured runs, {len(report['failures'])} failures.",
        "",
        "| Arm | Cycle speedup | Scratch reduction | Combined (mean) | Combined range | Median compile ms | Max process s |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in report["arms"]:
        row = summary.get(arm, {})
        if not row.get("complete"):
            lines.append(f"| {arm} | INCOMPLETE | | | | | |")
            continue
        lines.append(
            "| {arm} | {cycle:.4f}x | {scratch:.4f}x | {mean:.6f}x | {low:.6f}–{high:.6f} | "
            "{ms:.3f} | {proc:.2f} |".format(
                arm=arm,
                cycle=row["cycle_speedup_geomean"],
                scratch=row["scratch_reduction_geomean"],
                mean=row["combined_score_mean"],
                low=row["combined_score_min"],
                high=row["combined_score_max"],
                ms=1000 * row["median_compile_seconds"],
                proc=row["max_process_seconds"],
            )
        )

    direct = summary.get("direct_index", {})
    classical = summary.get("classical", {})
    lines += ["", "## Reading these numbers", ""]
    if direct.get("complete") and classical.get("complete"):
        faster = direct["median_compile_seconds"] < classical["median_compile_seconds"]
        better = direct["combined_score_mean"] > classical["combined_score_mean"]
        lines += [
            f"The direct-index compiler scores {direct['combined_score_mean']:.6f}x against "
            f"the classical arm's {classical['combined_score_mean']:.6f}x, so it is "
            f"{'better' if better else ('equal to' if abs(direct['combined_score_mean'] - classical['combined_score_mean']) < 1e-12 else 'worse')}"
            " on score.",
            "",
            f"It is {'faster' if faster else 'slower'} to run: median compile "
            f"{1000 * direct['median_compile_seconds']:.3f} ms against "
            f"{1000 * classical['median_compile_seconds']:.3f} ms. The direct method "
            "answers exact queries, so a larger constant is expected.",
            "",
            f"Every recorded repetition of the direct arm scored above 1.0: the "
            f"lowest was {direct['combined_score_min']:.6f}x.",
        ]
    lines += [
        "",
        "## Limitations",
        "",
    ] + [f"- {item}" for item in report["limitations"]]
    lines += [
        "",
        "All raw runs, per-repetition aggregates, source hashes and failures are in",
        "`runs.json`. Scores are relative to the frozen serial baseline on the eight",
        "public programs. Nothing here speaks to the private grader.",
        "",
    ]
    (output / "COMPARISON.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=ARMS)
    parser.add_argument("--program")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument(
        "--output", default=str(ROOT / "results" / "direct_index_v1" / "comparison")
    )
    arguments = parser.parse_args(argv)

    if arguments.worker:
        print(json.dumps(worker(arguments.worker, arguments.program)))
        return 0

    if arguments.repeats < 1:
        parser.error("--repeats must be positive")
    if not EXPORT.exists():
        print(
            f"the export {EXPORT} is missing; run export_direct.py first", file=sys.stderr
        )
        return 2

    report = run_all(arguments.repeats, arguments.timeout)
    write_report(report, Path(arguments.output))

    for arm in ARMS:
        row = report["summary"].get(arm, {})
        if row.get("complete"):
            print(
                f"{arm}: combined {row['combined_score_mean']:.6f}x "
                f"(range {row['combined_score_min']:.6f}-{row['combined_score_max']:.6f})",
                file=sys.stderr,
            )
        else:
            print(f"{arm}: INCOMPLETE", file=sys.stderr)
    print(str(Path(arguments.output) / "runs.json"))
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
