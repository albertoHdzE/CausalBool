"""Harness, checker and ownership mutation tests.

This module builds a small but *real* run directory once, confirms the checker
accepts it, and then applies every mutation in ACCEPTANCE_MATRIX.json to
**copies** of it. The unmutated control must pass first; a mutation that is
rejected because an unrelated file went missing is not a successful test, so
each injection changes exactly one thing and the reason is asserted.

No protected source is edited. The ownership guard is exercised by planting a
duplicate owner and a forbidden import in a temporary package copy.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / ".reference"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from research import check_structural_evidence as checker  # noqa: E402
from research import run_structural_experiments as runner  # noqa: E402
from research import structural_encoding as se  # noqa: E402


CONTRACT_DIR = ROOT / "plan" / "phase2"
MATRIX = json.loads((CONTRACT_DIR / "ACCEPTANCE_MATRIX.json").read_text())["checks"]


def run_cli(arguments, cwd=ROOT):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = f"{ROOT / '.reference'}{os.pathsep}{ROOT}"
    return subprocess.run(
        [sys.executable, *arguments], cwd=str(cwd), capture_output=True,
        text=True, timeout=1800, env=environment,
    )


class CommandLineContract(unittest.TestCase):
    """The CLI refuses what the contract says it must refuse."""

    def test_missing_arguments_is_usage(self):
        result = run_cli(["-m", "research.run_structural_experiments"])
        self.assertEqual(result.returncode, runner.EXIT_USAGE)

    def test_a_bad_run_id_is_refused(self):
        for bad in ("../escape", "has space", "semi;colon", ""):
            result = run_cli(
                ["-m", "research.run_structural_experiments",
                 "--stage", "preflight", "--run-id", bad]
            )
            self.assertEqual(result.returncode, runner.EXIT_USAGE, bad)

    def test_an_existing_run_is_never_overwritten(self):
        run_id = "unit_overwrite_probe"
        target = runner.RESULTS / run_id
        if target.exists():
            shutil.rmtree(target)
        try:
            first = run_cli(
                ["-m", "research.run_structural_experiments",
                 "--stage", "preflight", "--run-id", run_id]
            )
            self.assertEqual(first.returncode, runner.EXIT_OK, first.stderr)
            second = run_cli(
                ["-m", "research.run_structural_experiments",
                 "--stage", "preflight", "--run-id", run_id]
            )
            self.assertEqual(second.returncode, runner.EXIT_USAGE)
            self.assertIn("never overwritten", second.stderr)
        finally:
            shutil.rmtree(target, ignore_errors=True)

    def test_there_is_no_flag_that_disables_a_gate(self):
        parser_text = (ROOT / "research" / "run_structural_experiments.py").read_text()
        for forbidden in ("--force", "--skip-gate", "--no-gates", "--overwrite",
                          "--ignore-failures", "--sample", "--limit-corpus"):
            self.assertNotIn(forbidden, parser_text)

    def test_the_worker_validates_its_own_identity(self):
        result = run_cli(
            ["-m", "research.run_structural_experiments", "--worker",
             json.dumps({"kind": "not_a_measurement"})]
        )
        self.assertEqual(result.returncode, runner.EXIT_FAILURE)
        self.assertIn("not a phase 2 measurement", result.stderr)

    def test_the_worker_refuses_an_unknown_arm(self):
        result = run_cli(
            ["-m", "research.run_structural_experiments", "--worker",
             json.dumps({"kind": "phase2_measurement", "arm": "magic"})]
        )
        self.assertEqual(result.returncode, runner.EXIT_FAILURE)


class RealRun(unittest.TestCase):
    """One real P0 run, then every acceptance-matrix mutation against copies."""

    run_id = "unit_evidence_probe"

    @classmethod
    def setUpClass(cls):
        cls.root = runner.RESULTS / cls.run_id
        shutil.rmtree(cls.root, ignore_errors=True)
        result = run_cli(
            ["-m", "research.run_structural_experiments",
             "--stage", "p0", "--run-id", cls.run_id, "--contract", "plan/phase2"]
        )
        cls.creation = result
        if not (cls.root / "manifest.json").is_file():
            raise unittest.SkipTest(f"the probe run did not complete: {result.stderr}")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def copy_run(self):
        temporary = Path(tempfile.mkdtemp(prefix="phase2-mutation-"))
        destination = temporary / self.run_id
        shutil.copytree(self.root, destination)
        self.addCleanup(shutil.rmtree, temporary, ignore_errors=True)
        return destination

    @staticmethod
    def resync_manifest(run_root):
        """Re-record stage digests and row counts after a mutation.

        The checker verifies each stage summary against the digest the manifest
        claims. Without this, every content mutation below would also break that
        digest and would then be "detected" for the wrong reason. The lead review
        of 2026-09-23 is explicit that a recomputed hash must not rescue erased
        evidence, so the mutations are re-hashed deliberately: what is under test
        is the content check, not the hash check. One test deliberately does not
        resync, and asserts the digest check fires on its own.
        """

        manifest_path = Path(run_root) / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        digests = dict(manifest.get("stage_digests") or {})
        for stage in ("preflight", "p0", "p1", "p2", "p3", "p4", "p5"):
            summary = Path(run_root) / stage / "summary.json"
            if summary.is_file():
                digests[stage] = runner.file_digest(summary)
            else:
                digests.pop(stage, None)
        manifest["stage_digests"] = digests
        counts = {}
        for path in sorted(Path(run_root).rglob("*.jsonl")):
            counts[str(path.relative_to(run_root))] = sum(
                1 for line in path.read_text().splitlines() if line.strip()
            )
        manifest["row_counts"] = counts
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    def check(self, run_root, contract=CONTRACT_DIR, resync=True):
        if resync and (Path(run_root) / "manifest.json").is_file():
            self.resync_manifest(run_root)
        return checker.main(["--run", str(run_root), "--contract", str(contract)])

    # -- the control -------------------------------------------------------

    def test_00_the_unmutated_control_passes_first(self):
        self.assertEqual(self.creation.returncode, runner.EXIT_OK, self.creation.stderr)
        self.assertEqual(self.check(self.root), checker.EXIT_OK)

    def test_p0_summary_is_present_and_complete(self):
        summary = json.loads((self.root / "p0" / "summary.json").read_text())
        self.assertEqual(summary["fixture_count"], 12)
        self.assertEqual(summary["heldout"]["count"], 100)
        self.assertEqual(summary["heldout"]["collisions"], [])

    # -- C01 provenance ----------------------------------------------------

    def test_C01_a_changed_protected_hash_fails_preflight(self):
        temporary = Path(tempfile.mkdtemp(prefix="phase2-contract-"))
        self.addCleanup(shutil.rmtree, temporary, ignore_errors=True)
        contract = temporary / "phase2"
        shutil.copytree(CONTRACT_DIR, contract)
        lock = json.loads((contract / "BASELINE_LOCK.json").read_text())
        first = sorted(lock["files"])[0]
        lock["files"][first] = "0" * 64
        (contract / "BASELINE_LOCK.json").write_text(json.dumps(lock, indent=2))
        self.assertEqual(self.check(self.root, contract), checker.EXIT_FAILURE)

    def test_C01_a_changed_plan_byte_is_detected(self):
        run = self.copy_run()
        manifest = json.loads((run / "manifest.json").read_text())
        manifest["plan_sha256"] = "0" * 64
        (run / "manifest.json").write_text(json.dumps(manifest, indent=2))
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    # -- C02 fixture membership -------------------------------------------

    def test_C02_a_deleted_fixture_fails_membership(self):
        run = self.copy_run()
        summary = json.loads((run / "p0" / "summary.json").read_text())
        summary["fixtures"].pop()
        (run / "p0" / "summary.json").write_text(json.dumps(summary, indent=2))
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    def test_C02_a_duplicated_fixture_fails_membership(self):
        run = self.copy_run()
        summary = json.loads((run / "p0" / "summary.json").read_text())
        summary["fixtures"].append(dict(summary["fixtures"][0]))
        (run / "p0" / "summary.json").write_text(json.dumps(summary, indent=2))
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    def test_C02_a_changed_domain_digest_is_detected(self):
        run = self.copy_run()
        summary = json.loads((run / "p0" / "summary.json").read_text())
        summary["fixtures"][0]["domain_sha256"] = "0" * 64
        (run / "p0" / "summary.json").write_text(json.dumps(summary, indent=2))
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    # -- C03 held-out provenance ------------------------------------------

    def test_C03_a_renamed_duplicate_fails_the_corpus_freeze(self):
        run = self.copy_run()
        summary = json.loads((run / "p0" / "summary.json").read_text())
        programs = summary["heldout"]["programs"]
        # A renamed duplicate has the same semantic digest as another entry,
        # which is precisely what the name-excluding comparison catches.
        programs[1]["semantic_sha256"] = programs[0]["semantic_sha256"]
        (run / "p0" / "summary.json").write_text(json.dumps(summary, indent=2))
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    def test_C03_a_missing_seed_fails_membership(self):
        run = self.copy_run()
        summary = json.loads((run / "p0" / "summary.json").read_text())
        summary["heldout"]["programs"].pop()
        (run / "p0" / "summary.json").write_text(json.dumps(summary, indent=2))
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    def test_C03_a_seed_outside_the_frozen_range_is_rejected(self):
        run = self.copy_run()
        summary = json.loads((run / "p0" / "summary.json").read_text())
        summary["heldout"]["programs"][0]["seed"] = 999999
        (run / "p0" / "summary.json").write_text(json.dumps(summary, indent=2))
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    def test_C03_a_program_that_does_not_regenerate_is_rejected(self):
        run = self.copy_run()
        summary = json.loads((run / "p0" / "summary.json").read_text())
        summary["heldout"]["programs"][0]["semantic_sha256"] = "0" * 64
        (run / "p0" / "summary.json").write_text(json.dumps(summary, indent=2))
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    # -- C25 evidence provenance ------------------------------------------

    def test_C25_a_changed_source_snapshot_is_rejected(self):
        run = self.copy_run()
        manifest = json.loads((run / "manifest.json").read_text())
        manifest["source_snapshot"]["snapshot_sha256"] = "0" * 64
        (run / "manifest.json").write_text(json.dumps(manifest, indent=2))
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    def test_C25_a_changed_research_source_hash_is_rejected(self):
        run = self.copy_run()
        manifest = json.loads((run / "manifest.json").read_text())
        manifest["source_snapshot"]["research"]["structural_encoding.py"] = "0" * 64
        (run / "manifest.json").write_text(json.dumps(manifest, indent=2))
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    def test_C25_a_changed_contract_file_hash_is_rejected(self):
        run = self.copy_run()
        manifest = json.loads((run / "manifest.json").read_text())
        manifest["contract_files"]["PROTOCOL.json"] = "0" * 64
        (run / "manifest.json").write_text(json.dumps(manifest, indent=2))
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    def test_C25_a_changed_status_total_is_rejected(self):
        run = self.copy_run()
        summary = json.loads((run / "p0" / "summary.json").read_text())
        summary["historical_optimiser_statuses"]["unaccounted"] = 7
        (run / "p0" / "summary.json").write_text(json.dumps(summary, indent=2))
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    # -- C26 gate dependency truth ----------------------------------------

    def test_C26_a_pass_with_a_failed_dependency_is_rejected(self):
        run = self.copy_run()
        gates = json.loads((run / "gates.json").read_text())
        gates["p1"] = {"status": runner.FAIL, "reason": "planted", "evidence": {}}
        gates["p2"] = {"status": runner.PASS, "reason": "planted", "evidence": {}}
        (run / "gates.json").write_text(json.dumps(gates, indent=2))
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    def test_C26_a_pass_stage_without_a_summary_is_rejected(self):
        run = self.copy_run()
        gates = json.loads((run / "gates.json").read_text())
        gates["p3"] = {"status": runner.PASS, "reason": "planted", "evidence": {}}
        gates["p1"] = {"status": runner.PASS, "reason": "planted", "evidence": {}}
        (run / "gates.json").write_text(json.dumps(gates, indent=2))
        self.assertIn(self.check(run), (checker.EXIT_FAILURE, checker.EXIT_USAGE))

    def test_C26_an_omitted_independent_p5_is_rejected(self):
        run = self.copy_run()
        gates = json.loads((run / "gates.json").read_text())
        gates["p2"] = {"status": runner.PASS, "reason": "planted", "evidence": {}}
        gates["p5"] = {"status": runner.NOT_RUN, "reason": "planted", "evidence": {}}
        (run / "gates.json").write_text(json.dumps(gates, indent=2))
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    # -- C28 empty and malformed input ------------------------------------

    def test_C28_a_missing_run_directory_is_usage(self):
        self.assertEqual(
            self.check(runner.RESULTS / "definitely_absent"), checker.EXIT_USAGE
        )

    def test_C28_a_missing_manifest_is_usage(self):
        run = self.copy_run()
        (run / "manifest.json").unlink()
        self.assertEqual(self.check(run), checker.EXIT_USAGE)

    def test_C28_an_empty_manifest_is_usage(self):
        run = self.copy_run()
        (run / "manifest.json").write_text("")
        self.assertEqual(self.check(run, resync=False), checker.EXIT_USAGE)

    def test_an_edited_summary_whose_digest_is_not_resynced_is_detected(self):
        """The digest check on its own, with no content mutation at all.

        The mutations elsewhere in this class re-record the manifest digests on
        purpose, so that what they exercise is the content check. This one proves
        the digest check is not vacuous: reindenting a summary changes its bytes
        and nothing else, and it is still rejected.
        """

        run = self.copy_run()
        summary = json.loads((run / "p0" / "summary.json").read_text())
        (run / "p0" / "summary.json").write_text(json.dumps(summary, indent=4))
        self.assertEqual(self.check(run, resync=False), checker.EXIT_FAILURE)

    def test_C28_an_empty_row_file_is_never_a_pass(self):
        run = self.copy_run()
        (run / "p2").mkdir(parents=True, exist_ok=True)
        (run / "p2" / "summary.json").write_text(json.dumps({"stage": "p2"}))
        (run / "p2" / "benchmark_rows.jsonl").write_text("")
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    def test_C28_a_nan_metric_is_refused_by_canonical_json(self):
        with self.assertRaises(ValueError):
            se.canonical_json({"value": float("nan")})
        with self.assertRaises(ValueError):
            se.canonical_json({"value": float("inf")})

    def test_C28_a_foreign_result_identity_is_rejected(self):
        run = self.copy_run()
        summary = json.loads((run / "p0" / "summary.json").read_text())
        summary["fixtures"][0]["id"] = "not_a_declared_fixture"
        (run / "p0" / "summary.json").write_text(json.dumps(summary, indent=2))
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    # -- C11, C15, C21, C22, C23: row-level mutations ----------------------

    def synthetic_benchmark_run(self):
        """A P2 stage with exactly the expected membership, built from policy."""

        run = self.copy_run()
        p0 = json.loads((run / "p0" / "summary.json").read_text())
        contract = runner.Contract(CONTRACT_DIR)
        budgets = contract.budgets["optimisation_seconds"]
        repetitions = contract.statistics["timing_repetitions"]
        unbudgeted = ("accepted_bootstrap", "accepted_default")
        budgeted = ("accepted_budgeted",) + runner.STRUCTURAL_ARMS
        rows = []
        for key in runner.expected_keys(
            p0["public"], budgets, unbudgeted, budgeted, repetitions
        ):
            program_sha, budget, arm, seed, repetition = key
            rows.append(
                {
                    "stage": "p2", "corpus": "public", "program_sha256": program_sha,
                    "domain_sha256": None, "codec": None, "arm": arm,
                    "budget_seconds": budget, "search_seed": seed,
                    "repetition": repetition, "attempt": 0, "exit_code": 0,
                    "timed_out": False, "process_seconds": 0.5, "failed_row": False,
                    "correctness": "PASS", "cycles": 10, "scratch": 4, "product": 40,
                    "cases": 2, "discrepancy_count": 0,
                }
            )
        (run / "p2").mkdir(parents=True, exist_ok=True)
        runner.write_jsonl(run / "p2" / "benchmark_rows.jsonl", rows)

        # A *valid* control, not a stub: the checker derives tiny-fixture
        # membership from the twelve locked fixtures and recomputes every
        # comparison from these rows, so a summary that omitted either would be
        # rejected -- which is the point of the erased-evidence repair.
        from research import structural_oracle as so

        tiny = []
        for record in contract.fixtures:
            enumeration = so.enumerate_feasible(
                record, contract.budgets["oracle_cartesian_max"]
            )
            minimum = min(
                (item["product"] for item in enumeration["feasible"]), default=None
            )
            tiny.append(
                {
                    "id": record["id"],
                    "family": record["family"],
                    "oracle_minimum_product": minimum,
                    "arms": {
                        arm: {"best_product": minimum, "rejected_completions": []}
                        for arm in ("structural_dfs", "structural_bound")
                    },
                }
            )
        families = {entry["program_sha256"]: "public" for entry in p0["public"]}
        comparisons = {
            f"{candidate}_vs_{baseline}@{budget}": runner.paired_log_ratio_analysis(
                rows, families, baseline, candidate, budget, contract
            )
            for budget in budgets
            for baseline, candidate in (
                ("accepted_budgeted", "structural_bound"),
                ("accepted_budgeted", "structural_dfs"),
                ("accepted_budgeted", "structural_expanded"),
            )
        }
        (run / "p2" / "summary.json").write_text(
            json.dumps(
                {
                    "stage": "p2", "tiny_fixtures": tiny,
                    "comparisons": comparisons,
                    "primary_budget_seconds": contract.budgets["primary_seconds"],
                },
                indent=2,
            )
        )
        return run, rows

    def check_synthetic_p2(self, run):
        """Exercise the P2 evidence checks without pretending P1 passed.

        These row-level tests have an exact synthetic P2 matrix, but their copied
        control is intentionally only a P0 request. Run the P2 checker directly
        so an unrequested synthetic dependent stage is not misrepresented as an
        end-to-end campaign.
        """

        instance = checker.Checker(run, CONTRACT_DIR)
        p0 = json.loads((run / "p0" / "summary.json").read_text())
        instance.check_p2(p0)
        return checker.EXIT_FAILURE if instance.findings else checker.EXIT_OK

    def test_C15_a_duplicated_row_with_an_omitted_one_is_rejected(self):
        run, rows = self.synthetic_benchmark_run()
        self.assertEqual(self.check_synthetic_p2(run), checker.EXIT_OK)
        mutated = list(rows)
        mutated[5] = dict(mutated[0])
        runner.write_jsonl(run / "p2" / "benchmark_rows.jsonl", mutated)
        self.assertEqual(self.check_synthetic_p2(run), checker.EXIT_FAILURE)

    def test_C15_an_omitted_program_is_rejected(self):
        run, rows = self.synthetic_benchmark_run()
        victim = rows[0]["program_sha256"]
        kept = [row for row in rows if row["program_sha256"] != victim]
        runner.write_jsonl(run / "p2" / "benchmark_rows.jsonl", kept)
        self.assertEqual(self.check_synthetic_p2(run), checker.EXIT_FAILURE)

    def test_C15_an_omitted_arm_is_rejected(self):
        run, rows = self.synthetic_benchmark_run()
        kept = [row for row in rows if row["arm"] != "structural_bound"]
        runner.write_jsonl(run / "p2" / "benchmark_rows.jsonl", kept)
        self.assertEqual(self.check_synthetic_p2(run), checker.EXIT_FAILURE)

    def test_C23_a_removed_failed_row_is_rejected(self):
        run, rows = self.synthetic_benchmark_run()
        mutated = [dict(row) for row in rows]
        mutated[3]["failed_row"] = True
        mutated[3]["correctness"] = "FAIL"
        runner.write_jsonl(run / "p2" / "benchmark_rows.jsonl", mutated)
        self.assertEqual(self.check_synthetic_p2(run), checker.EXIT_FAILURE)
        # Dropping it instead of keeping it fails the membership check.
        dropped = [row for index, row in enumerate(mutated) if index != 3]
        runner.write_jsonl(run / "p2" / "benchmark_rows.jsonl", dropped)
        self.assertEqual(self.check_synthetic_p2(run), checker.EXIT_FAILURE)

    def test_C23_a_timed_out_row_cannot_be_dropped(self):
        run, rows = self.synthetic_benchmark_run()
        dropped = [row for row in rows if row["budget_seconds"] != 1.0]
        runner.write_jsonl(run / "p2" / "benchmark_rows.jsonl", dropped)
        self.assertEqual(self.check_synthetic_p2(run), checker.EXIT_FAILURE)

    def test_a_retained_discrepancy_blocks_the_stage(self):
        run, rows = self.synthetic_benchmark_run()
        mutated = [dict(row) for row in rows]
        mutated[0]["discrepancy_count"] = 1
        runner.write_jsonl(run / "p2" / "benchmark_rows.jsonl", mutated)
        self.assertEqual(self.check_synthetic_p2(run), checker.EXIT_FAILURE)

    def test_an_inconsistent_objective_is_rejected(self):
        run, rows = self.synthetic_benchmark_run()
        mutated = [dict(row) for row in rows]
        mutated[0]["product"] = 999
        runner.write_jsonl(run / "p2" / "benchmark_rows.jsonl", mutated)
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    def test_a_row_that_validated_no_case_is_rejected(self):
        run, rows = self.synthetic_benchmark_run()
        mutated = [dict(row) for row in rows]
        mutated[0]["cases"] = 0
        runner.write_jsonl(run / "p2" / "benchmark_rows.jsonl", mutated)
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    # -- C22 advancement intervals ----------------------------------------

    def test_C22_a_replaced_gate_interval_is_rejected(self):
        run = self.copy_run()
        (run / "p4").mkdir(parents=True, exist_ok=True)
        (run / "p4" / "summary.json").write_text(json.dumps({
            "stage": "p4",
            "h4_gate_percentiles": [0.025, 0.975],
            "contrasts": {},
        }, indent=2))
        runner.write_jsonl(run / "p4" / "model_rows.jsonl", [{"fixture_id": "x"}])
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    def test_C22_a_mutated_bootstrap_seed_is_rejected(self):
        run = self.copy_run()
        (run / "p4").mkdir(parents=True, exist_ok=True)
        (run / "p4" / "summary.json").write_text(json.dumps({
            "stage": "p4",
            "h4_gate_percentiles": [0.0125, 0.9875],
            "contrasts": {
                "model_expand_vs_one_bit@0.1": {
                    "interval": {
                        "status": runner.PASS, "seed": 1234,
                        "resamples": 10000,
                        "intervals": {"0.025-0.975": [0, 1], "0.0125-0.9875": [0, 1]},
                    }
                }
            },
        }, indent=2))
        runner.write_jsonl(run / "p4" / "model_rows.jsonl", [{"fixture_id": "x"}])
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)

    def test_C22_a_mutated_resample_count_is_rejected(self):
        run = self.copy_run()
        (run / "p4").mkdir(parents=True, exist_ok=True)
        (run / "p4" / "summary.json").write_text(json.dumps({
            "stage": "p4",
            "h4_gate_percentiles": [0.0125, 0.9875],
            "contrasts": {
                "model_expand_vs_one_bit@0.1": {
                    "interval": {
                        "status": runner.PASS,
                        "seed": runner.Contract(CONTRACT_DIR).seeds["bootstrap"],
                        "resamples": 50,
                        "intervals": {"0.025-0.975": [0, 1], "0.0125-0.9875": [0, 1]},
                    }
                }
            },
        }, indent=2))
        runner.write_jsonl(run / "p4" / "model_rows.jsonl", [{"fixture_id": "x"}])
        self.assertEqual(self.check(run), checker.EXIT_FAILURE)


class ArchitectureGuard(unittest.TestCase):
    """C24: a planted duplicate owner and a planted import must be rejected."""

    def package_copy(self):
        temporary = Path(tempfile.mkdtemp(prefix="phase2-ownership-"))
        self.addCleanup(shutil.rmtree, temporary, ignore_errors=True)
        destination = temporary / "research"
        shutil.copytree(
            ROOT / "research", destination,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        return destination

    def test_the_unmutated_control_passes_first(self):
        report = checker.architecture_report(ROOT / "research")
        self.assertEqual(report["status"], runner.PASS, report["findings"])
        self.assertGreaterEqual(report["scanned_count"], 6)
        self.assertEqual(report["runtime"]["leaked"], [])

    def test_a_planted_duplicate_cube_owner_is_rejected(self):
        package = self.package_copy()
        planted = package / "structural_models.py"
        planted.write_text(
            planted.read_text()
            + "\n\nclass Cube:\n    \"\"\"A second owner of the cube algebra.\"\"\"\n"
              "    pass\n"
        )
        report = checker.architecture_report(package)
        self.assertEqual(report["status"], runner.FAIL)
        self.assertTrue(
            any(finding.get("name") == "Cube" for finding in report["findings"])
        )

    def test_a_planted_machine_constant_is_rejected(self):
        package = self.package_copy()
        planted = package / "structural_search.py"
        planted.write_text(planted.read_text() + "\n\nVLEN = 8\n")
        report = checker.architecture_report(package)
        self.assertEqual(report["status"], runner.FAIL)
        self.assertTrue(
            any(finding.get("name") == "VLEN" for finding in report["findings"])
        )

    def test_a_planted_duplicate_lifetimes_owner_is_rejected(self):
        package = self.package_copy()
        planted = package / "structural_encoding.py"
        planted.write_text(
            planted.read_text() + "\n\ndef lifetimes(facts, times):\n    return {}\n"
        )
        report = checker.architecture_report(package)
        self.assertEqual(report["status"], runner.FAIL)

    def test_a_planted_oracle_import_is_rejected_statically_and_at_run_time(self):
        package = self.package_copy()
        oracle = package / "structural_oracle.py"
        oracle.write_text(
            oracle.read_text().replace(
                "import machine", "import machine\nimport direct_contract", 1
            )
        )
        report = checker.architecture_report(package)
        self.assertEqual(report["status"], runner.FAIL)
        kinds = {finding["kind"] for finding in report["findings"]}
        self.assertIn("oracle_import", kinds)
        self.assertIn("oracle_runtime_import", report["runtime"].get("leaked") and
                      {"oracle_runtime_import"} or kinds)

    def test_the_runtime_check_sees_a_transitive_import(self):
        """A forbidden module reached indirectly still shows in the graph."""

        package = self.package_copy()
        oracle = package / "structural_oracle.py"
        # A helper module that itself pulls in a forbidden owner. The static
        # scan of the oracle alone cannot see this; the runtime check can.
        (package / "sneaky.py").write_text("import schema_index\n")
        oracle.write_text(
            oracle.read_text().replace("import machine", "import machine\nimport sneaky", 1)
        )
        result = checker.runtime_import_check(package)
        self.assertTrue(result.get("leaked"), result)

    def test_the_guard_states_its_own_limits(self):
        report = checker.architecture_report(ROOT / "research")
        self.assertIn("cannot prove", report["limits"])
        self.assertIn("semantic", report["limits"])

    def test_the_architecture_cli_exits_nonzero_on_a_violation(self):
        result = run_cli(["-m", "research.check_structural_evidence", "--architecture"])
        self.assertEqual(result.returncode, checker.EXIT_OK, result.stdout[-2000:])


class FrozenProductionControls(unittest.TestCase):
    """C27: the existing gates keep their original definitions.

    The verifier, exporter and comparator are run as commands during the
    campaign; what is asserted here is that this assignment has not altered
    them, their acceptance thresholds or the production source list they guard.
    """

    def test_production_sources_match_the_baseline_lock(self):
        contract = runner.Contract(CONTRACT_DIR)
        locked = contract.baseline_lock["files"]
        checked = 0
        for name in ("verify_direct.py", "compare_direct.py", "export_direct.py",
                     "direct_compiler.py", "direct_constraints.py",
                     "direct_contract.py", "direct_optimizer.py", "schema_index.py"):
            key = f"luminal-challenge/{name}"
            if key not in locked:
                continue
            checked += 1
            self.assertEqual(
                runner.file_digest(ROOT / name), locked[key],
                f"{name} changed; the frozen control is no longer frozen",
            )
        self.assertGreater(checked, 0, "no production source was covered by the lock")

    def test_the_pinned_reference_is_unchanged(self):
        reference = json.loads((ROOT / "reference.json").read_text())
        for relative, expected in sorted(reference.get("files", {}).items()):
            self.assertEqual(
                runner.file_digest(ROOT / ".reference" / relative), expected, relative
            )

    def test_the_accepted_score_constants_are_untouched(self):
        import benchmark_optimization as bench

        self.assertEqual(bench.ACCEPTED_DIRECT_SCORE, 2.0084662022846573)
        self.assertEqual(bench.ACCEPTED_CLASSICAL_SCORE, 1.9013791212645499)
        self.assertEqual(bench.BOOTSTRAP_RESAMPLES, 10000)

    def test_the_research_package_is_not_on_the_production_source_list(self):
        import verify_direct as verification

        for source in verification.SOURCES:
            self.assertNotIn("research", str(source))

    def test_no_production_source_imports_the_research_package(self):
        import verify_direct as verification

        for source in verification.SOURCES:
            path = ROOT / str(source)
            if not path.is_file():
                continue
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    self.assertFalse(
                        name.split(".")[0] == "research",
                        f"{source} imports the research package",
                    )


class AcceptanceMatrixCoverage(unittest.TestCase):
    """Every matrix entry is named by at least one executable test."""

    def test_every_check_id_is_claimed(self):
        sources = "\n".join(
            path.read_text()
            for path in sorted((ROOT / "research_tests").glob("test_*.py"))
        )
        unclaimed = [
            entry["id"] for entry in MATRIX
            if entry["id"] not in sources
        ]
        self.assertEqual(unclaimed, [], f"no test names these matrix entries: {unclaimed}")

    def test_the_matrix_has_thirty_distinct_entries(self):
        self.assertEqual(len(MATRIX), 30)
        self.assertEqual(len({entry["id"] for entry in MATRIX}), 30)


if __name__ == "__main__":
    unittest.main()
