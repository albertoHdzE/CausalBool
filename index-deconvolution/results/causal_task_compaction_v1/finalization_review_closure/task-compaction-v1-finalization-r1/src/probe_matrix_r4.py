"""task-compaction-v1 final audit closure -- the declared matrix for audit_r4 (TEST_MATRIX_R4.md).

Groups P (23), F (23) and H (6) are imported unchanged from the hash-pinned finalization
probe_matrix_r3.py in its post-adoption form and re-run under audit_r4; group N holds the new
R1/R2 cases. Old-defect regression runs the pinned audit_r3 on six N copies; fault restoration
runs six mutants of audit_r4 (source text edited in memory, executed under audit_r4's own file
name so that its pinned import graph resolves) on the cases that must catch them.
Every case works on a COPY in a fresh scratch directory; saved evidence is only read.
Usage: python probe_matrix_r4.py <fresh scratch dir> <result dir>
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 6))
BASE = os.path.join(REPO, "index-deconvolution", "results", "causal_task_compaction_v1")
FIN = os.path.join(BASE, "finalization", "task-compaction-v1-finalization-r1")
PM3 = os.path.join(FIN, "src", "probe_matrix_r3.py")
R4 = os.path.join(HERE, "audit_r4.py")
if hashlib.sha256(open(PM3, "rb").read()).hexdigest() != \
        "7fc0ac659eb5e1044121f9bef8c5e59fae543fcd22bbf104348d0c91d6b6543c":
    raise SystemExit("finalization probe_matrix_r3.py identity mismatch")
_spec = importlib.util.spec_from_file_location("probe_matrix_r3", PM3)
P3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P3)
P2, PROD, HIST, PY, R3 = P3.P2, P3.PROD, P3.HIST, P3.PY, P3.R3


def rw(p, rel, fn):
    path = os.path.join(p, rel)
    d = json.load(open(path))
    note = fn(d)
    open(path, "w").write(json.dumps(d, sort_keys=True, separators=(",", ":")))
    return note


def fx(fn):
    return lambda p: rw(p, "fixtures/FX1_identity.json", fn)


def seal(fn):
    return lambda p: rw(p, "seal.json", fn)


def _set(k, v):
    def f(d):
        d[k] = v
        return f"{k} = {v!r}"
    return f


def _pop(k):
    def f(d):
        d.pop(k)
        return f"{k} removed"
    return f


def _seal_pop(k):
    def f(d):
        d["sha256"].pop(k)
        return f"seal entry {k} deleted"
    return f


def _seal_set(k, v):
    def f(d):
        d["sha256"][k] = v
        return f"seal sha256[{k}] = {v[:12]}"
    return f


def rm(rel):
    def f(p):
        os.remove(os.path.join(p, rel))
        return f"{rel} removed"
    return f


def cor3(p):
    return P2.COR.cor3(p, None)[0]


def change_and_reseal(p):
    q = os.path.join(p, "imports.json")
    open(q, "ab").write(b"\n")
    h = hashlib.sha256(open(q, "rb").read()).hexdigest()
    return [rw(p, "seal.json", _seal_set("imports.json", h)), "imports.json + newline, candidate seal hash updated"]


FXP = "fixtures/FX1_identity.json"
# id, mutation, bypass, status, invalid fragments, missing fragments, extra checks on the report
N_CASES = [
    ("N01a_fixture_id_int", fx(_set("fixture_id", 123)), True, "INVALID",
     ["FX1|fixture.fixture_id|type int != expected str"], [], {"fixture_completed": 0}),
    ("N01b_fixture_id_wrong", fx(_set("fixture_id", "NOT_FX1")), True, "INVALID",
     ["FX1|fixture.fixture_id|value 'NOT_FX1'"], [], {"fixture_completed": 0}),
    ("N01c_fixture_id_missing", fx(_pop("fixture_id")), True, "INVALID",
     ["FX1|fixture.fixture_id|missing required field"], [], {"fixture_completed": 0}),
    ("N01d_coarsening_null", fx(_set("coarsening", None)), True, "INVALID",
     ["FX1|fixture.coarsening|null where a value is required"], [], {"fixture_completed": 0}),
    ("N01e_K_bool", fx(_set("K", True)), True, "INVALID", ["FX1|fixture.K|non-boolean int"], [], {"fixture_completed": 0}),
    ("N01f_outputs_rebound", fx(_set("outputs", [0, 1, 1, 1])), True, "INVALID",
     ["FX1|fixture.outputs[1]|value 1 != expected 0"], [], {"fixture_completed": 0}),
    ("N02a_fixture_absent", rm(FXP), False, "INCOMPLETE", [],
     ["FX1|FX1_identity.json", f"seal|sealed artifact {FXP}"], {"fixture_completed": 0, "fixture_available": False}),
    ("N02b_valid_not_minimal", cor3, True, "INVALID", ["FX1||stage-induction check"], [],
     {"fixture_completed": 2, "validity": True, "minimality": False}),
    ("N03a_seal_empty_normal", seal(_set("sha256", {})), False, "INCOMPLETE", [], ["seal|seal entry "],
     {"seal_agreeing": 0, "seal_missing": 60, "compared": 60}),
    ("N03b_seal_empty_bypass", seal(_set("sha256", {})), True, "INCOMPLETE", [], ["seal|seal entry "],
     {"seal_agreeing": 0, "seal_missing": 60, "compared": 60}),
    ("N03c_seal_entry_deleted_normal", seal(_seal_pop(FXP)), False, "INCOMPLETE", [], [f"seal|seal entry {FXP}"],
     {"seal_agreeing": 59, "seal_missing": 1, "compared": 60}),
    ("N03d_seal_entry_deleted_bypass", seal(_seal_pop(FXP)), True, "INCOMPLETE", [], [f"seal|seal entry {FXP}"],
     {"seal_agreeing": 59, "seal_missing": 1, "compared": 60}),
    ("N03e_seal_file_absent", rm("seal.json"), False, "INCOMPLETE", [], ["seal|seal.json"],
     {"seal_agreeing": 0, "seal_missing": 60, "compared": 60}),
    ("N04a_seal_undeclared_entry", seal(_seal_set("extra.json", "0" * 64)), False, "INVALID",
     ["seal|sha256[extra.json]|undeclared path"], [], {"seal_agreeing": 60}),
    ("N04b_seal_malformed_hash", seal(_seal_set("summary.json", "XYZ")), False, "INVALID",
     ["seal|sha256[summary.json]|malformed hash"], [], {"seal_agreeing": 59}),
    ("N04c_seal_files_count", seal(_set("files", 59)), False, "INVALID", ["seal|files|"], [], {"seal_agreeing": 60}),
    ("N04d_seal_contradicts_bypass", seal(_seal_set("imports.json", "0" * 64)), True, "INVALID",
     ["seal|sha256[imports.json]|contradicts the pinned authority"], [], {"seal_agreeing": 59}),
    ("N05a_file_and_seal_changed_normal", change_and_reseal, False, "INVALID",
     ["seal|sha256[imports.json]|contradicts", "seal||sealed artifact imports.json: present bytes differ"], [],
     {"mismatch": 1}),
    ("N05b_file_and_seal_changed_bypass", change_and_reseal, True, "INVALID",
     ["seal|sha256[imports.json]|contradicts"], [], {"mismatch": 1}),
    ("N06_missing_entry_with_bad_fixture",
     lambda p: [seal(_seal_pop(FXP))(p), fx(_set("fixture_id", 123))(p)], True, "INVALID",
     ["FX1|fixture.fixture_id|"], [f"seal|seal entry {FXP}"], {"fixture_completed": 0, "seal_missing": 1}),
    ("N07_pristine", None, False, "VALID_COMPLETE", [], [],
     {"seal_agreeing": 60, "seal_missing": 0, "compared": 60, "mismatch": 0, "fixture_completed": 2,
      "validity": True, "minimality": True}),
]
OLD_DEFECT = ["N01a_fixture_id_int", "N01b_fixture_id_wrong", "N01d_coarsening_null", "N03a_seal_empty_normal",
              "N03c_seal_entry_deleted_normal", "N05a_file_and_seal_changed_normal"]

_FX_STRICT = '            ok &= R3.strict(L, "FX1", fx[k], v, f"fixture.{k}")\n'
_NULL_CO = ('        if co is None:\n            L.bad_field("FX1", "fixture.coarsening", "null where a value is required")\n'
            '            ok = False\n')
MUTANTS = {
    "X1_fixture_id_silent": ([(_FX_STRICT, '            ok &= (type(fx[k]) is str) if k == "fixture_id" else '
                                           'R3.strict(L, "FX1", fx[k], v, f"fixture.{k}")\n')], ["N01a_fixture_id_int"]),
    "X2_fixture_id_unbound": ([("    for k, v in FX1_DECL.items():",
                                "    for k, v in [x for x in FX1_DECL.items() if x[0] != 'fixture_id']:")],
                              ["N01b_fixture_id_wrong"]),
    "X3_null_coarsening_allowed": ([(_NULL_CO, "        if co is None:\n            pass\n")], ["N01d_coarsening_null"]),
    "X4_coverage_from_candidate": ([("    for k in sorted(set(AUTH) - set(cand)):", "    for k in sorted(set(cand) - set(cand)):"),
                                    ("    for k, v in sorted(AUTH.items()):",
                                     "    for k, v in sorted({k: AUTH[k] for k in cand if k in AUTH}.items()):")],
                                   ["N03a_seal_empty_normal", "N03c_seal_entry_deleted_normal"]),
    "X5_compare_with_candidate": ([("        elif v != AUTH[k]:", "        elif False:"),
                                   ("        if sha(p) != v:", "        if sha(p) != cand.get(k, v):")],
                                  ["N05a_file_and_seal_changed_normal"]),
    "X6_bypass_hides_missing_entry": ([('        L.absent("seal", f"seal entry {k}")',
                                        '        bypass or L.absent("seal", f"seal entry {k}")')],
                                      ["N03d_seal_entry_deleted_bypass"]),
}


def run_mutant(src, prod, out, bypass, root):
    code = ("import sys; p, s = sys.argv[1], open(sys.argv[2]).read(); sys.argv = [p] + sys.argv[3:]; "
            "g = {'__name__': '__main__', '__file__': p}; exec(compile(s, p, 'exec'), g)")
    cmd = [PY, "-c", code, R4, src, prod, out] + (["--bypass-integrity"] if bypass else []) + ["--inputs-root", root]
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    p = subprocess.run(cmd, capture_output=True, text=True, env=dict(env, PYTHONDONTWRITEBYTECODE="1"), cwd="/tmp")
    f = os.path.join(out, "audit.json")
    return p, (json.load(open(f)) if os.path.exists(f) else None)


def extras(a, want):
    if not a:
        return {"extras_ok": False}
    i, f = a.get("integrity", {}), a.get("fixture_FX1", {})
    got = {"seal_agreeing": i.get("candidate_entries_agreeing"), "seal_missing": len(i.get("candidate_entries_missing", [])),
           "compared": i.get("hashes_compared"), "mismatch": len(i.get("hash_mismatch", [])),
           "fixture_completed": f.get("certificate_checks_completed"), "fixture_available": f.get("file_available"),
           "validity": f.get("validity"), "minimality": f.get("minimality")}
    return {"extras_wanted": want, "extras_got": {k: got[k] for k in want},
            "extras_ok": all(got[k] == v for k, v in want.items()) and i.get("intended_entries") == 60
            and f.get("intended") == 1}


def make(scratch, cid, mut):
    prod = os.path.join(scratch, cid, "production")
    shutil.copytree(PROD, prod)
    return prod, (mut(prod) if mut else "none")


def main(scratch, result):
    for d in (scratch, result):
        if os.path.exists(d):
            print(f"refusing: {d} exists")
            return 2
    os.makedirs(scratch)
    os.makedirs(result)
    rows = []

    def record(row, cid, a_dir):
        rows.append(row)
        src = os.path.join(a_dir, "audit.json")
        shutil.copy(src if os.path.exists(src) else os.devnull, os.path.join(result, f"{cid}.audit_r4.json"))
        print(f"{row['group']} {cid:42s} {row['status']!s:15s} {'as required' if row['as_required'] else 'NOT AS REQUIRED'}")

    for cid, item, mut, bypass, want, inv, mis in P2.CASES:
        prod, change = make(scratch, cid, mut)
        inv = P3.R3_FRAG.get(cid, inv)
        a_dir = os.path.join(scratch, cid, "audit_r4")
        p, a = P3.run(R4, prod, a_dir, bypass, HIST)
        row = {"group": "P", "id": cid, "protocol_item": item, "change": change, "bypass_integrity": bypass,
               "expected_status": want, **P3.judge(p, a, want, inv, mis, 0)}
        if a and cid.startswith("M10c"):
            f = a.get("fixture_FX1", {})
            row["fx1_validity_minimality"] = [f.get("validity"), f.get("minimality")]
            row["as_required"] &= f.get("validity") is True and f.get("minimality") is False
        if a and cid == "M06a_candidates_malformed":
            row["as_required"] &= a["counts"]["cells"]["performed"] == 24
        record(row, cid, a_dir)
    for cid, mut, bypass, want, inv, mis, min_cells, _ in P3.F_CASES:
        prod, change = make(scratch, cid, mut)
        a_dir = os.path.join(scratch, cid, "audit_r4")
        p, a = P3.run(R4, prod, a_dir, bypass, HIST)
        record({"group": "F", "id": cid, "change": change, "bypass_integrity": bypass, "expected_status": want,
                **P3.judge(p, a, want, inv, mis, min_cells)}, cid, a_dir)
    for cid, mut, want, inv, mis in [P3.H01_POST] + P3.H_CASES[1:]:
        root, change = None, "default (current repository) inputs root"
        if mut != "repo":
            root = P3.hist_copy(scratch, cid)
            change = mut(root) if mut else "pristine copy of finalization/historical_inputs"
        a_dir = os.path.join(scratch, cid, "audit_r4")
        p, a = P3.run(R4, PROD, a_dir, False, root)
        record({"group": "H", "id": cid, "change": change, "expected_status": want,
                **P3.judge(p, a, want, inv, mis, 24)}, cid, a_dir)
    n_prods = {}
    for cid, mut, bypass, want, inv, mis, want_x in N_CASES:
        prod, change = make(scratch, cid, mut)
        n_prods[cid] = (prod, bypass)
        a_dir = os.path.join(scratch, cid, "audit_r4")
        p, a = P3.run(R4, prod, a_dir, bypass, HIST)
        row = {"group": "N", "id": cid, "change": change, "bypass_integrity": bypass, "expected_status": want,
               **P3.judge(p, a, want, inv, mis, 24), **extras(a, want_x)}
        row["as_required"] &= row["extras_ok"]
        record(row, cid, a_dir)
    old = []
    for cid in OLD_DEFECT:                                  # the defect r3 shows on the same copies
        prod, bypass = n_prods[cid]
        p, a = P3.run(R3, prod, os.path.join(scratch, cid, "audit_r3"), bypass, HIST)
        new = next(r for r in rows if r["id"] == cid)
        old.append({"id": cid, "r3_exit": p.returncode, "r3_status": a and a["status"],
                    "r3_integrity": a and {k: a["integrity"].get(k) for k in ("sealed", "absent", "hash_mismatch")},
                    "r3_fixture_FX1": a and a.get("fixture_FX1"), "r4_status": new["status"],
                    "demonstrates_old_defect": bool(a) and a["status"] == "VALID_COMPLETE" and p.returncode == 0
                    and new["status"] != "VALID_COMPLETE"})
        print(f"old-defect {cid:40s} r3 {a and a['status']}  r4 {new['status']}")
    base_src = open(R4).read()
    mutants = []
    for mid, (subs, catchers) in MUTANTS.items():
        s = base_src
        for old_s, new_s in subs:
            if s.count(old_s) != 1:
                raise SystemExit(f"mutant {mid}: anchor occurs {s.count(old_s)} times")
            s = s.replace(old_s, new_s)
        src = os.path.join(scratch, f"{mid}.py")
        open(src, "w").write(s)
        for cid in catchers:
            want, inv, mis, want_x = next((c[3], c[4], c[5], c[6]) for c in N_CASES if c[0] == cid)
            prod, bypass = n_prods[cid]
            out = os.path.join(scratch, cid, f"mutant_{mid}")
            p, a = run_mutant(src, prod, out, bypass, HIST)
            j = {**P3.judge(p, a, want, inv, mis, 24), **extras(a, want_x)}
            caught = not (j["as_required"] and j["extras_ok"])
            reason = {"status": j.get("status"), "required_invalid_found": j.get("required_invalid_found"),
                      "required_missing_found": j.get("required_missing_found"), "extras_got": j.get("extras_got")}
            frag_lost = not all(list((j.get("required_invalid_found") or {}).values())
                                + list((j.get("required_missing_found") or {}).values()))
            mutants.append({"mutant": mid, "case": cid, "caught": caught, "own_fragment_absent": frag_lost,
                            "traceback": j.get("traceback"), **reason})
            print(f"mutant {mid:32s} on {cid:36s} caught={caught} own_fragment_absent={frag_lost} status={j.get('status')}")
    doc = {"n": len(rows), "as_required": sum(r["as_required"] for r in rows),
           "by_group": {g: [sum(r["as_required"] for r in rows if r["group"] == g),
                            sum(r["group"] == g for r in rows)] for g in "PFHN"},
           "old_defect": old, "old_defect_demonstrated": sum(o["demonstrates_old_defect"] for o in old),
           "mutants": mutants, "mutants_caught_for_reason": sum(m["caught"] and m["own_fragment_absent"]
                                                                and not m["traceback"] for m in mutants),
           "cases": rows}
    json.dump(doc, open(os.path.join(result, "matrix.json"), "w"), indent=1, sort_keys=True)
    print(f"as required {doc['as_required']} / {doc['n']}  by group {doc['by_group']}")
    print(f"old defect demonstrated {doc['old_defect_demonstrated']} / {len(old)}; "
          f"mutants caught for their reason {doc['mutants_caught_for_reason']} / {len(mutants)}")
    ok = doc["as_required"] == doc["n"] == 73 and doc["old_defect_demonstrated"] == len(old) == 6 \
        and doc["mutants_caught_for_reason"] == len(mutants) == 7
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
