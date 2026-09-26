"""Targeted regression tests for the frozen recovery policy plumbing."""
from __future__ import annotations

from pathlib import Path
import json
import shutil
import tempfile
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / ".reference"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from research import physical_probes  # noqa: E402
from research import run_structural_experiments as runner  # noqa: E402
from research import check_structural_evidence as checker_module  # noqa: E402
from research import structural_encoding as se  # noqa: E402
from research import structural_oracle as oracle  # noqa: E402
import machine  # noqa: E402


class RecoveryPolicyTests(unittest.TestCase):
    def test_proposal_order_is_alternative_outer_and_time_then_producer(self):
        contract = runner.Contract(ROOT / "plan/phase2")
        record = next(item for item in contract.fixtures if item.get("incumbent"))
        domain = runner.fixture_domain(record)
        proposals = list(physical_probes.proposals(domain))
        fields = []
        for op_id in sorted(domain.time_domains):
            origin = domain.incumbent_times[op_id]
            alternatives = [v for v in domain.time_domains[op_id] if v != origin]
            fields.append(("time", str(op_id), alternatives))
        for name in sorted(domain.address_domains, key=lambda n: domain.facts.producers[n]):
            origin = domain.incumbent_addresses[name]
            alternatives = [v for v in domain.address_domains[name] if v != origin]
            fields.append(("address", name, alternatives))
        expected = []
        for ordinal in range(max(len(values) for _, _, values in fields)):
            expected.extend((kind, name, ordinal, values[ordinal])
                            for kind, name, values in fields if ordinal < len(values))
        self.assertEqual(proposals, expected)

    def test_amendment_is_exactly_the_lead_pinned_policy(self):
        loaded = runner.load_amendment(Path("plan/phase2_recovery/AMENDMENT.json"))
        self.assertEqual(loaded["id"], "luminal-phase2-recovery-1.0")
        with self.assertRaises(runner.StageBlocked):
            runner.load_amendment(Path("plan/phase2/PROTOCOL.json"))

    def test_checker_rejects_mismatched_amendment_and_import_policy(self):
        amendment = runner.load_amendment(Path("plan/phase2_recovery/AMENDMENT.json"))
        tmp = Path(tempfile.mkdtemp(prefix="amendment-policy-mutation-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        checker = checker_module.Checker(tmp, ROOT / "plan/phase2", amendment)
        manifest = {"amendment_files": amendment["files"],
                    "amendment_policy": {"forged.json": "0" * 64},
                    "cli_request": {"amendment_id": amendment["id"]}}
        checker.check_amendment(manifest)
        self.assertIn("provenance.amendment_policy", {f["check"] for f in checker.findings})
        prior = tmp / "prior"
        (prior / "p0").mkdir(parents=True)
        (prior / "p0/summary.json").write_text("{}\n")
        (prior / "manifest.json").write_text("{}\n")
        imported = {"imported_dependencies": {"p0": {
            "run": str(prior), "summary_sha256": runner.file_digest(prior / "p0/summary.json"),
            "manifest_sha256": runner.file_digest(prior / "manifest.json"),
            "derived_verdict": runner.PASS, "checker_exit_code": 0,
            "checker_report_sha256": "a" * 64,
            "amendment_files": {name: runner.file_digest(ROOT / name)
                                for name in runner.AMENDMENT_FILES}}},
            "amendment_policy": {"forged.json": "0" * 64}}
        imported_checker = checker_module.Checker(tmp, ROOT / "plan/phase2", amendment)
        imported_checker.check_imported_links(imported)
        self.assertIn("imports.amendment_policy",
                      {f["check"] for f in imported_checker.findings})

    def test_amended_p2_membership_is_1800_and_classical_is_unbudgeted(self):
        contract = runner.Contract(ROOT / "plan/phase2")
        programs = [{"program_sha256": f"p{i}"} for i in range(8)]
        rows = runner.expected_keys(programs, contract.budgets["optimisation_seconds"],
                                    ("accepted_bootstrap", "accepted_default", "classical"),
                                    ("accepted_budgeted",) + runner.STRUCTURAL_ARMS,
                                    contract.statistics["timing_repetitions"])
        self.assertEqual(len(rows), 1800)
        self.assertEqual(sum(row[1] is None and row[2] == "classical" for row in rows), 120)
        self.assertFalse(any(row[1] is not None and row[2] == "classical" for row in rows))

    def test_checker_rejects_missing_and_budgeted_classical_rows(self):
        contract = runner.Contract(ROOT / "plan/phase2")
        amendment = runner.load_amendment(Path("plan/phase2_recovery/AMENDMENT.json"))
        program = {"program_sha256": "one-program", "path": "unused"}
        expected = runner.expected_keys(
            [program], contract.budgets["optimisation_seconds"],
            ("accepted_bootstrap", "accepted_default", "classical"),
            ("accepted_budgeted",) + runner.STRUCTURAL_ARMS,
            contract.statistics["timing_repetitions"],
        )
        rows = [{"program_sha256": key[0], "budget_seconds": key[1], "arm": key[2],
                 "search_seed": key[3], "repetition": key[4], "cycles": 2,
                 "scratch": 2, "product": 4, "cases": 1}
                for key in expected]
        tmp = Path(tempfile.mkdtemp(prefix="classical-membership-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        checker = checker_module.Checker(tmp, ROOT / "plan/phase2", amendment)
        no_classical = [row for row in rows if row["arm"] != "classical"]
        checker.check_benchmark_rows("p2", no_classical, [program])
        self.assertIn("p2.membership", {f["check"] for f in checker.findings})
        checker = checker_module.Checker(tmp, ROOT / "plan/phase2", amendment)
        repeated = list(rows)
        repeated.append(dict(next(row for row in rows if row["arm"] == "classical"),
                             budget_seconds=contract.budgets["optimisation_seconds"][0]))
        checker.check_benchmark_rows("p2", repeated, [program])
        self.assertIn("p2.membership", {f["check"] for f in checker.findings})

    def test_no_flag_keeps_legacy_measurement_membership_and_cli_policy(self):
        contract = runner.Contract(ROOT / "plan/phase2")
        programs = [{"program_sha256": f"p{i}"} for i in range(8)]
        rows = runner.expected_keys(programs, contract.budgets["optimisation_seconds"],
                                    ("accepted_bootstrap", "accepted_default"),
                                    ("accepted_budgeted",) + runner.STRUCTURAL_ARMS,
                                    contract.statistics["timing_repetitions"])
        self.assertEqual(len(rows), 1680)
        args = runner.parse_args(["--stage", "p2", "--run-id", "compatibility_probe"])
        self.assertIsNone(args.amendment)
        with self.assertRaises(runner.StageBlocked):
            runner.run_measurement({"kind": "phase2_measurement", "arm": "classical"})

    def test_paired_quality_uses_matched_log_products_not_log_of_means(self):
        rows = []
        for repetition, (control, candidate) in enumerate(((100, 100), (400, 100))):
            rows.extend([
                {"arm": "accepted_budgeted", "budget_seconds": 0.1,
                 "program_sha256": "p", "repetition": repetition,
                 "search_seed": None, "product": control},
                {"arm": "structural_bound", "budget_seconds": 0.1,
                 "program_sha256": "p", "repetition": repetition,
                 "search_seed": None, "product": candidate},
            ])
        paired, counts = runner._paired_repetition_log_quality(
            rows, "accepted_budgeted", "structural_bound", 0.1
        )
        self.assertAlmostEqual(paired["p"], 0.6931471805599453)
        self.assertEqual(counts["p"], 2)
        means_log = __import__("math").log((100 + 400) / (100 + 100))
        self.assertAlmostEqual(means_log, 0.9162907318741551)
        self.assertNotAlmostEqual(paired["p"], means_log)

    def test_paired_quality_refuses_a_missing_technical_pair(self):
        rows = [
            {"arm": "accepted_budgeted", "budget_seconds": 0.1,
             "program_sha256": "p", "repetition": 0, "product": 10},
            {"arm": "structural_bound", "budget_seconds": 0.1,
             "program_sha256": "p", "repetition": 0, "product": 5},
            {"arm": "accepted_budgeted", "budget_seconds": 0.1,
             "program_sha256": "p", "repetition": 1, "product": 10},
        ]
        paired, _ = runner._paired_repetition_log_quality(
            rows, "accepted_budgeted", "structural_bound", 0.1
        )
        self.assertNotIn("p", paired)

    def test_recovery_primary_is_heldout_p5_at_frozen_budget_and_paired_log_endpoint(self):
        import math
        contract = runner.Contract(ROOT / "plan/phase2")
        budget = contract.budgets["primary_seconds"]
        rows = []
        def add(arm, row_budget, repetition, product):
            rows.append({"arm": arm, "budget_seconds": row_budget,
                         "program_sha256": "heldout-program", "repetition": repetition,
                         "product": product, "cycles": 10, "scratch": product / 10,
                         "compile_seconds": 0.1 + repetition, "process_seconds": 0.2 + repetition,
                         "peak_rss_bytes": 100, "failed_row": False})
        for current_budget in contract.budgets["optimisation_seconds"]:
            for repetition in range(contract.statistics["timing_repetitions"]):
                candidate_product = 100 if repetition < 2 else 100
                control_product = (100 if repetition == 0 else 400 if repetition == 1 else 100)
                add("structural_bound", current_budget, repetition, candidate_product)
                add("accepted_budgeted", current_budget, repetition, control_product)
            for arm in ("accepted_bootstrap", "accepted_default"):
                add(arm, None, 0, 100)
                add(arm, None, 1, 400)
        table = runner.build_recovery_comparison(
            {"heldout": rows}, {"heldout": {"heldout-program": "fam"}}, contract
        )
        primary = table["primary_h2"]
        self.assertEqual((primary["corpus"], primary["budget_seconds"], primary["control"]),
                         ("heldout", budget, "accepted_budgeted"))
        self.assertAlmostEqual(primary["analysis"]["per_program_log_ratio"]["heldout-program"],
                               math.log(4) / contract.statistics["timing_repetitions"])
        self.assertIn("mean paired log", primary["analysis"]["endpoint"])

    def test_p5_checker_rejects_forged_primary_budget_in_comparison_artifact(self):
        contract = runner.Contract(ROOT / "plan/phase2")
        amendment = runner.load_amendment(Path("plan/phase2_recovery/AMENDMENT.json"))
        rows_by_corpus = {}
        families_by_corpus = {}
        public_entries = []
        heldout_entries = []
        for corpus in ("public", "heldout"):
            program = f"{corpus}-program"
            families_by_corpus[corpus] = {program: "family"}
            if corpus == "public":
                public_entries.append({"program_sha256": program})
            else:
                heldout_entries.append({"program_sha256": program, "family": "family"})
            rows = []
            def add(arm, budget, repetition):
                product = 100 if arm == "structural_bound" or repetition == 0 else 400
                rows.append({"arm": arm, "budget_seconds": budget,
                             "program_sha256": program, "repetition": repetition,
                             "product": product, "cycles": 10, "scratch": product / 10,
                             "compile_seconds": 0.2, "process_seconds": 0.3,
                             "peak_rss_bytes": 1000, "failed_row": False})
            for budget in contract.budgets["optimisation_seconds"]:
                for repetition in range(contract.statistics["timing_repetitions"]):
                    add("structural_bound", budget, repetition)
                    add("accepted_budgeted", budget, repetition)
            for arm in ("accepted_default", "accepted_bootstrap"):
                for repetition in range(contract.statistics["timing_repetitions"]):
                    add(arm, None, repetition)
            rows_by_corpus[corpus] = rows
        expected = runner.build_recovery_comparison(rows_by_corpus, families_by_corpus, contract)
        forged = json.loads(json.dumps(expected))
        forged["primary_h2"]["budget_seconds"] = 1.0
        tmp = Path(tempfile.mkdtemp(prefix="comparison-primary-mutation-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "COMPARISON.md").write_text("Public and held-out programs are not pooled.\n")
        runner.write_json(tmp / "COMPARISON.json", forged)
        checker = checker_module.Checker(tmp, ROOT / "plan/phase2", amendment)
        summary = {"public": {"comparisons": {}}, "heldout": {"comparisons": {}},
                   "pooled": False, "model_arm": {"authorised": False}}
        with patch.object(checker, "load", side_effect=lambda rel: {
                "p5/summary.json": summary,
                "p5/public_rows.jsonl": rows_by_corpus["public"],
                "p5/heldout_rows.jsonl": rows_by_corpus["heldout"],
                "p2/summary.json": {},
                "COMPARISON.json": forged,
        }.get(rel)):
            with patch.object(checker, "check_benchmark_rows"), \
                 patch.object(checker, "check_intervals"), \
                 patch.object(checker, "recompute_comparisons"):
                checker.check_p5({"public": public_entries,
                                  "heldout": {"programs": heldout_entries}})
        self.assertIn("p5.comparison_matrix", {f["check"] for f in checker.findings})

    def test_p4_pairing_reuses_null_control_per_seed_and_rejects_missing_seed_rep(self):
        contract = runner.Contract(ROOT / "plan/phase2")
        record = next(item for item in contract.fixtures if item["id"] == "many_ready_1")
        repetitions = contract.statistics["timing_repetitions"]
        rows = []
        for repetition in range(repetitions):
            rows.append({"semantic_sha256": "sem", "fixture_id": record["id"],
                         "family": record["family"], "arm": "model_expand",
                         "budget_seconds": 0.1, "search_seed": None,
                         "repetition": repetition, "status": runner.PASS,
                         "counts": {"test_proposals": 0},
                         "best_test_product": 100})
            for seed in contract.seeds["search"]:
                rows.append({"semantic_sha256": "sem", "fixture_id": record["id"],
                             "family": record["family"], "arm": "uniform_bits",
                             "budget_seconds": 0.1, "search_seed": seed,
                             "repetition": repetition, "status": runner.PASS,
                             "counts": {"test_proposals": 0},
                             "best_test_product": 200 if repetition else 100})
        full = runner.p4_contrasts(rows, contract)
        contrast = full["contrasts"]["model_expand_vs_uniform_bits@0.1"]
        self.assertAlmostEqual(contrast["per_program_log_ratio"]["sem"],
                               sum(__import__("math").log((100 if i == 0 else 200) / 100)
                                   for i in range(repetitions)) / repetitions)
        rows = [row for row in rows if not (row["arm"] == "uniform_bits"
                                            and row["search_seed"] == contract.seeds["search"][0]
                                            and row["repetition"] == repetitions - 1)]
        missing = runner.p4_contrasts(rows, contract)
        self.assertEqual(missing["contrasts"]["model_expand_vs_uniform_bits@0.1"]["programs"], 0)

    def _physical_fixture(self):
        contract = runner.Contract(ROOT / "plan/phase2")
        record = next(item for item in contract.fixtures if item["id"] == "many_ready_1")
        domain = runner.fixture_domain(record)
        for index, (kind, field_id, _alt, value) in enumerate(physical_probes.proposals(domain)):
            times = dict(domain.incumbent_times)
            addresses = dict(domain.incumbent_addresses)
            if kind == "time":
                times[int(field_id)] = value
            else:
                addresses[field_id] = value
            candidate = __import__("direct_contract").compilation(domain.facts, times, addresses)
            try:
                machine.check_compilation(record["program"], candidate)
            except (machine.CompileError, machine.ProgramError):
                continue
            return record, domain, index
        self.fail("fixture has no machine-valid one-field physical neighbor")

    def test_physical_probe_deadline_during_cases_is_interrupted(self):
        record, domain, last_index = self._physical_fixture()
        clock = [0.0]
        original = machine.check_case
        def expires_after_case(*args):
            result = original(*args)
            clock[0] = 2.0
            return result
        with patch.object(physical_probes.time, "perf_counter", side_effect=lambda: clock[0]), \
             patch.object(machine, "check_case", side_effect=expires_after_case):
            rows, summary = physical_probes.run(domain, record["program"], last_index + 1,
                                                seconds=1.0, expected_program_sha256="p")
        self.assertEqual(rows[-1]["status"], "INTERRUPTED")
        self.assertEqual(rows[-1]["interrupted_phase"], "case_validation")
        self.assertEqual(summary["counts"]["INTERRUPTED"], 1)
        self.assertEqual(summary["distinct_complete"], 0)

    def test_physical_probe_deadline_during_roundtrip_is_interrupted(self):
        record, domain, last_index = self._physical_fixture()
        clock = [0.0]
        original = se.decode
        def expires_after_decode(*args, **kwargs):
            result = original(*args, **kwargs)
            clock[0] = 2.0
            return result
        with patch.object(physical_probes.time, "perf_counter", side_effect=lambda: clock[0]), \
             patch.object(se, "decode", side_effect=expires_after_decode):
            rows, summary = physical_probes.run(domain, record["program"], last_index + 1,
                                                seconds=1.0, expected_program_sha256="p")
        self.assertEqual(rows[-1]["status"], "INTERRUPTED")
        self.assertTrue(rows[-1]["interrupted_phase"].startswith("codec:"))
        self.assertEqual(summary["distinct_complete"], 0)

    def test_physical_probe_deadline_during_codec_case_check_is_interrupted(self):
        record, domain, last_index = self._physical_fixture()
        clock = [0.0]
        calls = [0]
        original = machine.check_case
        def expire_on_first_codec_case(*args, **kwargs):
            calls[0] += 1
            result = original(*args, **kwargs)
            if calls[0] == len(record["program"]["cases"]) + 1:
                clock[0] = 2.0
            return result
        with patch.object(physical_probes.time, "perf_counter", side_effect=lambda: clock[0]), \
             patch.object(machine, "check_case", side_effect=expire_on_first_codec_case):
            rows, summary = physical_probes.run(domain, record["program"], last_index + 1,
                                                seconds=1.0, expected_program_sha256="p")
        self.assertEqual(rows[-1]["status"], "INTERRUPTED")
        self.assertEqual(rows[-1]["interrupted_phase"], "codec:absolute:case_validation")
        self.assertEqual(rows[-1]["codec_counts"]["absolute"]["case_complete"], 1)
        self.assertEqual(summary["distinct_complete"], 0)

    def test_known_case_failure_beats_simultaneous_deadline(self):
        record, domain, last_index = self._physical_fixture()
        clock = [0.0]
        def error_after_expiry(*_args):
            clock[0] = 2.0
            raise machine.ProgramError("forced validation discrepancy")
        with patch.object(physical_probes.time, "perf_counter", side_effect=lambda: clock[0]), \
             patch.object(machine, "check_case", side_effect=error_after_expiry):
            rows, summary = physical_probes.run(domain, record["program"], last_index + 1,
                                                seconds=1.0, expected_program_sha256="p")
        self.assertEqual(rows[-1]["status"], "DISCREPANCY")
        self.assertEqual(summary["counts"]["DISCREPANCY"], 1)

    def test_p4_workers_return_fixture_identity_and_durable_journals(self):
        from research import structural_models as models
        amendment = runner.load_amendment(Path("plan/phase2_recovery/AMENDMENT.json"))
        contract = runner.Contract(ROOT / "plan/phase2")
        fixtures = ("chain_0", "many_ready_1")
        tmp = Path(tempfile.mkdtemp(prefix="p4-worker-smoke-"))
        harness = runner.Harness(tmp, timeout=30)
        rows = []
        for fixture_id in fixtures:
            for arm in models.MODEL_ARMS:
                seed = contract.seeds["search"][0] if arm == "uniform_bits" else None
                spec = {"kind": "phase2_model_measurement", "stage": "p4",
                        "corpus": "fixtures", "fixture_id": fixture_id,
                        "program_sha256": se.object_digest(next(
                            item["program"] for item in contract.fixtures if item["id"] == fixture_id
                        )),
                        "arm": arm, "budget_seconds": 0.01,
                        "search_seed": seed, "repetition": 0,
                        "contract": str(contract.directory),
                        "amendment_id": amendment["id"],
                        "amendment_files": amendment["files"]}
                row = harness.run(spec)
                rows.append(row)
                self.assertFalse(row["failed_row"], row.get("failure"))
                self.assertEqual(row["fixture_id"], fixture_id)
                self.assertIn(row.get("status"),
                              (runner.NOT_APPLICABLE, runner.INCONCLUSIVE, runner.PASS))
        self.assertEqual(len(runner.read_jsonl(tmp / "journals/p4_rows.jsonl")), 8)
        runner.write_jsonl(tmp / "commands.jsonl", harness.commands)
        runner.write_jsonl(tmp / "p4/model_rows.jsonl", rows)
        checker = checker_module.Checker(tmp, ROOT / "plan/phase2", amendment)
        checker.check_durable_journals(harness.commands)
        self.assertFalse(checker.findings, checker.findings)

    def test_crashed_worker_is_fsynced_and_missing_journal_row_is_detected(self):
        amendment = runner.load_amendment(Path("plan/phase2_recovery/AMENDMENT.json"))
        contract = runner.Contract(ROOT / "plan/phase2")
        fixture = next(item for item in contract.fixtures if item["id"] == "many_ready_1")
        spec = {"stage": "p4", "corpus": "fixtures", "fixture_id": fixture["id"],
                "program_sha256": se.object_digest(fixture["program"]),
                "arm": "model_expand", "budget_seconds": 0.01,
                "search_seed": None, "repetition": 0,
                "contract": str(contract.directory), "amendment_id": amendment["id"],
                "amendment_files": amendment["files"]}
        tmp = Path(tempfile.mkdtemp(prefix="p4-crash-journal-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        harness = runner.Harness(tmp, timeout=60)
        with patch.object(runner.subprocess, "run", return_value=SimpleNamespace(
                stdout="", stderr="synthetic worker crash", returncode=9)):
            row = harness.run(spec)
        self.assertTrue(row["failed_row"])
        self.assertEqual(len(runner.read_jsonl(tmp / "journals/p4_commands.jsonl")), 1)
        self.assertEqual(len(runner.read_jsonl(tmp / "journals/p4_rows.jsonl")), 1)
        (tmp / "p4").mkdir()
        runner.write_jsonl(tmp / "p4/model_rows.jsonl", [row])
        instance = checker_module.Checker(tmp, ROOT / "plan/phase2", amendment)
        instance.check_durable_journals(harness.commands)
        self.assertFalse(instance.findings)
        (tmp / "journals/p4_rows.jsonl").write_text("")
        missing = checker_module.Checker(tmp, ROOT / "plan/phase2", amendment)
        missing.check_durable_journals(harness.commands)
        self.assertIn("journals.row_command_count", {f["check"] for f in missing.findings})

    def _physical_checker_fixture(self):
        import direct_compiler as dcomp
        import direct_contract as dc
        name, program = runner.public_programs()[0]
        program_path = ROOT / ".reference" / "programs" / name
        facts = dc.derive(program)
        incumbent, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
        record = runner.whole_program_record(name, "public", program, facts, incumbent)
        domain = se.Domain.from_record(record)
        first_valid = None
        for index, (kind, field_id, _alt, value) in enumerate(physical_probes.proposals(domain)):
            times = dict(domain.incumbent_times)
            addresses = dict(domain.incumbent_addresses)
            if kind == "time":
                times[int(field_id)] = value
            else:
                addresses[field_id] = value
            candidate = __import__("direct_contract").compilation(facts, times, addresses)
            try:
                machine.check_compilation(program, candidate)
            except (machine.CompileError, machine.ProgramError):
                continue
            first_valid = index
            break
        self.assertIsNotNone(first_valid)
        cap = int(first_valid) + 1
        program_sha = runner.file_digest(program_path)
        rows, per_program = physical_probes.run(domain, program, cap, 60.0, program_sha)
        fixed = {"stage": "p1", "corpus": "public", "program": name,
                 "program_sha256": program_sha, "domain_sha256": domain.digest()}
        rows = [row | fixed for row in rows]
        per_program |= {"program": name, "program_sha256": program_sha,
                        "domain_sha256": domain.digest()}
        totals = {status: per_program["counts"][status]
                  for status in ("INVALID_PHYSICAL", "VALIDATED_COMPLETE", "INTERRUPTED", "DISCREPANCY")}
        p0 = {"public": [{"name": name, "path": f"inputs/public/{name}",
                          "program_sha256": program_sha}]}
        amendment = runner.load_amendment(Path("plan/phase2_recovery/AMENDMENT.json"))
        amendment["policy"]["supplemental_coverage"]["maximum_proposals_per_program"] = cap
        return name, program, domain, rows, per_program, totals, p0, amendment

    def _physical_checker_findings(self, data, mutation=None):
        name, program, domain, rows, per_program, totals, p0, amendment = data
        rows = json.loads(json.dumps(rows))
        per_program = json.loads(json.dumps(per_program))
        if mutation:
            mutation(rows, per_program)
        summary = {"programs": [per_program], "attempted": len(rows), "status_counts": totals}
        tmp = Path(tempfile.mkdtemp(prefix="physical-check-mutation-"))
        source = ROOT / ".reference" / "programs" / name
        target = tmp / p0["public"][0]["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        (tmp / "p1").mkdir(exist_ok=True)
        runner.write_jsonl(tmp / "p1/physical_coordinate_probes.jsonl", rows)
        runner.write_json(tmp / "p1/physical_coordinate_summary.json", summary)
        checker = checker_module.Checker(tmp, ROOT / "plan/phase2", amendment)
        checker.check_physical_probes(p0)
        return {item["check"] for item in checker.findings}

    def test_physical_checker_rejects_omission_duplicate_and_forged_identity(self):
        data = self._physical_checker_fixture()
        self.assertFalse(self._physical_checker_findings(data))
        self.assertTrue(self._physical_checker_findings(
            data, lambda rows, summary: rows.pop()
        ))
        self.assertTrue(self._physical_checker_findings(
            data, lambda rows, summary: rows.append(dict(rows[-1]))
        ))
        def forge(rows, _summary):
            valid = next(row for row in rows if row["status"] == "VALIDATED_COMPLETE")
            valid["identity_sha256"] = "0" * 64
        self.assertIn("p1.physical_identity", self._physical_checker_findings(data, forge))

    def test_physical_checker_rejects_reordered_field_and_codec_rejection(self):
        data = self._physical_checker_fixture()
        def reorder(rows, _summary):
            rows[0]["value"] += 1
        self.assertIn("p1.physical_order", self._physical_checker_findings(data, reorder))
        def reject_codec(rows, _summary):
            valid = next(row for row in rows if row["status"] == "VALIDATED_COMPLETE")
            valid["codec_results"][se.CODECS[0]]["status"] = se.DEAD_END
        self.assertIn("p1.physical_codec_rows",
                      self._physical_checker_findings(data, reject_codec))

    def test_physical_checker_rejects_invalid_as_complete_and_erased_counts(self):
        data = self._physical_checker_fixture()
        def relabel(rows, _summary):
            invalid = next(row for row in rows if row["status"] == "INVALID_PHYSICAL")
            invalid["status"] = "VALIDATED_COMPLETE"
        self.assertTrue(self._physical_checker_findings(data, relabel))
        def erase_case(rows, _summary):
            valid = next(row for row in rows if row["status"] == "VALIDATED_COMPLETE")
            valid["case_checks"] = 0
        self.assertTrue(self._physical_checker_findings(data, erase_case))
        def erase_codec(rows, _summary):
            valid = next(row for row in rows if row["status"] == "VALIDATED_COMPLETE")
            del valid["codec_counts"][se.CODECS[0]]
        self.assertTrue(self._physical_checker_findings(data, erase_codec))
        def erase_roundtrip_total(_rows, summary):
            summary["codec_roundtrips"] = 0
        self.assertIn("p1.physical_roundtrip_total",
                      self._physical_checker_findings(data, erase_roundtrip_total))

    def test_physical_checker_rejects_summary_membership_and_elapsed_mutation(self):
        data = self._physical_checker_fixture()
        name, program, domain, rows, per_program, totals, p0, amendment = data
        tmp = Path(tempfile.mkdtemp(prefix="physical-summary-mutation-"))
        source = ROOT / ".reference" / "programs" / name
        target = tmp / p0["public"][0]["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        (tmp / "p1").mkdir(exist_ok=True)
        runner.write_jsonl(tmp / "p1/physical_coordinate_probes.jsonl", rows)
        summary = {"programs": [per_program, dict(per_program)], "attempted": len(rows),
                   "status_counts": totals}
        runner.write_json(tmp / "p1/physical_coordinate_summary.json", summary)
        checker = checker_module.Checker(tmp, ROOT / "plan/phase2", amendment)
        checker.check_physical_probes(p0)
        self.assertIn("p1.physical_summary_membership", {f["check"] for f in checker.findings})
        def elapsed(rows, _summary):
            rows[1]["elapsed_seconds"] = -1
        self.assertIn("p1.physical_elapsed_order", self._physical_checker_findings(data, elapsed))

    def test_checker_rejects_false_original_and_amended_coverage_pass(self):
        source = ROOT / "results/phase2_structural_encoding/phase2_repair_20260923c"
        tmp = Path(tempfile.mkdtemp(prefix="coverage-false-pass-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        shutil.copytree(source / "p1", tmp / "p1")
        shutil.copytree(source / "inputs/public", tmp / "inputs/public")
        p0 = json.loads((source / "p0/summary.json").read_text())
        summary = json.loads((tmp / "p1/summary.json").read_text())
        summary["coverage_met"] = True
        summary["original_random_coverage"] = {
            "coverage_met": True, "per_program_distinct": [0] * len(p0["public"])}
        probes = tmp / "p1/physical_coordinate_probes.jsonl"
        probes.write_text("")
        empty_codec_counts = {codec: {"attempted": 0, "complete": 0, "interrupted": 0,
                                      "discrepancy": 0, "machine_attempted": 0,
                                      "machine_complete": 0, "case_attempted": 0,
                                      "case_complete": 0} for codec in se.CODECS}
        programs = [{"program": item["name"], "attempted": 0,
                     "counts": {"INVALID_PHYSICAL": 0, "VALIDATED_COMPLETE": 0,
                                "INTERRUPTED": 0, "DISCREPANCY": 0},
                     "distinct_complete": 0, "identity_sha256": [],
                     "codec_counts": empty_codec_counts, "codec_roundtrips": 0,
                     "case_checks": 0,
                     "diversity": {"unique_issue_time_vectors": 0,
                                   "unique_address_maps": 0, "per_field_changes": {},
                                   "cycles_range": None, "scratch_range": None,
                                   "product_range": None},
                     "elapsed_seconds": 0.0, "stopped_by": "invalid_early_stop",
                     "exhausted": False, "deadline_overshoot_seconds": 0.0}
                    for item in p0["public"]]
        physical_summary = {"programs": programs, "attempted": 0,
                            "status_counts": {"INVALID_PHYSICAL": 0,
                                              "VALIDATED_COMPLETE": 0,
                                              "INTERRUPTED": 0, "DISCREPANCY": 0}}
        runner.write_json(tmp / "p1/physical_coordinate_summary.json", physical_summary)
        summary["raw_artifacts"]["physical_coordinate_probes.jsonl"] = runner.file_digest(probes)
        summary["raw_artifacts"]["physical_coordinate_summary.json"] = runner.file_digest(
            tmp / "p1/physical_coordinate_summary.json")
        runner.write_json(tmp / "p1/summary.json", summary)
        amendment = runner.load_amendment(Path("plan/phase2_recovery/AMENDMENT.json"))
        checker = checker_module.Checker(tmp, ROOT / "plan/phase2", amendment)
        checker.check_p1({"public": p0["public"]})
        checks = {item["check"] for item in checker.findings}
        self.assertIn("p1.original_coverage", checks)
        self.assertIn("p1.coverage_met", checks)

    def _p4_test_spec(self, arm="model_expand"):
        contract = runner.Contract(ROOT / "plan/phase2")
        record = next(item for item in contract.fixtures if item["id"] == "many_ready_1")
        return contract, record, {"fixture_id": record["id"],
                                  "program_sha256": se.object_digest(record["program"]),
                                  "arm": arm, "budget_seconds": 0.01,
                                  "search_seed": None, "repetition": 0}

    def test_p4_cover_deadline_uses_remaining_budget_and_records_oracle_cost(self):
        from research import structural_models as models
        contract, record, spec = self._p4_test_spec()
        clock = [0.0]
        result = models.CoverResult(1, (), "COMPLETE", "ok", 0, 0, 0.0)
        with patch.object(runner.time, "perf_counter", side_effect=lambda: clock[0]), \
             patch.object(models, "exact_cover", side_effect=lambda *a, **k: (clock.__setitem__(0, 1.0) or result)):
            row = runner.run_model_measurement(spec, contract)
        self.assertEqual(row["status"], runner.INCONCLUSIVE)
        self.assertEqual(row["reason"], "optimization budget expired during cover construction")
        self.assertIn("oracle_preprocessing_seconds", row)

    def test_p4_decode_deadline_keeps_interruption_and_no_discovery(self):
        from research import structural_models as models
        contract, record, spec = self._p4_test_spec()
        enumeration = oracle.enumerate_feasible(record, contract.budgets["oracle_cartesian_max"])
        split = runner.split_fixture(enumeration, contract.seeds["split"],
                                     contract.statistics["p4_min_train"],
                                     contract.statistics["p4_min_test"])
        domain = se.Domain.from_record(record)
        index = se.encode(domain, json.loads(split["test"][0]), "structural_rank")
        clock = [0.0]
        original_decode = se.decode
        def expire_after_decode(*args, **kwargs):
            decoded = original_decode(*args, **kwargs)
            clock[0] = 1.0
            return decoded
        cover = models.CoverResult(1, (), "COMPLETE", "ok", 0, 0, 0.0)
        with patch.object(runner.time, "perf_counter", side_effect=lambda: clock[0]), \
             patch.object(oracle, "enumerate_feasible", return_value=enumeration), \
             patch.object(models, "exact_cover", return_value=cover), \
             patch.object(models, "proposals", return_value=iter([(index, False)])), \
             patch.object(se, "decode", side_effect=expire_after_decode):
            row = runner.run_model_measurement(spec, contract)
        self.assertEqual(row["status"], runner.PASS)
        self.assertEqual(row["counts"]["interrupted"], 1)
        self.assertEqual(row["counts"]["test_discoveries"], 0)

    def test_p4_test_evaluation_deadline_does_not_credit_discovery(self):
        from research import structural_models as models
        contract, record, spec = self._p4_test_spec()
        enumeration = oracle.enumerate_feasible(record, contract.budgets["oracle_cartesian_max"])
        split = runner.split_fixture(enumeration, contract.seeds["split"],
                                     contract.statistics["p4_min_train"],
                                     contract.statistics["p4_min_test"])
        domain = se.Domain.from_record(record)
        identity = split["test"][0]
        index = se.encode(domain, json.loads(identity), "structural_rank")
        clock = [0.0]
        class ExpiringEvaluation(dict):
            def __contains__(self, key):
                found = super().__contains__(key)
                clock[0] = 1.0
                return found
        hidden = ExpiringEvaluation(oracle.hidden_evaluation(enumeration))
        cover = models.CoverResult(1, (), "COMPLETE", "ok", 0, 0, 0.0)
        with patch.object(runner.time, "perf_counter", side_effect=lambda: clock[0]), \
             patch.object(oracle, "enumerate_feasible", return_value=enumeration), \
             patch.object(oracle, "hidden_evaluation", return_value=hidden), \
             patch.object(models, "exact_cover", return_value=cover), \
             patch.object(models, "proposals", return_value=iter([(index, False)])):
            row = runner.run_model_measurement(spec, contract)
        self.assertEqual(row["status"], runner.PASS)
        self.assertEqual(row["interrupted_phase"], "test_evaluation")
        self.assertEqual(row["counts"]["test_discoveries"], 0)
        self.assertEqual(row["counts"]["interrupted"], 1)

    def test_p4_known_case_failure_beats_deadline(self):
        from research import structural_models as models
        contract, record, spec = self._p4_test_spec()
        enumeration = oracle.enumerate_feasible(record, contract.budgets["oracle_cartesian_max"])
        split = runner.split_fixture(enumeration, contract.seeds["split"],
                                     contract.statistics["p4_min_train"],
                                     contract.statistics["p4_min_test"])
        domain = se.Domain.from_record(record)
        index = se.encode(domain, json.loads(split["test"][0]), "structural_rank")
        clock = [0.0]
        def fail_after_expiry(*_args):
            clock[0] = 1.0
            raise machine.ProgramError("known case mismatch")
        cover = models.CoverResult(1, (), "COMPLETE", "ok", 0, 0, 0.0)
        with patch.object(runner.time, "perf_counter", side_effect=lambda: clock[0]), \
             patch.object(oracle, "enumerate_feasible", return_value=enumeration), \
             patch.object(models, "exact_cover", return_value=cover), \
             patch.object(models, "proposals", return_value=iter([(index, False)])), \
             patch.object(machine, "check_case", side_effect=fail_after_expiry):
            row = runner.run_model_measurement(spec, contract)
        self.assertEqual(row["status"], runner.FAIL)
        self.assertIn("known case mismatch", row["discrepancy"])


if __name__ == "__main__":
    unittest.main()
