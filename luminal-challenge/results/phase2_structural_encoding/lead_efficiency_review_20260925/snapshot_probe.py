"""Read-only diagnostic of the inherited snapshot-only test failure."""
import json
import os
import subprocess
import unittest
from pathlib import Path

from research_tests import test_phase2_repair as tests

captured = []
original = subprocess.run


def record(*args, **kwargs):
    result = original(*args, **kwargs)
    command = args[0] if args else kwargs.get("args", [])
    if isinstance(command, list) and "research.check_structural_evidence" in command:
        try:
            payload = json.loads(result.stdout)
        except (ValueError, TypeError):
            payload = None
        captured.append({"command": command, "exit": result.returncode, "report": payload})
    return result


def differences(a, b, path=""):
    if type(a) is not type(b):
        return [{"path": path, "before": a, "after": b}]
    if isinstance(a, dict):
        out = []
        for key in sorted(set(a) | set(b)):
            out.extend(differences(a.get(key), b.get(key), path + "/" + key))
        return out
    if isinstance(a, list) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b))
                for d in differences(x, y, path + "/" + str(i))]
    return [] if a == b else [{"path": path, "before": a, "after": b}]


subprocess.run = record
suite = unittest.defaultTestLoader.loadTestsFromName(
    "R3DependencyGate.test_a_real_resumed_run_retains_checker_resolvable_transitive_links",
    tests)
result = unittest.TextTestRunner(verbosity=2).run(suite)
report = {"tests": result.testsRun, "failures": len(result.failures),
          "errors": len(result.errors), "skips": len(result.skipped), "checker_calls": len(captured),
          "reports": captured,
          "differences": differences(captured[-2]["report"], captured[-1]["report"])
          if len(captured) >= 2 else []}
output = Path(__file__).with_name(os.environ.get("LEAD_SNAPSHOT_REPORT", "SNAPSHOT_DIAGNOSIS.json"))
output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "reports"}))
