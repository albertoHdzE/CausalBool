"""R3: the successor checker approves only exact, evidenced historical deviations."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from research import efficiency_checker as ck
from research import efficiency_common as ec

RUN = ec.run_dir()
AUDIT = RUN / "assurance" / "successor_audit" / "SUCCESSOR_AUDIT.json"
FULL = RUN / "assurance" / "checker" / "HISTORICAL_CHECKER_FULL.json"


class Dispositions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.findings = json.loads(FULL.read_text())["all_findings"]
        cls.evidence = ck.evidence(RUN, AUDIT)

    def test_unchanged_evidence_approves_exactly_the_two_dispositions(self):
        result = ck.classify(self.findings, self.evidence)
        self.assertEqual(result["unapproved"], [])
        self.assertEqual(len(result["approved"]), 421)
        self.assertTrue(result["dispositions"]["D1"]["approved"])
        self.assertTrue(result["dispositions"]["D2"]["approved"])

    def test_an_unknown_finding_is_unapproved(self):
        findings = self.findings + [{"code": "ROW_MANIFEST_MISMATCH", "detail": "x"}]
        result = ck.classify(findings, self.evidence)
        self.assertEqual([f["code"] for f in result["unapproved"]], ["ROW_MANIFEST_MISMATCH"])

    def test_a_known_code_with_a_different_count_is_unapproved(self):
        findings = [f for f in self.findings if f["code"] != "ORACLE_LEAK"] + [
            f for f in self.findings if f["code"] == "ORACLE_LEAK"][:419]
        result = ck.classify(findings, self.evidence)
        self.assertFalse(result["dispositions"]["D2"]["approved"])
        self.assertEqual(len(result["unapproved"]), 419)

    def test_a_known_code_on_a_different_file_is_unapproved(self):
        findings = [f if f["code"] != "FROZEN_SOURCE_CHANGED" else
                    dict(f, detail="['research/next_round_search.py']") for f in self.findings]
        result = ck.classify(findings, self.evidence)
        self.assertFalse(result["dispositions"]["D1"]["approved"])
        self.assertIn("FROZEN_SOURCE_CHANGED", [f["code"] for f in result["unapproved"]])

    def test_failed_replay_evidence_withdraws_d2(self):
        ev = copy.deepcopy(self.evidence)
        ev["D2"]["replay_rows_sha256_now"] = "0" * 64
        self.assertFalse(ck.classify(self.findings, ev)["dispositions"]["D2"]["approved"])
        ev = copy.deepcopy(self.evidence)
        ev["D2"]["live_ranker_sha256"] = "1" * 64
        self.assertFalse(ck.classify(self.findings, ev)["dispositions"]["D2"]["approved"])

    def test_failed_audit_withdraws_d1(self):
        ev = copy.deepcopy(self.evidence)
        ev["D1"]["successor_audit_primary_or_candidate_findings"] = ["PRIMARY"]
        self.assertFalse(ck.classify(self.findings, ev)["dispositions"]["D1"]["approved"])

    def test_wider_analysis_change_breaks_the_exact_scope(self):
        live = (ec.ROOT / ck.ANALYSIS).read_text()
        planted = live.replace("TIE = 1e-12", "TIE = 1e-9")
        self.assertNotEqual(planted, live)
        scope = ck.analysis_scope(ck.ANALYSIS_AT_FREEZE.read_text(), planted)
        self.assertFalse(scope["exact_scope"])
        second_skip = live.replace("            values[row[\"program_sha256\"]].append(value)",
                                   "            if value is None:\n                continue\n"
                                   "            values[row[\"program_sha256\"]].append(value)")
        self.assertFalse(ck.analysis_scope(ck.ANALYSIS_AT_FREEZE.read_text(),
                                           second_skip)["exact_scope"])
        self.assertTrue(ck.analysis_scope(ck.ANALYSIS_AT_FREEZE.read_text(), live)["exact_scope"])


class Immutability(unittest.TestCase):
    def test_changed_source_is_reported(self):
        starting = RUN / "SOURCE_MANIFESTS" / "starting"
        lines = (starting / "source_sha256.txt").read_text().splitlines()
        target = next(i for i, l in enumerate(lines) if l.endswith("research/next_round_search.py"))
        digest, name = lines[target].split(None, 1)
        lines[target] = f"{'0' * 64}  {name}"
        with tempfile.TemporaryDirectory() as tmp:
            planted = Path(tmp) / "source_sha256.txt"
            planted.write_text("\n".join(lines) + "\n")
            result = ck.immutability(RUN, source_manifest=planted)
        self.assertEqual(result["changed_sources"], ["research/next_round_search.py"])
        self.assertGreater(result["sources_checked"], 50)

    def test_unchanged_tree_has_no_changed_source_or_result(self):
        result = ck.immutability(RUN)
        self.assertEqual(result["changed_sources"], [])
        self.assertEqual(result["changed_results"], [])
        self.assertGreater(result["results_checked"], 800)


if __name__ == "__main__":
    unittest.main()
