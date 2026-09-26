"""Regressions added by the Claude release audit (2026-09-24).

Each test pins a residual defect found while reviewing the seven lead findings
of ``recovery_lead_review_20260923/REPAIR_REVIEW.md`` against the frozen
checkpoint, or a finding that had no executable test:

* Finding 2 residue: under the amendment, H2 was still labelled from the public
  P2 contrast, P2 still used the log-of-mean-products estimand, and
  COMPARISON.md never rendered the held-out primary while claiming the
  primary used "the original confirmatory P2 interval".
* Finding 7 gap: nothing exercised ``stage_p4``'s balanced arm order.
* Finding 3 residue, observed at runtime in ``recovery_campaign_20260923_r2``:
  the checker's physical replay had no path that recomputes INTERRUPTED, so two
  genuine 60 s deadline interruptions were "re-completed" by the replay and
  credited to coverage, producing 17 false findings and the opposite of the
  amendment's rule that only fully validated objects count.
* H4 residue, masked in r2 by the cascade above: ``check_p4`` never derived
  INCONCLUSIVE when the recomputed H4 gate did not advance, so a legitimate
  triage outcome was derived as PASS and reported as a reconciliation finding.
"""
from __future__ import annotations

import json
import math
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / ".reference"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from research import run_structural_experiments as runner  # noqa: E402
from research import check_structural_evidence as checker_module  # noqa: E402
from research import structural_models as sm  # noqa: E402
from research import physical_probes  # noqa: E402
from research import structural_encoding as se  # noqa: E402


CONTRACT = runner.Contract(ROOT / "plan/phase2")
AMENDMENT = runner.load_amendment(Path("plan/phase2_recovery/AMENDMENT.json"))
REPS = CONTRACT.statistics["timing_repetitions"]


def _benchmark_rows(program: str, control_products, candidate_products) -> list:
    """Complete P2/P5-shaped rows for one program; products vary by repetition."""
    rows = []

    def add(arm, budget, repetition, product):
        rows.append({"arm": arm, "budget_seconds": budget, "program_sha256": program,
                     "repetition": repetition, "search_seed": None,
                     "product": product, "cycles": 10, "scratch": product / 10,
                     "compile_seconds": 0.1, "process_seconds": 0.2,
                     "peak_rss_bytes": 1000, "failed_row": False})

    for budget in CONTRACT.budgets["optimisation_seconds"]:
        for repetition in range(REPS):
            add("accepted_budgeted", budget, repetition, control_products[repetition])
            for arm in ("structural_bound", "structural_dfs", "structural_expanded"):
                add(arm, budget, repetition, candidate_products[repetition])
    for arm in ("accepted_default", "accepted_bootstrap", "classical"):
        for repetition in range(REPS):
            add(arm, None, repetition, control_products[repetition])
    return rows


# Control J alternates 100/400 and candidate J cycles 100/200/200, out of step,
# so the mean of paired log ratios differs from the log of the ratio of mean
# products; the first test below pins that difference.
CONTROL = [100 if r % 2 == 0 else 400 for r in range(REPS)]
CANDIDATE = [100 if r % 3 == 0 else 200 for r in range(REPS)]
PAIRED = sum(math.log(c / d) for c, d in zip(CONTROL, CANDIDATE)) / REPS
LOG_OF_MEANS = math.log(sum(CONTROL) / sum(CANDIDATE))


class AmendedP2UsesThePairedEstimand(unittest.TestCase):
    def test_the_two_estimands_differ_on_this_fixture(self):
        self.assertGreater(abs(PAIRED - LOG_OF_MEANS), 1e-3)

    def test_stage_p2_under_the_amendment_reports_the_paired_estimand(self):
        rows = _benchmark_rows("public-program", CONTROL, CANDIDATE)
        tmp = Path(tempfile.mkdtemp(prefix="release-p2-paired-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        contract = SimpleNamespace(budgets=CONTRACT.budgets, seeds=CONTRACT.seeds,
                                   statistics=CONTRACT.statistics, fixtures=[])
        fake_run = SimpleNamespace(contract=contract, amendment=AMENDMENT,
                                   stage_dir=lambda stage: tmp,
                                   prior=lambda stage: {"public": []})
        with patch.object(runner, "_benchmark_corpus", return_value=(
                rows, {"failed_rows": 0, "membership_exact": True})):
            summary = runner.stage_p2(fake_run)
        entry = summary["comparisons"]["structural_bound_vs_accepted_budgeted@0.1"]
        self.assertAlmostEqual(entry["per_program_log_ratio"]["public-program"], PAIRED)
        self.assertIn("mean paired log", entry["endpoint"])
        self.assertEqual(entry["paired_repetitions_per_program"]["public-program"], REPS)

    def test_legacy_p2_without_the_amendment_is_unchanged(self):
        rows = _benchmark_rows("public-program", CONTROL, CANDIDATE)
        legacy = runner.paired_log_ratio_analysis(
            rows, {"public-program": "public"}, "accepted_budgeted",
            "structural_bound", 0.1, CONTRACT)
        self.assertAlmostEqual(legacy["per_program_log_ratio"]["public-program"],
                               LOG_OF_MEANS)

    def test_the_checker_recomputes_amended_p2_with_the_paired_estimand(self):
        rows = _benchmark_rows("public-program", CONTROL, CANDIDATE)
        families = {"public-program": "public"}
        paired = runner.paired_log_ratio_analysis(
            rows, families, "accepted_budgeted", "structural_bound", 0.1, CONTRACT,
            paired_repetitions=True)
        unpaired = runner.paired_log_ratio_analysis(
            rows, families, "accepted_budgeted", "structural_bound", 0.1, CONTRACT)
        tmp = Path(tempfile.mkdtemp(prefix="release-p2-checker-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        faithful = checker_module.Checker(tmp, ROOT / "plan/phase2", AMENDMENT)
        faithful.recompute_comparisons("p2", {"c": paired}, rows, families)
        self.assertFalse(faithful.findings, faithful.findings)
        stale = checker_module.Checker(tmp, ROOT / "plan/phase2", AMENDMENT)
        stale.recompute_comparisons("p2", {"c": unpaired}, rows, families)
        self.assertIn("p2.comparison_point_estimate", {f["check"] for f in stale.findings})


class AmendedH2IsTheHeldoutPrimary(unittest.TestCase):
    def _root(self, public_interval, primary_interval, p5_status="PASS"):
        tmp = Path(tempfile.mkdtemp(prefix="release-h2-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "p2").mkdir()
        runner.write_json(tmp / "p2/summary.json", {
            "primary_budget_seconds": 0.1,
            "comparisons": {"structural_bound_vs_accepted_budgeted@0.1": {
                "wins": 8, "ties": 0, "losses": 0, "programs": 8,
                "interval": {"intervals": {"0.025-0.975": public_interval}}}}})
        runner.write_json(tmp / "gates.json", {"p5": {"status": p5_status}})
        if primary_interval is not None:
            runner.write_json(tmp / "COMPARISON.json", {"primary_h2": {
                "corpus": "heldout", "budget_seconds": 0.1, "control": "accepted_budgeted",
                "analysis": {"programs": 100, "expected_programs": 100,
                             "wins": 50, "ties": 0, "losses": 50,
                             "interval": {"intervals": {"0.025-0.975": primary_interval}}}}})
        return tmp

    def test_a_favourable_public_contrast_does_not_label_h2(self):
        root = self._root([0.1, 0.2], [-0.1, 0.2])
        self.assertEqual(runner.hypothesis_dispositions(root, amended=True)["H2"]["status"],
                         "inconclusive")
        # The legacy protocol keeps its own (public) semantics unchanged.
        self.assertEqual(runner.hypothesis_dispositions(root)["H2"]["status"], "supported")

    def test_the_heldout_primary_decides_both_directions(self):
        self.assertEqual(runner.hypothesis_dispositions(
            self._root([-0.2, -0.1], [0.05, 0.2]), amended=True)["H2"]["status"], "supported")
        self.assertEqual(runner.hypothesis_dispositions(
            self._root([0.1, 0.2], [-0.2, -0.05]), amended=True)["H2"]["status"], "unsupported")

    def test_no_heldout_primary_is_not_run_and_a_failed_p5_is_never_supported(self):
        self.assertEqual(runner.hypothesis_dispositions(
            self._root([0.1, 0.2], None), amended=True)["H2"]["status"], runner.NOT_RUN)
        self.assertEqual(runner.hypothesis_dispositions(
            self._root([0.1, 0.2], [0.05, 0.2], p5_status="FAIL"), amended=True)["H2"]["status"],
            "inconclusive")

    def test_the_checker_flags_a_public_derived_h2_label(self):
        root = self._root([0.1, 0.2], [-0.1, 0.2])
        runner.write_json(root / "hypotheses.json", runner.hypothesis_dispositions(root))
        checker = checker_module.Checker(root, ROOT / "plan/phase2", AMENDMENT)
        checker.check_hypotheses({})
        self.assertIn("hypotheses.status", {f["check"] for f in checker.findings})


class ComparisonMarkdownAndDenominators(unittest.TestCase):
    def _comparison(self, drop_candidate_rep_of=None):
        rows = {"public": _benchmark_rows("pub", CONTROL, CANDIDATE), "heldout": []}
        families = {"public": {"pub": "public"}, "heldout": {}}
        for index in range(4):
            program = f"held-{index}"
            rows["heldout"].extend(_benchmark_rows(program, CONTROL, CANDIDATE))
            families["heldout"][program] = f"family-{index % 2}"
        if drop_candidate_rep_of:
            rows["heldout"] = [row for row in rows["heldout"] if not (
                row["program_sha256"] == drop_candidate_rep_of
                and row["arm"] == "structural_bound" and row["repetition"] == 3)]
        return runner.build_recovery_comparison(rows, families, CONTRACT)

    def test_markdown_renders_the_heldout_primary_and_no_p2_primary_claim(self):
        comparison = self._comparison()
        text = runner.comparison_markdown(comparison)
        self.assertIn("## Primary H2 (confirmatory)", text)
        self.assertIn("Corpus `heldout`, budget 0.1 s", text)
        self.assertNotIn("confirmatory P2 interval", text)
        self.assertIn("Public and held-out programs are not pooled.", text)
        self.assertEqual(len(comparison["entries"]), 24)
        point = comparison["primary_h2"]["analysis"]["interval"]["point_estimate"]
        self.assertAlmostEqual(point, PAIRED)

    def test_an_unpaired_program_is_listed_not_silently_dropped(self):
        comparison = self._comparison(drop_candidate_rep_of="held-2")
        primary = comparison["primary_h2"]["analysis"]
        self.assertEqual((primary["programs"], primary["expected_programs"]), (3, 4))
        self.assertEqual(primary["unpaired_programs"], ["held-2"])
        entry = next(e for e in comparison["entries"] if e["corpus"] == "heldout"
                     and e["budget_seconds"] == 0.1 and e["control"] == "classical")
        self.assertEqual((entry["n_programs"], entry["expected_programs"],
                          entry["unpaired_programs"]), (3, 4, ["held-2"]))
        self.assertIn("| 3/4 |", runner.comparison_markdown(comparison))


class CheckerAcceptsGenuineDeadlineInterruption(unittest.TestCase):
    """A real bounded probe prefix whose last (valid) proposal expires mid round trip."""

    def _interrupted_prefix(self):
        import direct_compiler as dcomp
        import direct_contract as dc
        import machine
        name, program = runner.public_programs()[0]
        facts = dc.derive(program)
        incumbent, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
        domain = se.Domain.from_record(
            runner.whole_program_record(name, "public", program, facts, incumbent))
        first_valid = None
        for index, (kind, field_id, _alt, value) in enumerate(physical_probes.proposals(domain)):
            times, addresses = dict(domain.incumbent_times), dict(domain.incumbent_addresses)
            if kind == "time":
                times[int(field_id)] = value
            else:
                addresses[field_id] = value
            try:
                machine.check_compilation(program, dc.compilation(facts, times, addresses))
            except (machine.CompileError, machine.ProgramError):
                continue
            first_valid = index
            break
        self.assertIsNotNone(first_valid)
        cap = first_valid + 1
        clock = [0.0]
        original = se.decode

        def expires_after_first_decode(*args, **kwargs):
            result = original(*args, **kwargs)
            clock[0] = 2.0
            return result

        program_sha = runner.file_digest(ROOT / ".reference" / "programs" / name)
        with patch.object(physical_probes.time, "perf_counter", side_effect=lambda: clock[0]), \
             patch.object(se, "decode", side_effect=expires_after_first_decode):
            rows, per_program = physical_probes.run(domain, program, cap, 1.0, program_sha)
        fixed = {"stage": "p1", "corpus": "public", "program": name,
                 "program_sha256": program_sha, "domain_sha256": domain.digest()}
        rows = [row | fixed for row in rows]
        per_program |= {"program": name, "program_sha256": program_sha,
                        "domain_sha256": domain.digest()}
        amendment = json.loads(json.dumps(AMENDMENT))
        amendment["policy"]["supplemental_coverage"]["maximum_proposals_per_program"] = cap
        amendment["policy"]["supplemental_coverage"]["seconds_per_program"] = 1.0
        return name, rows, per_program, amendment

    def _check(self, data, mutation=None):
        name, rows, per_program, amendment = data
        rows, per_program = json.loads(json.dumps(rows)), json.loads(json.dumps(per_program))
        if mutation:
            mutation(rows, per_program)
        tmp = Path(tempfile.mkdtemp(prefix="release-physical-interrupt-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        target = tmp / "inputs/public" / name
        target.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / ".reference" / "programs" / name, target)
        (tmp / "p1").mkdir()
        runner.write_jsonl(tmp / "p1/physical_coordinate_probes.jsonl", rows)
        runner.write_json(tmp / "p1/physical_coordinate_summary.json", {
            "programs": [per_program], "attempted": len(rows),
            "status_counts": dict(per_program["counts"])})
        checker = checker_module.Checker(tmp, ROOT / "plan/phase2", amendment)
        full = checker.check_physical_probes({"public": [{
            "name": name, "path": f"inputs/public/{name}",
            "program_sha256": per_program["program_sha256"]}]})
        return {f["check"] for f in checker.findings}, full[name]

    def test_the_prefix_really_ends_in_a_codec_interruption(self):
        _name, rows, per_program, _amendment = data = self._interrupted_prefix()
        self.assertEqual(rows[-1]["status"], "INTERRUPTED")
        self.assertTrue(rows[-1]["interrupted_phase"].startswith("codec:"))
        self.assertIn(se.CODECS[0], rows[-1]["codec_results"])
        self.assertEqual((per_program["stopped_by"], per_program["distinct_complete"]),
                         ("deadline", 0))
        self.assertTrue(data)

    def test_a_genuine_interruption_is_accepted_and_never_credited(self):
        findings, credited = self._check(self._interrupted_prefix())
        self.assertFalse(findings, findings)
        self.assertEqual(credited, set())

    def test_an_interruption_before_the_deadline_is_rejected(self):
        def early(rows, _summary):
            rows[-1]["elapsed_seconds"] = 0.5
        findings, _ = self._check(self._interrupted_prefix(), early)
        self.assertIn("p1.physical_interruption", findings)

    def test_an_invalid_proposal_relabelled_interrupted_is_rejected(self):
        def hide(rows, summary):
            invalid = next(row for row in rows if row["status"] == "INVALID_PHYSICAL")
            invalid["status"], invalid["interrupted_phase"] = "INTERRUPTED", "machine_validation"
            summary["counts"]["INVALID_PHYSICAL"] -= 1
            summary["counts"]["INTERRUPTED"] += 1
        findings, _ = self._check(self._interrupted_prefix(), hide)
        self.assertIn("p1.physical_interruption", findings)

    def test_forged_partial_codec_evidence_is_rejected(self):
        def forge(rows, _summary):
            rows[-1]["codec_results"][se.CODECS[0]]["index"] = "0"
        findings, _ = self._check(self._interrupted_prefix(), forge)
        self.assertIn("p1.physical_codec_rows", findings)


class P4BalancedArmOrder(unittest.TestCase):
    def test_stage_p4_schedules_7020_rows_in_the_frozen_balanced_order(self):
        tmp = Path(tempfile.mkdtemp(prefix="release-p4-order-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        specs = []

        def fake_run(spec):
            specs.append(spec)
            return {"stage": "p4", "fixture_id": spec["fixture_id"], "arm": spec["arm"],
                    "budget_seconds": spec["budget_seconds"], "search_seed": spec["search_seed"],
                    "repetition": spec["repetition"], "status": runner.NOT_APPLICABLE,
                    "semantic_sha256": spec["fixture_id"], "failed_row": False}

        run = SimpleNamespace(contract=CONTRACT, amendment=AMENDMENT,
                              stage_dir=lambda stage: tmp, prior=lambda stage: {},
                              expect_subprocesses=lambda stage, count: None,
                              harness=SimpleNamespace(run=fake_run))
        with self.assertRaises(runner.StageBlocked):
            runner.stage_p4(run)
        self.assertEqual(len(specs), 12 * 3 * REPS * (3 + 10))
        self.assertEqual(len(specs), 7020)

        # Independent statement of contract section 9: one RNG for the stage;
        # fixtures in manifest order, budgets ascending, seeds null first; each
        # block's sorted eligible arms shuffled once and rotated by repetition.
        rng = random.Random(CONTRACT.seeds["arm_order"])
        expected = []
        for record in CONTRACT.fixtures:
            for budget in sorted(CONTRACT.budgets["optimisation_seconds"]):
                for seed in [None] + sorted(CONTRACT.seeds["search"]):
                    arms = sorted(a for a in sm.MODEL_ARMS
                                  if (a == "uniform_bits") == (seed is not None))
                    rng.shuffle(arms)
                    for repetition in range(REPS):
                        k = repetition % len(arms)
                        for arm in arms[k:] + arms[:k]:
                            expected.append((record["id"], budget, seed, repetition, arm))
        observed = [(s["fixture_id"], s["budget_seconds"], s["search_seed"],
                     s["repetition"], s["arm"]) for s in specs]
        self.assertEqual(observed, expected)

        # Not "one entire arm first": every repetition of a null-seed block runs
        # all three deterministic arms consecutively, and the leading arm rotates.
        first = [s for s in specs if s["fixture_id"] == CONTRACT.fixtures[0]["id"]
                 and s["budget_seconds"] == 0.01 and s["search_seed"] is None]
        windows = [first[i:i + 3] for i in range(0, len(first), 3)]
        self.assertTrue(all({s["repetition"] for s in w} == {w[0]["repetition"]} and
                            len({s["arm"] for s in w}) == 3 for w in windows))
        self.assertEqual(len({w[0]["arm"] for w in windows}), 3)
        self.assertTrue(all(s["program_sha256"] and s["fixture_id"] for s in specs))

    def test_the_checker_derives_inconclusive_when_the_recomputed_h4_gate_fails(self):
        tmp = Path(tempfile.mkdtemp(prefix="release-p4-h4-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "p4").mkdir()

        def fake_run(spec):
            return {"stage": "p4", "fixture_id": spec["fixture_id"], "arm": spec["arm"],
                    "budget_seconds": spec["budget_seconds"], "search_seed": spec["search_seed"],
                    "repetition": spec["repetition"], "status": runner.NOT_APPLICABLE,
                    "semantic_sha256": spec["fixture_id"], "failed_row": False}

        run = SimpleNamespace(contract=CONTRACT, amendment=AMENDMENT,
                              stage_dir=lambda stage: tmp / "p4", prior=lambda stage: {},
                              expect_subprocesses=lambda stage, count: None,
                              harness=SimpleNamespace(run=fake_run))
        with self.assertRaises(runner.StageBlocked) as blocked:
            runner.stage_p4(run)
        self.assertEqual(blocked.exception.status, runner.INCONCLUSIVE)
        checker = checker_module.Checker(tmp, ROOT / "plan/phase2", AMENDMENT)
        checker.check_p4()
        self.assertFalse(checker.findings, checker.findings)
        self.assertIn("p4.h4_gate", {item["check"] for item in checker.incompletes_for("p4")})
        # A forged advancement label is still a finding, and still INCONCLUSIVE.
        summary = json.loads((tmp / "p4/summary.json").read_text())
        summary["advance_to_model_arm"] = True
        runner.write_json(tmp / "p4/summary.json", summary)
        forged = checker_module.Checker(tmp, ROOT / "plan/phase2", AMENDMENT)
        forged.check_p4()
        self.assertIn("p4.contrast_recount", {f["check"] for f in forged.findings})
        self.assertIn("p4.h4_gate", {item["check"] for item in forged.incompletes_for("p4")})


if __name__ == "__main__":
    unittest.main()
