"""abstraction-validation-v1-r1 -- stage runner (Tracks V, calibrations, theorem, X, then D).

Usage (cwd = CausalBool, PYTHONPATH=index-deconvolution/src):
    python .../run.py declare        # write fixtures.json (declarations only, nothing executed)
    python .../run.py stage1         # V, calibrations, theorem checks, X  (after freeze)
    python .../run.py stageD         # all 2,730 D rows                       (after stage1 passes)
Refuses (exit 2) on an empty declaration, printing its denominator; exits 3 on
CHECKER-INVALID; exits 4 if the frozen sources differ from freeze.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import study as S
from deconvolution import commutation_failures, essential_variables, induced_map

HERE = os.path.dirname(os.path.abspath(__file__))


def out(name):
    return os.path.join(HERE, name)


def require_nonempty(label: str, n: int) -> None:
    print(f"{label}: denominator {n}")
    if n == 0:
        print(f"REFUSE: {label} declares 0 items")
        sys.exit(2)


# --------------------------------------------------------------------------- Track V declarations

def r150_ring(y: int, m: int) -> int:
    b = [(y >> i) & 1 for i in range(m)]
    return sum((b[(i - 1) % m] ^ b[i] ^ b[(i + 1) % m]) << i for i in range(m))


def setbit(y: int, k: int, c: int) -> int:
    return (y & ~(1 << k)) | (c << k)


def par_pairs(x: int) -> int:                      # F1 par (2,0) on n = 8 as a 4-bit integer
    return sum((((x >> 2 * b) ^ (x >> (2 * b + 1))) & 1) << b for b in range(4))


def parpar(x: int) -> int:                         # F4 par o par (2,0), o2 = 0, as a 2-bit integer
    y = par_pairs(x)
    return ((y ^ (y >> 1)) & 1) | ((((y >> 2) ^ (y >> 3)) & 1) << 1)


def v_controls() -> list[dict]:
    """Supplied controls of MODEL_AND_MAPS §6: (model, alpha, tau, Q, supplied map per q, expected)."""
    F150 = lambda y: r150_ring(y, 4)
    inc16 = lambda y: (y + 1) % 16
    flips8 = [{"op": "flip", "j": j, "c": None} for j in range(8)]
    idq = [{"op": "id", "j": None, "c": None}]
    p1q = idq + flips8 + [{"op": "block_reset", "j": 2 * b, "c": (c0, c1)} for b in range(4)
                          for c0 in (0, 1) for c1 in (0, 1)]

    def p1map(q):
        if q["op"] == "id":
            return F150, ("id",)
        if q["op"] == "flip":
            k = q["j"] // 2
            return (lambda y, k=k: F150(y ^ (1 << k))), ("flip", k)
        k, v = q["j"] // 2, q["c"][0] ^ q["c"][1]
        return (lambda y, k=k, v=v: F150(setbit(y, k, v))), ("reset", k, v)

    n1q = idq + [{"op": "reset", "j": j, "c": c} for j in range(8) for c in (0, 1)]

    def n1map(q):
        if q["op"] == "id":
            return F150, ("id",)
        k, c = q["j"] // 2, q["c"]
        return (lambda y, k=k, c=c: F150(setbit(y, k, c))), ("reset", k, c)

    def p2map(q):
        op, j, c = q["op"], q["j"], q["c"]
        if op == "tick":
            return (lambda y: inc16(inc16(y))), ("tick",)
        if op == "id" or j >= 4:
            return inc16, ("id",)
        if op == "reset":
            return (lambda y, j=j, c=c: inc16(setbit(y, j, c))), ("reset", j, c)
        if op == "flip":
            return (lambda y, j=j: inc16(y ^ (1 << j))), ("flip", j)
        return (lambda y, j=j, c=c: setbit(inc16(y), j, c)), ("knockout", j, c)

    p3q = idq + [{"op": "reset", "j": j, "c": c} for j in range(8) for c in (0, 1)] + flips8

    def p3map(q):
        op, j, c = q["op"], q["j"], q["c"]
        if op == "id" or j < 4:
            return inc16, ("id",)
        if op == "reset":
            return (lambda h, k=j - 4, c=c: inc16(setbit(h, k, c))), ("reset", j - 4, c)
        return (lambda h, k=j - 4: inc16(h ^ (1 << k))), ("flip", j - 4)

    n2q = idq + [{"op": "tick", "j": None, "c": None}]
    swap = lambda z: ((z >> 1) & 1) | ((z & 1) << 1)

    def p4map(q):
        if q["op"] == "id":
            return swap, ("id",)
        k = q["j"] // 4
        return (lambda z, k=k: swap(z ^ (1 << k))), ("flip", k)

    lo, hi = (lambda x: x & 15), (lambda x: (x >> 4) & 15)
    return [
        {"id": "P1", "model": "M1", "alpha": par_pairs, "tau": 2, "Q": p1q, "map": p1map,
         "expected_failing": 0, "expected_noexist": []},
        {"id": "N1", "model": "M1", "alpha": par_pairs, "tau": 2, "Q": n1q, "map": n1map,
         "expected_failing": 2048, "expected_failing_per_q": {S.q_name(q): 128 for q in n1q[1:]},
         "expected_noexist": [S.q_name(q) for q in n1q[1:]]},
        {"id": "P2", "model": "M2", "alpha": lo, "tau": 1, "Q": S.track_d_q(8), "map": p2map,
         "expected_failing": 0, "expected_noexist": []},
        {"id": "P3", "model": "M2", "alpha": hi, "tau": 16, "Q": p3q, "map": p3map,
         "expected_failing": 0, "expected_noexist": []},
        {"id": "N2", "model": "M2", "alpha": hi, "tau": 16, "Q": n2q,
         "map": lambda q: (inc16, ("id",)), "expected_failing": 16, "expected_noexist": ["tick"]},
        {"id": "N3", "model": "M2", "alpha": hi, "tau": 1, "Q": idq,
         "map": lambda q: ((lambda h: h), ("id",)), "expected_failing": 16, "expected_noexist": ["id"]},
        {"id": "P4", "model": "M1", "alpha": parpar, "tau": 2, "Q": idq + flips8, "map": p4map,
         "expected_failing": 0, "expected_noexist": []},
    ]


V_EXPECTED_PAIRS = {"P1": 6400, "N1": 4352, "P2": 10752, "P3": 6400, "N2": 512, "N3": 256, "P4": 2304}


def h_m2_f3_prediction(cand: dict, tau: int) -> bool:
    return tau % (2 ** cand["a"]) == 0


# --------------------------------------------------------------------------- declarations

def declarations() -> dict:
    cands = {n: S.candidates(n) for n in (8, 10)}
    d = {
        "schema": "abstraction-validation-v1-r1-fixtures",
        "models": {m: {"n": S.MODEL_N[m], "offset": S.OFFSETS[m]} for m in S.MODEL_IDS},
        "M4_source": S.EGFR, "taus": list(S.TAUS),
        "candidates": {str(n): c for n, c in cands.items()},
        "candidate_counts": {str(n): len(c) for n, c in cands.items()},
        "Q": {str(n): [S.q_name(q) for q in S.track_d_q(n)] for n in (8, 10)},
        "n_rows": sum(len(cands[S.MODEL_N[m]]) * 5 for m in S.MODEL_IDS),
        "declared_D_pairs": sum(len(cands[S.MODEL_N[m]]) * 5 * len(S.track_d_q(S.MODEL_N[m])) * 2 ** S.MODEL_N[m]
                                for m in S.MODEL_IDS),
        "schemes": {"beta_fine": "all candidates; singleton classes",
                    "H-COARSE": "F1 par/cnt/or/and, F2, F4: (op, coarse k, c); F4 coarse k = level-2",
                    "H-OUT": "F3 only: q_id + out-of-block reset/flip/knockout merged; tick and in-block singletons"},
        "V": [{"id": c["id"], "model": c["model"], "tau": c["tau"], "Q": [S.q_name(q) for q in c["Q"]],
               "expected_pairs": V_EXPECTED_PAIRS[c["id"]], "expected_failing": c["expected_failing"],
               "expected_noexist": c["expected_noexist"]} for c in v_controls()],
        "V_totals": {"pairs": 30976, "failing": 2080},
        "calibrations": {"H-M1-tau": {"expected_pass": 405},
                         "H-M2-F3": {"expected_pass": 75, "of": 150, "per_wo": [9, 11, 7, 10, 8, 6, 9, 8, 7]}},
        "X": {"pairs": 630},
        "fixtures": {
            "FX-R1a": "M2, F3 val [0,4), tau 1, beta_fine: G_flip_j exists j<4; all classes singletons; no disagreement",
            "FX-R1b": "same, wrong-beta class (flip, in) = flips 0..3: DISAGREE at macro code of x=0 (flip0->2, flip1->3); per-q existence passes",
            "FX-R1c": "M2, F1 val (4,0), tau 1, wrong-beta class (flip, block 0): DISAGREE at x=0; not masked by CONTROL",
            "FX-REP": "M1, F1 par (2,0), tau 2, H-COARSE class {reset0_0, reset1_0}: REP-NOEXIST; reset1_0 NOT-EVALUABLE; own E3 FAIL",
            "FX-TIMING": "M2 tau 1: F_{reset0_1}(0) = 2 (reset then step), not 1",
            "FX-RAGGED": "P(3,1,8) block lengths 1,3,3,1",
        },
        "fixture_exposure": "FX-R1a/b/c and FX-REP compute D-row evidence for (M2, F3 [0,4), 1), (M2, F1 val (4,0), 1), "
                            "(M1, F1 par (2,0), 2) before freeze; recorded as exposure",
        "audit_rows": S.audit_rows(),
    }
    tau_counts = [0] * 5
    for r in d["audit_rows"]:
        tau_counts[r % 5] += 1
    d["audit_tau_counts"] = tau_counts
    return d


# --------------------------------------------------------------------------- freeze check

def check_freeze() -> dict:
    fz = json.load(open(out("freeze.json")))
    bad = []
    for p, h in fz["files"].items():
        if hashlib.sha256(open(os.path.join(S.ROOT, p), "rb").read()).hexdigest() != h:
            bad.append(p)
    if bad:
        print("FREEZE VIOLATION", bad)
        sys.exit(4)
    origins = S.import_origins()
    if origins != fz["import_origins"]:
        print("IMPORT ORIGIN MISMATCH", origins)
        sys.exit(4)
    return fz


# --------------------------------------------------------------------------- stage 1

def track_v(models) -> dict:
    res, total_pairs, total_fail, ok = [], 0, 0, True
    for c in v_controls():
        m = models[c["model"]]
        alpha = [c["alpha"](x) for x in range(m.N)]
        per_q, noexist, pairs, fails = [], [], 0, 0
        for q in c["Q"]:
            Fq = m.q_table(q, c["tau"])
            image = [alpha[y] for y in Fq]
            f, label = c["map"](q)
            failing = commutation_failures(alpha, image, f)
            G, w = induced_map(alpha, image)
            pairs += m.N
            fails += len(failing)
            if G is None:
                noexist.append(S.q_name(q))
            per_q.append({"q": S.q_name(q), "beta": list(map(str, label)), "failing": len(failing),
                          "first_failing": failing[0] if failing else None, "iv_a": G is not None,
                          "witness": list(w) if w else None})
        good = (pairs == V_EXPECTED_PAIRS[c["id"]] and fails == c["expected_failing"]
                and noexist == c["expected_noexist"])
        if "expected_failing_per_q" in c:
            good &= all(r["failing"] == c["expected_failing_per_q"].get(r["q"], 0) for r in per_q)
        ok &= good
        total_pairs += pairs
        total_fail += fails
        res.append({"id": c["id"], "pairs": pairs, "failing": fails, "noexist": noexist,
                    "matches_hand": good, "per_q": per_q})
    # P4 nesting is representation: same partition as F1 par (4,0)
    f1par40 = next(c for c in S.candidates(8) if c["family"] == "F1" and c["w"] == 4 and c["o"] == 0 and c["g"] == "par")
    same = (S.canonical_partition([parpar(x) for x in range(256)])
            == S.canonical_partition([S.alpha_value(f1par40, x, 8) for x in range(256)]))
    # P1 beta sharing: flips 2b,2b+1 and resets (0,1)/(1,0), (0,0)/(1,1) share labels
    p1 = res[0]["per_q"]
    lab = {r["q"]: tuple(r["beta"]) for r in p1}
    share = all(lab[f"flip{2*b}"] == lab[f"flip{2*b+1}"] and lab[f"breset{2*b}_01"] == lab[f"breset{2*b}_10"]
                and lab[f"breset{2*b}_00"] == lab[f"breset{2*b}_11"] for b in range(4))
    ok &= same and share and total_pairs == 30976 and total_fail == 2080
    # C1/C2: constant and identity on every model and tau, Track-D Q
    cc = []
    for mid, m in models.items():
        cs = S.candidates(m.n)
        for cand in (cs[-2], cs[-1]):
            for tau in S.TAUS:
                canon = S.canonical_partition([S.alpha_value(cand, x, m.n) for x in range(m.N)])
                exist = sum(induced_map(canon, [canon[y] for y in m.q_table(q, tau)])[0] is not None
                            for q in S.track_d_q(m.n))
                cc.append({"model": mid, "control": cand["g"], "tau": tau, "q_exist": exist,
                           "n_Q": len(S.track_d_q(m.n)), "n_macro": len(set(canon))})
                ok &= exist == len(S.track_d_q(m.n))
    return {"controls": res, "P4_same_partition_as_F1par40": same, "P1_beta_sharing": share,
            "C1_C2": cc, "total_pairs": total_pairs, "total_failing": total_fail, "pass": bool(ok)}


def e2_status(m, cand, tau) -> tuple[bool, list | None]:
    canon = S.canonical_partition([S.alpha_value(cand, x, m.n) for x in range(m.N)])
    G, w = induced_map(canon, [canon[y] for y in m.Ft(tau)])
    return G is not None, (list(w) if w else None)


def calibrations(models) -> dict:
    m1 = models["M1"]
    m1_rows = [(c["id"], t, e2_status(m1, c, t)[0]) for c in S.candidates(8) for t in (4, 8, 16)]
    m1_pass = sum(p for _, _, p in m1_rows)
    m2 = models["M2"]
    f3 = [c for c in S.candidates(8) if c["family"] == "F3"]
    rows, per_wo, agree = [], {}, True
    for c in f3:
        for t in S.TAUS:
            got = e2_status(m2, c, t)[0]
            pred = h_m2_f3_prediction(c, t)
            agree &= got == pred
            per_wo[(c["w"], c["o"])] = per_wo.get((c["w"], c["o"]), 0) + int(got)
            rows.append({"cand_id": c["id"], "a": c["a"], "tau": t, "e2": got, "predicted": pred})
    per_wo_list = [per_wo[(w, o)] for w in S.WIDTHS for o in range(w)]
    m2_pass = sum(r["e2"] for r in rows)
    return {"H-M1-tau": {"pass": m1_pass, "of": len(m1_rows), "expected": 405, "ok": m1_pass == 405 == len(m1_rows)},
            "H-M2-F3": {"pass": m2_pass, "of": len(rows), "expected": 75, "per_wo": per_wo_list,
                        "per_pair_agree": agree, "rows": rows,
                        "ok": agree and m2_pass == 75 and per_wo_list == [9, 11, 7, 10, 8, 6, 9, 8, 7]}}


def theorem_checks(models) -> dict:
    """Injective (F1 val, identity) and constant maps: every individual G_q exists."""
    total = exist = 0
    viol = []
    for mid, m in models.items():
        for cand in S.candidates(m.n):
            if not ((cand["family"] == "F1" and cand["g"] == "val") or cand["family"] == "C"):
                continue
            canon = S.canonical_partition([S.alpha_value(cand, x, m.n) for x in range(m.N)])
            assert len(set(canon)) in (1, m.N)
            for tau in S.TAUS:
                for q in S.track_d_q(m.n):
                    total += 1
                    if induced_map(canon, [canon[y] for y in m.q_table(q, tau)])[0] is not None:
                        exist += 1
                    else:
                        viol.append([mid, cand["id"], tau, S.q_name(q)])
    return {"checked": total, "exist": exist, "violations": viol, "ok": total > 0 and exist == total}


def track_x(models) -> dict:
    rows, agree = [], 0
    for mid, m in models.items():
        for tau in S.TAUS:
            Ft = m.Ft(tau)
            ess = [essential_variables([(Ft[x] >> k) & 1 for x in range(m.N)], m.n) for k in range(m.n)]
            for c in S.candidates(m.n):
                if c["family"] != "F3":
                    continue
                B = set(range(c["a"], c["a"] + c["len"]))
                pred = all(set(ess[i]) <= B for i in B)
                got, w = e2_status(m, c, tau)
                agree += pred == got
                rows.append({"model": mid, "cand_id": c["id"], "tau": tau, "support_closed": pred, "e2": got})
    return {"pairs": len(rows), "agree": agree, "ok": len(rows) == 630 and agree == 630, "rows": rows}


def stage1() -> int:
    check_freeze()
    t0 = time.time()
    models = {m: S.Model(m) for m in S.MODEL_IDS}
    v = track_v(models)
    cal = calibrations(models)
    th = theorem_checks(models)
    x = track_x(models)
    invalid = not (v["pass"] and cal["H-M1-tau"]["ok"] and cal["H-M2-F3"]["ok"] and th["ok"] and x["ok"])
    status = S.run_status(False, invalid, False)
    json.dump({"status": status, "V": v, "calibrations": cal, "theorem": th, "import_origins": S.import_origins(),
               "runtime_seconds": round(time.time() - t0, 3)}, open(out("results_v.json"), "w"), indent=1)
    json.dump({"status": status, **x}, open(out("results_x.json"), "w"), indent=1)
    print("stage1", status, "V", v["total_pairs"], v["total_failing"], "H-M1", cal["H-M1-tau"]["pass"],
          "H-M2", cal["H-M2-F3"]["pass"], cal["H-M2-F3"]["per_wo"], "theorem", th["exist"], "/", th["checked"],
          "X", x["agree"], "/", x["pairs"])
    return 3 if invalid else 0


def stageD() -> int:
    check_freeze()
    v = json.load(open(out("results_v.json")))
    if v["status"] != "COMPLETE":
        print("stage1 not COMPLETE; D refused")
        return 3
    decl = declarations()
    require_nonempty("declared D rows", decl["n_rows"])
    require_nonempty("declared D pairs", decl["declared_D_pairs"])
    t0 = time.time()
    checked_pairs = rows = wit = 0
    path = out("results_d.jsonl")
    if os.path.exists(path):
        print("results_d.jsonl exists; refusing to overwrite")
        return 2
    with open(path, "w") as fh:
        for mid in S.MODEL_IDS:
            m = S.Model(mid)
            for cand in S.candidates(m.n):
                for tau in S.TAUS:
                    t1 = time.time()
                    r = S.evaluate_row(m, cand, tau)
                    wit += S.verify_row_witnesses(m, cand, r)
                    r["runtime"] = {"seconds": round(time.time() - t1, 4)}
                    checked_pairs += r["coverage"]["checked_pairs"]
                    rows += 1
                    fh.write(json.dumps(r, sort_keys=True) + "\n")
            print(mid, "done", round(time.time() - t0, 1), "s", flush=True)
    summary = {"rows": rows, "declared_rows": decl["n_rows"], "checked_pairs": checked_pairs,
               "declared_pairs": decl["declared_D_pairs"], "witnesses_verified": wit,
               "runtime_seconds": round(time.time() - t0, 2)}
    json.dump(summary, open(out("results_d_summary.json"), "w"), indent=1)
    print(summary)
    return 0 if rows == decl["n_rows"] and checked_pairs == decl["declared_D_pairs"] else 3


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "declare":
        if os.path.exists(out("fixtures.json")):
            print("fixtures.json exists; refusing to overwrite")
            sys.exit(2)
        d = declarations()
        require_nonempty("declared D rows", d["n_rows"])
        json.dump(d, open(out("fixtures.json"), "w"), indent=1)
        print("declared", d["candidate_counts"], d["n_rows"], d["declared_D_pairs"], d["audit_tau_counts"])
    elif cmd == "stage1":
        sys.exit(stage1())
    elif cmd == "stageD":
        sys.exit(stageD())
