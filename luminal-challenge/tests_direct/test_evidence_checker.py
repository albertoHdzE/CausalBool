"""Regressions for the independent evidence checker.

Finding R3 of the lead review of 2026-09-20, recorded in
``results/direct_index_v4_optimization/REVIEW.md``. The checker had claimed
rejection safeguards it did not have: removing the whole evaluation corpus,
erasing the recorded hash maps, forging every confidence interval, or drifting
an official classical measurement while preserving its product all left
``all_passed`` true.

Findings F1 and F2 of the re-review recorded in
``results/direct_index_v4_optimization_repair/REVIEW.md`` closed two further
gaps, and their regressions are here too:

* F1 — the report controlled its own confidence-interval protocol. An interval
  recomputed correctly at **one** resample, declaring ``resamples=1``, passed:
  the checker took the count and seed from the interval it was auditing. The
  enforced protocol is now fixed in the checker, and a CLI option can no longer
  relax it because there is no longer one.
* F2 — the recorded verification could lose whole stages without rejection.
  Any stage could be deleted and the run still passed, because only a positive
  total test count and the corpus totals were required. The positive fixture
  below was itself a two-record summary, so it masked rather than exercised the
  contract. It is now a complete verification artifact, built explicitly.

Every mutation is exercised through the checker's real entry point, on a copy
of a real evidence tree, and each must produce a nonzero exit. The tree is
copied to a temporary directory first, so no recorded evidence is ever
modified.

A checker that cannot reject corrupted evidence is not a check. These tests are
the guard that it still can.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Optional
import unittest

ROOT = Path(__file__).resolve().parents[1]
for entry in (str(ROOT / ".reference"), str(ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import check_optimization_evidence as checker  # noqa: E402
import compare_direct as official  # noqa: E402
import verify_direct as verifier  # noqa: E402


# The evidence tree of the current round. Each repair round writes a new one
# and the regressions follow it, because the tree records the hashes of the very
# sources and tests being exercised; an earlier round's tree is historical and
# would fail on hash drift alone, which would say nothing about the checker.
REPAIR_TREE = ROOT / "results" / "direct_index_v4_optimization_repair2"
BASELINE_TREE = ROOT / "results" / "direct_index_v4_optimization" / "baseline"

# The verification contract, stated here independently of the checker so that a
# checker which quietly shrank its own required set still fails these tests.
TEST_STAGES = (
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
ACCEPTANCE_STEPS = ("corpus", "public_suite", "cli")
PUBLIC_TESTS = 11

# Plausible per-stage counts for the fixture. Nothing depends on the exact
# values: the contract requires a positive count that agrees with the stage's
# own log, and the fixture writes both, so it stays self-consistent as the real
# suites grow.
FIXTURE_TEST_COUNTS = {
    "schema": 65,
    "contract": 31,
    "constraints": 43,
    "construction": 22,
    "optimizer": 22,
    "independence": 13,
    "export": 33,
    "benchmark": 47,
    "evidence": 24,
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unittest_log(count: int) -> str:
    """A realistic passing unittest tail, at the recorded count."""

    return (
        "test_an_example (tests_direct.example.Case.test_an_example) ... ok\n"
        "\n"
        "----------------------------------------------------------------------\n"
        f"Ran {count} tests in 0.010s\n"
        "\n"
        "OK\n"
    )


def tree_available() -> bool:
    return (REPAIR_TREE / "final" / "runs.json").exists() and (
        BASELINE_TREE / "runs.json"
    ).exists()


# The corpus the fixture stands its acceptance evidence on. Materialised once,
# through ``verify_direct.materialise_corpus`` — the function that owns writing
# it — and then copied per test. Taking it from the tree under test would make
# the fixture depend on artifacts this very verification run has not written
# yet, which is exactly how the acceptance evidence went missing when the
# ``evidence`` stage ran before the ``acceptance`` stage.
_CORPUS_SOURCE: Optional[Path] = None
_CORPUS_MANIFEST: Optional[dict] = None


def corpus_source() -> tuple:
    global _CORPUS_SOURCE, _CORPUS_MANIFEST
    if _CORPUS_SOURCE is None:
        directory = Path(tempfile.mkdtemp(prefix="evidence-corpus-"))
        _CORPUS_MANIFEST = verifier.materialise_corpus(directory / "corpus")
        _CORPUS_SOURCE = directory / "corpus"
    return _CORPUS_SOURCE, _CORPUS_MANIFEST


class EvidenceTreeCase(unittest.TestCase):
    """A copied evidence tree with a complete, explicitly built verification."""

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

    # -- the positive fixture --------------------------------------------

    def write_verification_summary(self):
        """Build a complete verification artifact, record by record.

        These tests run *inside* a staged verification run, so the summary on
        disk is the one that very run has not finished writing. Reading it would
        be reading a stale or partial file. The fixture therefore constructs the
        whole artifact explicitly: one record for every declared stage, the three
        acceptance steps, a log per logged stage whose ``Ran N tests`` line
        agrees with its record, and an isolated-corpus evidence file derived from
        the corpus inputs themselves rather than copied from a previous verdict.

        Nothing here is softened. Source and test hashes are computed from the
        files on disk, so a real hash drift still fails, and the corpus totals
        are counted from the 142 program inputs rather than asserted.
        """

        directory = self.root / "verification"
        logs = directory / "logs"
        logs.mkdir(parents=True, exist_ok=True)

        records = []
        for stage in TEST_STAGES:
            count = FIXTURE_TEST_COUNTS.get(stage, 7)
            body = unittest_log(count)
            (logs / f"{stage}.stderr.txt").write_text(body, encoding="utf-8")
            (logs / f"{stage}.stdout.txt").write_text("", encoding="utf-8")
            records.append(
                {
                    "command": f"python3 -m unittest tests_direct.test_{stage} -v",
                    "exit_code": 0,
                    "module": f"tests_direct.test_{stage}",
                    "seconds": 0.01,
                    "stage": stage,
                    "status": "PASS",
                    "stderr_tail": body[-2000:],
                    "tests": count,
                    "timed_out": False,
                }
            )

        records.append(self.build_corpus_record(directory))

        public_body = unittest_log(PUBLIC_TESTS)
        (logs / "acceptance_public_suite.stderr.txt").write_text(
            public_body, encoding="utf-8"
        )
        (logs / "acceptance_public_suite.stdout.txt").write_text("", encoding="utf-8")
        records.append(
            {
                "command": "python3 -m unittest discover -s .reference/tests -t .reference",
                "exit_code": 0,
                "expected_tests": PUBLIC_TESTS,
                "seconds": 1.0,
                "stage": "acceptance",
                "status": "PASS",
                "stderr_tail": public_body[-2000:],
                "step": "public_suite",
                "tests": PUBLIC_TESTS,
                "timed_out": False,
            }
        )

        records.append(
            {
                "stage": "acceptance",
                "status": "PASS",
                "step": "cli",
                "programs": [
                    {
                        "exit_code": 0,
                        "program": path.name,
                        "seconds": 0.2,
                        "status": "PASS",
                        "stderr_present": True,
                        "stdout_is_json": True,
                        "timed_out": False,
                    }
                    for path in sorted((official.REFERENCE / "programs").glob("*.json"))
                ],
            }
        )

        export_text = official.EXPORT.read_text(encoding="utf-8")
        summary = {
            "export": {
                "lines": len(export_text.splitlines()),
                "path": str(official.EXPORT),
                "sha256": digest(official.EXPORT),
                "status": "PASS",
            },
            "failures": [],
            "platform": sys.platform,
            "python": sys.version.split()[0],
            "records": records,
            "reference_commit": "fixture",
            "requested_stage": "all",
            "source_sha256": {
                name: digest(ROOT / name)
                for name in set(checker.bench.SOURCES) | set(checker.REQUIRED_SCRIPTS)
            },
            "stages_run": list(TEST_STAGES) + ["acceptance"] * len(ACCEPTANCE_STEPS),
            "status": "PASS",
            "test_sha256": {
                path.name: digest(path)
                for path in sorted((ROOT / "tests_direct").glob("*.py"))
            },
            "timeout_seconds": 20.0,
        }
        destination = directory / "summary.json"
        destination.write_text(json.dumps(summary, indent=2, sort_keys=True))

    def build_corpus_record(self, directory: Path) -> dict:
        """The isolated-corpus evidence, counted from the corpus inputs.

        The inputs are materialised by the fixture rather than read out of the
        tree, and the manifest is the one ``materialise_corpus`` returns, so the
        record, the evidence file and the inputs are one consistent set however
        far along the surrounding verification run happens to be.
        """

        source, manifest = corpus_source()
        corpus = directory / "corpus"
        if corpus.exists():
            shutil.rmtree(corpus)
        shutil.copytree(source, corpus)
        (directory / "corpus_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True)
        )
        files = sorted(path.name for path in corpus.glob("*.json"))
        runs = []
        for name in files:
            program = json.loads((corpus / name).read_text())
            runs.append(
                {
                    "exit_code": 0,
                    "process_seconds": 0.2,
                    "program": name,
                    "result": {
                        "cases": len(program["cases"]),
                        "discrepancy_count": 0,
                        "leaked": [],
                        "target_discrepancies": [],
                        "validation_errors": [],
                    },
                    "sha256": digest(corpus / name),
                    "status": "PASS",
                }
            )
        cases = sum(run["result"]["cases"] for run in runs)
        evidence = {
            "accepted_improvements": 0,
            "cases": cases,
            "expected": len(files),
            "export_sha256": digest(official.EXPORT),
            "failures": [],
            "max_process_seconds": 0.2,
            "passed": len(files),
            "programs": len(files),
            "runs": runs,
            "timeout_seconds": 20.0,
        }
        path = directory / "isolated_corpus.json"
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True))
        return {
            "accepted_improvements": 0,
            "cases_checked": cases,
            "discrepancies": [],
            "evidence": str(path),
            "failures": [],
            "max_process_seconds": 0.2,
            "programs_checked": len(files),
            "programs_expected": len(files),
            "stage": "acceptance",
            "status": "PASS",
            "step": "corpus",
        }

    # -- plumbing ---------------------------------------------------------

    def run_checker(self) -> int:
        return checker.main(
            [
                "--root", str(self.root),
                "--baseline", str(self.baseline),
                "--output", str(self.temp / "out.json"),
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

    def edit_verification(self, mutate):
        path = self.root / "verification" / "summary.json"
        payload = json.loads(path.read_text())
        mutate(payload)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def record_named(self, payload: dict, label: str) -> dict:
        for record in payload["records"]:
            if (record.get("step") or record.get("stage")) == label:
                return record
        raise AssertionError(f"the fixture has no {label} record")


class EvidenceCheckerTests(EvidenceTreeCase):
    """Every mutation must be rejected through the real entry point."""

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


class BootstrapProtocolTests(EvidenceTreeCase):
    """F1: the report may not choose the protocol it is audited against.

    The defect was narrow and total. ``check_aggregates_and_intervals`` read the
    resample count and seed out of the very interval it was verifying, so an
    experiment run at one resample was recomputed at one resample, agreed with
    itself, and passed — while the printed detail still said ten thousand.
    """

    def intervals(self, payload):
        return [
            entry["paired_bootstrap_95"]
            for entry in payload["analysis"]["ratios"].values()
        ]

    def recompute(self, payload, seed, resamples):
        """Honest bounds for a weakened protocol: correct, and still refused."""

        for name, baseline, candidate in checker.bench.RATIOS:
            entry = payload["analysis"]["ratios"].get(name)
            if entry is None:
                continue
            entry["paired_bootstrap_95"] = checker.bench.paired_bootstrap(
                payload["runs"], payload["analysis"]["programs"],
                baseline, candidate, payload["analysis"]["repetitions"],
                seed=seed, resamples=resamples,
            )

    def test_a_one_resample_interval_is_rejected(self):
        """The lead's probe: mathematically correct bounds at one resample."""

        self.edit_final(lambda payload: self.recompute(payload, 20260920, 1))
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("bootstrap_protocol:final", self.failing_checks())

    def test_a_wrong_seed_interval_is_rejected(self):
        self.edit_final(lambda payload: self.recompute(payload, 12345, 10000))
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("bootstrap_protocol:final", self.failing_checks())

    def test_a_drifted_run_seed_is_rejected(self):
        def mutate(payload):
            payload["seed"] = 99

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("bootstrap_protocol:final", self.failing_checks())

    def test_a_missing_protocol_field_is_rejected(self):
        def mutate(payload):
            for interval in self.intervals(payload):
                del interval["resamples"]

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("bootstrap_protocol:final", self.failing_checks())

    def test_a_missing_seed_declaration_is_rejected(self):
        def mutate(payload):
            for interval in self.intervals(payload):
                del interval["seed"]

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("bootstrap_protocol:final", self.failing_checks())

    def test_a_missing_interval_is_rejected(self):
        def mutate(payload):
            del payload["analysis"]["ratios"]["full_candidate_vs_frozen"][
                "paired_bootstrap_95"
            ]

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("bootstrap_protocol:final", self.failing_checks())

    def test_a_missing_ratio_is_rejected(self):
        def mutate(payload):
            del payload["analysis"]["ratios"]["full_candidate_vs_frozen"]

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        failing = self.failing_checks()
        self.assertIn("bootstrap_protocol:final", failing)
        self.assertIn("ratio_coverage:final", failing)

    # -- target declarations must be complete ----------------------------

    def test_an_omitted_target_declaration_is_rejected(self):
        """An omitted declaration must not quietly bypass the comparison."""

        def mutate(payload):
            del payload["performance_targets"]["full_candidate_vs_frozen"]

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("target_decisions:final", self.failing_checks())

    def test_an_incomplete_target_declaration_is_rejected(self):
        def mutate(payload):
            del payload["performance_targets"]["full_candidate_vs_frozen"]["measured"]

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("target_decisions:final", self.failing_checks())

    def test_a_weakened_target_value_is_rejected(self):
        """Lowering the bar so a missed target reads as met."""

        def mutate(payload):
            payload["performance_targets"]["full_candidate_vs_frozen"]["target"] = 1.0
            payload["analysis"]["ratios"]["full_candidate_vs_frozen"]["target"] = 1.0
            payload["analysis"]["ratios"]["full_candidate_vs_frozen"]["target_met"] = True
            payload["performance_targets"]["full_candidate_vs_frozen"]["met"] = True

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("target_decisions:final", self.failing_checks())

    def test_a_drifted_target_measurement_is_rejected(self):
        def mutate(payload):
            payload["performance_targets"]["full_candidate_vs_frozen"][
                "measured"
            ] = 42.0

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("target_decisions:final", self.failing_checks())

    def test_a_target_outside_the_contract_is_rejected(self):
        def mutate(payload):
            payload["performance_targets"]["invented_target"] = {
                "target": 1.0, "criterion": "invented", "measured": 9.0,
                "interval_low": 8.0, "interval_high": 10.0, "met": True,
            }

        self.edit_final(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("target_decisions:final", self.failing_checks())

    # -- the enforced settings are the checker's own ---------------------

    def test_the_enforced_protocol_is_fixed_and_reported(self):
        self.run_checker()
        payload = json.loads((self.temp / "out.json").read_text())
        contract = payload["contract"]
        self.assertEqual(contract["bootstrap_resamples"], 10000)
        self.assertEqual(contract["bootstrap_seed"], 20260920)
        detail = next(
            check["detail"] for check in payload["checks"]
            if check["check"] == "confidence_intervals:final"
        )
        self.assertIn("10000", detail)
        self.assertIn("20260920", detail)

    def test_no_option_can_relax_the_resample_count(self):
        """There is no longer a CLI lever on an acceptance check."""

        with self.assertRaises(SystemExit):
            checker.main(
                [
                    "--root", str(self.root),
                    "--baseline", str(self.baseline),
                    "--output", str(self.temp / "out.json"),
                    "--resamples", "1",
                ]
            )


class VerificationContractTests(EvidenceTreeCase):
    """F2: a required verification stage may not simply be absent.

    The checker required a positive total test count and the corpus totals.
    Deleting every stage but ``schema`` and ``corpus`` therefore left
    ``all_passed`` true — and the positive fixture was itself that two-record
    summary, so the suite asserted the hole rather than the contract.
    """

    def test_the_complete_fixture_passes(self):
        self.assertEqual(
            self.run_checker(), 0,
            f"the complete verification fixture failed: {self.failing_checks()}",
        )

    def test_the_checker_requires_the_same_stages_this_suite_declares(self):
        self.assertEqual(checker.REQUIRED_TEST_STAGES, TEST_STAGES)
        self.assertEqual(checker.REQUIRED_ACCEPTANCE_STEPS, ACCEPTANCE_STEPS)
        self.assertEqual(checker.EXPECTED_PUBLIC_TESTS, PUBLIC_TESTS)

    def test_the_leads_stage_deletion_is_rejected(self):
        """Keep only schema and corpus, exactly as the lead's probe did."""

        def mutate(payload):
            payload["records"] = [
                record for record in payload["records"]
                if record.get("stage") == "schema" or record.get("step") == "corpus"
            ]

        self.edit_verification(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_stages", self.failing_checks())

    def test_removing_any_single_required_record_is_rejected(self):
        for label in TEST_STAGES + ACCEPTANCE_STEPS:
            with self.subTest(label=label):
                self.setUp()

                def mutate(payload, label=label):
                    payload["records"] = [
                        record for record in payload["records"]
                        if (record.get("step") or record.get("stage")) != label
                    ]

                self.edit_verification(mutate)
                self.assertEqual(self.run_checker(), 1)
                self.assertIn("verification_stages", self.failing_checks())

    def test_a_duplicate_standing_in_for_a_missing_stage_is_rejected(self):
        def mutate(payload):
            payload["records"] = [
                record for record in payload["records"]
                if (record.get("step") or record.get("stage")) != "export"
            ]
            payload["records"].append(
                copy.deepcopy(self.record_named(payload, "schema"))
            )

        self.edit_verification(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_stages", self.failing_checks())

    def test_an_unexpected_stage_record_is_rejected(self):
        def mutate(payload):
            extra = copy.deepcopy(self.record_named(payload, "schema"))
            extra["stage"] = "invented"
            payload["records"].append(extra)

        self.edit_verification(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_stages", self.failing_checks())

    def test_a_zero_test_stage_is_rejected(self):
        def mutate(payload):
            record = self.record_named(payload, "constraints")
            record["tests"] = 0
            record["stderr_tail"] = unittest_log(0)[-2000:]

        self.edit_verification(mutate)
        path = self.root / "verification" / "logs" / "constraints.stderr.txt"
        path.write_text(unittest_log(0), encoding="utf-8")
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_test_counts", self.failing_checks())

    def test_a_failing_stage_is_rejected(self):
        def mutate(payload):
            self.record_named(payload, "optimizer")["status"] = "FAIL"

        self.edit_verification(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_status", self.failing_checks())

    def test_a_nonzero_stage_exit_code_is_rejected(self):
        def mutate(payload):
            self.record_named(payload, "export")["exit_code"] = 1

        self.edit_verification(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_status", self.failing_checks())

    def test_a_timed_out_stage_is_rejected(self):
        def mutate(payload):
            self.record_named(payload, "export")["timed_out"] = True

        self.edit_verification(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_status", self.failing_checks())

    def test_a_summary_level_failure_is_rejected(self):
        def mutate(payload):
            payload["failures"] = ["export"]

        self.edit_verification(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_status", self.failing_checks())

    # -- the logs must agree with the summary ----------------------------

    def test_a_count_the_log_does_not_support_is_rejected(self):
        def mutate(payload):
            self.record_named(payload, "schema")["tests"] = 9999

        self.edit_verification(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_logs", self.failing_checks())

    def test_a_missing_stage_log_is_rejected(self):
        (self.root / "verification" / "logs" / "benchmark.stderr.txt").unlink()
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_logs", self.failing_checks())

    def test_a_recorded_tail_that_is_not_the_logs_tail_is_rejected(self):
        def mutate(payload):
            record = self.record_named(payload, "contract")
            record["stderr_tail"] = "fabricated tail\n" + record["stderr_tail"]

        self.edit_verification(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_logs", self.failing_checks())

    # -- the public suite and the CLI ------------------------------------

    def test_a_public_suite_at_the_wrong_count_is_rejected(self):
        def mutate(payload):
            self.record_named(payload, "public_suite")["tests"] = 10

        self.edit_verification(mutate)
        path = self.root / "verification" / "logs" / "acceptance_public_suite.stderr.txt"
        path.write_text(unittest_log(10), encoding="utf-8")
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_public_suite", self.failing_checks())

    def test_a_dropped_cli_program_is_rejected(self):
        def mutate(payload):
            self.record_named(payload, "cli")["programs"].pop()

        self.edit_verification(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_cli", self.failing_checks())

    def test_a_failing_cli_program_is_rejected(self):
        def mutate(payload):
            entry = self.record_named(payload, "cli")["programs"][0]
            entry["status"] = "FAIL"
            entry["exit_code"] = 1

        self.edit_verification(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_cli", self.failing_checks())

    def test_cli_output_that_is_not_json_is_rejected(self):
        def mutate(payload):
            self.record_named(payload, "cli")["programs"][0]["stdout_is_json"] = False

        self.edit_verification(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_cli", self.failing_checks())

    # -- the corpus evidence behind the totals ---------------------------

    def test_a_missing_corpus_evidence_artifact_is_rejected(self):
        (self.root / "verification" / "isolated_corpus.json").unlink()
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("present:isolated_corpus.json", self.failing_checks())

    def test_corpus_totals_the_evidence_does_not_support_are_rejected(self):
        """The summary claims the contract; the evidence behind it is short."""

        path = self.root / "verification" / "isolated_corpus.json"
        evidence = json.loads(path.read_text())
        evidence["runs"].pop()
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True))
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_corpus", self.failing_checks())

    def test_a_failing_corpus_program_is_rejected(self):
        path = self.root / "verification" / "isolated_corpus.json"
        evidence = json.loads(path.read_text())
        evidence["runs"][0]["status"] = "FAIL"
        evidence["runs"][0]["exit_code"] = 1
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True))
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_corpus", self.failing_checks())

    def test_a_corpus_discrepancy_is_rejected(self):
        path = self.root / "verification" / "isolated_corpus.json"
        evidence = json.loads(path.read_text())
        evidence["runs"][0]["result"]["discrepancy_count"] = 1
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True))
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_corpus", self.failing_checks())

    def test_corpus_evidence_for_the_wrong_export_is_rejected(self):
        path = self.root / "verification" / "isolated_corpus.json"
        evidence = json.loads(path.read_text())
        evidence["export_sha256"] = "0" * 64
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True))
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_corpus", self.failing_checks())

    def test_a_corpus_run_outside_the_materialised_set_is_rejected(self):
        path = self.root / "verification" / "isolated_corpus.json"
        evidence = json.loads(path.read_text())
        evidence["runs"][0]["program"] = "999_not_in_the_corpus.json"
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True))
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_corpus", self.failing_checks())

    def test_reduced_corpus_totals_are_rejected(self):
        def mutate(payload):
            record = self.record_named(payload, "corpus")
            record["programs_checked"] = 2
            record["programs_expected"] = 2

        self.edit_verification(mutate)
        self.assertEqual(self.run_checker(), 1)
        failing = self.failing_checks()
        self.assertTrue(
            "verification_corpus" in failing or "verification_corpus_totals" in failing,
            failing,
        )

    def test_a_drifted_export_record_is_rejected(self):
        def mutate(payload):
            payload["export"]["sha256"] = "0" * 64

        self.edit_verification(mutate)
        self.assertEqual(self.run_checker(), 1)
        self.assertIn("verification_export", self.failing_checks())


if __name__ == "__main__":
    unittest.main()
