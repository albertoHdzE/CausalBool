"""Regressions for the 2026-09-23 lead repair: L1 and R1-R6.

Every finding of `results/phase2_structural_encoding/lead_review_20260923/LEAD_REVIEW.md`
has at least one test here that *reproduces its failure mode*, with the expected
outcome written down. Naming a check identifier in a string is not evidence that
its failure mode was tested, so each test either performs the lead's own
reproduction or the smallest faithful version of it, and asserts what the
repaired code does instead.

The R2 and R3 tests need a real run to corrupt. They build one: a complete
campaign under a *temporary copy* of the frozen contract whose only difference is
a smaller sampling request, so that a valid control exists inside a unit test's
time budget. No scientific gate, seed or threshold is changed, and the real
campaign's budgets are untouched -- the reduced request lives in a temporary
directory and is never the contract the campaign runs under. That temporary
control is the new valid control the repair handoff requires: the lead's original
control now legitimately fails the strengthened provenance, so corrupting it
would prove nothing.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import random
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / ".reference"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import machine  # noqa: E402

import direct_compiler as dc  # noqa: E402
import direct_contract as dcontract  # noqa: E402
import schema_index as si  # noqa: E402

from research import check_structural_evidence as checker  # noqa: E402
from research import run_structural_experiments as runner  # noqa: E402
from research import structural_encoding as se  # noqa: E402
from research import structural_models as sm  # noqa: E402
from research import structural_search as ss  # noqa: E402


CONTRACT_DIR = ROOT / "plan" / "phase2"
FIXTURES = json.loads((CONTRACT_DIR / "FIXTURES.json").read_text())["fixtures"]


@contextlib.contextmanager
def _reference_manifest(payload: dict):
    """Present a different `reference.json` to `verify_locks`, on disk only.

    Nothing writes to the real file: the reference manifest is baseline-locked
    protected input. Only the read is redirected.
    """

    original = Path.read_text
    target = ROOT / "reference.json"

    def read_text(self, *args, **kwargs):
        if self == target:
            return json.dumps(payload)
        return original(self, *args, **kwargs)

    with patch.object(Path, "read_text", read_text):
        yield


def constant_domain(record: dict) -> se.Domain:
    """The lead probe's zero-width legal domain: one option per decision.

    Every declared domain is narrowed to the incumbent's own choice, so every
    field is zero bits wide and index 0 decodes completely. It is the smallest
    input on which "did the case validator run?" has an unambiguous answer.
    """

    record = json.loads(json.dumps(record))
    incumbent = record["incumbent"]
    times = {
        str(op): cycle
        for cycle, bundle in enumerate(incumbent["bundles"])
        for ids in bundle.values()
        for op in ids
    }
    for key in record["time_domains"]:
        record["time_domains"][key] = [times[key]]
    for key in record["address_domains"]:
        record["address_domains"][key] = [incumbent["scratch"][key]]
    return se.Domain.from_record(record)


# --------------------------------------------------------------------------
# L1 -- the test-placement repair
# --------------------------------------------------------------------------


class L1TestPlacement(unittest.TestCase):
    """The four research test modules live outside `tests_direct/`."""

    def test_no_phase2_test_module_remains_in_tests_direct(self):
        stray = sorted(
            path.name for path in (ROOT / "tests_direct").glob("test_phase2_*.py")
        )
        self.assertEqual(stray, [], f"these still fail the frozen evidence gate: {stray}")

    def test_the_research_tests_are_a_package_here(self):
        self.assertTrue((ROOT / "research_tests" / "__init__.py").is_file())
        for name in ("encoding", "search", "models", "evidence"):
            self.assertTrue(
                (ROOT / "research_tests" / f"test_phase2_{name}.py").is_file(), name
            )

    def test_the_source_snapshot_covers_the_new_location(self):
        snapshot = runner.source_snapshot()
        self.assertIn("test_phase2_encoding.py", snapshot["tests"])
        self.assertIn("test_phase2_repair.py", snapshot["tests"])
        self.assertIn("__init__.py", snapshot["tests"])
        for name, digest in snapshot["tests"].items():
            self.assertEqual(
                digest, runner.file_digest(ROOT / "research_tests" / name), name
            )

    def test_the_frozen_historical_evidence_suite_passes_with_them_present(self):
        """The two failures the blocker recorded, re-run at their new location."""

        environment = dict(os.environ)
        environment["PYTHONPATH"] = f"{ROOT / '.reference'}{os.pathsep}{ROOT}"
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "tests_direct.test_evidence_checker"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=1800,
            env=environment,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-3000:])
        self.assertIn("Ran 64 tests", result.stderr)


# --------------------------------------------------------------------------
# R6 -- the reference manifest
# --------------------------------------------------------------------------


class R6ReferenceManifest(unittest.TestCase):
    """The manifest is read through its declared schema, and its denominator shows."""

    def setUp(self):
        self.contract = runner.Contract(CONTRACT_DIR)

    def test_the_declared_key_is_sha256_and_the_scan_is_not_empty(self):
        manifest = json.loads((ROOT / "reference.json").read_text())
        self.assertIn(runner.REFERENCE_MANIFEST_KEY, manifest)
        self.assertNotIn("files", manifest)
        report = self.contract.verify_locks()
        self.assertEqual(report["status"], runner.PASS, report["findings"])
        self.assertEqual(
            report["entry_counts"]["reference"], len(manifest["sha256"])
        )
        self.assertGreater(report["entry_counts"]["reference"], 0)
        self.assertEqual(
            report["checked"],
            report["entry_counts"]["package"]
            + report["entry_counts"]["baseline"]
            + report["entry_counts"]["reference"]
            + 2,
        )

    def test_the_lead_reproduction_now_fails(self):
        """`.reference/README.md` is a manifest entry the baseline lock omits.

        The lead's probe reported wrong hash for exactly that file and
        `verify_locks` still returned PASS with 58 checks. It must now fail.
        """

        baseline = json.loads((CONTRACT_DIR / "BASELINE_LOCK.json").read_text())
        self.assertNotIn(
            "luminal-challenge/.reference/README.md", baseline["files"],
            "this test needs an entry outside the baseline lock to be meaningful",
        )
        target = ROOT / ".reference" / "README.md"
        original = runner.file_digest
        with patch.object(
            runner, "file_digest",
            side_effect=lambda path: "0" * 64 if Path(path) == target else original(path),
        ):
            report = self.contract.verify_locks()
        self.assertEqual(report["status"], runner.FAIL)
        self.assertTrue(
            any("README.md" in finding for finding in report["findings"]),
            report["findings"],
        )

    def test_a_missing_manifest_key_is_a_failure_not_an_empty_scan(self):
        real = json.loads((ROOT / "reference.json").read_text())
        without = {key: value for key, value in real.items() if key != "sha256"}
        with _reference_manifest(without):
            report = self.contract.verify_locks()
        self.assertEqual(report["status"], runner.FAIL)
        self.assertEqual(report["entry_counts"]["reference"], 0)
        self.assertTrue(
            any("sha256" in finding for finding in report["findings"]),
            report["findings"],
        )

    def test_the_old_key_name_no_longer_verifies_anything(self):
        """Reading `files` was the defect: it verified zero entries silently."""

        real = json.loads((ROOT / "reference.json").read_text())
        renamed = {"url": real["url"], "commit": real["commit"],
                   "files": real["sha256"]}
        with _reference_manifest(renamed):
            report = self.contract.verify_locks()
        self.assertEqual(report["status"], runner.FAIL)
        self.assertEqual(report["entry_counts"]["reference"], 0)

    def test_a_wrong_pinned_commit_is_a_failure(self):
        with patch.object(runner, "REFERENCE_COMMIT", "0" * 40):
            report = self.contract.verify_locks()
        self.assertEqual(report["status"], runner.FAIL)
        self.assertTrue(
            any("pinned commit" in finding for finding in report["findings"]),
            report["findings"],
        )
        self.assertEqual(
            report["reference_commit"],
            json.loads((ROOT / "reference.json").read_text())["commit"],
        )

    def test_a_reference_file_absent_from_the_manifest_is_a_failure(self):
        real = json.loads((ROOT / "reference.json").read_text())
        trimmed = dict(real)
        trimmed["sha256"] = {
            key: value for key, value in real["sha256"].items() if key != "README.md"
        }
        with _reference_manifest(trimmed):
            report = self.contract.verify_locks()
        self.assertEqual(report["status"], runner.FAIL)
        self.assertTrue(
            any("not in the manifest" in finding for finding in report["findings"]),
            report["findings"],
        )


# --------------------------------------------------------------------------
# R1 -- sampled completions are validated and every attempt is retained
# --------------------------------------------------------------------------


class R1SamplingEvidence(unittest.TestCase):
    """Every completed decode runs every case, and every draw reaches a row."""

    def setUp(self):
        self.domain = constant_domain(FIXTURES[0])
        self.cases = len(self.domain.program["cases"])
        self.assertGreater(self.cases, 0)

    def test_the_lead_reproduction_now_calls_the_case_validator(self):
        """Three completions with zero case-validator calls was the finding."""

        sink = runner._ListSink()
        real = machine.check_case
        with patch.object(machine, "check_case", side_effect=real) as spy:
            stream, identities = runner.raw_bit_stream(
                self.domain, "structural_rank", 20260922, 3, 10, sink=sink,
                identity={"program": "probe"},
            )
        self.assertEqual(stream["complete"], 3)
        self.assertEqual(spy.call_count, 3 * self.cases)
        self.assertEqual(stream["case_checks"], 3 * self.cases)
        self.assertEqual(stream["case_failures"], 0)
        self.assertEqual(stream["discrepancies"], [])
        self.assertEqual(len(identities), 1)

    def test_every_attempt_produces_one_raw_row(self):
        sink = runner._ListSink()
        stream, _ = runner.raw_bit_stream(
            se.Domain.from_record(FIXTURES[0]), "structural_rank", 20260922, 250, 30,
            sink=sink, identity={"program": "probe", "program_sha256": "x"},
        )
        self.assertEqual(stream["attempts_drawn"], 250)
        self.assertEqual(stream["raw_rows_written"], 250)
        self.assertEqual(len(sink.rows), 250)
        self.assertEqual(
            sorted(row["attempt"] for row in sink.rows), list(range(250))
        )
        counts = {status: 0 for status in se.STATUSES}
        for row in sink.rows:
            counts[row["status"]] += 1
            self.assertEqual(row["program"], "probe")
            self.assertEqual(row["domain_sha256"], stream["domain_sha256"])
            self.assertEqual(row["codec"], "structural_rank")
            self.assertEqual(row["seed"], 20260922)
            self.assertIsInstance(row["index"], str)
        self.assertEqual(counts[se.COMPLETE], stream["complete"])
        self.assertEqual(counts[se.INVALID_CODE], stream["invalid_code"])
        self.assertEqual(counts[se.DEAD_END], stream["dead_end"])
        self.assertEqual(
            sum(row["cases_checked"] for row in sink.rows), stream["case_checks"]
        )

    def test_completions_are_not_capped_at_fifty(self):
        """The old stream retained at most fifty distinct completed examples."""

        sink = runner._ListSink()
        stream, _ = runner.option_path_stream(
            se.Domain.from_record(FIXTURES[0]), "structural_rank", 20260923, 400, 30,
            sink=sink,
        )
        self.assertEqual(len(stream["completions"]), stream["distinct_complete"])
        self.assertLessEqual(len(stream["complete_examples_excerpt"]), 50)
        if stream["distinct_complete"] > 50:
            self.assertGreater(
                len(stream["completions"]), len(stream["complete_examples_excerpt"])
            )

    def test_a_rejected_completion_is_a_retained_discrepancy_not_a_dead_end(self):
        real = machine.check_case
        state = {"raised": False}

        def once(program, compilation, case):
            if not state["raised"]:
                state["raised"] = True
                raise machine.ProgramError("planted case failure")
            return real(program, compilation, case)

        with patch.object(machine, "check_case", side_effect=once):
            stream, _ = runner.raw_bit_stream(
                self.domain, "structural_rank", 20260922, 3, 10,
                sink=runner._ListSink(),
            )
        self.assertEqual(stream["complete"], 3, "the status is unchanged")
        self.assertEqual(stream["dead_end"], 0, "a defect is never a DEAD_END")
        self.assertEqual(stream["case_failures"], 1)
        self.assertEqual(stream["discrepancy_count"], 1)
        artifact = stream["discrepancies"][0]
        self.assertEqual(artifact["kind"], "sampled_completion_failed_case")
        self.assertIn("planted case failure", artifact["validator_message"])
        for field in ("index", "times", "addresses", "compilation_sha256", "attempt"):
            self.assertIn(field, artifact)

    def test_the_identity_union_is_reconstructible_from_the_rows(self):
        sink = runner._ListSink()
        stream, identities = runner.raw_bit_stream(
            se.Domain.from_record(FIXTURES[0]), "structural_rank", 20260922, 300, 30,
            sink=sink,
        )
        from_rows = {
            row["compilation_sha256"] for row in sink.rows
            if row["status"] == se.COMPLETE
        }
        self.assertEqual(from_rows, identities)
        self.assertEqual(
            sum(stream["identity_multiplicities"].values()), stream["complete"]
        )

    def test_the_stream_refuses_a_sink_that_loses_a_row(self):
        class LossySink(runner._ListSink):
            def write(self, row):
                if row["attempt"] % 2:
                    return
                super().write(row)

        with self.assertRaises(runner.StageBlocked):
            runner.raw_bit_stream(
                se.Domain.from_record(FIXTURES[0]), "structural_rank", 20260922,
                10, 10, sink=LossySink(),
            )


# --------------------------------------------------------------------------
# R4 -- one absolute deadline across construction, search and validation
# --------------------------------------------------------------------------


class R4SharedDeadline(unittest.TestCase):
    """Construction time is debited, and no expired interval is restarted."""

    @classmethod
    def setUpClass(cls):
        cls.program = machine.load_program(
            ROOT / ".reference" / "programs" / "02_scalar_dual_chain.json"
        )
        cls.facts = dcontract.derive(cls.program)
        compiled, _ = dc.compile_with_report(cls.program, optimise=False)
        cls.times = se.issue_cycles_of(cls.program, compiled["bundles"])
        cls.addresses = dict(compiled["scratch"])
        cls.limits = json.loads((CONTRACT_DIR / "PROTOCOL.json").read_text())["budgets"]

    def optimise(self, arm, budget, query, clock=None, **patches):
        captured = []

        def capture(domain, incumbent, search_arm, budget_object, **kwargs):
            captured.append(
                {
                    "budget_seconds": budget_object.seconds,
                    "deadline": kwargs.get("deadline"),
                    "clock": time.perf_counter(),
                }
            )
            return ss.SearchReport(
                arm=search_arm, domain_id=domain.identifier,
                domain_sha256=domain.digest(), status="UNSAT",
                reason="probe", incumbent_product=1,
            )

        stack = contextlib.ExitStack()
        if clock is not None:
            stack.enter_context(
                patch.object(runner.time, "perf_counter", side_effect=lambda: clock[0])
            )
        stack.enter_context(patch.object(runner.ss, "search", side_effect=capture))
        for name, value in patches.items():
            stack.enter_context(patch.object(runner, name, side_effect=value))
        with stack:
            _, _, record = runner.structural_optimise(
                self.program, self.facts, self.times, self.addresses, arm,
                budget, query, 32, self.limits,
            )
        return record, captured

    def test_the_lead_reproduction_no_longer_restarts_an_expired_search(self):
        """A constructor that spends 1.0 s of a 0.01 s allowance ends the query."""

        clock = [0.0]
        original = runner.matched_window_record

        def slow(*args, **kwargs):
            result = original(*args, **kwargs)
            clock[0] += 1.0
            return result

        record, captured = self.optimise(
            "structural_bound", 0.01, 0.01, clock=clock, matched_window_record=slow
        )
        self.assertEqual(captured, [], "search must not be invoked past the deadline")
        self.assertEqual(record["stopped_because"], "deadline")
        self.assertEqual(record["budget_renewals"], 0)
        phases = [item["phase"] for item in record["interrupted_attempts"]]
        self.assertIn("after_construction", phases)
        self.assertEqual(record["statuses"]["UNKNOWN_CONSTRUCTION"], 1)

    def test_construction_time_is_debited_from_the_search_allowance(self):
        clock = [0.0]
        original = runner.matched_window_record

        def slow(*args, **kwargs):
            result = original(*args, **kwargs)
            clock[0] += 0.004
            return result

        record, captured = self.optimise(
            "structural_bound", 1.0, 0.01, clock=clock, matched_window_record=slow
        )
        self.assertTrue(captured, "the search should still have been reached")
        first = captured[0]
        self.assertAlmostEqual(first["budget_seconds"], 0.006, places=9)
        self.assertAlmostEqual(first["deadline"], 0.01, places=9)
        self.assertLess(
            first["budget_seconds"], 0.01,
            "a fresh full query allowance after building is the defect",
        )

    def test_the_expanded_arm_debits_its_construction_too(self):
        clock = [0.0]
        original = runner.whole_program_record

        def slow(*args, **kwargs):
            result = original(*args, **kwargs)
            clock[0] += 1.0
            return result

        record, captured = self.optimise(
            "structural_expanded", 0.01, 0.01, clock=clock, whole_program_record=slow
        )
        self.assertEqual(captured, [])
        self.assertEqual(record["stopped_because"], "deadline")
        self.assertIn(
            "after_construction",
            [item["phase"] for item in record["interrupted_attempts"]],
        )

    def test_search_refuses_to_start_after_the_deadline(self):
        domain = se.Domain.from_record(FIXTURES[0])
        report = ss.search(
            domain, None, "structural_bound", si.Budget(seconds=1.0),
            deadline=time.perf_counter() - 1.0,
        )
        self.assertEqual(report.status, "UNKNOWN")
        self.assertTrue(report.deadline_expired)
        self.assertEqual(report.nodes, 0)
        self.assertNotEqual(report.status, "UNSAT")

    def test_validation_crossing_the_deadline_retains_the_incumbent(self):
        record, domain, incumbent, baseline = _improvable_fixture()
        deadline = [time.perf_counter() + 3600.0]
        real = machine.check_case

        def expire(program, compilation, case):
            # The deadline crosses *inside* the uninterruptible validation call.
            deadline[0] = time.perf_counter() - 1.0
            return real(program, compilation, case)

        with patch.object(machine, "check_case", side_effect=expire):
            report = ss.search(
                domain, incumbent, "structural_dfs", si.Budget(seconds=60.0),
                deadline=_FloatCell(deadline),
            )
        self.assertGreaterEqual(report.interrupted_validations, 1)
        self.assertTrue(report.deadline_expired)
        self.assertEqual(report.status, "UNKNOWN")
        self.assertEqual(
            report.best_product, baseline,
            "the previously validated incumbent must be retained",
        )
        self.assertFalse(report.improved)

    def test_a_deadline_before_validation_is_an_accounted_interruption(self):
        record, domain, incumbent, baseline = _improvable_fixture()
        deadline = [time.perf_counter() + 3600.0]
        real_objective = se.objective
        seen = {"completions": 0}

        def objective(facts, times, addresses):
            result = real_objective(facts, times, addresses)
            if result[2] < baseline:
                seen["completions"] += 1
                deadline[0] = time.perf_counter() - 1.0
            return result

        with patch.object(ss.se, "objective", side_effect=objective):
            report = ss.search(
                domain, incumbent, "structural_dfs", si.Budget(seconds=60.0),
                deadline=_FloatCell(deadline),
            )
        self.assertGreaterEqual(seen["completions"], 1)
        self.assertGreaterEqual(report.interrupted_validations, 1)
        self.assertEqual(report.validations, 0, "nothing was paid for past the deadline")
        self.assertEqual(report.best_product, baseline)

    def test_the_declared_node_cap_is_exercised(self):
        domain = se.Domain.from_record(FIXTURES[0])
        report = ss.search(
            domain, None, "structural_dfs",
            si.Budget(seconds=60.0, max_visited=1, max_records=20000),
        )
        self.assertEqual(report.status, "UNKNOWN")
        self.assertIn("visited", report.reason)

    def test_the_declared_validation_cap_is_exercised(self):
        """A cap of one validation stops the second one, on a domain that has one."""

        domain = None
        for record in FIXTURES:
            candidate = se.Domain.from_record(record)
            uncapped = ss.search(
                candidate, None, "structural_dfs", si.Budget(seconds=60.0)
            )
            if uncapped.validations >= 2:
                domain = candidate
                break
        if domain is None:
            self.skipTest("no locked fixture pays for two validations")
        report = ss.search(
            domain, None, "structural_dfs",
            si.Budget(seconds=60.0, max_visited=50000, max_records=1),
        )
        self.assertEqual(report.status, "UNKNOWN")
        self.assertIn("record", report.reason)
        self.assertLessEqual(report.validations, 1)

    def test_no_positive_budget_is_manufactured_after_expiry(self):
        text = (ROOT / "research" / "run_structural_experiments.py").read_text()
        self.assertNotIn("max(remaining, 1e-6)", text)
        self.assertIn("remaining <= 0", text)


class _FloatCell:
    """A deadline whose value is re-read at every comparison.

    ``search`` evaluates ``time.perf_counter() >= deadline``; the left operand is
    a real float, so the reflected ``__le__`` below is what answers. A mutable
    cell makes "the deadline passed *during* an uninterruptible call" an actual
    event rather than a simulated one.
    """

    def __init__(self, cell):
        self.cell = cell

    def __le__(self, other):
        return self.cell[0] <= other

    def __lt__(self, other):
        return self.cell[0] < other

    def __ge__(self, other):
        return self.cell[0] >= other

    def __gt__(self, other):
        return self.cell[0] > other

    def __float__(self):
        return float(self.cell[0])


def _improvable_fixture():
    """A locked fixture whose declared domain holds a strict improvement.

    A deadline test needs a candidate worth validating: on a fixture whose
    incumbent is already optimal no validation happens and the test would pass
    without exercising anything.
    """

    from research import structural_oracle as so

    budgets = runner.Contract(CONTRACT_DIR).budgets
    for record in FIXTURES:
        domain = se.Domain.from_record(record)
        if domain.incumbent is None:
            continue
        incumbent = se.normalise_compilation(domain.facts, record["incumbent"])
        baseline = se.objective(
            domain.facts,
            se.issue_cycles_of(domain.program, incumbent["bundles"]),
            dict(incumbent["scratch"]),
        )[2]
        enumeration = so.enumerate_feasible(record, budgets["oracle_cartesian_max"])
        minimum = min(
            (item["product"] for item in enumeration["feasible"]), default=None
        )
        if minimum is not None and minimum < baseline:
            return record, domain, incumbent, baseline
    raise unittest.SkipTest("no locked fixture admits a strict improvement")


# --------------------------------------------------------------------------
# R5 -- the conditional large-domain model arm
# --------------------------------------------------------------------------


class R5ConditionalModelArm(unittest.TestCase):
    """The arm is routed, measured, required conditionally, and lazy."""

    @classmethod
    def setUpClass(cls):
        cls.program = machine.load_program(
            ROOT / ".reference" / "programs" / "02_scalar_dual_chain.json"
        )
        cls.facts = dcontract.derive(cls.program)
        compiled, _ = dc.compile_with_report(cls.program, optimise=False)
        cls.times = se.issue_cycles_of(cls.program, compiled["bundles"])
        cls.addresses = dict(compiled["scratch"])
        cls.limits = json.loads((CONTRACT_DIR / "PROTOCOL.json").read_text())["budgets"]

    def test_the_lead_reproduction_no_longer_raises(self):
        """`unknown search arm 'structural_model'` was the finding."""

        _, _, record = runner.structural_optimise(
            self.program, self.facts, self.times, self.addresses,
            runner.MODEL_ARM, 0.1, 0.1, 4, self.limits, elite_fraction=0.1,
        )
        self.assertEqual(record["arm"], runner.MODEL_ARM)
        self.assertIsNotNone(record["phases"])
        self.assertIn("search_seconds", record["phases"])
        self.assertIn("proposal_seconds", record["phases"])

    def test_the_arm_never_reaches_the_dfs_arm_list(self):
        self.assertNotIn(runner.MODEL_ARM, ss.ARMS)
        with self.assertRaises(ValueError):
            ss.search(
                se.Domain.from_record(FIXTURES[0]), None, runner.MODEL_ARM,
                si.Budget(seconds=0.01),
            )

    def test_each_query_splits_one_fixed_allowance_in_half(self):
        seen = []
        original = runner.ss.search

        def capture(domain, incumbent, arm, budget, **kwargs):
            seen.append({"arm": arm, "deadline": kwargs.get("deadline")})
            return original(domain, incumbent, arm, budget, **kwargs)

        with patch.object(runner.ss, "search", side_effect=capture):
            _, _, record = runner.structural_optimise(
                self.program, self.facts, self.times, self.addresses,
                runner.MODEL_ARM, 0.2, 0.1, 2, self.limits, elite_fraction=0.1,
            )
        self.assertTrue(seen)
        for call in seen:
            self.assertEqual(
                call["arm"], "structural_bound",
                "the search half is the bounded arm, not a new algorithm",
            )
        for query in record["queries"]:
            if "allowance_seconds" not in query:
                continue
            self.assertAlmostEqual(
                query["phase_split_seconds"], query["allowance_seconds"] / 2, places=9
            )
            self.assertLessEqual(query["allowance_seconds"], 0.1 + 1e-9)

    def test_no_complete_observation_means_model_unavailable_and_no_fallback(self):
        empty = ss.SearchReport(
            arm="structural_bound", domain_id="probe", domain_sha256="0" * 64,
            status="UNSAT", reason="probe", incumbent_product=10 ** 9,
        )
        with patch.object(runner.ss, "search", return_value=empty):
            _, _, record = runner.structural_optimise(
                self.program, self.facts, self.times, self.addresses,
                runner.MODEL_ARM, 0.2, 0.1, 3, self.limits, elite_fraction=0.1,
            )
        modelled = [query["model"] for query in record["queries"] if "model" in query]
        self.assertTrue(modelled)
        for model in modelled:
            self.assertEqual(model["status"], runner.NOT_APPLICABLE)
            self.assertIn("no complete observation", model["reason"])
        self.assertEqual(record["phases"]["proposals"], 0)
        self.assertGreaterEqual(record["phases"]["model_unavailable"], 1)

    def test_the_authorised_branch_builds_a_model_and_walks_its_proposals(self):
        """The positive branch, on a controlled stage fixture.

        On the public programs the matched window domains hold no completion at
        all, so the model half is never reachable there and the real run cannot
        exercise it. `many_ready_1` is a locked fixture whose domain does hold
        completions; substituting it for the constructed matched domain drives
        the search half, the cover, and the proposal walk in one pass. Nothing
        here fabricates an H4 outcome: it tests the implementation, and P4 was
        never run.
        """

        record = next(item for item in FIXTURES if item["id"] == "many_ready_1")
        program = record["program"]
        facts = dcontract.derive(program)
        compiled, _ = dc.compile_with_report(program, optimise=False)
        times = se.issue_cycles_of(program, compiled["bundles"])
        addresses = dict(compiled["scratch"])
        with patch.object(
            runner, "matched_window_record",
            side_effect=lambda *args, **kwargs: json.loads(json.dumps(record)),
        ):
            _, _, report = runner.structural_optimise(
                program, facts, times, addresses, runner.MODEL_ARM,
                2.0, 1.0, 2, self.limits, elite_fraction=0.1,
            )
        phases = report["phases"]
        self.assertGreater(phases["observations"], 0)
        self.assertGreater(phases["elite"], 0)
        self.assertGreater(phases["proposals"], 0)
        self.assertEqual(phases["model_unavailable"], 0)
        models = [
            query["model"] for query in report["queries"]
            if isinstance(query.get("model"), dict)
        ]
        self.assertTrue(models)
        for model in models:
            self.assertEqual(model["status"], runner.PASS)
            self.assertEqual(model["cover_status"], "COMPLETE")
            self.assertGreater(model["cover_cubes"], 0)
            counts = model["counts"]
            self.assertEqual(
                counts["attempted"],
                counts["duplicate"] + counts["invalid_code"] + counts["dead_end"]
                + counts["interrupted"] + counts["complete"],
                "every attempted proposal must fall in exactly one bucket",
            )
        self.assertEqual(report["discrepancy_count"], 0)

    def test_the_blocked_branch_runs_no_model_arm_at_all(self):
        """H4 blocked: the arm is absent from the schedule and from membership."""

        contract = runner.Contract(CONTRACT_DIR)
        programs = [{"program_sha256": "a", "path": "x"}]
        schedule = runner.arm_schedule(
            programs, contract.budgets["optimisation_seconds"],
            ("accepted_bootstrap", "accepted_default"),
            ("accepted_budgeted",) + runner.STRUCTURAL_ARMS,
            random.Random(contract.seeds["arm_order"]),
            contract.statistics["timing_repetitions"],
        )
        self.assertFalse(
            any(entry[4] == runner.MODEL_ARM for entry in schedule),
            "an unauthorised arm must never be scheduled",
        )
        with_model = runner.arm_schedule(
            programs, contract.budgets["optimisation_seconds"],
            ("accepted_bootstrap", "accepted_default"),
            ("accepted_budgeted",) + runner.STRUCTURAL_ARMS + (runner.MODEL_ARM,),
            random.Random(contract.seeds["arm_order"]),
            contract.statistics["timing_repetitions"],
        )
        self.assertTrue(any(entry[4] == runner.MODEL_ARM for entry in with_model))

    def test_the_search_half_observes_the_candidates_it_pays_for(self):
        domain = se.Domain.from_record(FIXTURES[0])
        observations = []
        report = ss.search(
            domain, None, "structural_dfs", si.Budget(seconds=30.0),
            observe=observations.append,
        )
        self.assertEqual(len(observations), report.completions - report.duplicate_hits)
        for item in observations:
            self.assertEqual(
                item["product"], item["cycles"] * item["scratch"]
            )
            self.assertIn("compilation", item)

    # -- lazy union ------------------------------------------------------

    def test_the_expanded_union_yields_its_first_proposal_without_materialising(self):
        """A 40-bit cube with 30 free coordinates has 2**30 members."""

        cube = si.Cube(40, 0, (1 << 30) - 1)
        started = time.perf_counter()
        stream = sm.proposals("model_expand", 40, [0], (cube,), set(), None)
        first, duplicate = next(stream)
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 1.0, "the union must not be enumerated eagerly")
        self.assertEqual(first, 0)
        self.assertFalse(duplicate)
        stream.close()

    def test_the_union_is_ascending_and_deduplicated(self):
        cubes = (si.Cube(4, 0b0000, 0b0011), si.Cube(4, 0b0010, 0b0001))
        members = list(sm.ordered_union(cubes))
        self.assertEqual(members, sorted(set(members)))
        self.assertEqual(members, [0, 1, 2, 3])

    def test_cover_members_agrees_with_the_lazy_union(self):
        cubes = (si.Cube(6, 0b000000, 0b000101), si.Cube(6, 0b001000, 0b010000))
        self.assertEqual(sm.cover_members(cubes), list(sm.ordered_union(cubes)))

    def test_the_union_consults_the_budget_and_stops(self):
        cube = si.Cube(40, 0, (1 << 30) - 1)
        calls = [0]

        class Stop(Exception):
            pass

        def check():
            calls[0] += 1
            if calls[0] > 5:
                raise Stop

        stream = sm.proposals(
            "model_expand", 40, [0], (cube,), set(), None, budget_check=check
        )
        with self.assertRaises(Stop):
            for _ in stream:
                pass
        self.assertLessEqual(calls[0], 6)

    # -- membership and status --------------------------------------------

    def test_the_arm_enters_the_expected_membership_only_when_authorised(self):
        contract = runner.Contract(CONTRACT_DIR)
        programs = [{"program_sha256": "a", "path": "x"}]
        budgets = contract.budgets["optimisation_seconds"]
        repetitions = contract.statistics["timing_repetitions"]
        without = runner.expected_keys(
            programs, budgets, ("accepted_bootstrap",),
            ("accepted_budgeted",) + runner.STRUCTURAL_ARMS, repetitions,
        )
        with_model = runner.expected_keys(
            programs, budgets, ("accepted_bootstrap",),
            ("accepted_budgeted",) + runner.STRUCTURAL_ARMS + (runner.MODEL_ARM,),
            repetitions,
        )
        self.assertEqual(
            len(with_model) - len(without), len(budgets) * repetitions
        )
        self.assertTrue(any(key[2] == runner.MODEL_ARM for key in with_model))
        self.assertFalse(any(key[2] == runner.MODEL_ARM for key in without))

    def test_the_worker_accepts_the_model_arm(self):
        self.assertIn(runner.MODEL_ARM, runner.WORKER_ARMS)


class R5CheckerRequiresModelRows(unittest.TestCase):
    """The checker refuses an authorised arm with no measured row."""

    def build(self, authorised, rows):
        temporary = Path(tempfile.mkdtemp(prefix="phase2-model-"))
        self.addCleanup(shutil.rmtree, temporary, ignore_errors=True)
        run = temporary / "run"
        (run / "p5").mkdir(parents=True)
        (run / "p5" / "summary.json").write_text(
            json.dumps(
                {
                    "stage": "p5",
                    "pooled": False,
                    "model_arm": {
                        "arm": runner.MODEL_ARM,
                        "status": runner.PASS if authorised else runner.NOT_RUN,
                        "authorised": authorised,
                        "measured_rows": len(rows),
                        "reason": "probe",
                    },
                    "public": {"comparisons": {}},
                    "heldout": {"comparisons": {}},
                }
            )
        )
        runner.write_jsonl(run / "p5" / "public_rows.jsonl", rows or [{"arm": "x"}])
        runner.write_jsonl(run / "p5" / "heldout_rows.jsonl", rows or [{"arm": "x"}])
        instance = checker.Checker(run, CONTRACT_DIR)
        instance.check_p5(None)
        return instance

    def test_authorised_without_rows_is_a_finding(self):
        instance = self.build(True, [])
        names = [finding["check"] for finding in instance.findings]
        self.assertIn("p5.model_arm_unmeasured", names)
        self.assertIn("p5.model_arm_missing_rows", names)

    def test_authorised_with_rows_is_accepted(self):
        rows = [{"arm": runner.MODEL_ARM, "program_sha256": "a"}]
        instance = self.build(True, rows)
        names = [finding["check"] for finding in instance.findings]
        self.assertNotIn("p5.model_arm_unmeasured", names)
        self.assertNotIn("p5.model_arm_missing_rows", names)

    def test_unauthorised_rows_are_a_finding(self):
        temporary = Path(tempfile.mkdtemp(prefix="phase2-model-"))
        self.addCleanup(shutil.rmtree, temporary, ignore_errors=True)
        run = temporary / "run"
        (run / "p5").mkdir(parents=True)
        (run / "p5" / "summary.json").write_text(
            json.dumps(
                {
                    "stage": "p5", "pooled": False,
                    "model_arm": {
                        "arm": runner.MODEL_ARM, "status": runner.NOT_RUN,
                        "authorised": False, "reason": "probe",
                    },
                    "public": {"comparisons": {}}, "heldout": {"comparisons": {}},
                }
            )
        )
        rows = [{"arm": runner.MODEL_ARM, "program_sha256": "a"}]
        runner.write_jsonl(run / "p5" / "public_rows.jsonl", rows)
        runner.write_jsonl(run / "p5" / "heldout_rows.jsonl", rows)
        instance = checker.Checker(run, CONTRACT_DIR)
        instance.check_p5(None)
        self.assertIn(
            "p5.model_arm_unauthorised",
            [finding["check"] for finding in instance.findings],
        )


# --------------------------------------------------------------------------
# A real control run, for R2 and R3
# --------------------------------------------------------------------------


class RepairControl:
    """A valid P0-P1 run under a temporary contract with a smaller sample."""

    root: Path
    contract: Path
    workspace: Path
    exit_code: int

    @classmethod
    def build(cls, attempts=60, seconds=20):
        cls.workspace = Path(
            tempfile.mkdtemp(prefix="_unit_repair_", dir=str(runner.RESULTS))
        )
        cls.contract = cls.workspace / "contract"
        shutil.copytree(CONTRACT_DIR, cls.contract)
        protocol = json.loads((cls.contract / "PROTOCOL.json").read_text())
        protocol["sampling"]["attempts_per_program_per_stream"] = attempts
        protocol["sampling"]["seconds_per_program_per_stream"] = seconds
        (cls.contract / "PROTOCOL.json").write_text(
            json.dumps(protocol, indent=2, sort_keys=True)
        )
        results = cls.workspace / "runs"
        results.mkdir()
        buffer = io.StringIO()
        with patch.object(runner, "RESULTS", results):
            with contextlib.redirect_stdout(buffer):
                # The whole stage graph: P1 needs P0, and P2-P5 are blocked by
                # P1's coverage gate, so nothing expensive runs after it.
                cls.exit_code = runner.main(
                    ["--stage", "all", "--run-id", "control",
                     "--contract", str(cls.contract)]
                )
        cls.root = results / "control"
        cls.banner = buffer.getvalue()
        return cls

    @classmethod
    def destroy(cls):
        shutil.rmtree(cls.workspace, ignore_errors=True)


class R2EvidenceChecker(unittest.TestCase):
    """The erased-evidence probe, on a new valid control."""

    @classmethod
    def setUpClass(cls):
        cls.control = RepairControl.build()
        if not (cls.control.root / "p1" / "summary.json").is_file():
            raise unittest.SkipTest(f"the control run did not reach P1: {cls.control.banner}")

    @classmethod
    def tearDownClass(cls):
        RepairControl.destroy()

    def check(self, run):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = checker.main(
                ["--run", str(run), "--contract", str(self.control.contract)]
            )
        return code, json.loads(buffer.getvalue())

    def copy(self):
        temporary = Path(tempfile.mkdtemp(prefix="phase2-erase-"))
        self.addCleanup(shutil.rmtree, temporary, ignore_errors=True)
        destination = temporary / "copy"
        shutil.copytree(self.control.root, destination)
        return destination

    @staticmethod
    def resync(run):
        """Recompute every stage digest and row count, as the review requires."""

        path = Path(run) / "manifest.json"
        manifest = json.loads(path.read_text())
        digests = dict(manifest.get("stage_digests") or {})
        for stage in ("preflight", "p0", "p1", "p2", "p3", "p4", "p5"):
            summary = Path(run) / stage / "summary.json"
            if summary.is_file():
                digests[stage] = runner.file_digest(summary)
        manifest["stage_digests"] = digests
        manifest["row_counts"] = {
            str(item.relative_to(run)): sum(
                1 for line in item.read_text().splitlines() if line.strip()
            )
            for item in sorted(Path(run).rglob("*.jsonl"))
        }
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    # -- the control -------------------------------------------------------

    def test_00_the_control_is_accepted_as_internally_consistent(self):
        code, report = self.check(self.control.root)
        self.assertEqual(
            report["findings"], [], json.dumps(report["findings"], indent=2)[:4000]
        )
        self.assertTrue(report["artifacts_internally_consistent"])
        # The reduced sample misses the coverage minimum, exactly as the real
        # campaign does; that is exit 2, not a correctness failure.
        self.assertEqual(code, checker.EXIT_USAGE)
        self.assertEqual(report["inconclusive_count"], 1)
        self.assertEqual(report["stage_status"]["p1"], runner.INCONCLUSIVE)

    def test_the_lead_erased_evidence_probe_is_now_rejected(self):
        """The exact corruption of LEAD_REVIEW R2, with the hashes recomputed."""

        run = self.copy()
        summary = json.loads((run / "p1" / "summary.json").read_text())
        summary["fixtures"] = []
        summary["public_coverage"] = []
        (run / "p1" / "summary.json").write_text(json.dumps(summary))
        (run / "p1" / "sampling_streams.jsonl").write_text("")
        for name in ("decoder_rows.jsonl", "oracle_domains.jsonl",
                     "sampling_attempts.jsonl", "sampling_identities.jsonl"):
            (run / "p1" / name).unlink()
        gates = json.loads((run / "gates.json").read_text())
        gates["p1"]["status"] = runner.PASS
        (run / "gates.json").write_text(json.dumps(gates))
        self.resync(run)

        code, report = self.check(run)
        self.assertEqual(code, checker.EXIT_FAILURE)
        self.assertFalse(report["artifacts_complete"])
        self.assertGreater(report["finding_count"], 0)
        names = {finding["check"] for finding in report["findings"]}
        self.assertIn("p1.fixture_membership", names)
        self.assertIn("p1.raw_artifacts", names)
        self.assertIn("p1.coverage_membership", names)

    def test_an_emptied_attempt_file_alone_is_rejected(self):
        run = self.copy()
        (run / "p1" / "sampling_attempts.jsonl").write_text("")
        self.resync(run)
        code, report = self.check(run)
        self.assertEqual(code, checker.EXIT_FAILURE)
        self.assertIn(
            "p1.raw_artifacts", {finding["check"] for finding in report["findings"]}
        )

    def test_a_trimmed_attempt_file_fails_reconciliation(self):
        run = self.copy()
        rows = runner.read_jsonl(run / "p1" / "sampling_attempts.jsonl")
        runner.write_jsonl(run / "p1" / "sampling_attempts.jsonl", rows[:-5])
        self.resync(run)
        code, report = self.check(run)
        self.assertEqual(code, checker.EXIT_FAILURE)
        names = {finding["check"] for finding in report["findings"]}
        self.assertTrue(
            names & {"p1.raw_reconciliation", "p1.raw_status_counts",
                     "p1.raw_attempt_indices"},
            names,
        )

    def test_a_zeroed_case_count_on_a_completion_is_rejected(self):
        run = self.copy()
        rows = runner.read_jsonl(run / "p1" / "sampling_attempts.jsonl")
        for row in rows:
            if row["status"] == se.COMPLETE:
                row["cases_checked"] = 0
                break
        else:
            self.skipTest("the control sampled no completion to mutate")
        runner.write_jsonl(run / "p1" / "sampling_attempts.jsonl", rows)
        self.resync(run)
        code, report = self.check(run)
        self.assertEqual(code, checker.EXIT_FAILURE)
        self.assertIn(
            "p1.case_denominator", {finding["check"] for finding in report["findings"]}
        )

    def test_an_inflated_coverage_count_is_recomputed_and_rejected(self):
        run = self.copy()
        summary = json.loads((run / "p1" / "summary.json").read_text())
        summary["public_coverage"][0]["distinct_complete_union"] = 10 ** 6
        summary["public_coverage"][0]["meets_minimum"] = True
        summary["coverage_met"] = True
        (run / "p1" / "summary.json").write_text(json.dumps(summary))
        self.resync(run)
        code, report = self.check(run)
        self.assertEqual(code, checker.EXIT_FAILURE)
        names = {finding["check"] for finding in report["findings"]}
        self.assertIn("p1.coverage_recount", names)
        self.assertIn("p1.coverage_met", names)

    def test_a_dropped_identity_union_row_is_rejected(self):
        run = self.copy()
        rows = runner.read_jsonl(run / "p1" / "sampling_identities.jsonl")
        runner.write_jsonl(run / "p1" / "sampling_identities.jsonl", rows[1:])
        self.resync(run)
        code, report = self.check(run)
        self.assertEqual(code, checker.EXIT_FAILURE)
        self.assertIn(
            "p1.union_rows", {finding["check"] for finding in report["findings"]}
        )

    def test_a_rewritten_status_in_a_raw_row_fails_the_redecode(self):
        run = self.copy()
        rows = runner.read_jsonl(run / "p1" / "sampling_attempts.jsonl")
        for row in rows:
            if row["status"] == se.DEAD_END:
                row["status"] = se.INVALID_CODE
                break
        runner.write_jsonl(run / "p1" / "sampling_attempts.jsonl", rows)
        self.resync(run)
        code, report = self.check(run)
        self.assertEqual(code, checker.EXIT_FAILURE)
        names = {finding["check"] for finding in report["findings"]}
        self.assertTrue(names & {"p1.legality_recompute", "p1.raw_status_counts"}, names)

    def test_a_missing_amendment_record_is_rejected(self):
        run = self.copy()
        manifest = json.loads((run / "manifest.json").read_text())
        manifest.pop("amendment_files")
        (run / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
        code, report = self.check(run)
        self.assertEqual(code, checker.EXIT_FAILURE)
        self.assertIn(
            "provenance.amendment", {finding["check"] for finding in report["findings"]}
        )

    def test_a_tampered_amendment_hash_is_rejected(self):
        run = self.copy()
        manifest = json.loads((run / "manifest.json").read_text())
        name = sorted(manifest["amendment_files"])[0]
        manifest["amendment_files"][name] = "0" * 64
        (run / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
        code, report = self.check(run)
        self.assertEqual(code, checker.EXIT_FAILURE)
        self.assertIn(
            "provenance.amendment", {finding["check"] for finding in report["findings"]}
        )

    def test_a_failed_command_cannot_be_labelled_complete(self):
        run = self.copy()
        runner.write_jsonl(
            run / "commands.jsonl",
            [{"command": ["probe"], "exit_code": 1, "timed_out": False,
              "process_seconds": 0.0, "spec": {}}],
        )
        self.resync(run)
        code, report = self.check(run)
        self.assertEqual(code, checker.EXIT_FAILURE)
        self.assertIn(
            "commands.exit_codes", {finding["check"] for finding in report["findings"]}
        )

    def test_a_wrong_row_count_in_the_manifest_is_rejected(self):
        run = self.copy()
        manifest = json.loads((run / "manifest.json").read_text())
        key = sorted(manifest["row_counts"])[0]
        manifest["row_counts"][key] += 1
        (run / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
        code, report = self.check(run)
        self.assertEqual(code, checker.EXIT_FAILURE)
        self.assertIn(
            "commands.row_counts", {finding["check"] for finding in report["findings"]}
        )

    def test_a_gate_status_the_protocol_does_not_declare_is_rejected(self):
        run = self.copy()
        gates = json.loads((run / "gates.json").read_text())
        gates["p1"]["status"] = "MOSTLY_FINE"
        (run / "gates.json").write_text(json.dumps(gates))
        self.resync(run)
        code, report = self.check(run)
        self.assertEqual(code, checker.EXIT_FAILURE)
        self.assertIn(
            "gates.status_vocabulary",
            {finding["check"] for finding in report["findings"]},
        )

    def test_an_origin_claim_that_does_not_recompute_is_rejected(self):
        run = self.copy()
        summary = json.loads((run / "p1" / "summary.json").read_text())
        for entry in summary["fixtures"]:
            if entry.get("origin_is_incumbent"):
                key = sorted(entry["origin_is_incumbent"])[0]
                entry["origin_is_incumbent"][key] = not entry["origin_is_incumbent"][key]
                break
        else:
            self.skipTest("no fixture recorded an origin claim")
        (run / "p1" / "summary.json").write_text(json.dumps(summary))
        self.resync(run)
        code, report = self.check(run)
        self.assertEqual(code, checker.EXIT_FAILURE)
        self.assertIn(
            "p1.origin_is_incumbent",
            {finding["check"] for finding in report["findings"]},
        )


class R2IntervalRecomputation(unittest.TestCase):
    """Reported intervals are recomputed from raw rows, not label-checked."""

    def setUp(self):
        self.contract = runner.Contract(CONTRACT_DIR)
        self.rows = []
        programs = ["a", "b", "c", "d"]
        for index, program in enumerate(programs):
            for arm, product in (("accepted_budgeted", 40 + index),
                                 ("structural_bound", 30 + index)):
                for repetition in range(2):
                    self.rows.append(
                        {
                            "program_sha256": program, "arm": arm,
                            "budget_seconds": 0.1, "search_seed": None,
                            "repetition": repetition, "product": product,
                            "cycles": 1, "scratch": product, "cases": 2,
                            "failed_row": False, "discrepancy_count": 0,
                        }
                    )
        self.families = {program: "public" for program in programs}

    def recomputed(self):
        return runner.paired_log_ratio_analysis(
            self.rows, self.families, "accepted_budgeted", "structural_bound",
            0.1, self.contract,
        )

    def instance(self):
        temporary = Path(tempfile.mkdtemp(prefix="phase2-interval-"))
        self.addCleanup(shutil.rmtree, temporary, ignore_errors=True)
        run = temporary / "run"
        run.mkdir()
        return checker.Checker(run, CONTRACT_DIR)

    def test_the_faithful_report_is_accepted(self):
        entry = self.recomputed()
        instance = self.instance()
        instance.recompute_comparisons(
            "probe", {"structural_bound_vs_accepted_budgeted@0.1": entry},
            self.rows, self.families,
        )
        self.assertEqual(instance.findings, [])

    def test_a_widened_interval_is_rejected(self):
        entry = json.loads(json.dumps(self.recomputed()))
        key = sorted(entry["interval"]["intervals"])[0]
        entry["interval"]["intervals"][key] = [0.5, 0.9]
        instance = self.instance()
        instance.recompute_comparisons(
            "probe", {"structural_bound_vs_accepted_budgeted@0.1": entry},
            self.rows, self.families,
        )
        self.assertIn(
            "probe.comparison_interval",
            {finding["check"] for finding in instance.findings},
        )

    def test_a_moved_point_estimate_is_rejected(self):
        entry = json.loads(json.dumps(self.recomputed()))
        entry["interval"]["point_estimate"] += 1.0
        instance = self.instance()
        instance.recompute_comparisons(
            "probe", {"structural_bound_vs_accepted_budgeted@0.1": entry},
            self.rows, self.families,
        )
        self.assertIn(
            "probe.comparison_point_estimate",
            {finding["check"] for finding in instance.findings},
        )

    def test_an_inflated_win_count_is_rejected(self):
        entry = json.loads(json.dumps(self.recomputed()))
        entry["wins"] += 3
        instance = self.instance()
        instance.recompute_comparisons(
            "probe", {"structural_bound_vs_accepted_budgeted@0.1": entry},
            self.rows, self.families,
        )
        self.assertIn(
            "probe.comparison_recount",
            {finding["check"] for finding in instance.findings},
        )

    def test_comparisons_without_rows_are_rejected(self):
        instance = self.instance()
        instance.recompute_comparisons(
            "probe", {"x": self.recomputed()}, [], self.families
        )
        self.assertIn(
            "probe.comparison_rows",
            {finding["check"] for finding in instance.findings},
        )

    def test_an_empty_comparison_set_is_rejected(self):
        instance = self.instance()
        instance.recompute_comparisons("probe", {}, self.rows, self.families)
        self.assertIn(
            "probe.comparisons_empty",
            {finding["check"] for finding in instance.findings},
        )


class R2P4Recomputation(unittest.TestCase):
    """The H4 gate is recomputed from the retained model rows."""

    def rows(self):
        contract = runner.Contract(CONTRACT_DIR)
        rows = []
        for record in contract.fixtures[:4]:
            semantic = se.program_semantic_digest(record["program"])
            for arm, product in (("model_expand", 10), ("one_bit", 20),
                                 ("uniform_bits", 20), ("empirical_cover", 20)):
                seeds = contract.seeds["search"][:1] if arm == "uniform_bits" else [None]
                for seed in seeds:
                    rows.append(
                        {
                            "fixture_id": record["id"], "family": record["family"],
                            "semantic_sha256": semantic, "arm": arm,
                            "budget_seconds": 0.1, "search_seed": seed,
                            "repetition": 0, "status": runner.PASS,
                            "failed_row": False, "best_test_product": product,
                            "training_best_product": 100,
                            "counts": {
                                "attempted": 1, "duplicate": 0, "invalid_code": 0,
                                "dead_end": 0, "interrupted": 0, "complete": 1,
                                "novel": 1, "test_proposals": 1,
                                "test_discoveries": 0, "exhausted": True,
                            },
                        }
                    )
        return rows, contract

    def instance(self):
        temporary = Path(tempfile.mkdtemp(prefix="phase2-p4-"))
        self.addCleanup(shutil.rmtree, temporary, ignore_errors=True)
        run = temporary / "run"
        run.mkdir()
        return checker.Checker(run, CONTRACT_DIR)

    def test_a_faithful_summary_is_accepted(self):
        rows, contract = self.rows()
        analysis = runner.p4_contrasts(rows, contract)
        instance = self.instance()
        instance.recompute_p4_contrasts(analysis, rows)
        self.assertEqual(instance.findings, [])

    def test_a_flipped_advancement_flag_is_rejected(self):
        rows, contract = self.rows()
        analysis = json.loads(json.dumps(runner.p4_contrasts(rows, contract)))
        analysis["advance_to_model_arm"] = not analysis["advance_to_model_arm"]
        instance = self.instance()
        instance.recompute_p4_contrasts(analysis, rows)
        self.assertIn(
            "p4.contrast_recount",
            {finding["check"] for finding in instance.findings},
        )

    def test_a_moved_gate_bound_is_rejected(self):
        rows, contract = self.rows()
        analysis = json.loads(json.dumps(runner.p4_contrasts(rows, contract)))
        analysis["h4_gate_lower_bounds"]["one_bit"] = 99.0
        instance = self.instance()
        instance.recompute_p4_contrasts(analysis, rows)
        self.assertIn(
            "p4.gate_bounds", {finding["check"] for finding in instance.findings}
        )

    def test_contrasts_without_rows_are_rejected(self):
        instance = self.instance()
        instance.recompute_p4_contrasts({"contrasts": {}}, [])
        self.assertIn(
            "p4.contrast_rows", {finding["check"] for finding in instance.findings}
        )


# --------------------------------------------------------------------------
# R3 -- a dependent stage cannot be entered on a failed dependency
# --------------------------------------------------------------------------


class R3DependencyGate(unittest.TestCase):
    """`--inputs` obeys the same gate as a local dependency."""

    @classmethod
    def setUpClass(cls):
        cls.control = RepairControl.build()
        if not (cls.control.root / "manifest.json").is_file():
            raise unittest.SkipTest(f"no control run: {cls.control.banner}")
        gates = json.loads((cls.control.root / "gates.json").read_text())
        if gates["p1"]["status"] != runner.INCONCLUSIVE:
            raise unittest.SkipTest(
                f"the control's P1 is {gates['p1']['status']}, not INCONCLUSIVE"
            )

    @classmethod
    def tearDownClass(cls):
        RepairControl.destroy()

    def run_stage(self, stage, inputs, run_id):
        entered = []

        def stub(run):
            entered.append(run.prior("p1"))
            return {"stage": stage, "regression_probe_only": True}

        results = Path(tempfile.mkdtemp(prefix="phase2-resume-",
                                       dir=str(self.control.workspace)))
        self.addCleanup(shutil.rmtree, results, ignore_errors=True)
        buffer = io.StringIO()
        with patch.object(runner, "RESULTS", results), \
                patch.dict(runner.STAGE_FUNCTIONS, {stage: stub}):
            with contextlib.redirect_stdout(buffer):
                code = runner.main(
                    ["--stage", stage, "--run-id", run_id,
                     "--contract", str(self.control.contract),
                     "--inputs", str(inputs)]
                )
        gates = json.loads((results / run_id / "gates.json").read_text())
        return code, entered, gates

    def test_the_lead_reproduction_no_longer_enters_p2(self):
        """Exit 0 with the stub entered on `coverage_met=false` was the finding."""

        code, entered, gates = self.run_stage("p2", self.control.root, "probe_p2")
        self.assertEqual(entered, [], "the stage body must not be reached")
        self.assertNotEqual(code, runner.EXIT_OK)
        self.assertEqual(gates["p2"]["status"], runner.BLOCKED)
        self.assertIn("p1", gates["p2"]["reason"])
        self.assertIn(runner.INCONCLUSIVE, gates["p2"]["reason"])

    def test_p3_is_blocked_on_the_same_dependency(self):
        code, entered, gates = self.run_stage("p3", self.control.root, "probe_p3")
        self.assertEqual(entered, [])
        self.assertNotEqual(code, runner.EXIT_OK)
        self.assertEqual(gates["p3"]["status"], runner.BLOCKED)

    def test_a_valid_prior_pass_is_the_positive_control(self):
        promoted = Path(tempfile.mkdtemp(prefix="phase2-pass-",
                                         dir=str(self.control.workspace)))
        self.addCleanup(shutil.rmtree, promoted, ignore_errors=True)
        source = promoted / "passing"
        shutil.copytree(self.control.root, source)
        manifest = json.loads((source / "manifest.json").read_text())
        manifest["stage_status"]["p1"] = runner.PASS
        (source / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
        code, entered, gates = self.run_stage("p2", source, "probe_pass")
        self.assertEqual(len(entered), 1, "the stage body must be reached")
        self.assertEqual(gates["p2"]["status"], runner.PASS)
        self.assertEqual(code, runner.EXIT_OK)

    def test_a_missing_stage_digest_is_a_failure(self):
        broken = Path(tempfile.mkdtemp(prefix="phase2-nodigest-",
                                       dir=str(self.control.workspace)))
        self.addCleanup(shutil.rmtree, broken, ignore_errors=True)
        source = broken / "nodigest"
        shutil.copytree(self.control.root, source)
        manifest = json.loads((source / "manifest.json").read_text())
        manifest["stage_status"]["p1"] = runner.PASS
        manifest["stage_digests"].pop("p1")
        (source / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
        code, entered, gates = self.run_stage("p2", source, "probe_nodigest")
        self.assertEqual(entered, [])
        self.assertEqual(code, runner.EXIT_FAILURE)
        self.assertEqual(gates["p2"]["status"], runner.FAIL)
        self.assertIn("no digest", gates["p2"]["reason"])

    def test_a_tampered_prior_summary_is_a_failure(self):
        broken = Path(tempfile.mkdtemp(prefix="phase2-tamper-",
                                       dir=str(self.control.workspace)))
        self.addCleanup(shutil.rmtree, broken, ignore_errors=True)
        source = broken / "tampered"
        shutil.copytree(self.control.root, source)
        manifest = json.loads((source / "manifest.json").read_text())
        manifest["stage_status"]["p1"] = runner.PASS
        (source / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
        summary = json.loads((source / "p1" / "summary.json").read_text())
        summary["coverage_met"] = True
        (source / "p1" / "summary.json").write_text(json.dumps(summary, indent=4))
        code, entered, gates = self.run_stage("p2", source, "probe_tampered")
        self.assertEqual(entered, [])
        self.assertEqual(code, runner.EXIT_FAILURE)
        self.assertIn("manifest hash", gates["p2"]["reason"])

    def test_a_transitive_dependency_is_imported_and_checked(self):
        broken = Path(tempfile.mkdtemp(prefix="phase2-transitive-",
                                       dir=str(self.control.workspace)))
        self.addCleanup(shutil.rmtree, broken, ignore_errors=True)
        source = broken / "transitive"
        shutil.copytree(self.control.root, source)
        manifest = json.loads((source / "manifest.json").read_text())
        manifest["stage_status"]["p1"] = runner.PASS
        manifest["stage_status"]["p0"] = runner.INCONCLUSIVE
        (source / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
        code, entered, gates = self.run_stage("p2", source, "probe_transitive")
        self.assertEqual(entered, [])
        self.assertNotEqual(code, runner.EXIT_OK)
        self.assertIn("p0", gates["p2"]["reason"])

    def test_a_foreign_source_snapshot_is_a_failure(self):
        broken = Path(tempfile.mkdtemp(prefix="phase2-foreign-",
                                       dir=str(self.control.workspace)))
        self.addCleanup(shutil.rmtree, broken, ignore_errors=True)
        source = broken / "foreign"
        shutil.copytree(self.control.root, source)
        manifest = json.loads((source / "manifest.json").read_text())
        manifest["stage_status"]["p1"] = runner.PASS
        manifest["source_snapshot"]["snapshot_sha256"] = "0" * 64
        (source / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
        code, entered, gates = self.run_stage("p2", source, "probe_foreign")
        self.assertEqual(entered, [])
        self.assertEqual(code, runner.EXIT_FAILURE)
        self.assertIn("source", gates["p2"]["reason"])

    def test_there_is_still_no_flag_that_forces_a_stage(self):
        text = (ROOT / "research" / "run_structural_experiments.py").read_text()
        for forbidden in ("--force", "--skip-gate", "--no-gates", "--allow-blocked",
                          "--ignore-dependencies"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
