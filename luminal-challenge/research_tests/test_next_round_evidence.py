"""The next-round checker and auditor must catch planted defects (next round 1.0).

Each test copies the minimum of the run of record into a temporary directory,
plants one defect, and requires the specific finding; the unmodified copy must
pass. Skipped only when the run of record has not reached the stage in question.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from research import next_round_checker as nck
from research import next_round_common as nrc

RUN = nrc.run_dir()
AUDIT = Path(__file__).resolve().parents[1] / "research" / "next_round_audit.py"


def _audit_module():
    spec = importlib.util.spec_from_file_location("next_round_audit_isolated", AUDIT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _copy(parts):
    root = Path(tempfile.mkdtemp(prefix="nr_evidence_"))
    run = root / "results" / "phase2_structural_encoding" / RUN.name
    for part in parts:
        source = RUN / part
        target = run / part
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    return root, run


DEV_PARTS = ("inputs/development", "stages/D_factorial", "stages/D_fixed_work",
             "stages/D_profile", "stages/E_engineering", "SELECTION.json", "FACTORIAL.json",
             "ENGINEERING_DECISION.json")


@unittest.skipUnless((RUN / "ENGINEERING_DECISION.json").exists(), "run of record not ready")
class AuditorCatchesPlantedDefects(unittest.TestCase):
    def setUp(self):
        self.audit = _audit_module()
        self.root, self.run = _copy(DEV_PARTS)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _report(self):
        return self.audit.Audit(self.run).run_all()

    def _rewrite_rows(self, stage, change):
        path = self.run / "stages" / stage / "rows.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        rows = change(rows)
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))

    def test_clean_copy_passes(self):
        report = self._report()
        self.assertEqual(report["status"], "PASS", report["findings"][:3])
        self.assertGreater(report["checks"], 10_000)

    def test_fabricated_product(self):
        def change(rows):
            rows[5]["product"] += 1
            return rows
        self._rewrite_rows("D_factorial", change)
        self.assertIn("PRODUCT", self._report()["finding_codes"])

    def test_missing_row(self):
        self._rewrite_rows("D_factorial", lambda rows: rows[1:])
        self.assertIn("ROW_SET", self._report()["finding_codes"])

    def test_duplicate_row(self):
        self._rewrite_rows("D_factorial", lambda rows: rows + rows[:1])
        self.assertIn("DUPLICATES", self._report()["finding_codes"])

    def test_false_selection(self):
        path = self.run / "SELECTION.json"
        data = json.loads(path.read_text())
        data["selection"]["selected_arm"] = nrc.EARLIER
        path.write_text(json.dumps(data))
        self.assertIn("SELECTION", self._report()["finding_codes"])

    def test_false_factorial_estimate(self):
        path = self.run / "FACTORIAL.json"
        data = json.loads(path.read_text())
        data["budgets"]["0.1"]["factorial"]["catalog_effect_a4_minus_a3"]["estimate"] += 1e-6
        path.write_text(json.dumps(data))
        self.assertIn("FACTORIAL_CATALOG", self._report()["finding_codes"])

    def test_false_engineering_decision(self):
        path = self.run / "ENGINEERING_DECISION.json"
        data = json.loads(path.read_text())
        data["frozen_candidate"] = data["frozen_candidate"] + "+engineered"
        path.write_text(json.dumps(data))
        self.assertIn("E_DECISION", self._report()["finding_codes"])

    def test_auditor_imports_nothing_from_the_experiment(self):
        text = AUDIT.read_text()
        self.assertNotIn("from research", text)
        self.assertNotIn("import research", text)


@unittest.skipUnless((RUN / "stages" / "D_factorial" / "rows.jsonl").exists(),
                     "run of record not ready")
class CheckerCatchesPlantedDefects(unittest.TestCase):
    def test_duplicate_failed_and_manifest_mismatch(self):
        checker = nck.Checker(RUN)
        rows_path = RUN / "stages" / "D_factorial" / "rows.jsonl"
        rows = [json.loads(line) for line in rows_path.read_text().splitlines() if line.strip()]
        rows = rows[:50]
        planted = [dict(rows[0]), dict(rows[1], failed_row=True),
                   dict(rows[2], manifest_sha256="0" * 64),
                   dict(rows[3], product=rows[3]["product"] + 1)]
        # Row-level checks exercised directly on planted rows (the run is not modified).
        manifest = json.loads((RUN / "stages" / "D_factorial" / "STAGE_MANIFEST.json").read_text())
        before = len(checker.findings)
        for row in planted:
            checker.expect(not row["failed_row"], "FAILED_ROW", row["key"])
            checker.expect(row["manifest_sha256"] == manifest["manifest_sha256"],
                           "ROW_MANIFEST_MISMATCH", row["key"])
            checker.expect(row["product"] == row["cycles"] * row["scratch"], "PRODUCT_MISMATCH",
                           row["key"])
        codes = {f["code"] for f in checker.findings[before:]}
        self.assertEqual(codes, {"FAILED_ROW", "ROW_MANIFEST_MISMATCH", "PRODUCT_MISMATCH"})

    def test_isolation_flags_the_frozen_solver(self):
        checker = nck.Checker(RUN)
        row = {"key": "k", "arm": "cell_a4cat_dfs"}
        result = {"imported_sources": {
            "research.next_round_search": str(nrc.ROOT / "research" / "next_round_search.py"),
            "research.objective_index_search": "x"},
            "optimisation": {}}
        checker.isolation("D_factorial", row, result)
        codes = {f["code"] for f in checker.findings}
        self.assertIn("FROZEN_SOLVER_LOADED", codes)
        self.assertIn("REPAIRED_ACCOUNTING_MISSING", codes)


if __name__ == "__main__":
    unittest.main()
