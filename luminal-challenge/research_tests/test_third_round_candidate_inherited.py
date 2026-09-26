"""Inherited semantic tests bound explicitly to the third-round candidate C1.

The inherited files are NOT edited. Each is loaded from its own bytes into a
fresh module object whose solver name (``nrs``, ``ois`` or ``es``) is rebound to
``research.third_round_candidate`` before any test runs; parity tests in them
then compare C1 with their frozen comparison owner.

``research/objective_index_validation.py`` (used by ``PropagationSoundness`` and
``CanonicalRanks``) reads its solver through a module global ``ois``; it is
loaded fresh with ``ois`` bound to a view of C1 whose ``Propagation`` is the class
C1's expander actually constructs (``third_round_kernel.SharedPropagation``), so
its planted-mutation hooks reach the measured code.

``APPLICABLE``/``EXCLUDED`` cover every ``TestCase`` class of the three files,
with a reason for each exclusion; ``test_coverage_is_declared`` enforces it.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path

from research import third_round_candidate as c1
from research import third_round_kernel as tk

ROOT = Path(__file__).resolve().parents[1]

SOURCES = {
    "test_next_round_search": {"file": "research_tests/test_next_round_search.py",
                               "rebind": "nrs"},
    "test_objective_index": {"file": "research_tests/test_objective_index.py",
                             "rebind": "ois"},
    "test_efficiency_search": {"file": "research_tests/test_efficiency_search.py",
                               "rebind": "es"},
}

APPLICABLE = {
    "test_next_round_search": (
        "InterruptionAccounting", "DecisionParityWithFrozenOwner",
        "TraversalExhaustiveAgreement", "AblationController"),
    "test_objective_index": (
        "IntegerCapLemma", "PropagationSoundness", "CanonicalRanks", "Catalog",
        "ResumableQueries", "AcceptanceSafety", "CertificateStream"),
    "test_efficiency_search": (
        "ConstructionExits", "ValidationEventsWithDeadlines", "ModelPhaseLateValidations",
        "ParityWithParent"),
}

EXCLUDED = {
    "test_next_round_search": {
        "FrozenOwnerStillHasTheDefect":
            "asserts the defect of the frozen owner ``ois``; it names no successor",
    },
    "test_objective_index": {
        "TradeOffCoverage": "the frozen A1-A3 sequential arms, not the A4 controller",
        "OwnerParity": "compares the A3 ``ss_bound`` replica with structural_search; "
                       "the replica is not on the measured A4 path",
        "LearnedCompilerPair": "the closed learner, which imports the frozen owner "
                               "``objective_index_search`` itself",
    },
    "test_efficiency_search": {
        "PowerOnParent": "asserts the parent's (next_round_search) defect; names no successor",
    },
}


def _c1_view() -> types.ModuleType:
    view = types.ModuleType("third_round_candidate_view")
    view.__dict__.update({k: v for k, v in vars(c1).items() if not k.startswith("__")})
    view.Propagation = tk.SharedPropagation
    return view


def _fresh(path: Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load(name: str) -> object:
    info = SOURCES[name]
    path = ROOT / info["file"]
    module = _fresh(path, f"c1_inherited_{name}")
    setattr(module, info["rebind"], c1)
    if hasattr(module, "oiv"):
        oiv = _fresh(ROOT / "research/objective_index_validation.py", f"c1_oiv_{name}")
        oiv.ois = _c1_view()
        module.oiv = oiv
    module.__c1_source_sha256__ = hashlib.sha256(path.read_bytes()).hexdigest()
    return module


def _classes(path: Path) -> list:
    tree = ast.parse(path.read_text())
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)
            and any(getattr(b, "attr", getattr(b, "id", "")) == "TestCase" for b in node.bases)]


class InheritedCoverage(unittest.TestCase):
    def test_coverage_is_declared(self):
        for name, info in SOURCES.items():
            declared = set(APPLICABLE[name]) | set(EXCLUDED[name])
            found = set(_classes(ROOT / info["file"]))
            self.assertTrue(found, f"{name}: zero TestCase classes scanned")
            self.assertEqual(found, declared, name)
            self.assertFalse(set(APPLICABLE[name]) & set(EXCLUDED[name]))

    def test_rebinding_reaches_c1(self):
        module = _load("test_objective_index")
        self.assertIs(module.ois, c1)
        self.assertIs(module.oiv.ois.Propagation, tk.SharedPropagation)
        self.assertIs(module.oiv.ois.Expander, c1.Expander)


def load_tests(loader, standard_tests, pattern):
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(InheritedCoverage))
    for name in SOURCES:
        module = _load(name)
        for class_name in APPLICABLE[name]:
            suite.addTests(loader.loadTestsFromTestCase(getattr(module, class_name)))
    return suite
