"""T06: the standalone export, its command line, and its isolation.

The export is exercised in fresh processes whose import path holds only the
export directory and the supplied machine module, so anything it silently
relied on in the development tree would fail here.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / ".reference") not in sys.path:
    sys.path.insert(0, str(ROOT / ".reference"))

import machine
import export_direct
from tests_direct import generate_programs as gp


REFERENCE = ROOT / ".reference"
PROGRAM = REFERENCE / "programs" / "03_vector_axpy.json"


def build_export():
    directory = Path(tempfile.mkdtemp(prefix="direct_export_"))
    return export_direct.export(directory / "compiler.py")


def isolated_env(export_directory):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(export_directory), str(REFERENCE)])
    return env


class AssemblyTests(unittest.TestCase):
    def test_the_export_is_valid_python_and_passes_its_own_audit(self):
        source = export_direct.assemble()
        compile(source, "<export>", "exec")
        self.assertEqual(export_direct.audit(source), [])

    def test_the_allowlist_is_explicit_and_in_dependency_order(self):
        self.assertEqual(
            export_direct.ALLOWLIST,
            (
                "schema_index.py",
                "direct_contract.py",
                "direct_constraints.py",
                "direct_optimizer.py",
                "direct_compiler.py",
            ),
        )
        for name in export_direct.ALLOWLIST:
            self.assertTrue((ROOT / name).exists(), name)

    def test_the_export_is_not_a_copy_of_the_previous_one(self):
        source = export_direct.assemble()
        previous = ROOT / ".build" / "index" / "compiler.py"
        if previous.exists():
            self.assertNotEqual(source, previous.read_text(encoding="utf-8"))
        self.assertNotIn("_Manager", source)
        self.assertNotIn("solve_exhaustive", source)

    def test_a_prohibited_dependency_would_be_refused(self):
        # The audit is the guard, so prove it actually rejects something.
        self.assertTrue(export_direct.audit("import common\n"))
        self.assertTrue(export_direct.audit("machine.serial_compile(p)\n"))
        self.assertTrue(export_direct.audit("exec('x = 1')\n"))


class StandaloneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.export = build_export()
        cls.env = isolated_env(cls.export.parent)

    def test_the_command_line_emits_only_json_on_stdout(self):
        completed = subprocess.run(
            [sys.executable, str(self.export), str(PROGRAM)],
            capture_output=True,
            text=True,
            env=self.env,
            timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(set(payload), {"scratch", "bundles"})
        # Diagnostics belong on stderr, and there are some.
        self.assertTrue(completed.stderr.strip())

    def test_the_emitted_schedule_satisfies_the_frozen_validator(self):
        completed = subprocess.run(
            [sys.executable, str(self.export), str(PROGRAM)],
            capture_output=True,
            text=True,
            env=self.env,
            timeout=20,
        )
        program = machine.load_program(PROGRAM)
        compilation = json.loads(completed.stdout)
        machine.check_compilation(program, compilation)
        for case in program["cases"]:
            machine.check_case(program, compilation, case)

    def test_a_missing_or_broken_argument_exits_nonzero_without_json(self):
        for argv in ([], [str(PROGRAM), "extra"]):
            completed = subprocess.run(
                [sys.executable, str(self.export)] + argv,
                capture_output=True,
                text=True,
                env=self.env,
                timeout=20,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(completed.stdout.strip(), "")
        missing = subprocess.run(
            [sys.executable, str(self.export), str(ROOT / "no_such_program.json")],
            capture_output=True,
            text=True,
            env=self.env,
            timeout=20,
        )
        self.assertEqual(missing.returncode, 1)
        self.assertEqual(missing.stdout.strip(), "")
        self.assertIn("FAILED", missing.stderr)

    def test_every_public_program_compiles_within_the_external_timeout(self):
        paths = sorted((REFERENCE / "programs").glob("*.json"))
        self.assertEqual(len(paths), 8)
        for path in paths:
            completed = subprocess.run(
                [sys.executable, str(self.export), str(path)],
                capture_output=True,
                text=True,
                env=self.env,
                timeout=20,
            )
            self.assertEqual(completed.returncode, 0, f"{path.name}: {completed.stderr}")
            program = machine.load_program(path)
            machine.check_compilation(program, json.loads(completed.stdout))

    def test_the_unchanged_public_suite_passes_against_the_export(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(REFERENCE / "tests"),
                "-t",
                str(REFERENCE),
                "-v",
            ],
            capture_output=True,
            text=True,
            env=self.env,
            timeout=300,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Ran 11 tests", completed.stderr)

    def test_the_export_imports_only_the_standard_library_and_machine(self):
        script = r"""
import json, sys
import compiler
print(json.dumps(sorted(m for m in sys.modules if not m.startswith("_"))))
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=60,
            env=self.env,
            cwd=tempfile.gettempdir(),
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        loaded = set(json.loads(completed.stdout))
        for forbidden in (
            "common",
            "compilers",
            "index_query",
            "repertoire_program",
            "schema_index",
            "direct_compiler",
        ):
            self.assertNotIn(forbidden, loaded)
        self.assertIn("machine", loaded)

    def test_the_export_does_not_modify_its_input(self):
        script = r"""
import copy, json, sys
import machine, compiler
program = machine.load_program(sys.argv[1])
before = copy.deepcopy(program)
compiler.compile_program(program)
print(json.dumps(program == before))
"""
        completed = subprocess.run(
            [sys.executable, "-c", script, str(PROGRAM)],
            capture_output=True,
            text=True,
            timeout=60,
            env=self.env,
            cwd=tempfile.gettempdir(),
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(json.loads(completed.stdout), "the input program was modified")

    def test_the_corpus_compiles_through_the_export_in_one_isolated_process(self):
        with tempfile.TemporaryDirectory(prefix="direct_corpus_") as directory:
            destination = Path(directory)
            programs = gp.corpus()
            for index, program in enumerate(programs):
                (destination / f"{index:03d}.json").write_text(
                    json.dumps(program, sort_keys=True), encoding="utf-8"
                )
            script = r"""
import json, sys
from pathlib import Path
import machine, compiler
failures = []
checked = 0
for path in sorted(Path(sys.argv[1]).glob("*.json")):
    program = machine.load_program(path)
    try:
        result = compiler.compile_program(program)
        machine.check_compilation(program, result)
        for case in program["cases"]:
            machine.check_case(program, result, case)
        checked += 1
    except Exception as exc:
        failures.append([program["name"], repr(exc)])
print(json.dumps({"checked": checked, "failures": failures}))
"""
            completed = subprocess.run(
                [sys.executable, "-c", script, str(destination)],
                capture_output=True,
                text=True,
                timeout=900,
                env=self.env,
                cwd=tempfile.gettempdir(),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr[-2000:])
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["failures"], [])
            self.assertEqual(payload["checked"], gp.EXPECTED_CORPUS_SIZE)


if __name__ == "__main__":
    unittest.main()


class ReleaseGateTests(unittest.TestCase):
    """The gates must reject. A gate never shown to fail is not a gate.

    Each case here injects a defect and requires the real release path — the
    comparison's gate evaluation, or the verifier's isolated corpus runner — to
    refuse it, while keeping the records of everything that did pass.
    """

    @staticmethod
    def synthetic_report(direct_scores, classical_scores=None, runs_per_arm=24,
                         discrepancies=0, leaked=False):
        """A complete, well-formed comparison report with chosen scores."""

        import compare_direct

        classical_scores = classical_scores or [
            compare_direct.HISTORICAL_CLASSICAL_SCORE
        ] * len(direct_scores)
        runs = []
        for arm in compare_direct.ARMS:
            for index in range(runs_per_arm):
                runs.append(
                    {
                        "arm": arm,
                        "program": "p%d" % (index % 8),
                        "repeat": index // 8,
                        "cycles": 10,
                        "scratch": 20,
                        "compile_seconds": 0.01,
                        "process_seconds": 0.1,
                        "peak_rss_bytes": 1000,
                        "correctness": "PASS",
                        "discrepancy_count": discrepancies if arm == "direct_index" else 0,
                        "leaked": ["common"] if (leaked and arm == "direct_index") else [],
                    }
                )
        return {
            "runs": runs,
            "failures": [],
            "per_repeat": {
                "direct_index": [
                    {"repeat": i, "combined_score": s} for i, s in enumerate(direct_scores)
                ],
                "classical": [
                    {"repeat": i, "combined_score": s}
                    for i, s in enumerate(classical_scores)
                ],
                "serial": [{"repeat": i, "combined_score": 1.0} for i in range(3)],
            },
        }

    def test_the_real_results_pass_every_gate(self):
        """Every recorded comparison carrying the full controls must pass.

        Reports written before a control existed cannot be judged by it, so
        they are not candidates; there must still be at least one that is.
        """

        import compare_direct

        candidates = []
        for path in sorted(ROOT.glob("results/*/comparison/runs.json")):
            report = json.loads(path.read_text())
            if "historical_metrics" in report and "program_names" in report:
                candidates.append((path, report))
        self.assertTrue(
            candidates, "no comparison evidence carries the frozen integer control"
        )
        for path, report in candidates:
            gates = compare_direct.evaluate_gates(report, report["repetitions"])
            self.assertTrue(gates["all_passed"]["passed"], f"{path}: {gates}")

    def test_a_score_equal_to_the_baseline_fails(self):
        import compare_direct

        report = self.synthetic_report([1.0, 1.0, 1.0])
        gates = compare_direct.evaluate_gates(report, 3)
        self.assertFalse(gates["direct_beats_baseline"]["passed"])
        self.assertFalse(gates["all_passed"]["passed"])

    def test_a_score_below_the_baseline_fails(self):
        import compare_direct

        report = self.synthetic_report([1.4, 0.98, 1.4])
        gates = compare_direct.evaluate_gates(report, 3)
        self.assertFalse(gates["direct_beats_baseline"]["passed"])

    def test_a_missing_repetition_fails(self):
        import compare_direct

        report = self.synthetic_report([1.5, 1.5], runs_per_arm=16)
        gates = compare_direct.evaluate_gates(report, 3)
        self.assertFalse(gates["direct_beats_baseline"]["passed"])
        self.assertFalse(gates["all_runs_present"]["passed"])

    def test_a_drifted_classical_control_fails(self):
        import compare_direct

        report = self.synthetic_report([1.5, 1.5, 1.5], classical_scores=[1.9, 1.9, 1.9])
        gates = compare_direct.evaluate_gates(report, 3)
        self.assertFalse(gates["frozen_classical_control"]["passed"])

    def test_a_recorded_discrepancy_fails(self):
        import compare_direct

        report = self.synthetic_report([1.5, 1.5, 1.5], discrepancies=1)
        gates = compare_direct.evaluate_gates(report, 3)
        self.assertFalse(gates["no_candidate_discrepancies"]["passed"])

    def test_a_leaked_module_in_the_direct_arm_fails(self):
        import compare_direct

        report = self.synthetic_report([1.5, 1.5, 1.5], leaked=True)
        gates = compare_direct.evaluate_gates(report, 3)
        self.assertFalse(gates["direct_arm_isolated"]["passed"])

    def test_a_stale_export_is_refused(self):
        import compare_direct

        original = EXPORT_PATH.read_text(encoding="utf-8")
        try:
            EXPORT_PATH.write_text(original + "\n# stale\n", encoding="utf-8")
            with self.assertRaises(RuntimeError) as caught:
                compare_direct.verify_export_fresh()
            self.assertIn("differs", str(caught.exception))
        finally:
            EXPORT_PATH.write_text(original, encoding="utf-8")

    def test_a_moved_protected_control_is_refused(self):
        import compare_direct

        original = dict(compare_direct.PROTECTED)
        try:
            compare_direct.PROTECTED["common.py"] = "0" * 64
            with self.assertRaises(RuntimeError) as caught:
                compare_direct.verify_protected()
            self.assertIn("common.py", str(caught.exception))
        finally:
            compare_direct.PROTECTED.clear()
            compare_direct.PROTECTED.update(original)


EXPORT_PATH = ROOT / ".build" / "direct_index" / "compiler.py"


class InjectedCorpusFailureTests(unittest.TestCase):
    """The verifier's corpus gate must fail on a defect and keep the rest."""

    def small_corpus(self, directory, count=3):
        """Programs on which the optimiser actually reaches a witness.

        Public programs are useless here: the optimiser finds every query
        infeasible on them, so a patched decode would never be called and the
        injection would silently do nothing.
        """

        from tests_direct.test_optimizer import CYCLE_FOR_MEMORY_TRADE, JOINT_NEEDED

        programs = [JOINT_NEEDED, CYCLE_FOR_MEMORY_TRADE, gp.public_programs()[0]]
        programs = programs[:count]
        for index, program in enumerate(programs):
            (directory / f"{index:03d}.json").write_text(
                json.dumps(program, sort_keys=True), encoding="utf-8"
            )
        return len(programs)

    def corrupted_export(self, directory, patch):
        """The real export with a defect appended, written beside it."""

        source = export_direct.assemble() + patch
        path = directory / "compiler.py"
        path.write_text(source, encoding="utf-8")
        return path

    def test_a_target_discrepancy_fails_the_corpus_gate(self):
        import verify_direct

        patch = (
            "\n\n"
            "def _forced_decode(self, cube):\n"
            "    return dict(self.times), dict(self.addresses)\n"
            "JointQuery.decode = _forced_decode\n"
        )
        with tempfile.TemporaryDirectory(prefix="inject_target_") as directory:
            work = Path(directory)
            corpus = work / "corpus"
            corpus.mkdir()
            expected = self.small_corpus(corpus)
            export = self.corrupted_export(work, patch)
            record = verify_direct.run_isolated_corpus(
                corpus, export, 20.0, work, expected
            )
            self.assertEqual(record["status"], "FAIL")
            self.assertTrue(record["discrepancies"], "the discrepancy must be named")
            payload = json.loads((work / "isolated_corpus.json").read_text())
            # Every input still has a record, defect or not.
            self.assertEqual(len(payload["runs"]), expected)
            self.assertTrue(
                any(r.get("result", {}).get("target_discrepancies") for r in payload["runs"])
            )

    def test_a_machine_invalid_candidate_fails_the_corpus_gate(self):
        import verify_direct

        patch = (
            "\n\n"
            "def _bad_decode(self, cube):\n"
            "    return dict(self.times), {n: 0 for n in self.facts.value_names}\n"
            "JointQuery.decode = _bad_decode\n"
        )
        with tempfile.TemporaryDirectory(prefix="inject_invalid_") as directory:
            work = Path(directory)
            corpus = work / "corpus"
            corpus.mkdir()
            expected = self.small_corpus(corpus)
            export = self.corrupted_export(work, patch)
            record = verify_direct.run_isolated_corpus(
                corpus, export, 20.0, work, expected
            )
            self.assertEqual(record["status"], "FAIL")
            payload = json.loads((work / "isolated_corpus.json").read_text())
            self.assertEqual(len(payload["runs"]), expected)
            flagged = [
                r
                for r in payload["runs"]
                if r.get("result", {}).get("discrepancy_count", 0)
            ]
            self.assertTrue(flagged, "an invalid candidate must be recorded")

    def test_one_timed_out_input_fails_overall_without_losing_the_others(self):
        import verify_direct

        real_run = subprocess.run
        target = "001.json"

        def fake_run(argv, **kwargs):
            if any(target in str(item) for item in argv):
                raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs.get("timeout", 20))
            return real_run(argv, **kwargs)

        with tempfile.TemporaryDirectory(prefix="inject_timeout_") as directory:
            work = Path(directory)
            corpus = work / "corpus"
            corpus.mkdir()
            expected = self.small_corpus(corpus)
            export = self.corrupted_export(work, "")
            verify_direct.subprocess.run = fake_run
            try:
                record = verify_direct.run_isolated_corpus(
                    corpus, export, 20.0, work, expected
                )
            finally:
                verify_direct.subprocess.run = real_run
            self.assertEqual(record["status"], "FAIL")
            self.assertIn(target, record["failures"])
            payload = json.loads((work / "isolated_corpus.json").read_text())
            self.assertEqual(len(payload["runs"]), expected, "records must be retained")
            survivors = [r for r in payload["runs"] if r["status"] == "PASS"]
            self.assertEqual(len(survivors), expected - 1)
            timed_out = [r for r in payload["runs"] if r.get("timed_out")]
            self.assertEqual(len(timed_out), 1)


class PublicSuiteGateTests(unittest.TestCase):
    """R9: the frozen suite is eleven tests, and an abort must not read PASS."""

    def test_only_exactly_eleven_tests_pass(self):
        import verify_direct

        self.assertEqual(verify_direct.EXPECTED_PUBLIC_TESTS, 11)
        self.assertEqual(
            verify_direct.public_suite_verdict(0, "Ran 11 tests in 0.01s", False)["status"],
            "PASS",
        )
        for stderr in ("Ran 10 tests in 0.01s", "Ran 12 tests in 0.01s", ""):
            self.assertEqual(
                verify_direct.public_suite_verdict(0, stderr, False)["status"],
                "FAIL",
                stderr,
            )

    def test_a_timed_out_public_suite_fails(self):
        import verify_direct

        verdict = verify_direct.public_suite_verdict(124, "Ran 11 tests in 0.01s", True)
        self.assertEqual(verdict["status"], "FAIL")
        self.assertTrue(verdict["timed_out"])

    def test_an_aborted_run_leaves_no_stale_pass(self):
        """The summary is claimed as IN_PROGRESS before any stage runs."""

        import verify_direct

        with tempfile.TemporaryDirectory(prefix="stale_summary_") as directory:
            output = Path(directory) / "verification"
            output.mkdir(parents=True)
            summary = output / "summary.json"
            summary.write_text(
                json.dumps({"status": "PASS", "note": "a previous run"}), encoding="utf-8"
            )
            # A stage that cannot succeed, run after the claim is written.
            # Its diagnostics are captured so the deliberate failure does not
            # look like a real one in the suite's output.
            noise, quiet = io.StringIO(), io.StringIO()
            with contextlib.redirect_stderr(noise), contextlib.redirect_stdout(quiet):
                code = verify_direct.main(["--stage", "schema", "--output", str(output),
                                           "--timeout", "0.0001"])
            payload = json.loads(summary.read_text())
            self.assertNotEqual(
                payload.get("status"), "PASS", "a stale PASS survived the rerun"
            )
            self.assertNotEqual(code, 0)


class ComparisonMembershipTests(unittest.TestCase):
    """F1 and F2: replay recorded worker results through the real run_all.

    Only the subprocess responses are injected. Every aggregate and every gate
    is recomputed by the production code, so these exercise the release path
    rather than a forged finished report.
    """

    @classmethod
    def setUpClass(cls):
        import compare_direct

        cls.comparison = compare_direct
        source = None
        for path in sorted(ROOT.glob("results/*/comparison/runs.json")):
            report = json.loads(path.read_text())
            if "historical_metrics" in report:
                source = report
        if source is None:  # pragma: no cover - evidence must exist
            raise unittest.SkipTest("no comparison evidence to replay")
        cls.source = source

    def replay(self, mutate=None):
        """Run the real run_all against recorded responses."""

        import copy
        from unittest.mock import patch

        real_run = subprocess.run
        counter = [0]
        programs = sorted((REFERENCE / "programs").glob("*.json"))
        first_name = json.loads(programs[0].read_text())["name"]

        def responder(argv, **kwargs):
            if argv[0] != sys.executable:
                return real_run(argv, **kwargs)
            repeat = (counter[0] // 3) % 3
            counter[0] += 1
            arm = argv[argv.index("--worker") + 1] if "--worker" in argv else "direct_index"
            program = json.loads(Path(argv[-1]).read_text())["name"]
            record = copy.deepcopy(
                next(
                    run
                    for run in self.source["runs"]
                    if run["arm"] == arm
                    and run["program"] == program
                    and run["repeat"] == repeat
                )
            )
            if mutate is not None:
                record = mutate(record, arm, program, repeat, first_name, self.source)
            return subprocess.CompletedProcess(argv, 0, json.dumps(record), "")

        with patch.object(self.comparison.subprocess, "run", side_effect=responder):
            return self.comparison.run_all(3, 20)

    def test_the_unmodified_replay_passes(self):
        result = self.replay()
        self.assertTrue(result["gates"]["all_passed"]["passed"], result["gates"])
        self.assertEqual(len(result["runs"]), 72)

    def test_a_duplicated_classical_measurement_is_rejected(self):
        """A duplicate filling a missing slot keeps the row count at 72."""

        import copy

        def duplicate(record, arm, program, repeat, first_name, source):
            if arm == "classical" and repeat == 1 and program == first_name:
                return copy.deepcopy(
                    next(
                        run
                        for run in source["runs"]
                        if run["arm"] == arm
                        and run["repeat"] == repeat
                        and run["program"] != program
                    )
                )
            return record

        result = self.replay(duplicate)
        gates = result["gates"]
        self.assertFalse(gates["all_passed"]["passed"])
        # Caught at the identity check, so the bad row never enters the report.
        self.assertTrue(
            gates["all_runs_present"]["missing"] or result["failures"],
            "the missing measurement must be named",
        )

    def test_a_product_preserving_metric_drift_is_rejected(self):
        """Doubling cycles and halving scratch leaves every score untouched."""

        def drift(record, arm, program, repeat, first_name, source):
            if arm == "classical" and record["scratch"] % 2 == 0:
                record["cycles"] *= 2
                record["scratch"] //= 2
            return record

        result = self.replay(drift)
        gates = result["gates"]
        self.assertFalse(gates["all_passed"]["passed"])
        self.assertFalse(gates["frozen_integer_metrics"]["passed"])
        self.assertTrue(gates["frozen_integer_metrics"]["drift"])
        # The aggregate alone would not have noticed.
        self.assertTrue(gates["frozen_classical_control"]["passed"])

    def test_a_serial_metric_drift_is_rejected(self):
        def drift(record, arm, program, repeat, first_name, source):
            if arm == "serial" and program == first_name:
                record["cycles"] += 1
            return record

        result = self.replay(drift)
        self.assertFalse(result["gates"]["frozen_integer_metrics"]["passed"])

    def test_a_foreign_arm_response_is_rejected(self):
        def swap(record, arm, program, repeat, first_name, source):
            if arm == "classical" and program == first_name and repeat == 0:
                record["arm"] = "serial"
            return record

        result = self.replay(swap)
        self.assertFalse(result["gates"]["all_passed"]["passed"])
        self.assertTrue(result["failures"], "the mismatch must be retained")

    def test_the_command_line_exits_nonzero_on_a_rejected_comparison(self):
        import copy
        from unittest.mock import patch

        def duplicate(record, arm, program, repeat, first_name, source):
            if arm == "classical" and repeat == 1 and program == first_name:
                return copy.deepcopy(
                    next(
                        run
                        for run in source["runs"]
                        if run["arm"] == arm
                        and run["repeat"] == repeat
                        and run["program"] != program
                    )
                )
            return record

        real_run = subprocess.run
        counter = [0]
        programs = sorted((REFERENCE / "programs").glob("*.json"))
        first_name = json.loads(programs[0].read_text())["name"]

        def responder(argv, **kwargs):
            if argv[0] != sys.executable:
                return real_run(argv, **kwargs)
            repeat = (counter[0] // 3) % 3
            counter[0] += 1
            arm = argv[argv.index("--worker") + 1] if "--worker" in argv else "direct_index"
            program = json.loads(Path(argv[-1]).read_text())["name"]
            record = copy.deepcopy(
                next(
                    run
                    for run in self.source["runs"]
                    if run["arm"] == arm
                    and run["program"] == program
                    and run["repeat"] == repeat
                )
            )
            return subprocess.CompletedProcess(
                argv, 0, json.dumps(duplicate(record, arm, program, repeat, first_name, self.source)), ""
            )

        with tempfile.TemporaryDirectory(prefix="cmp_gate_") as directory:
            noise, quiet = io.StringIO(), io.StringIO()
            with patch.object(self.comparison.subprocess, "run", side_effect=responder):
                with contextlib.redirect_stderr(noise), contextlib.redirect_stdout(quiet):
                    code = self.comparison.main(
                        ["--repeats", "3", "--timeout", "20", "--output", directory]
                    )
            self.assertNotEqual(code, 0, "a rejected comparison must exit nonzero")
