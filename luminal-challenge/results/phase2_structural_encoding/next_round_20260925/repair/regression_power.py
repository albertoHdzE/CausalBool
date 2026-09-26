"""Run the R1 regression class against the frozen owner and against the successor.

The class under test is ``research_tests.test_next_round_search.InterruptionAccounting``;
only the module it drives (``nrs``) is swapped. Expected: failures on the frozen
owner (the defect), none on the successor (the repair). Writes REGRESSION_POWER.json.
"""
import json, sys, unittest
from pathlib import Path
from research import objective_index_search as ois
from research import next_round_search as nrs
import research_tests.test_next_round_search as t

out = {}
for label, module in (("frozen_objective_index_search", ois), ("successor_next_round_search", nrs)):
    t.nrs = module
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(t.InterruptionAccounting)
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=0).run(suite)
    out[label] = {"tests": result.testsRun, "failures": len(result.failures),
                  "errors": len(result.errors),
                  "failed_tests": sorted(c.id().split(".")[-1] for c, _ in result.failures + result.errors)}
t.nrs = nrs
out["status"] = ("PASS" if out["frozen_objective_index_search"]["failures"]
                 + out["frozen_objective_index_search"]["errors"] > 0
                 and out["successor_next_round_search"]["failures"]
                 + out["successor_next_round_search"]["errors"] == 0 else "FAIL")
Path(__file__).with_name("REGRESSION_POWER.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out))
