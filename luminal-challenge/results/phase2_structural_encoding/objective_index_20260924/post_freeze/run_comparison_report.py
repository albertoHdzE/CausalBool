"""POST-FREEZE WRAPPER (disclosed deviation; not frozen research source).

The frozen ``objective_index_report.comparison`` crashed in its descriptive
absolute-times table: the reused owner ``optimization_analysis.absolute_times``
summarises ``attempted_queries`` whenever a record has ``aggregate``, and A4
records have ``aggregate`` but no ``attempted_queries`` (empty median). This
wrapper runs the frozen ``comparison()`` byte-for-byte unchanged, substituting
for the duration of the call ONLY that helper, with one guard: an empty
``attempted_queries`` list is omitted instead of summarised. Every other number,
including every primary estimand and interval, comes from frozen code.
"""
import collections, statistics, sys
from pathlib import Path
from research import optimization_analysis as oa, objective_index_report as rep, run_structural_experiments as rse

def guarded_absolute_times(rows, arm, budget):
    selected = [r for r in rows if r["arm"] == arm and r["budget_seconds"] == budget and not r["failed_row"]]
    if not selected:
        return {"rows": 0}
    def summary(values):
        values = sorted(values)
        return {"median": statistics.median(values), "p95": rse.percentile(values, 0.95), "max": values[-1]}
    out = {"rows": len(selected),
           "compile_seconds": summary([r["result"]["compile_seconds"] for r in selected]),
           "process_seconds": summary([r["process_seconds"] for r in selected]),
           "peak_rss_bytes_max": max(r["result"].get("peak_rss_bytes") or 0 for r in selected)}
    over = [r["result"].get("overshoot_seconds") for r in selected if r["result"].get("overshoot_seconds") is not None]
    if over:
        out["overshoot_seconds"] = summary(over)
    opt = [r["result"].get("optimisation") or {} for r in selected]
    if any("aggregate" in o for o in opt):
        out["nodes"] = summary([o["aggregate"]["nodes"] for o in opt if "aggregate" in o])
        attempted = [o["attempted_queries"] for o in opt if "attempted_queries" in o]
        if attempted:  # the ONLY change from the owner
            out["attempted_queries"] = summary(attempted)
    out["stopped_because"] = dict(collections.Counter(o.get("stopped_because") for o in opt))
    return out

oa.absolute_times = guarded_absolute_times
payload = rep.comparison(Path(sys.argv[1]).resolve())
print(payload["primary"]["claim_text"])
