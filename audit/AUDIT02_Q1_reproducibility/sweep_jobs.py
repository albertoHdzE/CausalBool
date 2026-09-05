"""AUDIT02/Q1 job list — a second JOBS set for the reproducibility sweep.

AUDIT03-C. This file was UNRUNNABLE and had been for some time. It obtained its
`run` helper by exec-ing /tmp/q1_sweep.py:

    sys.path.insert(0,'/tmp')
    exec(open('/tmp/q1_sweep.py').read().split('JOBS = []')[0])

That temp file is long gone, so the script raised FileNotFoundError at line 3 and
`ruff --select F` flagged the consequence statically as F821 (undefined name
`run`). Worse, had the exec merely produced nothing, every job would have been
recorded as "ERR name 'run' is not defined" and reported WILL-NOT-RUN -- a
harness confidently reporting a result it never computed, which is the exact
class of defect this audit exists to remove.

The helper it was copying already lives in the sibling sweep_harness.py, which
defines sh/committed_files/snap/elementwise_diff/json_diff/run and guards its own
main loop with __name__ == "__main__". It now imports from that owner. One
concept, one home.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sweep_harness import run  # noqa: E402  (path must be set first)

JOBS = [
 ("causalNet/export_notebook_results", ".venv/bin/python scripts/export_notebook_results.py",
  "imp-causalNet-paper/results", "imp-causalNet-paper"),
 ("pathinfo/causalbool_mirror", ".venv/bin/python scripts/causalbool_mirror.py",
  "imp-pathinfo-paper/results", "imp-pathinfo-paper"),
 ("pathinfo/analyse_sizebins", ".venv/bin/python scripts/analyse_sizebins.py",
  "imp-pathinfo-paper/results", "imp-pathinfo-paper"),
 ("pathinfo/campaign_status", ".venv/bin/python scripts/campaign_status.py",
  "imp-pathinfo-paper/results", "imp-pathinfo-paper"),
 ("prices/phase1_stability", ".venv/bin/python scripts/phase1_stability.py",
  "imp-prices/results", "imp-prices"),
 ("prices/phase1b_gate_network", ".venv/bin/python scripts/phase1b_gate_network.py",
  "imp-prices/results", "imp-prices"),
 ("prices/phase2_gate", ".venv/bin/python scripts/phase2_gate.py",
  "imp-prices/results", "imp-prices"),
 ("prices/phase2_forecast", ".venv/bin/python scripts/phase2_forecast.py",
  "imp-prices/results", "imp-prices"),
 ("prices/phase1_b4_description_length", ".venv/bin/python scripts/phase1_b4_description_length.py",
  "imp-prices/results", "imp-prices"),
 ("prices/gate10_feasibility", ".venv/bin/python scripts/gate10_feasibility.py",
  "imp-prices/results", "imp-prices"),
 ("prices/lint_ledger_full", ".venv/bin/python scripts/lint_ledger_full.py",
  "imp-prices/results", "imp-prices"),
 ("causal/index_method_comparison", ".venv/bin/python index_method_comparison/run_comparison.py",
  "imp-causal-paper/results", "imp-causal-paper"),
]
out=[]
for label,cmd,prefix,cwd in JOBS:
    print(f"-- {label}", flush=True)
    try: res = run(label, cmd, prefix, cwd)
    except Exception as e:
        res=dict(label=label,cmd=cmd,exit=f"ERR {e}",ran=False,n_changed=0,changed=[],diffs={})
    out.append(res)
    flag = "OK-identical" if res["ran"] and res["n_changed"]==0 else ("DIFFERS" if res["ran"] else "WILL-NOT-RUN")
    print(f"   {flag}  exit={res['exit']}  changed={res['n_changed']}", flush=True)
    if not res["ran"]: print("     ", res.get("stderr_tail"))
json.dump(out, open('/tmp/q1b_results.json','w'), indent=1)
print("\n=== SUMMARY ===")
for r in out:
    flag = "OK-identical" if r["ran"] and r["n_changed"]==0 else ("DIFFERS" if r["ran"] else "WILL-NOT-RUN")
    print(f"{flag:14s} {r['label']}")
