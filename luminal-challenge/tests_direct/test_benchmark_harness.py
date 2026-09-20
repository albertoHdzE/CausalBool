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
from pathlib import Path
import sys
import unittest

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
