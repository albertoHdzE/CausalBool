"""task-compaction-v1 finalization -- revised evidence audit (run-local revision r3).

A separately identified revision. It replaces neither the frozen
../../../task-compaction-v1-r1/src/audit.py nor the closure's audit_r2.py; both are imported
by path and verified by SHA-256 before use:

  * frozen audit.py  -- the independent scientific primitives (certificate, check_witnesses,
                        audit_tables, hand_fixture_checks, determines, frac, TASK) and,
                        through its own sys.path entry, the accepted study declarations;
  * audit_r2.py      -- the parsing layer (NaN/Infinity rejected, per-line JSONL), the seal
                        check and the structural schema helpers;
  * expected_r3.py   -- the expected-value authority: the frozen audit_cell's calculation,
                        refactored to RETURN the expected candidate records and per-cell
                        summary. The frozen audit_cell itself is NOT called here.

What r3 adds is the FIELD INVENTORY (FIELD_INVENTORY.md): every scientific field consumed is
declared with its exact type, shape, range and nullability, and is compared TYPE-EXACTLY
(1, 1.0 and True stay distinct) against the independently recomputed value, recursively.
Two saved copies are never compared only with each other: summary.json rows and the cell
artifact's summary are each compared with the expected summary.

Semantics. Absent file or absent record => missing evidence (INCOMPLETE). Present but
malformed, missing a required field, carrying an undeclared field, or contradicting the
independent value => INVALID, with the field path. INVALID outranks INCOMPLETE; both lists
survive; checks that do not depend on the failed item continue. No blanket exception handler.

Historical identities. --inputs-root DIR resolves the freeze.json `inputs` group under DIR
(the immutable finalization/historical_inputs snapshot) instead of the current repository;
`isolated` and `run_files` always resolve to the ORIGINAL run. Under an explicit root the
file set must equal the declared set exactly. The root that supplied each group is recorded.

Usage: python audit_r3.py <production dir> <audit out dir> [--bypass-integrity] [--inputs-root DIR]
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
FIN = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(FIN, *[".."] * 5))
BASE = os.path.join(REPO, "index-deconvolution", "results", "causal_task_compaction_v1")
ORIG_RUN = os.path.join(BASE, "task-compaction-v1-r1")
ORIG_ISO = os.path.join(ORIG_RUN, "isolated")
R2_PATH = os.path.join(BASE, "review_closure", "task-compaction-v1-r1", "src", "audit_r2.py")
PINNED = {"audit_r2.py": (R2_PATH, "9e8c927c56936e5a3d251efc05006d88bdd2557568af86470b67dc2d4fae093d"),
          "frozen audit.py": (os.path.join(ORIG_RUN, "src", "audit.py"),
                              "3198a65679b51f30d7a517d28b0908f2f13602e18b159e48701fe03c9bd20b39"),
          "freeze.json": (os.path.join(ORIG_RUN, "freeze.json"),
                          "7d94e3197de8a1159d44b6c082abe0214b8e10cd506bcbfb8adbf30247af578c")}


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


for _name, (_p, _h) in PINNED.items():
    if sha(_p) != _h:
        raise SystemExit(f"pinned identity mismatch: {_name}")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R2 = _load("audit_r2_closure", R2_PATH)        # loads the frozen audit once, hash-checked
A = R2.A
S = A.S
E = _load("expected_r3", os.path.join(HERE, "expected_r3.py"))
with open(PINNED["freeze.json"][0]) as _fh:
    FREEZE = json.load(_fh)
CELL_FIELDS = frozenset(FREEZE["schema"]["cell_fields"])
RECORD_FIELDS = tuple(FREEZE["schema"]["record_fields"])
SCIENTIFIC_MODULES = ("study", "deconvolution", "causalbool", "bnet", "ca_deconvolution", "reprogramming")
WITNESS_FIELDS = frozenset({"round", "from_stage", "to_stage", "first_separation_stage", "x", "y", "word",
                            "word_names", "path_x", "path_y", "outputs_x", "outputs_y"})
TABLE_FIELDS = frozenset({"model", "n", "N", "tau", "auto_action_ids", "actions", "tables"})
ACTION_FIELDS = frozenset({"action_id", "op", "j", "c", "name"})
CALPHA_FIELDS, CALPHA_ENTRY = frozenset({"model", "candidates"}), frozenset({"id", "candidate", "alpha"})
FX_FIELDS = frozenset({"fixture_id", "K", "transitions", "outputs", "stages", "alpha", "decoder", "macro",
                       "representatives", "strict_rounds", "coarsening"})
SUMMARY_FIELDS = frozenset({"cells", "intervention_refines_auto", "n_cells", "n_candidate_records",
                            "n_action_tables", "n_state_action_entries"})
is_int, int_vec, load_json, load_jsonl = R2.is_int, R2.int_vec, R2.load_json, R2.load_jsonl


class Ledger(R2.Ledger):
    def bad_field(self, where, field, reason):
        self.invalid.append({"where": where, "field": field, "check": reason})


# ---------------------------------------------------------------------- type-exact comparison
def first_diff(saved, exp, path):
    """(path, reason) of the first type-exact difference, recursively; None when identical."""
    if type(saved) is not type(exp):
        return path, f"type {type(saved).__name__} != expected {type(exp).__name__}"
    if isinstance(exp, dict):
        for k in sorted(set(saved) | set(exp)):
            if k not in saved:
                return f"{path}.{k}", "missing required field"
            if k not in exp:
                return f"{path}.{k}", "undeclared field"
            d = first_diff(saved[k], exp[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(exp, list):
        if len(saved) != len(exp):
            return path, f"length {len(saved)} != expected {len(exp)}"
        for i, (s, e) in enumerate(zip(saved, exp)):
            d = first_diff(s, e, f"{path}[{i}]")
            if d:
                return d
        return None
    if saved != exp:
        return path, f"value {saved!r} != expected {exp!r}"
    return None


def strict(L, where, saved, exp, path):
    d = first_diff(saved, exp, path)
    if d:
        L.bad_field(where, d[0], d[1])
    return d is None


def inventory(L, where, obj, declared, path):
    """Exact key set: a missing required field and an undeclared field are both INVALID."""
    ok = True
    for k in sorted(declared - set(obj)):
        L.bad_field(where, f"{path}.{k}", "missing required field")
        ok = False
    for k in sorted(set(obj) - declared):
        L.bad_field(where, f"{path}.{k}", "undeclared field")
        ok = False
    return ok


# ---------------------------------------------------------------------- record schema (independent of expectations)
def pair(v, N):
    return int_vec(v, 2, 0, N) and v[0] < v[1]


def schema_record(r, c, n_tables):
    """[(field, reason)] for one candidate record: types, shapes, ranges, nullability."""
    N, out = c["N"], []
    for k in RECORD_FIELDS:
        if k not in r:
            out.append((k, "missing required field"))
    out += [(k, "undeclared field") for k in sorted(set(r) - set(RECORD_FIELDS))]
    g = r.get

    def need(k, ok, why):
        if k in r and not ok:
            out.append((k, why))
    for k in ("record_id", "cell_id", "candidate_id"):
        need(k, is_int(g(k)) and g(k) >= 0, "non-negative built-in int required")
    need("candidate", isinstance(g("candidate"), dict) and all(
        isinstance(k, str) and (type(v) is str or is_int(v)) for k, v in g("candidate", {}).items()),
        "descriptor object of str/int values required")
    need("K_candidate", is_int(g("K_candidate")) and 1 <= g("K_candidate") <= N, "int in [1, N] required")
    for k in ("decodable", "closed", "task_sufficient", "is_control"):
        need(k, type(g(k)) is bool, "bool required")
    need("failing_actions", int_vec(g("failing_actions"), None, 0, n_tables)
         and g("failing_actions") == sorted(set(g("failing_actions"))), "increasing action indices required")
    cw = g("closure_witnesses")
    need("closure_witnesses", isinstance(cw, dict) and all(
        isinstance(k, str) and k.isdigit() and str(int(k)) == k and int(k) < n_tables and pair(v, N)
        for k, v in (cw or {}).items()), "map action-index string -> state pair required")
    if type(g("decodable")) is bool:
        need("decode_conflict", g("decode_conflict") is None if g("decodable") else pair(g("decode_conflict"), N),
             "null iff decodable, else a state pair")
    ts = g("task_sufficient")
    if type(ts) is bool:
        need("factors_through", (g("factors_through") is True) if ts else g("factors_through") is None,
             "true iff task_sufficient, else null")
        need("K_minus_Kstar", (is_int(g("K_minus_Kstar")) and g("K_minus_Kstar") >= 0) if ts
             else g("K_minus_Kstar") is None, "non-negative int iff task_sufficient, else null")
        kr = g("K_ratio")
        need("K_ratio", (isinstance(kr, dict) and set(kr) == {"num", "den"} and is_int(kr["num"])
                         and is_int(kr["den"]) and kr["num"] > 0 and kr["den"] > 0) if ts else kr is None,
             "{num:int>0, den:int>0} iff task_sufficient, else null")
        need("identical_to_optimum", type(g("identical_to_optimum")) is bool if ts
             else g("identical_to_optimum") is None, "bool iff task_sufficient, else null")
        nr = g("null_reason")
        need("null_reason", nr is None if ts else (type(nr) is str and nr != ""),
             "null iff task_sufficient, else a non-empty string")
    return out


# ---------------------------------------------------------------------- integrity of frozen identities
def check_freeze(L, report, inputs_root):
    label = "current_repository" if inputs_root is None else \
        "explicit_root:" + os.path.relpath(os.path.abspath(inputs_root), REPO)
    roots = {"isolated": (ORIG_ISO, "original_run/isolated"), "run_files": (ORIG_RUN, "original_run"),
             "inputs": (REPO if inputs_root is None else os.path.abspath(inputs_root), label)}
    fz, out, n = FREEZE, {}, 0
    for group, (root, lab) in roots.items():
        g = {"root": lab, "declared": len(fz[group]), "absent": [], "mismatch": [], "extra": []}
        for k, v in sorted(fz[group].items()):
            p = os.path.join(root, k)
            n += 1
            if not os.path.isfile(p):
                g["absent"].append(k)
                L.absent("freeze", f"{group}/{k} under {lab}")
            elif sha(p) != v:
                g["mismatch"].append(k)
                L.bad("freeze", f"identity mismatch {group}/{k} under {lab}")
        if group == "inputs" and inputs_root is not None:     # exact set: no substitution
            have = {os.path.relpath(os.path.join(dp, f), root) for dp, _, fs in os.walk(root) for f in fs}
            g["extra"] = sorted(have - set(fz[group]))
            for k in g["extra"]:
                L.bad("freeze", f"undeclared file in explicit inputs root: {k}")
        out[group] = g
    L.tick("frozen_identities_checked", n)
    L.intended["frozen_identities_checked"] = n
    report["freeze_roots"] = out


def source_resolution(L, report):
    """Every scientific module the frozen checks import must come from the ORIGINAL isolated copy."""
    res = {}
    for m in SCIENTIFIC_MODULES:
        f = getattr(sys.modules.get(m), "__file__", None)
        rel = None if f is None else os.path.relpath(os.path.abspath(f), ORIG_RUN)
        res[m] = rel
        if f is None or not os.path.abspath(f).startswith(ORIG_ISO + os.sep):
            L.bad("source_resolution", f"module {m} resolves outside the original isolated copy: {rel}")
    report["source_resolution"] = res


# ---------------------------------------------------------------------- pipeline
def main(prod, out, bypass=False, inputs_root=None):
    if os.path.exists(out):
        print(f"refusing: {out} exists")
        return 2
    L = Ledger()
    report = {"audit_revision": "r3", "bypass_integrity": bypass,
              "source_identity": {"audit_r3.py": sha(os.path.abspath(__file__)),
                                  "expected_r3.py": sha(os.path.join(HERE, "expected_r3.py")),
                                  **{k: v[1] for k, v in PINNED.items()}}}
    source_resolution(L, report)
    R2.check_seal(prod, L, bypass, report)
    st, cases = load_json(os.path.join(prod, "cases.json"), L, "cases")
    if st != "ok" or not R2.schema_cases(cases, L):
        report["not_evaluated"] = "every cell check: cases.json unavailable or malformed"
        return finish(L, report, out)
    report["mode"] = mode = cases.get("mode")
    if mode != "production":
        L.bad_field("cases", "mode", "production required")
        return finish(L, report, out)
    check_freeze(L, report, inputs_root)
    st, declared = load_json(os.path.join(ORIG_RUN, "protocol", "CASES.json"), L, "protocol")
    if st == "ok":
        strict(L, "cases", cases["cells"], declared["cells"], "cells")
        strict(L, "cases", cases["expected_counts"], declared["expected_counts"], "expected_counts")
    exp, cells = cases["expected_counts"], cases["cells"]
    ids = [c["cell_id"] for c in cells]
    if ids != list(range(len(cells))) or len(cells) != exp.get("cells"):
        L.bad("cases", "cell ID set")
    acts_by_model, by_model = {}, {}
    for c in cells:
        acts_by_model[c["model"]] = max(acts_by_model.get(c["model"], 0), c["n_actions"])
        by_model.setdefault(c["model"], {(c["n"], c["N"], c["tau"])}).add((c["n"], c["N"], c["tau"]))
    for mid, v in by_model.items():
        if len(v) != 1:
            L.bad("cases", f"model {mid}: cells disagree on n/N/tau")
    dims = {mid: next(iter(v)) for mid, v in by_model.items()}
    n_rec = sum(c["n_candidates"] for c in cells)
    L.intended.update({
        "cells": len(cells), "summary_rows": len(cells), "cell_summaries_compared": len(cells),
        "candidate_records": n_rec, "candidate_decisions_checked": n_rec,
        "record_fields_compared_exact": n_rec * (len(RECORD_FIELDS) - 1),
        "record_null_reason_typed_rule": n_rec,
        "action_tables": sum(acts_by_model.values()),
        "transition_entries_owner_checked": sum(acts_by_model[m] * dims[m][1] for m in acts_by_model)})
    for k, ek in (("action_tables", "distinct_model_action_tables"),
                  ("transition_entries_owner_checked", "distinct_model_state_action_entries"),
                  ("candidate_records", "candidate_records")):
        if L.intended[k] != exp.get(ek):
            L.bad("cases", f"declared {ek} {exp.get(ek)} != {L.intended[k]} implied by the cells")

    # ---- tables: inventory and declarations type-exactly, then the frozen range/owner checks
    T = {}
    for mid in sorted(acts_by_model):
        st, t = load_json(os.path.join(prod, "tables", f"{mid}.json"), L, mid)
        if st == "ok" and not R2.schema_table(t, mid):
            L.bad(mid, "schema: table file")
            st = "invalid"
        if st == "ok":
            n, N, tau = dims[mid]
            acts = S.track_d_q(n)
            ok = inventory(L, mid, t, TABLE_FIELDS, "table")
            ok &= strict(L, mid, t.get("model"), mid, "table.model")
            ok &= strict(L, mid, t.get("n"), n, "table.n") & strict(L, mid, t.get("N"), N, "table.N")
            ok &= strict(L, mid, t.get("tau"), tau, "table.tau")
            ok &= strict(L, mid, t.get("auto_action_ids"), [0], "table.auto_action_ids")
            if len(t["actions"]) == len(acts):
                for q, (a, d) in enumerate(zip(t["actions"], acts)):
                    ok &= inventory(L, mid, a, ACTION_FIELDS, f"actions[{q}]")
                    ok &= strict(L, mid, {k: a.get(k) for k in ("action_id", "op", "j", "c", "name")},
                                 {"action_id": q, **d, "name": S.q_name(d)}, f"actions[{q}]")
            if not ok:
                st = "invalid"
        if st == "ok":
            T[mid] = t
        else:
            L.skip(mid, "transition-table checks and every cell of this model", f"table {st}")
    tabs = A.audit_tables(T, mode, L)
    for mid in sorted(T):
        if mid not in tabs:
            L.skip(mid, "every cell of this model", "table failed its dimension/range check")
    report["tables"] = {"intended": L.intended["action_tables"],
                        "available": sum(len(v) for v in tabs.values()),
                        "state_action_entries_available": sum(len(v) * len(v[0]) for v in tabs.values())}
    L.tick("action_tables", report["tables"]["available"])
    report["hand_fixtures"] = A.hand_fixture_checks(L)

    # ---- candidate declarations: descriptors and ids type-exactly, alpha vectors recomputed
    calpha = {}
    for mid in sorted(acts_by_model):
        where = f"{mid}/candidate_alphas"
        st, ca = load_json(os.path.join(prod, "candidate_alphas", f"{mid}.json"), L, where)
        if st == "ok" and not R2.schema_candidate_alphas(ca, dims[mid][1]):
            L.bad(where, "schema: candidate alpha file")
            st = "invalid"
        if st == "ok":
            n = dims[mid][0]
            decl = S.candidates(n)
            mine = [A.first_appearance([S.alpha_value(c, x, n) for x in range(2 ** n)]) for c in decl]
            ok = inventory(L, where, ca, CALPHA_FIELDS, "file") & strict(L, where, ca.get("model"), mid, "model")
            if len(ca["candidates"]) != len(decl):
                L.bad_field(where, "candidates", f"length {len(ca['candidates'])} != declared {len(decl)}")
                ok = False
            else:
                for k, (e, d, a) in enumerate(zip(ca["candidates"], decl, mine)):
                    ok &= inventory(L, where, e, CALPHA_ENTRY, f"candidates[{k}]")
                    ok &= strict(L, where, e.get("id"), d["id"], f"candidates[{k}].id")
                    ok &= strict(L, where, e.get("candidate"), d, f"candidates[{k}].candidate")
                    ok &= strict(L, where, e.get("alpha"), a, f"candidates[{k}].alpha")
            st = "ok" if ok else "invalid"
            L.tick("candidate_vectors_checked", len(decl))
        if st != "ok":
            L.skip(mid, "candidate decisions of this model", f"candidate alphas {st}")
            continue
        calpha[mid] = (decl, mine)

    # ---- cells
    present = set(os.listdir(os.path.join(prod, "cells"))) if os.path.isdir(os.path.join(prod, "cells")) else set()
    for f in sorted(present - {f"cell_{i:02d}.json" for i in ids}):
        L.bad(f, "undeclared cell artifact")
    rows, alphas, clos = {}, {}, {}
    for c in cells:
        rows[c["cell_id"]] = audit_cell_r3(prod, c, present, tabs, calpha, clos, alphas, L)
    L.tick("cells", sum(1 for r in rows.values() if "certificate" in r))
    got = L.counts.get("candidate_records", 0)
    if got < n_rec:
        L.absent("candidates", f"{n_rec - got} declared records absent or unusable")
    report["candidate_records"] = {"declared": n_rec, "present_valid": got}

    # ---- cross-cell: INTERVENTION refines AUTO
    refine = []
    for c in cells:
        if c["regime"] != "INTERVENTION":
            continue
        a = next((x for x in cells if x["model"] == c["model"] and x["task"] == c["task"]
                  and x["regime"] == "AUTO"), None)
        if a is None:
            L.bad("cases", f"cell {c['cell_id']}: no AUTO partner declared")
        elif c["cell_id"] in alphas and a["cell_id"] in alphas:
            ai, aa = alphas[c["cell_id"]], alphas[a["cell_id"]]
            ok = A.determines(ai, aa) is None and max(ai) >= max(aa)
            refine.append({"intervention_cell": c["cell_id"], "auto_cell": a["cell_id"], "refines": ok})
            L.tick("refinement_pairs_checked")
            if not ok:
                L.bad(f"cell_{c['cell_id']:02d}", "INTERVENTION optimum does not refine AUTO")
        else:
            L.skip(f"cell_{c['cell_id']:02d}", "INTERVENTION-refines-AUTO", "a cell of the pair is unavailable")
    L.intended["refinement_pairs_checked"] = sum(c["regime"] == "INTERVENTION" for c in cells)
    report["intervention_refines_auto"] = refine
    check_summary(prod, cells, rows, refine, L)
    check_fixture(prod, L, report)
    report["cells"] = {str(k): {kk: vv for kk, vv in v.items() if kk != "expected_summary"} for k, v in rows.items()}
    report["aggregates"] = aggregates(cells, rows) if not (L.invalid or L.missing) else \
        {"evaluated": False, "reason": "withheld: the audit is not VALID_COMPLETE"}
    return finish(L, report, out)


def audit_cell_r3(prod, c, present, tabs, calpha, clos, alphas, L):
    cid, where = c["cell_id"], f"cell_{c['cell_id']:02d}"
    ni, nm = len(L.invalid), len(L.missing)
    n_tables = c["n_actions"]
    # candidate records: identity and typed schema, independent of the certificate
    _, raw = load_jsonl(os.path.join(prod, "candidates", f"{where}.jsonl"), L, where)
    recs, seen = {}, set()
    for k, r in enumerate(raw):
        if not isinstance(r, dict):
            L.bad_field(where, f"record[{k}]", "record is not an object")
            continue
        issues = schema_record(r, c, n_tables)
        for f, why in issues:
            L.bad_field(where, f"record[{k}].{f}", why)
        bad = {f for f, _ in issues}
        if bad & {"record_id", "candidate_id", "cell_id"}:
            continue                                   # identity unusable: cannot be bound
        if r["record_id"] in seen:
            L.bad_field(where, f"record[{k}].record_id", f"duplicate {r['record_id']}")
            continue
        if r["record_id"] != cid * 1000 + r["candidate_id"] or not 0 <= r["candidate_id"] < c["n_candidates"]:
            L.bad_field(where, f"record[{k}].record_id", f"undeclared record_id {r['record_id']}")
            continue
        if r["cell_id"] != cid:
            L.bad_field(where, f"record[{k}].cell_id", f"value {r['cell_id']} != declared cell {cid}")
            bad.add("cell_id")
        seen.add(r["record_id"])
        recs[r["candidate_id"]] = (r, bad)
    L.tick("candidate_records", len(recs))
    row = {}
    st, art = "missing", None
    if f"{where}.json" in present:
        st, art = load_json(os.path.join(prod, "cells", f"{where}.json"), L, where)
    else:
        L.absent(where, "cell artifact")
    if st == "ok":
        why = R2.schema_cell(art, c, n_tables)
        ok = why is None
        if why:
            L.bad(where, f"schema: {why}")
        ok &= inventory(L, where, art, CELL_FIELDS, "cell")
        if ok:
            for k in ("cell_id", "model", "task", "regime", "n", "N"):
                ok &= strict(L, where, art[k], c[k], f"cell.{k}")
            ok &= strict(L, where, art["action_ids"], list(range(n_tables)), "cell.action_ids")
            ok &= strict(L, where, art["outputs"], E.expected_outputs(A, c), "cell.outputs")
            for k in ("coarsening", "witnesses"):
                if art[k] is None:
                    L.bad_field(where, f"cell.{k}", "null where a value is required")
                    ok = False
            if ok:
                ok &= schema_witness_extras(art, c, L, where)
        st = "ok" if ok else "invalid"
    if st != "ok" or c["model"] not in tabs:
        L.skip(where, "certificate, witness, candidate and summary checks",
               f"cell artifact {st}" if st != "ok" else "model tables unavailable")
        row["status"] = A.label_status(len(L.invalid) - ni, len(L.missing) - nm)
        return row
    tabs_all = tabs[c["model"]]
    tables = E.regime_tables(c, tabs_all)
    if len(tables) != n_tables:
        L.bad(where, "action IDs")
    row["certificate"] = A.certificate(art, tables, L, where)
    A.check_witnesses(art, tables, L, where)
    alpha = art["alpha"]
    K = max(alpha) + 1
    row["K_star"] = K
    alphas[cid] = alpha
    if c["primary"] and K == 1:
        L.bad(where, "K*=1 on a nonconstant primary task")
    if c["model"] not in calpha:
        L.skip(where, "candidate decisions and summary", "candidate declarations unavailable")
        L.absent(where, "candidate declarations")
        row["status"] = A.label_status(len(L.invalid) - ni, len(L.missing) - nm)
        return row
    decl, vecs = calpha[c["model"]]
    exp_rows = E.expected_candidates(A, c, alpha, tabs_all, decl, vecs, clos)
    for e, _, theorem in exp_rows:
        if theorem is False:
            L.bad(where, f"candidate {e['candidate_id']}: sufficient but alpha* does not factor through it")
        got = recs.get(e["candidate_id"])
        if got is None:
            continue
        r, bad = got
        for f in RECORD_FIELDS:
            if f in bad or f == "null_reason":          # schema already failed / typed rule only
                continue
            strict(L, where, r[f], e[f], f"candidate[{e['candidate_id']}].{f}")
            L.tick("record_fields_compared_exact")
        L.tick("record_null_reason_typed_rule", "null_reason" not in bad)
    L.tick("candidate_decisions_checked", len(exp_rows))
    exp_summary = E.expected_summary(A, c, art["stages"], alpha, tabs_all, decl, exp_rows)
    if not next(e for e, _, _ in exp_rows if e["candidate_id"] == exp_summary["baselines"]["identity"]["candidate_id"])[
            "task_sufficient"]:
        L.bad(where, "identity control is not sufficient")
    strict(L, where, art["summary"], exp_summary, "cell.summary")
    L.tick("cell_summaries_compared")
    row["expected_summary"] = exp_summary
    row["n_candidates_audited"] = len(exp_rows)
    row["status"] = A.label_status(len(L.invalid) - ni, len(L.missing) - nm)
    return row


def schema_witness_extras(art, c, L, where):
    """Witness field inventory and the bookkeeping fields the frozen replay does not read."""
    acts, ok = S.track_d_q(c["n"]), True
    for i, w in enumerate(art["witnesses"]):
        ok &= inventory(L, where, w, WITNESS_FIELDS, f"witnesses[{i}]")
        if not ok:
            continue
        d = w["round"]
        ok &= strict(L, where, w["from_stage"], d, f"witnesses[{i}].from_stage")
        ok &= strict(L, where, w["to_stage"], d + 1, f"witnesses[{i}].to_stage")
        ok &= strict(L, where, w["first_separation_stage"], len(w["word"]), f"witnesses[{i}].first_separation_stage")
        ok &= strict(L, where, w["word_names"], [S.q_name(acts[q]) for q in w["word"]], f"witnesses[{i}].word_names")
    return ok


def check_summary(prod, cells, rows, refine, L):
    st, summ = load_json(os.path.join(prod, "summary.json"), L, "summary")
    if st != "ok":
        L.skip("summary", "summary rows", f"summary.json {st}")
        return
    if not (isinstance(summ, dict) and isinstance(summ.get("cells"), list)):
        L.bad("summary", "schema: summary.cells")
        return
    inventory(L, "summary", summ, SUMMARY_FIELDS, "summary")
    declared = {c["cell_id"] for c in cells}
    seen, compared = set(), 0
    for k, s in enumerate(summ["cells"]):
        cid = s.get("cell", {}).get("cell_id") if isinstance(s, dict) and isinstance(s.get("cell"), dict) else None
        if not is_int(cid):
            L.bad_field("summary", f"cells[{k}].cell.cell_id", "missing or non-integer")
            continue
        if cid in seen or cid not in declared:
            L.bad_field("summary", f"cells[{k}].cell.cell_id", f"duplicate or undeclared cell {cid}")
            continue
        seen.add(cid)
        ref = rows.get(cid, {}).get("expected_summary")
        if ref is None:
            L.skip("summary", f"row for cell {cid}", "its independent expectation is unavailable")
            continue
        strict(L, "summary", s, ref, f"cells[{k}]")          # against the INDEPENDENT value
        compared += 1
    L.tick("summary_rows", compared)
    for cid in sorted(declared - seen):
        L.absent("summary", f"row for cell {cid}")
    top = {"n_cells": len(cells), "n_candidate_records": L.intended["candidate_records"],
           "n_action_tables": L.intended["action_tables"],
           "n_state_action_entries": L.intended["transition_entries_owner_checked"]}
    for f, v in top.items():
        if f in summ:
            strict(L, "summary", summ[f], v, f)
    if "intervention_refines_auto" in summ:
        if len(refine) == L.intended["refinement_pairs_checked"]:
            strict(L, "summary", summ["intervention_refines_auto"], refine, "intervention_refines_auto")
        else:
            L.skip("summary", "top-level intervention_refines_auto", "not every pair was available")


def check_fixture(prod, L, report):
    st, fx = load_json(os.path.join(prod, "fixtures", "FX1_identity.json"), L, "FX1")
    if st != "ok":
        return
    tr = fx.get("transitions") if isinstance(fx, dict) else None
    N = len(tr[0]) if isinstance(tr, list) and tr and isinstance(tr[0], list) else 0
    if not (N and all(int_vec(t, N, 0, N) for t in tr)) or R2.schema_certificate(fx, N, len(tr)):
        L.bad("FX1", "schema: fixture certificate")
        return
    ok = inventory(L, "FX1", fx, FX_FIELDS, "fixture") & (type(fx.get("fixture_id")) is str)
    ok &= strict(L, "FX1", fx.get("K"), max(fx["alpha"]) + 1, "fixture.K")
    if not ok:
        return
    fxL = A.Ledger()
    r = A.certificate(fx, tr, fxL, "FX1")
    report["fixture_FX1"] = {"validity": r["validity"], "minimality": r["minimality"], "issues": fxL.invalid}
    L.invalid += fxL.invalid


def aggregates(cells, rows):
    """Outcome counts per regime from the INDEPENDENT summaries of a complete valid audit."""
    agg = {}
    for c in cells:
        s = rows[c["cell_id"]]["expected_summary"]
        g = agg.setdefault(c["regime"], {"cells": 0, "EXACT_REDUCTION": 0, "NO_REDUCTION": 0,
                                         "MATCHES_OPTIMUM": 0, "CANDIDATE_GAP": 0, "no_sufficient_candidate": 0})
        g["cells"] += 1
        g[s["outcome"]] += 1
        g[s["candidates"]["comparison"] or "no_sufficient_candidate"] += 1
    return {"evaluated": True, "by_regime": agg}


def finish(L, report, out):
    os.makedirs(out)
    status = A.label_status(len(L.invalid), len(L.missing))
    counts = {k: {"intended": L.intended.get(k), "performed": v} for k, v in sorted(L.counts.items())}
    for k in sorted(set(L.intended) - set(L.counts)):
        counts[k] = {"intended": L.intended[k], "performed": 0}
    report.update({"status": status, "n_invalid": len(L.invalid), "n_missing": len(L.missing),
                   "invalid": L.invalid, "missing": L.missing, "skipped": L.skipped, "counts": counts})
    with open(os.path.join(out, "audit.json"), "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
    print(f"status {status} invalid {len(L.invalid)} missing {len(L.missing)} skipped {len(L.skipped)}")
    return 0 if status == "VALID_COMPLETE" else 1


def _args(argv):
    root = None
    if "--inputs-root" in argv:
        root = argv[argv.index("--inputs-root") + 1]
    return argv[0], argv[1], "--bypass-integrity" in argv[2:], root


if __name__ == "__main__":
    sys.exit(main(*_args(sys.argv[1:])))
