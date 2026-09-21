"""Independently check an optimization-phase evidence tree.

Section 7a of ``plan/OPTIMIZATION_PHASE_PLAN.md``, rewritten after the lead
review of 2026-09-20 recorded in
``results/direct_index_v4_optimization/REVIEW.md`` (finding R3) and again after
the re-review in ``results/direct_index_v4_optimization_repair/REVIEW.md``
(findings F1 and F2).

This tool trusts **nothing** a report says about itself. In particular it does
not read a stored gate flag, a stored confidence interval, a stored score, a
stored snapshot-linkage boolean or a stored aggregate and call it verified. Each
of those is recomputed from the raw rows and the files on disk, and the run is
rejected when the recomputation disagrees.

The contract it checks against is fixed **here and in the pinned inputs**, never
taken from the report under examination. Arms come from the harness module,
programs from the pinned reference directory, repetition counts, corpus size,
verification stages and the bootstrap protocol from the plan. A report that
measured a reduced contract therefore fails rather than defining its own.

That last point was the substance of F1 and F2:

* F1 — the resample count and seed used to recompute a paired interval were
  read out of the interval being audited. An experiment run at one resample was
  therefore recomputed at one resample, agreed with itself, and passed. Both are
  now fixed here, a run declaring anything else is rejected before any interval
  is recomputed, and there is no longer a command-line option that can lower
  them, because an option must not be able to relax an acceptance check.
* F2 — the recorded verification was required only to carry a positive total
  test count and the corpus totals, so whole stages could be deleted without
  rejection. Exactly one record is now required for every declared stage and
  for each of the three acceptance steps, each with its own log, its own count
  and the artifacts behind its totals.

What it verifies:

* the pinned reference manifest and the four protected files;
* exact field and key coverage of every required report and manifest;
* that the recorded source, test, harness and checker hashes match the working
  tree, and that both exports hash to what is recorded;
* that the candidate export is what the current sources assemble to, and that
  the frozen export is byte-identical to the baseline snapshot — by hashing the
  files, not by reading a boolean;
* exact ``(arm, program, repetition)`` membership against the fixed contract,
  for the public suite and for every extra-corpus row;
* that every row is validated, has positive finite timings, checked cases, no
  discrepancy and no module leak;
* that every classical measurement reproduces its protected historical
  per-program cycles and scratch — which a product-preserving drift does not;
* that every paired interval declares the fixed protocol, and that the bounds,
  the aggregates and every target decision recompute from the raw rows under
  that protocol rather than under the report's;
* that each declared engineering target carries a complete declaration, so an
  omission cannot bypass the comparison;
* the extra corpus: every input present, re-hashed, and its score distribution
  recomputed;
* that the comparison's seven gates really passed, recomputed from raw rows;
* that the verification carries every declared stage exactly once, that each
  ran a positive number of tests consistent with its own log, and that the
  corpus, public-suite and CLI acceptance steps are present, complete and
  supported by the artifacts they reference.

Exit status is zero only when every check passes.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
from typing import Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import compare_direct as official  # noqa: E402
import benchmark_optimization as bench  # noqa: E402
import verify_direct as verifier  # noqa: E402

# --------------------------------------------------------------------------
# The fixed contract. None of this is read from the report being checked.
# --------------------------------------------------------------------------

EXPECTED_ARMS = tuple(bench.ARMS)
EXPECTED_REPEATS = 15
EXPECTED_EXTRA_REPEATS = 3
EXPECTED_EXTRA_SIZE = 100
EXPECTED_EXTRA_FAMILIES = 5
EXPECTED_PUBLIC_PROGRAMS = 8
EXPECTED_CORPUS_PROGRAMS = 142
EXPECTED_CORPUS_CASES = 277
EXPECTED_COMPARISON_REPEATS = 3

# The bootstrap protocol of section 1 of the plan. Fixed here, enforced against
# the report, and used for every recomputation. Not an argument, not a default,
# and not something the evidence under examination may choose.
EXPECTED_BOOTSTRAP_RESAMPLES = 10000
EXPECTED_BOOTSTRAP_SEED = 20260920

REQUIRED_INTERVAL_FIELDS = ("low", "high", "median", "resamples", "seed")
REQUIRED_TARGET_FIELDS = (
    "target",
    "criterion",
    "measured",
    "interval_low",
    "interval_high",
    "met",
)

# Every stage the verifier declares, plus the three acceptance steps. Written
# out here rather than derived, so that a stage silently dropped from the
# verifier is caught as readily as one dropped from a summary.
REQUIRED_TEST_STAGES = (
    "schema",
    "contract",
    "constraints",
    "construction",
    "optimizer",
    "independence",
    "export",
    "benchmark",
    "evidence",
)
REQUIRED_ACCEPTANCE_STEPS = ("corpus", "public_suite", "cli")
EXPECTED_PUBLIC_TESTS = 11

# The log stem each record's output was written under.
STAGE_LOG_STEMS = {"public_suite": "acceptance_public_suite"}
LOGGED_RECORDS = REQUIRED_TEST_STAGES + ("public_suite",)

RAN_PATTERN = re.compile(r"^Ran (\d+) tests? in", re.MULTILINE)

# Paired intervals are a pure, deterministic function of the rows and the fixed
# protocol. Several checker runs inside one process — the regression suite —
# ask for the same interval from the same rows; memoising the result changes no
# verdict and keeps that suite bounded.
_BOOTSTRAP_CACHE: Dict[str, dict] = {}

ACCEPTED_DIRECT_SCORE = 2.0084662022846573
ACCEPTED_CLASSICAL_SCORE = 1.9013791212645499
SCORE_TOLERANCE = 1e-12

# Scripts whose content the evidence depends on. The harness that produced the
# numbers and this checker itself are part of the evidence, not outside it.
REQUIRED_SCRIPTS = ("benchmark_optimization.py", "check_optimization_evidence.py")

REQUIRED_RUN_FIELDS = (
    "phase",
    "provenance",
    "command",
    "seed",
    "timeout_seconds",
    "elapsed_seconds",
    "arm_order",
    "analysis",
    "runs",
    "failures",
    "acceptance_gates",
    "performance_targets",
    "acceptance_claimed",
)

REQUIRED_PROVENANCE_FIELDS = (
    "git",
    "python",
    "platform",
    "reference_commit",
    "protected_sha256",
    "source_sha256",
    "test_sha256",
    "export_sha256",
    "export_lines",
)

REQUIRED_ROW_FIELDS = (
    "arm",
    "program",
    "repeat",
    "cycles",
    "scratch",
    "cases",
    "correctness",
    "compile_seconds",
    "import_seconds",
    "process_seconds",
    "discrepancy_count",
    "leaked",
)

REQUIRED_MANIFEST_FIELDS = (
    "seed",
    "per_family",
    "families",
    "size",
    "programs",
    "independence_note",
)

REQUIRED_MANIFEST_PROGRAM_FIELDS = (
    "index",
    "file",
    "name",
    "seed",
    "family",
    "operations",
    "cases",
    "serial_cycles",
    "serial_scratch",
    "sha256",
)


def sha256(path: Path) -> Optional[str]:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def finite_positive(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0


class Checker:
    def __init__(self, root: Path, baseline: Optional[Path] = None) -> None:
        self.root = root
        # An explicit baseline path lets a repair tree be checked against the
        # frozen snapshot and corpus of an earlier round, without overwriting
        # that round's evidence.
        self.baseline = baseline or (root / "baseline")
        self.external_baseline = self.baseline.resolve() != (root / "baseline").resolve()
        self.checks: List[dict] = []
        self.public_programs = self.pinned_programs()

    # -- plumbing --------------------------------------------------------

    def record(self, name: str, passed: bool, detail: str, **extra) -> bool:
        entry = {"check": name, "passed": bool(passed), "detail": detail}
        entry.update(extra)
        self.checks.append(entry)
        return bool(passed)

    def require(self, path: Path) -> Optional[dict]:
        if not path.exists():
            self.record(f"present:{path.name}", False, f"{path} is missing")
            return None
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            self.record(f"parse:{path.name}", False, f"{path} is not valid JSON: {exc}")
            return None

    def pinned_programs(self) -> List[str]:
        paths = sorted((official.REFERENCE / "programs").glob("*.json"))
        return [official._name_of(path) for path in paths]

    def fields(self, label: str, payload: dict, required: Sequence[str]) -> bool:
        missing = [name for name in required if name not in payload]
        return self.record(
            f"fields:{label}",
            not missing,
            f"{len(required)} required fields; missing {missing or 'none'}",
        )

    # -- pinned material -------------------------------------------------

    def check_pinned_material(self) -> None:
        try:
            commit = official.verify_reference()
            self.record("pinned_reference", True, f"reference manifest verified at {commit}")
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
            candidate_hash = official.verify_export_fresh()
            self.record(
                "candidate_export_assembly",
                True,
                f"the candidate export is what the current sources assemble to, "
                f"{candidate_hash[:16]}…",
            )
        except RuntimeError as exc:
            self.record("candidate_export_assembly", False, str(exc))
        self.record(
            "public_program_set",
            len(self.public_programs) == EXPECTED_PUBLIC_PROGRAMS
            and len(set(self.public_programs)) == EXPECTED_PUBLIC_PROGRAMS,
            f"{len(self.public_programs)} pinned public programs, "
            f"{EXPECTED_PUBLIC_PROGRAMS} expected",
        )

    # -- hashes ----------------------------------------------------------

    def check_recorded_hashes(self, label: str, provenance: dict) -> None:
        """Every recorded hash must match the file on disk, and cover it."""

        sources = provenance.get("source_sha256") or {}
        tests = provenance.get("test_sha256") or {}

        required_sources = set(bench.SOURCES) | set(REQUIRED_SCRIPTS)
        required_tests = {path.name for path in sorted((ROOT / "tests_direct").glob("*.py"))}
        missing_sources = sorted(required_sources - set(sources))
        missing_tests = sorted(required_tests - set(tests))

        drift = []
        for name, expected in sources.items():
            actual = sha256(ROOT / name)
            if actual != expected:
                drift.append({"file": name, "recorded": expected, "actual": actual})
        for name, expected in tests.items():
            actual = sha256(ROOT / "tests_direct" / name)
            if actual != expected:
                drift.append(
                    {"file": f"tests_direct/{name}", "recorded": expected, "actual": actual}
                )

        self.record(
            f"recorded_hashes:{label}",
            not drift and not missing_sources and not missing_tests and bool(sources),
            (
                f"{len(sources)} source and {len(tests)} test hashes recorded; "
                f"{len(drift)} differ from the working tree; missing sources "
                f"{missing_sources or 'none'}; missing tests {missing_tests or 'none'}"
            ),
            drift=drift,
        )

    def check_exports(self, label: str, provenance: dict) -> None:
        """Hash both exports. A stored linkage boolean proves nothing."""

        candidate = sha256(official.EXPORT)
        self.record(
            f"candidate_export_hash:{label}",
            candidate is not None and provenance.get("export_sha256") == candidate,
            f"recorded {str(provenance.get('export_sha256'))[:16]}…, on disk "
            f"{str(candidate)[:16]}…",
        )

        snapshot = self.baseline / "snapshot" / "compiler_frozen.py"
        frozen = sha256(snapshot)
        recorded = provenance.get("frozen_export_sha256")
        self.record(
            f"frozen_export_hash:{label}",
            frozen is not None and recorded == frozen,
            f"recorded {str(recorded)[:16]}…, snapshot on disk {str(frozen)[:16]}…",
        )

        baseline_provenance = self.require(self.baseline / "provenance.json")
        if baseline_provenance is not None:
            expected = baseline_provenance.get("frozen_export_sha256")
            self.record(
                f"frozen_snapshot_linkage:{label}",
                frozen is not None and expected == frozen,
                (
                    f"the frozen export measured by {label} hashes to "
                    f"{str(frozen)[:16]}…; the baseline phase snapshotted "
                    f"{str(expected)[:16]}…"
                ),
            )

    # -- rows ------------------------------------------------------------

    def check_rows(
        self,
        label: str,
        runs: Sequence[dict],
        failures: Sequence[dict],
        programs: Sequence[str],
        repeats: int,
    ) -> bool:
        expected = {
            (arm, program, repeat)
            for arm in EXPECTED_ARMS
            for program in programs
            for repeat in range(repeats)
        }
        observed = [(r.get("arm"), r.get("program"), r.get("repeat")) for r in runs]
        duplicates = len(observed) - len(set(observed))
        missing = expected - set(observed)
        foreign = set(observed) - expected
        ok_membership = (
            set(observed) == expected
            and duplicates == 0
            and len(observed) == len(expected)
            and not failures
            and len(expected) > 0
        )
        self.record(
            f"membership:{label}",
            ok_membership,
            (
                f"contract requires {len(expected)} keys over {len(EXPECTED_ARMS)} arms, "
                f"{len(programs)} programs and {repeats} repetitions; observed "
                f"{len(observed)} rows, {len(set(observed))} unique, {duplicates} "
                f"duplicated, {len(missing)} missing, {len(foreign)} foreign, "
                f"{len(failures)} execution failures"
            ),
        )

        bad_fields = []
        invalid = []
        for run in runs:
            absent = [name for name in REQUIRED_ROW_FIELDS if name not in run]
            if absent:
                bad_fields.append({"row": observed[runs.index(run)], "missing": absent})
                continue
            problems = []
            if not isinstance(run["cycles"], int) or run["cycles"] <= 0:
                problems.append("cycles")
            if not isinstance(run["scratch"], int) or run["scratch"] <= 0:
                problems.append("scratch")
            if run["correctness"] != "PASS":
                problems.append("correctness")
            if not isinstance(run["cases"], int) or run["cases"] <= 0:
                problems.append("cases")
            if run["discrepancy_count"]:
                problems.append("discrepancy")
            if run["leaked"]:
                problems.append("module leak")
            for timing in ("compile_seconds", "import_seconds", "process_seconds"):
                if not finite_positive(run[timing]):
                    problems.append(timing)
            if problems:
                invalid.append({"arm": run["arm"], "program": run["program"], "problems": problems})
        self.record(
            f"rows_valid:{label}",
            not invalid and not bad_fields,
            (
                f"{len(runs)} rows checked for required fields, validation, positive "
                f"finite timings, discrepancies and module leaks; {len(invalid)} "
                f"invalid, {len(bad_fields)} with missing fields"
            ),
            invalid=invalid[:20],
        )
        return ok_membership and not invalid and not bad_fields

    # -- the bootstrap protocol ------------------------------------------

    def bootstrap(self, runs: Sequence[dict], programs: Sequence[str],
                  baseline_arm: str, candidate_arm: str, repeats: int) -> dict:
        """Recompute a paired interval under the **fixed** protocol.

        The count and the seed are this module's constants. Reading them from
        the interval under audit, as this did before F1, made the check
        self-confirming: a one-resample experiment was recomputed at one
        resample and agreed with itself.
        """

        key = hashlib.sha256(
            json.dumps(
                [
                    [
                        [run.get("arm"), run.get("program"), run.get("repeat"),
                         run.get("compile_seconds")]
                        for run in runs
                    ],
                    list(programs),
                    baseline_arm,
                    candidate_arm,
                    repeats,
                ],
                sort_keys=True,
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        cached = _BOOTSTRAP_CACHE.get(key)
        if cached is None:
            cached = bench.paired_bootstrap(
                runs, programs, baseline_arm, candidate_arm, repeats,
                seed=EXPECTED_BOOTSTRAP_SEED,
                resamples=EXPECTED_BOOTSTRAP_RESAMPLES,
            )
            _BOOTSTRAP_CACHE[key] = cached
        return cached

    def check_bootstrap_protocol(self, label: str, payload: dict) -> None:
        """The declared protocol must be the contract's, in every place."""

        problems: List[dict] = []
        if bench.BOOTSTRAP_RESAMPLES != EXPECTED_BOOTSTRAP_RESAMPLES:
            problems.append(
                {"where": "harness", "resamples": bench.BOOTSTRAP_RESAMPLES}
            )
        if bench.DEFAULT_SEED != EXPECTED_BOOTSTRAP_SEED:
            problems.append({"where": "harness", "seed": bench.DEFAULT_SEED})
        run_seed = payload.get("seed")
        if run_seed != EXPECTED_BOOTSTRAP_SEED:
            problems.append({"where": "report", "seed": run_seed})

        ratios = payload.get("analysis", {}).get("ratios", {})
        for name, _, _ in bench.RATIOS:
            entry = ratios.get(name)
            if not isinstance(entry, dict):
                problems.append({"ratio": name, "error": "absent from the report"})
                continue
            interval = entry.get("paired_bootstrap_95")
            if not isinstance(interval, dict):
                problems.append({"ratio": name, "error": "no paired interval"})
                continue
            absent = [f for f in REQUIRED_INTERVAL_FIELDS if f not in interval]
            if absent:
                problems.append({"ratio": name, "missing": absent})
                continue
            if interval["resamples"] != EXPECTED_BOOTSTRAP_RESAMPLES:
                problems.append({"ratio": name, "resamples": interval["resamples"]})
            if interval["seed"] != EXPECTED_BOOTSTRAP_SEED:
                problems.append({"ratio": name, "seed": interval["seed"]})
            elif interval["seed"] != run_seed:
                problems.append(
                    {"ratio": name, "error": "interval seed disagrees with the run seed"}
                )

        self.record(
            f"bootstrap_protocol:{label}",
            not problems,
            (
                f"the enforced protocol is {EXPECTED_BOOTSTRAP_RESAMPLES} paired "
                f"resamples at seed {EXPECTED_BOOTSTRAP_SEED}, fixed in this checker; "
                f"{len(bench.RATIOS)} contract ratios and the run seed were checked "
                f"against it; {len(problems)} declarations disagree"
            ),
            problems=problems[:10],
        )

    # -- recomputed statistics -------------------------------------------

    def metric_sets(self, runs: Sequence[dict], programs: Sequence[str], arm: str):
        cycles: Dict[str, set] = {p: set() for p in programs}
        scratch: Dict[str, set] = {p: set() for p in programs}
        for run in runs:
            if run["arm"] == arm and run["program"] in cycles:
                cycles[run["program"]].add(run["cycles"])
                scratch[run["program"]].add(run["scratch"])
        return cycles, scratch

    def check_frozen_integers(self, label: str, runs: Sequence[dict]) -> None:
        history = official.historical_metrics()
        drift = []
        controlled = 0
        for run in runs:
            if run["arm"] != "classical":
                continue
            expected = history["classical"].get(run["program"])
            if expected is None:
                continue
            controlled += 1
            if (run["cycles"], run["scratch"]) != (expected["cycles"], expected["scratch"]):
                drift.append(
                    {
                        "program": run["program"],
                        "repeat": run["repeat"],
                        "expected": expected,
                        "observed": {"cycles": run["cycles"], "scratch": run["scratch"]},
                    }
                )
        self.record(
            f"frozen_classical_integers:{label}",
            not drift and controlled > 0,
            (
                f"{controlled} classical measurements recomputed against the protected "
                f"per-program integers; {len(drift)} disagree"
            ),
            drift=drift[:20],
        )

    def check_scores(self, label: str, runs: Sequence[dict], analysis: dict,
                     programs: Sequence[str]) -> None:
        serial = official.historical_metrics()["serial"]
        for arm in EXPECTED_ARMS:
            cycles, scratch = self.metric_sets(runs, programs, arm)
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
            cycle_ratios = [serial[p]["cycles"] / next(iter(cycles[p])) for p in programs]
            scratch_ratios = [serial[p]["scratch"] / next(iter(scratch[p])) for p in programs]
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
                floor = ACCEPTED_CLASSICAL_SCORE
            else:
                ok = agrees and score >= ACCEPTED_DIRECT_SCORE - SCORE_TOLERANCE
                floor = ACCEPTED_DIRECT_SCORE
            self.record(
                f"score:{label}:{arm}",
                ok,
                f"recomputed {score!r}; report says {reported!r}; floor {floor!r}",
                recomputed=score,
                reported=reported,
            )

    def check_products_and_bootstrap(self, label: str, runs: Sequence[dict],
                                     programs: Sequence[str]) -> None:
        """The per-program gates of R2, recomputed rather than read."""

        regressions = []
        compared = 0
        for mode in ("bootstrap", "full"):
            fc, fs = self.metric_sets(runs, programs, f"frozen_{mode}")
            cc, cs = self.metric_sets(runs, programs, f"candidate_{mode}")
            for program in programs:
                if not (fc[program] and fs[program] and cc[program] and cs[program]):
                    continue
                compared += 1
                if max(cc[program]) * max(cs[program]) > max(fc[program]) * max(fs[program]):
                    regressions.append({"mode": mode, "program": program})
        self.record(
            f"per_program_product_nonregression:{label}",
            not regressions and compared > 0,
            f"{compared} per-program products recomputed; {len(regressions)} regressed",
            regressions=regressions,
        )

        fc, fs = self.metric_sets(runs, programs, "frozen_bootstrap")
        cc, cs = self.metric_sets(runs, programs, "candidate_bootstrap")
        mismatched = [p for p in programs if fc[p] != cc[p] or fs[p] != cs[p]]
        self.record(
            f"bootstrap_metrics_identical:{label}",
            not mismatched and bool(programs),
            f"{len(programs)} programs recomputed; {len(mismatched)} differ between "
            f"the frozen and candidate bootstrap arms",
            mismatched=mismatched,
        )

    def check_aggregates_and_intervals(self, label: str, payload: dict,
                                       programs: Sequence[str],
                                       repeats: int) -> None:
        analysis = payload["analysis"]
        runs = payload["runs"]
        mismatched = []
        interval_mismatched = []
        target_mismatched = []
        recomputed_targets: Dict[str, bool] = {}
        recomputed_measured: Dict[str, float] = {}
        recomputed_bounds: Dict[str, dict] = {}

        expected_ratios = {name for name, _, _ in bench.RATIOS}
        reported_ratios = set(analysis.get("ratios", {}))
        self.record(
            f"ratio_coverage:{label}",
            expected_ratios <= reported_ratios,
            f"{len(expected_ratios)} contract ratios; missing "
            f"{sorted(expected_ratios - reported_ratios) or 'none'}",
        )

        for name, baseline_arm, candidate_arm in bench.RATIOS:
            entry = analysis.get("ratios", {}).get(name)
            if entry is None:
                continue
            ratios = []
            for program in programs:
                base = [r["compile_seconds"] for r in runs
                        if r["arm"] == baseline_arm and r["program"] == program]
                cand = [r["compile_seconds"] for r in runs
                        if r["arm"] == candidate_arm and r["program"] == program]
                if not base or not cand:
                    ratios = []
                    break
                ratios.append(statistics.median(base) / statistics.median(cand))
            if not ratios:
                continue
            recomputed = official.geomean(ratios)
            if not math.isclose(
                recomputed, entry["geometric_mean_of_per_program_medians"],
                rel_tol=1e-12, abs_tol=0,
            ):
                mismatched.append({"ratio": name, "recomputed": recomputed,
                                   "reported": entry["geometric_mean_of_per_program_medians"]})

            # The interval is recomputed from the raw timings under the fixed
            # protocol — this checker's resample count and seed, never the
            # report's. A forged interval cannot survive this, and neither can
            # an honestly computed one from a weakened experiment.
            reported_interval = entry.get("paired_bootstrap_95") or {}
            interval = self.bootstrap(
                runs, programs, baseline_arm, candidate_arm, repeats
            )
            recomputed_bounds[name] = interval
            for bound in ("low", "high"):
                if not math.isclose(
                    interval[bound], reported_interval.get(bound, float("nan")),
                    rel_tol=1e-9, abs_tol=0,
                ):
                    interval_mismatched.append(
                        {"ratio": name, "bound": bound,
                         "recomputed": interval[bound],
                         "reported": reported_interval.get(bound)}
                    )

            if name in bench.TARGETS:
                target = bench.TARGETS[name]
                met = bool(recomputed >= target and interval["low"] > 1.0)
                recomputed_targets[name] = met
                recomputed_measured[name] = recomputed
                if met != bool(entry.get("target_met")):
                    target_mismatched.append(
                        {"ratio": name, "recomputed_met": met,
                         "reported_met": entry.get("target_met")}
                    )
                if entry.get("target") != target:
                    target_mismatched.append(
                        {"ratio": name, "declared_target": entry.get("target"),
                         "contract_target": target, "where": "analysis.ratios"}
                    )

        # Every declared target must carry a complete declaration. Before F1 an
        # omitted or truncated entry was simply skipped, so leaving a target out
        # of the report was enough to avoid being compared against it.
        reported_targets = payload.get("performance_targets")
        if not isinstance(reported_targets, dict):
            target_mismatched.append({"error": "no performance_targets section"})
            reported_targets = {}
        for name, target in bench.TARGETS.items():
            reported = reported_targets.get(name)
            if not isinstance(reported, dict):
                target_mismatched.append(
                    {"ratio": name, "error": "no performance_targets entry"}
                )
                continue
            absent = [f for f in REQUIRED_TARGET_FIELDS if f not in reported]
            if absent:
                target_mismatched.append({"ratio": name, "missing": absent})
                continue
            if reported["target"] != target:
                target_mismatched.append(
                    {"ratio": name, "declared_target": reported["target"],
                     "contract_target": target, "where": "performance_targets"}
                )
            if name not in recomputed_targets:
                target_mismatched.append(
                    {"ratio": name,
                     "error": "no decision could be recomputed for this target"}
                )
                continue
            if bool(reported["met"]) != recomputed_targets[name]:
                target_mismatched.append(
                    {"ratio": name, "recomputed_met": recomputed_targets[name],
                     "reported_met": reported["met"], "where": "performance_targets"}
                )
            if not math.isclose(
                reported["measured"], recomputed_measured[name],
                rel_tol=1e-12, abs_tol=0,
            ):
                target_mismatched.append(
                    {"ratio": name, "recomputed_measured": recomputed_measured[name],
                     "reported_measured": reported["measured"]}
                )
            for bound, field in (("low", "interval_low"), ("high", "interval_high")):
                if not math.isclose(
                    reported[field], recomputed_bounds[name][bound],
                    rel_tol=1e-9, abs_tol=0,
                ):
                    target_mismatched.append(
                        {"ratio": name, "bound": field,
                         "recomputed": recomputed_bounds[name][bound],
                         "reported": reported[field]}
                    )
        invented = sorted(set(reported_targets) - set(bench.TARGETS))
        if invented:
            target_mismatched.append(
                {"error": "targets declared outside the contract", "names": invented}
            )

        self.record(
            f"aggregates:{label}", not mismatched,
            f"{len(bench.RATIOS)} aggregate ratios recomputed from raw per-program "
            f"medians; {len(mismatched)} disagree", mismatched=mismatched,
        )
        self.record(
            f"confidence_intervals:{label}", not interval_mismatched,
            f"paired intervals recomputed from raw timings under the enforced "
            f"protocol, {EXPECTED_BOOTSTRAP_RESAMPLES} resamples at seed "
            f"{EXPECTED_BOOTSTRAP_SEED}; {len(interval_mismatched)} bounds disagree",
            mismatched=interval_mismatched[:10],
        )
        self.record(
            f"target_decisions:{label}", not target_mismatched,
            f"{len(bench.TARGETS)} contract targets recomputed and their "
            f"declarations checked for completeness; "
            f"{len(target_mismatched)} disagree", mismatched=target_mismatched,
        )

    def check_gates_recomputed(self, label: str, payload: dict, phase: str,
                               extra_present: bool) -> None:
        """Recompute the mandatory gates rather than trusting stored flags."""

        recomputed = bench.acceptance_gates(payload["analysis"], phase, extra_present)
        stored = payload.get("acceptance_gates", {})
        disagreements = [
            name for name, gate in recomputed.items()
            if bool(stored.get(name, {}).get("passed")) != bool(gate["passed"])
        ]
        self.record(
            f"gate_flags_recomputed:{label}",
            not disagreements and bool(stored),
            f"{len(recomputed)} mandatory gates recomputed from the analysis; "
            f"{len(disagreements)} stored flags disagree: {disagreements or 'none'}",
        )
        self.record(
            f"mandatory_gates:{label}",
            bool(recomputed["all_passed"]["passed"]),
            "; ".join(
                f"{name}={'PASS' if gate['passed'] else 'FAIL'}"
                for name, gate in recomputed.items() if name != "all_passed"
            ),
        )
        self.record(
            f"acceptance_claimed:{label}",
            bool(payload.get("acceptance_claimed")),
            "the run is labelled acceptance evidence"
            if payload.get("acceptance_claimed")
            else "the run is labelled DIAGNOSTIC and cannot support acceptance",
        )

    # -- extra corpus ----------------------------------------------------

    def check_extra_corpus(self, label: str, payload: dict) -> None:
        extra = payload.get("extra_corpus")
        if not extra:
            self.record(
                f"extra_corpus:{label}", False,
                "the frozen evaluation corpus is absent from this run",
            )
            return

        manifest_path = self.baseline / "extra_corpus_manifest.json"
        manifest = self.require(manifest_path)
        if manifest is None:
            return
        if not self.fields(f"extra_manifest:{label}", manifest, REQUIRED_MANIFEST_FIELDS):
            return

        self.record(
            f"extra_corpus_contract:{label}",
            manifest["size"] == EXPECTED_EXTRA_SIZE
            and len(manifest["programs"]) == EXPECTED_EXTRA_SIZE
            and manifest["per_family"] == EXPECTED_EXTRA_SIZE // EXPECTED_EXTRA_FAMILIES
            and len(manifest["families"]) == EXPECTED_EXTRA_FAMILIES
            and manifest["seed"] == bench.EXTRA_CORPUS_SEED,
            (
                f"manifest declares {manifest['size']} programs, "
                f"{manifest['per_family']} per family over "
                f"{len(manifest['families'])} families at seed {manifest['seed']}; "
                f"contract requires {EXPECTED_EXTRA_SIZE}, "
                f"{EXPECTED_EXTRA_SIZE // EXPECTED_EXTRA_FAMILIES}, "
                f"{EXPECTED_EXTRA_FAMILIES}, {bench.EXTRA_CORPUS_SEED}"
            ),
        )

        # Every input re-hashed from disk.
        from tests_direct import generate_programs as gp

        directory = self.baseline / "extra_corpus"
        bad = []
        per_family: Dict[str, int] = {}
        for entry in manifest["programs"]:
            absent = [f for f in REQUIRED_MANIFEST_PROGRAM_FIELDS if f not in entry]
            if absent:
                bad.append({"entry": entry.get("file"), "missing": absent})
                continue
            per_family[entry["family"]] = per_family.get(entry["family"], 0) + 1
            path = directory / entry["file"]
            if not path.exists():
                bad.append({"file": entry["file"], "error": "missing"})
                continue
            if gp.program_digest(json.loads(path.read_text())) != entry["sha256"]:
                bad.append({"file": entry["file"], "error": "content hash changed"})
        self.record(
            f"extra_corpus_inputs:{label}",
            not bad
            and len(manifest["programs"]) == EXPECTED_EXTRA_SIZE
            and all(count == EXPECTED_EXTRA_SIZE // EXPECTED_EXTRA_FAMILIES
                    for count in per_family.values()),
            f"{len(manifest['programs'])} corpus inputs re-hashed from disk; "
            f"{len(bad)} missing or altered; per family {per_family}",
            bad=bad[:10],
        )

        names = [entry["name"] for entry in manifest["programs"]]
        self.check_rows(
            f"extra:{label}", extra.get("runs", []), extra.get("failures", []),
            names, EXPECTED_EXTRA_REPEATS,
        )

        cases_expected = {entry["name"]: entry["cases"] for entry in manifest["programs"]}
        wrong_cases = [
            run["program"] for run in extra.get("runs", [])
            if run.get("cases") != cases_expected.get(run.get("program"))
        ]
        self.record(
            f"extra_corpus_cases:{label}", not wrong_cases,
            f"{len(extra.get('runs', []))} corpus rows checked against the manifest's "
            f"declared case counts; {len(wrong_cases)} disagree",
        )

        # Score distribution recomputed from the manifest's own serial integers.
        serial = {
            entry["name"]: (entry["serial_cycles"], entry["serial_scratch"])
            for entry in manifest["programs"]
        }
        reported = extra.get("score_distribution", {})
        mismatched = []
        for arm in EXPECTED_ARMS:
            cycles, scratch = self.metric_sets(extra.get("runs", []), names, arm)
            usable = [n for n in names if len(cycles[n]) == 1 and len(scratch[n]) == 1]
            if not usable:
                continue
            scores = [
                math.sqrt(
                    (serial[n][0] / next(iter(cycles[n])))
                    * (serial[n][1] / next(iter(scratch[n])))
                )
                for n in usable
            ]
            recomputed = official.geomean(scores)
            claimed = reported.get(arm, {}).get("combined_score_geomean")
            if claimed is None or not math.isclose(
                recomputed, claimed, rel_tol=1e-12, abs_tol=0
            ):
                mismatched.append({"arm": arm, "recomputed": recomputed, "reported": claimed})
        self.record(
            f"extra_corpus_scores:{label}", not mismatched,
            f"{len(EXPECTED_ARMS)} corpus score distributions recomputed from the "
            f"manifest's serial integers; {len(mismatched)} disagree",
            mismatched=mismatched,
        )

    # -- official acceptance artifacts -----------------------------------

    def check_comparison(self, payload: dict) -> None:
        runs = payload.get("runs", [])
        repeats = payload.get("repetitions", 0)
        expected_keys = {
            (arm, program, repeat)
            for arm in official.ARMS
            for program in self.public_programs
            for repeat in range(EXPECTED_COMPARISON_REPEATS)
        }
        keys = [(r["arm"], r["program"], r["repeat"]) for r in runs]
        self.record(
            "comparison_membership",
            set(keys) == expected_keys
            and len(keys) == len(expected_keys)
            and repeats == EXPECTED_COMPARISON_REPEATS,
            f"{len(runs)} rows, {len(set(keys))} unique, {len(expected_keys)} required "
            f"by the fixed contract at {EXPECTED_COMPARISON_REPEATS} repetitions",
        )

        # Gates recomputed from the raw rows, not read from stored flags.
        recomputed = official.evaluate_gates(payload, EXPECTED_COMPARISON_REPEATS)
        failing = [n for n, g in recomputed.items() if not g["passed"]]
        stored = payload.get("gates", {})
        disagreeing = [
            n for n, g in recomputed.items()
            if bool(stored.get(n, {}).get("passed")) != bool(g["passed"])
        ]
        self.record(
            "comparison_gates",
            not failing and not disagreeing and bool(recomputed),
            f"{len(recomputed)} gates recomputed from the raw runs; failing "
            f"{failing or 'none'}; stored flags disagreeing {disagreeing or 'none'}",
        )

        by_key = {(r["arm"], r["program"], r["repeat"]): r for r in runs}
        scores: Dict[str, List[float]] = {}
        for arm in official.ARMS:
            per_repeat = []
            for repeat in range(EXPECTED_COMPARISON_REPEATS):
                try:
                    ratios = [
                        (by_key[("serial", p, repeat)]["cycles"]
                         * by_key[("serial", p, repeat)]["scratch"])
                        / (by_key[(arm, p, repeat)]["cycles"]
                           * by_key[(arm, p, repeat)]["scratch"])
                        for p in self.public_programs
                    ]
                except KeyError:
                    per_repeat = []
                    break
                per_repeat.append(math.exp(statistics.fmean(math.log(r) / 2 for r in ratios)))
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
            direct=direct, classical=classical,
        )

    def check_verification(self, payload: dict) -> None:
        """The whole verification contract, stage by stage.

        Before F2 this required a positive *total* test count and the corpus
        totals, so a summary holding only ``schema`` and ``corpus`` passed. What
        is required now is one record per declared stage and per acceptance
        step, each consistent with its own log and with the artifacts its totals
        are drawn from.
        """

        directory = self.root / "verification"
        records = payload.get("records", [])
        labels = [record.get("step") or record.get("stage") for record in records]
        required = list(REQUIRED_TEST_STAGES) + list(REQUIRED_ACCEPTANCE_STEPS)

        self.record(
            "verification_stage_contract",
            tuple(verifier.TEST_STAGES) == REQUIRED_TEST_STAGES
            and verifier.EXPECTED_PUBLIC_TESTS == EXPECTED_PUBLIC_TESTS,
            (
                f"the verifier declares {len(verifier.TEST_STAGES)} test stages and "
                f"{verifier.EXPECTED_PUBLIC_TESTS} public tests; this checker "
                f"requires {len(REQUIRED_TEST_STAGES)} named stages and "
                f"{EXPECTED_PUBLIC_TESTS}"
            ),
        )

        counts = Counter(labels)
        missing = [name for name in required if counts.get(name, 0) != 1]
        duplicated = sorted(name for name, count in counts.items() if count > 1)
        unexpected = sorted(set(labels) - set(required))
        self.record(
            "verification_stages",
            not missing and not duplicated and not unexpected,
            (
                f"{len(required)} records required, one for each of "
                f"{len(REQUIRED_TEST_STAGES)} test stages and the acceptance steps "
                f"{REQUIRED_ACCEPTANCE_STEPS}; {len(records)} present; absent or not "
                f"exactly once {missing or 'none'}; duplicated {duplicated or 'none'}; "
                f"outside the contract {unexpected or 'none'}"
            ),
        )

        first: Dict[str, dict] = {}
        for record, label in zip(records, labels):
            first.setdefault(label, record)

        bad_status = []
        for record, label in zip(records, labels):
            if record.get("status") != "PASS":
                bad_status.append({"record": label, "status": record.get("status")})
            if record.get("exit_code") not in (None, 0):
                bad_status.append({"record": label, "exit_code": record["exit_code"]})
            if record.get("timed_out"):
                bad_status.append({"record": label, "error": "timed out"})
        stages_run = set(payload.get("stages_run") or [])
        expected_run = set(REQUIRED_TEST_STAGES) | {"acceptance"}
        self.record(
            "verification_status",
            payload.get("status") == "PASS"
            and not payload.get("failures")
            and not bad_status
            and stages_run == expected_run,
            (
                f"summary status {payload.get('status')!r} with "
                f"{len(payload.get('failures') or [])} recorded failures; "
                f"{len(bad_status)} records not passing cleanly; stages run "
                f"{sorted(stages_run)} against {sorted(expected_run)}"
            ),
            bad_status=bad_status[:10],
        )

        zero = []
        for stage in REQUIRED_TEST_STAGES:
            record = first.get(stage)
            if record is None:
                zero.append({"stage": stage, "error": "record absent"})
                continue
            count = record.get("tests")
            if not isinstance(count, int) or count <= 0:
                zero.append({"stage": stage, "tests": count})
        self.record(
            "verification_test_counts",
            not zero,
            (
                f"{len(REQUIRED_TEST_STAGES)} test stages must each have run a "
                f"positive number of tests; {len(zero)} did not"
            ),
            zero=zero,
        )

        log_problems = []
        for label in LOGGED_RECORDS:
            record = first.get(label)
            if record is None:
                log_problems.append({"record": label, "error": "record absent"})
                continue
            log = directory / "logs" / f"{STAGE_LOG_STEMS.get(label, label)}.stderr.txt"
            if not log.exists():
                log_problems.append({"record": label, "error": f"{log.name} is missing"})
                continue
            text = log.read_text(encoding="utf-8", errors="replace")
            match = RAN_PATTERN.search(text)
            in_log = int(match.group(1)) if match else None
            if in_log != record.get("tests"):
                log_problems.append(
                    {"record": label, "log_says": in_log,
                     "summary_says": record.get("tests")}
                )
                continue
            tail = record.get("stderr_tail")
            if tail and not text.endswith(tail):
                log_problems.append(
                    {"record": label,
                     "error": "the recorded tail is not this log's tail"}
                )
        self.record(
            "verification_logs",
            not log_problems,
            (
                f"{len(LOGGED_RECORDS)} records checked against the log each one "
                f"names, on the reported test count and the recorded tail; "
                f"{len(log_problems)} disagree"
            ),
            problems=log_problems[:10],
        )

        public = first.get("public_suite")
        self.record(
            "verification_public_suite",
            public is not None
            and public.get("tests") == EXPECTED_PUBLIC_TESTS
            and public.get("expected_tests") == EXPECTED_PUBLIC_TESTS
            and public.get("exit_code") == 0
            and not public.get("timed_out")
            and public.get("status") == "PASS",
            (
                f"the frozen public suite must run exactly {EXPECTED_PUBLIC_TESTS} "
                f"tests; the record reports {(public or {}).get('tests')} against a "
                f"declared expectation of {(public or {}).get('expected_tests')}"
            ),
        )

        self.check_verification_corpus(directory, first.get("corpus"))
        self.check_verification_cli(first.get("cli"))

        export = payload.get("export") or {}
        on_disk = sha256(official.EXPORT)
        lines = (
            len(official.EXPORT.read_text(encoding="utf-8").splitlines())
            if official.EXPORT.exists()
            else None
        )
        self.record(
            "verification_export",
            export.get("sha256") == on_disk
            and export.get("status") == "PASS"
            and export.get("lines") == lines,
            (
                f"the verified export is recorded as {str(export.get('sha256'))[:16]}… "
                f"over {export.get('lines')} lines; on disk it is "
                f"{str(on_disk)[:16]}… over {lines}"
            ),
        )

    def check_verification_corpus(self, directory: Path, record: Optional[dict]) -> None:
        """The corpus totals, and the evidence file they are drawn from."""

        problems: List[dict] = []
        if record is None:
            self.record(
                "verification_corpus", False,
                "the isolated-corpus acceptance record is absent",
            )
            return

        if record.get("programs_checked") != EXPECTED_CORPUS_PROGRAMS:
            problems.append({"programs_checked": record.get("programs_checked")})
        if record.get("programs_expected") != EXPECTED_CORPUS_PROGRAMS:
            problems.append({"programs_expected": record.get("programs_expected")})
        if record.get("cases_checked") != EXPECTED_CORPUS_CASES:
            problems.append({"cases_checked": record.get("cases_checked")})
        if record.get("failures"):
            problems.append({"failures": record["failures"][:5]})
        if record.get("discrepancies"):
            problems.append({"discrepancies": record["discrepancies"][:5]})

        name = Path(str(record.get("evidence", ""))).name
        if name != "isolated_corpus.json":
            problems.append({"evidence": record.get("evidence")})
            evidence = None
        else:
            evidence = self.require(directory / name)

        if evidence is not None:
            runs = evidence.get("runs") or []
            for field, expected in (
                ("programs", EXPECTED_CORPUS_PROGRAMS),
                ("expected", EXPECTED_CORPUS_PROGRAMS),
                ("passed", EXPECTED_CORPUS_PROGRAMS),
                ("cases", EXPECTED_CORPUS_CASES),
            ):
                if evidence.get(field) != expected:
                    problems.append(
                        {"evidence_field": field, "value": evidence.get(field),
                         "required": expected}
                    )
            if evidence.get("failures"):
                problems.append({"evidence_failures": evidence["failures"][:5]})
            if len(runs) != EXPECTED_CORPUS_PROGRAMS:
                problems.append({"evidence_rows": len(runs)})
            if record.get("cases_checked") != evidence.get("cases"):
                problems.append(
                    {"error": "the summary's case count is not the evidence's"}
                )
            bad = [
                run.get("program") for run in runs
                if run.get("status") != "PASS"
                or run.get("exit_code") != 0
                or (run.get("result") or {}).get("discrepancy_count")
                or (run.get("result") or {}).get("validation_errors")
                or (run.get("result") or {}).get("leaked")
                or (run.get("result") or {}).get("target_discrepancies")
            ]
            if bad:
                problems.append({"failing_programs": bad[:5], "count": len(bad)})
            counted = sum((run.get("result") or {}).get("cases", 0) for run in runs)
            if counted != EXPECTED_CORPUS_CASES:
                problems.append({"cases_summed_from_rows": counted})
            if evidence.get("export_sha256") != sha256(official.EXPORT):
                problems.append(
                    {"error": "the corpus was checked against a different export",
                     "recorded": str(evidence.get("export_sha256"))[:16]}
                )

            manifest = self.require(directory / "corpus_manifest.json")
            if manifest is not None:
                declared = set(manifest.get("files") or [])
                observed = {run.get("program") for run in runs}
                if declared != observed:
                    problems.append(
                        {"error": "the measured programs are not the materialised set",
                         "only_declared": sorted(declared - observed)[:5],
                         "only_measured": sorted(observed - declared)[:5]}
                    )
                if len(declared) != EXPECTED_CORPUS_PROGRAMS:
                    problems.append({"manifest_files": len(declared)})
                absent = [
                    entry for entry in sorted(declared)
                    if not (directory / "corpus" / entry).exists()
                ]
                if absent:
                    problems.append({"missing_inputs": absent[:5]})

        self.record(
            "verification_corpus",
            not problems,
            (
                f"{EXPECTED_CORPUS_PROGRAMS} corpus programs and "
                f"{EXPECTED_CORPUS_CASES} cases required, checked against the "
                f"isolated-corpus evidence and the materialised inputs rather than "
                f"against the summary's totals alone; {len(problems)} disagree"
            ),
            problems=problems[:10],
        )

    def check_verification_cli(self, record: Optional[dict]) -> None:
        """The documented command line, one fresh process per public program."""

        expected = sorted(
            path.name for path in (official.REFERENCE / "programs").glob("*.json")
        )
        entries = (record or {}).get("programs") or []
        observed = sorted(entry.get("program") for entry in entries)
        bad = [
            entry.get("program") for entry in entries
            if entry.get("status") != "PASS"
            or entry.get("exit_code") != 0
            or not entry.get("stdout_is_json")
            or entry.get("timed_out")
        ]
        self.record(
            "verification_cli",
            record is not None
            and record.get("status") == "PASS"
            and len(expected) == EXPECTED_PUBLIC_PROGRAMS
            and observed == expected
            and not bad,
            (
                f"{len(expected)} pinned public programs must each run under the "
                f"documented command line and emit JSON alone; {len(entries)} "
                f"recorded, {len(bad)} not passing cleanly; "
                f"{'the recorded set is the pinned set' if observed == expected else 'the recorded set is not the pinned set'}"
            ),
            failing=bad[:8],
        )

    # -- driver ----------------------------------------------------------

    def check_phase(self, label: str, path: Path, phase: str,
                    repeats: int) -> None:
        payload = self.require(path)
        if payload is None:
            return
        if not self.fields(label, payload, REQUIRED_RUN_FIELDS):
            return
        provenance = payload["provenance"]
        if not self.fields(f"provenance:{label}", provenance, REQUIRED_PROVENANCE_FIELDS):
            return

        programs = self.public_programs
        analysis = payload["analysis"]
        self.record(
            f"contract:{label}",
            analysis.get("repetitions") == repeats
            and list(analysis.get("arms", [])) == list(EXPECTED_ARMS)
            and sorted(analysis.get("programs", [])) == sorted(programs),
            (
                f"report declares {analysis.get('repetitions')} repetitions, "
                f"{len(analysis.get('arms', []))} arms and "
                f"{len(analysis.get('programs', []))} programs; the fixed contract "
                f"requires {repeats}, {len(EXPECTED_ARMS)} and {len(programs)}"
            ),
        )

        self.check_recorded_hashes(label, provenance)
        self.check_exports(label, provenance)
        # The declared protocol is checked whatever the rows turn out to be: a
        # weakened experiment is a finding in its own right, not a consequence.
        self.check_bootstrap_protocol(label, payload)
        rows_ok = self.check_rows(
            label, payload["runs"], payload["failures"], programs, repeats
        )
        self.check_frozen_integers(label, payload["runs"])
        if rows_ok:
            self.check_scores(label, payload["runs"], analysis, programs)
            self.check_products_and_bootstrap(label, payload["runs"], programs)
            self.check_aggregates_and_intervals(label, payload, programs, repeats)
        else:
            # Recomputing an aggregate from rows already known to be corrupt
            # would report a second, derived failure and could raise on the way.
            # The membership and validity failures above are the finding.
            self.record(
                f"statistics_recomputed:{label}", False,
                "the rows failed validation, so no statistic was recomputed from "
                "them; fix the rows before reading any aggregate",
            )
        if phase == "final":
            self.check_extra_corpus(label, payload)
        self.check_gates_recomputed(
            label, payload, phase, bool(payload.get("extra_corpus"))
        )

    def run(self) -> dict:
        self.check_pinned_material()
        if self.external_baseline:
            # A repair round reuses an earlier round's frozen baseline rather
            # than remeasuring it, so that round's report is historical and is
            # not held to this round's contract. What is still checked is
            # everything this round depends on: that the baseline exists, that
            # its recorded frozen-export hash matches the file on disk, and —
            # through ``check_exports`` and ``check_extra_corpus`` below — that
            # the snapshot and every corpus input hash as recorded.
            provenance = self.require(self.baseline / "provenance.json")
            snapshot = sha256(self.baseline / "snapshot" / "compiler_frozen.py")
            self.record(
                "external_baseline",
                provenance is not None
                and snapshot is not None
                and provenance.get("frozen_export_sha256") == snapshot,
                (
                    f"frozen baseline {self.baseline} carries a snapshot hashing to "
                    f"{str(snapshot)[:16]}…, recorded as "
                    f"{str((provenance or {}).get('frozen_export_sha256'))[:16]}…; "
                    "its own phase report is historical and is not re-validated "
                    "against this round's contract"
                ),
            )
        else:
            self.check_phase(
                "baseline", self.baseline / "runs.json", "baseline",
                EXPECTED_REPEATS,
            )
        self.check_phase(
            "final", self.root / "final" / "runs.json", "final",
            EXPECTED_REPEATS,
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
            "baseline": str(self.baseline),
            "all_passed": passed,
            "contract": {
                "arms": list(EXPECTED_ARMS),
                "public_programs": EXPECTED_PUBLIC_PROGRAMS,
                "repetitions": EXPECTED_REPEATS,
                "extra_corpus_size": EXPECTED_EXTRA_SIZE,
                "extra_repetitions": EXPECTED_EXTRA_REPEATS,
                "comparison_repetitions": EXPECTED_COMPARISON_REPEATS,
                "corpus_programs": EXPECTED_CORPUS_PROGRAMS,
                "corpus_cases": EXPECTED_CORPUS_CASES,
                "bootstrap_resamples": EXPECTED_BOOTSTRAP_RESAMPLES,
                "bootstrap_seed": EXPECTED_BOOTSTRAP_SEED,
                "verification_stages": list(REQUIRED_TEST_STAGES),
                "verification_acceptance_steps": list(REQUIRED_ACCEPTANCE_STEPS),
                "public_suite_tests": EXPECTED_PUBLIC_TESTS,
                "note": "fixed here and in the pinned inputs; never read from the report",
                "enforced": (
                    "these are the settings actually used for every recomputation; "
                    "no command-line option can change them"
                ),
            },
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
    parser.add_argument(
        "--baseline",
        help="frozen baseline tree holding the snapshot and evaluation corpus; "
        "defaults to <root>/baseline",
    )
    parser.add_argument("--output")
    # There is deliberately no option for the resample count or the seed. They
    # are the acceptance protocol; an option that could lower them would be an
    # option that could weaken an acceptance check, which is how F1 arose.
    arguments = parser.parse_args(argv)

    root = Path(arguments.root).resolve()
    if not root.exists():
        print(f"{root} does not exist", file=sys.stderr)
        return 2
    baseline = Path(arguments.baseline).resolve() if arguments.baseline else None

    payload = Checker(root, baseline).run()
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
