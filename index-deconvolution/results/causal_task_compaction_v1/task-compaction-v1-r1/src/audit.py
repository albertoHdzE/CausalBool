"""task-compaction-v1-r1 -- independent certificate audit.

Imports NO minimizer, witness or replay helper, NO producer code and NO report code; it
does not call the owner's fibre check. It uses only the accepted model owner and the
existing candidate declarations (study.Model.q_table, study.track_d_q, study.candidates,
study.alpha_value, study.is_control) and its own per-block checks written here.

Evidence labels: an observed inconsistency => INVALID; else missing evidence => INCOMPLETE;
else VALID_COMPLETE. INVALID outranks missing; both are recorded. A candidate that fails a
task is an ordinary negative, not an issue.

Usage: python audit.py <production dir> <audit out dir> [--bypass-integrity]
--bypass-integrity is ONLY for the manifested corruption probes: a seal mismatch is then
recorded as bypassed instead of INVALID, so the semantic checks are what must fire.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.dirname(HERE)
ISO = os.path.join(RUN, "isolated", "index-deconvolution")
STUDY_DIR = os.path.join(ISO, "results", "causal_abstraction_validation", "abstraction-validation-v1-r1-source-r2")
sys.path[:0] = [os.path.join(ISO, "src"), STUDY_DIR]

import study as S  # noqa: E402  (accepted model owner + candidate declarations)

TASK = {"T0": lambda x, n: x & 1, "T1": lambda x, n: (x >> (n - 1)) & 1,
        "TP": lambda x, n: bin(x).count("1") % 2}


class Ledger:
    def __init__(self):
        self.invalid, self.missing, self.counts = [], [], {}

    def bad(self, where, what):
        self.invalid.append({"where": where, "check": what})

    def absent(self, where, what):
        self.missing.append({"where": where, "missing": what})

    def tick(self, name, n=1):
        self.counts[name] = self.counts.get(name, 0) + n


def label_status(n_invalid, n_missing):
    if n_invalid:
        return "INVALID"
    if n_missing:
        return "INCOMPLETE"
    return "VALID_COMPLETE"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def load(path, L, where):
    try:
        return json.load(open(path))
    except FileNotFoundError:
        L.absent(where, os.path.basename(path))
    except (ValueError, OSError) as e:
        L.bad(where, f"malformed JSON: {e}")
    return None


def first_appearance(seq):
    lab, out = {}, []
    for v in seq:
        if v not in lab:
            lab[v] = len(lab)
        out.append(lab[v])
    return out


def blocks_of(vec):
    out = {}
    for x, b in enumerate(vec):
        out.setdefault(b, []).append(x)
    return out


def determines(a, b):
    """None if equal a-values force equal b-values; else the lexicographically least
    violating pair (x, y), x < y. Per-block grouping, written for this audit."""
    best = None
    for members in blocks_of(a).values():
        x = members[0]
        if best is not None and x > best[0]:
            continue
        for y in members[1:]:
            if b[y] != b[x]:
                if best is None or x < best[0]:
                    best = (x, y)
                break
    return best


def replay(tables, x, word):
    path = [x]
    for q in word:
        path.append(tables[q][path[-1]])
    return path


def is_canonical(vec):
    nxt = 0
    for v in vec:
        if v == nxt:
            nxt += 1
        elif not (type(v) is int and 0 <= v < nxt):
            return False
    return True


def check_stage_step(prev, nxt, tables):
    """True iff nxt is EXACTLY the equivalence induced by prev labels and successor prev
    labels, checked per prev-block with two-way signature/label maps."""
    up = {}
    for x in range(len(prev)):
        if up.setdefault(nxt[x], prev[x]) != prev[x]:
            return False                      # a next block straddles two prev blocks
    for members in blocks_of(prev).values():
        sig2lab, lab2sig = {}, {}
        for x in members:
            s = tuple(prev[t[x]] for t in tables)
            if sig2lab.setdefault(s, nxt[x]) != nxt[x] or lab2sig.setdefault(nxt[x], s) != s:
                return False
    return is_canonical(nxt)


def certificate(art, tables, L, where, check_minimality=True):
    """Validity (decoder, macro, alpha, coarsening) and minimality (stage induction)."""
    h, stages, alpha = art.get("outputs"), art.get("stages"), art.get("alpha")
    N = len(tables[0])
    res = {"validity": True, "minimality": True}
    if not (isinstance(stages, list) and len(stages) >= 2 and all(isinstance(s, list) and len(s) == N for s in stages)):
        L.bad(where, "stage vectors missing or malformed")
        return {"validity": False, "minimality": False}
    if alpha != stages[-1] or not is_canonical(alpha):
        L.bad(where, "alpha is not the canonical terminal stage")
        res["validity"] = False
    K = max(alpha) + 1
    if art.get("K", K) != K or len(art.get("decoder", [])) != K:
        L.bad(where, "K or decoder length")
        res["validity"] = False
    dec = art.get("decoder", [])
    if any(dec[alpha[x]] != h[x] for x in range(N) if alpha[x] < len(dec)):
        L.bad(where, "decoder value check: H(alpha(x)) != h(x)")
        res["validity"] = False
    L.tick("decoder_states_checked", N)
    macro = art.get("macro", [])
    if len(macro) != len(tables) or any(len(G) != K for G in macro):
        L.bad(where, "macro table count/shape")
        res["validity"] = False
    else:
        for q, (G, t) in enumerate(zip(macro, tables)):
            if any(G[alpha[x]] != alpha[t[x]] for x in range(N)):
                L.bad(where, f"macro-transition check: G_{q}(alpha(x)) != alpha(T_{q}(x))")
                res["validity"] = False
            L.tick("macro_state_action_checked", N)
    reps = art.get("representatives")
    if reps != [min(m) for _, m in sorted(blocks_of(alpha).items())]:
        L.bad(where, "representatives are not the smallest state per block")
        res["validity"] = False
    if not check_minimality:
        return res
    if stages[0] != first_appearance(h):
        L.bad(where, "P0 is not the canonical output partition")
        res["minimality"] = False
    for d in range(len(stages) - 1):
        if not check_stage_step(stages[d], stages[d + 1], tables):
            L.bad(where, f"stage-induction check: P{d + 1} is not the equivalence induced by P{d}")
            res["minimality"] = False
        L.tick("stage_steps_checked")
    if stages[-1] != stages[-2] or any(stages[i] == stages[i + 1] for i in range(len(stages) - 2)):
        L.bad(where, "stage chain is not strict until the first repeat")
        res["minimality"] = False
    if art.get("strict_rounds") != len(stages) - 2:
        L.bad(where, "strict_rounds")
    coars = art.get("coarsening")
    if coars is not None:
        if len(coars) != len(stages) - 1 or any(
                any(coars[d][stages[d + 1][x]] != stages[d][x] for x in range(N)) for d in range(len(stages) - 1)):
            L.bad(where, "coarsening map check")
            res["validity"] = False
    return res


def sep_stage(stages, x, y):
    return next((d for d, s in enumerate(stages) if s[x] != s[y]), None)


def check_witnesses(art, tables, L, where):
    stages, h = art["stages"], art["outputs"]
    ws = art.get("witnesses")
    if ws is None:
        L.absent(where, "witnesses")
        return
    if len(ws) != len(stages) - 2:
        L.bad(where, "one witness per strict round")
    for w in ws:
        d = w["round"]
        prev, nxt = stages[d], stages[d + 1]
        pair = None
        for x in range(len(prev)):
            y = next((y for y in range(x + 1, len(prev)) if prev[y] == prev[x] and nxt[y] != nxt[x]), None)
            if y is not None:
                pair = (x, y)
                break
        if pair != (w["x"], w["y"]):
            L.bad(where, f"witness round {d}: pair is not the lexicographically first split")
        word = w["word"]
        sd = sep_stage(stages, w["x"], w["y"])
        if sd != d + 1 or len(word) != sd:
            L.bad(where, f"witness round {d}: length {len(word)} != first separation stage {sd}")
        px, py = replay(tables, w["x"], word), replay(tables, w["y"], word)
        ox, oy = [h[s] for s in px], [h[s] for s in py]
        if px != w["path_x"] or py != w["path_y"] or ox != w["outputs_x"] or oy != w["outputs_y"]:
            L.bad(where, f"witness round {d}: replay in written order differs from saved path")
        if ox[-1] == oy[-1] or ox[:-1] != oy[:-1]:
            L.bad(where, f"witness round {d}: word does not first distinguish at its end")
        for i, q in enumerate(word):        # least action index at every position
            r = len(word) - i - 1
            P = stages[r]
            a, b = px[i], py[i]
            if P[tables[q][a]] == P[tables[q][b]] or any(P[tables[q2][a]] != P[tables[q2][b]] for q2 in range(q)):
                L.bad(where, f"witness round {d}: not the least shortest word at position {i}")
        L.tick("witnesses_replayed")


def frac(a, b):
    f = Fraction(a, b)
    return {"num": f.numerator, "den": f.denominator}


def hand_actions(F, n):
    N = 2 ** n
    tabs = [list(F)]
    tabs += [[F[(x & ~(1 << j)) | (c << j)] for x in range(N)] for j in range(n) for c in (0, 1)]
    tabs += [[F[x ^ (1 << j)] for x in range(N)] for j in range(n)]
    tabs += [[(F[x] & ~(1 << j)) | (c << j) for x in range(N)] for j in range(n) for c in (0, 1)]
    tabs += [[F[F[x]] for x in range(N)]]
    return tabs


def rule150(n):
    def f(x):
        b = [(x >> i) & 1 for i in range(n)]
        return sum((b[(i - 1) % n] ^ b[i] ^ b[(i + 1) % n]) << i for i in range(n))
    return [f(x) for x in range(2 ** n)]


def audit_tables(T, mode, L):
    out = {}
    for mid, t in T.items():
        n, N, tabs = t["n"], t["N"], t["tables"]
        acts = S.track_d_q(n)
        if N != 2 ** n or len(tabs) != len(acts) or [a["action_id"] for a in t["actions"]] != list(range(len(acts))):
            L.bad(mid, "table dimensions or action IDs")
            continue
        if any(len(r) != N or any(type(v) is not int or not 0 <= v < N for v in r) for r in tabs):
            L.bad(mid, "state range")
            continue
        if any({k: a[k] for k in ("op", "j", "c")} != q for a, q in zip(t["actions"], acts)):
            L.bad(mid, "action declarations differ from study.track_d_q order")
        if mode == "production":
            m = S.Model(mid)
            owner = [m.q_table(q, 1) for q in acts]
            if owner != tabs:
                L.bad(mid, "transition entries differ from the accepted owner")
            L.tick("transition_entries_owner_checked", len(tabs) * N)
            hand = None
            if mid == "M2":
                hand = hand_actions([(x + 1) % N for x in range(N)], n)
            if mid == "M1":
                if tabs[0] != rule150(n):
                    L.bad(mid, "M1 F differs from the rule-150 ring formula")
                L.tick("hand_checked_M1_F_entries", N)
        else:
            hand = hand_actions([(x + 1) % N for x in range(N)] if mid == "FXA" else rule150(n), n)
        if hand is not None:
            if hand != tabs:
                L.bad(mid, "transition entries differ from the hand formula")
            L.tick(f"hand_checked_{mid}_entries", len(tabs) * N)
        out[mid] = tabs
    return out


def hand_fixture_checks(L):
    T = rule150(4)
    par = [bin(x).count("1") % 2 for x in range(16)]
    ok = all(par[T[x]] == par[x] for x in range(16))
    reset0 = [T[x & ~1] for x in range(16)]
    sep = par[reset0[0]] != par[reset0[3]] and par[0] == par[3]
    cnt = all((x + 1) % 256 == ((x + 1) & 255) for x in range(256))
    if not (ok and sep and cnt):
        L.bad("fixtures", "rule-150 parity / reset witness / counter hand check")
    return {"rule150_ring4_parity_conserved": ok, "reset0_separates_0_3": sep, "counter_wraps": cnt}


def main(prod, out, bypass=False):
    if os.path.exists(out):
        print(f"refusing: {out} exists")
        return 2
    L = Ledger()
    report = {"bypass_integrity": bypass}
    # ---- integrity, identities and ID sets BEFORE computation
    seal = load(os.path.join(prod, "seal.json"), L, "seal")
    if seal:
        mism = sorted(k for k, v in seal["sha256"].items()
                      if not os.path.exists(os.path.join(prod, k)) or sha(os.path.join(prod, k)) != v)
        report["integrity_mismatches"] = mism
        if mism and not bypass:
            L.bad("seal", f"{len(mism)} files differ from seal")
    cases = load(os.path.join(prod, "cases.json"), L, "cases")
    if cases is None:
        return finish(L, report, out)
    mode = cases.get("mode")
    report["mode"] = mode
    if mode == "production":
        fz = load(os.path.join(RUN, "freeze.json"), L, "freeze")
        if fz:
            iso_root = os.path.join(RUN, "isolated")
            bad = [k for k, v in fz["isolated"].items() if not os.path.exists(os.path.join(iso_root, k))
                   or sha(os.path.join(iso_root, k)) != v]
            repo = os.path.abspath(os.path.join(RUN, *[".."] * 4))
            bad += [k for k, v in fz["inputs"].items() if sha(os.path.join(repo, k)) != v]
            bad += [k for k, v in fz["run_files"].items() if sha(os.path.join(RUN, k)) != v]
            L.tick("frozen_identities_checked", len(fz["isolated"]) + len(fz["inputs"]) + len(fz["run_files"]))
            if bad:
                L.bad("freeze", f"identity mismatch: {bad}")
        declared = json.load(open(os.path.join(RUN, "protocol", "CASES.json")))
        if declared["cells"] != cases["cells"] or declared["expected_counts"] != cases["expected_counts"]:
            L.bad("cases", "production cases differ from protocol/CASES.json")
    exp = cases["expected_counts"]
    cells = cases["cells"]
    if len(cells) != exp["cells"] or [c["cell_id"] for c in cells] != list(range(exp["cells"])):
        L.bad("cases", "cell ID set")
    present = sorted(os.listdir(os.path.join(prod, "cells"))) if os.path.isdir(os.path.join(prod, "cells")) else []
    want = [f"cell_{c['cell_id']:02d}.json" for c in cells]
    for f in sorted(set(want) - set(present)):
        L.absent(f, "cell artifact")
    for f in sorted(set(present) - set(want)):
        L.bad(f, "undeclared cell artifact")
    # ---- tables
    T = {}
    for mid in sorted({c["model"] for c in cells}):
        t = load(os.path.join(prod, "tables", f"{mid}.json"), L, mid)
        if t:
            T[mid] = t
    tabs = audit_tables(T, mode, L)
    n_tab = sum(len(v) for v in tabs.values())
    n_ent = sum(len(v) * len(v[0]) for v in tabs.values())
    if (n_tab, n_ent) != (exp["distinct_model_action_tables"], exp["distinct_model_state_action_entries"]):
        L.bad("tables", f"counts {n_tab}/{n_ent} differ from declaration")
    report["tables"] = {"action_tables": n_tab, "state_action_entries": n_ent}
    report["hand_fixtures"] = hand_fixture_checks(L)
    # ---- candidate alphas against the declarations
    calpha = {}
    for mid, t in T.items():
        ca = load(os.path.join(prod, "candidate_alphas", f"{mid}.json"), L, mid)
        if not ca:
            continue
        decl = S.candidates(t["n"])
        mine = [first_appearance([S.alpha_value(c, x, t["n"]) for x in range(t["N"])]) for c in decl]
        saved = [c["alpha"] for c in ca["candidates"]]
        if mine != saved or [c["id"] for c in ca["candidates"]] != [c["id"] for c in decl]:
            L.bad(mid, "candidate alpha vectors differ from study declarations")
        calpha[mid] = (decl, mine)
        L.tick("candidate_vectors_checked", len(decl))
    # ---- cells
    cell_rows, alphas, clos = {}, {}, {}
    rec_ids = []
    for c in cells:
        cid, where = c["cell_id"], f"cell_{c['cell_id']:02d}"
        art = load(os.path.join(prod, "cells", f"{where}.json"), L, where) if f"{where}.json" in present else None
        recs = []
        try:
            with open(os.path.join(prod, "candidates", f"{where}.jsonl")) as fh:
                recs = [json.loads(line) for line in fh]
        except FileNotFoundError:
            L.absent(where, "candidate records")
        rec_ids += [r.get("record_id") for r in recs]
        if art is None or c["model"] not in tabs:
            continue
        n0, nmiss0 = len(L.invalid), len(L.missing)
        try:
            row = audit_cell(c, art, recs, tabs[c["model"]], calpha.get(c["model"]), clos, L, where)
            alphas[cid] = art["alpha"]
        except (KeyError, IndexError, TypeError, ValueError) as e:
            L.bad(where, f"malformed artifact: {type(e).__name__}: {e}")
            row = {}
        row["status"] = label_status(len(L.invalid) - n0, len(L.missing) - nmiss0)
        cell_rows[cid] = row
    want_ids = sorted(c["cell_id"] * 1000 + k for c in cells for k in range(c["n_candidates"]))
    if len(want_ids) != exp["candidate_records"]:
        L.bad("cases", "declared candidate record count")
    got = sorted(i for i in rec_ids if isinstance(i, int))
    if got != sorted(set(got)) or not set(got) <= set(want_ids):
        L.bad("candidates", "duplicate or undeclared record IDs")
    if set(want_ids) - set(got):
        L.absent("candidates", f"{len(set(want_ids) - set(got))} declared records absent")
    report["candidate_records"] = {"declared": len(want_ids), "present": len(got)}
    # ---- cross-cell: INTERVENTION refines AUTO
    refine = []
    for c in cells:
        if c["regime"] != "INTERVENTION":
            continue
        a = next(x for x in cells if x["model"] == c["model"] and x["task"] == c["task"] and x["regime"] == "AUTO")
        if c["cell_id"] in alphas and a["cell_id"] in alphas:
            ok = determines(alphas[c["cell_id"]], alphas[a["cell_id"]]) is None and \
                max(alphas[c["cell_id"]]) >= max(alphas[a["cell_id"]])
            refine.append({"intervention_cell": c["cell_id"], "auto_cell": a["cell_id"], "refines": ok})
            if not ok:
                L.bad(f"cell_{c['cell_id']:02d}", "INTERVENTION optimum does not refine AUTO")
    report["intervention_refines_auto"] = refine
    # ---- summary.json numbers equal the audited per-cell summaries
    summ = load(os.path.join(prod, "summary.json"), L, "summary")
    if summ:
        for s in summ.get("cells", []):
            cid = s["cell"]["cell_id"]
            if cid in cell_rows and "summary" in cell_rows[cid] and s != cell_rows[cid]["summary"]:
                L.bad("summary", f"cell {cid} summary differs from the cell artifact")
        L.tick("summary_cells_compared", len(summ.get("cells", [])))
    # ---- declared fixture certificate (FX1), validity vs minimality separately
    fx = load(os.path.join(prod, "fixtures", "FX1_identity.json"), L, "FX1")
    if fx:
        fxL = Ledger()
        r = certificate(fx, fx["transitions"], fxL, "FX1")
        report["fixture_FX1"] = {"validity": r["validity"], "minimality": r["minimality"],
                                 "issues": fxL.invalid}
        L.invalid += fxL.invalid
    report["cells"] = {str(k): {kk: vv for kk, vv in v.items() if kk != "summary"} for k, v in cell_rows.items()}
    return finish(L, report, out)


def audit_cell(c, art, recs, tabs_all, cdecl, clos, L, where):
    n, N = c["n"], c["N"]
    tables = tabs_all[:1] if c["regime"] == "AUTO" else tabs_all
    if art.get("action_ids") != list(range(c["n_actions"])) or len(tables) != c["n_actions"]:
        L.bad(where, "action IDs")
    for k in ("model", "task", "regime"):
        if art.get(k) != c[k]:
            L.bad(where, f"{k} differs from declaration")
    h = [TASK[c["task"]](x, n) for x in range(N)]
    if art["outputs"] != h:
        L.bad(where, "outputs differ from the declared task")
    cert = certificate(art, tables, L, where)
    check_witnesses(art, tables, L, where)
    alpha = art["alpha"]
    K = max(alpha) + 1
    if c["primary"] and K == 1:
        L.bad(where, "K*=1 on a nonconstant primary task")
    # candidates, recomputed from saved alpha and tables with the audit's own check
    if cdecl is None:
        L.absent(where, "candidate declarations")
        return {"certificate": cert}
    decl, vecs = cdecl
    if len(recs) != c["n_candidates"]:
        L.absent(where, f"{c['n_candidates'] - len(recs)} candidate records") if len(recs) < c["n_candidates"] \
            else L.bad(where, "extra candidate records")
    mine = []
    for cand, a in zip(decl, vecs):
        key = (c["model"], cand["id"])
        if key not in clos:
            clos[key] = [determines(a, [a[t[x]] for x in range(N)]) for t in tabs_all]
        cl = clos[key][:len(tables)]
        dbad = determines(a, h)
        failing = [q for q, b in enumerate(cl) if b is not None]
        suff = dbad is None and not failing
        Kc = max(a) + 1
        mine.append({"candidate_id": cand["id"], "K_candidate": Kc, "decodable": dbad is None,
                     "decode_conflict": None if dbad is None else list(dbad), "closed": not failing,
                     "failing_actions": failing, "closure_witnesses": {str(q): list(cl[q]) for q in failing},
                     "task_sufficient": suff, "vec": tuple(a), "control": S.is_control(Kc, N)})
        m = mine[-1]
        if suff:
            if determines(a, alpha) is not None or Kc < K:
                L.bad(where, f"candidate {cand['id']}: sufficient but alpha* does not factor through it")
            m.update({"factors_through": True, "K_minus_Kstar": Kc - K, "K_ratio": frac(Kc, K),
                      "identical_to_optimum": list(a) == alpha})
        else:
            m.update({"factors_through": None, "K_minus_Kstar": None, "K_ratio": None,
                      "identical_to_optimum": None})
    L.tick("candidate_decisions_checked", len(mine))
    byid = {r.get("candidate_id"): r for r in recs}
    for m in mine:
        r = byid.get(m["candidate_id"])
        if r is None:
            continue
        if r.get("record_id") != c["cell_id"] * 1000 + m["candidate_id"]:
            L.bad(where, f"candidate {m['candidate_id']}: record_id")
        for k in ("K_candidate", "decodable", "decode_conflict", "closed", "failing_actions", "closure_witnesses",
                  "task_sufficient", "factors_through", "K_minus_Kstar", "K_ratio", "identical_to_optimum"):
            if r.get(k, "<absent>") != m[k]:
                L.bad(where, f"candidate {m['candidate_id']}: field {k}")
        if r.get("is_control") != m["control"]:
            L.bad(where, f"candidate {m['candidate_id']}: is_control")
        if not m["task_sufficient"] and not r.get("null_reason"):
            L.bad(where, f"candidate {m['candidate_id']}: failing row without a null reason")
        if m["task_sufficient"] and r.get("null_reason") is not None:
            L.bad(where, f"candidate {m['candidate_id']}: sufficient row carries a null reason")
    # summary numbers
    suff = [m for m in mine if m["task_sufficient"]]
    best = min(suff, key=lambda m: (m["K_candidate"], m["candidate_id"])) if suff else None
    nc = [m for m in suff if m["control"] is not True]
    bnc = min(nc, key=lambda m: (m["K_candidate"], m["candidate_id"])) if nc else None
    P0 = art["stages"][0]
    p0c = [determines(P0, [P0[t[x]] for x in range(N)]) for t in tables]
    ident = next(m for m, cd in zip(mine, decl) if cd["family"] == "C" and cd["g"] == "identity")
    fam = {cd["id"]: cd["family"] for cd in decl}
    exp_summary = {
        "cell": c, "N": N, "K0": max(P0) + 1, "K_star": K, "K_star_over_N": frac(K, N),
        "capacity_saving_bits": n - (K - 1).bit_length(), "strict_rounds": len(art["stages"]) - 2,
        "outcome": "EXACT_REDUCTION" if K < N else "NO_REDUCTION",
        "storage_entries_excluded_from_capacity": {
            "state_to_group_map": N, "decoder": K, "macro_transition_tables": len(tables) * K,
            "action_labels": len(tables), "micro_action_tables": len(tables) * N},
        "baselines": {
            "identity": {"candidate_id": ident["candidate_id"], "K": N, "task_sufficient": ident["task_sufficient"]},
            "output_partition_P0": {"K": max(P0) + 1, "closed": all(b is None for b in p0c),
                                    "failing_actions": [q for q, b in enumerate(p0c) if b is not None],
                                    "closure_witnesses": {str(q): list(b) for q, b in enumerate(p0c) if b is not None}},
            "alpha_star": {"K": K}},
        "candidates": {
            "raw": len(mine), "distinct_partitions": len({m["vec"] for m in mine}),
            "decodable_raw": sum(m["decodable"] for m in mine), "closed_raw": sum(m["closed"] for m in mine),
            "sufficient_raw": len(suff), "sufficient_distinct": len({m["vec"] for m in suff}),
            "matching_optimum_raw": sum(bool(m["identical_to_optimum"]) for m in suff),
            "matching_optimum_distinct": len({m["vec"] for m in suff if m["identical_to_optimum"]}),
            "best": None if best is None else {
                "candidate_id": best["candidate_id"], "K": best["K_candidate"],
                "K_minus_Kstar": best["K_minus_Kstar"], "family": fam[best["candidate_id"]]},
            "best_lossless_control_excluded": None if bnc is None else {
                "candidate_id": bnc["candidate_id"], "K": bnc["K_candidate"],
                "K_minus_Kstar": bnc["K_minus_Kstar"], "family": fam[bnc["candidate_id"]]},
            "comparison": None if best is None else
            ("MATCHES_OPTIMUM" if best["K_candidate"] == K else "CANDIDATE_GAP")}}
    if not ident["task_sufficient"]:
        L.bad(where, "identity control is not sufficient")
    if art.get("summary") != exp_summary:
        diff = sorted(k for k in exp_summary if (art.get("summary") or {}).get(k) != exp_summary[k])
        L.bad(where, f"reported numbers differ from audit recomputation: {diff}")
    return {"certificate": cert, "K_star": K, "summary": art.get("summary") if art.get("summary") == exp_summary
            else None, "n_candidates_audited": len(mine)}


def finish(L, report, out):
    os.makedirs(out)
    report.update({"status": label_status(len(L.invalid), len(L.missing)),
                   "n_invalid": len(L.invalid), "n_missing": len(L.missing),
                   "invalid": L.invalid, "missing": L.missing, "denominators": L.counts})
    with open(os.path.join(out, "audit.json"), "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
    print(f"status {report['status']} invalid {len(L.invalid)} missing {len(L.missing)} "
          f"denominators {json.dumps(L.counts, sort_keys=True)}")
    return 0 if report["status"] == "VALID_COMPLETE" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], "--bypass-integrity" in sys.argv[3:]))
