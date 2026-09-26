"""Stage C reporter and auditor: synthetic dry runs before the confirmation freeze.

Complete positive, negative cost, negative quality, parity mismatch, incomplete
(missing / failed rows), None-valued optional control fields, wrong public
denominator; the auditor's numerical part must agree with the reporter to 1e-9
on both interval endpoints and reject fabricated lower/upper bounds, a false
joint PASS and an unmapped claim.
"""

from __future__ import annotations

import copy
import math
import unittest

from research import third_round_common as tc
from research import third_round_resume_audit as ra
from research import third_round_resume_stage_c as sc

MODES = sc.WALL_MODES


def _row(stage, sha, seed, rep, arm, mode, **extra):
    base = {"stage_id": stage, "program_sha256": sha, "seed": seed, "repetition": rep,
            "arm_id": arm, "mode_key": mode, "correctness": "PASS", "exit_code": 0,
            "timed_out": False, "construction_overrun_count": None, "unknown_queries": 0,
            "validations": 0, "overshoot_seconds": 0.0, "ok": True}
    base.update(extra)
    return base


def matrix(cost=0.5, quality=0.0, mismatch=False, spread=0.02):
    rows = {s: [] for s in ("C_fixed_work", "C_wall", "C_public", "C_export", "C_acceptance")}
    for i, seed in enumerate(range(980000, 980200)):
        sha = f"{seed:064d}"
        jitter = 1 + spread * ((i * 7919) % 13 - 6) / 6
        for rep in range(5):
            for arm in ("R0", "C1"):
                t = 1.0 if arm == "R0" else cost * jitter
                fp = {"t": "x" if (mismatch and i == 3 and arm == "C1") else "t"}
                rows["C_fixed_work"].append(_row("C_fixed_work", sha, seed, rep, arm,
                                                 "work:10000", compile_call_seconds=t, J=50,
                                                 fingerprint=fp))
                for mode in MODES:
                    j = 100 if arm == "R0" else 100 * math.exp(quality) * (
                        1 + spread * ((i * 31) % 5 - 2) / 2)
                    rows["C_wall"].append(_row("C_wall", sha, seed, rep, arm, mode,
                                               compile_call_seconds=0.2, J=j))
        for rep in range(3):
            for arm in ("R0", "C1"):
                rows["C_export"].append(_row("C_export", sha, None, rep, arm, "wall:0.1", J=10))
    for k in range(8):
        sha = f"p{k:063d}"
        for rep in range(5):
            for arm in ("R0", "C1"):
                for mode in MODES:
                    rows["C_public"].append(_row("C_public", sha, None, rep, arm, mode,
                                                 cycles=10, scratch=5, J=50))
            rows["C_public"].append(_row("C_public", sha, None, rep, "serial", "serial",
                                         cycles=20, scratch=6, J=120))
        for rep in range(3):
            for arm in ("R0", "C1"):
                rows["C_export"].append(_row("C_export", sha, None, rep, arm, "wall:0.1", J=50))
    for k in range(142):
        for arm in ("R0", "C1"):
            rows["C_acceptance"].append(_row("C_acceptance", f"a{k:063d}", None, 0, arm,
                                             "wall:0.1", J=1, cases=2))
    keys = {s: [tc.row_key(r) for r in v] for s, v in rows.items()}
    return rows, keys


class ReporterDryRuns(unittest.TestCase):
    def test_complete_positive(self):
        out = sc.comparison(*matrix(cost=0.5, quality=-0.02))
        self.assertTrue(out["complete"])
        self.assertEqual(out["verdict"], "SUCCESS", out["intervals_97_5"])
        self.assertLess(out["intervals_97_5"]["cost"][0], out["intervals_97_5"]["cost"][1])
        for arm_mode, scores in out["descriptive"]["public_scores"].items():
            self.assertEqual(len(scores), 5)
            self.assertAlmostEqual(scores[0], math.sqrt(2 * 1.2))

    def test_negative_cost(self):
        self.assertEqual(sc.comparison(*matrix(cost=0.85))["verdict"], "TARGET_NOT_REACHED")

    def test_negative_quality(self):
        self.assertEqual(sc.comparison(*matrix(quality=0.02))["verdict"], "TARGET_NOT_REACHED")

    def test_parity_mismatch(self):
        out = sc.comparison(*matrix(mismatch=True))
        self.assertFalse(out["fixed_work_parity"]["exact"])
        self.assertEqual(out["verdict"], "TARGET_NOT_REACHED")

    def test_incomplete(self):
        rows, keys = matrix()
        rows["C_wall"] = rows["C_wall"][1:]
        self.assertEqual(sc.comparison(rows, keys)["verdict"], "INCOMPLETE_WITH_EVIDENCE")

    def test_failed_row(self):
        rows, keys = matrix()
        rows["C_export"][5] = dict(rows["C_export"][5], failed=True)
        self.assertEqual(sc.comparison(rows, keys)["verdict"], "INCOMPLETE_WITH_EVIDENCE")

    def test_wrong_public_denominator(self):
        rows = [r for r in matrix()[0]["C_public"]
                if not (r["arm_id"] == "R0" and r["repetition"] == 0
                        and r["program_sha256"].endswith("7"))]
        with self.assertRaises(ValueError):
            sc.public_scores(rows)


class AuditorDryRuns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, keys = matrix(cost=0.5, quality=-0.02)
        cls.comp = sc.comparison(cls.rows, keys)

    def _audit(self, comp, rows=None):
        rep = ra.Report()
        ra._c_numbers(rep, rows or self.rows, comp)
        return rep.result()

    def test_agrees_with_reporter(self):
        result = self._audit(self.comp)
        self.assertEqual(result["status"], "PASS", result["findings"][:5])

    def test_fabricated_upper(self):
        c = copy.deepcopy(self.comp)
        c["intervals_97_5"]["cost"][1] = 0.79
        self.assertEqual(self._audit(c)["status"], "FAIL")

    def test_fabricated_lower(self):
        c = copy.deepcopy(self.comp)
        c["intervals_97_5"]["quality"][0] *= 0.99
        self.assertEqual(self._audit(c)["status"], "FAIL")

    def test_false_joint_pass(self):
        rows, keys = matrix(cost=0.85)
        c = sc.comparison(rows, keys)
        c["success"], c["verdict"] = True, "SUCCESS"
        self.assertEqual(self._audit(c, rows)["status"], "FAIL")

    def test_unmapped_claim(self):
        c = copy.deepcopy(self.comp)
        c["private_grader_score"] = 1.0
        self.assertEqual(self._audit(c)["status"], "FAIL")

    def test_serial_denominator(self):
        rows = copy.deepcopy(self.rows)
        rows["C_public"] = [r for r in rows["C_public"] if not (
            r["arm_id"] == "serial" and r["repetition"] == 4)]
        self.assertEqual(self._audit(self.comp, rows)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
