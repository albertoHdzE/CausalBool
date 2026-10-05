"""screen_s6_report.py -- identification screen, step 6: table.md and VERDICT.md.

Reads the four results files of steps 2-5 and writes
results/screen_identification/{table.md, VERDICT.md, figures/*.png}.  Every
number in both documents is computed here from those files; the verdict is
applied mechanically as PROTOCOL sec.4 defines it.

A competitor "answers a class at n = 200" (gate H2) only if, on every question
of that class at n = 200, it returned status ok, took under 1 s (median of 3),
and its answer was verified: fixed points and attractors state by state with
causalbool.step and with counts agreeing across the tools that answered;
reachability agreeing with the Z3 bounded-model-checking cross-check; S3a
counts agreeing across all three arms.

Usage: venv/bin/python index-deconvolution/experiments/screen_s6_report.py
"""

from __future__ import annotations

import json
import statistics

from screen_common import RES

S1 = json.loads((RES / "s1_full_table.json").read_text())
S2 = json.loads((RES / "s2_queries.json").read_text())
S3A = json.loads((RES / "s3a_one_step.json").read_text())
S3B = json.loads((RES / "s3b_multi_step.json").read_text())
for name, d in (("S1", S1), ("S2", S2), ("S3a", S3A), ("S3b", S3B)):
    if d.get("partial") or not d.get("rows"):
        raise SystemExit(f"{name} results are partial or empty: refusing to report")


def fmt_s(x):
    if x is None:
        return "—"
    if x < 1e-3:
        return f"{x * 1e6:.0f} µs"
    if x < 1:
        return f"{x * 1e3:.1f} ms"
    return f"{x:.2f} s"


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


# ---------------------------------------------------------------------------
# S1 / H3
# ---------------------------------------------------------------------------

def s1_section():
    L = ["## S1 — full table (n ≤ 20): `deconvolve` against BoolNet", "",
         f"{len(S1['rows'])} networks. Time is the median of {S1['settings']['reps']} runs of the "
         f"reconstruction call alone; limit {S1['settings']['limit_s']} s per run. BoolNet was given "
         "maxK = the true maximum in-degree (an oracle advantage). Exact = `verify_forward` "
         "rebuilds the whole repertoire.", "",
         "| network | n | max in-deg | `deconvolve` | exact | BoolNet reveal | exact | BoolNet best-fit | exact |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in S1["rows"]:
        cells = []
        for k in ("deconvolve", "boolnet_reveal", "boolnet_bestfit"):
            c = r[k]
            t = fmt_s(c.get("median_s")) if not str(c.get("status", "ok")).startswith(("timeout", "error")) \
                else c["status"].split(":")[0]
            if c.get("status") not in (None, "ok") and not str(c["status"]).startswith("timeout"):
                t = c["status"][:40]
            cells += [t, "yes" if c.get("exact") else "no"]
        L.append(f"| {r['id']} | {r['n']} | {r['max_indegree']} | " + " | ".join(cells) + " |")
    h = S1["h3"]
    L += ["", f"**H3.** `deconvolve` exact on {sum(r['deconvolve']['exact'] for r in S1['rows'])}/"
          f"{len(S1['rows'])}; at least as fast as the best exact competitor on "
          f"{h['ours_at_least_as_fast']}/{h['denominator']}."]
    ratios = [x["best_competitor_s"] / x["ours_s"] for x in h["per_network"]
              if x["best_competitor_s"] and x["ours_s"]]
    if ratios:
        L.append(f"Where both were exact, the best competitor took {min(ratios):.1f}× to "
                 f"{max(ratios):.1f}× the time of `deconvolve` (median {med(ratios):.1f}×, "
                 f"{len(ratios)} networks).")
    return L


# ---------------------------------------------------------------------------
# S3a
# ---------------------------------------------------------------------------

def s3a_section():
    L = ["## S3a — one-step causal questions", "",
         "Questions from the owner's task generator (T1 = 1 node, T2 = 4, T3 = 8); 5 per (n, task). "
         "Median of 3 runs; 60 s limit. Answer size in bits: ours and Z3 = assignments × support; "
         "CUDD = nodes × (⌈log₂ n⌉ + 2⌈log₂ nodes⌉).", "",
         f"Guards: {json.dumps(S3A['guards'])}", "",
         "| n | task | ours median / max | CUDD median / max | Z3 median / max | ours bits | CUDD bits (nodes) | support | assignments |",
         "|---|---|---|---|---|---|---|---|---|"]
    for a in S3A["aggregate"]:
        L.append(f"| {a['n']} | {a['task'][:2]} | {fmt_s(a['ours_median_s'])} / {fmt_s(a['ours_max_s'])} | "
                 f"{fmt_s(a['bdd_median_s'])} / {fmt_s(a['bdd_max_s'])} | "
                 f"{fmt_s(a['z3_median_s'])} / {fmt_s(a['z3_max_s'])} | {a['ours_median_answer_bits']:.0f} | "
                 f"{a['bdd_median_answer_bits']:.0f} ({a['bdd_median_nodes']:.0f}) | "
                 f"{a['median_support']:.0f} | {a['median_assignments']:.0f} |")
    return L


def s3a_gate():
    rows = [r for r in S3A["rows"] if r["n"] == 200]
    out = {}
    for arm in ("bdd", "z3"):
        out[arm] = bool(rows) and all(r[arm]["median_s"] < 1 and not r[arm]["timeout"]
                                      and r["counts_agree"] for r in rows)
    lead = {}
    for task in ("T1_single", "T2_small", "T3_medium"):
        rs = [r for r in rows if r["task"] == task]
        lead[task] = {"ours_faster_than_cudd": sum(r["ours"]["median_s"] < r["bdd"]["median_s"] for r in rs),
                      "ours_smaller_than_cudd": sum(r["ours"]["answer_bits"] < r["bdd"]["answer_bits"] for r in rs),
                      "of": len(rs)}
    return {"solved_by": [a for a, v in out.items() if v], "questions_at_200": len(rows), "lead": lead}


# ---------------------------------------------------------------------------
# S3b
# ---------------------------------------------------------------------------

def _cell_ok(c):
    return isinstance(c, dict) and c.get("status") == "ok"


def s3b_solved(q, tool, n=200):
    rows = [r for r in S3B["rows"] if r["n"] == n]
    if not rows:
        return False, 0
    if q == "reach":
        other = "pyboolnet" if tool == "z3_bmc" else "z3_bmc"
        cells = [(r["reach"][t][tool], r["reach"][t][other]) for r in rows for t in r["reach"]]
        ok = all(_cell_ok(c) and c["median_s"] < 1 and _cell_ok(z) and c["reachable"] == z["reachable"]
                 for c, z in cells)
        return ok, len(cells)
    ok = all(_cell_ok(r[q][tool]) and r[q][tool]["median_s"] < 1 and r[q][tool].get("verified")
             and r[q]["counts_agree"] and len(r[q]["counts"]) >= 2 for r in rows)
    return ok, len(rows)


def s3b_section():
    L = ["## S3b — multi-step questions", "",
         "All 55 networks. `fixed` = all fixed points; `attr` = all synchronous attractors; "
         "`reach` = does any state reach a 4-node target within 3 steps (T+ reachable by "
         "construction, T− its complement). Our only arm is `num_attractors`, **exhaustive over "
         "2ⁿ states**, for `attr`; no arm exists for `fixed` or `reach`, and no index-based arm "
         "exists for any S3b class.", "",
         f"Checks: {json.dumps({k: v for k, v in S3B['checks'].items() if k != 'verified_false'})}; "
         f"answers that failed state-by-state verification: {len(S3B['checks']['verified_false'])}.", ""]
    ns = sorted({r["n"] for r in S3B["rows"] if r["kind"] == "synthetic"})
    L += ["Slowest median time over the 5 synthetic networks at each n (— = no answer within 60 s):", "",
          "| class | tool | " + " | ".join(f"n={n}" for n in ns) + " | answered |",
          "|---|---|" + "---|" * len(ns) + "---|"]
    for q, tools in (("fixed", ("pyboolnet", "boolnet")), ("attr", ("ours", "pyboolnet", "boolnet")),
                     ("reach", ("pyboolnet", "z3_bmc"))):
        for tool in tools:
            if q == "reach":
                cells = [(r, r["reach"][t][tool]) for r in S3B["rows"] for t in r["reach"]]
            else:
                cells = [(r, r[q][tool]) for r in S3B["rows"]]
            by_n = []
            for n in ns:
                cs = [c for r, c in cells if r["n"] == n and r["kind"] == "synthetic"]
                ok = [c["median_s"] for c in cs if _cell_ok(c)]
                by_n.append(fmt_s(max(ok)) + ("" if len(ok) == len(cs) else f" ({len(cs) - len(ok)} none)")
                            if ok else "—")
            answered = sum(_cell_ok(c) for _, c in cells)
            label = tool + (" (exhaustive)" if tool == "ours" else "")
            L.append(f"| {q} | {label} | " + " | ".join(by_n) + f" | {answered}/{len(cells)} |")
    # PyBoolNet synchronous attractor completeness
    dis = [r for r in S3B["rows"] if _cell_ok(r["attr"]["pyboolnet"])
           and not r["attr"]["counts_agree"]]
    flag = {}
    for r in dis:
        f = str(r["attr"]["pyboolnet"].get("is_complete"))
        flag[f] = flag.get(f, 0) + 1
    L += ["", f"PyBoolNet's synchronous attractor count disagreed with the other tools on {len(dis)} "
          f"networks; its own completeness flag on those was {json.dumps(flag)}."]
    return L


# ---------------------------------------------------------------------------
# S2 / H1
# ---------------------------------------------------------------------------

def s2_section():
    L = ["## S2 — queries: random-sample identification against Q_LB", "",
         "Akutsu 2003 (strategic perturbations) has no released software and was replaced, per "
         "PROTOCOL §2, by Akutsu 1999 (random samples), solved by BoolNet's reconstructNetwork "
         "with maxK = k = 3. m = smallest number of uniform random state queries at which the "
         "recovered network is exact (`verify_forward`, or its symbolic twin above n = 15); "
         "lenient = first-listed solution exact, unique = exact and no gene ambiguous. "
         "Our arm: none exists.", "",
         f"Guards: {json.dumps(S2['guards'])}", "",
         "| n | Q_LB | 2×Q_LB | best-fit m lenient (median, range) | best-fit m unique | REVEAL m lenient | REVEAL m unique | best / Q_LB |",
         "|---|---|---|---|---|---|---|---|"]
    for n in sorted({r["n"] for r in S2["rows"]}):
        rs = [r for r in S2["rows"] if r["n"] == n]

        def col(meth, key):
            v = [r[f"boolnet_{meth}"][key] for r in rs]
            ok = [x for x in v if x is not None]
            miss = len(v) - len(ok)
            if not ok:
                return "—"
            s = f"{med(ok):.0f} ({min(ok)}–{max(ok)})"
            return s + (f", {miss} none" if miss else "")
        best = [min([x for x in (r["boolnet_bestfit"]["m_exact_lenient"], r["boolnet_reveal"]["m_exact_lenient"])
                     if x is not None], default=None) for r in rs]
        ratio = [b / r["Q_LB"] for b, r in zip(best, rs) if b is not None]
        L.append(f"| {n} | {rs[0]['Q_LB']} | {rs[0]['2xQ_LB']} | {col('bestfit', 'm_exact_lenient')} | "
                 f"{col('bestfit', 'm_exact_unique')} | {col('reveal', 'm_exact_lenient')} | "
                 f"{col('reveal', 'm_exact_unique')} | "
                 + (f"{min(ratio):.2f}–{max(ratio):.2f}" if ratio else "—") + " |")
    nm = sum(not r[f"boolnet_{m}"]["probes_monotone"] for r in S2["rows"] for m in ("bestfit", "reveal"))
    L += ["", f"Non-monotone probe sequences (exact at some m, inexact at a larger probed m): {nm}."]
    return L


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

def verdict():
    h1 = S2["h1"]
    h1_no_headroom = h1["no_headroom"]
    g3a = s3a_gate()
    classes = {"S3a one-step": (bool(g3a["solved_by"]), g3a["solved_by"], g3a["questions_at_200"])}
    for q in ("fixed", "attr", "reach"):
        # reach: Z3 bounded model checking was run as a cross-check, but Z3 is a
        # protocol competitor (S3a) and it answers this class; counting it is
        # the reading that can only REMOVE headroom, so it is the one applied.
        tools = ("pyboolnet", "boolnet") if q != "reach" else ("pyboolnet", "z3_bmc")
        solved = [t for t in tools if s3b_solved(q, t)[0]]
        classes[f"S3b {q}"] = (bool(solved), solved, s3b_solved(q, tools[0])[1])
    h2_no_headroom = all(v[0] for v in classes.values())
    our_arm = {"S2": "none exists", "S3a one-step": "index-based (exact_query_representation)",
               "S3b fixed": "none exists", "S3b attr": "exhaustive (num_attractors)",
               "S3b reach": "none exists"}
    headroom = ([] if h1_no_headroom else ["S2"]) + [c for c, v in classes.items() if not v[0]]
    if not headroom:
        v = "STOP"
    elif all(our_arm[h].startswith(("none", "exhaustive")) for h in headroom):
        v = "NARROW"
    else:
        v = "GO"
    return {"verdict": v, "h1": h1, "h1_no_headroom": h1_no_headroom, "classes": classes,
            "h2_no_headroom": h2_no_headroom, "headroom": headroom, "our_arm": our_arm,
            "s3a": g3a}


def figures():
    """Render the objects the gates read: every network's queries-to-exact
    against Q_LB (S2), and every question's time per arm (S3a, T3)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    blue, orange, aqua = "#2a78d6", "#eb6834", "#1baf7a"   # categorical slots 1-3
    (RES / "figures").mkdir(exist_ok=True)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    rs = S2["rows"]
    ns = sorted({r["n"] for r in rs})
    ax[0].plot(ns, [rs[[r["n"] for r in rs].index(n)]["Q_LB"] for n in ns], color="#555", lw=2, label="Q_LB")
    ax[0].plot(ns, [2 * rs[[r["n"] for r in rs].index(n)]["Q_LB"] for n in ns], color="#555", lw=2,
               ls="--", label="2 × Q_LB (H1 bar)")
    ax[0].scatter([r["n"] for r in rs], [r["boolnet_bestfit"]["m_exact_lenient"] for r in rs],
                  s=40, color=blue, edgecolor="white", lw=1.5, label="BoolNet best-fit, exact (lenient)", zorder=3)
    ax[0].scatter([r["n"] for r in rs], [r["boolnet_bestfit"]["m_exact_unique"] for r in rs],
                  s=40, marker="D", color=orange, edgecolor="white", lw=1.5, label="… exact and unique", zorder=2)
    ax[0].set_xscale("log"); ax[0].set_xticks(ns); ax[0].set_xticklabels(ns)
    ax[0].set_xlabel("n (nodes)"); ax[0].set_ylabel("random state queries to exact recovery")
    ax[0].set_title("S2: one point per network (5 per n)", fontsize=10)
    ax[0].legend(frameon=False, fontsize=8); ax[0].grid(alpha=.25)
    rows = [r for r in S3A["rows"] if r["task"] == "T3_medium"]
    for arm, c, lab in (("ours", blue, "ours (exact_query_representation)"), ("bdd", orange, "CUDD"),
                        ("z3", aqua, "Z3 all-SAT")):
        ax[1].scatter([r["n"] for r in rows], [r[arm]["median_s"] for r in rows], s=40, color=c,
                      edgecolor="white", lw=1.5, label=lab)
    ax[1].axhline(1.0, color="#555", ls="--", lw=1.5, label="1 s (H2 bar)")
    ax[1].set_xscale("log"); ax[1].set_yscale("log"); ax[1].set_xticks(ns); ax[1].set_xticklabels(ns)
    ax[1].set_xlabel("n (nodes)"); ax[1].set_ylabel("seconds per question (median of 3)")
    ax[1].set_title("S3a, 8-node questions: one point per question", fontsize=10)
    ax[1].legend(frameon=False, fontsize=8); ax[1].grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(RES / "figures" / "s2_s3a.png", dpi=150)


def main():
    figures()
    V = verdict()
    tv = S3B["tool_versions"]
    head = ["# Identification screen — results table", "",
            "Protocol: `PROTOCOL_screen_identification.md` (frozen at `dcc1d59e`). Generated by "
            "`experiments/screen_s6_report.py` from `s1_full_table.json`, `s2_queries.json`, "
            "`s3a_one_step.json`, `s3b_multi_step.json`. Corpus: `corpus/manifest.json`.", "",
            "Tools: " + ", ".join(f"{k} {v}" for k, v in tv.items() if v), ""]
    body = head + s1_section() + [""] + s2_section() + [""] + s3a_section() + [""] + s3b_section()
    (RES / "table.md").write_text("\n".join(body) + "\n", encoding="utf-8")

    L = ["# VERDICT — identification screen", "",
         f"**{V['verdict']}**, applied as PROTOCOL §4 defines it. Every number below is "
         "computed by `experiments/screen_s6_report.py`; the tables are in `table.md`.", "",
         "## Gates", ""]
    h1 = V["h1"]
    L.append(f"- **H1 (S2 headroom).** The best competitor needed at most 2 × Q_LB queries on "
             f"{h1['within_2xQ_LB']} networks at n ≥ 50. "
             + ("No headroom." if V["h1_no_headroom"] else "Headroom exists: identification by queries is not near-optimal.")
             + " Our arm: none exists.")
    for c, (solved, by, nq) in V["classes"].items():
        L.append(f"- **H2 ({c}).** " + (f"Answered, verified and under 1 s on all {nq} questions at n = 200 by "
                                        f"{', '.join(by)}: no headroom." if solved else
                                        f"No competitor answered all {nq} questions at n = 200 under 1 s "
                                        "with a verified answer: headroom.")
                 + f" Our arm: {V['our_arm'][c]}.")
    lead = V["s3a"]["lead"]
    L.append("  - S3a, time and size against CUDD at n = 200 (H2 moves the comparison there): "
             + "; ".join(f"{t[:2]}: ours faster on {x['ours_faster_than_cudd']}/{x['of']}, smaller on "
                         f"{x['ours_smaller_than_cudd']}/{x['of']}" for t, x in lead.items()) + ".")
    h3 = S1["h3"]
    L.append(f"- **H3 (our standing in S1).** `deconvolve` was at least as fast as the best exact "
             f"competitor on {h3['ours_at_least_as_fast']}/{h3['denominator']} networks at n ≤ 20.")
    L += ["", "## Verdict rule applied", "",
          f"- H1 shows no headroom: **{V['h1_no_headroom']}**. H2 shows no headroom (all classes): "
          f"**{V['h2_no_headroom']}**.",
          f"- Headroom found in: **{', '.join(V['headroom']) or 'nowhere'}**.",
          "- Our arm in each of those: " + ("; ".join(f"{h} → {V['our_arm'][h]}" for h in V['headroom']) or "—") + ".",
          "- STOP needs no headroom under H1 and H2; NARROW needs headroom only where our arms are "
          "exhaustive or do not exist; GO needs headroom where an existing arm already leads.",
          f"- Result: **{V['verdict']}**."]
    (RES / "VERDICT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (RES / "verdict.json").write_text(json.dumps(V, indent=2, default=str))
    print("verdict:", V["verdict"], "| headroom:", V["headroom"])


if __name__ == "__main__":
    main()
