"""Resume: the successor auditor rejects the lead's four false-PASS probes and more.

The OLD auditor (``research.third_round_audit``) is run unchanged on the same
overlays and its PASS is asserted, so the demonstration shows both sides.
Every mutation uses temporary copies; no retained evidence is touched.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from research import third_round_audit as old_audit
from research import third_round_resume_audit as ra
from research import third_round_resume_common as rc

PARENT = rc.PARENT_RUN
RESUME = rc.run_dir()


def _rows(path):
    return [json.loads(x) for x in path.read_text().splitlines()]


def _write_rows(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


class Overlay:
    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="resume_audit_")
        base = Path(self.tmp.name)
        self.parent = base / PARENT.name
        self.resume = base / RESUME.name
        shutil.copytree(PARENT, self.parent, ignore=shutil.ignore_patterns("workloads"))
        shutil.copytree(RESUME, self.resume)
        return self

    def __exit__(self, *exc):
        self.tmp.cleanup()

    def successor(self):
        return ra.audit(self.parent, self.resume, self.resume / "RECALIBRATED_PREDICTION.json")


class ReleaseAndLeadProbes(unittest.TestCase):
    def test_unmodified_release_passes(self):
        with Overlay() as o:
            report = o.successor()
            self.assertEqual(report["status"], "PASS", report["findings"][:5])
            self.assertGreater(report["total_checks"], 5000)

    def _both(self, mutate):
        with Overlay() as o:
            mutate(o)
            old = old_audit.audit(o.parent)["status"]
            new = o.successor()
            return old, new

    def test_extra_torn_row(self):
        def m(o):
            with (o.parent / "stages/M_kernel/rows.jsonl").open("a") as f:
                f.write('{"stage_id": "unfinished"')
        old, new = self._both(m)
        self.assertEqual(old, "PASS")               # the lead's probe reproduces
        self.assertEqual(new["status"], "FAIL")
        self.assertIn("STRICT", {f[0] for f in new["findings"]})

    def test_zeroed_kernel_freeze_hash(self):
        def m(o):
            p = o.parent / "WORKLOAD_MANIFEST.json"
            payload = json.loads(p.read_text())
            payload["kernel_stage_sources"]["research/third_round_kernel.py"] = "0" * 64
            p.write_text(json.dumps(payload))
        old, new = self._both(m)
        self.assertEqual(old, "PASS")
        self.assertEqual(new["status"], "FAIL")
        self.assertIn("SOURCES", {f[0] for f in new["findings"]})

    def test_false_m0_instrumentation_parity(self):
        def m(o):
            p = o.parent / "stages/M_diagnosis/rows.jsonl"
            rows = _rows(p)
            for r in rows:
                if r["mode_key"] == "instrumentation_parity":
                    r["parity"] = False
                    break
            _write_rows(p, rows)
        old, new = self._both(m)
        self.assertEqual(old, "PASS")
        self.assertEqual(new["status"], "FAIL")
        self.assertIn("M0", {f[0] for f in new["findings"]})

    def test_missing_not_run(self):
        def m(o):
            (o.parent / "NOT_RUN.json").unlink()
        old, new = self._both(m)
        self.assertEqual(old, "PASS")
        self.assertEqual(new["status"], "FAIL")
        self.assertIn("STAGES", {f[0] for f in new["findings"]})


class FurtherMutations(unittest.TestCase):
    def _fails(self, mutate, area=None):
        with Overlay() as o:
            mutate(o)
            report = o.successor()
            self.assertEqual(report["status"], "FAIL")
            if area:
                self.assertIn(area, {f[0].split(":")[0] for f in report["findings"]})

    def test_blank_line(self):
        def m(o):
            p = o.resume / "stages/R_adapter/rows.jsonl"
            p.write_text(p.read_text() + "\n")
        self._fails(m, "STRICT")

    def test_nan_value(self):
        def m(o):
            p = o.resume / "stages/R_adapter/rows.jsonl"
            lines = p.read_text().splitlines()
            lines[0] = lines[0].replace('"adapter_seconds":', '"adapter_seconds":NaN,"x":', 1)
            p.write_text("\n".join(lines) + "\n")
        self._fails(m)

    def test_changed_adapter_row_payload(self):
        def m(o):
            p = o.resume / "stages/R_adapter/rows.jsonl"
            rows = _rows(p)
            rows[0]["adapter_seconds"] *= 0.5
            _write_rows(p, rows)
        self._fails(m, "MEMBERSHIP")

    def test_duplicate_row(self):
        def m(o):
            p = o.parent / "stages/M_kernel/rows.jsonl"
            rows = _rows(p)
            _write_rows(p, rows + rows[:1])
        self._fails(m, "MEMBERSHIP")

    def test_hidden_retry(self):
        def m(o):
            p = o.resume / "stages/R_adapter/ATTEMPTS.jsonl"
            first = p.read_text().splitlines()[0]
            p.write_text(p.read_text() + first + "\n")
        self._fails(m, "MEMBERSHIP")

    def test_ledger_charge_removed(self):
        def m(o):
            p = o.resume / "MEASUREMENT_WALL_LEDGER.jsonl"
            p.write_text("".join(x + "\n" for x in p.read_text().splitlines()[1:]))
        self._fails(m, "MEMBERSHIP")

    def test_frozen_keys_edited(self):
        def m(o):
            p = o.resume / "stages/R_adapter/EXPECTED_KEYS.json"
            payload = json.loads(p.read_text())
            payload["keys"] = payload["keys"][1:]
            p.write_text(json.dumps(payload))
        self._fails(m, "MEMBERSHIP")

    def test_kernel_parity_part_false(self):
        def m(o):
            p = o.parent / "stages/M_kernel/rows.jsonl"
            rows = _rows(p)
            rows[5]["parity"]["emitted_mismatches"] = 1
            _write_rows(p, rows)
        self._fails(m, "M2")

    def test_missing_stage_states(self):
        self._fails(lambda o: (o.resume / "STAGE_STATES.json").unlink(), "STAGES")

    def test_dependent_launched_without_gate(self):
        def m(o):
            p = o.resume / "STAGE_STATES.json"
            states = json.loads(p.read_text())
            states["gates"]["D"] = "NOT_EVALUATED"
            states["stages"]["C_fixed_work"] = "COMPLETE"
            p.write_text(json.dumps(states))
            (o.resume / "stages" / "C_fixed_work").mkdir(exist_ok=True)
        self._fails(m, "STAGES")

    def test_not_run_stage_with_directory(self):
        def m(o):
            p = o.resume / "STAGE_STATES.json"
            states = json.loads(p.read_text())
            states["stages"]["C_public"] = "NOT_RUN (contradicts its directory)"
            p.write_text(json.dumps(states))
            (o.resume / "stages" / "C_public").mkdir(exist_ok=True)
        self._fails(m, "STAGES")

    def test_false_gate_in_prediction(self):
        def m(o):
            p = o.resume / "RECALIBRATED_PREDICTION.json"
            payload = json.loads(p.read_text())
            payload["gate_met"] = not payload["gate_met"]
            p.write_text(json.dumps(payload))
        self._fails(m, "NUMBERS")

    def test_fabricated_aggregate(self):
        def m(o):
            p = o.resume / "RECALIBRATED_PREDICTION.json"
            payload = json.loads(p.read_text())
            payload["corrected_conservative"] = 0.70
            p.write_text(json.dumps(payload))
        self._fails(m, "NUMBERS")

    def test_old_speedup_median_rejected(self):
        def m(o):
            p = o.resume / "RECALIBRATED_PREDICTION.json"
            payload = json.loads(p.read_text())
            payload["kernel_speedup_median"] = 2.3947613512067907
            p.write_text(json.dumps(payload))
        self._fails(m, "NUMBERS")

    def test_unmapped_field(self):
        def m(o):
            p = o.resume / "RECALIBRATED_PREDICTION.json"
            payload = json.loads(p.read_text())
            payload["claimed_speedup_of_compiler"] = 2.0
            p.write_text(json.dumps(payload))
        self._fails(m, "FIELD_MAP")

    def test_adapter_spec_changed(self):
        def m(o):
            p = o.resume / "ADAPTER_SPEC.json"
            p.write_text(p.read_text().replace("one_implementation", "one_implementation_"))
        self._fails(m, "SOURCES")


class StrictParser(unittest.TestCase):
    def test_common_strict_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.jsonl"
            p.write_text('{"a": 1}\n{"b"')
            with self.assertRaises(rc.StrictRowError):
                rc.strict_rows(p)
            p.write_text('{"a": 1}\n\n')
            with self.assertRaises(rc.StrictRowError):
                rc.strict_rows(p)
            p.write_text('{"a": NaN}\n')
            with self.assertRaises(rc.StrictRowError):
                rc.strict_rows(p)
            p.write_text('[1]\n')
            with self.assertRaises(rc.StrictRowError):
                rc.strict_rows(p)
            p.write_text('{"a": 1}\n')
            self.assertEqual(rc.strict_rows(p), [{"a": 1}])

    def test_resume_protocol_constants(self):
        self.assertEqual(rc.check_protocol_constants()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
