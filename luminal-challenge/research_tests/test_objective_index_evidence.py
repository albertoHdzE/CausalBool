"""Mutation tests of the objective-index evidence checker and independent auditor.

Each test builds a shadow of the run of record in a temporary directory --
every file a symbolic link to the real one except the single file being
mutated, which is a modified copy -- and asserts that the checker or auditor
raises the specific finding the planted defect must raise, and that the
unmutated shadow does not. The run of record is never written.

Development-stage mutations run as soon as those stages exist; post-freeze and
claim mutations are skipped until the corresponding artifacts exist. All of
these are run after timing stops.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results" / "phase2_structural_encoding" / "objective_index_20260924"
HAS_DEV = (RUN / "stages" / "DEV_model" / "rows.jsonl").exists() and \
    (RUN / "stages" / "DEV_compiler" / "rows.jsonl").exists()
HAS_EVAL = (RUN / "PUBLIC_SCORE.json").exists() and (RUN / "LEARNING.json").exists() and \
    (RUN / "COMPARISON.json").exists()
LINK_WHOLE = ("frozen_control_workspace", "export", "inputs", "SOURCE_MANIFESTS", "fixtures",
              "pruning_replay", "theory", "stage_a", "logs", "isolation")


def shadow(mutate: dict, extra: dict = None) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="oi_shadow_"))
    for current, dirs, files in os.walk(RUN):
        rel = Path(current).relative_to(RUN)
        if rel.parts and rel.parts[0] in LINK_WHOLE:
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
    for key, text in (extra or {}).items():
        (tmp / key).parent.mkdir(parents=True, exist_ok=True)
        (tmp / key).write_text(text)
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


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from research import objective_index_audit as au
        from research import objective_index_checker as ck

        cls.ck, cls.au = ck, au
        base = shadow({})
        try:
            cls.base_codes = set(ck.Checker(base).run_all()["finding_codes"])
            cls.base_audit = {f["check"] for f in au.Audit(base).run_all()["findings"]}
        finally:
            shutil.rmtree(base)

    def codes(self, mutate: dict, extra: dict = None) -> set:
        tmp = shadow(mutate, extra)
        try:
            return set(self.ck.Checker(tmp).run_all()["finding_codes"])
        finally:
            shutil.rmtree(tmp)

    def audit_checks(self, mutate: dict) -> set:
        tmp = shadow(mutate)
        try:
            return {f["check"] for f in self.au.Audit(tmp).run_all()["findings"]}
        finally:
            shutil.rmtree(tmp)

    def assertRaisesFinding(self, code: str, mutate: dict, extra: dict = None) -> None:
        self.assertNotIn(code, self.base_codes)
        self.assertIn(code, self.codes(mutate, extra))


@unittest.skipUnless(HAS_DEV, "requires the development stages of the run of record")
class DevelopmentMutations(_Base):
    def test_missing_row(self):
        self.assertRaisesFinding("MISSING_ROWS", {
            "stages/DEV_model/rows.jsonl": rows_transform(lambda rows: rows[1:])})

    def test_duplicate_row(self):
        self.assertRaisesFinding("DUPLICATE_ROWS", {
            "stages/DEV_model/rows.jsonl": rows_transform(lambda rows: rows + rows[:1])})

    def test_row_from_another_manifest(self):
        def forge(rows):
            rows[3]["manifest_sha256"] = "f" * 64
            return rows
        self.assertRaisesFinding("ROW_MANIFEST_MISMATCH", {
            "stages/DEV_model/rows.jsonl": rows_transform(forge)})

    def test_fabricated_discovery_is_rejected_against_the_oracle(self):
        def forge(rows):
            for row in rows:
                if row["arm"] == "tree" and row.get("result"):
                    row["result"]["found"].append({"identity": "{\"forged\":1}",
                                                   "product": 1, "index": "0"})
                    break
            return rows
        self.assertRaisesFinding("FABRICATED_DISCOVERY", {
            "stages/DEV_model/rows.jsonl": rows_transform(forge)})

    def test_training_object_reported_as_new(self):
        split = json.loads((RUN / "fixtures" / "development" / "development_920000" /
                            "split.json").read_text())
        oracle = json.loads((RUN / "fixtures" / "development" / "development_920000" /
                             "oracle.json").read_text())
        product = {x["identity"]: x["product"] for x in oracle["feasible"]}
        leaked = split["train"][0]

        def forge(rows):
            for row in rows:
                if row["fixture_id"] == "development_920000" and row["arm"] == "tree":
                    row["result"]["found"].append({"identity": leaked,
                                                   "product": product[leaked], "index": "0"})
                    break
            return rows
        self.assertRaisesFinding("TRAINING_OBJECT_REPORTED_NEW", {
            "stages/DEV_model/rows.jsonl": rows_transform(forge)})

    def test_wrong_pool_hash(self):
        def forge(rows):
            for row in rows:
                if row["arm"] == "hamming" and (row.get("result") or {}).get("info", {}).get(
                        "pool_sha256"):
                    row["result"]["info"]["pool_sha256"] = "0" * 64
                    break
            return rows
        self.assertRaisesFinding("POOL_HASH_DIFFERS_ACROSS_ARMS", {
            "stages/DEV_model/rows.jsonl": rows_transform(forge)})

    def test_negative_control_proposing_novel_objects(self):
        def forge(rows):
            for row in rows:
                if row["arm"] == "empirical_cover" and row.get("result"):
                    row["result"]["counts"]["novel"] = 3
                    break
            return rows
        self.assertRaisesFinding("NEGATIVE_CONTROL_PROPOSED_NOVEL", {
            "stages/DEV_model/rows.jsonl": rows_transform(forge)})

    def test_discrepancy_not_failed(self):
        def forge(rows):
            for row in rows:
                if row["arm"] == "A4_multiscale_search":
                    row["result"]["discrepancy_count"] = 1
                    break
            return rows
        self.assertRaisesFinding("DISCREPANCY_NOT_FAILED", {
            "stages/DEV_compiler/rows.jsonl": rows_transform(forge)})

    def test_learned_stage_without_gate(self):
        self.assertRaisesFinding("LEARNED_COMPILER_RUN_WITHOUT_H_LEARN", {}, extra={
            "stages/EVAL_learned_tree/rows.jsonl": "",
            "stages/EVAL_learned_tree/EXPECTED_KEYS.json": json.dumps({"keys": ["x"]}),
            "stages/EVAL_learned_tree/STAGE_MANIFEST.json": json.dumps(
                {"manifest_sha256": "0", "extra": {"cells": [], "repetitions": 15,
                                                   "programs": []}}),
            "stages/EVAL_learned_tree/resume_log.jsonl": "",
            "stages/EVAL_learned_tree/commands.jsonl": ""})

    def test_auditor_detects_a_tampered_development_product(self):
        def forge(rows):
            for row in rows:
                if row["arm"] == "A4_multiscale_search" and row["budget_seconds"] == 0.1:
                    row["product"] = row["product"] + 1
                    break
            return rows
        found = self.audit_checks({"stages/DEV_compiler/rows.jsonl": rows_transform(forge)})
        self.assertIn("J=C*S", found - self.base_audit)

    def test_auditor_detects_a_changed_selection(self):
        def forge(payload):
            payload["selection"]["selected_arm"] = "A1_deadline_control"
        found = self.audit_checks({"DEVELOPMENT.json": json_transform(forge)})
        self.assertIn("dev_selected_arm", found - self.base_audit)


@unittest.skipUnless(HAS_EVAL, "requires the completed evaluation of the run of record")
class EvaluationMutations(_Base):
    def test_row_without_freeze(self):
        def forge(rows):
            rows[0]["freeze_sha256"] = "0" * 64
            return rows
        self.assertRaisesFinding("ROW_WITHOUT_FREEZE", {
            "stages/EVAL_public/rows.jsonl": rows_transform(forge)})

    def test_source_change_after_freeze(self):
        def forge(payload):
            name = "research/objective_index_search.py"
            payload["sources"]["research"][name] = "0" * 64
        self.assertRaisesFinding("POST_FREEZE_SOURCE_CHANGE", {
            "FROZEN_SELECTION.json": json_transform(forge)})

    def test_false_h_learn_pass(self):
        def forge(payload):
            payload["H_LEARN"]["verdict"] = "PASS"
        self.assertRaisesFinding("FALSE_H_LEARN_VERDICT", {"LEARNING.json": json_transform(forge)})

    def test_false_primary_claim(self):
        def forge(payload):
            payload["primary"]["claim_best_average_quality"] = \
                not payload["primary"]["claim_best_average_quality"]
        self.assertRaisesFinding("FALSE_PRIMARY_CLAIM", {"COMPARISON.json": json_transform(forge)})

    def test_wrong_score_denominator(self):
        def forge(payload):
            for arm in payload["score"]["scores"]["arms"].values():
                if arm["scores"][0] is not None:
                    arm["scores"][0] *= 1.01
                    break
        self.assertRaisesFinding("SCORE_DENOMINATOR", {"PUBLIC_SCORE.json": json_transform(forge)})

    def test_false_strict_public_gain(self):
        def forge(payload):
            for entry in payload["score"]["ratios"].values():
                entry["strict_improvement_every_repetition"] = \
                    not entry["strict_improvement_every_repetition"]
                break
        self.assertRaisesFinding("FALSE_PUBLIC_STRICT_GAIN", {
            "PUBLIC_SCORE.json": json_transform(forge)})

    def test_serial_denominator_tampering(self):
        def forge(rows):
            rows[0]["cycles"] += 1
            rows[0]["product"] = rows[0]["cycles"] * rows[0]["scratch"]
            rows[0]["result"]["cycles"] = rows[0]["cycles"]
            return rows
        found = self.audit_checks({"stages/EVAL_public_serial/rows.jsonl":
                                   rows_transform(forge)})
        self.assertIn("serial_stable", found - self.base_audit)

    def test_auditor_detects_a_changed_interval(self):
        def forge(payload):
            contrast = payload["primary"]["contrasts"]["classical"]
            contrast["interval"][0] += 0.01
        found = self.audit_checks({"COMPARISON.json": json_transform(forge)})
        self.assertIn("primary_low:classical", found - self.base_audit)

    def test_auditor_detects_a_changed_h_learn_point(self):
        def forge(payload):
            payload["H_LEARN"]["contrasts"]["hamming"]["point"] = 0.5
        found = self.audit_checks({"LEARNING.json": json_transform(forge)})
        self.assertIn("learn_point:hamming", found - self.base_audit)


if __name__ == "__main__":
    unittest.main()
