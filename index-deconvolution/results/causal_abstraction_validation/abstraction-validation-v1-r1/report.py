"""Presentation only: summarise results_d.jsonl into report_tables.json and report_tables.md.
Reads results; computes no scientific field."""
import json, os
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, "results_d.jsonl"))]
TAUS = [1, 2, 4, 8, 16]
def cname(c):
    f = c["family"]
    if f == "F1": return f"F1 {c['g']} ({c['w']},{c['o']})"
    if f == "F2": return f"F2 {c['g']}"
    if f == "F3": return f"F3 [{c['a']},{c['a']+c['len']}) of ({c['w']},{c['o']})"
    if f == "F4": return f"F4 {c['g']}o{c['g']} ({c['w']},{c['o']}) o2={c['o2']}"
    return f"C {c['g']}"
md = []
md.append("### Display label per model and tau (rows)\n")
labs = sorted({r["display"] for r in rows})
md.append("| model | tau | " + " | ".join(labs) + " |\n|" + "---|" * (len(labs) + 2))
tab = defaultdict(Counter)
for r in rows: tab[(r["model"], r["tau"])][r["display"]] += 1
for (m, t), c in sorted(tab.items(), key=lambda k: (k[0][0], TAUS.index(k[0][1]))):
    md.append(f"| {m} | {t} | " + " | ".join(str(c.get(l, 0)) for l in labs) + " |")
md.append("\n### FULL non-control candidates (lossy), per row\n")
md.append("| row | model | tau | candidate | family | |alpha(X)| | fibre min-max |\n|---|---|---|---|---|---|---|")
full = [r for r in rows if r["display"] == "FULL"]
for r in full:
    md.append(f"| {r['row']} | {r['model']} | {r['tau']} | {cname(r['candidate'])} | {r['candidate']['family']} | "
              f"{r['E1']['n_macro']} | {r['E1']['fibre_min']}-{r['E1']['fibre_max']} |")
md.append("\n### E6 ambiguity: FULL non-control rows per (model, tau), raw and distinct partitions\n")
md.append("| model | tau | FULL raw | distinct partitions | of which non-F3 raw |\n|---|---|---|---|---|")
for m in ["M1", "M2", "M3", "M4"]:
    for t in TAUS:
        f = [r for r in full if r["model"] == m and r["tau"] == t]
        md.append(f"| {m} | {t} | {len(f)} | {len({r['partition_sha'] for r in f})} | "
                  f"{sum(r['candidate']['family'] != 'F3' for r in f)} |")
md.append("\n### Coarse-hypothesis labels (separate column; counts of rows)\n")
md.append("| model | scheme | " + " | ".join(["COARSE-DISAGREE", "COARSE-STRUCT-FAIL", "COARSE-INCOMPLETE", "COARSE-NO-HOLDOUT", "COARSE-HOLDS"]) + " |\n|---|---|---|---|---|---|---|")
co = defaultdict(Counter)
for r in rows:
    for s, v in r["coarse"].items(): co[(r["model"], s)][v["label"]] += 1
for (m, s), c in sorted(co.items()):
    md.append(f"| {m} | {s} | " + " | ".join(str(c.get(l, 0)) for l in ["COARSE-DISAGREE", "COARSE-STRUCT-FAIL", "COARSE-INCOMPLETE", "COARSE-NO-HOLDOUT", "COARSE-HOLDS"]) + " |")
md.append("\n### COARSE-HOLDS rows\n")
md.append("| row | model | tau | candidate | scheme | classes | evaluable micro pairs |\n|---|---|---|---|---|---|---|")
for r in rows:
    for s, v in r["coarse"].items():
        if v["label"] == "COARSE-HOLDS":
            md.append(f"| {r['row']} | {r['model']} | {r['tau']} | {cname(r['candidate'])} | {s} | {v['n_classes']} | {v['pairs_evaluable']} |")
md.append("\n### Restriction E8 among RESTRICTED rows: |Q'|/|Q| distribution per model\n")
md.append("| model | RESTRICTED rows | min |Q'| | median |Q'| | max |Q'| | |Q| |\n|---|---|---|---|---|---|")
for m in ["M1", "M2", "M3", "M4"]:
    rr = sorted(len(r["Q_prime"]) for r in rows if r["model"] == m and r["status"] == "RESTRICTED")
    if rr:
        md.append(f"| {m} | {len(rr)} | {rr[0]} | {rr[len(rr)//2]} | {rr[-1]} | {rows[[r['model'] for r in rows].index(m)]['n_Q']} |")
summary = {"rows": len(rows), "display": dict(Counter(r["display"] for r in rows)),
           "status": dict(Counter(r["status"] for r in rows)),
           "full_noncontrol": [{"row": r["row"], "model": r["model"], "tau": r["tau"], "candidate": cname(r["candidate"]),
                                "family": r["candidate"]["family"], "n_macro": r["E1"]["n_macro"]} for r in full],
           "full_lossy_M3_M4": {"F3": sum(r["candidate"]["family"] == "F3" for r in full if r["model"] in ("M3", "M4")),
                                "non_F3": sum(r["candidate"]["family"] != "F3" for r in full if r["model"] in ("M3", "M4"))}}
json.dump(summary, open(os.path.join(HERE, "report_tables.json"), "w"), indent=1)
open(os.path.join(HERE, "report_tables.md"), "w").write("\n".join(md) + "\n")
print(json.dumps({k: summary[k] for k in ("display", "status", "full_lossy_M3_M4")}))
