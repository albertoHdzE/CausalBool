"""Independent audit oracle for abstraction-validation-v1-r1 (declared validation exception).

Written separately from study.py / run.py and from the production checker in
deconvolution.py, none of which is imported. Shared inputs, disclosed: the frozen
fixtures.json (audit row list, candidate ids are re-derived and cross-checked), the
results files under audit, and for M4 only the model owners bnet.parse_bnet and
causalbool.repertoire (one-step table of the .bnet file). M1-M3 one-step maps and
all interventions (including knockouts, as "bit j of the next state := c") are
computed here from their definitions.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, *[".."] * 4))
TAUS = [1, 2, 4, 8, 16]


# ---------------------------------------------------------------- models from definitions

def eca_step(rule, n):
    def f(x):
        y = 0
        for i in range(n):
            l, c, r = (x >> ((i - 1) % n)) & 1, (x >> i) & 1, (x >> ((i + 1) % n)) & 1
            y |= ((rule >> (4 * l + 2 * c + r)) & 1) << i
        return y
    return [f(x) for x in range(2 ** n)]


def m4_step():
    sys.path.insert(0, os.path.join(ROOT, "index-deconvolution", "src"))
    from bnet import parse_bnet
    from causalbool import repertoire
    net, _ = parse_bnet(os.path.join(ROOT, "index-deconvolution/results/screen_identification/corpus/bio/egfr_signaling.bnet"))
    return [sum(v << k for k, v in enumerate(row)) for row in repertoire(net)]


def one_step(model):
    return {"M1": lambda: eca_step(150, 8), "M2": lambda: [(x + 1) % 256 for x in range(256)],
            "M3": lambda: eca_step(30, 8), "M4": m4_step}[model]()


def iterate(T, t):
    res = []
    for x in range(len(T)):
        y = x
        for _ in range(t):
            y = T[y]
        res.append(y)
    return res


def interventions(n):
    out = [("id", None, None)]
    for j in range(n):
        out += [("reset", j, 0), ("reset", j, 1)]
    out += [("flip", j, None) for j in range(n)]
    for j in range(n):
        out += [("knockout", j, 0), ("knockout", j, 1)]
    return out + [("tick", None, None)]


def intervened(T, n, q, tau):
    op, j, c = q
    N = 2 ** n
    if op == "id":
        return iterate(T, tau)
    if op == "tick":
        return iterate(T, tau + 1)
    if op == "knockout":
        K = [(T[x] | (1 << j)) if c else (T[x] & ~(1 << j)) for x in range(N)]
        return iterate(K, tau)
    Ft = iterate(T, tau)
    if op == "flip":
        return [Ft[x ^ (1 << j)] for x in range(N)]
    return [Ft[(x | (1 << j)) if c else (x & ~(1 << j))] for x in range(N)]


# ---------------------------------------------------------------- candidates

def blocks(w, o, n):
    b = [] if o == 0 else [(0, o)]
    for s in range(o, n, w):
        b.append((s, min(s + w, n) - s))
    return b


def bits(x, s, ln):
    return [(x >> (s + i)) & 1 for i in range(ln)]


def agg(g, v):
    return {"val": lambda: int("".join(map(str, reversed(v))) or "0", 2), "par": lambda: sum(v) % 2,
            "cnt": lambda: sum(v), "or": lambda: max(v), "and": lambda: min(v)}[g]()


def family(n):
    wo = [(2, 0), (2, 1), (3, 0), (3, 1), (3, 2), (4, 0), (4, 1), (4, 2), (4, 3)]
    c = [("F1", w, o, g) for w, o in wo for g in ("val", "par", "cnt", "or", "and")]
    c += [("F2", g) for g in ("par", "cnt", "or", "and")]
    c += [("F3", w, o, k) for w, o in wo for k in range(len(blocks(w, o, n)))]
    c += [("F4", w, o, g, o2) for w, o in wo for g in ("par", "or", "and") for o2 in (0, 1)]
    return c + [("C", "identity"), ("C", "constant")]


def macro(c, x, n):
    if c[0] == "F1":
        return tuple(agg(c[3], bits(x, s, ln)) for s, ln in blocks(c[1], c[2], n))
    if c[0] == "F2":
        return agg(c[1], bits(x, 0, n))
    if c[0] == "F3":
        s, ln = blocks(c[1], c[2], n)[c[3]]
        return agg("val", bits(x, s, ln))
    if c[0] == "F4":
        y = [agg(c[3], bits(x, s, ln)) for s, ln in blocks(c[1], c[2], n)]
        return tuple(agg(c[3], y[s:s + ln]) for s, ln in blocks(2, c[4], len(y)))
    return x if c[1] == "identity" else 0


def block_of(c, j, n):
    bl = blocks(c[1], c[2], n)
    for k, (s, ln) in enumerate(bl):
        if s <= j < s + ln:
            return k, j - s, bl


# ---------------------------------------------------------------- fibre logic (independent)

def labels(vals):
    lab, out = {}, []
    for v in vals:
        if v not in lab:
            lab[v] = len(lab)
        out.append(lab[v])
    return out


def exists_and_witness(lab, img):
    fib = {}
    for x, a in enumerate(lab):
        fib.setdefault(a, []).append(x)
    mixed = {a for a, xs in fib.items() if len({img[x] for x in xs}) > 1}
    if not mixed:
        return {a: img[xs[0]] for a, xs in fib.items()}, None
    for x in range(len(lab)):
        if lab[x] in mixed:
            for y in fib[lab[x]]:
                if y > x and img[y] != img[x]:
                    return None, [x, y]


def coarse_key(scheme, c, q, n):
    op, j, v = q
    if op in ("id", "tick"):
        return (op,)
    if scheme == "H-OUT":
        k, p, _ = block_of(c, j, n)
        return ("id",) if k != c[3] else (op, k, p, v)
    if c[0] in ("F2",):
        return (op, 0, v)
    k, p, _ = block_of(c, j, n)
    if c[0] == "F4":
        bl = blocks(c[1], c[2], n)
        for k2, (s, ln) in enumerate(blocks(2, c[4], len(bl))):
            if s <= k < s + ln:
                return (op, k2, v)
    return (op, k, v)


def coarse(scheme, c, Q, n, G, lab):
    N = 2 ** n
    groups = {}
    for i, q in enumerate(Q):
        groups.setdefault(coarse_key(scheme, c, q, n), []).append(i)
    cls = sorted(groups.values())
    size = {}
    for a in lab:
        size[a] = size.get(a, 0) + 1
    res = {"DISAGREE": 0, "REP-NOEXIST": 0, "MEMBER-NOEXIST": 0, "MISSING": 0}
    tot = {"i": 0, "s": 0, "e": 0, "mac": 0, "mic": 0}
    rows = []
    for m in cls:
        r = m[0]
        tot["i"] += N * (len(m) - 1)
        st = "OK" if G[r] is not None else "REP-NOEXIST"
        res["REP-NOEXIST"] += st == "REP-NOEXIST"
        mem = []
        for q in m[1:]:
            tot["s"] += N
            own = "PASS" if G[q] is not None else "FAIL"
            base = {"q": q, "own_e3": own, "macro_disagreements": None, "micro_mismatches": None,
                    "witness_macro": None}
            if st == "REP-NOEXIST":
                mem.append({**base, "outcome": "NOT-EVALUABLE", "reason": "representative has no induced map"})
            elif G[q] is None:
                res["MEMBER-NOEXIST"] += 1
                mem.append({**base, "outcome": "MEMBER-NOEXIST", "reason": "member has no induced map"})
            else:
                tot["e"] += N
                diff = [a for a in sorted(G[r]) if G[r][a] != G[q][a]]
                res["DISAGREE"] += bool(diff)
                tot["mac"] += len(diff)
                tot["mic"] += sum(size[a] for a in diff)
                mem.append({**base, "outcome": "DISAGREE" if diff else "AGREE", "reason": None,
                            "macro_disagreements": len(diff), "micro_mismatches": sum(size[a] for a in diff),
                            "witness_macro": diff[0] if diff else None})
        rows.append({"rep": r, "rep_state": st, "members": mem})
    if res["DISAGREE"]:
        lbl = "COARSE-DISAGREE"
    elif res["REP-NOEXIST"] + res["MEMBER-NOEXIST"]:
        lbl = "COARSE-STRUCT-FAIL"
    elif max(len(m) for m in cls) == 1:
        lbl = "COARSE-NO-HOLDOUT"
    else:
        lbl = "COARSE-HOLDS"
    return {"label": lbl, "classes": rows, "n_classes": len(cls), "counts": res, "pairs_intended": tot["i"],
            "pairs_inspected": tot["s"], "pairs_evaluable": tot["e"], "macro_state_disagreements": tot["mac"],
            "micro_state_pair_mismatches": tot["mic"]}


def status_of(e3):
    """Complete evidence only (production rows have no UNKNOWN)."""
    if e3[0] == "FAIL":
        return "AUT-FAIL"
    rest = e3[1:]
    if all(s == "PASS" for s in rest):
        return "FULL"
    if any(s == "PASS" for s in rest):
        return "RESTRICTED"
    return "AUT-ONLY"


def oracle_row(model, ci, tau, T, n):
    N = 2 ** n
    fam = family(n)
    c = fam[ci]
    lab = labels([macro(c, x, n) for x in range(N)])
    Q = interventions(n)
    G, e3, wit = {}, [], []
    for i, q in enumerate(Q):
        Fq = intervened(T, n, q, tau)
        G[i], w = exists_and_witness(lab, [lab[y] for y in Fq])
        e3.append("PASS" if G[i] is not None else "FAIL")
        wit.append(w)
    k = len(set(lab))
    sizes = [lab.count(a) for a in range(k)]
    st = status_of(e3)
    ctl = k in (1, N)
    disp = ("CONTROL" if st == "FULL" else "CHECKER-INVALID") if ctl else st
    sch = []
    if c[0] == "F3":
        sch = ["H-OUT"]
    elif c[0] in ("F2", "F4") or (c[0] == "F1" and c[3] != "val"):
        sch = ["H-COARSE"]
    return {"model": model, "cand_id": ci, "tau": tau,
            "E1": {"n_macro": k, "log2_n_macro": round(math.log2(k), 12), "fibre_min": min(sizes), "fibre_max": max(sizes)},
            "is_control": ctl, "E2": {"status": e3[0], "witness": wit[0]},
            "E3": [[i, e3[i], wit[i]] for i in range(len(Q))],
            "Q_prime": [i for i, s in enumerate(e3) if s == "PASS"], "n_Q": len(Q), "status": st,
            "q_prime_lower_bound": False, "display": disp, "beta_fine_all_singletons": True,
            "coarse": {s: coarse(s, c, Q, n, G, lab) for s in sch},
            "coverage": {"declared_pairs": len(Q) * N, "checked_pairs": len(Q) * N},
            "partition_sha": hashlib.sha256(",".join(map(str, lab)).encode()).hexdigest()[:16]}


# ---------------------------------------------------------------- Track V and calibrations

def v_audit(T1, T2):
    def r150(y):
        return sum((((y >> ((i - 1) % 4)) ^ (y >> i) ^ (y >> ((i + 1) % 4))) & 1) << i for i in range(4))

    def par2(x):
        return sum((((x >> 2 * b) & 1) ^ ((x >> 2 * b + 1) & 1)) << b for b in range(4))

    def sb(y, k, v):
        return (y | (1 << k)) if v else (y & ~(1 << k))

    def run(T, n, alpha, tau, cases):
        fails, noex, pairs = 0, [], 0
        Ft = iterate(T, tau)
        a = [alpha(x) for x in range(2 ** n)]
        for name, micro, macro_f in cases:
            img = [alpha(Ft[micro(x) if micro else x]) for x in range(2 ** n)]
            fails += sum(macro_f(a[x]) != img[x] for x in range(2 ** n))
            pairs += 2 ** n
            if exists_and_witness(a, img)[0] is None:
                noex.append(name)
        return pairs, fails, noex

    out = {}
    flips = [(f"flip{j}", (lambda x, j=j: x ^ (1 << j))) for j in range(8)]
    p1 = [("id", None, r150)] + [(nm, f, (lambda y, k=int(nm[4:]) // 2: r150(y ^ (1 << k)))) for nm, f in flips]
    for b in range(4):
        for c0 in (0, 1):
            for c1 in (0, 1):
                p1.append((f"breset{2*b}_{c0}{c1}", (lambda x, b=b, c0=c0, c1=c1: sb(sb(x, 2 * b, c0), 2 * b + 1, c1)),
                           (lambda y, b=b, v=c0 ^ c1: r150(sb(y, b, v)))))
    out["P1"] = run(T1, 8, par2, 2, p1)
    n1 = [("id", None, r150)] + [(f"reset{j}_{c}", (lambda x, j=j, c=c: sb(x, j, c)),
                                   (lambda y, k=j // 2, c=c: r150(sb(y, k, c)))) for j in range(8) for c in (0, 1)]
    out["N1"] = run(T1, 8, par2, 2, n1)
    lo, hi, inc = (lambda x: x % 16), (lambda x: x // 16), (lambda y: (y + 1) % 16)
    # P2 with full Q incl. knockouts and tick: computed directly
    pairs = fails = 0
    noex = []
    a = [lo(x) for x in range(256)]
    for q in interventions(8):
        op, j, c = q
        img = [lo(y) for y in intervened(T2, 8, q, 1)]
        if op == "tick":
            f = lambda y: inc(inc(y))
        elif op == "id" or j >= 4:
            f = inc
        elif op == "reset":
            f = lambda y, j=j, c=c: inc(sb(y, j, c))
        elif op == "flip":
            f = lambda y, j=j: inc(y ^ (1 << j))
        else:
            f = lambda y, j=j, c=c: sb(inc(y), j, c)
        fails += sum(f(a[x]) != img[x] for x in range(256))
        pairs += 256
        if exists_and_witness(a, img)[0] is None:
            noex.append(q)
    out["P2"] = (pairs, fails, noex)
    p3 = [("id", None, inc)] + [(f"reset{j}_{c}", (lambda x, j=j, c=c: sb(x, j, c)),
                                   (inc if j < 4 else (lambda h, k=j - 4, c=c: inc(sb(h, k, c)))))
                                  for j in range(8) for c in (0, 1)]
    p3 += [(nm, f, (inc if int(nm[4:]) < 4 else (lambda h, k=int(nm[4:]) - 4: inc(h ^ (1 << k))))) for nm, f in flips]
    out["P3"] = run(T2, 8, hi, 16, p3)
    a = [hi(x) for x in range(256)]
    img = [hi(y) for y in iterate(T2, 17)]
    out["N2"] = (512, sum(inc(a[x]) != img[x] for x in range(256)),
                 ["tick"] if exists_and_witness(a, img)[0] is None else [])
    img = [hi(y) for y in iterate(T2, 1)]
    out["N3"] = (256, sum(a[x] != img[x] for x in range(256)), ["id"] if exists_and_witness(a, img)[0] is None else [])

    def pp(x):
        y = par2(x)
        return ((y & 1) ^ ((y >> 1) & 1)) | ((((y >> 2) & 1) ^ ((y >> 3) & 1)) << 1)
    sw = lambda z: ((z & 1) << 1) | ((z >> 1) & 1)
    p4 = [("id", None, sw)] + [(nm, f, (lambda z, k=int(nm[4:]) // 4: sw(z ^ (1 << k)))) for nm, f in flips]
    out["P4"] = run(T1, 8, pp, 2, p4)
    return {k: {"pairs": v[0], "failing": v[1], "noexist": [str(x) for x in v[2]]} for k, v in out.items()}


def main():
    fx = json.load(open(os.path.join(HERE, "fixtures.json")))
    sel = [10 * j + j % 5 for j in range(273)]
    checks = []

    def chk(name, ok, detail=None):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    chk("audit list equals frozen list", sel == fx["audit_rows"], len(sel))
    T = {m: one_step(m) for m in ("M1", "M2", "M3", "M4")}
    # independent candidate ids against declarations
    for n in (8, 10):
        fam = family(n)
        dec = fx["candidates"][str(n)]
        chk(f"candidate count n={n}", len(fam) == len(dec), len(fam))
    # Track V
    rv = json.load(open(os.path.join(HERE, "results_v.json")))
    va = v_audit(T["M1"], T["M2"])
    prod = {c["id"]: c for c in rv["V"]["controls"]}
    for k, v in va.items():
        same = v["pairs"] == prod[k]["pairs"] and v["failing"] == prod[k]["failing"] and len(v["noexist"]) == len(prod[k]["noexist"])
        chk(f"V {k}", same, {"oracle": v, "prod": {x: prod[k][x] for x in ("pairs", "failing", "noexist")}})
    chk("V totals 30976 / 2080", sum(v["pairs"] for v in va.values()) == 30976 and sum(v["failing"] for v in va.values()) == 2080)
    # calibrations
    m1ok = 0
    for ci in range(135):
        lab = labels([macro(family(8)[ci], x, 8) for x in range(256)])
        for t in (4, 8, 16):
            m1ok += exists_and_witness(lab, [lab[y] for y in iterate(T["M1"], t)])[0] is not None
    chk("H-M1-tau 405", m1ok == 405 == rv["calibrations"]["H-M1-tau"]["pass"], m1ok)
    m2 = []
    for ci, c in enumerate(family(8)):
        if c[0] != "F3":
            continue
        lab = labels([macro(c, x, 8) for x in range(256)])
        for t in TAUS:
            m2.append(exists_and_witness(lab, [lab[y] for y in iterate(T["M2"], t)])[0] is not None)
    chk("H-M2-F3 75/150", sum(m2) == 75 == rv["calibrations"]["H-M2-F3"]["pass"] and len(m2) == 150, sum(m2))
    chk("H-M2-F3 per pair", m2 == [r["e2"] for r in rv["calibrations"]["H-M2-F3"]["rows"]])
    # D: whole-run coverage and arithmetic
    rows = [json.loads(ln) for ln in open(os.path.join(HERE, "results_d.jsonl"))]
    ids = [r["row"] for r in rows]
    chk("D row coverage exactly 0..2729 once", sorted(ids) == list(range(2730)) and len(ids) == 2730, len(ids))
    chk("D checked pairs = declared 59,312,640",
        sum(r["coverage"]["checked_pairs"] for r in rows) == 59312640 == sum(r["coverage"]["declared_pairs"] for r in rows))
    offs = {"M1": 0, "M2": 675, "M3": 1350, "M4": 2025}
    arith = []
    for r in rows:
        e3 = [s for _, s, _ in r["E3"]]
        ok = (r["row"] == offs[r["model"]] + 5 * r["cand_id"] + TAUS.index(r["tau"])
              and r["E2"]["status"] == e3[0] and r["Q_prime"] == [i for i, s in enumerate(e3) if s == "PASS"]
              and r["n_Q"] == len(e3) and r["status"] == status_of(e3)
              and all((s == "FAIL") == (w is not None) for _, s, w in r["E3"]))
        for sch in r["coarse"].values():
            ok &= sch["pairs_intended"] == sum((len(c["members"])) * 2 ** (8 if r["model"] != "M4" else 10) for c in sch["classes"])
            ok &= sch["pairs_evaluable"] <= sch["pairs_inspected"] <= sch["pairs_intended"]
        if not ok:
            arith.append(r["row"])
    chk("D cross-field arithmetic all rows", not arith, arith[:10])
    # D: independent recomputation of the 273 selected rows
    by = {r["row"]: r for r in rows}
    sci_skip = {"runtime", "candidate", "row"}
    mism = []
    for rid in sel:
        r = by[rid]
        n = 10 if r["model"] == "M4" else 8
        o = oracle_row(r["model"], r["cand_id"], r["tau"], T[r["model"]], n)
        p = {k: v for k, v in r.items() if k not in sci_skip}
        if json.dumps(p, sort_keys=True) != json.dumps(o, sort_keys=True):
            diff = [k for k in set(p) | set(o) if json.dumps(p.get(k), sort_keys=True) != json.dumps(o.get(k), sort_keys=True)]
            mism.append({"row": rid, "fields": diff})
    chk("D 273 selected rows: all scientific fields equal", not mism, {"rows": len(sel), "mismatches": mism[:10]})
    res = {"pass": all(c["pass"] for c in checks), "n_checks": len(checks), "checks": checks,
           "selected_rows": len(sel), "selected_pairs": sum(by[r]["coverage"]["checked_pairs"] for r in sel),
           "shared_inputs": ["fixtures.json", "results_*.json(l)", "bnet.parse_bnet", "causalbool.repertoire (M4 only)"]}
    json.dump(res, open(os.path.join(HERE, "audit.json"), "w"), indent=1)
    print("AUDIT", "PASS" if res["pass"] else "FAIL", f"{sum(c['pass'] for c in checks)}/{len(checks)}")
    for c in checks:
        if not c["pass"]:
            print("  FAIL", c["check"], str(c["detail"])[:300])
    sys.exit(0 if res["pass"] else 1)


if __name__ == "__main__":
    main()
