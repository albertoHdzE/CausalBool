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


# Plan section 2 pins these. They guard the frozen baseline, the reference
# manifest and the historical record against drift that would silently
# invalidate a comparison.
PROTECTED = {
    "common.py": "5b3ae21c5a6c3a73380069ac685fdde7d3cee2fb7bc7704b610d5e24b0056fab",
    "reference.json": "ef6042ce4acc2cfe531d974afb666b6ad40656e15828ad5f814d6cbb338875f0",
    "results/comparison.json": "f070a6691c57c78395e67f4054928cddd753b5aa0265fe1386bb7da27f9cc535",
    "../GOVERNANCE/GLOSSARY.md":
        "c3d0402150fefcb1e72339ef986e9f124754c2370c0c55f3c741b311795b2b3e",
}

HISTORICAL_CLASSICAL_SCORE = 1.9013791212645499

# The direct arm runs here: a neutral directory holding only the export and the
# pinned machine module, started with -I -S so that neither the development
# tree nor an inherited environment is reachable.
DIRECT_WORKER = r'''
import json, resource, sys, time
sys.path.insert(0, sys.argv[1])
import machine

def prohibited(*args, **kwargs):
    raise AssertionError("serial_compile was called by the direct export")

machine.serial_compile = prohibited
import compiler

program = machine.load_program(sys.argv[2])
started = time.perf_counter()
compiled, report = compiler.compile_with_report(program)
compile_seconds = time.perf_counter() - started
cycles = machine.check_compilation(program, compiled)
for case in program["cases"]:
    machine.check_case(program, compiled, case)
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
if sys.platform != "darwin":
    peak *= 1024
banned = {"common", "compilers", "index_query", "repertoire_program", "direct_compiler"}
optimisation = report.get("optimisation", {})
print(json.dumps({
    "arm": "direct_index",
    "identity": compiler.__file__,
    "program": program["name"],
    "cycles": cycles,
    "scratch": machine.scratch_footprint(program, compiled),
    "compile_seconds": compile_seconds,
    "peak_rss_bytes": peak,
    "correctness": "PASS",
    "cases": len(program["cases"]),
    "discrepancy_count": report.get("discrepancy_count", 0),
    "queries": {
        "accepted": optimisation.get("accepted", 0),
        "attempted": optimisation.get("attempted_queries", 0),
        "statuses": optimisation.get("statuses", {}),
        "stopped_because": optimisation.get("stopped_because"),
    },
    "bootstrap": {
        "cycles": report.get("bootstrap", {}).get("cycles"),
        "footprint": report.get("bootstrap", {}).get("footprint"),
    },
    "leaked": sorted(n for n in sys.modules if n.split(".")[0] in banned),
}))
'''


def historical_metrics() -> Dict[str, Dict[str, Dict[str, int]]]:
    """Per-program cycles and scratch for the frozen arms, from pinned history.

    ``results/comparison.json`` is one of the protected files, so its integers
    are a trustworthy control once its hash has been verified. The aggregate
    score alone is not: cycles and scratch can both move while their product,
    and therefore every ratio derived from it, stays put.
    """

    payload = json.loads((ROOT / "results" / "comparison.json").read_text())
    metrics: Dict[str, Dict[str, Dict[str, int]]] = {"serial": {}, "classical": {}}
    for entry in payload["programs"]:
        for arm in ("serial", "classical"):
            first = entry["runs"][arm][0]
            metrics[arm][entry["program"]] = {
                "cycles": first["cycles"],
                "scratch": first["scratch"],
            }
    return metrics


def verify_protected() -> Dict[str, str]:
    """Refuse to measure anything if a protected control has moved."""

    for name, expected in PROTECTED.items():
        actual = digest(ROOT / name)
        if actual != expected:
            raise RuntimeError(
                f"protected file {name} has changed: expected {expected}, found {actual}"
            )
    return dict(PROTECTED)


def verify_export_fresh() -> str:
    """The measured export must be what the current sources assemble to.

    Checking only that a file exists would let a stale binary be measured and
    then reported beside hashes of newer source.
    """

    if not EXPORT.exists():
        raise RuntimeError(f"the export {EXPORT} is missing; run export_direct.py")
    sys.path.insert(0, str(ROOT))
    import export_direct

    current = export_direct.assemble()
    on_disk = EXPORT.read_text(encoding="utf-8")
    if current != on_disk:
        raise RuntimeError(
            "the export on disk differs from what the current sources assemble to; "
            "rebuild it with export_direct.py before measuring"
        )
    return digest(EXPORT)


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
    import shutil
    import tempfile

    commit = verify_reference()
    protected = verify_protected()
    export_hash = verify_export_fresh()
    # Read after the hash check, so the control itself is pinned.
    history = historical_metrics()
    paths = sorted((REFERENCE / "programs").glob("*.json"))
    if len(paths) != 8:
        raise RuntimeError(f"expected eight public programs, found {len(paths)}")

    runs: List[dict] = []
    failures: List[dict] = []

    neutral_directory = Path(tempfile.mkdtemp(prefix="direct-arm-"))
    shutil.copyfile(EXPORT, neutral_directory / "compiler.py")
    shutil.copyfile(REFERENCE / "machine.py", neutral_directory / "machine.py")

    def command_for(arm: str, path: Path):
        if arm == "direct_index":
            # Isolated: no development tree, no inherited environment.
            return (
                [sys.executable, "-I", "-S", "-c", DIRECT_WORKER,
                 str(neutral_directory), str(path)],
                str(neutral_directory),
            )
        return (
            [sys.executable, __file__, "--worker", arm, "--program", str(path)],
            str(ROOT),
        )

    for path in paths:
        for repeat in range(repeats):
            # Rotate the arm order so a fixed position cannot bias timings.
            order = ARMS[repeat % len(ARMS) :] + ARMS[: repeat % len(ARMS)]
            for arm in order:
                argv, working = command_for(arm, path)
                started = time.monotonic()
                try:
                    completed = subprocess.run(
                        argv,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=working,
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
                # Check the response against what was actually asked for before
                # the parent stamps its own repetition on it. Trusting the
                # worker's identity lets a duplicated measurement fill the slot
                # of a missing one and keep the row count intact.
                expected_program = _name_of(path)
                if record.get("arm") != arm or record.get("program") != expected_program:
                    failures.append(
                        {
                            "arm": arm,
                            "program": path.name,
                            "repeat": repeat,
                            "timed_out": False,
                            "exit_code": completed.returncode,
                            "error": (
                                f"worker answered for ({record.get('arm')!r}, "
                                f"{record.get('program')!r}) when ({arm!r}, "
                                f"{expected_program!r}) was requested"
                            ),
                        }
                    )
                    continue
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

    report = {
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
        "program_names": [_name_of(path) for path in paths],
        "historical_metrics": history,
        "export_sha256": export_hash,
        "export_freshness": "matches the current assembly",
        "protected_sha256": protected,
        "limitations": [
            "Eight public programs only; the private grader is unavailable.",
            "compile_seconds excludes interpreter start, imports and validation;"
            " process_seconds includes them and is what the 20 s limit governs.",
            "Peak resident memory includes the interpreter and its imports.",
            "No claim of global optimality follows from any of these numbers.",
        ],
    }
    report["gates"] = evaluate_gates(report, repeats)
    return report


def _name_of(path: Path) -> str:
    return json.loads(path.read_text())["name"]


def evaluate_gates(report: dict, repeats: int) -> dict:
    """The acceptance gates, evaluated rather than asserted.

    Exit status and report wording are both derived from this. Execution
    succeeding is not the same as the comparison passing: a correct compiler
    that merely matched the serial baseline would run cleanly and must still
    fail here.
    """

    gates: Dict[str, dict] = {}
    runs = report["runs"]
    expected_per_arm = 8 * repeats

    # Exact membership, not row counts. A duplicate standing in for a missing
    # measurement leaves the count untouched, so count it and you learn nothing.
    programs = report.get("program_names") or sorted(
        {run["program"] for run in runs}
    )
    expected_keys = {
        (arm, program, repeat)
        for arm in ARMS
        for program in programs
        for repeat in range(repeats)
    }
    observed_keys = [(run["arm"], run["program"], run["repeat"]) for run in runs]
    observed_set = set(observed_keys)
    duplicates = sorted(
        {key for key in observed_keys if observed_keys.count(key) > 1}
    )
    missing = sorted(expected_keys - observed_set)
    unexpected = sorted(observed_set - expected_keys)
    counts = {arm: sum(1 for run in runs if run["arm"] == arm) for arm in ARMS}
    gates["all_runs_present"] = {
        "passed": not report["failures"]
        and not duplicates
        and not missing
        and not unexpected
        and len(observed_keys) == len(expected_keys)
        and len(programs) == 8,
        "detail": (
            f"expected {len(expected_keys)} unique (arm, program, repetition) keys over "
            f"{len(programs)} programs, observed {len(observed_keys)} rows and "
            f"{len(observed_set)} unique; {len(duplicates)} duplicated, {len(missing)} missing, "
            f"{len(unexpected)} unexpected, {len(report['failures'])} execution failures; "
            f"rows per arm {counts}"
        ),
        "duplicates": [list(key) for key in duplicates],
        "missing": [list(key) for key in missing],
        "unexpected": [list(key) for key in unexpected],
    }

    # The frozen baselines must reproduce their recorded integers, not merely
    # an equal aggregate. Doubling cycles while halving scratch leaves every
    # product and therefore every score untouched.
    historical = report.get("historical_metrics") or {}
    drift = []
    for run in runs:
        expected = historical.get(run["arm"], {}).get(run["program"])
        if expected is None:
            continue
        if run["cycles"] != expected["cycles"] or run["scratch"] != expected["scratch"]:
            drift.append(
                {
                    "arm": run["arm"],
                    "program": run["program"],
                    "repeat": run["repeat"],
                    "expected": expected,
                    "observed": {"cycles": run["cycles"], "scratch": run["scratch"]},
                }
            )
    controlled = sum(
        1 for run in runs if historical.get(run["arm"], {}).get(run["program"])
    )
    gates["frozen_integer_metrics"] = {
        "passed": not drift and controlled > 0,
        "detail": (
            f"{controlled} serial and classical measurements checked against the "
            f"protected historical per-program integers; {len(drift)} disagree"
        ),
        "drift": drift,
    }

    bad_metrics = [
        run
        for run in runs
        if not isinstance(run["cycles"], int)
        or not isinstance(run["scratch"], int)
        or run["cycles"] <= 0
        or run["scratch"] <= 0
        or run["correctness"] != "PASS"
    ]
    gates["metrics_valid"] = {
        "passed": not bad_metrics,
        "detail": f"{len(bad_metrics)} runs with non-positive or unvalidated metrics",
    }

    direct_scores = [
        score["combined_score"] for score in report["per_repeat"].get("direct_index", [])
    ]
    gates["direct_beats_baseline"] = {
        "passed": bool(direct_scores)
        and len(direct_scores) == repeats
        and all(score > 1.0 for score in direct_scores),
        "detail": f"direct combined scores per repetition: {direct_scores}; "
        f"each must exceed 1.0 and all {repeats} must be present",
    }

    classical_repeats = report["per_repeat"].get("classical", [])
    classical_ids = sorted(score["repeat"] for score in classical_repeats)
    classical_scores = [score["combined_score"] for score in classical_repeats]
    # Every requested repetition must be present, not merely some of them.
    control_ok = (
        classical_ids == list(range(repeats))
        and all(
            math.isclose(score, HISTORICAL_CLASSICAL_SCORE, rel_tol=0, abs_tol=1e-9)
            for score in classical_scores
        )
    )
    gates["frozen_classical_control"] = {
        "passed": control_ok,
        "detail": f"classical aggregates for repetitions {classical_ids} "
        f"(all of {list(range(repeats))} required): {classical_scores}, each within "
        f"1e-9 of the historical {HISTORICAL_CLASSICAL_SCORE!r}",
    }

    discrepant = [
        run for run in runs if run.get("discrepancy_count", 0)
    ]
    gates["no_candidate_discrepancies"] = {
        "passed": not discrepant,
        "detail": f"{len(discrepant)} measured compilations reported a "
        f"query/validator discrepancy",
    }

    leaked = [run for run in runs if run.get("leaked")]
    gates["direct_arm_isolated"] = {
        "passed": not leaked,
        "detail": f"{len(leaked)} direct runs loaded a prohibited module",
    }

    gates["all_passed"] = {
        "passed": all(gate["passed"] for gate in gates.values()),
        "detail": "every gate above",
    }
    return gates


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
            (
                f"Every recorded repetition of the direct arm scored above 1.0; "
                f"the lowest was {direct['combined_score_min']:.6f}x."
            )
            if report["gates"]["direct_beats_baseline"]["passed"]
            else (
                "**The score gate FAILED.** "
                + report["gates"]["direct_beats_baseline"]["detail"]
            ),
        ]
    lines += ["", "## Acceptance gates", "", "| Gate | Result | Detail |", "|---|---|---|"]
    for name, gate in report["gates"].items():
        lines.append(
            "| {name} | {verdict} | {detail} |".format(
                name=name.replace("_", " "),
                verdict="PASS" if gate["passed"] else "**FAIL**",
                detail=gate["detail"],
            )
        )
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
    for name, gate in report["gates"].items():
        if name == "all_passed":
            continue
        print(
            f"gate {name}: {'PASS' if gate['passed'] else 'FAIL'} — {gate['detail']}",
            file=sys.stderr,
        )
    print(str(Path(arguments.output) / "runs.json"))
    # Running cleanly is not passing. A correct compiler that only matched the
    # serial baseline would reach here with no failures and must still exit
    # nonzero.
    return 0 if report["gates"]["all_passed"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
