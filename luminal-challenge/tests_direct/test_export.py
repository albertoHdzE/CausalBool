"""T06: the standalone export, its command line, and its isolation.

The export is exercised in fresh processes whose import path holds only the
export directory and the supplied machine module, so anything it silently
relied on in the development tree would fail here.
"""

from __future__ import annotations

import copy
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
