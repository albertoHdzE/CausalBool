"""screen_s3a_one_step.py -- identification screen, step 3: S3a and gate H2 (S3a).

PROTOCOL sec.2 row S3a: the model is known; the question is which assignments
of which inputs make chosen nodes take chosen values at the next step.

Questions: exactly the owner's task generator, ``build_task_specs`` of
papers/method/code/scalability_resource_envelope (T1: 1 node, T2: 4 nodes,
T3: 8 nodes; targets are the successor bits of a pinned witness state), on
every synthetic network of the frozen corpus (n = 10 .. 200, 5 seeds).
Biological models are not posed here: our arm accepts the eleven named
families only, and the biological models are look-up tables.

Arms, each answering the SAME question in full (every satisfying assignment):
  ours  exact_query_representation (index-based; answer = the list of
        assignments over the support union)
  bdd   dd.cudd (CUDD), conjunction of the query nodes' functions, read from
        the frozen .bnet; answer = the diagram
  z3    Z3, all satisfying assignments projected on the variables of the
        query formula (blocking clauses); answer = the list of assignments

Exactness: the three counts of satisfying assignments over the support must
agree, and every sampled row of our answer is checked by causalbool.step with
the free coordinates drawn at random.  The dict adapter is checked against
causalbool.step first (denominator printed).

Time: median of 3 runs, 60 s limit per question (a run over the limit is
recorded as a timeout and not repeated).  Answer size: ours and z3 in bits
(assignments x support size); bdd in diagram nodes, and also in bits at
ceil(log2 n) + 2 pointers of ceil(log2 nodes) per node, so the three are
comparable in one unit.

Usage: venv/bin/python index-deconvolution/experiments/screen_s3a_one_step.py [--quiet]
"""

from __future__ import annotations

import math
import random
import statistics
import time

from screen_common import (CORPUS, RES, canonical_names, load_entry, load_manifest,
                           log, to_query_network, tool_versions, write_json)

import scalability_resource_envelope as sre
from causalbool import step

LIMIT_S = 60.0
REPS = 3


def _rules(bnet_text: str) -> list[str]:
    return [ln.split(",", 1)[1].strip() for ln in bnet_text.splitlines()[1:]]


def timed(fn):
    times, out = [], None
    for _ in range(REPS):
        t0 = time.perf_counter()
        out = fn()
        times.append(time.perf_counter() - t0)
        if times[-1] > LIMIT_S:
            return times, out, True
    return times, out, False


def bdd_answer(rules, names, nodes0, bits):
    """Fresh CUDD manager per run (declaration untimed), so that no run is
    answered from the computed-table cache of a previous one."""
    from dd.cudd import BDD
    times, m, u, to = [], None, None, False
    for _ in range(REPS):
        m = BDD()
        m.declare(*names)
        t0 = time.perf_counter()
        u = _bdd_build(m, rules, nodes0, bits)
        times.append(time.perf_counter() - t0)
        if times[-1] > LIMIT_S:
            to = True
            break
    return times, m, u, to


def _bdd_build(m, rules, nodes0, bits):
        u = m.true
        for k, b in zip(nodes0, bits):
            f = m.add_expr(rules[k] if rules[k] not in ("0", "1")
                           else ("TRUE" if rules[k] == "1" else "FALSE"))
            u = u & (f if b else ~f)
        return u


def z3_answer(rules, names, nodes0, bits):
    import z3

    def run():
        env = {nm: z3.Bool(nm) for nm in names}
        cons = []
        used = set()
        for k, b in zip(nodes0, bits):
            r = rules[k]
            e = (z3.BoolVal(r == "1") if r in ("0", "1")
                 else eval(r.replace("!", "~"), {"__builtins__": {}}, env))  # noqa: S307
            used.update(t for t in names if t in r.replace("(", " ").replace(")", " ")
                        .replace("!", " ").replace("&", " ").replace("|", " ").split())
            cons.append(e if b else z3.Not(e))
        vs = [env[t] for t in sorted(used)]
        s = z3.Solver()
        s.set("timeout", int(LIMIT_S * 1000))
        s.add(*cons)
        count = 0
        t0 = time.perf_counter()
        while s.check() == z3.sat:
            mdl = s.model()
            count += 1
            s.add(z3.Or([v != mdl.eval(v, model_completion=True) for v in vs]))
            if time.perf_counter() - t0 > LIMIT_S:
                return {"count": None, "support": len(vs), "timeout": True}
        return {"count": count, "support": len(vs), "timeout": False}
    return run


def main() -> None:
    manifest = load_manifest()
    entries = [e for e in manifest["entries"] if e["kind"] == "synthetic"]
    rows, adapter_ok, adapter_total, sample_ok, sample_total = [], 0, 0, 0, 0
    for e in entries:
        net = load_entry(e)
        q = to_query_network(net)
        names = canonical_names(net.n)
        rules = _rules((CORPUS / e["bnet"]).read_text())
        rng = random.Random(f"s3a:{e['id']}")
        for _ in range(64):                       # adapter guard
            s = [rng.randint(0, 1) for _ in range(net.n)]
            adapter_total += 1
            adapter_ok += sre.network_update(s, q) == step(net, s)
        seed_idx = int(e["id"].rsplit("_s", 1)[1])
        for spec in sre.build_task_specs(q, seed_idx):
            nodes1, bits = spec["query_nodes"], spec["target_bits"]
            nodes0 = [k - 1 for k in nodes1]
            row = {"id": e["id"], "n": net.n, "task": spec["task"], "query_nodes": nodes1,
                   "target_bits": bits}
            # ours
            t, ans, to = timed(lambda: sre.exact_query_representation(q, nodes1, bits))
            S = ans["support_union"]
            row["ours"] = {"times_s": t, "median_s": statistics.median(t), "timeout": to,
                           "support_size": ans["support_size"],
                           "assignments": ans["support_assignments_count"],
                           "answer_bits": ans["support_assignments_count"] * ans["support_size"]}
            for srow in ans["support_assignments_sample"]:  # forward check of rows
                st = [rng.randint(0, 1) for _ in range(net.n)]
                for c, v in zip(S, srow):
                    st[c - 1] = v
                nxt = step(net, st)
                sample_total += 1
                sample_ok += all(nxt[k] == b for k, b in zip(nodes0, bits))
            # bdd
            t, m, u, to = bdd_answer(rules, names, nodes0, bits)
            supp = m.support(u)
            cnt_n = m.count(u, nvars=net.n)
            cnt_S = round(cnt_n / 2 ** (net.n - len(S))) if set(supp) <= {names[c - 1] for c in S} else None
            nodes = len(u)
            bits_per_node = math.ceil(math.log2(max(net.n, 2))) + 2 * math.ceil(math.log2(max(nodes, 2)))
            row["bdd"] = {"times_s": t, "median_s": statistics.median(t), "timeout": to,
                          "support_size": len(supp), "assignments_over_S": cnt_S,
                          "diagram_nodes": nodes, "answer_bits": nodes * bits_per_node}
            # z3
            t, z, to = timed(z3_answer(rules, names, nodes0, bits))
            row["z3"] = {"times_s": t, "median_s": statistics.median(t),
                         "timeout": to or z["timeout"], "support_size": z["support"],
                         "assignments": z["count"],
                         "answer_bits": None if z["count"] is None else z["count"] * z["support"]}
            row["counts_agree"] = (row["ours"]["assignments"] == row["bdd"]["assignments_over_S"]
                                   == row["z3"]["assignments"])
            rows.append(row)
            log(e["id"], spec["task"], {a: (round(row[a]["median_s"], 5), row[a].get("answer_bits"))
                                       for a in ("ours", "bdd", "z3")}, row["counts_agree"])

    # aggregate per (n, task) and H2 for S3a
    agg = []
    for n in sorted({r["n"] for r in rows}):
        for task in ("T1_single", "T2_small", "T3_medium"):
            rs = [r for r in rows if r["n"] == n and r["task"] == task]
            a = {"n": n, "task": task, "questions": len(rs)}
            for arm in ("ours", "bdd", "z3"):
                a[f"{arm}_median_s"] = statistics.median(r[arm]["median_s"] for r in rs)
                a[f"{arm}_max_s"] = max(r[arm]["median_s"] for r in rs)
                a[f"{arm}_median_answer_bits"] = statistics.median(
                    r[arm]["answer_bits"] for r in rs if r[arm]["answer_bits"] is not None)
            a["bdd_median_nodes"] = statistics.median(r["bdd"]["diagram_nodes"] for r in rs)
            a["median_support"] = statistics.median(r["ours"]["support_size"] for r in rs)
            a["median_assignments"] = statistics.median(r["ours"]["assignments"] for r in rs)
            agg.append(a)
    at200 = [r for r in rows if r["n"] == 200]
    h2 = {arm: {"max_s_at_n200": max(r[arm]["median_s"] for r in at200),
                "all_under_1s_at_n200": all(r[arm]["median_s"] < 1.0 and not r[arm]["timeout"]
                                            for r in at200), "questions": len(at200)}
          for arm in ("ours", "bdd", "z3")}
    h2["competitor_solves_class"] = h2["bdd"]["all_under_1s_at_n200"] or h2["z3"]["all_under_1s_at_n200"]
    out = {"protocol": "PROTOCOL_screen_identification.md S3a, H2",
           "script": "index-deconvolution/experiments/screen_s3a_one_step.py",
           "tool_versions": tool_versions(),
           "guards": {"adapter_matches_causalbool_step": f"{adapter_ok}/{adapter_total}",
                      "sampled_answer_rows_satisfy_query": f"{sample_ok}/{sample_total}",
                      "counts_agree_all_three": f"{sum(r['counts_agree'] for r in rows)}/{len(rows)}"},
           "aggregate": agg, "h2_s3a": h2, "rows": rows}
    write_json(RES / "s3a_one_step.json", out)
    print("guards:", out["guards"])
    print("H2(S3a):", {k: v for k, v in h2.items()})


if __name__ == "__main__":
    main()
