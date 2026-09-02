import os, sys, json, subprocess, hashlib
sys.path.insert(0,'/tmp'); 
exec(open('/tmp/q1_sweep.py').read().split('JOBS = []')[0])

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
