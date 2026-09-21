"""Regressions for the independent evidence checker.

Finding R3 of the lead review of 2026-09-20, recorded in
``results/direct_index_v4_optimization/REVIEW.md``. The checker had claimed
rejection safeguards it did not have: removing the whole evaluation corpus,
erasing the recorded hash maps, forging every confidence interval, or drifting
an official classical measurement while preserving its product all left
``all_passed`` true.

Each of those mutations is exercised here through the checker's real entry
point, on a copy of a real evidence tree, and each must produce a nonzero exit.
The tree is copied to a temporary directory first, so no recorded evidence is
ever modified.

A checker that cannot reject corrupted evidence is not a check. These tests are
the guard that it still can.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for entry in (str(ROOT / ".reference"), str(ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import check_optimization_evidence as checker  # noqa: E402


REPAIR_TREE = ROOT / "results" / "direct_index_v4_optimization_repair"
BASELINE_TREE = ROOT / "results" / "direct_index_v4_optimization" / "baseline"

# Recomputing ten thousand resamples for every mutation would dominate the
# suite. The interval check is exercised at a smaller, still deterministic,
# resample count; the full count is used in the retained evidence run.
RESAMPLES = 200


def tree_available() -> bool:
    return (REPAIR_TREE / "final" / "runs.json").exists() and (
        BASELINE_TREE / "runs.json"
    ).exists()


class EvidenceCheckerTests(unittest.TestCase):
    """Every mutation must be rejected through the real entry point."""

    @classmethod
    def setUpClass(cls):
        if not tree_available():
            raise unittest.SkipTest(
                "the repair evidence tree is not present in this checkout; "
                f"expected {REPAIR_TREE / 'final' / 'runs.json'}"
            )

    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="evidence-check-"))
        self.addCleanup(shutil.rmtree, self.temp, ignore_errors=True)
        self.root = self.temp / "tree"
        self.baseline = self.temp / "baseline"
        shutil.copytree(REPAIR_TREE, self.root)
        shutil.copytree(BASELINE_TREE, self.baseline)
        self.write_verification_summary()

    def write_verification_summary(self):
        """Stand in for the verifier's own summary.

        These tests run *inside* a staged verification run, so the summary the
        checker would read is the one still being written by that very run and
        is necessarily incomplete. What is under test here is the checker's
        treatment of the benchmark and comparison evidence, so the verification
        artifact is replaced by a correct one built from the live tree. Its
        hashes are computed from the files on disk, so it cannot mask a real
        hash drift.
        """

        import hashlib

        def digest(path):
            return hashlib.sha256(path.read_bytes()).hexdigest()

        summary = {
            "status": "PASS",
            "failures": [],
            "records": [
                {"stage": "schema", "status": "PASS", "tests": 65},
                {
                    "stage": "acceptance", "step": "corpus", "status": "PASS",
                    "programs_checked": checker.EXPECTED_CORPUS_PROGRAMS,
                    "cases_checked": checker.EXPECTED_CORPUS_CASES,
                },
            ],
            "source_sha256": {
                name: digest(ROOT / name)
                for name in set(checker.bench.SOURCES) | set(checker.REQUIRED_SCRIPTS)
            },
            "test_sha256": {
                path.name: digest(path)
                for path in sorted((ROOT / "tests_direct").glob("*.py"))
            },
        }
        destination = self.root / "verification" / "summary.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(summary, indent=2, sort_keys=True))

    def run_checker(self) -> int:
        return checker.main(
            [
                "--root", str(self.root),
                "--baseline", str(self.baseline),
                "--output", str(self.temp / "out.json"),
                "--resamples", str(RESAMPLES),
            ]
        )

    def failing_checks(self):
        payload = json.loads((self.temp / "out.json").read_text())
        return [c["check"] for c in payload["checks"] if not c["passed"]]

    def edit_final(self, mutate):
        path = self.root / "final" / "runs.json"
        payload = json.loads(path.read_text())
        mutate(payload)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def edit_comparison(self, mutate):
        path = self.root / "comparison" / "runs.json"
        payload = json.loads(path.read_text())
        mutate(payload)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    # -- the control -----------------------------------------------------

    def test_the_unmutated_tree_passes(self):
        self.assertEqual(
            self.run_checker(), 0,
            f"the control tree failed: {self.failing_checks()}",
        )

    # -- the lead's four mutations ---------------------------------------

    def test_removing_the_evaluation_corpus_is_rejected(self):
        def mutate(payload):
            payload["extra_corpus"] = None

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("extra_corpus:final", self.failing_checks())

    def test_erasing_the_recorded_hash_maps_is_rejected(self):
        def mutate(payload):
            payload["provenance"]["source_sha256"] = {}
            payload["provenance"]["test_sha256"] = {}

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("recorded_hashes:final", self.failing_checks())

    def test_a_forged_confidence_interval_is_rejected(self):
        def mutate(payload):
            for entry in payload["analysis"]["ratios"].values():
                entry["paired_bootstrap_95"].update(low=999, high=1000)

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("confidence_intervals:final", self.failing_checks())

    def test_a_product_preserving_classical_drift_is_rejected(self):
        """The official comparison, drifted so every aggregate is untouched."""

        def mutate(payload):
            row = next(
                r for r in payload["runs"]
                if r["arm"] == "classical" and r["scratch"] % 2 == 0
            )
            row["cycles"] *= 2
            row["scratch"] //= 2

        self.edit_comparison(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("comparison_gates", self.failing_checks())

    # -- the contract may not be defined by the report -------------------

    def test_a_reduced_arm_contract_is_rejected(self):
        """Dropping an arm from the report must not shrink what is required."""

        def mutate(payload):
            dropped = "frozen_bootstrap"
            payload["analysis"]["arms"] = [
                a for a in payload["analysis"]["arms"] if a != dropped
            ]
            payload["runs"] = [r for r in payload["runs"] if r["arm"] != dropped]

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        failing = self.failing_checks()
        self.assertIn("contract:final", failing)
        self.assertIn("membership:final", failing)

    def test_a_reduced_repetition_contract_is_rejected(self):
        def mutate(payload):
            payload["analysis"]["repetitions"] = 3
            payload["runs"] = [r for r in payload["runs"] if r["repeat"] < 3]

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("contract:final", self.failing_checks())

    def test_a_reduced_program_contract_is_rejected(self):
        def mutate(payload):
            dropped = payload["analysis"]["programs"][0]
            payload["analysis"]["programs"] = payload["analysis"]["programs"][1:]
            payload["runs"] = [r for r in payload["runs"] if r["program"] != dropped]

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("contract:final", self.failing_checks())

    # -- stored flags are never taken on trust ---------------------------

    def test_a_forged_gate_flag_is_rejected(self):
        def mutate(payload):
            payload["acceptance_gates"]["frozen_classical_integers"]["passed"] = True
            payload["analysis"]["frozen_classical_integers"]["passed"] = False

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        failing = self.failing_checks()
        self.assertTrue(
            "gate_flags_recomputed:final" in failing
            or "mandatory_gates:final" in failing,
            failing,
        )

    def test_a_forged_score_is_rejected(self):
        def mutate(payload):
            payload["analysis"]["scores"]["candidate_full"]["combined_score"] = 99.0

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("score:final:candidate_full", self.failing_checks())

    def test_a_forged_aggregate_is_rejected(self):
        def mutate(payload):
            entry = payload["analysis"]["ratios"]["full_candidate_vs_frozen"]
            entry["geometric_mean_of_per_program_medians"] = 42.0

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("aggregates:final", self.failing_checks())

    def test_a_forged_target_decision_is_rejected(self):
        """Claiming a missed target was met must not survive recomputation."""

        def mutate(payload):
            payload["performance_targets"]["full_candidate_vs_frozen"]["met"] = True
            payload["analysis"]["ratios"]["full_candidate_vs_frozen"]["target_met"] = True

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("target_decisions:final", self.failing_checks())

    # -- rows and timings ------------------------------------------------

    def test_a_duplicated_row_standing_in_for_a_missing_one_is_rejected(self):
        def mutate(payload):
            payload["runs"].pop()
            payload["runs"].append(copy.deepcopy(payload["runs"][0]))

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("membership:final", self.failing_checks())

    def test_a_non_finite_timing_is_rejected(self):
        def mutate(payload):
            payload["runs"][0]["compile_seconds"] = None

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        failing = self.failing_checks()
        self.assertIn("rows_valid:final", failing)
        # And no aggregate is recomputed from rows already known to be corrupt.
        self.assertIn("statistics_recomputed:final", failing)

    def test_a_zero_timing_is_rejected(self):
        def mutate(payload):
            payload["runs"][0]["compile_seconds"] = 0.0

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("rows_valid:final", self.failing_checks())

    def test_an_unvalidated_row_is_rejected(self):
        def mutate(payload):
            payload["runs"][0]["correctness"] = "SKIPPED"

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("rows_valid:final", self.failing_checks())

    # -- the evaluation corpus is audited, not taken on trust ------------

    def test_a_corrupted_corpus_input_is_rejected(self):
        manifest = json.loads((self.baseline / "extra_corpus_manifest.json").read_text())
        victim = self.baseline / "extra_corpus" / manifest["programs"][0]["file"]
        program = json.loads(victim.read_text())
        program["name"] = program["name"] + "_tampered"
        victim.write_text(json.dumps(program, sort_keys=True))
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("extra_corpus_inputs:final", self.failing_checks())

    def test_a_missing_corpus_input_is_rejected(self):
        manifest = json.loads((self.baseline / "extra_corpus_manifest.json").read_text())
        (self.baseline / "extra_corpus" / manifest["programs"][0]["file"]).unlink()
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("extra_corpus_inputs:final", self.failing_checks())

    def test_a_dropped_corpus_row_is_rejected(self):
        def mutate(payload):
            payload["extra_corpus"]["runs"].pop()

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("membership:extra:final", self.failing_checks())

    def test_a_forged_corpus_score_distribution_is_rejected(self):
        def mutate(payload):
            payload["extra_corpus"]["score_distribution"]["candidate_full"][
                "combined_score_geomean"
            ] = 9.0

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("extra_corpus_scores:final", self.failing_checks())

    # -- required structure ----------------------------------------------

    def test_a_missing_required_field_is_rejected(self):
        def mutate(payload):
            del payload["acceptance_gates"]

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("fields:final", self.failing_checks())

    def test_a_missing_final_report_is_rejected(self):
        (self.root / "final" / "runs.json").unlink()
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("present:runs.json", self.failing_checks())

    def test_a_diagnostic_run_cannot_pass_as_acceptance(self):
        def mutate(payload):
            payload["acceptance_claimed"] = False

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("acceptance_claimed:final", self.failing_checks())

    def test_the_contract_is_reported_and_does_not_come_from_the_report(self):
        self.run_checker()
        payload = json.loads((self.temp / "out.json").read_text())
        contract = payload["contract"]
        self.assertEqual(contract["arms"], list(checker.EXPECTED_ARMS))
        self.assertEqual(contract["repetitions"], checker.EXPECTED_REPEATS)
        self.assertEqual(contract["extra_corpus_size"], checker.EXPECTED_EXTRA_SIZE)
        self.assertIn("never read from the report", contract["note"])


if __name__ == "__main__":
    unittest.main()
