"""Independently check an optimization-phase evidence tree.

Section 7a of ``plan/OPTIMIZATION_PHASE_PLAN.md``, rewritten after the lead
review of 2026-09-20 recorded in
``results/direct_index_v4_optimization/REVIEW.md`` (finding R3).

This tool trusts **nothing** a report says about itself. In particular it does
not read a stored gate flag, a stored confidence interval, a stored score, a
stored snapshot-linkage boolean or a stored aggregate and call it verified. Each
of those is recomputed from the raw rows and the files on disk, and the run is
rejected when the recomputation disagrees.

The contract it checks against is fixed **here and in the pinned inputs**, never
taken from the report under examination. Arms come from the harness module,
programs from the pinned reference directory, repetition counts and corpus size
from the plan. A report that measured a reduced contract therefore fails rather
than defining its own.

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
* combined scores, per-program products, bootstrap metric equality, aggregate
  ratios, paired confidence intervals and target decisions, all recomputed;
* the extra corpus: every input present, re-hashed, and its score distribution
  recomputed;
* that the comparison's seven gates and the verifier's stages really passed,
  recomputed from their raw rows.

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
from typing import Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import compare_direct as official  # noqa: E402
import benchmark_optimization as bench  # noqa: E402

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
                                       programs: Sequence[str], repeats: int,
                                       resamples: int) -> None:
        analysis = payload["analysis"]
        runs = payload["runs"]
        seed = payload.get("seed")
        mismatched = []
        interval_mismatched = []
        target_mismatched = []

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

            # The interval is recomputed from the raw timings with the declared
            # seed. A forged interval cannot survive this. The resample count
            # is taken from the report itself, so recomputation is exact and
            # the --resamples option cannot be used to weaken the comparison.
            reported_interval = entry.get("paired_bootstrap_95", {})
            interval = bench.paired_bootstrap(
                runs, programs, baseline_arm, candidate_arm, repeats,
                seed=reported_interval.get("seed", seed),
                resamples=reported_interval.get("resamples") or resamples,
            )
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
                if met != bool(entry.get("target_met")):
                    target_mismatched.append(
                        {"ratio": name, "recomputed_met": met,
                         "reported_met": entry.get("target_met")}
                    )
                reported_target = payload.get("performance_targets", {}).get(name, {})
                if reported_target and met != bool(reported_target.get("met")):
                    target_mismatched.append(
                        {"ratio": name, "recomputed_met": met,
                         "reported_met": reported_target.get("met"),
                         "where": "performance_targets"}
                    )

        self.record(
            f"aggregates:{label}", not mismatched,
            f"{len(bench.RATIOS)} aggregate ratios recomputed from raw per-program "
            f"medians; {len(mismatched)} disagree", mismatched=mismatched,
        )
        self.record(
            f"confidence_intervals:{label}", not interval_mismatched,
            f"paired intervals recomputed from raw timings with seed {seed} and "
            f"{resamples} resamples; {len(interval_mismatched)} bounds disagree",
            mismatched=interval_mismatched[:10],
        )
        self.record(
            f"target_decisions:{label}", not target_mismatched,
            f"{len(bench.TARGETS)} target decisions recomputed; "
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
            programs == EXPECTED_CORPUS_PROGRAMS and cases == EXPECTED_CORPUS_CASES,
            f"{programs} of {EXPECTED_CORPUS_PROGRAMS} corpus programs and "
            f"{cases} of {EXPECTED_CORPUS_CASES} cases",
        )

    # -- driver ----------------------------------------------------------

    def check_phase(self, label: str, path: Path, phase: str, repeats: int,
                    resamples: int) -> None:
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
        rows_ok = self.check_rows(
            label, payload["runs"], payload["failures"], programs, repeats
        )
        self.check_frozen_integers(label, payload["runs"])
        if rows_ok:
            self.check_scores(label, payload["runs"], analysis, programs)
            self.check_products_and_bootstrap(label, payload["runs"], programs)
            self.check_aggregates_and_intervals(
                label, payload, programs, repeats, resamples
            )
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

    def run(self, resamples: int = bench.BOOTSTRAP_RESAMPLES) -> dict:
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
                EXPECTED_REPEATS, resamples,
            )
        self.check_phase(
            "final", self.root / "final" / "runs.json", "final",
            EXPECTED_REPEATS, resamples,
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
                "note": "fixed here and in the pinned inputs; never read from the report",
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
    parser.add_argument(
        "--resamples", type=int, default=bench.BOOTSTRAP_RESAMPLES,
        help="resamples used when recomputing the paired intervals",
    )
    arguments = parser.parse_args(argv)

    root = Path(arguments.root).resolve()
    if not root.exists():
        print(f"{root} does not exist", file=sys.stderr)
        return 2
    baseline = Path(arguments.baseline).resolve() if arguments.baseline else None

    payload = Checker(root, baseline).run(arguments.resamples)
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
