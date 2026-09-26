"""Inherited semantic tests, run explicitly on the efficiency baseline R0.

Plan ``CLAUDE_PHASE2_EFFICIENCY_PHASE.md`` section 3, R exit: "Run applicable
inherited semantic tests on R0 explicitly". The inherited files are NOT edited.
Each is loaded from its own bytes into a fresh module object whose solver name
(``nrs`` for the next-round tests, ``ois`` for the objective-index tests) is
rebound to ``research.efficiency_search`` before any test runs. Everything else
in those files -- the frozen comparison owner, the oracle, the fixtures -- is
unchanged, so a parity test in them now compares R0 with the frozen owner.

``APPLICABLE`` names every inherited class that is run here; ``EXCLUDED``
names every class that is not, with its reason. The two lists together cover
every ``TestCase`` class in the two files (``test_coverage_is_declared``).
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path

from research import efficiency_search as es

ROOT = Path(__file__).resolve().parents[1]

SOURCES = {
    "test_next_round_search": {"file": "research_tests/test_next_round_search.py",
                               "rebind": "nrs"},
    "test_objective_index": {"file": "research_tests/test_objective_index.py",
                             "rebind": "ois"},
}

APPLICABLE = {
    "test_next_round_search": (
        "InterruptionAccounting", "DecisionParityWithFrozenOwner",
        "TraversalExhaustiveAgreement", "AblationController"),
    "test_objective_index": (
        "IntegerCapLemma", "PropagationSoundness", "CanonicalRanks", "Catalog",
        "ResumableQueries", "AcceptanceSafety", "CertificateStream"),
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
}


def _load(name: str) -> object:
    spec_info = SOURCES[name]
    path = ROOT / spec_info["file"]
    spec = importlib.util.spec_from_file_location(f"efficiency_inherited_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    setattr(module, spec_info["rebind"], es)
    module.__efficiency_source_sha256__ = hashlib.sha256(path.read_bytes()).hexdigest()
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


def load_tests(loader, standard_tests, pattern):
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(InheritedCoverage))
    for name in SOURCES:
        module = _load(name)
        for class_name in APPLICABLE[name]:
            suite.addTests(loader.loadTestsFromTestCase(getattr(module, class_name)))
    return suite
