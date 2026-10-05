"""Presentation only: for every FULL lossy non-F3 row, print the fibres and the induced maps
G_q (via the frozen production owner). Changes no measured row."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import study as S
rows = [json.loads(l) for l in open(os.path.join(HERE, "results_d.jsonl"))]
out = []
models = {}
for r in rows:
    if r["display"] != "FULL" or r["candidate"]["family"] == "F3":
        continue
    m = models.setdefault(r["model"], S.Model(r["model"]))
    c = dict(r["candidate"], id=r["cand_id"])
    vals = [S.alpha_value(c, x, m.n) for x in range(m.N)]
    canon = S.canonical_partition(vals)
    macro = {}
    for x, v in enumerate(vals):
        macro.setdefault(canon[x], {"value": v, "size": 0, "min_x": x})["size"] += 1
    Q = S.track_d_q(m.n)
    maps = {S.q_name(q): S.induced_map(canon, [canon[y] for y in m.q_table(q, r["tau"])])[0] for q in Q}
    distinct = {}
    for name, G in maps.items():
        distinct.setdefault(json.dumps(G, sort_keys=True), []).append(name)
    out.append({"row": r["row"], "model": r["model"], "tau": r["tau"], "candidate": r["candidate"],
                "macro_states": macro, "G_id": maps["id"], "distinct_maps": [{"G": json.loads(k), "q": v} for k, v in distinct.items()]})
json.dump(out, open(os.path.join(HERE, "nonf3_full_maps.json"), "w"), indent=1)
for o in out:
    print(o["row"], o["model"], o["tau"], {k: (v["value"], v["size"]) for k, v in o["macro_states"].items()},
          "G_id", o["G_id"], "distinct G_q:", len(o["distinct_maps"]))
