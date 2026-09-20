"""Paired five-arm performance harness for the direct-index optimization phase.

Section 4 of ``plan/OPTIMIZATION_PHASE_PLAN.md``. This is a *performance*
instrument. It does not replace ``compare_direct.py``, which remains the owner
of the official three-arm acceptance comparison and whose gates decide release.
Where the two need the same fact — protected hashes, the pinned reference, the
export freshness check, the historical per-program integers, the public program
set, the geometric mean — this module imports that fact from ``compare_direct``
rather than restating it. The corpus generator of ``tests_direct`` is likewise
the owner of generated programs; the extra evaluation corpus here is built by
calling it, not by writing a second generator.

Five arms, each measured in a fresh isolated process:

* ``classical`` — the frozen ``common.classical_compile``.
* ``frozen_bootstrap`` — the frozen v3 export, ``optimise=False``.
* ``frozen_full`` — the frozen v3 export, ``optimise=True``.
* ``candidate_bootstrap`` — the candidate export, ``optimise=False``.
* ``candidate_full`` — the candidate export, ``optimise=True``.

Frozen and candidate are measured *together* in every phase, so no candidate
time is ever divided by a historical number. During the baseline phase the two
exports are the same file, which makes that phase a measurement of the harness's
own noise floor as well as a record of the starting point.

Three timings are kept apart and mean different things. ``compile_seconds`` is
the compiler call alone, including any validation that call performs
internally. ``import_seconds`` is the worker's own import cost.
``process_seconds`` is the whole subprocess, which is what the external twenty
second limit governs. External reference validation and every case check happen
*after* the timer, for every arm alike.
"""

from __future__ import annotations

import argparse
import cProfile
import io
import json
import math
import os
import platform
import pstats
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import compare_direct as official  # noqa: E402  (the owner of the shared facts)
import verify_direct as verification  # noqa: E402  (the owner of the source list)

REFERENCE = official.REFERENCE
EXPORT = official.EXPORT

# Reused from the official comparator rather than redefined here.
digest = official.digest
geomean = official.geomean
verify_protected = official.verify_protected
verify_reference = official.verify_reference
verify_export_fresh = official.verify_export_fresh
historical_metrics = official.historical_metrics
program_name_of = official._name_of

ARMS = (
    "classical",
    "frozen_bootstrap",
    "frozen_full",
    "candidate_bootstrap",
    "candidate_full",
)

DIRECT_ARMS = tuple(arm for arm in ARMS if arm != "classical")

# (label, baseline arm, candidate arm). A speedup is baseline / candidate.
RATIOS = (
    ("full_candidate_vs_frozen", "frozen_full", "candidate_full"),
    ("bootstrap_candidate_vs_frozen", "frozen_bootstrap", "candidate_bootstrap"),
    ("full_candidate_vs_classical", "classical", "candidate_full"),
    ("bootstrap_candidate_vs_classical", "classical", "candidate_bootstrap"),
    ("full_frozen_vs_classical", "classical", "frozen_full"),
    ("bootstrap_frozen_vs_classical", "classical", "frozen_bootstrap"),
    ("optimizer_cost_frozen", "frozen_bootstrap", "frozen_full"),
    ("optimizer_cost_candidate", "candidate_bootstrap", "candidate_full"),
)

# Section 1's engineering targets. These are objectives, not licence to weaken
# anything to reach them; an unmet target is a valid recorded outcome.
TARGETS = {
    "full_candidate_vs_frozen": 2.0,
    "bootstrap_candidate_vs_frozen": 1.20,
}

BOOTSTRAP_RESAMPLES = 10000
DEFAULT_SEED = 20260920
EXTRA_CORPUS_SEED = 20260921
EXTRA_PER_FAMILY = 20

# The verification runner owns the list of production sources; it is imported
# rather than restated so the two can never drift apart.
SOURCES = verification.SOURCES


# --------------------------------------------------------------------------
# Workers
# --------------------------------------------------------------------------


# The direct arms run here: -I -S from a neutral directory holding only an
# export and the pinned machine module, so neither the development tree nor an
# inherited environment is reachable. The optimise flag selects bootstrap or
# full; nothing else differs between the four direct arms.
DIRECT_WORKER = r'''
import json, resource, sys, time
_started = time.perf_counter()
sys.path.insert(0, sys.argv[1])
import machine

def prohibited(*args, **kwargs):
    raise AssertionError("serial_compile was called by the direct export")

machine.serial_compile = prohibited
import compiler
import_seconds = time.perf_counter() - _started

arm = sys.argv[3]
optimise = sys.argv[4] == "1"
program = machine.load_program(sys.argv[2])

# Only the call is timed. Validation of the result is done afterwards, for
# every arm alike, and no internal safety check is disabled to make the
# implementations comparable.
started = time.perf_counter()
compiled, report = compiler.compile_with_report(program, optimise=optimise)
compile_seconds = time.perf_counter() - started

validate_started = time.perf_counter()
cycles = machine.check_compilation(program, compiled)
cases = 0
for case in program["cases"]:
    machine.check_case(program, compiled, case)
    cases += 1
validate_seconds = time.perf_counter() - validate_started

peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
if sys.platform != "darwin":
    peak *= 1024
banned = {"common", "compilers", "index_query", "repertoire_program", "direct_compiler"}
optimisation = report.get("optimisation", {})
bootstrap = report.get("bootstrap", {})
print(json.dumps({
    "arm": arm,
    "identity": compiler.__file__,
    "program": program["name"],
    "optimise": optimise,
    "cycles": cycles,
    "scratch": machine.scratch_footprint(program, compiled),
    "compile_seconds": compile_seconds,
    "import_seconds": import_seconds,
    "validate_seconds": validate_seconds,
    "peak_rss_bytes": peak,
    "correctness": "PASS",
    "cases": cases,
    "discrepancy_count": report.get("discrepancy_count", 0),
    "optimisation_enabled": bool(optimisation.get("enabled")),
    "optimiser": {
        "accepted": optimisation.get("accepted", 0),
        "attempted": optimisation.get("attempted_queries", 0),
        "statuses": optimisation.get("statuses", {}),
        "stopped_because": optimisation.get("stopped_because"),
        "seconds": optimisation.get("seconds"),
    },
    "bootstrap_metrics": {
        "cycles": bootstrap.get("cycles"),
        "footprint": bootstrap.get("footprint"),
        "seconds": bootstrap.get("seconds"),
        "queries": bootstrap.get("queries"),
    },
    "leaked": sorted(n for n in sys.modules if n.split(".")[0] in banned),
}))
'''


def classical_worker(program_path: str) -> dict:
    """The classical arm, measured under the same protocol as the direct arms."""

    started = time.perf_counter()
    sys.path.insert(0, str(REFERENCE))
    import machine

    sys.path.insert(0, str(ROOT))
    import common

    import_seconds = time.perf_counter() - started

    program = machine.load_program(program_path)
    call_started = time.perf_counter()
    compilation = common.classical_compile(program)
    compile_seconds = time.perf_counter() - call_started

    validate_started = time.perf_counter()
    cycles = machine.check_compilation(program, compilation)
    cases = 0
    for case in program["cases"]:
        machine.check_case(program, compilation, case)
        cases += 1
    validate_seconds = time.perf_counter() - validate_started

    return {
        "arm": "classical",
        "identity": "common.classical_compile",
        "program": program["name"],
        "optimise": None,
        "cycles": cycles,
        "scratch": machine.scratch_footprint(program, compilation),
        "compile_seconds": compile_seconds,
        "import_seconds": import_seconds,
        "validate_seconds": validate_seconds,
        "peak_rss_bytes": official.peak_rss_bytes(),
        "correctness": "PASS",
        "cases": cases,
        "discrepancy_count": 0,
        "optimisation_enabled": False,
        "optimiser": {},
        "bootstrap_metrics": {},
        "leaked": [],
    }


# --------------------------------------------------------------------------
# Measurement
# --------------------------------------------------------------------------


class Bench:
    """One measurement session over a fixed set of programs and arms."""

    def __init__(
        self,
        frozen_export: Path,
        candidate_export: Path,
        timeout: float,
        seed: int,
    ) -> None:
        self.frozen_export = Path(frozen_export)
        self.candidate_export = Path(candidate_export)
        self.timeout = timeout
        self.seed = seed
        self._directories: Dict[str, Path] = {}
        self._temporary: List[Path] = []

    def __enter__(self) -> "Bench":
        for label, export in (
            ("frozen", self.frozen_export),
            ("candidate", self.candidate_export),
        ):
            directory = Path(tempfile.mkdtemp(prefix=f"v4-{label}-"))
            shutil.copyfile(export, directory / "compiler.py")
            shutil.copyfile(REFERENCE / "machine.py", directory / "machine.py")
            self._directories[label] = directory
            self._temporary.append(directory)
        return self

    def __exit__(self, *exc) -> None:
        for directory in self._temporary:
            shutil.rmtree(directory, ignore_errors=True)

    def command_for(self, arm: str, path: Path) -> Tuple[List[str], str]:
        if arm == "classical":
            return (
                [sys.executable, __file__, "--worker", "classical", "--program", str(path)],
                str(ROOT),
            )
        label = "frozen" if arm.startswith("frozen") else "candidate"
        optimise = "1" if arm.endswith("_full") else "0"
        directory = self._directories[label]
        return (
            [
                sys.executable,
                "-I",
                "-S",
                "-c",
                DIRECT_WORKER,
                str(directory),
                str(path),
                arm,
                optimise,
            ],
            str(directory),
        )

    def run(
        self,
        paths: Sequence[Path],
        arms: Sequence[str],
        repeats: int,
        quiet: bool = False,
    ) -> Tuple[List[dict], List[dict], List[dict]]:
        """Measure every ``(arm, program, repetition)`` in a fresh process.

        The arm order inside each ``(program, repetition)`` is shuffled from a
        pinned seed and retained, so no arm can benefit from a fixed position
        and the schedule is reproducible. Nothing is discarded: there are no
        warmups, no outlier removal and no silent retries, and a failed row
        stays in the dataset where it invalidates a success claim.
        """

        rng = random.Random(self.seed)
        runs: List[dict] = []
        failures: List[dict] = []
        orders: List[dict] = []
        names = [program_name_of(path) for path in paths]

        total = len(paths) * repeats * len(arms)
        done = 0
        for path, name in zip(paths, names):
            for repeat in range(repeats):
                order = list(arms)
                rng.shuffle(order)
                orders.append({"program": name, "repeat": repeat, "order": list(order)})
                for arm in order:
                    done += 1
                    if not quiet and done % 25 == 0:
                        print(
                            f"  {done}/{total} measurements", file=sys.stderr, flush=True
                        )
                    record, failure = self._one(arm, path, name, repeat)
                    if failure is not None:
                        failures.append(failure)
                    else:
                        runs.append(record)
        return runs, failures, orders

    def _one(
        self, arm: str, path: Path, name: str, repeat: int
    ) -> Tuple[Optional[dict], Optional[dict]]:
        argv, working = self.command_for(arm, path)
        started = time.monotonic()
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=working,
            )
            process_seconds = time.monotonic() - started
            timed_out = False
        except subprocess.TimeoutExpired:
            process_seconds = self.timeout
            timed_out = True
            completed = None

        base = {"arm": arm, "program": name, "repeat": repeat, "argv": argv}
        if timed_out or completed is None or completed.returncode != 0:
            return None, dict(
                base,
                timed_out=timed_out,
                exit_code=None if completed is None else completed.returncode,
                stderr_tail="" if completed is None else completed.stderr[-1500:],
                error="worker exited nonzero" if not timed_out else "worker timed out",
            )
        try:
            record = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return None, dict(
                base,
                timed_out=False,
                exit_code=completed.returncode,
                error="worker output was not JSON",
                stdout_tail=completed.stdout[-1500:],
            )

        # Identity is checked against what was actually requested before the
        # parent stamps its own repetition on the row. Trusting the worker's
        # own label lets a duplicated measurement fill a missing slot and leave
        # the row count intact.
        if record.get("arm") != arm or record.get("program") != name:
            return None, dict(
                base,
                timed_out=False,
                exit_code=completed.returncode,
                error=(
                    f"worker answered for ({record.get('arm')!r}, "
                    f"{record.get('program')!r}) when ({arm!r}, {name!r}) was requested"
                ),
            )
        expected_optimise = None if arm == "classical" else arm.endswith("_full")
        if record.get("optimise") != expected_optimise:
            return None, dict(
                base,
                timed_out=False,
                exit_code=completed.returncode,
                error=(
                    f"worker reported optimise={record.get('optimise')!r} for arm {arm!r}"
                ),
            )
        record.update(
            {
                "repeat": repeat,
                "process_seconds": process_seconds,
                "timed_out": False,
                "exit_code": completed.returncode,
            }
        )
        return record, None


# --------------------------------------------------------------------------
# Row validation — gate 10
# --------------------------------------------------------------------------


def validate_rows(
    runs: Sequence[dict],
    failures: Sequence[dict],
    programs: Sequence[str],
    arms: Sequence[str],
    repeats: int,
) -> dict:
    """Exact membership and per-row validity.

    Counting rows establishes nothing: a duplicate standing in for a missing
    measurement leaves the count untouched. Membership is therefore checked as
    a set of ``(arm, program, repetition)`` keys against the expected set.
    """

    expected = {
        (arm, program, repeat)
        for arm in arms
        for program in programs
        for repeat in range(repeats)
    }
    observed = [(run["arm"], run["program"], run["repeat"]) for run in runs]
    counted: Dict[Tuple[str, str, int], int] = {}
    for key in observed:
        counted[key] = counted.get(key, 0) + 1
    duplicates = sorted(key for key, count in counted.items() if count > 1)
    missing = sorted(expected - set(observed))
    unexpected = sorted(set(observed) - expected)

    invalid = []
    for run in runs:
        problems = []
        if not isinstance(run.get("cycles"), int) or run.get("cycles", 0) <= 0:
            problems.append("cycles")
        if not isinstance(run.get("scratch"), int) or run.get("scratch", 0) <= 0:
            problems.append("scratch")
        if run.get("correctness") != "PASS":
            problems.append("correctness")
        if run.get("cases", 0) <= 0:
            problems.append("cases")
        if run.get("discrepancy_count", 0):
            problems.append("discrepancy")
        if run.get("leaked"):
            problems.append("module leak")
        if not isinstance(run.get("compile_seconds"), (int, float)) or run.get(
            "compile_seconds", -1
        ) < 0:
            problems.append("compile_seconds")
        if problems:
            invalid.append(
                {
                    "arm": run.get("arm"),
                    "program": run.get("program"),
                    "repeat": run.get("repeat"),
                    "problems": problems,
                }
            )

    passed = (
        not failures
        and not duplicates
        and not missing
        and not unexpected
        and not invalid
        and len(observed) == len(expected)
        and len(expected) > 0
    )
    return {
        "passed": passed,
        "expected_keys": len(expected),
        "observed_rows": len(observed),
        "unique_keys": len(set(observed)),
        "duplicates": [list(key) for key in duplicates],
        "missing": [list(key) for key in missing],
        "unexpected": [list(key) for key in unexpected],
        "invalid_rows": invalid,
        "execution_failures": list(failures),
        "detail": (
            f"expected {len(expected)} unique (arm, program, repetition) keys over "
            f"{len(programs)} programs and {len(arms)} arms; observed {len(observed)} "
            f"rows, {len(set(observed))} unique; {len(duplicates)} duplicated, "
            f"{len(missing)} missing, {len(unexpected)} unexpected, {len(invalid)} "
            f"invalid, {len(failures)} execution failures"
        ),
    }


def check_frozen_integers(runs: Sequence[dict], history: dict) -> dict:
    """The classical arm must reproduce its protected per-program integers.

    An aggregate is not enough. Doubling cycles while halving scratch leaves
    every product, and therefore every score, exactly where it was.
    """

    drift = []
    controlled = 0
    for run in runs:
        if run["arm"] != "classical":
            continue
        expected = history.get("classical", {}).get(run["program"])
        if expected is None:
            continue
        controlled += 1
        if run["cycles"] != expected["cycles"] or run["scratch"] != expected["scratch"]:
            drift.append(
                {
                    "program": run["program"],
                    "repeat": run["repeat"],
                    "expected": expected,
                    "observed": {"cycles": run["cycles"], "scratch": run["scratch"]},
                }
            )
    return {
        "passed": not drift and controlled > 0,
        "checked": controlled,
        "drift": drift,
        "detail": (
            f"{controlled} classical measurements checked against the protected "
            f"historical per-program integers; {len(drift)} disagree"
        ),
    }


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------


def per_program_medians(
    runs: Sequence[dict], programs: Sequence[str], arms: Sequence[str], key: str
) -> Dict[str, Dict[str, float]]:
    table: Dict[str, Dict[str, List[float]]] = {
        arm: {program: [] for program in programs} for arm in arms
    }
    for run in runs:
        if run["arm"] in table and run["program"] in table[run["arm"]]:
            table[run["arm"]][run["program"]].append(run[key])
    return {
        arm: {
            program: statistics.median(values) if values else float("nan")
            for program, values in rows.items()
        }
        for arm, rows in table.items()
    }


def aggregate_ratio(
    medians: Dict[str, Dict[str, float]],
    programs: Sequence[str],
    baseline: str,
    candidate: str,
) -> dict:
    """The equal-program geometric mean of per-program median ratios.

    This is the primary aggregate. The pooled median of all of one arm's times
    divided by the other's is reported separately and is a different quantity;
    the two are never mixed.
    """

    ratios = {}
    for program in programs:
        base = medians[baseline][program]
        cand = medians[candidate][program]
        ratios[program] = base / cand if cand > 0 else float("inf")
    values = [ratios[program] for program in programs]
    losing = sorted(program for program in programs if ratios[program] < 1.0)
    return {
        "baseline_arm": baseline,
        "candidate_arm": candidate,
        "per_program_ratio": ratios,
        "geometric_mean_of_per_program_medians": geomean(values),
        "min_ratio": min(values),
        "max_ratio": max(values),
        "programs_slower_than_baseline": losing,
    }


def pooled_median_ratio(
    runs: Sequence[dict], baseline: str, candidate: str, key: str = "compile_seconds"
) -> float:
    """The existing pooled-median statistic, reported explicitly and apart."""

    base = [run[key] for run in runs if run["arm"] == baseline]
    cand = [run[key] for run in runs if run["arm"] == candidate]
    if not base or not cand:
        return float("nan")
    denominator = statistics.median(cand)
    if denominator <= 0:
        return float("inf")
    return statistics.median(base) / denominator


def paired_bootstrap(
    runs: Sequence[dict],
    programs: Sequence[str],
    baseline: str,
    candidate: str,
    repeats: int,
    seed: int = DEFAULT_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
    key: str = "compile_seconds",
) -> dict:
    """A paired 95% percentile interval over repetition identifiers.

    Repetition IDs are resampled within each program and used jointly for every
    arm, so the pairing that makes the comparison fair is preserved. This
    interval measures timing uncertainty on this fixed suite of programs. It
    says nothing about programs outside the suite.
    """

    indexed: Dict[Tuple[str, str], Dict[int, List[float]]] = {}
    for run in runs:
        indexed.setdefault((run["arm"], run["program"]), {}).setdefault(
            run["repeat"], []
        ).append(run[key])

    def series(arm: str, program: str, repeat: int) -> List[float]:
        return indexed.get((arm, program), {}).get(repeat, [])

    rng = random.Random(seed)
    draws: List[float] = []
    for _ in range(resamples):
        ratios = []
        for program in programs:
            picks = [rng.randrange(repeats) for _ in range(repeats)]
            base_values: List[float] = []
            cand_values: List[float] = []
            for pick in picks:
                base_values.extend(series(baseline, program, pick))
                cand_values.extend(series(candidate, program, pick))
            if not base_values or not cand_values:
                ratios = []
                break
            denominator = statistics.median(cand_values)
            ratios.append(
                statistics.median(base_values) / denominator
                if denominator > 0
                else float("inf")
            )
        if ratios:
            draws.append(geomean(ratios))
    if not draws:
        return {"low": float("nan"), "high": float("nan"), "resamples": 0}
    draws.sort()
    low = draws[int(0.025 * (len(draws) - 1))]
    high = draws[int(math.ceil(0.975 * (len(draws) - 1)))]
    return {
        "low": low,
        "high": high,
        "median": statistics.median(draws),
        "resamples": len(draws),
        "seed": seed,
    }


def combined_score(
    medians_cycles: Dict[str, int],
    medians_scratch: Dict[str, int],
    serial: Dict[str, Dict[str, int]],
    programs: Sequence[str],
) -> float:
    """The official combined score, recomputed from raw integers.

    The serial baseline integers come from the protected historical record
    rather than from a re-measurement: ``serial`` is not one of this harness's
    five arms, and ``compare_direct``'s ``frozen_integer_metrics`` gate is what
    keeps that record honest against a fresh serial run.
    """

    cycle_ratios = []
    scratch_ratios = []
    for program in programs:
        cycle_ratios.append(serial[program]["cycles"] / medians_cycles[program])
        scratch_ratios.append(serial[program]["scratch"] / medians_scratch[program])
    return math.sqrt(geomean(cycle_ratios) * geomean(scratch_ratios))


def metric_table(runs: Sequence[dict], programs: Sequence[str], arm: str) -> dict:
    """Per-program integer metrics for one arm, with any within-arm variation."""

    cycles: Dict[str, set] = {program: set() for program in programs}
    scratch: Dict[str, set] = {program: set() for program in programs}
    for run in runs:
        if run["arm"] != arm:
            continue
        cycles[run["program"]].add(run["cycles"])
        scratch[run["program"]].add(run["scratch"])
    varying = sorted(
        program
        for program in programs
        if len(cycles[program]) > 1 or len(scratch[program]) > 1
    )
    return {
        "cycles": {p: sorted(cycles[p]) for p in programs},
        "scratch": {p: sorted(scratch[p]) for p in programs},
        "deterministic": not varying,
        "varying_programs": varying,
    }


def bootstrap_equals_full(runs: Sequence[dict], programs: Sequence[str], label: str) -> dict:
    """Test — not assume — that bootstrap metrics equal full-direct metrics.

    Section 4 requires this hypothesis to be measured per program and its
    discrepancies reported, not merely an aggregate equality.
    """

    boot = metric_table(runs, programs, f"{label}_bootstrap")
    full = metric_table(runs, programs, f"{label}_full")
    discrepancies = []
    for program in programs:
        if boot["cycles"][program] != full["cycles"][program] or (
            boot["scratch"][program] != full["scratch"][program]
        ):
            discrepancies.append(
                {
                    "program": program,
                    "bootstrap": {
                        "cycles": boot["cycles"][program],
                        "scratch": boot["scratch"][program],
                    },
                    "full": {
                        "cycles": full["cycles"][program],
                        "scratch": full["scratch"][program],
                    },
                }
            )
    return {
        "label": label,
        "hypothesis": "bootstrap cycles and scratch equal full-direct cycles and scratch",
        "holds": not discrepancies,
        "programs": len(programs),
        "discrepancies": discrepancies,
        "bootstrap_metrics": boot,
        "full_metrics": full,
    }


def analyse(
    runs: Sequence[dict],
    failures: Sequence[dict],
    programs: Sequence[str],
    arms: Sequence[str],
    repeats: int,
    history: dict,
    seed: int,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> dict:
    medians = per_program_medians(runs, programs, arms, "compile_seconds")
    process_medians = per_program_medians(runs, programs, arms, "process_seconds")
    import_medians = per_program_medians(runs, programs, arms, "import_seconds")

    ratios = {}
    for label, baseline, candidate in RATIOS:
        if baseline not in arms or candidate not in arms:
            continue
        entry = aggregate_ratio(medians, programs, baseline, candidate)
        entry["pooled_median_ratio"] = pooled_median_ratio(runs, baseline, candidate)
        entry["paired_bootstrap_95"] = paired_bootstrap(
            runs, programs, baseline, candidate, repeats, seed=seed, resamples=resamples
        )
        if label in TARGETS:
            target = TARGETS[label]
            entry["target"] = target
            entry["target_met"] = bool(
                entry["geometric_mean_of_per_program_medians"] >= target
                and entry["paired_bootstrap_95"]["low"] > 1.0
            )
        ratios[label] = entry

    serial = history.get("serial", {})
    scores = {}
    for arm in arms:
        table = metric_table(runs, programs, arm)
        if any(program not in serial for program in programs):
            # No protected serial baseline covers this program set, which is
            # the case for the frozen evaluation corpus. Its scores are
            # computed separately from its own manifest rather than left to
            # fall back on a baseline that does not describe it.
            scores[arm] = {
                "combined_score": None,
                "note": (
                    "no protected serial baseline for these programs; see the "
                    "corpus score distribution instead"
                ),
                "metrics": table,
            }
            continue
        if any(len(values) != 1 for values in table["cycles"].values()):
            scores[arm] = {
                "combined_score": None,
                "note": "metrics varied within the arm; no single score is defined",
                "metrics": table,
            }
            continue
        cycles = {p: table["cycles"][p][0] for p in programs}
        scratch = {p: table["scratch"][p][0] for p in programs}
        scores[arm] = {
            "combined_score": combined_score(cycles, scratch, serial, programs),
            "metrics": table,
        }

    optimiser = {}
    for arm in arms:
        if not arm.endswith("_full"):
            continue
        entries = [run for run in runs if run["arm"] == arm]
        statuses: Dict[str, int] = {}
        for run in entries:
            for name, count in (run.get("optimiser", {}).get("statuses") or {}).items():
                statuses[name] = statuses.get(name, 0) + count
        optimiser[arm] = {
            "accepted_total": sum(
                run.get("optimiser", {}).get("accepted", 0) for run in entries
            ),
            "attempted_total": sum(
                run.get("optimiser", {}).get("attempted", 0) for run in entries
            ),
            "statuses": statuses,
            "median_optimiser_seconds": (
                statistics.median(
                    [
                        run["optimiser"]["seconds"]
                        for run in entries
                        if run.get("optimiser", {}).get("seconds") is not None
                    ]
                )
                if entries
                else None
            ),
        }

    return {
        "programs": list(programs),
        "arms": list(arms),
        "repetitions": repeats,
        "membership": validate_rows(runs, failures, programs, arms, repeats),
        "frozen_classical_integers": check_frozen_integers(runs, history),
        "median_compile_seconds": medians,
        "median_process_seconds": process_medians,
        "median_import_seconds": import_medians,
        "ratios": ratios,
        "scores": scores,
        "optimiser": optimiser,
        "bootstrap_vs_full": [
            bootstrap_equals_full(runs, programs, label)
            for label in ("frozen", "candidate")
            if f"{label}_bootstrap" in arms and f"{label}_full" in arms
        ],
        "statistic_definitions": {
            "speedup": "baseline median compile time divided by candidate median",
            "primary_aggregate": (
                "equal-program geometric mean of per-program median ratios"
            ),
            "pooled_median_ratio": (
                "median of all baseline times divided by median of all candidate "
                "times; a different quantity from the primary aggregate and never "
                "mixed with it"
            ),
            "paired_bootstrap_95": (
                "percentile interval over repetition identifiers resampled within "
                "each program and used jointly for every arm; timing uncertainty on "
                "this fixed program suite only"
            ),
            "serial_baseline": (
                "combined scores use the protected historical serial integers; "
                "serial is not one of this harness's arms"
            ),
        },
    }


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------


def git_state() -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.run(
                ["git", *args],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()
        except OSError:
            return ""

    return {
        "commit": run("rev-parse", "HEAD"),
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "status_porcelain": run("status", "--porcelain", "--", str(ROOT)),
    }


def provenance(export_hash: str) -> dict:
    return {
        "recorded": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "git": git_state(),
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "reference_commit": verify_reference(),
        "protected_sha256": verify_protected(),
        "source_sha256": {name: digest(ROOT / name) for name in SOURCES},
        "test_sha256": {
            path.name: digest(path)
            for path in sorted((ROOT / "tests_direct").glob("*.py"))
        },
        "export_sha256": export_hash,
        "export_lines": len(EXPORT.read_text(encoding="utf-8").splitlines()),
    }


def public_paths() -> List[Path]:
    """The public set, from the official comparator's pinned membership rule."""

    paths = sorted((REFERENCE / "programs").glob("*.json"))
    if len(paths) != 8:
        raise RuntimeError(f"expected eight public programs, found {len(paths)}")
    return paths


# --------------------------------------------------------------------------
# Extra evaluation corpus
# --------------------------------------------------------------------------


def build_extra_corpus(destination: Path) -> dict:
    """Freeze a deterministic evaluation corpus from the existing generator.

    Twenty programs from each of the five existing families, selected by a
    pinned seed from the range above the acceptance corpus's own seeds so that
    no program is shared with it. This corpus is generated by the same
    generator as the acceptance corpus and is therefore **not** statistically
    independent of it; it is a held-out evaluation set, nothing more.
    """

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(REFERENCE))
    from tests_direct import generate_programs as gp
    import machine

    rng = random.Random(EXTRA_CORPUS_SEED)
    excluded = set(gp.ADDITIONAL_SEEDS) | set(range(30))
    wanted = {family: [] for family in gp.FAMILIES}
    seen: set = set()
    while any(len(values) < EXTRA_PER_FAMILY for values in wanted.values()):
        seed = rng.randrange(200000, 400000)
        if seed in excluded or seed in seen:
            continue
        seen.add(seed)
        family = gp.FAMILIES[seed % 5]
        if len(wanted[family]) >= EXTRA_PER_FAMILY:
            continue
        wanted[family].append(seed)

    destination.mkdir(parents=True, exist_ok=True)
    entries = []
    index = 0
    for family in gp.FAMILIES:
        for seed in sorted(wanted[family]):
            program = gp.additional_program(seed)
            machine.validate_program(program)
            baseline = machine.serial_compile(program)
            machine.check_compilation(program, baseline)
            for case in program["cases"]:
                machine.check_case(program, baseline, case)
            path = destination / f"{index:03d}_{program['name']}.json"
            path.write_text(json.dumps(program, sort_keys=True), encoding="utf-8")
            entries.append(
                {
                    "index": index,
                    "file": path.name,
                    "name": program["name"],
                    "seed": seed,
                    "family": family,
                    "operations": len(program["operations"]),
                    "cases": len(program["cases"]),
                    "serial_cycles": len(baseline["bundles"]),
                    "serial_scratch": machine.scratch_footprint(program, baseline),
                    "reference_valid": True,
                    "sha256": gp.program_digest(program),
                }
            )
            index += 1

    manifest = {
        "seed": EXTRA_CORPUS_SEED,
        "per_family": EXTRA_PER_FAMILY,
        "families": list(gp.FAMILIES),
        "size": len(entries),
        "excluded_seed_ranges": ["0-29 regression", "1000-1099 acceptance additional"],
        "independence_note": (
            "generated by the same generator as the acceptance corpus; a held-out "
            "evaluation set, not a statistically independent sample"
        ),
        "programs": entries,
    }
    (destination.parent / "extra_corpus_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return manifest


def verify_extra_corpus(destination: Path, manifest: dict) -> dict:
    """Re-hash a frozen corpus before it is used for evaluation."""

    sys.path.insert(0, str(ROOT))
    from tests_direct import generate_programs as gp

    drift = []
    for entry in manifest["programs"]:
        path = destination / entry["file"]
        if not path.exists():
            drift.append({"file": entry["file"], "error": "missing"})
            continue
        program = json.loads(path.read_text())
        if gp.program_digest(program) != entry["sha256"]:
            drift.append({"file": entry["file"], "error": "content hash changed"})
    return {"passed": not drift, "checked": len(manifest["programs"]), "drift": drift}


# --------------------------------------------------------------------------
# Profiling
# --------------------------------------------------------------------------


PROFILE_TARGETS = (
    "direct_optimizer.optimise",
    "JointQuery.expression",
    "relation_cover",
    "_scratch_safety",
    "_engine_capacity",
    "schema_index.restrict",
    "Cube",
    "solve",
    "intersect",
    "normalise_cover",
    "interval",
    "record",
    "_subtract_cover",
    "_intersect_cover",
    "difference",
    "check_time",
    "bounds",
)


def profile_program(path: Path, optimise: bool, output: Path) -> dict:
    """Profile one compilation of the development modules.

    Profiling changes wall-clock search behaviour, so nothing measured here is
    a performance result. It is used only to find where the time goes.
    """

    sys.path.insert(0, str(REFERENCE))
    sys.path.insert(0, str(ROOT))
    import machine
    import direct_compiler

    program = machine.load_program(path)
    profiler = cProfile.Profile()
    profiler.enable()
    compiled, report = direct_compiler.compile_with_report(program, optimise=optimise)
    profiler.disable()

    machine.check_compilation(program, compiled)
    for case in program["cases"]:
        machine.check_case(program, compiled, case)

    buffer = io.StringIO()
    stats = pstats.Stats(profiler, stream=buffer)
    stats.sort_stats("cumulative")
    stats.print_stats(45)
    label = f"{path.stem}_{'full' if optimise else 'bootstrap'}"
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{label}.txt").write_text(buffer.getvalue(), encoding="utf-8")

    rows = []
    for (filename, line, function), (calls, _, tottime, cumtime, _) in stats.stats.items():
        module = Path(filename).name
        for target in PROFILE_TARGETS:
            needle = target.split(".")[-1]
            if needle == function or (
                "." in target and target.split(".")[0] in module and needle in function
            ):
                rows.append(
                    {
                        "function": f"{module}:{line}({function})",
                        "matched": target,
                        "calls": calls,
                        "tottime": tottime,
                        "cumtime": cumtime,
                    }
                )
                break
    rows.sort(key=lambda row: -row["cumtime"])
    return {
        "program": program["name"],
        "file": path.name,
        "operations": len(program["operations"]),
        "optimise": optimise,
        "total_seconds": stats.total_tt,
        "cycles": len(compiled["bundles"]),
        "footprint": report["footprint"],
        "report_seconds": report["seconds"],
        "hotspots": rows,
        "text_report": str(output / f"{label}.txt"),
    }


# --------------------------------------------------------------------------
# Phases
# --------------------------------------------------------------------------


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def phase_baseline(arguments) -> int:
    output = Path(arguments.output).resolve()
    if output.exists() and any(output.iterdir()) and not arguments.allow_existing:
        print(
            f"{output} already exists and is not empty; use a new numbered round",
            file=sys.stderr,
        )
        return 2
    output.mkdir(parents=True, exist_ok=True)

    export_hash = verify_export_fresh()
    record = provenance(export_hash)

    snapshot = output / "snapshot"
    snapshot.mkdir(parents=True, exist_ok=True)
    for name in SOURCES:
        shutil.copyfile(ROOT / name, snapshot / name)
    shutil.copyfile(EXPORT, snapshot / "compiler_frozen.py")
    record["snapshot_directory"] = str(snapshot)
    record["frozen_export_sha256"] = digest(snapshot / "compiler_frozen.py")
    write_json(output / "provenance.json", record)

    corpus_directory = output / "extra_corpus"
    manifest = build_extra_corpus(corpus_directory)
    print(
        f"froze {manifest['size']} extra evaluation programs", file=sys.stderr, flush=True
    )

    paths = public_paths()
    programs = [program_name_of(path) for path in paths]
    history = historical_metrics()

    print(
        f"measuring {len(ARMS)} arms x {len(paths)} programs x {arguments.repeats} "
        f"repetitions",
        file=sys.stderr,
        flush=True,
    )
    started = time.monotonic()
    with Bench(
        snapshot / "compiler_frozen.py", EXPORT, arguments.timeout, arguments.seed
    ) as bench:
        runs, failures, orders = bench.run(paths, ARMS, arguments.repeats, arguments.quiet)
    elapsed = time.monotonic() - started

    analysis = analyse(
        runs, failures, programs, ARMS, arguments.repeats, history, arguments.seed
    )
    payload = {
        "phase": "baseline",
        "provenance": record,
        "command": " ".join(sys.argv),
        "seed": arguments.seed,
        "timeout_seconds": arguments.timeout,
        "elapsed_seconds": elapsed,
        "arm_order": orders,
        "analysis": analysis,
        "runs": runs,
        "failures": failures,
        "extra_corpus_manifest": str(output / "extra_corpus_manifest.json"),
        "note": (
            "during the baseline phase the frozen and candidate exports are the "
            "same file, so the candidate-versus-frozen ratios measure this "
            "harness's own noise floor rather than any code change"
        ),
    }
    write_json(output / "runs.json", payload)
    report_lines(payload, output / "BASELINE_MEASUREMENTS.md")
    print(summarise(payload), file=sys.stderr)
    print(str(output / "runs.json"))
    return 0 if analysis["membership"]["passed"] else 1


def profile_search(path: Path, output: Path, seconds: float = 120.0) -> List[dict]:
    """Profile the *search* on queries that exhaust the ordinary time budget.

    Under the production hundred-millisecond budget a deterministic profiler
    slows construction enough that the clock expires before the search does any
    work, so a profile taken there sees construction only. These runs give the
    same queries a generous deterministic budget, which is the only way to see
    where solver traversal and cover intersection actually spend their time.
    Nothing measured here is a performance result either.
    """

    sys.path.insert(0, str(REFERENCE))
    sys.path.insert(0, str(ROOT))
    import machine
    import direct_compiler as dcmp
    import direct_constraints as dk
    import direct_contract as dc
    import direct_optimizer as do
    import schema_index as si

    program = machine.load_program(path)
    facts = dc.derive(program)
    limits = dcmp.DEFAULT_LIMITS
    deadline = dcmp._Deadline(limits.total_seconds)
    counters = dcmp._Counters()
    times, addresses = dcmp.bootstrap(facts, limits, deadline, counters)
    cycles = max(times.values()) + 1
    memory = dc.footprint(facts, addresses)

    # Find the queries the production budget cannot finish, then profile them
    # with a budget that lets them run to exhaustion.
    unfinished: List[Tuple[Tuple[int, ...], int, int]] = []
    for target_cycles, target_memory in do.targets_for(facts, cycles, memory):
        for window in do.windows_for(
            facts, times, addresses, scratch_first=target_memory < memory
        ):
            meter = si.Budget(
                seconds=limits.query_seconds,
                max_cover=limits.max_cover,
                max_visited=limits.max_visited,
                max_records=limits.max_records,
            ).start()
            try:
                query = dk.JointQuery(
                    facts, times, addresses, window, target_cycles, target_memory, meter
                )
                expression = query.expression()
            except (dk.Infeasible, si.BudgetExhausted):
                continue
            if si.solve(expression, query.n, meter=meter).is_unknown:
                unfinished.append((window, target_cycles, target_memory))

    output.mkdir(parents=True, exist_ok=True)
    entries = []
    for window, target_cycles, target_memory in unfinished[:2]:
        meter = si.Budget(
            seconds=seconds, max_cover=limits.max_cover,
            max_visited=10 ** 9, max_records=10 ** 9,
        ).start()
        query = dk.JointQuery(
            facts, times, addresses, window, target_cycles, target_memory, meter
        )
        expression = query.expression()
        build_records = meter.records
        profiler = cProfile.Profile()
        profiler.enable()
        result = si.solve(expression, query.n, meter=meter)
        profiler.disable()

        buffer = io.StringIO()
        stats = pstats.Stats(profiler, stream=buffer)
        stats.sort_stats("tottime")
        stats.print_stats(25)
        label = f"{path.stem}_search_{'_'.join(str(i) for i in window)}"
        (output / f"{label}.txt").write_text(buffer.getvalue(), encoding="utf-8")
        entries.append(
            {
                "program": program["name"],
                "window": list(window),
                "target": [target_cycles, target_memory],
                "width_bits": query.n,
                "status_under_generous_budget": result.status,
                "profiled_search_seconds": stats.total_tt,
                "visited": meter.visited,
                "intersections": meter.intersections,
                "expression_records": build_records,
                "text_report": str(output / f"{label}.txt"),
                "note": (
                    "this query returns UNKNOWN under the production 100 ms budget; "
                    "the status here is what exhaustion actually yields"
                ),
            }
        )
    return entries


def phase_profile(arguments) -> int:
    output = Path(arguments.output).resolve()
    if output.exists() and any(output.iterdir()) and not arguments.allow_existing:
        print(f"{output} already exists and is not empty", file=sys.stderr)
        return 2
    output.mkdir(parents=True, exist_ok=True)

    paths = public_paths()
    sizes = sorted(paths, key=lambda path: len(json.loads(path.read_text())["operations"]))
    chosen = [sizes[0], sizes[len(sizes) // 2], sizes[-1]]

    entries = []
    for path in chosen:
        for optimise in (False, True):
            print(
                f"profiling {path.name} optimise={optimise}", file=sys.stderr, flush=True
            )
            entries.append(profile_program(path, optimise, output / "reports"))

    searches = []
    for path in chosen:
        print(f"profiling exhaustive search for {path.name}", file=sys.stderr, flush=True)
        searches.extend(profile_search(path, output / "reports"))

    payload = {
        "phase": "profile",
        "search_profiles": searches,
        "command": " ".join(sys.argv),
        "provenance": provenance(verify_export_fresh()),
        "selection": "smallest, median and largest public program by operation count",
        "programs": [path.name for path in chosen],
        "caveat": (
            "a deterministic profiler perturbs wall-clock search behaviour; these "
            "times locate cost, they are not performance results"
        ),
        "profiles": entries,
    }
    write_json(output / "profile.json", payload)
    print(str(output / "profile.json"))
    return 0


def phase_final(arguments) -> int:
    output = Path(arguments.output).resolve()
    baseline = Path(arguments.baseline).resolve()
    if output.exists() and any(output.iterdir()) and not arguments.allow_existing:
        print(f"{output} already exists and is not empty", file=sys.stderr)
        return 2
    frozen_export = baseline / "snapshot" / "compiler_frozen.py"
    if not frozen_export.exists():
        print(f"missing frozen snapshot {frozen_export}", file=sys.stderr)
        return 2
    output.mkdir(parents=True, exist_ok=True)

    export_hash = verify_export_fresh()
    record = provenance(export_hash)
    record["frozen_export_sha256"] = digest(frozen_export)
    record["baseline_directory"] = str(baseline)
    baseline_provenance = json.loads((baseline / "provenance.json").read_text())
    record["baseline_source_sha256"] = baseline_provenance["source_sha256"]
    record["frozen_snapshot_matches_baseline"] = (
        digest(frozen_export) == baseline_provenance["frozen_export_sha256"]
    )
    write_json(output / "provenance.json", record)

    paths = public_paths()
    programs = [program_name_of(path) for path in paths]
    history = historical_metrics()

    started = time.monotonic()
    with Bench(frozen_export, EXPORT, arguments.timeout, arguments.seed) as bench:
        runs, failures, orders = bench.run(paths, ARMS, arguments.repeats, arguments.quiet)
    elapsed = time.monotonic() - started
    analysis = analyse(
        runs, failures, programs, ARMS, arguments.repeats, history, arguments.seed
    )

    extra: Optional[dict] = None
    if not arguments.skip_extra_corpus:
        corpus_directory = baseline / "extra_corpus"
        manifest = json.loads((baseline / "extra_corpus_manifest.json").read_text())
        integrity = verify_extra_corpus(corpus_directory, manifest)
        extra_paths = [corpus_directory / entry["file"] for entry in manifest["programs"]]
        extra_names = [entry["name"] for entry in manifest["programs"]]
        print(
            f"extra corpus: {len(extra_paths)} programs x {arguments.extra_repeats} "
            f"repetitions",
            file=sys.stderr,
            flush=True,
        )
        extra_started = time.monotonic()
        with Bench(frozen_export, EXPORT, arguments.timeout, arguments.seed) as bench:
            extra_runs, extra_failures, extra_orders = bench.run(
                extra_paths, ARMS, arguments.extra_repeats, arguments.quiet
            )
        extra_elapsed = time.monotonic() - extra_started
        extra_analysis = analyse(
            extra_runs,
            extra_failures,
            extra_names,
            ARMS,
            arguments.extra_repeats,
            {},
            arguments.seed,
            resamples=2000,
        )
        extra = {
            "manifest": manifest["size"],
            "integrity": integrity,
            "repetitions": arguments.extra_repeats,
            "elapsed_seconds": extra_elapsed,
            "arm_order": extra_orders,
            "analysis": extra_analysis,
            "score_distribution": extra_score_distribution(extra_runs, extra_names, manifest),
            "runs": extra_runs,
            "failures": extra_failures,
        }

    payload = {
        "phase": "final",
        "provenance": record,
        "command": " ".join(sys.argv),
        "seed": arguments.seed,
        "timeout_seconds": arguments.timeout,
        "elapsed_seconds": elapsed,
        "arm_order": orders,
        "analysis": analysis,
        "runs": runs,
        "failures": failures,
        "extra_corpus": extra,
    }
    write_json(output / "runs.json", payload)
    report_lines(payload, output / "FINAL_MEASUREMENTS.md")
    print(summarise(payload), file=sys.stderr)
    print(str(output / "runs.json"))
    ok = analysis["membership"]["passed"] and (
        extra is None or extra["analysis"]["membership"]["passed"]
    )
    return 0 if ok else 1


def extra_score_distribution(
    runs: Sequence[dict], programs: Sequence[str], manifest: dict
) -> dict:
    """Per-arm score distribution over the extra corpus, against serial."""

    serial = {
        entry["name"]: {
            "cycles": entry["serial_cycles"],
            "scratch": entry["serial_scratch"],
        }
        for entry in manifest["programs"]
    }
    out = {}
    for arm in ARMS:
        table = metric_table(runs, programs, arm)
        usable = [p for p in programs if len(table["cycles"][p]) == 1 and len(table["scratch"][p]) == 1]
        if not usable:
            out[arm] = {"programs": 0}
            continue
        per_program = []
        for program in usable:
            cycles = table["cycles"][program][0]
            scratch = table["scratch"][program][0]
            per_program.append(
                math.sqrt(
                    (serial[program]["cycles"] / cycles)
                    * (serial[program]["scratch"] / scratch)
                )
            )
        out[arm] = {
            "programs": len(usable),
            "varying_programs": table["varying_programs"],
            "combined_score_geomean": geomean(per_program),
            "min": min(per_program),
            "max": max(per_program),
            "median": statistics.median(per_program),
            "accepted_improvements": sum(
                run.get("optimiser", {}).get("accepted", 0)
                for run in runs
                if run["arm"] == arm
            ),
        }
    return out


def summarise(payload: dict) -> str:
    analysis = payload["analysis"]
    lines = [f"phase {payload['phase']}: {analysis['membership']['detail']}"]
    for label, entry in analysis["ratios"].items():
        interval = entry["paired_bootstrap_95"]
        target = (
            f" target {entry['target']}x {'MET' if entry['target_met'] else 'NOT MET'}"
            if "target" in entry
            else ""
        )
        lines.append(
            f"  {label}: geomean {entry['geometric_mean_of_per_program_medians']:.4f}x "
            f"(95% CI {interval['low']:.4f}-{interval['high']:.4f}), pooled median "
            f"{entry['pooled_median_ratio']:.4f}x{target}"
        )
    for arm, score in analysis["scores"].items():
        value = score.get("combined_score")
        lines.append(
            f"  score {arm}: {value:.16f}" if value is not None else
            f"  score {arm}: undefined ({score.get('note')})"
        )
    return "\n".join(lines)


def report_lines(payload: dict, path: Path) -> None:
    analysis = payload["analysis"]
    programs = analysis["programs"]
    medians = analysis["median_compile_seconds"]
    lines = [
        f"# Measured arms — {payload['phase']} phase",
        "",
        f"Command: `{payload['command']}`",
        "",
        f"Seed {payload['seed']}, {analysis['repetitions']} repetitions, "
        f"{len(payload['runs'])} rows, {len(payload['failures'])} failures, "
        f"{payload['elapsed_seconds']:.1f} s elapsed.",
        "",
        "## Median compile time per program (milliseconds)",
        "",
        "| Program | " + " | ".join(analysis["arms"]) + " |",
        "|---" * (len(analysis["arms"]) + 1) + "|",
    ]
    for program in programs:
        cells = [f"{1000 * medians[arm][program]:.4f}" for arm in analysis["arms"]]
        lines.append(f"| {program} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "## Aggregate ratios",
        "",
        "| Comparison | Geomean of per-program median ratios | 95% paired CI | "
        "Pooled median ratio | Slower programs |",
        "|---|---:|---|---:|---|",
    ]
    for label, entry in analysis["ratios"].items():
        interval = entry["paired_bootstrap_95"]
        losing = ", ".join(entry["programs_slower_than_baseline"]) or "none"
        lines.append(
            f"| {label} | {entry['geometric_mean_of_per_program_medians']:.4f}x | "
            f"{interval['low']:.4f}–{interval['high']:.4f} | "
            f"{entry['pooled_median_ratio']:.4f}x | {losing} |"
        )

    lines += ["", "## Combined scores recomputed from raw integers", ""]
    for arm, score in analysis["scores"].items():
        value = score.get("combined_score")
        lines.append(
            f"- `{arm}`: {value:.16f}" if value is not None
            else f"- `{arm}`: undefined — {score.get('note')}"
        )

    lines += ["", "## Bootstrap versus full-direct metrics", ""]
    for entry in analysis["bootstrap_vs_full"]:
        verdict = "holds" if entry["holds"] else "**FAILS**"
        lines.append(
            f"- `{entry['label']}`: the hypothesis that bootstrap metrics equal "
            f"full-direct metrics {verdict} over {entry['programs']} programs; "
            f"{len(entry['discrepancies'])} discrepancies."
        )
        for discrepancy in entry["discrepancies"]:
            lines.append(
                f"  - `{discrepancy['program']}`: bootstrap "
                f"{discrepancy['bootstrap']} against full {discrepancy['full']}"
            )

    lines += [
        "",
        "## Definitions and limits",
        "",
    ] + [f"- **{k}**: {v}" for k, v in analysis["statistic_definitions"].items()]
    lines += [
        "",
        "Raw rows, the retained arm order and full provenance are in `runs.json`.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("baseline", "profile", "final"))
    parser.add_argument("--worker", choices=("classical",))
    parser.add_argument("--program")
    parser.add_argument("--baseline")
    parser.add_argument("--output")
    parser.add_argument("--repeats", type=int, default=15)
    parser.add_argument("--extra-repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--allow-existing", action="store_true")
    parser.add_argument("--skip-extra-corpus", action="store_true")
    arguments = parser.parse_args(argv)

    if arguments.worker:
        print(json.dumps(classical_worker(arguments.program)))
        return 0
    if not arguments.phase:
        parser.error("--phase is required")
    if not arguments.output:
        parser.error("--output is required")
    if arguments.repeats < 1:
        parser.error("--repeats must be positive")
    if arguments.phase == "final" and not arguments.baseline:
        parser.error("--baseline is required for the final phase")

    if arguments.phase == "baseline":
        return phase_baseline(arguments)
    if arguments.phase == "profile":
        return phase_profile(arguments)
    return phase_final(arguments)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
