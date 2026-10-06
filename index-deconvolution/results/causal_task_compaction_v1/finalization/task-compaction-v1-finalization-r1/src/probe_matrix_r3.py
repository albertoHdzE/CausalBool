"""task-compaction-v1 finalization -- declared finite matrix for audit_r3 (TEST_MATRIX.md).

Three groups, every case on a COPY in a fresh scratch directory; saved evidence is only read.
  P  the 23 closure cases (mutations imported from the hash-pinned closure probe_matrix.py),
     re-run under audit_r3 with the same expected status and r3's field-level fragments;
  F  field-category cases: the three Codex probes (also run against audit_r2 to show its
     false acceptance), bool/int/float confusion, nested ratios, nulls, candidate metadata,
     missing required fields, malformed index containers, paired summary mutation, INVALID
     together with missing evidence, plus one normal-mode integrity case;
  H  historical-root cases: explicit snapshot root, and corrupted / extra / missing /
     substituted copies of that snapshot.
A case is "as required" iff status, exit code, aggregate withholding and every required
(where|field|check) fragment match, nothing tracebacks, and the declared independent
checks still ran (cells performed).
Usage: python probe_matrix_r3.py <fresh scratch dir> <result dir> [--post-adoption]
--post-adoption: after the five active paths changed, groups P and F verify freeze inputs against
the historical snapshot (--inputs-root), the audit_r2 comparison is not repeated (r2 can only
check the current tree), and H01 must disclose exactly the two adopted-input mismatches.
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
FIN = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(FIN, *[".."] * 5))
BASE = os.path.join(REPO, "index-deconvolution", "results", "causal_task_compaction_v1")
ORIG = os.path.join(BASE, "task-compaction-v1-r1")
PROD = os.path.join(ORIG, "production")
PY = os.path.join(REPO, "venv", "bin", "python")
R3 = os.path.join(HERE, "audit_r3.py")
R2 = os.path.join(BASE, "review_closure", "task-compaction-v1-r1", "src", "audit_r2.py")
HIST = os.path.join(FIN, "historical_inputs")
PM2 = os.path.join(BASE, "review_closure", "task-compaction-v1-r1", "src", "probe_matrix.py")
if hashlib.sha256(open(PM2, "rb").read()).hexdigest() != \
        "75093ea342e3243ed71ce81e2ed02c1735ef722949afd270e1f5e1aeedae9b14":
    raise SystemExit("closure probe_matrix.py identity mismatch")
_spec = importlib.util.spec_from_file_location("probe_matrix_r2", PM2)
P2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P2)

# r3 fragments for the closure cases whose wording changed (field-level now); status unchanged
R3_FRAG = {"M03a_summary_duplicate": ["summary|cells[24].cell.cell_id|duplicate or undeclared cell 2"],
           "M04_summary_value": ["summary|cells[5].K_star|"],
           "M08a_summary_id_missing": ["summary|cells[6].cell.cell_id|missing or non-integer"],
           "M08b_record_id_missing": ["cell_02|record[0].record_id|missing required field"],
           "M10d_COR4_remove_and_corrupt": ["cell_05|cell.summary.K_star|value"]}


def recs(p, cell_i, fn):
    path = os.path.join(p, "candidates", f"cell_{cell_i:02d}.jsonl")
    rows = [json.loads(x) for x in open(path).read().splitlines()]
    change = fn(rows)
    open(path, "w").write("".join(json.dumps(r) + "\n" for r in rows))
    return change


def both(*fns):
    def run(p):
        return [f(p) for f in fns]
    return run


def f01_codex_candidate_bool(p):
    return recs(p, 0, lambda r: (r[0].update(decodable=1, K_candidate=256.0), "cell 0 rec 0 decodable=1, K_candidate=256.0")[1])


def f02_codex_candidate_metadata(p):
    def f(r):
        r[0]["cell_id"] = 999
        r[0]["candidate"]["g"] = "invented"
        return "cell 0 rec 0 cell_id=999, candidate.g='invented'"
    return recs(p, 0, f)


def f03_codex_summary_both_bool(p):
    a = P2.cell(p, 0, lambda d: (d["summary"]["baselines"]["identity"].__setitem__("task_sufficient", 1), "cell 0")[1])
    b = P2.summary(p, lambda d: (d["cells"][0]["baselines"]["identity"].__setitem__("task_sufficient", 1), "row 0")[1])
    return f"identity.task_sufficient true->1 in {a} artifact and summary {b}"


def f04_record_ratio_float(p):
    return recs(p, 0, lambda r: (r[0]["K_ratio"].__setitem__("den", 1.0), "cell 0 rec 0 K_ratio.den 1 -> 1.0")[1])


def f05_summary_ratio_float(p):
    return P2.summary(p, lambda d: (d["cells"][0]["K_star_over_N"].__setitem__("num", 1.0), "row 0 K_star_over_N.num -> 1.0")[1])


def f06_null_not_allowed(p):
    return recs(p, 0, lambda r: (r[1].__setitem__("is_control", None), "cell 0 rec 1 is_control -> null")[1])


def f07_value_where_null_required(p):
    return recs(p, 0, lambda r: (r[1].__setitem__("K_ratio", {"num": 1, "den": 1}), "cell 0 rec 1 (insufficient) K_ratio -> 1/1")[1])


def f08_alpha_declaration_metadata(p):
    def f(d):
        d["candidates"][3]["candidate"]["g"] = "x"
        return "M1 candidate_alphas[3].candidate.g -> 'x'"
    return P2.jrw(os.path.join(p, "candidate_alphas", "M1.json"), f)


def f09a_record_field_missing(p):
    return recs(p, 0, lambda r: (r[0].pop("closed"), "cell 0 rec 0 lost 'closed'")[1])


def f09b_cell_field_missing(p):
    return P2.cell(p, 2, lambda d: (d.pop("coarsening"), "cell 2 lost 'coarsening'")[1])


def f09c_fixture_K_missing(p):
    return P2.jrw(os.path.join(p, "fixtures", "FX1_identity.json"), lambda d: (d.pop("K"), "FX1 lost 'K'")[1])


def f10a_closure_witness_shape(p):
    return recs(p, 0, lambda r: (r[1]["closure_witnesses"].__setitem__("0", [0]), "cell 0 rec 1 closure_witnesses['0'] -> [0]")[1])


def f10b_failing_actions_float(p):
    return recs(p, 0, lambda r: (r[1].__setitem__("failing_actions", [0.0]), "cell 0 rec 1 failing_actions -> [0.0]")[1])


def f10c_conflict_pair_string(p):
    return recs(p, 0, lambda r: (r[1].__setitem__("decode_conflict", "0,3"), "cell 0 rec 1 decode_conflict -> '0,3'")[1])


def f11_paired_summary_value(p):
    a = P2.cell(p, 0, lambda d: (d["summary"].__setitem__("K0", d["summary"]["K0"] + 1), "cell 0 summary.K0+1")[1])
    b = P2.summary(p, lambda d: (d["cells"][0].__setitem__("K0", d["cells"][0]["K0"] + 1), "row 0 K0+1")[1])
    return f"{a}; {b} (the two saved copies still agree)"


def f12_invalid_with_missing(p):
    a = f01_codex_candidate_bool(p)
    os.remove(os.path.join(p, "candidates", "cell_05.jsonl"))
    return f"{a}; candidates/cell_05.jsonl removed"


def f13_top_level_float(p):
    return P2.summary(p, lambda d: (d.__setitem__("n_cells", 24.0), "summary n_cells -> 24.0")[1])


def f14_cell_scalar_value(p):
    return P2.cell(p, 0, lambda d: (d.__setitem__("model", "M2"), "cell 0 model -> 'M2'")[1])


def f15_witness_name(p):
    return P2.cell(p, 0, lambda d: (d["witnesses"][0]["word_names"].__setitem__(0, "tick"), "cell 0 witness 0 word_names[0] -> 'tick'")[1])


def f16_action_decl_bool(p):
    return P2.jrw(os.path.join(p, "tables", "M1.json"),
                  lambda d: (d["actions"][1].__setitem__("c", False), "M1 actions[1].c 0 -> false")[1])


def f17_undeclared_record_field(p):
    return recs(p, 0, lambda r: (r[0].__setitem__("bonus", 1), "cell 0 rec 0 gains 'bonus'")[1])


def f18_bool_summary_count(p):
    def f(d):
        d["cells"][3]["strict_rounds"] = bool(d["cells"][3]["strict_rounds"])
        return f"row 3 strict_rounds int -> {d['cells'][3]['strict_rounds']}"
    return P2.summary(p, f)


# id, mutation, bypass, expected status, required "where|field|check" fragments, required missing fragments,
# min cells performed, run against r2 too
F_CASES = [
    ("F01_codex_candidate_bool", f01_codex_candidate_bool, True, "INVALID",
     ["cell_00|record[0].decodable|bool required", "cell_00|record[0].K_candidate|int in [1, N]"], [], 24, True),
    ("F02_codex_candidate_metadata", f02_codex_candidate_metadata, True, "INVALID",
     ["cell_00|record[0].cell_id|value 999", "cell_00|candidate[0].candidate.g|value 'invented'"], [], 24, True),
    ("F03_codex_summary_both_bool", f03_codex_summary_both_bool, True, "INVALID",
     ["cell_00|cell.summary.baselines.identity.task_sufficient|type int != expected bool",
      "summary|cells[0].baselines.identity.task_sufficient|type int != expected bool"], [], 24, True),
    ("F04_record_ratio_float", f04_record_ratio_float, True, "INVALID", ["cell_00|record[0].K_ratio|"], [], 24, False),
    ("F05_summary_ratio_float", f05_summary_ratio_float, True, "INVALID",
     ["summary|cells[0].K_star_over_N.num|type float != expected int"], [], 24, False),
    ("F06_null_not_allowed", f06_null_not_allowed, True, "INVALID", ["cell_00|record[1].is_control|bool required"], [], 24, False),
    ("F07_value_where_null_required", f07_value_where_null_required, True, "INVALID",
     ["cell_00|record[1].K_ratio|{num:int>0, den:int>0} iff task_sufficient, else null"], [], 24, False),
    ("F08_alpha_declaration_metadata", f08_alpha_declaration_metadata, True, "INVALID",
     ["M1/candidate_alphas|candidates[3].candidate.g|value 'x'"], [], 24, False),
    ("F09a_record_field_missing", f09a_record_field_missing, True, "INVALID",
     ["cell_00|record[0].closed|missing required field"], [], 24, False),
    ("F09b_cell_field_missing", f09b_cell_field_missing, True, "INVALID", ["cell_02|cell.coarsening|missing required field"], [], 23, False),
    ("F09c_fixture_K_missing", f09c_fixture_K_missing, True, "INVALID", ["FX1|fixture.K|missing required field"], [], 24, False),
    ("F10a_closure_witness_shape", f10a_closure_witness_shape, True, "INVALID", ["cell_00|record[1].closure_witnesses|"], [], 24, False),
    ("F10b_failing_actions_float", f10b_failing_actions_float, True, "INVALID", ["cell_00|record[1].failing_actions|"], [], 24, False),
    ("F10c_conflict_pair_string", f10c_conflict_pair_string, True, "INVALID", ["cell_00|record[1].decode_conflict|"], [], 24, False),
    ("F11_paired_summary_value", f11_paired_summary_value, True, "INVALID",
     ["cell_00|cell.summary.K0|value", "summary|cells[0].K0|value"], [], 24, True),
    ("F12_invalid_with_missing", f12_invalid_with_missing, True, "INVALID",
     ["cell_00|record[0].decodable|bool required"], ["cell_05|cell_05.jsonl", "candidates|135 declared records"], 24, False),
    ("F13_top_level_float", f13_top_level_float, True, "INVALID", ["summary|n_cells|type float != expected int"], [], 24, True),
    ("F14_cell_scalar_value", f14_cell_scalar_value, True, "INVALID", ["cell_00|cell.model|value 'M2'"], [], 23, False),
    ("F15_witness_name", f15_witness_name, True, "INVALID", ["cell_00|witnesses[0].word_names[0]|value 'tick'"], [], 23, False),
    ("F16_action_decl_bool", f16_action_decl_bool, True, "INVALID", ["M1|actions[1].c|type bool != expected int"], [], 16, False),
    ("F17_undeclared_record_field", f17_undeclared_record_field, True, "INVALID",
     ["cell_00|record[0].bonus|undeclared field"], [], 24, False),
    ("F18_bool_summary_count", f18_bool_summary_count, True, "INVALID",
     ["summary|cells[3].strict_rounds|type bool != expected int"], [], 24, True),
    ("F19_codex_candidate_bool_normal_mode", f01_codex_candidate_bool, False, "INVALID",
     ["seal||sealed artifact candidates/cell_00.jsonl: present bytes differ", "cell_00|record[0].decodable|bool required"], [], 24, False),
]


def hist_copy(scratch, cid):
    d = os.path.join(scratch, cid, "historical_inputs")
    shutil.copytree(HIST, d)
    for dp, dns, fns in os.walk(d):
        for x in dns + fns:
            os.chmod(os.path.join(dp, x), 0o755 if x in dns else 0o644)
    os.chmod(d, 0o755)
    return d


def h_corrupt(d):
    p = os.path.join(d, "GOVERNANCE", "CORE.md")
    open(p, "ab").write(b" ")
    return "snapshot GOVERNANCE/CORE.md + 1 byte"


def h_extra(d):
    open(os.path.join(d, "index-deconvolution", "src", "extra.py"), "w").write("")
    return "snapshot gains index-deconvolution/src/extra.py"


def h_missing(d):
    os.remove(os.path.join(d, "index-deconvolution", "src", "deconvolution.py"))
    return "snapshot loses index-deconvolution/src/deconvolution.py"


def h_substitute(d):
    src = os.path.join(BASE, "review_closure", "task-compaction-v1-r1", "isolated", "index-deconvolution", "src",
                       "deconvolution.py")
    shutil.copyfile(src, os.path.join(d, "index-deconvolution", "src", "deconvolution.py"))
    return "snapshot deconvolution.py replaced by the reviewed (to-be-adopted) owner"


# id, root mutation (None = pristine snapshot copy, "repo" = default current root), status, invalid frags, missing frags
H_CASES = [
    ("H01_default_current_root", "repo", "VALID_COMPLETE", [], []),
    ("H02_explicit_historical_root", None, "VALID_COMPLETE", [], []),
    ("H03_snapshot_corrupted", h_corrupt, "INVALID", ["freeze||identity mismatch inputs/GOVERNANCE/CORE.md"], []),
    ("H04_snapshot_extra_file", h_extra, "INVALID", ["freeze||undeclared file in explicit inputs root: index-deconvolution/src/extra.py"], []),
    ("H05_snapshot_missing_file", h_missing, "INCOMPLETE", [], ["inputs/index-deconvolution/src/deconvolution.py"]),
    ("H06_snapshot_substituted_owner", h_substitute, "INVALID", ["freeze||identity mismatch inputs/index-deconvolution/src/deconvolution.py"], []),
]


def run(audit, prod, out, bypass, root=None):
    cmd = [PY, audit, prod, out] + (["--bypass-integrity"] if bypass else []) + (["--inputs-root", root] if root else [])
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    p = subprocess.run(cmd, capture_output=True, text=True, env=dict(env, PYTHONDONTWRITEBYTECODE="1"), cwd="/tmp")
    f = os.path.join(out, "audit.json")
    return p, (json.load(open(f)) if os.path.exists(f) else None)


def flat(i):
    return f"{i.get('where', '')}|{i.get('field', '')}|{i.get('check', '')}"


def judge(p, a, want, inv, mis, min_cells):
    row = {"exit_code": p.returncode, "traceback": "Traceback" in p.stderr, "status": a and a["status"]}
    if not a:
        row.update(as_required=False, stderr_tail=p.stderr[-800:])
        return row
    ok_inv = {f: any(f in flat(i) for i in a["invalid"]) for f in inv}
    ok_mis = {f: any(f in f"{i['where']}|{i['missing']}" for i in a["missing"]) for f in mis}
    cells = a.get("counts", {}).get("cells", {}).get("performed", 0)
    agg = a.get("aggregates", {}).get("evaluated")
    row.update({"n_invalid": a["n_invalid"], "n_missing": a["n_missing"], "invalid": a["invalid"][:8],
                "missing": a["missing"][:6], "skipped": a["skipped"][:6], "cells_performed": cells,
                "required_invalid_found": ok_inv, "required_missing_found": ok_mis,
                "aggregates_evaluated": agg})
    row["as_required"] = (a["status"] == want and all(ok_inv.values()) and all(ok_mis.values())
                          and not row["traceback"] and cells >= min_cells
                          and (p.returncode == 0) == (want == "VALID_COMPLETE")
                          and agg is (want == "VALID_COMPLETE"))
    return row


H01_POST = ("H01_default_current_root", "repo", "INVALID",
            ["freeze||identity mismatch inputs/GOVERNANCE/CORE.md under current_repository",
             "freeze||identity mismatch inputs/index-deconvolution/src/deconvolution.py under current_repository"], [])


def main(scratch, result, post=False):
    root_pf = HIST if post else None
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
        shutil.copy(src if os.path.exists(src) else os.devnull, os.path.join(result, f"{cid}.audit_r3.json"))
        extra = f"  | audit_r2: {row['audit_r2']['status']} invalid={row['audit_r2']['n_invalid']}" if "audit_r2" in row else ""
        print(f"{cid:42s} {row['status']!s:15s} {'as required' if row['as_required'] else 'NOT AS REQUIRED'}{extra}")

    for cid, item, mut, bypass, want, inv, mis in P2.CASES:          # group P
        prod = os.path.join(scratch, cid, "production")
        shutil.copytree(PROD, prod)
        change = mut(prod) if mut else "none"
        inv = R3_FRAG.get(cid, inv)
        p, a = run(R3, prod, os.path.join(scratch, cid, "audit_r3"), bypass, root_pf)
        row = {"group": "P", "id": cid, "protocol_item": item, "change": change, "bypass_integrity": bypass,
               "expected_status": want, **judge(p, a, want, inv, mis, 0)}
        if a and cid.startswith("M10c"):
            fx = a.get("fixture_FX1", {})
            row["fx1_validity_minimality"] = [fx.get("validity"), fx.get("minimality")]
            row["as_required"] &= fx.get("validity") is True and fx.get("minimality") is False
        if a and cid == "M06a_candidates_malformed":
            row["as_required"] &= a["counts"]["cells"]["performed"] == 24
        record(row, cid, os.path.join(scratch, cid, "audit_r3"))
    for cid, mut, bypass, want, inv, mis, min_cells, vs_r2 in F_CASES:      # group F
        prod = os.path.join(scratch, cid, "production")
        shutil.copytree(PROD, prod)
        change = mut(prod)
        p, a = run(R3, prod, os.path.join(scratch, cid, "audit_r3"), bypass, root_pf)
        row = {"group": "F", "id": cid, "change": change, "bypass_integrity": bypass, "expected_status": want,
               **judge(p, a, want, inv, mis, min_cells)}
        if vs_r2 and not post:
            p2, a2 = run(R2, prod, os.path.join(scratch, cid, "audit_r2"), bypass)
            row["audit_r2"] = {"exit_code": p2.returncode, "status": a2 and a2["status"],
                               "n_invalid": a2 and a2["n_invalid"], "n_missing": a2 and a2["n_missing"],
                               "invalid": (a2 or {}).get("invalid", [])[:4]}
        record(row, cid, os.path.join(scratch, cid, "audit_r3"))
    for cid, mut, want, inv, mis in ([H01_POST] + H_CASES[1:] if post else H_CASES):                                 # group H
        root = None
        change = "default (current repository) inputs root"
        if mut != "repo":
            root = hist_copy(scratch, cid)
            change = mut(root) if mut else "pristine copy of finalization/historical_inputs"
        p, a = run(R3, PROD, os.path.join(scratch, cid, "audit_r3"), False, root)
        row = {"group": "H", "id": cid, "change": change, "expected_status": want, **judge(p, a, want, inv, mis, 24)}
        if a:
            row["freeze_roots"] = a.get("freeze_roots")
        record(row, cid, os.path.join(scratch, cid, "audit_r3"))
    doc = {"post_adoption": post, "n": len(rows), "as_required": sum(r["as_required"] for r in rows),
           "by_group": {g: [sum(r["as_required"] for r in rows if r["group"] == g),
                            sum(r["group"] == g for r in rows)] for g in "PFH"}, "cases": rows}
    json.dump(doc, open(os.path.join(result, "matrix.json"), "w"), indent=1, sort_keys=True)
    print(f"as required {doc['as_required']} / {doc['n']}  by group {doc['by_group']}")
    return 0 if doc["as_required"] == doc["n"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], "--post-adoption" in sys.argv[3:]))
