"""Re-derive the repaired M gate from R_adapter raw rows plus the per-program terms.

Adapter medians come from the 90 raw rows (stdout hashes checked); N, point and
conservative ratios and the equal-family aggregate are recomputed. T0, O_matched
and N_kernel are taken from RECALIBRATED_PREDICTION.json: the lead already
reproduced them from the parent's raw rows (lead_third_round_review_20260925).
"""
import hashlib, json, math, statistics
from collections import defaultdict
from pathlib import Path
RUN = Path("results/phase2_structural_encoding/third_round_20260925_resume")
pred = json.loads((RUN / "RECALIBRATED_PREDICTION.json").read_text())
runs = defaultdict(list)
bad = 0
for line in (RUN / "stages/R_adapter/rows.jsonl").read_text().splitlines():
    r = json.loads(line)
    raw = (RUN / "stages/R_adapter/raw" / f"{r['raw_index']:05d}.stdout").read_bytes()
    bad += hashlib.sha256(raw).hexdigest() != r["stdout_sha256"] or r["exit_code"] != 0
    runs[str(r["seed"])].append(r["adapter_seconds"])
fam = defaultdict(lambda: ([], []))
diff = 0.0
for seed, p in pred["programs"].items():
    a = statistics.median(runs[seed])
    diff = max(diff, abs(a - p["adapter_repaired_median"]))
    N = p["N_kernel"] + max(p["adapter_old_median"], a)
    fam[p["family"]][0].append(math.log((p["T0"] - p["O_matched"] + N) / p["T0"]))
    fam[p["family"]][1].append(math.log((p["T0"] - p["O_matched"] + 1.5 * N) / p["T0"]))
agg = lambda i: math.exp(statistics.fmean(statistics.fmean(v[i]) for v in fam.values()))
out = {"adapter_rows": sum(map(len, runs.values())), "bad_rows": int(bad),
       "programs": len(runs), "max_adapter_median_diff": diff,
       "point": agg(0), "conservative": agg(1),
       "reported": [pred["corrected_point"], pred["corrected_conservative"]],
       "families": len(fam)}
print(json.dumps(out, indent=1))
(Path(__file__).parent / "RECOMPUTE_M.json").write_text(json.dumps(out, indent=1) + "\n")
