"""Regressions for the optimization-phase measurement harness.

Gate 10 of ``plan/OPTIMIZATION_PHASE_PLAN.md``. A benchmark that cannot detect
a corrupted dataset is not evidence, so every rejection the harness claims to
make is exercised here against an injected defect: a swapped identity, a
missing row, a duplicated row, an invalid metric, protected-hash drift, a stale
export, and a product-preserving drift in the frozen classical integers.

Also enforced here is the single-owner rule. The harness must take the shared
facts — hashing, the geometric mean, the protected-file and reference checks,
export freshness, the historical integers, the public program set — from
``compare_direct``, which owns them, rather than defining a second copy.
"""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
import sys
import unittest
import unittest.mock

ROOT = Path(__file__).resolve().parents[1]
for entry in (str(ROOT / ".reference"), str(ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import benchmark_optimization as bench
import compare_direct as official


PROGRAMS = ("alpha", "beta")
ARMS = bench.ARMS
REPEATS = 2


def row(arm, program, repeat, **overrides):
    record = {
        "arm": arm,
        "program": program,
        "repeat": repeat,
        "cycles": 10,
        "scratch": 8,
        "correctness": "PASS",
        "cases": 2,
        "discrepancy_count": 0,
        "leaked": [],
        "compile_seconds": 0.001,
        "process_seconds": 0.05,
        "import_seconds": 0.01,
    }
    record.update(overrides)
    return record


def dataset():
    return [
        row(arm, program, repeat)
        for arm in ARMS
        for program in PROGRAMS
        for repeat in range(REPEATS)
    ]


def validate(runs, failures=()):
    return bench.validate_rows(runs, list(failures), PROGRAMS, ARMS, REPEATS)


class MembershipRejectionTests(unittest.TestCase):
    def test_a_complete_dataset_passes(self):
        verdict = validate(dataset())
        self.assertTrue(verdict["passed"], verdict["detail"])
        self.assertEqual(verdict["expected_keys"], len(ARMS) * len(PROGRAMS) * REPEATS)
        self.assertEqual(verdict["observed_rows"], verdict["expected_keys"])

    def test_a_missing_row_is_rejected(self):
        runs = dataset()
        runs.pop()
        verdict = validate(runs)
        self.assertFalse(verdict["passed"])
        self.assertEqual(len(verdict["missing"]), 1)

    def test_a_duplicate_standing_in_for_a_missing_row_is_rejected(self):
        """The row count is untouched, which is why counting proves nothing."""

        runs = dataset()
        victim = runs.pop()
        runs.append(copy.deepcopy(runs[0]))
        self.assertEqual(len(runs), len(dataset()))
        verdict = validate(runs)
        self.assertFalse(verdict["passed"])
        self.assertEqual(len(verdict["duplicates"]), 1)
        self.assertEqual(len(verdict["missing"]), 1)
        self.assertEqual(victim["arm"], verdict["missing"][0][0])

    def test_a_foreign_program_is_rejected(self):
        runs = dataset()
        runs[0] = row(runs[0]["arm"], "not_a_public_program", runs[0]["repeat"])
        verdict = validate(runs)
        self.assertFalse(verdict["passed"])
        self.assertEqual(len(verdict["unexpected"]), 1)

    def test_an_execution_failure_fails_the_dataset(self):
        verdict = validate(dataset(), failures=[{"arm": "classical", "error": "boom"}])
        self.assertFalse(verdict["passed"])
        self.assertEqual(len(verdict["execution_failures"]), 1)

    def test_an_empty_dataset_is_refused_rather_than_trivially_passing(self):
        verdict = bench.validate_rows([], [], [], ARMS, REPEATS)
        self.assertFalse(verdict["passed"], "zero expected keys must not read as a pass")
        self.assertIn("0 programs", verdict["detail"])


class InvalidRowTests(unittest.TestCase):
    def bad(self, **overrides):
        runs = dataset()
        runs[0] = row(runs[0]["arm"], runs[0]["program"], runs[0]["repeat"], **overrides)
        verdict = validate(runs)
        self.assertFalse(verdict["passed"])
        self.assertEqual(len(verdict["invalid_rows"]), 1)
        return verdict["invalid_rows"][0]["problems"]

    def test_a_non_positive_cycle_count_is_rejected(self):
        self.assertIn("cycles", self.bad(cycles=0))

    def test_a_non_positive_scratch_footprint_is_rejected(self):
        self.assertIn("scratch", self.bad(scratch=-1))

    def test_an_unvalidated_run_is_rejected(self):
        self.assertIn("correctness", self.bad(correctness="SKIPPED"))

    def test_a_run_that_checked_no_case_is_rejected(self):
        self.assertIn("cases", self.bad(cases=0))

    def test_a_query_validator_discrepancy_is_rejected(self):
        self.assertIn("discrepancy", self.bad(discrepancy_count=1))

    def test_a_leaked_prohibited_module_is_rejected(self):
        self.assertIn("module leak", self.bad(leaked=["common"]))


class FrozenIntegerTests(unittest.TestCase):
    """A product-preserving drift leaves every score intact and must still fail."""

    HISTORY = {
        "classical": {
            "alpha": {"cycles": 10, "scratch": 8},
            "beta": {"cycles": 10, "scratch": 8},
        }
    }

    def test_matching_integers_pass(self):
        verdict = bench.check_frozen_integers(dataset(), self.HISTORY)
        self.assertTrue(verdict["passed"], verdict["detail"])
        self.assertEqual(verdict["checked"], len(PROGRAMS) * REPEATS)

    def test_a_product_preserving_drift_is_rejected(self):
        runs = dataset()
        for record in runs:
            if record["arm"] == "classical" and record["program"] == "alpha":
                # 10 * 8 == 20 * 4, so nothing downstream of the product moves.
                record["cycles"], record["scratch"] = 20, 4
        verdict = bench.check_frozen_integers(runs, self.HISTORY)
        self.assertFalse(verdict["passed"])
        self.assertEqual(len(verdict["drift"]), REPEATS)

    def test_no_controlled_measurement_is_not_a_pass(self):
        verdict = bench.check_frozen_integers(dataset(), {})
        self.assertFalse(verdict["passed"], "an unchecked control must not read PASS")


class IdentityTests(unittest.TestCase):
    """A worker answering for the wrong arm or mode must be refused."""

    class FakeCompleted:
        returncode = 0
        stderr = ""

        def __init__(self, payload):
            import json

            self.stdout = json.dumps(payload)

    def one(self, payload, arm="candidate_full", program="alpha"):
        import json
        import subprocess

        session = bench.Bench.__new__(bench.Bench)
        session.timeout = 5
        original = subprocess.run
        completed = self.FakeCompleted(payload)
        subprocess.run = lambda *a, **k: completed
        session.command_for = lambda *a, **k: (["true"], str(ROOT))
        try:
            return session._one(arm, Path("x.json"), program, 0)
        finally:
            subprocess.run = original

    def test_a_matching_response_is_accepted(self):
        record, failure = self.one(
            {"arm": "candidate_full", "program": "alpha", "optimise": True}
        )
        self.assertIsNone(failure)
        self.assertEqual(record["repeat"], 0)

    def test_a_swapped_arm_is_rejected(self):
        record, failure = self.one(
            {"arm": "frozen_full", "program": "alpha", "optimise": True}
        )
        self.assertIsNone(record)
        self.assertIn("was requested", failure["error"])

    def test_a_swapped_program_is_rejected(self):
        record, failure = self.one(
            {"arm": "candidate_full", "program": "beta", "optimise": True}
        )
        self.assertIsNone(record)
        self.assertIn("was requested", failure["error"])

    def test_a_bootstrap_answer_for_a_full_arm_is_rejected(self):
        """The mode is part of the identity, not only the arm's name."""

        record, failure = self.one(
            {"arm": "candidate_full", "program": "alpha", "optimise": False}
        )
        self.assertIsNone(record)
        self.assertIn("optimise", failure["error"])

    def test_output_that_is_not_json_is_rejected(self):
        import subprocess

        class Broken:
            returncode = 0
            stdout = "not json at all"
            stderr = ""

        session = bench.Bench.__new__(bench.Bench)
        session.timeout = 5
        session.command_for = lambda *a, **k: (["true"], str(ROOT))
        original = subprocess.run
        subprocess.run = lambda *a, **k: Broken()
        try:
            record, failure = session._one("classical", Path("x.json"), "alpha", 0)
        finally:
            subprocess.run = original
        self.assertIsNone(record)
        self.assertIn("not JSON", failure["error"])

    def test_a_nonzero_exit_is_recorded_as_a_failure(self):
        import subprocess

        class Failed:
            returncode = 3
            stdout = ""
            stderr = "traceback"

        session = bench.Bench.__new__(bench.Bench)
        session.timeout = 5
        session.command_for = lambda *a, **k: (["true"], str(ROOT))
        original = subprocess.run
        subprocess.run = lambda *a, **k: Failed()
        try:
            record, failure = session._one("classical", Path("x.json"), "alpha", 0)
        finally:
            subprocess.run = original
        self.assertIsNone(record)
        self.assertEqual(failure["exit_code"], 3)


class ProvenanceRefusalTests(unittest.TestCase):
    def test_protected_hash_drift_stops_the_measurement(self):
        original = dict(official.PROTECTED)
        try:
            official.PROTECTED["common.py"] = "0" * 64
            with self.assertRaises(RuntimeError) as caught:
                bench.verify_protected()
            self.assertIn("common.py", str(caught.exception))
        finally:
            official.PROTECTED.clear()
            official.PROTECTED.update(original)

    def test_a_stale_export_stops_the_measurement(self):
        export = bench.EXPORT
        saved = export.read_text(encoding="utf-8")

        def fresh() -> bool:
            try:
                bench.verify_export_fresh()
            except RuntimeError:
                return False
            return True

        # Whether the checked-out export happens to be fresh right now is not
        # this test's business; that it *notices* a change is.
        was_fresh = fresh()
        try:
            export.write_text(saved + "\n# staleness injected\n", encoding="utf-8")
            with self.assertRaises(RuntimeError) as caught:
                bench.verify_export_fresh()
            self.assertIn("differs", str(caught.exception))
        finally:
            export.write_text(saved, encoding="utf-8")
        self.assertEqual(was_fresh, fresh(), "the export was not restored")


class AggregateTests(unittest.TestCase):
    def test_the_primary_aggregate_is_the_geometric_mean_of_median_ratios(self):
        medians = {
            "classical": {"alpha": 1.0, "beta": 4.0},
            "candidate_full": {"alpha": 1.0, "beta": 1.0},
        }
        entry = bench.aggregate_ratio(medians, ("alpha", "beta"), "classical", "candidate_full")
        # sqrt(1 * 4) == 2
        self.assertAlmostEqual(entry["geometric_mean_of_per_program_medians"], 2.0)
        self.assertEqual(entry["programs_slower_than_baseline"], [])

    def test_a_losing_program_is_named(self):
        medians = {
            "classical": {"alpha": 0.5, "beta": 4.0},
            "candidate_full": {"alpha": 1.0, "beta": 1.0},
        }
        entry = bench.aggregate_ratio(medians, ("alpha", "beta"), "classical", "candidate_full")
        self.assertEqual(entry["programs_slower_than_baseline"], ["alpha"])

    def test_the_paired_interval_brackets_a_noiseless_ratio(self):
        runs = []
        for program in PROGRAMS:
            for repeat in range(REPEATS):
                runs.append(row("classical", program, repeat, compile_seconds=2.0))
                runs.append(row("candidate_full", program, repeat, compile_seconds=1.0))
        interval = bench.paired_bootstrap(
            runs, PROGRAMS, "classical", "candidate_full", REPEATS, resamples=200
        )
        self.assertAlmostEqual(interval["low"], 2.0)
        self.assertAlmostEqual(interval["high"], 2.0)

    def test_the_pooled_median_is_kept_apart_from_the_primary_aggregate(self):
        runs = []
        for repeat in range(REPEATS):
            runs.append(row("classical", "alpha", repeat, compile_seconds=1.0))
            runs.append(row("classical", "beta", repeat, compile_seconds=9.0))
            runs.append(row("candidate_full", "alpha", repeat, compile_seconds=1.0))
            runs.append(row("candidate_full", "beta", repeat, compile_seconds=3.0))
        medians = bench.per_program_medians(
            runs, PROGRAMS, ("classical", "candidate_full"), "compile_seconds"
        )
        primary = bench.aggregate_ratio(
            medians, PROGRAMS, "classical", "candidate_full"
        )["geometric_mean_of_per_program_medians"]
        pooled = bench.pooled_median_ratio(runs, "classical", "candidate_full")
        # sqrt(1 * 3) against median(1,1,9,9) / median(1,1,3,3) = 5/2.
        self.assertAlmostEqual(primary, 3.0 ** 0.5)
        self.assertAlmostEqual(pooled, 2.5)
        self.assertNotAlmostEqual(primary, pooled)


class BootstrapVersusFullTests(unittest.TestCase):
    def test_equal_metrics_hold_and_unequal_metrics_are_reported(self):
        runs = dataset()
        verdict = bench.bootstrap_equals_full(runs, PROGRAMS, "candidate")
        self.assertTrue(verdict["holds"])

        for record in runs:
            if record["arm"] == "candidate_full" and record["program"] == "alpha":
                record["cycles"] = 9
        verdict = bench.bootstrap_equals_full(runs, PROGRAMS, "candidate")
        self.assertFalse(verdict["holds"])
        self.assertEqual(len(verdict["discrepancies"]), 1)
        self.assertEqual(verdict["discrepancies"][0]["program"], "alpha")


class SingleOwnerTests(unittest.TestCase):
    """The harness must borrow the shared facts, not restate them."""

    SHARED = (
        "digest",
        "geomean",
        "verify_protected",
        "verify_reference",
        "verify_export_fresh",
        "historical_metrics",
    )

    def test_the_shared_helpers_are_the_comparator_own_objects(self):
        for name in self.SHARED:
            self.assertIs(
                getattr(bench, name),
                getattr(official, name),
                f"{name} is not the comparator's own object",
            )
        self.assertIs(bench.program_name_of, official._name_of)

    def test_the_harness_defines_no_second_copy_of_a_shared_helper(self):
        tree = ast.parse((ROOT / "benchmark_optimization.py").read_text(encoding="utf-8"))
        defined = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        for name in self.SHARED:
            self.assertNotIn(
                name, defined, f"{name} is redefined instead of imported"
            )

    def test_the_source_list_comes_from_the_verification_runner(self):
        import verify_direct

        self.assertIs(bench.SOURCES, verify_direct.SOURCES)

    def test_the_public_set_is_the_comparator_pinned_membership(self):
        paths = bench.public_paths()
        self.assertEqual(len(paths), 8)
        names = {bench.program_name_of(path) for path in paths}
        self.assertEqual(len(names), 8)


if __name__ == "__main__":
    unittest.main()


# --------------------------------------------------------------------------
# R2: a detected failure must reach the exit code
# (lead review of 2026-09-20, results/direct_index_v4_optimization/REVIEW.md)
# --------------------------------------------------------------------------


def analysis_for(runs, failures=(), programs=PROGRAMS, repeats=REPEATS):
    return bench.analyse(
        list(runs), list(failures), list(programs), list(ARMS), repeats,
        {"classical": {p: {"cycles": 10, "scratch": 8} for p in programs},
         "serial": {p: {"cycles": 20, "scratch": 16} for p in programs}},
        bench.DEFAULT_SEED, resamples=50,
    )


class MandatoryGateTests(unittest.TestCase):
    """Every control the harness evaluates must be able to fail the run.

    The defect this replaces was not a missing check. The frozen-integer
    control was computed correctly and recorded a real failure, and the phase
    returned success anyway. A detected failure that does not reach the exit
    code is worse than an absent one: it turns a defect into a passing record.

    These fixtures are small synthetic datasets, so the score floors are scoped
    to what this fixture scores rather than to the real accepted values. What is
    under test is the conjunction, not the constants; the constants are
    exercised against real measured rows in ``PhaseExitCodeTests``.
    """

    def setUp(self):
        # serial 20x16 against an arm's 10x8 gives a combined score of exactly 2.
        for name in ("ACCEPTED_DIRECT_SCORE", "ACCEPTED_CLASSICAL_SCORE"):
            patcher = unittest.mock.patch.object(bench, name, 2.0)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_a_clean_dataset_passes_every_mandatory_gate(self):
        gates = bench.acceptance_gates(analysis_for(dataset()), "baseline", True)
        self.assertTrue(gates["all_passed"]["passed"], gates)

    def test_a_product_preserving_classical_drift_fails_the_conjunction(self):
        runs = dataset()
        for record in runs:
            if record["arm"] == "classical" and record["program"] == "alpha":
                record["cycles"], record["scratch"] = 20, 4
        gates = bench.acceptance_gates(analysis_for(runs), "baseline", True)
        self.assertFalse(gates["frozen_classical_integers"]["passed"])
        self.assertFalse(gates["all_passed"]["passed"])

    def test_a_missing_row_fails_the_conjunction(self):
        runs = dataset()
        runs.pop()
        gates = bench.acceptance_gates(analysis_for(runs), "baseline", True)
        self.assertFalse(gates["membership"]["passed"])
        self.assertFalse(gates["all_passed"]["passed"])

    def test_an_invalid_row_fails_the_conjunction(self):
        runs = dataset()
        runs[0]["discrepancy_count"] = 1
        gates = bench.acceptance_gates(analysis_for(runs), "baseline", True)
        self.assertFalse(gates["rows_valid"]["passed"])
        self.assertFalse(gates["all_passed"]["passed"])

    def test_a_per_program_product_regression_fails_the_conjunction(self):
        runs = dataset()
        for record in runs:
            if record["arm"] == "candidate_full" and record["program"] == "alpha":
                record["scratch"] = 16  # product 160 against the frozen 80
        gates = bench.acceptance_gates(analysis_for(runs), "baseline", True)
        self.assertFalse(gates["per_program_product_nonregression"]["passed"])
        self.assertFalse(gates["all_passed"]["passed"])

    def test_a_bootstrap_metric_change_fails_the_conjunction(self):
        runs = dataset()
        for record in runs:
            if record["arm"] == "candidate_bootstrap" and record["program"] == "beta":
                record["cycles"] = 9  # a better product, but not identical
        gates = bench.acceptance_gates(analysis_for(runs), "baseline", True)
        self.assertFalse(gates["bootstrap_metrics_identical"]["passed"])
        self.assertFalse(gates["all_passed"]["passed"])

    def test_a_score_below_the_accepted_floor_fails_the_conjunction(self):
        runs = dataset()
        for record in runs:
            if record["arm"].startswith("candidate"):
                record["cycles"] = 40  # a far worse score than the v3 floor
        gates = bench.acceptance_gates(analysis_for(runs), "baseline", True)
        self.assertFalse(gates["score_floor"]["passed"])
        self.assertFalse(gates["all_passed"]["passed"])

    def test_a_skipped_evaluation_corpus_fails_a_final_run(self):
        gates = bench.acceptance_gates(analysis_for(dataset()), "final", False)
        self.assertFalse(gates["extra_corpus_evaluated"]["passed"])
        self.assertFalse(gates["all_passed"]["passed"])
        # The same dataset is acceptable once the corpus is present.
        gates = bench.acceptance_gates(analysis_for(dataset()), "final", True)
        self.assertTrue(gates["all_passed"]["passed"])

    def test_a_missed_speed_target_is_not_a_gate(self):
        """An unmet engineering target is an outcome, not a correctness failure."""

        runs = dataset()
        for record in runs:
            # Make the candidate no faster than the frozen arm at all.
            if record["arm"].startswith("candidate"):
                record["compile_seconds"] = 1.0
            if record["arm"].startswith("frozen"):
                record["compile_seconds"] = 1.0
        analysis = analysis_for(runs)
        targets = bench.performance_targets(analysis)
        self.assertFalse(targets["full_candidate_vs_frozen"]["met"])
        self.assertFalse(targets["bootstrap_candidate_vs_frozen"]["met"])
        gates = bench.acceptance_gates(analysis, "baseline", True)
        self.assertTrue(
            gates["all_passed"]["passed"],
            "a missed speed target must not fail a correctness conjunction",
        )

    def test_report_gates_derives_the_exit_code_from_the_conjunction(self):
        import contextlib
        import io

        payload = {
            "acceptance_gates": bench.acceptance_gates(
                analysis_for(dataset()), "baseline", True
            ),
            "performance_targets": {},
            "acceptance_claimed": True,
        }
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(bench.report_gates(payload), 0)
        payload["acceptance_gates"]["all_passed"]["passed"] = False
        with contextlib.redirect_stderr(io.StringIO()) as captured:
            self.assertEqual(bench.report_gates(payload), 1)
        self.assertIn("not valid measurement evidence", captured.getvalue())

    def test_a_diagnostic_run_is_labelled_as_non_acceptance(self):
        import contextlib
        import io

        payload = {
            "acceptance_gates": bench.acceptance_gates(
                analysis_for(dataset()), "baseline", True
            ),
            "performance_targets": {},
            "acceptance_claimed": False,
        }
        with contextlib.redirect_stderr(io.StringIO()) as captured:
            bench.report_gates(payload)
        self.assertIn("NOT ACCEPTANCE EVIDENCE", captured.getvalue())


class PhaseExitCodeTests(unittest.TestCase):
    """The real phase entry points, driven with injected failures."""

    def phase_final(self, rows, **overrides):
        import argparse
        import contextlib
        import io
        import tempfile
        from unittest.mock import patch

        results = ROOT / "results" / "direct_index_v4_optimization"
        with tempfile.TemporaryDirectory() as temp:
            options = dict(
                output=temp, baseline=str(results / "baseline"), allow_existing=False,
                timeout=20.0, seed=bench.DEFAULT_SEED, repeats=15, quiet=True,
                skip_extra_corpus=True, diagnostic=True, extra_repeats=3,
            )
            options.update(overrides)
            args = argparse.Namespace(**options)
            with patch.object(bench.Bench, "run", return_value=(rows, [], [])), \
                 patch.object(bench, "paired_bootstrap",
                              return_value={"low": 1.0, "high": 1.0}), \
                 contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                code = bench.phase_final(args)
            written = Path(temp) / "runs.json"
            report = json.loads(written.read_text()) if written.exists() else None
        return code, report

    def real_rows(self):
        import copy

        path = (ROOT / "results" / "direct_index_v4_optimization"
                / "final" / "runs.json")
        if not path.exists():
            self.skipTest("the v4 measured rows are not present in this checkout")
        return copy.deepcopy(json.loads(path.read_text())["runs"])

    def test_the_lead_probe_now_exits_nonzero(self):
        """Doubling classical cycles and halving scratch preserves the product.

        Every aggregate, ratio and score is therefore untouched, which is
        exactly why an aggregate check cannot see it and the per-program
        integer control must.
        """

        rows = self.real_rows()
        drifted = 0
        for row in rows:
            if row["arm"] == "classical" and row["scratch"] % 2 == 0:
                row["cycles"] *= 2
                row["scratch"] //= 2
                drifted += 1
        self.assertGreater(drifted, 0)
        code, report = self.phase_final(rows)
        self.assertEqual(code, 1, "a failed historical control exited successfully")
        self.assertFalse(report["analysis"]["frozen_classical_integers"]["passed"])
        self.assertFalse(report["acceptance_gates"]["all_passed"]["passed"])

    def test_an_unmodified_replay_passes_its_correctness_gates(self):
        rows = self.real_rows()
        code, report = self.phase_final(rows)
        gates = report["acceptance_gates"]
        for name in ("membership", "rows_valid", "frozen_classical_integers",
                     "per_program_product_nonregression",
                     "bootstrap_metrics_identical", "score_floor"):
            self.assertTrue(gates[name]["passed"], f"{name}: {gates[name]['detail']}")
        # It still exits nonzero, because a diagnostic run skipped the corpus.
        self.assertEqual(code, 1)
        self.assertFalse(gates["extra_corpus_evaluated"]["passed"])
        self.assertFalse(report["acceptance_claimed"])

    def test_skipping_the_corpus_without_the_diagnostic_flag_is_refused(self):
        rows = self.real_rows()
        code, report = self.phase_final(rows, diagnostic=False)
        self.assertEqual(code, 2, "a mandatory evaluation step was silently skipped")
        self.assertIsNone(report, "no report may be written for a refused run")

    def test_a_frozen_snapshot_mismatch_is_refused_before_measuring(self):
        import argparse
        import contextlib
        import io
        import tempfile
        from unittest.mock import patch

        results = ROOT / "results" / "direct_index_v4_optimization"
        if not (results / "baseline" / "provenance.json").exists():
            self.skipTest("the v4 baseline is not present in this checkout")
        measured = []
        with tempfile.TemporaryDirectory() as temp:
            args = argparse.Namespace(
                output=temp, baseline=str(results / "baseline"), allow_existing=False,
                timeout=20.0, seed=bench.DEFAULT_SEED, repeats=15, quiet=True,
                skip_extra_corpus=False, diagnostic=False, extra_repeats=3,
            )
            with patch.object(bench, "digest", return_value="0" * 64), \
                 patch.object(bench.Bench, "run",
                              side_effect=lambda *a, **k: measured.append(1) or ([], [], [])), \
                 contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                code = bench.phase_final(args)
        self.assertEqual(code, 2)
        self.assertEqual(measured, [], "measurement started despite a bad snapshot")
