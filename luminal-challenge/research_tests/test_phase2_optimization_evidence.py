"""Mutation tests of the optimization evidence checker and independent auditor.

Each test builds a shadow of the completed run of record in a temporary
directory -- every file a symbolic link to the real one except the single file
being mutated, which is a modified copy -- and asserts that the checker or the
auditor raises the specific finding the planted defect must raise, and that the
unmutated shadow does not. The run of record is never written.

These tests require the completed run directory and are run after timing stops.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results" / "phase2_structural_encoding" / "optimization_20260924"
COMPLETE = (RUN / "COMPARISON.json").exists() and (RUN / "MODEL_EVALUATION.json").exists()


def shadow(mutate: dict) -> Path:
    """A linked copy of RUN; ``mutate`` maps relative paths to a transform."""

    tmp = Path(tempfile.mkdtemp(prefix="opt_shadow_"))
    for current, dirs, files in os.walk(RUN):
        rel = Path(current).relative_to(RUN)
        if rel.parts and rel.parts[0] in ("frozen_control_workspace", "export", "inputs",
                                          "SOURCE_MANIFESTS"):
            dirs[:] = []
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            if not (tmp / rel).exists():
                os.symlink(RUN / rel, tmp / rel)
            continue
        (tmp / rel).mkdir(parents=True, exist_ok=True)
        for name in files:
            source = RUN / rel / name
            target = tmp / rel / name
            key = str(rel / name)
            if key in mutate:
                target.write_text(mutate[key](source.read_text()))
            else:
                os.symlink(source, target)
    return tmp


def rows_transform(func):
    def apply(text: str) -> str:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        return "".join(json.dumps(r, sort_keys=True) + "\n" for r in func(rows))
    return apply


def json_transform(func):
    def apply(text: str) -> str:
        payload = json.loads(text)
        func(payload)
        return json.dumps(payload)
    return apply


@unittest.skipUnless(COMPLETE, "requires the completed optimization run of record")
class CheckerMutations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from research import optimization_checker as ck

        cls.ck = ck
        base = shadow({})
        cls.base_codes = set(ck.Checker(base).run_all()["finding_codes"])
        shutil.rmtree(base)

    def codes(self, mutate: dict, root: Path = ROOT) -> set:
        tmp = shadow(mutate)
        try:
            return set(self.ck.Checker(tmp, root=root).run_all()["finding_codes"])
        finally:
            shutil.rmtree(tmp)

    def assertRaisesFinding(self, code: str, mutate: dict) -> None:
        self.assertNotIn(code, self.base_codes)
        self.assertIn(code, self.codes(mutate))

    def test_missing_row(self):
        self.assertRaisesFinding("MISSING_ROWS", {
            "stages/D_public/rows.jsonl": rows_transform(lambda rows: rows[1:])})

    def test_duplicate_row(self):
        self.assertRaisesFinding("DUPLICATE_ROWS", {
            "stages/D_public/rows.jsonl": rows_transform(lambda rows: rows + rows[:1])})

    def test_forged_row_without_freeze(self):
        def forge(rows):
            rows[0]["freeze_sha256"] = "0" * 64
            return rows
        self.assertRaisesFinding("ROW_WITHOUT_FREEZE", {
            "stages/D_public/rows.jsonl": rows_transform(forge)})

    def test_row_from_another_manifest(self):
        def forge(rows):
            rows[3]["manifest_sha256"] = "f" * 64
            return rows
        self.assertRaisesFinding("ROW_MANIFEST_MISMATCH", {
            "stages/D_public/rows.jsonl": rows_transform(forge)})

    def test_interrupted_validation_credited(self):
        def forge(rows):
            for row in rows:
                if row["arm"] == "selected_nonmodel":
                    row["result"]["discrepancy_count"] = 1
                    break
            return rows
        self.assertRaisesFinding("DISCREPANCY_NOT_FAILED", {
            "stages/D_public/rows.jsonl": rows_transform(forge)})

    def test_timed_out_worker_is_a_failure(self):
        def forge(rows):
            rows[5]["timed_out"] = True
            rows[5]["failed_row"] = True
            return rows
        self.assertRaisesFinding("FAILED_ROW", {
            "stages/D_public/rows.jsonl": rows_transform(forge)})

    def test_hidden_split_exposure(self):
        def forge(rows):
            rows[0]["result"]["discoveries"]["train"] = 1
            return rows
        self.assertRaisesFinding("TRAINING_OBJECT_REPORTED_NEW", {
            "stages/C_model_evaluation/rows.jsonl": rows_transform(forge)})

    def test_control_imported_from_modified_tree(self):
        def forge(rows):
            for row in rows:
                if row["arm"] == "frozen_phase2":
                    row["result"]["imported_sources"]["research"] = str(
                        ROOT / "research" / "__init__.py")
                    break
            return rows
        self.assertRaisesFinding("CONTROL_NOT_ISOLATED", {
            "stages/D_public/rows.jsonl": rows_transform(forge)})

    def test_post_freeze_source_change(self):
        def forge(payload):
            payload["sources"]["research"]["research/optimization_search.py"] = "0" * 64
        self.assertRaisesFinding("POST_FREEZE_SOURCE_CHANGE", {
            "FROZEN_SELECTION.json": json_transform(forge)})

    def test_ledger_changed_after_freeze(self):
        def forge(payload):
            payload["keys"] = payload["keys"][:-1]
        self.assertRaisesFinding("LEDGER_CHANGED_AFTER_FREEZE", {
            "frozen_expected/D_public.json": json_transform(forge)})

    def test_false_h4_pass(self):
        def forge(payload):
            payload["H4_NEW"] = "PASS"
        self.assertRaisesFinding("FALSE_H4_PASS", {"MODEL_EVALUATION.json": json_transform(forge)})

    def test_false_primary_verdict(self):
        def forge(payload):
            payload["primary"]["verdict"] = ("SUPPORTS_DEGRADATION"
                                             if payload["primary"]["verdict"] != "SUPPORTS_DEGRADATION"
                                             else "SUPPORTS_IMPROVEMENT")
        self.assertRaisesFinding("FALSE_PRIMARY_VERDICT", {"COMPARISON.json": json_transform(forge)})

    def test_wrong_score_denominator(self):
        def forge(payload):
            arm = payload["scores"]["arms"]["selected_nonmodel@0.1"]
            arm["scores"][0] = arm["scores"][0] * 1.01
        self.assertRaisesFinding("SCORE_DENOMINATOR", {"PUBLIC_SCORE.json": json_transform(forge)})

    def test_false_public_strict_gain(self):
        def forge(payload):
            for entry in payload["paired_score_ratios"].values():
                entry["strict_improvement_every_repetition"] = \
                    not entry["strict_improvement_every_repetition"]
        self.assertRaisesFinding("FALSE_PUBLIC_STRICT_GAIN", {
            "PUBLIC_SCORE.json": json_transform(forge)})

    def test_false_model_advancement(self):
        tmp = shadow({})
        try:
            (tmp / "stages" / "D_fresh_model_compiler").mkdir()
            for name in ("rows.jsonl", "resume_log.jsonl"):
                (tmp / "stages" / "D_fresh_model_compiler" / name).write_text("")
            (tmp / "stages" / "D_fresh_model_compiler" / "EXPECTED_KEYS.json").write_text(
                json.dumps({"keys": ["x"]}))
            (tmp / "stages" / "D_fresh_model_compiler" / "STAGE_MANIFEST.json").write_text(
                json.dumps({"manifest_sha256": "x"}))
            codes = set(self.ck.Checker(tmp).run_all()["finding_codes"])
        finally:
            shutil.rmtree(tmp)
        if json.loads((RUN / "MODEL_EVALUATION.json").read_text())["H4_NEW"] != "PASS":
            self.assertIn("MODEL_COMPILER_RUN_WITHOUT_H4", codes)

    def test_planted_learner_import_of_the_oracle(self):
        tmp_root = Path(tempfile.mkdtemp(prefix="opt_root_"))
        try:
            for item in ROOT.iterdir():
                if item.name in ("research", "results", ".git"):
                    continue
                os.symlink(item, tmp_root / item.name)
            (tmp_root / "research").mkdir()
            for path in (ROOT / "research").glob("*.py"):
                os.symlink(path, tmp_root / "research" / path.name)
            planted = tmp_root / "research" / "optimization_models.py"
            planted.unlink()
            planted.write_text((ROOT / "research" / "optimization_models.py").read_text() +
                               "\nfrom research import structural_oracle as _leak\n")
            self.assertIn("LEARNER_IMPORTS_EVALUATOR", self.codes({}, root=tmp_root))
        finally:
            shutil.rmtree(tmp_root)


@unittest.skipUnless(COMPLETE, "requires the completed optimization run of record")
class AuditorMutations(unittest.TestCase):
    def audit(self, mutate: dict) -> dict:
        from research import optimization_audit as au

        tmp = shadow(mutate)
        try:
            out = tmp / "AUDIT.json"
            au.main(["--run", str(tmp), "--output", str(out)])
            return json.loads(out.read_text())
        finally:
            shutil.rmtree(tmp)

    def labels(self, report: dict) -> set:
        return {f["check"] for f in report["findings"]}

    def test_auditor_imports_no_research_module(self):
        import ast

        tree = ast.parse((ROOT / "research" / "optimization_audit.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                         else [node.module or ""])
                self.assertFalse(any(n.startswith("research") for n in names), names)

    def test_dropped_loss_changes_the_primary(self):
        def drop(rows):
            # Remove one repetition of the selected arm on its worst program.
            worst = None
            for row in rows:
                if row["arm"] == "selected_nonmodel" and row["budget_seconds"] == 0.1:
                    worst = row if worst is None or row["product"] > worst["product"] else worst
            return [r for r in rows if r["key"] != worst["key"]]
        report = self.audit({"stages/D_fresh_compiler/rows.jsonl": rows_transform(drop)})
        self.assertTrue({"D_fresh_compiler:no_missing", "primary:programs"} & self.labels(report))

    def test_changed_estimand_is_detected(self):
        def forge(payload):
            payload["primary"]["effect"] += 1e-6
        report = self.audit({"COMPARISON.json": json_transform(forge)})
        self.assertIn("primary:effect", self.labels(report))

    def test_tampered_score_aggregation(self):
        def forge(payload):
            arm = payload["scores"]["arms"]["accepted_default@None"]
            arm["scores"][2] = arm["scores"][2] + 1e-6
        report = self.audit({"PUBLIC_SCORE.json": json_transform(forge)})
        self.assertIn("public:score:accepted_default@None", self.labels(report))

    def test_false_h4_pass_is_detected(self):
        def forge(payload):
            payload["H4_NEW"] = "PASS"
        report = self.audit({"MODEL_EVALUATION.json": json_transform(forge)})
        self.assertIn("h4:no_false_pass", self.labels(report))

    def test_changed_product_is_detected(self):
        def forge(rows):
            rows[10]["product"] += 1
            return rows
        report = self.audit({"stages/D_public/rows.jsonl": rows_transform(forge)})
        self.assertIn("D_public:product", self.labels(report))


if __name__ == "__main__":
    unittest.main()
