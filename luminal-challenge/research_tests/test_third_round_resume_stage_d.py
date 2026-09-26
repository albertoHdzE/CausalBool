"""Stage D reporter and auditor: synthetic dry runs before the timing freeze.

Complete positive, negative (cost, quality, parity), incomplete (missing,
failed, incorrect) and None-valued optional control fields. The auditor's
numerical part (``_dev_numbers``) must accept the reporter's output on the
positive matrix and reject fabricated fields, a false PASS and an unmapped claim.
"""

from __future__ import annotations

import copy
import unittest

from research import third_round_common as tc
from research import third_round_resume_audit as ra
from research import third_round_resume_stage_d as sd

FP = {"trace_sha256": "t", "certificates": "c", "aggregate": {"nodes": 1}}


def _row(stage, seed, rep, arm, **extra):
    base = {"stage_id": stage, "program_sha256": f"p{seed}", "seed": seed, "repetition": rep,
            "arm_id": arm, "mode_key": sd.STAGES[stage], "correctness": "PASS",
            "discrepancy_count": 0, "cases": 2, "exit_code": 0, "timed_out": False,
            "construction_overrun_count": None, "interrupted_validation_total": None,
            "unknown_queries": 0, "nodes": 10}
    base.update(extra)
    return base


def matrix(cost=0.5, quality=-0.01, mismatch=False):
    fixed, wall, memory = [], [], []
    for seed in range(800000, 800100):
        for rep in range(3):
            for arm in ("R0", "C1"):
                t = 1.0 if arm == "R0" else cost
                fp = dict(FP, trace_sha256="x" if (mismatch and seed == 800003 and arm == "C1")
                          else "t")
                fixed.append(_row("D_fixed_work", seed, rep, arm, compile_call_seconds=t,
                                  J=100, fingerprint=fp))
                j = 100 if arm == "R0" else 100 * (2.718281828459045 ** quality)
                wall.append(_row("D_wall", seed, rep, arm, compile_call_seconds=0.2, J=j))
    for seed in range(800000, 800030):
        for arm in ("R0", "C1"):
            memory.append(_row("D_memory", seed, 0, arm, tracemalloc_peak_bytes=1000,
                               fingerprint=FP, J=100))
    keys = {s: [tc.row_key(r) for r in rows] for s, rows in
            (("D_fixed_work", fixed), ("D_wall", wall), ("D_memory", memory))}
    return fixed, wall, memory, keys


class ReporterDryRuns(unittest.TestCase):
    def test_complete_positive(self):
        out = sd.development(*matrix())
        self.assertTrue(out["complete"])
        self.assertEqual(out["verdict"], "PASS")
        self.assertAlmostEqual(out["fixed_work_compile_ratio_equal_family"], 0.5)
        self.assertAlmostEqual(out["wall_primary_mean_log_J_ratio_equal_family"], -0.01)

    def test_negative_cost(self):
        self.assertEqual(sd.development(*matrix(cost=0.95))["verdict"],
                         "DEVELOPMENT_TARGET_NOT_REACHED")

    def test_negative_quality(self):
        self.assertEqual(sd.development(*matrix(quality=0.001))["verdict"],
                         "DEVELOPMENT_TARGET_NOT_REACHED")

    def test_parity_mismatch_blocks(self):
        out = sd.development(*matrix(mismatch=True))
        self.assertFalse(out["fixed_work_parity"]["exact"])
        self.assertFalse(out["gate_met"])

    def test_incomplete_missing_row(self):
        fixed, wall, memory, keys = matrix()
        out = sd.development(fixed[1:], wall, memory, keys)
        self.assertEqual(out["verdict"], "INCOMPLETE_WITH_EVIDENCE")

    def test_failed_row_not_droppable(self):
        fixed, wall, memory, keys = matrix()
        wall[7] = dict(wall[7], failed=True)
        self.assertEqual(sd.development(fixed, wall, memory, keys)["verdict"],
                         "INCOMPLETE_WITH_EVIDENCE")

    def test_incorrect_row(self):
        fixed, wall, memory, keys = matrix()
        memory[3] = dict(memory[3], correctness="FAIL")
        self.assertEqual(sd.development(fixed, wall, memory, keys)["verdict"],
                         "INCOMPLETE_WITH_EVIDENCE")

    def test_refuses_empty(self):
        with self.assertRaises(ValueError):
            sd.development([], [], [], {"D_fixed_work": [], "D_wall": [], "D_memory": []})


class AuditorDryRuns(unittest.TestCase):
    def _audit(self, report, rows):
        rep = ra.Report()
        ra._dev_numbers(rep, rows, report)
        return rep.result()

    def setUp(self):
        fixed, wall, memory, keys = matrix()
        self.rows = {"D_fixed_work": fixed, "D_wall": wall, "D_memory": memory}
        self.report = sd.development(fixed, wall, memory, keys)

    def test_accepts_reporter(self):
        result = self._audit(self.report, self.rows)
        self.assertEqual(result["status"], "PASS", result["findings"][:5])

    def test_fabricated_cost(self):
        r = copy.deepcopy(self.report)
        r["fixed_work_compile_ratio_equal_family"] = 0.4
        self.assertEqual(self._audit(r, self.rows)["status"], "FAIL")

    def test_false_pass(self):
        fixed, wall, memory, keys = matrix(cost=0.95)
        rows = {"D_fixed_work": fixed, "D_wall": wall, "D_memory": memory}
        r = sd.development(fixed, wall, memory, keys)
        r["gate_met"], r["verdict"] = True, "PASS"
        self.assertEqual(self._audit(r, rows)["status"], "FAIL")

    def test_hidden_parity_mismatch(self):
        fixed, wall, memory, keys = matrix(mismatch=True)
        rows = {"D_fixed_work": fixed, "D_wall": wall, "D_memory": memory}
        r = sd.development(fixed, wall, memory, keys)
        r["fixed_work_parity"] = {"pairs": 300, "mismatches": [], "exact": True}
        self.assertEqual(self._audit(r, rows)["status"], "FAIL")

    def test_unmapped_claim(self):
        r = copy.deepcopy(self.report)
        r["compiler_speedup_claim"] = 3.0
        self.assertEqual(self._audit(r, self.rows)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
