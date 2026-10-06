"""task-compaction-v1-r1 review closure -- revised evidence audit (run-local revision r2).

A separately identified revision; it does NOT replace the frozen
../../task-compaction-v1-r1/src/audit.py.  The independent scientific checks are the
frozen audit's own functions (certificate, check_witnesses, audit_cell, audit_tables,
hand_fixture_checks, determines), imported by path and verified by SHA-256 before use;
this file replaces only the pipeline around them, in four separated layers:

  1. schema    -- parse JSON/JSONL (NaN/Infinity rejected) and validate every field the
                  scientific checks index, before they index it;
  2. availability and integrity -- declared ID sets, seal, freeze;
  3. scientific checks -- the frozen audit's functions, run only on schema-valid inputs
                  whose dependencies are available;
  4. reporting -- intended and performed counts, skipped dependencies, labels.

Labels: available malformed or contradictory evidence is INVALID; missing evidence alone
is INCOMPLETE; INVALID outranks INCOMPLETE and both issue lists survive.  Aggregates are
evaluated only when every input they depend on is complete and valid.  There is no
blanket exception handler: an audit bug raises and exits non-zero, never VALID_COMPLETE.
No producer, minimizer, witness or replay helper of the owner is imported.

Usage: python audit_r2.py <production dir> <audit out dir> [--bypass-integrity]
--bypass-integrity (corruption probes only): a seal HASH mismatch is recorded as
bypassed; a sealed file that is ABSENT is still missing evidence.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys

sys.dont_write_bytecode = True        # the frozen run directory must stay byte-identical

HERE = os.path.dirname(os.path.abspath(__file__))
CLOSURE = os.path.dirname(HERE)
ORIG_RUN = os.path.abspath(os.path.join(CLOSURE, "..", "..", "task-compaction-v1-r1"))
ORIG_AUDIT = os.path.join(ORIG_RUN, "src", "audit.py")
ORIG_AUDIT_SHA256 = "3198a65679b51f30d7a517d28b0908f2f13602e18b159e48701fe03c9bd20b39"


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


if sha(ORIG_AUDIT) != ORIG_AUDIT_SHA256:
    raise SystemExit(f"frozen audit identity mismatch: {ORIG_AUDIT}")
_spec = importlib.util.spec_from_file_location("audit_v1_frozen", ORIG_AUDIT)
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)           # also imports the accepted study declarations
S = A.S


# ---------------------------------------------------------------------- ledger
class Ledger(A.Ledger):
    """Invalid and missing issue lists, performed counts, intended counts, skips."""

    def __init__(self):
        super().__init__()
        self.intended, self.skipped = {}, []

    def skip(self, where, what, reason):
        self.skipped.append({"where": where, "skipped": what, "reason": reason})


# ---------------------------------------------------------------------- layer 1: parsing and schema
def _no_constants(name):
    raise ValueError(f"non-finite constant {name}")


def load_json(path, L, where):
    """('ok', value) | ('missing', None) | ('invalid', None); issues are recorded."""
    try:
        with open(path) as fh:
            return "ok", json.load(fh, parse_constant=_no_constants)
    except FileNotFoundError:
        L.absent(where, os.path.basename(path))
        return "missing", None
    except (ValueError, UnicodeDecodeError) as e:
        L.bad(where, f"malformed JSON in {os.path.basename(path)}: {e}")
        return "invalid", None


def load_jsonl(path, L, where):
    """Parse each line independently; a malformed line is INVALID with its line number,
    readable lines are still returned for checking."""
    try:
        with open(path) as fh:
            lines = fh.read().split("\n")
    except FileNotFoundError:
        L.absent(where, os.path.basename(path))
        return "missing", []
    except UnicodeDecodeError as e:
        L.bad(where, f"undecodable {os.path.basename(path)}: {e}")
        return "invalid", []
    if lines and lines[-1] == "":
        lines.pop()
    recs, status = [], "ok"
    for i, line in enumerate(lines, 1):
        try:
            recs.append(json.loads(line, parse_constant=_no_constants))
        except ValueError as e:
            L.bad(where, f"malformed JSONL {os.path.basename(path)} line {i}: {e}")
            status = "invalid"
    return status, recs


def is_int(v):
    return type(v) is int


def int_vec(v, n=None, lo=0, hi=None):
    """List of built-in ints (bool excluded), optional exact length and range [lo, hi)."""
    return (isinstance(v, list) and (n is None or len(v) == n)
            and all(is_int(x) and x >= lo and (hi is None or x < hi) for x in v))


def canonical(v):
    return int_vec(v) and A.is_canonical(v)


CASE_KEYS = {"N": int, "cell_id": int, "model": str, "n": int, "n_actions": int, "n_candidates": int,
             "primary": bool, "regime": str, "task": str, "tau": int}


def schema_cases(cases, L):
    ok = isinstance(cases, dict) and isinstance(cases.get("cells"), list) \
        and isinstance(cases.get("expected_counts"), dict)
    if ok:
        for c in cases["cells"]:
            if not (isinstance(c, dict) and all(type(c.get(k)) is t for k, t in CASE_KEYS.items())
                    and c["task"] in A.TASK and c["regime"] in ("AUTO", "INTERVENTION")
                    and c["N"] == 2 ** c["n"] and c["n_actions"] >= 1 and c["n_candidates"] >= 0):
                ok = False
        ok = ok and all(is_int(v) and v >= 0 for v in cases["expected_counts"].values())
    if not ok:
        L.bad("cases", "schema: cases.json cells/expected_counts")
    return ok


def schema_table(t, mid):
    """Fields audit_tables indexes, with their types; ranges are its own scientific check."""
    return (isinstance(t, dict) and is_int(t.get("n")) and t["n"] >= 1 and is_int(t.get("N"))
            and isinstance(t.get("tables"), list) and all(isinstance(r, list) for r in t["tables"])
            and isinstance(t.get("actions"), list)
            and all(isinstance(a, dict) and all(k in a for k in ("action_id", "op", "j", "c"))
                    for a in t["actions"]) and t.get("model", mid) == mid)


def schema_candidate_alphas(ca, N):
    return (isinstance(ca, dict) and isinstance(ca.get("candidates"), list)
            and all(isinstance(c, dict) and is_int(c.get("id")) and int_vec(c.get("alpha"), N, 0, N)
                    for c in ca["candidates"]))


def schema_certificate(art, N, n_actions):
    """Every field the frozen certificate/witness/cell checks index; returns a reason or None."""
    if not isinstance(art, dict):
        return "artifact is not an object"
    if not int_vec(art.get("outputs"), N, 0):
        return "outputs vector"
    st = art.get("stages")
    if not (isinstance(st, list) and len(st) >= 2 and all(int_vec(s, N, 0, N) for s in st)):
        return "stage vectors"
    if not int_vec(art.get("alpha"), N, 0, N):
        return "alpha vector"
    for k in ("decoder", "representatives"):
        if not int_vec(art.get(k), None, 0):
            return f"{k} vector"
    m = art.get("macro")
    if not (isinstance(m, list) and all(int_vec(g, None, 0) for g in m)):
        return "macro tables"
    if not is_int(art.get("strict_rounds")):
        return "strict_rounds"
    co = art.get("coarsening")
    if co is not None:
        if not (isinstance(co, list) and all(int_vec(r, None, 0) for r in co)):
            return "coarsening maps"
        if len(co) == len(st) - 1 and any(len(co[d]) != max(st[d + 1]) + 1 for d in range(len(co))):
            return "coarsening map length"
    ws = art.get("witnesses")
    if ws is not None:
        if not isinstance(ws, list):
            return "witnesses"
        for w in ws:
            if not (isinstance(w, dict) and is_int(w.get("round")) and 0 <= w["round"] <= len(st) - 2
                    and all(is_int(w.get(k)) and 0 <= w[k] < N for k in ("x", "y"))
                    and int_vec(w.get("word"), None, 0, n_actions) and len(w["word"]) <= len(st)
                    and all(int_vec(w.get(k)) for k in ("path_x", "path_y", "outputs_x", "outputs_y"))):
                return "witness record"
    return None


CELL_SCALARS = {"cell_id": int, "model": str, "task": str, "regime": str, "N": int, "n": int}


def schema_cell(art, c, n_actions):
    why = schema_certificate(art, c["N"], n_actions)
    if why is None and not (int_vec(art.get("action_ids")) and isinstance(art.get("summary"), dict)):
        why = "action_ids or summary"
    if why is None and any(type(art.get(k)) is not t for k, t in CELL_SCALARS.items()):
        why = "cell scalar fields"
    return why


RECORD_TYPES = {"record_id": int, "candidate_id": int}


# ---------------------------------------------------------------------- layer 2: integrity
def check_seal(prod, L, bypass, report):
    st, seal = load_json(os.path.join(prod, "seal.json"), L, "seal")
    if st != "ok":
        return
    if not (isinstance(seal, dict) and isinstance(seal.get("sha256"), dict)
            and all(isinstance(v, str) for v in seal["sha256"].values())):
        L.bad("seal", "schema: seal.sha256")
        return
    absent, changed = [], []
    for k, v in sorted(seal["sha256"].items()):
        p = os.path.join(prod, k)
        if not os.path.isfile(p):
            absent.append(k)
        elif sha(p) != v:
            changed.append(k)
    L.tick("sealed_files_checked", len(seal["sha256"]) - len(absent))
    L.intended["sealed_files_checked"] = len(seal["sha256"])
    report["integrity"] = {"sealed": len(seal["sha256"]), "absent": absent, "hash_mismatch": changed,
                           "hash_mismatch_bypassed": bool(bypass and changed)}
    for k in absent:
        L.absent("seal", f"sealed artifact {k}")
    for k in changed:
        if not bypass:
            L.bad("seal", f"sealed artifact {k}: present bytes differ from the seal")


def check_freeze(L):
    st, fz = load_json(os.path.join(ORIG_RUN, "freeze.json"), L, "freeze")
    if st != "ok":
        return
    if not (isinstance(fz, dict) and all(isinstance(fz.get(g), dict) for g in ("isolated", "inputs", "run_files"))):
        L.bad("freeze", "schema: freeze.json groups")
        return
    repo = os.path.abspath(os.path.join(ORIG_RUN, *[".."] * 4))
    roots = {"isolated": os.path.join(ORIG_RUN, "isolated"), "inputs": repo, "run_files": ORIG_RUN}
    n = 0
    for group, root in roots.items():
        for k, v in fz[group].items():
            p = os.path.join(root, k)
            n += 1
            if not os.path.isfile(p):
                L.absent("freeze", f"{group}/{k}")
            elif sha(p) != v:
                L.bad("freeze", f"identity mismatch {group}/{k}")
    L.tick("frozen_identities_checked", n)


# ---------------------------------------------------------------------- pipeline
def main(prod, out, bypass=False):
    if os.path.exists(out):
        print(f"refusing: {out} exists")
        return 2
    L = Ledger()
    report = {"bypass_integrity": bypass, "audit_revision": "r2",
              "source_identity": {"audit_r2.py": sha(os.path.abspath(__file__)),
                                  "frozen_audit.py (imported checks)": ORIG_AUDIT_SHA256}}
    check_seal(prod, L, bypass, report)
    st, cases = load_json(os.path.join(prod, "cases.json"), L, "cases")
    if st != "ok" or not schema_cases(cases, L):
        report["not_evaluated"] = "every cell check: cases.json unavailable or malformed"
        return finish(L, report, out)
    mode = cases.get("mode")
    report["mode"] = mode
    if mode == "production":
        check_freeze(L)
        st, declared = load_json(os.path.join(ORIG_RUN, "protocol", "CASES.json"), L, "protocol")
        if st == "ok" and (declared.get("cells") != cases["cells"]
                           or declared.get("expected_counts") != cases["expected_counts"]):
            L.bad("cases", "production cases differ from protocol/CASES.json")
    exp, cells = cases["expected_counts"], cases["cells"]
    ids = [c["cell_id"] for c in cells]
    if ids != list(range(len(cells))) or len(cells) != exp.get("cells"):
        L.bad("cases", "cell ID set")
    # intended denominators, from the declaration alone
    acts_by_model = {}
    for c in cells:
        acts_by_model[c["model"]] = max(acts_by_model.get(c["model"], 0), c["n_actions"])
    N_by_model = {c["model"]: c["N"] for c in cells}
    L.intended.update({
        "cells": len(cells), "summary_rows": len(cells),
        "candidate_records": sum(c["n_candidates"] for c in cells),
        "candidate_decisions_checked": sum(c["n_candidates"] for c in cells),
        "action_tables": sum(acts_by_model.values()),
        "transition_entries_owner_checked": sum(acts_by_model[m] * N_by_model[m] for m in acts_by_model)})
    for k, ek in (("action_tables", "distinct_model_action_tables"),
                  ("transition_entries_owner_checked", "distinct_model_state_action_entries"),
                  ("candidate_records", "candidate_records")):
        if L.intended[k] != exp.get(ek):
            L.bad("cases", f"declared {ek} {exp.get(ek)} != {L.intended[k]} implied by the cells")

    # ---- tables (each model independently)
    T = {}
    for mid in sorted(acts_by_model):
        st, t = load_json(os.path.join(prod, "tables", f"{mid}.json"), L, mid)
        if st == "ok" and not schema_table(t, mid):
            L.bad(mid, "schema: table file")
            st = "invalid"
        if st == "ok":
            T[mid] = t
        else:
            L.skip(mid, "transition-table checks and every cell of this model", f"table {st}")
    tabs = A.audit_tables(T, mode, L)            # frozen independent check
    for mid in sorted(T):
        if mid not in tabs:
            L.skip(mid, "every cell of this model", "table failed its dimension/range check")
    report["tables"] = {"intended": L.intended["action_tables"],
                        "available": sum(len(v) for v in tabs.values()),
                        "state_action_entries_available": sum(len(v) * len(v[0]) for v in tabs.values())}
    L.tick("action_tables", report["tables"]["available"])
    report["hand_fixtures"] = A.hand_fixture_checks(L)

    # ---- candidate declarations against the study
    calpha = {}
    for mid in sorted(acts_by_model):
        st, ca = load_json(os.path.join(prod, "candidate_alphas", f"{mid}.json"), L, f"{mid}/candidate_alphas")
        if st == "ok" and not schema_candidate_alphas(ca, N_by_model[mid]):
            L.bad(f"{mid}/candidate_alphas", "schema: candidate alpha file")
            st = "invalid"
        if st != "ok":
            L.skip(mid, "candidate decisions of this model", f"candidate alphas {st}")
            continue
        n = N_by_model[mid].bit_length() - 1
        decl = S.candidates(n)
        mine = [A.first_appearance([S.alpha_value(c, x, n) for x in range(2 ** n)]) for c in decl]
        if mine != [c["alpha"] for c in ca["candidates"]] or [c["id"] for c in ca["candidates"]] != [c["id"] for c in decl]:
            L.bad(mid, "candidate alpha vectors differ from study declarations")
        calpha[mid] = (decl, mine)
        L.tick("candidate_vectors_checked", len(decl))

    # ---- cells
    present = set(os.listdir(os.path.join(prod, "cells"))) if os.path.isdir(os.path.join(prod, "cells")) else set()
    want = {f"cell_{i:02d}.json" for i in ids}
    for f in sorted(present - want):
        L.bad(f, "undeclared cell artifact")
    cell_rows, alphas, clos = {}, {}, {}
    for c in cells:
        cid, where = c["cell_id"], f"cell_{c['cell_id']:02d}"
        ni, nm = len(L.invalid), len(L.missing)
        row = {}
        # candidate records: parsed and identity-checked independently of the certificate
        st_r, raw = load_jsonl(os.path.join(prod, "candidates", f"{where}.jsonl"), L, where)
        recs, seen = [], set()
        for k, r in enumerate(raw):
            if not (isinstance(r, dict) and all(type(r.get(f)) is t for f, t in RECORD_TYPES.items())):
                L.bad(where, f"record {k}: missing or non-integer record_id/candidate_id")
                continue
            if r["record_id"] in seen:
                L.bad(where, f"duplicate record_id {r['record_id']}")
                continue
            if r["record_id"] != cid * 1000 + r["candidate_id"] or not 0 <= r["candidate_id"] < c["n_candidates"]:
                L.bad(where, f"undeclared record_id {r['record_id']}")
                continue
            seen.add(r["record_id"])
            recs.append(r)
        L.tick("candidate_records", len(recs))
        st_a, art = ("missing", None)
        if f"{where}.json" in present:
            st_a, art = load_json(os.path.join(prod, "cells", f"{where}.json"), L, where)
        else:
            L.absent(where, "cell artifact")
        tables_ok = c["model"] in tabs
        if st_a == "ok":
            why = schema_cell(art, c, c["n_actions"])
            if why:
                L.bad(where, f"schema: {why}")
                st_a = "invalid"
        if st_a != "ok" or not tables_ok:
            reason = f"cell artifact {st_a}" if st_a != "ok" else "model tables unavailable"
            L.skip(where, "certificate, witness, candidate and summary checks", reason)
        else:
            if c["model"] not in calpha:
                L.skip(where, "candidate decisions", "candidate alphas unavailable")
            row = A.audit_cell(c, art, recs, tabs[c["model"]], calpha.get(c["model"]), clos, L, where)
            alphas[cid] = art["alpha"]
        row["status"] = A.label_status(len(L.invalid) - ni, len(L.missing) - nm)
        cell_rows[cid] = row
    L.tick("cells", sum(1 for r in cell_rows.values() if "certificate" in r))
    present_records = L.counts.get("candidate_records", 0)
    if present_records < L.intended["candidate_records"]:
        L.absent("candidates", f"{L.intended['candidate_records'] - present_records} declared records absent or unusable")
    report["candidate_records"] = {"declared": L.intended["candidate_records"], "present_valid": present_records}

    # ---- cross-cell: INTERVENTION refines AUTO (only for available pairs)
    refine = []
    for c in cells:
        if c["regime"] != "INTERVENTION":
            continue
        a = next((x for x in cells if x["model"] == c["model"] and x["task"] == c["task"]
                  and x["regime"] == "AUTO"), None)
        if a is None:
            L.bad("cases", f"cell {c['cell_id']}: no AUTO partner declared")
            continue
        if c["cell_id"] in alphas and a["cell_id"] in alphas:
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

    # ---- summary.json: exact declared row set, field by field against audited cells
    check_summary(prod, cells, cell_rows, refine, L, report)

    # ---- declared fixture certificate (FX1): validity and minimality separately
    st, fx = load_json(os.path.join(prod, "fixtures", "FX1_identity.json"), L, "FX1")
    if st == "ok":
        tr = fx.get("transitions") if isinstance(fx, dict) else None
        N = len(tr[0]) if isinstance(tr, list) and tr and isinstance(tr[0], list) else 0
        if not (N and all(int_vec(t, N, 0, N) for t in tr)) or schema_certificate(fx, N, len(tr)):
            L.bad("FX1", "schema: fixture certificate")
        else:
            fxL = A.Ledger()
            r = A.certificate(fx, tr, fxL, "FX1")
            report["fixture_FX1"] = {"validity": r["validity"], "minimality": r["minimality"], "issues": fxL.invalid}
            L.invalid += fxL.invalid
    report["cells"] = {str(k): {kk: vv for kk, vv in v.items() if kk != "summary"} for k, v in cell_rows.items()}
    report["aggregates"] = aggregates(cells, cell_rows, L)
    if report["aggregates"]["evaluated"] and (L.invalid or L.missing):
        report["aggregates"] = {"evaluated": False, "reason": "withheld: the audit is not VALID_COMPLETE "
                                "(summary, seal, fixture or declaration evidence failed or is missing)"}
    return finish(L, report, out)


def exact(v):
    """Type-exact identity: 0, 0.0, False and null stay distinct (plain == conflates them)."""
    return json.dumps(v, sort_keys=True)


SUMMARY_TOP = ("n_cells", "n_candidate_records", "n_action_tables", "n_state_action_entries")


def check_summary(prod, cells, cell_rows, refine, L, report):
    st, summ = load_json(os.path.join(prod, "summary.json"), L, "summary")
    if st != "ok":
        L.skip("summary", "summary rows", f"summary.json {st}")
        return
    if not (isinstance(summ, dict) and isinstance(summ.get("cells"), list)):
        L.bad("summary", "schema: summary.cells")
        return
    declared = {c["cell_id"] for c in cells}
    seen, compared = set(), 0
    for k, s in enumerate(summ["cells"]):
        cid = s.get("cell", {}).get("cell_id") if isinstance(s, dict) and isinstance(s.get("cell"), dict) else None
        if not is_int(cid):
            L.bad("summary", f"row {k}: missing or non-integer cell.cell_id")
            continue
        if cid in seen:
            L.bad("summary", f"row {k}: duplicate cell {cid}")
            continue
        if cid not in declared:
            L.bad("summary", f"row {k}: undeclared cell {cid}")
            continue
        seen.add(cid)
        ref = cell_rows.get(cid, {}).get("summary")
        if ref is None:
            L.skip("summary", f"row for cell {cid}", "its cell artifact was not verified")
            continue
        for f in sorted(set(ref) | set(s)):
            if exact(s.get(f, "<absent>")) != exact(ref.get(f, "<absent>")):
                L.bad("summary", f"cell {cid}: field {f} differs from the audited cell")
        compared += 1
    L.tick("summary_rows", compared)
    for cid in sorted(declared - seen):
        L.absent("summary", f"row for cell {cid}")
    top = {"n_cells": len(cells), "n_candidate_records": L.intended["candidate_records"],
           "n_action_tables": L.intended["action_tables"],
           "n_state_action_entries": L.intended["transition_entries_owner_checked"]}
    for f in SUMMARY_TOP:
        if f not in summ:
            L.absent("summary", f"top-level {f}")
        elif exact(summ[f]) != exact(top[f]):
            L.bad("summary", f"top-level {f} {summ[f]!r} != declared {top[f]}")
    if "intervention_refines_auto" not in summ:
        L.absent("summary", "top-level intervention_refines_auto")
    elif len(refine) == L.intended["refinement_pairs_checked"]:
        if exact(summ["intervention_refines_auto"]) != exact(refine):
            L.bad("summary", "top-level intervention_refines_auto differs from the audited pairs")
    else:
        L.skip("summary", "top-level intervention_refines_auto", "not every pair was available")


def aggregates(cells, cell_rows, L):
    """Outcome counts per regime, ONLY from a complete set of verified cells."""
    if any(cell_rows.get(c["cell_id"], {}).get("status") != "VALID_COMPLETE"
           or cell_rows[c["cell_id"]].get("summary") is None for c in cells):
        return {"evaluated": False, "reason": "not every declared cell is VALID_COMPLETE"}
    agg = {}
    for c in cells:
        s = cell_rows[c["cell_id"]]["summary"]
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


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], "--bypass-integrity" in sys.argv[3:]))
