"""gap-ranking-v1-r1 -- independent audit from saved bytes (PROTOCOL.md §7).

Imports no producer score/rank/join function: gapscore, join and produce are never
imported.  The only repository import is the adopted ``study`` (model owners and the
candidate declaration), used to validate trajectories and population identity.  The
oracle logic below (sampling, block slicing, occurrence membership, first differences,
pooled counts, rational ordering by cross-multiplication, endpoints) is a run-local
audit exception, hand-written here, not a second production owner.

Usage: python audit.py <production dir> <audit out dir>
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
import shutil
import sys
import tempfile

TRUSTED = {
    "results_d": "7119aa72f6483e955aa1033cbde7d0ef144f34ea8a614a03ba66830354ad0e12",
    "nonf3": "3dc79653b540512de1e374e0a95d73b9abc8b02b80b5e7390d450ad73ea6959d",
}
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 5))
OUTCOME = os.path.join(REPO, "index-deconvolution", "results", "causal_abstraction_validation",
                       "abstraction-validation-v1-r1")
TAU_LIST = [1, 2, 4, 8, 16]
OFFSET = {"M1": 0, "M2": 675, "M3": 1350, "M4": 2025}
NBITS = {"M1": 8, "M2": 8, "M3": 8, "M4": 10}


def h(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class Audit:
    def __init__(self):
        self.checks, self.failures, self.missing = {}, [], []

    def ok(self, name, n=1):
        self.checks[name] = self.checks.get(name, 0) + n

    def bad(self, name, detail):
        self.failures.append({"check": name, "detail": str(detail)[:300]})

    def status(self):
        if self.failures:
            return "INVALID"
        if self.missing:
            return "INCOMPLETE"
        return "VALID_COMPLETE"


# --------------------------------------------------------------------------- oracle pieces

def blocks_of(w, o, n):
    out = []
    if o:
        out.append((0, o))
    start = o
    while start < n:
        out.append((start, min(start + w, n) - start))
        start += w
    return out


def frames_of(xs, tau):
    return [xs[k * tau] for k in range(64 // tau + 1)]


def bits_value(x, a, ln):
    return sum(((x >> (a + k)) & 1) << k for k in range(ln))


def rule150(x, n=8):
    y = 0
    for i in range(n):
        left, mid, right = (x >> ((i - 1) % n)) & 1, (x >> i) & 1, (x >> ((i + 1) % n)) & 1
        y |= (left ^ mid ^ right) << i
    return y


def cmp_score(p, q):
    """Descending rational score; None (UNAVAILABLE) last.  Ties left to the caller."""
    if p is None or q is None:
        return (p is None) - (q is None)
    lhs, rhs = p[0] * q[1], q[0] * p[1]
    return -1 if lhs > rhs else (1 if lhs < rhs else 0)


# --------------------------------------------------------------------------- audit

def run(prod, results_d, nonf3, check_seal=True):
    import study as S
    A = Audit()
    files = {}
    for f in ("trajectories.json", "occurrences.jsonl", "scores.json", "ranks.json",
              "joined.json", "seal.json"):
        p = os.path.join(prod, f)
        if not os.path.exists(p):
            A.missing.append(f)
        files[f] = p
    if A.missing:
        return A
    if check_seal:
        seal = json.load(open(files["seal.json"]))
        for f, v in seal.items():
            if f != "counts" and h(os.path.join(prod, f)) != v:
                A.bad("seal", f)
        A.ok("seal_files", len(seal) - 1)

    # trajectories ---------------------------------------------------------------
    T = json.load(open(files["trajectories.json"]))
    nt = 0
    for mid in ("M1", "M2", "M3", "M4"):
        n = NBITS[mid]
        F = S.Model(mid).F
        starts = [0, 1, 1 << (n - 1), (1 << n) - 1,
                  int("".join("01"[(i % 2 == 0)] for i in reversed(range(n))), 2),
                  int("".join("01"[(i % 2 == 1)] for i in reversed(range(n))), 2)]
        trs = T.get(mid, [])
        if [t["x0"] for t in trs] != starts:
            A.bad("start_states", mid)
        for t in trs:
            xs = t["states"]
            nt += 1
            if len(xs) != 65 or xs[0] != t["x0"]:
                A.bad("trajectory_length", (mid, t["x0"], len(xs)))
            for a, b in zip(xs, xs[1:]):
                if F[a] != b:
                    A.bad("transition_owner", (mid, a, b))
                if mid == "M2" and b != (a + 1) % 256:
                    A.bad("transition_counter", (a, b))
                if mid == "M1" and b != rule150(a):
                    A.bad("transition_rule150", (a, b))
            A.ok("transitions", len(xs) - 1)
    if nt != 24:
        A.bad("trajectory_count", nt)
    A.ok("trajectories", nt)
    if rule150(1) != 131 or S.Model("M1").F[1] != 131:
        A.bad("control_rule150_declared_state", S.Model("M1").F[1])
    A.ok("control_rule150_declared_state")
    if S.Model("M2").F[255] != 0:
        A.bad("control_counter_wrap", S.Model("M2").F[255])
    A.ok("control_counter_wrap")

    # occurrences and scores ---------------------------------------------------------
    saved = {}
    with open(files["occurrences.jsonl"]) as fh:
        for line in fh:
            r = json.loads(line)
            key = (r["model"], r["tau"], r["w"], r["o"], r["traj"], r["block"], r["value"])
            if key in saved:
                A.bad("occurrence_duplicate", key)
            saved[key] = r
    expect_scores = {}
    seen = set()
    for mid in ("M1", "M2", "M3", "M4"):
        n = NBITS[mid]
        for tau in TAU_LIST:
            sampled = [frames_of(t["states"], tau) for t in T[mid]]
            for w in (2, 3, 4):
                for o in range(w):
                    reg = eli = 0
                    for ti, fr in enumerate(sampled):
                        for bi, (a, ln) in enumerate(blocks_of(w, o, n)):
                            toks = [bits_value(x, a, ln) for x in fr]
                            for v in set(toks):
                                key = (mid, tau, w, o, ti, bi, v)
                                seen.add(key)
                                occ = [k for k in range(len(toks)) if toks[k] == v]
                                d = [occ[k + 1] - occ[k] for k in range(len(occ) - 1)]
                                e = len(occ) > 2
                                g = e and all(x == d[0] for x in d)
                                eli += e
                                reg += g
                                r = saved.get(key)
                                if r is None:
                                    A.missing.append(("occurrence", key))
                                    continue
                                if (r["frames"], r["gaps"], r["eligible"], r["regular"],
                                        r["a"], r["len"]) != (occ, d, e, g, a, ln):
                                    A.bad("occurrence_record", key)
                                else:
                                    A.ok("occurrence_records")
                    expect_scores[(mid, tau, w, o)] = (reg, eli)
    for key in set(saved) - seen:
        A.bad("occurrence_unexpected", key)
    S_saved = json.load(open(files["scores.json"]))
    got = {(s["model"], s["tau"], s["w"], s["o"]): s for s in S_saved}
    if len(S_saved) != 180 or len(got) != 180:
        A.bad("score_count", len(S_saved))
    for key, (reg, eli) in expect_scores.items():
        s = got.get(key)
        if s is None:
            A.missing.append(("score", key))
        elif (s["regular"], s["eligible"], s["available"]) != (reg, eli, eli > 0):
            A.bad("score", (key, s["regular"], s["eligible"], reg, eli))
        else:
            A.ok("scores")

    # ranks --------------------------------------------------------------------------
    R = json.load(open(files["ranks.json"]))
    if len(R) != 20 or len({(r["model"], r["tau"]) for r in R}) != 20:
        A.bad("rank_lists", len(R))
    positions = 0
    for cell in R:
        mid, tau, n = cell["model"], cell["tau"], NBITS[cell["model"]]
        decl = {c["id"]: {k: v for k, v in c.items() if k != "id"} for c in S.candidates(n)}
        pop = sorted(i for i, c in decl.items()
                     if c["family"] != "C" and not (c["family"] == "F1" and c["g"] == "val"))
        if len(pop) != (124 if n == 8 else 130):
            A.bad("population_size", (mid, len(pop)))
        cands = {c["id"]: c for c in cell["candidates"]}
        if sorted(cands) != pop or cell["N"] != len(pop):
            A.bad("population_identity", (mid, tau))
            continue
        for i in pop:
            if cands[i]["candidate"] != decl[i]:
                A.bad("candidate_identity", (mid, i))
        sc = {}
        for i in pop:
            c = decl[i]
            if c["family"] == "F2":
                sc[i] = None
            else:
                reg, eli = expect_scores[(mid, tau, c["w"], c["o"])]
                sc[i] = (reg, eli) if eli else None
            saved_sc = cands[i]["score"]
            if (None if saved_sc is None else tuple(saved_sc)) != sc[i]:
                A.bad("candidate_score", (mid, tau, i))
        order = sorted(pop, key=functools.cmp_to_key(
            lambda x, y: cmp_score(sc[x], sc[y]) or (x - y)))
        if cell["canonical_order"] != pop:
            A.bad("canonical_order", (mid, tau))
        for k, (a, b) in enumerate(zip(order, cell["gap_order"])):
            if a != b:
                A.bad("rank_position", (mid, tau, k, a, b))
            else:
                positions += 1
        if len(cell["gap_order"]) != len(order):
            A.bad("rank_length", (mid, tau))
    A.ok("rank_positions", positions)
    if positions != 2510:
        A.bad("rank_positions_total", positions)

    # join and endpoints ---------------------------------------------------------------
    if h(results_d) != TRUSTED["results_d"]:
        A.bad("trusted_input_results_d", "sha256 mismatch")
        return A
    if h(nonf3) != TRUSTED["nonf3"]:
        A.bad("trusted_input_nonf3", "sha256 mismatch")
        return A
    lab = {}
    with open(results_d) as fh:
        for line in fh:
            r = json.loads(line)
            k = (r["model"], r["cand_id"], r["tau"])
            if k in lab or r["row"] != OFFSET[r["model"]] + 5 * r["cand_id"] + TAU_LIST.index(r["tau"]):
                A.bad("label_identity", k)
            lab[k] = r
    if len(lab) != 2730:
        A.bad("label_count", len(lab))
    const = {}
    for e in json.load(open(nonf3)):
        const[e["row"]] = all(len(set(m["G"].values())) == 1 for m in e["distinct_maps"])
    J = json.load(open(files["joined.json"]))
    jc = {(c["model"], c["tau"]): c for c in J["cells"]}
    tallies = {"vs_random": {}, "vs_canonical": {}}
    for cell in R:
        mid, tau = cell["model"], cell["tau"]
        c = jc.get((mid, tau))
        if c is None:
            A.missing.append(("joined_cell", mid, tau))
            continue
        full = [i for i in cell["canonical_order"] if lab[(mid, i, tau)]["status"] == "FULL"]
        N, m = len(cell["canonical_order"]), len(full)
        exp = {"N": N, "m": m, "full_ids": full}
        if m == 0:
            exp.update({"status": "NO_FULL_REFERENCE", "r_G": None, "r_C": None})
        else:
            fs = set(full)
            rG = 1 + min(k for k, i in enumerate(cell["gap_order"]) if i in fs)
            rC = 1 + min(k for k, i in enumerate(cell["canonical_order"]) if i in fs)
            # delta_random = (N+1)/(m+1) - rG, compared as exact integer cross products
            num, den = (N + 1) - rG * (m + 1), m + 1
            exp.update({"status": "AVAILABLE", "r_G": rG, "r_C": rC})
            hit = cell["gap_order"][rG - 1]
            row = OFFSET[mid] + 5 * hit + TAU_LIST.index(tau)
            dyn = ("NOT_CHARACTERISED" if row not in const else
                   "CONSTANT_DYNAMICS" if const[row] else "NONCONSTANT_DYNAMICS")
            vr = "EARLIER" if num > 0 else ("TIE" if num == 0 else "LATER")
            vc = "EARLIER" if rC > rG else ("TIE" if rC == rG else "LATER")
            fr = c.get("delta_random") or [None, None]
            ex = c.get("random_expected") or {}
            if (fr[0] * den != num * fr[1] or ex.get("num") != N + 1 or ex.get("den") != m + 1
                    or c.get("delta_canonical") != [rC - rG, 1] or c.get("vs_random") != vr
                    or c.get("vs_canonical") != vc or c["first_hit"]["id"] != hit
                    or c["first_hit"]["row"] != row or c["first_hit"]["dynamics"] != dyn):
                A.bad("endpoint_values", (mid, tau))
            tallies["vs_random"][vr] = tallies["vs_random"].get(vr, 0) + 1
            tallies["vs_canonical"][vc] = tallies["vs_canonical"].get(vc, 0) + 1
        for k, v in exp.items():
            if c.get(k) != v:
                A.bad("endpoint_" + k, (mid, tau, c.get(k), v))
        A.ok("endpoints")
    for comp in tallies:
        for k in ("EARLIER", "TIE", "LATER"):
            if J["summary"][comp].get(k, 0) != tallies[comp].get(k, 0):
                A.bad("summary_" + comp, k)
    return A


def report(A):
    return {"status": A.status(), "checks": A.checks, "failures": A.failures[:50],
            "n_failures": len(A.failures), "missing": [str(m) for m in A.missing[:50]],
            "n_missing": len(A.missing)}


def corruption_tests(prod, results_d, nonf3):
    """Three deliberate corruptions of copies; originals are never touched."""
    out = []
    tmp = tempfile.mkdtemp(prefix="ggap_corrupt_")
    try:
        # 1 alter one occurrence index
        d1 = os.path.join(tmp, "c1")
        shutil.copytree(prod, d1)
        lines = open(os.path.join(d1, "occurrences.jsonl")).read().splitlines()
        for k, line in enumerate(lines):
            r = json.loads(line)
            if len(r["frames"]) >= 3:
                r["frames"][1] += 1
                lines[k] = json.dumps(r, sort_keys=True, separators=(",", ":"))
                break
        open(os.path.join(d1, "occurrences.jsonl"), "w").write("\n".join(lines) + "\n")
        a = run(d1, results_d, nonf3, check_seal=False)
        out.append({"corruption": "occurrence_index", "caught": a.status() == "INVALID",
                    "by": sorted({f["check"] for f in a.failures})})
        # 2 swap two ranked ids, same id set
        d2 = os.path.join(tmp, "c2")
        shutil.copytree(prod, d2)
        R = json.load(open(os.path.join(d2, "ranks.json")))
        g = R[0]["gap_order"]
        g[0], g[1] = g[1], g[0]
        json.dump(R, open(os.path.join(d2, "ranks.json"), "w"))
        a = run(d2, results_d, nonf3, check_seal=False)
        out.append({"corruption": "rank_swap", "caught": a.status() == "INVALID",
                    "by": sorted({f["check"] for f in a.failures})})
        # 3 change one FULL label in a copied join input
        lab = os.path.join(tmp, "results_d.jsonl")
        lines = open(results_d).read().splitlines()
        for k, line in enumerate(lines):
            r = json.loads(line)
            if r["status"] == "FULL" and r["display"] != "CONTROL":
                r["status"] = "AUT-FAIL"
                lines[k] = json.dumps(r, sort_keys=True)
                break
        open(lab, "w").write("\n".join(lines) + "\n")
        a = run(prod, lab, nonf3)
        out.append({"corruption": "full_label", "caught": a.status() == "INVALID" and any(
            f["check"] == "trusted_input_results_d" for f in a.failures),
            "by": sorted({f["check"] for f in a.failures})})
    finally:
        shutil.rmtree(tmp)
    return out


def main(prod, dest):
    os.makedirs(dest, exist_ok=False)
    results_d = os.path.join(OUTCOME, "results_d.jsonl")
    nonf3 = os.path.join(OUTCOME, "nonf3_full_maps.json")
    A = run(prod, results_d, nonf3)
    rep = report(A)
    rep["imports"] = {m: os.path.relpath(sys.modules[m].__file__, REPO)
                      for m in ("study",) if m in sys.modules}
    rep["producer_modules_imported"] = sorted(
        m for m in ("gapscore", "join", "produce") if m in sys.modules)
    cor = corruption_tests(prod, results_d, nonf3)
    json.dump(rep, open(os.path.join(dest, "audit.json"), "w"), indent=1, sort_keys=True)
    json.dump(cor, open(os.path.join(dest, "corruptions.json"), "w"), indent=1)
    print(rep["status"], rep["n_failures"], rep["n_missing"], json.dumps(rep["checks"]))
    print(json.dumps(cor))
    ok = rep["status"] == "VALID_COMPLETE" and all(c["caught"] for c in cor) \
        and not rep["producer_modules_imported"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
