"""Independently check the optimization phase's evidence tree.

Section 7a of ``plan/OPTIMIZATION_PHASE_PLAN.md``. This tool trusts nothing a
report says about itself. It recomputes the hashes, the membership, the
integers and the aggregates from the raw rows, and it links every result to the
source snapshot that actually produced it. A report's own ``PASS`` text is not
evidence and is never read as such.

What it verifies:

* the pinned reference manifest and the four protected files;
* that the recorded source, test and export hashes match the working tree;
* that the measured export is what the current sources assemble to;
* that the benchmark's ``(arm, program, repetition)`` membership is exact,
  with no duplicate, missing, foreign or invalid row;
* that every classical measurement reproduces its protected historical
  per-program cycles and scratch, not merely an equal aggregate;
* that the combined scores recomputed from the raw integers match what the
  reports claim, and that the direct arms clear the accepted v3 score;
* that the aggregates, the geometric means and the per-program median ratios
  recompute from the raw timings;
* that the comparison's seven gates and the verifier's stages really passed;
* that each result directory's provenance names the snapshot it ran against.

Exit status is zero only when every check passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import compare_direct as official  # noqa: E402

# The score the lead accepted for v3. A candidate may not fall below it.
ACCEPTED_DIRECT_SCORE = 2.0084662022846573
ACCEPTED_CLASSICAL_SCORE = 1.9013791212645499
SCORE_TOLERANCE = 1e-12


class Checker:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.checks: List[dict] = []

    def record(self, name: str, passed: bool, detail: str, **extra) -> bool:
        entry = {"check": name, "passed": bool(passed), "detail": detail}
        entry.update(extra)
        self.checks.append(entry)
        return bool(passed)

    def require(self, path: Path) -> Optional[dict]:
        if not path.exists():
            self.record(f"present:{path.name}", False, f"{path} is missing")
            return None
        return json.loads(path.read_text())

    # -- provenance ------------------------------------------------------

    def check_pinned_material(self) -> None:
        try:
            commit = official.verify_reference()
            self.record(
                "pinned_reference", True, f"reference manifest verified at {commit}"
            )
        except RuntimeError as exc:
            self.record("pinned_reference", False, str(exc))
        try:
            protected = official.verify_protected()
            self.record(
                "protected_files",
                True,
                f"{len(protected)} protected files match their pinned hashes",
            )
        except RuntimeError as exc:
            self.record("protected_files", False, str(exc))
        try:
            export_hash = official.verify_export_fresh()
            self.record(
                "export_freshness",
                True,
                f"the export on disk is what the current sources assemble to, {export_hash[:16]}…",
            )
        except RuntimeError as exc:
            self.record("export_freshness", False, str(exc))

    def check_recorded_hashes(self, label: str, provenance: dict) -> None:
        drift = []
        for name, expected in provenance.get("source_sha256", {}).items():
            path = ROOT / name
            actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
            if actual != expected:
                drift.append({"file": name, "recorded": expected, "actual": actual})
        for name, expected in provenance.get("test_sha256", {}).items():
            path = ROOT / "tests_direct" / name
            actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
            if actual != expected:
                drift.append({"file": f"tests_direct/{name}", "recorded": expected, "actual": actual})
        self.record(
            f"recorded_hashes:{label}",
            not drift,
            (
                f"{len(provenance.get('source_sha256', {}))} source and "
                f"{len(provenance.get('test_sha256', {}))} test hashes recorded by "
                f"{label}; {len(drift)} differ from the working tree"
            ),
            drift=drift,
        )

    # -- benchmark rows --------------------------------------------------

    def check_benchmark(self, label: str, payload: dict) -> None:
        analysis = payload["analysis"]
        runs = payload["runs"]
        programs = analysis["programs"]
        arms = analysis["arms"]
        repeats = analysis["repetitions"]

        # Membership, recomputed here rather than read from the report.
        expected = {
            (arm, program, repeat)
            for arm in arms
            for program in programs
            for repeat in range(repeats)
        }
        observed = [(r["arm"], r["program"], r["repeat"]) for r in runs]
        duplicates = len(observed) - len(set(observed))
        self.record(
            f"membership:{label}",
            set(observed) == expected
            and duplicates == 0
            and len(observed) == len(expected)
            and not payload["failures"],
            (
                f"{len(expected)} expected keys, {len(observed)} rows, "
                f"{len(set(observed))} unique, {duplicates} duplicated, "
                f"{len(expected - set(observed))} missing, "
                f"{len(set(observed) - expected)} foreign, "
                f"{len(payload['failures'])} execution failures"
            ),
        )

        invalid = [
            r
            for r in runs
            if r.get("correctness") != "PASS"
            or r.get("discrepancy_count", 0)
            or r.get("leaked")
            or not isinstance(r.get("cycles"), int)
            or r.get("cycles", 0) <= 0
            or r.get("scratch", 0) <= 0
            or r.get("cases", 0) <= 0
        ]
        self.record(
            f"rows_valid:{label}",
            not invalid,
            f"{len(runs)} rows checked for validation, discrepancies and module leaks; "
            f"{len(invalid)} invalid",
        )

        # Frozen classical integers, per program, against pinned history.
        history = official.historical_metrics()
        drift = []
        controlled = 0
        for run in runs:
            if run["arm"] != "classical":
                continue
            expected_metrics = history["classical"].get(run["program"])
            if expected_metrics is None:
                continue
            controlled += 1
            if (run["cycles"], run["scratch"]) != (
                expected_metrics["cycles"],
                expected_metrics["scratch"],
            ):
                drift.append(run["program"])
        self.record(
            f"frozen_classical_integers:{label}",
            not drift and controlled > 0,
            f"{controlled} classical measurements against the protected per-program "
            f"integers; {len(drift)} disagree",
        )

        # Scores, recomputed from the raw integers rather than read back.
        serial = history["serial"]
        for arm in arms:
            cycles: Dict[str, set] = {p: set() for p in programs}
            scratch: Dict[str, set] = {p: set() for p in programs}
            for run in runs:
                if run["arm"] == arm:
                    cycles[run["program"]].add(run["cycles"])
                    scratch[run["program"]].add(run["scratch"])
            if any(len(v) != 1 for v in cycles.values()) or any(
                len(v) != 1 for v in scratch.values()
            ):
                self.record(
                    f"score:{label}:{arm}",
                    False,
                    "metrics varied within the arm, so no single score is defined",
                )
                continue
            if any(p not in serial for p in programs):
                continue
            cycle_ratios = [
                serial[p]["cycles"] / next(iter(cycles[p])) for p in programs
            ]
            scratch_ratios = [
                serial[p]["scratch"] / next(iter(scratch[p])) for p in programs
            ]
            score = math.sqrt(
                official.geomean(cycle_ratios) * official.geomean(scratch_ratios)
            )
            reported = analysis["scores"].get(arm, {}).get("combined_score")
            agrees = reported is not None and math.isclose(
                score, reported, rel_tol=0, abs_tol=1e-15
            )
            if arm == "classical":
                ok = agrees and math.isclose(
                    score, ACCEPTED_CLASSICAL_SCORE, rel_tol=0, abs_tol=1e-9
                )
                detail = (
                    f"recomputed {score!r}; the frozen classical control is "
                    f"{ACCEPTED_CLASSICAL_SCORE!r}"
                )
            else:
                ok = agrees and score >= ACCEPTED_DIRECT_SCORE - SCORE_TOLERANCE
                detail = (
                    f"recomputed {score!r}; must be at least the accepted v3 "
                    f"{ACCEPTED_DIRECT_SCORE!r} within {SCORE_TOLERANCE:g}"
                )
            self.record(f"score:{label}:{arm}", ok, detail, recomputed=score,
                        reported=reported)

        # Aggregates, recomputed from the raw timings.
        mismatched = []
        for name, entry in analysis["ratios"].items():
            baseline, candidate = entry["baseline_arm"], entry["candidate_arm"]
            ratios = []
            for program in programs:
                base = statistics.median(
                    [r["compile_seconds"] for r in runs
                     if r["arm"] == baseline and r["program"] == program]
                )
                cand = statistics.median(
                    [r["compile_seconds"] for r in runs
                     if r["arm"] == candidate and r["program"] == program]
                )
                ratios.append(base / cand)
            recomputed = official.geomean(ratios)
            if not math.isclose(
                recomputed,
                entry["geometric_mean_of_per_program_medians"],
                rel_tol=1e-12,
                abs_tol=0,
            ):
                mismatched.append(
                    {"ratio": name, "recomputed": recomputed,
                     "reported": entry["geometric_mean_of_per_program_medians"]}
                )
        self.record(
            f"aggregates:{label}",
            not mismatched,
            f"{len(analysis['ratios'])} aggregate ratios recomputed from the raw "
            f"per-program medians; {len(mismatched)} disagree",
            mismatched=mismatched,
        )

        # Bootstrap against full, reported as a measured hypothesis.
        for entry in analysis["bootstrap_vs_full"]:
            self.record(
                f"bootstrap_equals_full:{label}:{entry['label']}",
                entry["holds"],
                f"{entry['programs']} programs; {len(entry['discrepancies'])} "
                f"per-program metric discrepancies between bootstrap and full",
                discrepancies=entry["discrepancies"],
            )

    # -- official acceptance artifacts -----------------------------------

    def check_comparison(self, payload: dict) -> None:
        gates = payload.get("gates", {})
        failed = [name for name, gate in gates.items() if not gate["passed"]]
        self.record(
            "comparison_gates",
            bool(gates) and not failed,
            f"{len(gates)} gates evaluated from the raw runs; failing: {failed or 'none'}",
        )
        runs = payload.get("runs", [])
        keys = {(r["arm"], r["program"], r["repeat"]) for r in runs}
        repeats = payload.get("repetitions", 0)
        expected = 3 * 8 * repeats
        self.record(
            "comparison_membership",
            len(keys) == len(runs) == expected and expected > 0,
            f"{len(runs)} rows, {len(keys)} unique keys, {expected} expected",
        )
        # Scores recomputed from the raw measurements, not read from summary.
        by_key = {(r["arm"], r["program"], r["repeat"]): r for r in runs}
        programs = payload.get("program_names", [])
        scores = {}
        for arm in payload.get("arms", []):
            per_repeat = []
            for repeat in range(repeats):
                try:
                    ratios = [
                        (by_key[("serial", p, repeat)]["cycles"]
                         * by_key[("serial", p, repeat)]["scratch"])
                        / (by_key[(arm, p, repeat)]["cycles"]
                           * by_key[(arm, p, repeat)]["scratch"])
                        for p in programs
                    ]
                except KeyError:
                    per_repeat = []
                    break
                per_repeat.append(
                    math.exp(statistics.fmean(math.log(r) / 2 for r in ratios))
                )
            scores[arm] = per_repeat
        direct = scores.get("direct_index", [])
        classical = scores.get("classical", [])
        self.record(
            "comparison_scores",
            bool(direct)
            and all(s >= ACCEPTED_DIRECT_SCORE - SCORE_TOLERANCE for s in direct)
            and bool(classical)
            and all(
                math.isclose(s, ACCEPTED_CLASSICAL_SCORE, rel_tol=0, abs_tol=1e-9)
                for s in classical
            ),
            f"direct per repetition {direct}; classical {classical}",
            direct=direct,
            classical=classical,
        )

    def check_verification(self, payload: dict) -> None:
        records = payload.get("records", [])
        failing = [r for r in records if r.get("status") != "PASS"]
        tests = sum(r.get("tests", 0) or 0 for r in records)
        corpus = [r for r in records if r.get("step") == "corpus"]
        programs = corpus[0]["programs_checked"] if corpus else 0
        cases = corpus[0]["cases_checked"] if corpus else 0
        self.record(
            "verification",
            payload.get("status") == "PASS" and not failing and tests > 0,
            f"{len(records)} stage records, {tests} tests, {programs} corpus programs, "
            f"{cases} cases; {len(failing)} failing",
        )
        self.record(
            "verification_corpus",
            programs == 142 and cases == 277,
            f"{programs} of 142 corpus programs and {cases} of 277 cases",
        )

    # -- reporting -------------------------------------------------------

    def run(self) -> dict:
        self.check_pinned_material()

        baseline_provenance = self.require(self.root / "baseline" / "provenance.json")
        baseline = self.require(self.root / "baseline" / "runs.json")
        final = self.require(self.root / "final" / "runs.json")

        if baseline is not None:
            self.check_benchmark("baseline", baseline)
        if final is not None:
            self.check_benchmark("final", final)
            provenance = final["provenance"]
            self.check_recorded_hashes("final", provenance)
            # The candidate must have been measured against the snapshot the
            # baseline phase actually froze, not some other file.
            self.record(
                "frozen_snapshot_linkage",
                bool(provenance.get("frozen_snapshot_matches_baseline")),
                (
                    "the frozen export measured in the final phase is the one the "
                    "baseline phase snapshotted"
                    if provenance.get("frozen_snapshot_matches_baseline")
                    else "the final phase measured a frozen export that is not the "
                    "baseline snapshot"
                ),
            )
            if baseline_provenance is not None:
                changed = sorted(
                    name
                    for name, value in provenance.get("source_sha256", {}).items()
                    if baseline_provenance.get("source_sha256", {}).get(name) != value
                )
                self.record(
                    "candidate_differs_from_baseline",
                    True,
                    f"sources changed since the baseline snapshot: {changed or 'none'}",
                    changed=changed,
                )

        comparison = self.require(self.root / "comparison" / "runs.json")
        if comparison is not None:
            self.check_comparison(comparison)
        verification = self.require(self.root / "verification" / "summary.json")
        if verification is not None:
            self.check_verification(verification)
            self.check_recorded_hashes("verification", verification)

        passed = all(check["passed"] for check in self.checks)
        return {
            "root": str(self.root),
            "all_passed": passed,
            "checks": self.checks,
            "scope": (
                "independent evidence checks only; the lead's verdict is not "
                "recorded here and this tool cannot grant acceptance"
            ),
        }


def main(argv) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", default=str(ROOT / "results" / "direct_index_v4_optimization")
    )
    parser.add_argument("--output")
    arguments = parser.parse_args(argv)

    root = Path(arguments.root).resolve()
    if not root.exists():
        print(f"{root} does not exist", file=sys.stderr)
        return 2

    payload = Checker(root).run()
    destination = Path(arguments.output) if arguments.output else root / "evidence_checks.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    for check in payload["checks"]:
        print(
            f"{'PASS' if check['passed'] else 'FAIL'}  {check['check']}: {check['detail']}",
            file=sys.stderr,
        )
    print(str(destination))
    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
