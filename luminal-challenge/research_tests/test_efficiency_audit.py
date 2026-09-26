"""R2: the successor auditor fails on false evidence and passes the unchanged release.

Report mutations are applied in memory through ``Audit.loader``; raw-evidence
mutations are applied to an OVERLAY: a temporary directory of symlinks to the
real run in which only the mutated file is a modified copy. The real run is
never written. Each test names the finding code it requires.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results" / "phase2_structural_encoding" / "next_round_20260925"


def _auditor():
    spec = importlib.util.spec_from_file_location("efficiency_audit_under_test",
                                                  ROOT / "research" / "efficiency_audit.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EA = _auditor()


def audit(mutate_report=None, run=RUN):
    a = EA.Audit(run, root=ROOT)
    if mutate_report is not None:
        original = a._read_report

        def loader(name):
            value = original(name)
            if value is None:
                return None
            value = copy.deepcopy(value)
            return mutate_report(name, value)

        a.loader = loader
    return a.run_all()


class Overlay:
    """A symlink tree of the real run; ``replace`` swaps one file for a copy."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name) / "run"
        for dirpath, _, files in os.walk(RUN):
            rel = Path(dirpath).relative_to(RUN)
            (self.run / rel).mkdir(parents=True, exist_ok=True)
            for f in files:
                os.symlink(Path(dirpath) / f, self.run / rel / f)

    def replace(self, relative, transform):
        target = self.run / relative
        text = (RUN / relative).read_text()
        target.unlink()
        target.write_text(transform(text))

    def remove(self, relative):
        path = self.run / relative
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()

    def close(self):
        self.tmp.cleanup()


def _codes(result):
    return set(result["finding_codes"])


class UnchangedReleasePasses(unittest.TestCase):
    def test_unchanged_release_passes_with_its_negative_verdicts(self):
        result = audit()
        self.assertEqual(result["status"], "PASS", result["findings"][:5])
        self.assertEqual(result["unmapped_fields"], 0)
        self.assertFalse(result["complete_coverage_claimed"])
        self.assertTrue(result["declared_unchecked"])
        self.assertGreater(result["checks"], 100_000)
        report = json.loads((RUN / "LEARNING_FEASIBILITY.json").read_text())
        self.assertEqual(report["contrasts"]["mechanism_signal"], "FAIL_OR_INCONCLUSIVE")
        self.assertEqual(report["economics"]["verdict"], "ECONOMICALLY_UNAVAILABLE")


class ReportMutationsFail(unittest.TestCase):
    def _fails(self, mutate, code):
        result = audit(mutate)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn(code, _codes(result), result["finding_codes"])
        return result

    def test_lead_mutation_false_mechanism_and_upper_bounds(self):
        def mutate(name, value):
            if name == "LEARNING_FEASIBILITY.json":
                value["contrasts"]["mechanism_signal"] = "PASS"
                for item in value["contrasts"].values():
                    if isinstance(item, dict) and "interval_98_333" in item:
                        item["passes"] = True
                        item["interval_98_333"][1] = 999.0
            return value
        self._fails(mutate, "LEARNING_CONTRASTS")

    def test_upper_bound_only(self):
        def mutate(name, value):
            if name == "LEARNING_FEASIBILITY.json":
                value["contrasts"]["tree_minus_hamming"]["interval_98_333"][1] += 1e-3
            return value
        self._fails(mutate, "LEARNING_CONTRASTS")

    def test_primary_lower_bound_only(self):
        def mutate(name, value):
            if name == "COMPARISON.json":
                value["primary"]["interval_95"][0] -= 1e-4
            return value
        self._fails(mutate, "PRIMARY")

    def test_candidate_upper_bound_only(self):
        def mutate(name, value):
            if name == "COMPARISON.json":
                value["candidate_endpoints"]["cell_a4cat_heap"]["J_ratio_interval_98_75"][1] = 0.97
            return value
        self._fails(mutate, "CANDIDATE_ENDPOINTS")

    def test_false_route_flag_and_verdict(self):
        def mutate(name, value):
            if name == "COMPARISON.json":
                value["candidate_endpoints"]["routes_passed"]["quality_route"] = True
                value["candidate_endpoints"]["verdict"] = "QUALITY_ROUTE"
            return value
        self._fails(mutate, "CANDIDATE_ENDPOINTS")

    def test_false_per_contrast_flag(self):
        def mutate(name, value):
            if name == "LEARNING_FEASIBILITY.json":
                value["contrasts"]["tree_minus_shuffled_tree"]["passes"] = True
            return value
        self._fails(mutate, "LEARNING_CONTRASTS")

    def test_wrong_economics_denominator(self):
        def mutate(name, value):
            if name == "LEARNING_FEASIBILITY.json":
                value["economics"]["programs"] = 99
            return value
        self._fails(mutate, "ECONOMICS")

    def test_false_economics_verdict(self):
        def mutate(name, value):
            if name == "LEARNING_FEASIBILITY.json":
                value["economics"]["verdict"] = "AVAILABLE"
            return value
        self._fails(mutate, "ECONOMICS")

    def test_false_per_row_yield(self):
        def mutate(name, value):
            if name == "LEARNING_FEASIBILITY.json":
                fixture = sorted(value["orderings"]["per_fixture_yield"])[0]
                value["orderings"]["per_fixture_yield"][fixture]["tree"] += 1 / 32
            return value
        self._fails(mutate, "ORDERINGS")

    def test_wrong_public_score(self):
        def mutate(name, value):
            if name == "PUBLIC_SCORE.json":
                value["scores"]["arms"]["cell_a4cat_dfs@0.1"]["scores"][2] += 1e-6
            return value
        self._fails(mutate, "PUBLIC_SCORE")

    def test_unmapped_new_field(self):
        def mutate(name, value):
            if name == "COMPARISON.json":
                value["claimed_speedup"] = 0.5
            return value
        self._fails(mutate, "UNMAPPED_FIELD")

    def test_missing_required_report(self):
        def mutate(name, value):
            return None if name == "PUBLIC_SCORE.json" else value
        self._fails(mutate, "MISSING_REQUIRED")


class RawEvidenceMutationsFail(unittest.TestCase):
    def setUp(self):
        self.overlay = Overlay()

    def tearDown(self):
        self.overlay.close()

    def _fails(self, code):
        result = audit(run=self.overlay.run)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn(code, _codes(result), result["finding_codes"])

    def _ranker_input(self, need_free_index=False):
        for design in json.loads((RUN / "learning/DESIGN_EVALUATION.json").read_text())[
                "designs"]:
            relative = f"learning/design/evaluation/{design['fixture_id']}/RANKER_INPUT.json"
            data = json.loads((RUN / relative).read_text())
            used = len(data["pool"]) + len(data["training_indices"])
            if not need_free_index or used < (1 << data["bits"]):
                return relative
        raise AssertionError("no fixture has an index outside its pool and training set")

    def test_altered_training_j(self):
        def transform(text):
            data = json.loads(text)
            data["training_products"][0] += 1
            return json.dumps(data)
        self.overlay.replace(self._ranker_input(), transform)
        self._fails("TRAINING_J_ALIGNMENT")

    def test_invented_pool_membership(self):
        def transform(text):
            data = json.loads(text)
            universe = 1 << data["bits"]
            taken = {int(i) for i in data["pool"]} | {int(i) for i in data["training_indices"]}
            extra = next(i for i in range(universe) if i not in taken)
            data["pool"] = [str(i) for i in sorted({int(i) for i in data["pool"]} | {extra})]
            return json.dumps(data)
        self.overlay.replace(self._ranker_input(need_free_index=True), transform)
        self._fails("POOL_MEMBERSHIP")

    def test_false_ordering_row(self):
        def transform(text):
            lines = text.splitlines()
            row = json.loads(lines[0])
            ordered = row["result"]["ordered"]
            ordered[0], ordered[-1] = ordered[-1], ordered[0]
            lines[0] = json.dumps(row)
            return "\n".join(lines) + "\n"
        self.overlay.replace("stages/L_orderings/rows.jsonl", transform)
        self._fails("ORDERING_DIGEST")

    def test_missing_export_row(self):
        self.overlay.replace("export/candidate/rows.jsonl",
                             lambda text: "\n".join(text.splitlines()[1:]) + "\n")
        self._fails("EXPORT_MEMBERSHIP")

    def test_missing_required_stage(self):
        self.overlay.remove("stages/L_acquisition")
        self._fails("MISSING_REQUIRED")

    def test_wrong_serial_denominator(self):
        def transform(text):
            lines = text.splitlines()
            for i, line in enumerate(lines):
                row = json.loads(line)
                if row["arm"] == "serial" and row["repetition"] == 3:
                    row["cycles"] += 1
                    row["product"] = row["cycles"] * row["scratch"]
                    lines[i] = json.dumps(row)
                    break
            return "\n".join(lines) + "\n"
        self.overlay.replace("stages/C_public/rows.jsonl", transform)
        self._fails("SERIAL_STABLE")

    def test_torn_final_row(self):
        self.overlay.replace("stages/D_profile/rows.jsonl", lambda text: text + '{"key": "tor')
        self._fails("MALFORMED_ROW")

    def test_duplicate_row(self):
        self.overlay.replace("stages/L_acquisition/rows.jsonl",
                             lambda text: text + text.splitlines()[0] + "\n")
        self._fails("DUPLICATES")

    def test_timed_out_row(self):
        def transform(text):
            lines = text.splitlines()
            row = json.loads(lines[5])
            row["timed_out"] = True
            lines[5] = json.dumps(row)
            return "\n".join(lines) + "\n"
        self.overlay.replace("stages/C_confirmation/rows.jsonl", transform)
        self._fails("TIMED_OUT")


if __name__ == "__main__":
    unittest.main()
