"""Method independence: by inspection, by guard, and by behaviour.

Renaming a classical routine would not satisfy any of this. The checks are
static import inspection of both the development modules and the assembled
export, runtime guards that make the prohibited routes raise, and behaviour
checks proving that both the bootstrap and the optimiser still work with those
routes closed.
"""

from __future__ import annotations

import ast
import importlib
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
import direct_compiler as dcmp
import export_direct
from tests_direct import generate_programs as gp


def _isolated_env():
    """Only the direct modules and the supplied machine module on the path."""

    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(ROOT / ".reference")])
    return env


DIRECT_MODULES = (
    "schema_index.py",
    "direct_contract.py",
    "direct_constraints.py",
    "direct_optimizer.py",
    "direct_compiler.py",
)

PROHIBITED_MODULES = {
    "common",
    "compilers",
    "index_query",
    "repertoire_program",
    "doppel_challenge",
    "test_comparison",
    "benchmark",
    "export",
}

# Third-party or solver backends that must not appear anywhere in the path.
PROHIBITED_BACKENDS = {"dd", "pyeda", "z3", "pysat", "sympy", "networkx", "numpy"}

ALLOWED_IMPORTS = {
    "machine",
    "argparse",
    "ast",
    "dataclasses",
    "hashlib",
    "json",
    "pathlib",
    "sys",
    "time",
    "typing",
    "__future__",
}


def imports_of(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.add(node.module.split(".")[0])
    return found


class StaticInspectionTests(unittest.TestCase):
    def test_direct_modules_import_nothing_prohibited(self):
        internal = {name[:-3] for name in DIRECT_MODULES}
        for name in DIRECT_MODULES:
            found = imports_of(ROOT / name)
            for module in found:
                self.assertNotIn(module, PROHIBITED_MODULES, f"{name} imports {module}")
                self.assertNotIn(module, PROHIBITED_BACKENDS, f"{name} imports {module}")
                self.assertTrue(
                    module in ALLOWED_IMPORTS or module in internal,
                    f"{name} imports an unexpected module {module!r}",
                )

    def test_no_direct_module_mentions_a_baseline_compiler(self):
        for name in DIRECT_MODULES:
            text = (ROOT / name).read_text(encoding="utf-8")
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr in (
                    "serial_compile",
                    "classical_compile",
                ):
                    self.fail(f"{name} references {node.attr}")
                if isinstance(node, ast.Name) and node.id in (
                    "serial_compile",
                    "classical_compile",
                ):
                    self.fail(f"{name} references {node.id}")

    def test_the_export_carries_no_prohibited_dependency(self):
        source = export_direct.assemble()
        self.assertEqual(export_direct.audit(source), [])
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    self.assertNotIn(root, PROHIBITED_MODULES)
                    self.assertNotIn(root, PROHIBITED_BACKENDS)
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                self.assertNotIn(root, PROHIBITED_MODULES)
                self.assertNotIn(root, PROHIBITED_BACKENDS)

    def test_the_export_hides_nothing_behind_exec(self):
        source = export_direct.assemble()
        for banned in ("exec(", "eval(", "__import__", "marshal", "base64", "zlib"):
            self.assertNotIn(banned, source, f"the export uses {banned}")

    def test_the_export_records_its_constituent_hashes(self):
        source = export_direct.assemble()
        import hashlib

        for name in export_direct.ALLOWLIST:
            expected = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            self.assertIn(expected, source, f"{name} hash missing from the export")


class RuntimeGuardTests(unittest.TestCase):
    def test_bootstrap_and_optimiser_both_work_with_serial_compile_raising(self):
        def refuse(*args, **kwargs):
            raise AssertionError("serial_compile must never be called")

        original = machine.serial_compile
        machine.serial_compile = refuse
        try:
            # A program known to exercise the optimiser to an acceptance.
            source = gp.additional_program(1024)
            compiled, report = dcmp.compile_with_report(source)
            machine.check_compilation(source, compiled)
            self.assertGreater(report["optimisation"]["attempted_queries"], 0)
            self.assertGreaterEqual(report["optimisation"]["accepted"], 1)
        finally:
            machine.serial_compile = original

    def test_no_prohibited_module_is_present_after_a_compilation(self):
        for name in PROHIBITED_MODULES:
            sys.modules.pop(name, None)
        importlib.reload(dcmp)
        for source in gp.public_programs()[:3]:
            dcmp.compile_program(source)
        for name in PROHIBITED_MODULES:
            self.assertNotIn(name, sys.modules, f"{name} was imported during compilation")

    def test_compilation_in_an_isolated_process_imports_nothing_prohibited(self):
        script = r"""
import json, sys
from pathlib import Path
import machine, direct_compiler
program = machine.load_program(sys.argv[1])
result = direct_compiler.compile_program(program)
machine.check_compilation(program, result)
print(json.dumps(sorted(m for m in sys.modules if not m.startswith("_"))))
"""
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                script,
                str(ROOT / ".reference" / "programs" / "01_scalar_pipeline.json"),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            env=_isolated_env(),
            cwd=tempfile.gettempdir(),
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        loaded = set(json.loads(completed.stdout)) if completed.stdout else set()
        for name in PROHIBITED_MODULES | PROHIBITED_BACKENDS:
            self.assertNotIn(name, loaded)


import json  # noqa: E402  (used by the isolated-process test above)


class DecisionProvenanceTests(unittest.TestCase):
    """Every decision must come from the query path, not from a table."""

    def test_no_program_name_or_case_value_reaches_a_decision(self):
        for name in DIRECT_MODULES:
            text = (ROOT / name).read_text(encoding="utf-8")
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                    self.assertNotIn(
                        node.slice.value,
                        ("cases", "name"),
                        f"{name} reads program[{node.slice.value!r}]",
                    )

    def test_renaming_a_program_changes_nothing(self):
        source = gp.public_programs()[2]
        first = dcmp.compile_program(source)
        renamed = dict(source)
        renamed["name"] = "a_completely_different_name"
        second = dcmp.compile_program(renamed)
        self.assertEqual(first, second)

    def test_changing_case_values_changes_nothing(self):
        source = gp.public_programs()[2]
        first = dcmp.compile_program(source)
        altered = dict(source)
        altered["cases"] = [
            {buffer: [(word + 7) % (1 << 32) for word in words] for buffer, words in case.items()}
            for case in source["cases"]
        ]
        second = dcmp.compile_program(altered)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()


class ExportOptimisationTests(unittest.TestCase):
    """A successful optimisation, through the export, with the routes shut.

    The development compiler passing under guards says nothing about what the
    grader would run. This drives the assembled export in a neutral directory
    under -I -S, with serial_compile replaced by a raising stub, on a program
    known to reach an accepted improvement.
    """

    WORKER = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import machine

def prohibited(*args, **kwargs):
    raise AssertionError("serial_compile was called by the direct export")

machine.serial_compile = prohibited
import compiler

program = json.loads(open(sys.argv[2]).read())
compiled, report = compiler.compile_with_report(program)
machine.check_compilation(program, compiled)
for case in program["cases"]:
    machine.check_case(program, compiled, case)
banned = {"common", "compilers", "index_query", "repertoire_program", "direct_compiler"}
print(json.dumps({
    "accepted": report["optimisation"]["accepted"],
    "attempted": report["optimisation"]["attempted_queries"],
    "discrepancy_count": report["discrepancy_count"],
    "cycles": report["cycles"],
    "footprint": report["footprint"],
    "bootstrap": report["bootstrap"]["cycles"],
    "bootstrap_footprint": report["bootstrap"]["footprint"],
    "compiler_path": compiler.__file__,
    "leaked": sorted(n for n in sys.modules if n.split(".")[0] in banned),
}))
'''

    def drive(self, program):
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory(prefix="export_opt_") as directory:
            work = Path(directory)
            export = export_direct.export(work / "compiler.py")
            shutil.copyfile(ROOT / ".reference" / "machine.py", work / "machine.py")
            source = work / "program.json"
            source.write_text(json.dumps(program, sort_keys=True), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "-I", "-S", "-c", self.WORKER, str(work), str(source)],
                cwd=str(work),
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr[-2000:])
            payload = json.loads(completed.stdout)
            self.assertEqual(str(export), payload["compiler_path"])
            return payload

    def test_the_export_optimises_successfully_with_prohibited_routes_blocked(self):
        from tests_direct.test_optimizer import CYCLE_FOR_MEMORY_TRADE

        payload = self.drive(CYCLE_FOR_MEMORY_TRADE)
        self.assertGreater(payload["attempted"], 0)
        self.assertGreaterEqual(payload["accepted"], 1, "the export must optimise")
        self.assertEqual(payload["discrepancy_count"], 0)
        self.assertEqual(payload["leaked"], [])
        # The accepted witness is the cycle-for-scratch trade.
        self.assertGreater(payload["cycles"], payload["bootstrap"])
        self.assertLess(payload["footprint"], payload["bootstrap_footprint"])

    def test_the_export_optimises_a_second_program_the_same_way(self):
        from tests_direct.test_optimizer import JOINT_NEEDED

        payload = self.drive(JOINT_NEEDED)
        self.assertGreaterEqual(payload["accepted"], 1)
        self.assertEqual(payload["discrepancy_count"], 0)
        self.assertEqual(payload["leaked"], [])
