"""Third round: the independent auditor accepts the release and rejects planted defects."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from research import optimization_common as oc
from research import third_round_audit as ta
from research import third_round_common as tc

RUN = tc.run_dir()


def _inputs():
    rows_m0 = oc.read_rows(RUN / "stages/M_diagnosis/rows.jsonl")
    rows_k = oc.read_rows(RUN / "stages/M_kernel/rows.jsonl")
    prediction = json.loads((RUN / "PREDICTION.json").read_text())
    decision = json.loads((RUN / "MECHANISM_DECISION.json").read_text())
    return rows_m0, rows_k, prediction, decision


class NumericalAudit(unittest.TestCase):
    def setUp(self):
        self.m0, self.k, self.pred, self.dec = _inputs()

    def audit(self, m0=None, k=None, pred=None, dec=None):
        return ta.numerical_audit(self.m0 if m0 is None else m0, self.k if k is None else k,
                                  self.pred if pred is None else pred,
                                  self.dec if dec is None else dec)

    def test_release_passes(self):
        report = self.audit()
        self.assertEqual(report["status"], "PASS", report["findings"][:5])
        self.assertGreater(report["checks"], 300)
        self.assertEqual(report["programs"], 30)

    def test_refuses_empty(self):
        with self.assertRaises(ValueError):
            ta.numerical_audit([], [], self.pred, self.dec)

    def test_fabricated_conservative_ratio(self):
        pred = copy.deepcopy(self.pred)
        pred["predicted_ratio_conservative_equal_family"] = 0.79
        self.assertEqual(self.audit(pred=pred)["status"], "FAIL")

    def test_false_gate_pass(self):
        pred = copy.deepcopy(self.pred)
        pred["gate_met"] = True
        dec = copy.deepcopy(self.dec)
        dec["gate"]["met"] = True
        dec["decision"] = "INTEGRATE_C1"
        self.assertEqual(self.audit(pred=pred, dec=dec)["status"], "FAIL")

    def test_changed_program_field(self):
        pred = copy.deepcopy(self.pred)
        pred["programs"]["800005"]["O"] *= 1.01
        self.assertEqual(self.audit(pred=pred)["status"], "FAIL")

    def test_missing_kernel_row(self):
        self.assertEqual(self.audit(k=self.k[1:])["status"], "FAIL")

    def test_duplicate_time_row(self):
        dup = [r for r in self.m0 if r["mode_key"] == "work:10000"][:1]
        self.assertEqual(self.audit(m0=self.m0 + dup)["status"], "FAIL")

    def test_failed_row_not_droppable(self):
        k = copy.deepcopy(self.k)
        k[0]["failed"] = True
        self.assertEqual(self.audit(k=k)["status"], "FAIL")

    def test_parity_false(self):
        k = copy.deepcopy(self.k)
        k[3]["parity"]["parity"] = False
        self.assertEqual(self.audit(k=k)["status"], "FAIL")

    def test_wrong_family_weight(self):
        # Six programs per family make pooled == equal-family; weight families by
        # their summed T0 instead (a plausible wrong weight) and it must fail.
        import collections
        import math
        logs, weight = collections.defaultdict(list), collections.Counter()
        for seed, p in self.pred["programs"].items():
            logs[p["family"]].append(math.log(p["ratio_conservative"]))
            weight[p["family"]] += p["T0"]
        total = sum(weight.values())
        wrong = math.exp(sum(weight[f] / total * sum(v) / len(v) for f, v in logs.items()))
        self.assertGreater(abs(wrong - self.pred["predicted_ratio_conservative_equal_family"]),
                           1e-6)
        pred = copy.deepcopy(self.pred)
        pred["predicted_ratio_conservative_equal_family"] = wrong
        self.assertEqual(self.audit(pred=pred)["status"], "FAIL")


class IdentityCheck(unittest.TestCase):
    def _copy(self, tmp: Path) -> Path:
        run = tmp / RUN.name
        shutil.copytree(RUN, run, ignore=shutil.ignore_patterns("workloads"))
        return run

    def test_release_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = ta.identity_check(self._copy(Path(tmp)))
            self.assertEqual(report["status"], "PASS", report["findings"])

    def test_dependent_stage_started(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self._copy(Path(tmp))
            (run / "stages" / "D_fixed_work").mkdir()
            self.assertEqual(ta.identity_check(run)["status"], "FAIL")

    def test_workload_manifest_tampered(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self._copy(Path(tmp))
            path = run / "WORKLOAD_MANIFEST.json"
            manifest = json.loads(path.read_text())
            manifest["workloads"]["800000"]["sha256"] = "0" * 64
            path.write_text(json.dumps(manifest))
            self.assertEqual(ta.identity_check(run)["status"], "FAIL")

    def test_torn_or_missing_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self._copy(Path(tmp))
            path = run / "stages/M_kernel/rows.jsonl"
            lines = path.read_text().splitlines()
            path.write_text("\n".join(lines[:-1]) + "\n" + lines[-1][:40])
            self.assertEqual(ta.identity_check(run)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
