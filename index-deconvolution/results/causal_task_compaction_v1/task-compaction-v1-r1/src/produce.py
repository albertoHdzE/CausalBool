"""task-compaction-v1-r1 -- production orchestration (thin): declarations in, artifacts out.

Owns only serialization and orchestration. The minimizer, witness and replay are the
isolated owner's (deconvolution.minimal_task_partition / distinguishing_task_word /
task_word_path); fibre checks are the owner's induced_map; model tables and candidate
alpha values are the accepted study adapter's (study.Model.q_table, study.candidates,
study.alpha_value). Usage: python produce.py <fresh destination directory> [--dryrun]
(--dryrun runs the declared supplemental fixture SUP2 instead of M1-M4; it never touches M1-M4.)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.dirname(HERE)
ISO = os.path.join(RUN, "isolated", "index-deconvolution")
ISO_SRC = os.path.join(ISO, "src")
ISO_STUDY = os.path.join(ISO, "results", "causal_abstraction_validation", "abstraction-validation-v1-r1-source-r2")
sys.path[:0] = [ISO_SRC, ISO_STUDY]

import deconvolution as D  # noqa: E402
import study as S  # noqa: E402

TASKS = {"T0": lambda x, n: x & 1,
         "T1": lambda x, n: (x >> (n - 1)) & 1,
         "TP": lambda x, n: bin(x).count("1") % 2}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def dump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(obj, fh, sort_keys=True, separators=(",", ":"))
        fh.write("\n")


def frac(a, b):
    f = Fraction(a, b)
    return {"num": f.numerator, "den": f.denominator}


def ceil_log2(k):
    return (k - 1).bit_length()


def assert_imports(freeze):
    mods = {m.__name__: m for m in S.OWNER_MODULES}
    mods["study"] = S
    out = {}
    for name, m in sorted(mods.items()):
        p = os.path.realpath(m.__file__)
        if not p.startswith(os.path.realpath(ISO) + os.sep):
            raise RuntimeError(f"{name} resolved outside the isolated tree: {p}")
        rel = os.path.relpath(p, os.path.realpath(os.path.join(RUN, "isolated")))
        h = sha(p)
        if freeze["isolated"].get(rel) != h:
            raise RuntimeError(f"{name}: {rel} hash {h} differs from freeze")
        out[name] = {"path": rel, "sha256": h}
    return out


def first_split_pair(prev, nxt):
    """Lexicographically first x < y equal in prev and different in nxt."""
    blocks: dict = {}
    for x, b in enumerate(prev):
        blocks.setdefault(b, []).append(x)
    best = None
    for members in blocks.values():
        for i, x in enumerate(members):
            if best is not None and x >= best[0]:
                break
            y = next((y for y in members[i + 1:] if nxt[y] != nxt[x]), None)
            if y is not None:
                best = (x, y)
                break
    return best


def candidate_alphas(n):
    N = 2 ** n
    return [{"id": c["id"], "cand": c,
             "alpha": D.canonical_partition([S.alpha_value(c, x, n) for x in range(N)])}
            for c in S.candidates(n)]


def production_spec():
    """M1-M4 from the accepted study adapter at tau=1, Q = study.track_d_q(n) in order."""
    cases = json.load(open(os.path.join(RUN, "protocol", "CASES.json")))
    models = {}
    for mid in S.MODEL_IDS:
        m = S.Model(mid)
        acts = S.track_d_q(m.n)
        tabs = [m.q_table(q, 1) for q in acts]
        if tabs[0] != m.F:
            raise RuntimeError("T_id at tau=1 is not F")
        models[mid] = {"id": mid, "n": m.n, "N": m.N, "acts": acts, "tables": tabs}
    return cases, models


def hand_actions(F, n):
    """SUP2 dry-run only: PROTOCOL §2 action order built from F by formula, not by study."""
    N = 2 ** n
    tabs = [list(F)]
    tabs += [[F[(x & ~(1 << j)) | (c << j)] for x in range(N)] for j in range(n) for c in (0, 1)]
    tabs += [[F[x ^ (1 << j)] for x in range(N)] for j in range(n)]
    tabs += [[(F[x] & ~(1 << j)) | (c << j) for x in range(N)] for j in range(n) for c in (0, 1)]
    tabs += [[F[F[x]] for x in range(N)]]
    return tabs


def dryrun_spec():
    """SUP2 (fixtures.json): 3-bit counter FXA and 4-cell rule-150 ring FXB, 12 cells."""
    def r150(x):
        b = [(x >> (i % 4)) & 1 for i in range(4)]
        return sum((b[(i - 1) % 4] ^ b[i] ^ b[(i + 1) % 4]) << i for i in range(4))
    models = {"FXA": {"id": "FXA", "n": 3, "N": 8, "F": [(x + 1) % 8 for x in range(8)]},
              "FXB": {"id": "FXB", "n": 4, "N": 16, "F": [r150(x) for x in range(16)]}}
    for m in models.values():
        m["acts"] = S.track_d_q(m["n"])
        m["tables"] = hand_actions(m.pop("F"), m["n"])
    cells, k = [], 0
    for mid, m in models.items():
        for task in ("T0", "T1", "TP"):
            for reg in ("AUTO", "INTERVENTION"):
                cells.append({"cell_id": k, "model": mid, "n": m["n"], "N": m["N"], "task": task,
                              "regime": reg, "tau": 1, "n_actions": 1 if reg == "AUTO" else len(m["tables"]),
                              "n_candidates": len(S.candidates(m["n"])), "primary": reg == "INTERVENTION"})
                k += 1
    exp = {"cells": len(cells), "candidate_records": sum(c["n_candidates"] for c in cells),
           "distinct_model_action_tables": sum(len(m["tables"]) for m in models.values()),
           "distinct_model_state_action_entries": sum(len(m["tables"]) * m["N"] for m in models.values())}
    return {"run_id": "SUP2-dry-run", "cells": cells, "expected_counts": exp}, models


def closure(alpha, tables):
    """Per action: None if closed, else the smallest violating pair (owner's fibre check)."""
    res = []
    for t in tables:
        _, bad = D.induced_map(alpha, [alpha[t[x]] for x in range(len(alpha))])
        res.append(None if bad is None else list(bad))
    return res


def run_cell(cell, model, tables_all, cands, clos_cache):
    n, N = model["n"], model["N"]
    reg = cell["regime"]
    tables = tables_all[:1] if reg == "AUTO" else tables_all
    if len(tables) != cell["n_actions"]:
        raise RuntimeError(f"cell {cell['cell_id']}: {len(tables)} actions, declared {cell['n_actions']}")
    h = [TASKS[cell["task"]](x, n) for x in range(N)]
    r = D.minimal_task_partition(h, tables)
    stages, alpha, K = r["stages"], r["alpha"], r["K"]
    if stages[-1] != stages[-2] or any(stages[i] == stages[i + 1] for i in range(len(stages) - 2)):
        raise RuntimeError("stage chain not strictly refining until the first repeat")
    if cell["primary"] and K == 1:
        raise RuntimeError("K*=1 on a nonconstant primary task: harness failure")
    witnesses = []
    for d in range(r["strict_rounds"]):
        x, y = first_split_pair(stages[d], stages[d + 1])
        word = D.distinguishing_task_word(h, tables, stages, x, y)
        px, py = D.task_word_path(tables, x, word), D.task_word_path(tables, y, word)
        ox, oy = [h[s] for s in px], [h[s] for s in py]
        if len(word) != d + 1 or ox[-1] == oy[-1] or ox[:-1] != oy[:-1]:
            raise RuntimeError(f"witness replay failed at round {d}")
        witnesses.append({"round": d, "from_stage": d, "to_stage": d + 1, "x": x, "y": y,
                          "first_separation_stage": d + 1, "word": word,
                          "word_names": [S.q_name(model["acts"][q]) for q in word],
                          "path_x": px, "path_y": py, "outputs_x": ox, "outputs_y": oy})
    # candidates
    P0 = stages[0]
    p0_closure = closure(P0, tables)
    records = []
    for ca in cands:
        a = ca["alpha"]
        Kc = max(a) + 1
        _, dbad = D.induced_map(a, h)
        key = (model["id"], ca["id"])
        if key not in clos_cache:
            clos_cache[key] = closure(a, tables_all)
        cl = clos_cache[key][:len(tables)]
        failing = [q for q, b in enumerate(cl) if b is not None]
        suff = dbad is None and not failing
        rec = {"record_id": cell["cell_id"] * 1000 + ca["id"], "cell_id": cell["cell_id"],
               "candidate_id": ca["id"], "candidate": ca["cand"], "K_candidate": Kc,
               "decodable": dbad is None, "decode_conflict": None if dbad is None else list(dbad),
               "closed": not failing, "failing_actions": failing,
               "closure_witnesses": {str(q): cl[q] for q in failing},
               "task_sufficient": suff, "is_control": S.is_control(Kc, N)}
        if suff:
            fmap, fbad = D.induced_map(a, alpha)
            if fbad is not None or Kc < K:
                raise RuntimeError(f"theory defect: sufficient candidate {ca['id']} does not factor alpha*")
            rec.update({"factors_through": True, "K_minus_Kstar": Kc - K, "K_ratio": frac(Kc, K),
                        "identical_to_optimum": a == alpha, "null_reason": None})
        else:
            why = [w for w, bad in (("not decodable", dbad is not None), ("not closed", bool(failing))) if bad]
            rec.update({"factors_through": None, "K_minus_Kstar": None, "K_ratio": None,
                        "identical_to_optimum": None, "null_reason": " and ".join(why)})
        records.append(rec)
    suff = [rc for rc in records if rc["task_sufficient"]]
    best = min(suff, key=lambda rc: (rc["K_candidate"], rc["candidate_id"]))
    nonctl = [rc for rc in suff if rc["is_control"] is not True]
    best_nc = min(nonctl, key=lambda rc: (rc["K_candidate"], rc["candidate_id"])) if nonctl else None
    avec = {ca["id"]: tuple(ca["alpha"]) for ca in cands}
    ident = next(rc for rc in records if rc["candidate"]["family"] == "C" and rc["candidate"]["g"] == "identity")
    summary = {
        "cell": cell, "N": N, "K0": max(stages[0]) + 1, "K_star": K,
        "K_star_over_N": frac(K, N), "capacity_saving_bits": n - ceil_log2(K),
        "strict_rounds": r["strict_rounds"],
        "outcome": "EXACT_REDUCTION" if K < N else "NO_REDUCTION",
        "storage_entries_excluded_from_capacity": {
            "state_to_group_map": N, "decoder": K, "macro_transition_tables": len(tables) * K,
            "action_labels": len(tables), "micro_action_tables": len(tables) * N},
        "baselines": {
            "identity": {"candidate_id": ident["candidate_id"], "K": N, "task_sufficient": ident["task_sufficient"]},
            "output_partition_P0": {"K": max(P0) + 1, "closed": all(b is None for b in p0_closure),
                                    "failing_actions": [q for q, b in enumerate(p0_closure) if b is not None],
                                    "closure_witnesses": {str(q): b for q, b in enumerate(p0_closure) if b is not None}},
            "alpha_star": {"K": K}},
        "candidates": {
            "raw": len(records), "distinct_partitions": len({avec[rc["candidate_id"]] for rc in records}),
            "decodable_raw": sum(rc["decodable"] for rc in records),
            "closed_raw": sum(rc["closed"] for rc in records),
            "sufficient_raw": len(suff),
            "sufficient_distinct": len({avec[rc["candidate_id"]] for rc in suff}),
            "matching_optimum_raw": sum(bool(rc["identical_to_optimum"]) for rc in suff),
            "matching_optimum_distinct": len({avec[rc["candidate_id"]] for rc in suff if rc["identical_to_optimum"]}),
            "best": {"candidate_id": best["candidate_id"], "K": best["K_candidate"],
                     "K_minus_Kstar": best["K_minus_Kstar"], "family": best["candidate"]["family"]},
            "best_lossless_control_excluded": None if best_nc is None else {
                "candidate_id": best_nc["candidate_id"], "K": best_nc["K_candidate"],
                "K_minus_Kstar": best_nc["K_minus_Kstar"], "family": best_nc["candidate"]["family"]},
            "comparison": "MATCHES_OPTIMUM" if best["K_candidate"] == K else "CANDIDATE_GAP"},
    }
    cell_art = {"cell_id": cell["cell_id"], "model": cell["model"], "task": cell["task"],
                "regime": cell["regime"], "n": n, "N": N, "action_ids": list(range(len(tables))),
                "outputs": h, "alpha": alpha, "stages": stages, "strict_rounds": r["strict_rounds"],
                "representatives": r["representatives"], "decoder": r["decoder"], "macro": r["macro"],
                "coarsening": r["coarsening"], "witnesses": witnesses, "summary": summary}
    return cell_art, records


def main(dest, mode="production"):
    if os.path.exists(dest):
        print(f"refusing: {dest} exists")
        return 2
    t0 = time.time()
    if mode == "production":
        imports = assert_imports(json.load(open(os.path.join(RUN, "freeze.json"))))
        cases, models = production_spec()
    elif mode == "dryrun":
        imports = {m.__name__: {"path": os.path.realpath(m.__file__), "sha256": sha(m.__file__)}
                   for m in (D, S)}
        cases, models = dryrun_spec()
    else:
        raise ValueError(mode)
    os.makedirs(dest)
    dump(imports, os.path.join(dest, "imports.json"))
    dump({"mode": mode, **cases}, os.path.join(dest, "cases.json"))
    tables, cands, cost = {}, {}, {}
    n_tables = n_entries = 0
    for mid, m in models.items():
        t = time.time()
        tabs = m["tables"]
        tables[mid], cands[mid] = tabs, candidate_alphas(m["n"])
        n_tables += len(tabs)
        n_entries += len(tabs) * m["N"]
        dump({"model": mid, "n": m["n"], "N": m["N"], "tau": 1,
              "actions": [{"action_id": i, "name": S.q_name(q), **q} for i, q in enumerate(m["acts"])],
              "auto_action_ids": [0], "tables": tabs}, os.path.join(dest, "tables", f"{mid}.json"))
        dump({"model": mid, "candidates": [{"id": c["id"], "candidate": c["cand"], "alpha": c["alpha"]}
                                           for c in cands[mid]]},
             os.path.join(dest, "candidate_alphas", f"{mid}.json"))
        cost[f"tables_{mid}_s"] = round(time.time() - t, 3)
    exp = cases["expected_counts"]
    if (n_tables, n_entries) != (exp["distinct_model_action_tables"], exp["distinct_model_state_action_entries"]):
        raise RuntimeError(f"table counts {n_tables}/{n_entries} differ from declaration")
    clos_cache: dict = {}
    summaries, n_records = [], 0
    for cell in cases["cells"]:
        t = time.time()
        m = models[cell["model"]]
        if len(cands[cell["model"]]) != cell["n_candidates"]:
            raise RuntimeError("candidate count differs from declaration")
        art, recs = run_cell(cell, m, tables[cell["model"]], cands[cell["model"]], clos_cache)
        dump(art, os.path.join(dest, "cells", f"cell_{cell['cell_id']:02d}.json"))
        path = os.path.join(dest, "candidates", f"cell_{cell['cell_id']:02d}.jsonl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            for rc in recs:
                fh.write(json.dumps(rc, sort_keys=True, separators=(",", ":")) + "\n")
        n_records += len(recs)
        summaries.append(art["summary"])
        cost[f"cell_{cell['cell_id']:02d}_s"] = round(time.time() - t, 3)
    if n_records != exp["candidate_records"]:
        raise RuntimeError(f"{n_records} candidate records, declared {exp['candidate_records']}")
    refine = []
    for s in summaries:
        if s["cell"]["regime"] == "INTERVENTION":
            auto = next(a for a in summaries if a["cell"]["regime"] == "AUTO"
                        and a["cell"]["model"] == s["cell"]["model"] and a["cell"]["task"] == s["cell"]["task"])
            ia = json.load(open(os.path.join(dest, "cells", f"cell_{s['cell']['cell_id']:02d}.json")))["alpha"]
            aa = json.load(open(os.path.join(dest, "cells", f"cell_{auto['cell']['cell_id']:02d}.json")))["alpha"]
            ok = D.induced_map(ia, aa)[1] is None and s["K_star"] >= auto["K_star"]
            refine.append({"intervention_cell": s["cell"]["cell_id"], "auto_cell": auto["cell"]["cell_id"],
                           "refines": ok})
            if not ok:
                raise RuntimeError("INTERVENTION optimum does not refine AUTO")
    # declared fixture artifact for the audit's certificate probes (FX1, computed by the owner)
    fx = {f["id"]: f for f in json.load(open(os.path.join(RUN, "fixtures.json")))["fixtures"]}["FX1_identity"]
    r = D.minimal_task_partition(fx["outputs"], fx["transitions"])
    dump({"fixture_id": "FX1_identity", "outputs": fx["outputs"], "transitions": fx["transitions"], **r},
         os.path.join(dest, "fixtures", "FX1_identity.json"))
    dump({"n_cells": len(summaries), "n_candidate_records": n_records, "n_action_tables": n_tables,
          "n_state_action_entries": n_entries, "cells": summaries, "intervention_refines_auto": refine},
         os.path.join(dest, "summary.json"))
    seal = {}
    for d, _, fs in os.walk(dest):
        for f in fs:
            p = os.path.join(d, f)
            seal[os.path.relpath(p, dest)] = sha(p)
    dump({"files": len(seal), "sha256": seal}, os.path.join(dest, "seal.json"))
    cost["total_s"] = round(time.time() - t0, 3)
    with open(os.path.join(dest, "cost.json"), "w") as fh:
        json.dump(cost, fh, indent=1, sort_keys=True)
    print(f"cells {len(summaries)} records {n_records} tables {n_tables} entries {n_entries} "
          f"sealed {len(seal)} files in {cost['total_s']} s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], *(["dryrun"] if sys.argv[2:] == ["--dryrun"] else [])))
