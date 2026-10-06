"""task-compaction-v1-r1 review closure -- the declared finite R1 test matrix (PROTOCOL R1, 1-10).

Every case runs on a COPY of the saved production in a fresh scratch directory; the
original evidence is only read.  The four original corruptions are the frozen
src/corruptions.py functions, imported by path.  The three Codex probes also run against
the frozen audit, to show that it fails for the reasons the review gives.
Usage: python probe_matrix.py <fresh scratch dir> <result dir inside the closure>
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
CLOSURE = os.path.dirname(HERE)
ORIG = os.path.abspath(os.path.join(CLOSURE, "..", "..", "task-compaction-v1-r1"))
PROD = os.path.join(ORIG, "production")
REPO = os.path.abspath(os.path.join(ORIG, *[".."] * 4))
PY = os.path.join(REPO, "venv", "bin", "python")
NEW, OLD = os.path.join(HERE, "audit_r2.py"), os.path.join(ORIG, "src", "audit.py")
_spec = importlib.util.spec_from_file_location("corruptions_v1_frozen", os.path.join(ORIG, "src", "corruptions.py"))
COR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(COR)


def jrw(path, fn, compact=False):
    d = json.load(open(path))
    change = fn(d)
    with open(path, "w") as fh:
        json.dump(d, fh, **({"sort_keys": True, "separators": (",", ":")} if compact else {}))
    return change


def summary(p, fn):
    return jrw(os.path.join(p, "summary.json"), fn)


def cell(p, i, fn):
    return jrw(os.path.join(p, "cells", f"cell_{i:02d}.json"), fn, compact=True)


def c2_empty(p):
    return summary(p, lambda d: (d.__setitem__("cells", []), "summary.cells = []")[1])


def c2_omit(p):
    return summary(p, lambda d: (d["cells"].pop(7), "summary row for cell 7 removed")[1])


def c3_dup(p):
    return summary(p, lambda d: (d["cells"].append(dict(d["cells"][2])), "row for cell 2 duplicated")[1])


def c3_undeclared(p):
    def f(d):
        r = json.loads(json.dumps(d["cells"][2]))
        r["cell"]["cell_id"] = 99
        d["cells"].append(r)
        return "extra row with undeclared cell_id 99"
    return summary(p, f)


def c4_value(p):
    def f(d):
        d["cells"][5]["K_star"] += 1
        return "summary row cell 5: K_star + 1"
    return summary(p, f)


def c5_no_m1(p):
    os.remove(os.path.join(p, "tables", "M1.json"))
    return "tables/M1.json removed"


def c6_jsonl(p):
    with open(os.path.join(p, "candidates", "cell_00.jsonl"), "w") as fh:
        fh.write("{broken json\n")
    return "candidates/cell_00.jsonl replaced by one malformed line"


def c6_jsonl_line(p):
    path = os.path.join(p, "candidates", "cell_01.jsonl")
    lines = open(path).read().split("\n")
    lines[4] = lines[4][:-5]
    open(path, "w").write("\n".join(lines))
    return "candidates/cell_01.jsonl line 5 truncated; other lines intact"


def c6_table(p):
    with open(os.path.join(p, "tables", "M2.json"), "w") as fh:
        fh.write('{"n": 8, "tables": [[0, 1,')
    return "tables/M2.json truncated mid-array"


def c7(p):
    os.remove(os.path.join(p, "cells", "cell_03.json"))
    return {"removed": "cells/cell_03.json",
            "decoder": cell(p, 4, lambda d: (d["decoder"].__setitem__(0, 1 - d["decoder"][0]), "cell 4 decoder[0] flipped")[1])}


def c8_summary_id(p):
    return summary(p, lambda d: (d["cells"][6]["cell"].pop("cell_id"), "summary row 6 lost cell.cell_id")[1])


def c8_record_id(p):
    path = os.path.join(p, "candidates", "cell_02.jsonl")
    lines = open(path).read().split("\n")
    r = json.loads(lines[0])
    r.pop("record_id")
    lines[0] = json.dumps(r)
    open(path, "w").write("\n".join(lines))
    return "cell_02.jsonl line 1 lost record_id"


def c8_alpha(p):
    return cell(p, 9, lambda d: (d["alpha"].__setitem__(3, "3"), "cell 9 alpha[3] = '3' (string)")[1])


def c8_stage(p):
    return cell(p, 10, lambda d: (d["stages"][1].pop(), "cell 10 stages[1] shortened by one")[1])


def c8_state(p):
    def f(d):
        d["alpha"][0] = d["N"]
        return "cell 11 alpha[0] = N (state index out of range)"
    return cell(p, 11, f)


def c8_bool(p):
    return cell(p, 12, lambda d: (d["witnesses"][0]["word"].__setitem__(0, True) if d["witnesses"] and d["witnesses"][0]["word"]
                                  else d["outputs"].__setitem__(0, True), "cell 12 bool where an integer is required")[1])


def c9_missing(p):
    os.remove(os.path.join(p, "candidates", "cell_07.jsonl"))
    return "sealed candidates/cell_07.jsonl removed"


def c9_modified(p):
    path = os.path.join(p, "summary.json")
    text = json.dumps(json.load(open(path))) + "\n"
    open(path, "w").write(text)
    return "summary.json re-serialised: same content, different bytes"


def cor(fn):
    def run(p):
        return fn(p, COR.pick_cell(p))[0]
    return run


# id, protocol item, mutation, bypass, expected status, required issue fragments (invalid / missing)
CASES = [
    ("M01_original", 1, None, False, "VALID_COMPLETE", [], []),
    ("M02a_summary_empty", 2, c2_empty, True, "INCOMPLETE", [], ["row for cell"]),
    ("M02b_summary_row_omitted", 2, c2_omit, True, "INCOMPLETE", [], ["row for cell 7"]),
    ("M03a_summary_duplicate", 3, c3_dup, True, "INVALID", ["duplicate cell 2"], []),
    ("M03b_summary_undeclared", 3, c3_undeclared, True, "INVALID", ["undeclared cell 99"], []),
    ("M04_summary_value", 4, c4_value, True, "INVALID", ["cell 5: field K_star"], []),
    ("M05_table_M1_removed", 5, c5_no_m1, True, "INCOMPLETE", [], ["M1.json"]),
    ("M06a_candidates_malformed", 6, c6_jsonl, True, "INVALID", ["cell_00.jsonl line 1"], []),
    ("M06b_candidates_one_bad_line", 6, c6_jsonl_line, True, "INVALID", ["cell_01.jsonl line 5"], []),
    ("M06c_table_malformed", 6, c6_table, True, "INVALID", ["malformed JSON in M2.json"], []),
    ("M07_missing_cell_and_wrong_decoder", 7, c7, True, "INVALID", ["decoder value check"], ["cell artifact"]),
    ("M08a_summary_id_missing", 8, c8_summary_id, True, "INVALID", ["missing or non-integer cell.cell_id"], []),
    ("M08b_record_id_missing", 8, c8_record_id, True, "INVALID", ["missing or non-integer record_id"], []),
    ("M08c_alpha_type", 8, c8_alpha, True, "INVALID", ["schema: alpha vector"], []),
    ("M08d_stage_length", 8, c8_stage, True, "INVALID", ["schema: stage vectors"], []),
    ("M08e_state_index", 8, c8_state, True, "INVALID", ["schema: alpha vector"], []),
    ("M08f_bool_index", 8, c8_bool, True, "INVALID", ["schema:"], []),
    ("M09a_sealed_missing_normal", 9, c9_missing, False, "INCOMPLETE", [], ["sealed artifact candidates/cell_07.jsonl"]),
    ("M09b_sealed_modified_normal", 9, c9_modified, False, "INVALID", ["sealed artifact summary.json"], []),
    ("M10a_COR1_decoder_value", 10, cor(COR.cor1), True, "INVALID", ["decoder value check"], []),
    ("M10b_COR2_macro_entry", 10, cor(COR.cor2), True, "INVALID", ["macro-transition check"], []),
    ("M10c_COR3_identity_certificate", 10, cor(COR.cor3), True, "INVALID", ["stage-induction check"], []),
    ("M10d_COR4_remove_and_corrupt", 10, cor(COR.cor4), True, "INVALID", ["reported numbers differ"], ["cell artifact"]),
]
CODEX = {"M02a_summary_empty": "VALID_COMPLETE accepted with zero summary rows",
         "M05_table_M1_removed": "INVALID although only evidence is missing",
         "M06a_candidates_malformed": "uncaught JSONDecodeError, no audit record"}


def run(audit, prod, out, bypass):
    cmd = [PY, audit, prod, out] + (["--bypass-integrity"] if bypass else [])
    p = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    f = os.path.join(out, "audit.json")
    return p, (json.load(open(f)) if os.path.exists(f) else None)


def main(scratch, result):
    for d in (scratch, result):
        if os.path.exists(d):
            print(f"refusing: {d} exists")
            return 2
    os.makedirs(scratch)
    os.makedirs(result)
    rows = []
    for cid, item, mut, bypass, want, inv, mis in CASES:
        prod = os.path.join(scratch, cid, "production")
        shutil.copytree(PROD, prod)
        change = mut(prod) if mut else "none"
        p, a = run(NEW, prod, os.path.join(scratch, cid, "audit_r2"), bypass)
        row = {"id": cid, "protocol_item": item, "change": change, "bypass_integrity": bypass,
               "expected_status": want, "exit_code": p.returncode,
               "traceback": "Traceback" in p.stderr, "status": a and a["status"]}
        if a:
            ok_inv = all(any(f in i["check"] or f in i["where"] for i in a["invalid"]) for f in inv)
            ok_mis = all(any(f in i["missing"] or f in i["where"] for i in a["missing"]) for f in mis)
            row.update({"n_invalid": a["n_invalid"], "n_missing": a["n_missing"], "invalid": a["invalid"][:6],
                        "missing": a["missing"][:6], "skipped": a["skipped"][:6],
                        "counts": {k: v for k, v in a["counts"].items() if v["intended"] is not None},
                        "aggregates_evaluated": a["aggregates"]["evaluated"] if "aggregates" in a else None,
                        "required_invalid_found": ok_inv, "required_missing_found": ok_mis})
            if cid.startswith("M10c"):
                fx = a.get("fixture_FX1", {})
                row["fx1_validity_minimality"] = [fx.get("validity"), fx.get("minimality")]
                ok_inv = ok_inv and fx.get("validity") is True and fx.get("minimality") is False
            if cid == "M06a_candidates_malformed":   # independent evidence still checked
                ok_inv = ok_inv and a["counts"]["cells"]["performed"] == 24
            if cid == "M05_table_M1_removed":
                ok_inv = ok_inv and a["counts"]["action_tables"]["performed"] < a["counts"]["action_tables"]["intended"]
            row["as_required"] = (a["status"] == want and ok_inv and ok_mis and not row["traceback"]
                                  and (p.returncode == 0) == (want == "VALID_COMPLETE")
                                  and (a["aggregates"]["evaluated"] is (want == "VALID_COMPLETE")))
        else:
            row["as_required"] = False
            row["stderr_tail"] = p.stderr[-800:]
        if cid in CODEX:
            po, ao = run(OLD, prod, os.path.join(scratch, cid, "audit_v1_frozen"), bypass)
            row["frozen_audit"] = {"defect_reported_by_review": CODEX[cid], "exit_code": po.returncode,
                                   "status": ao and ao["status"], "traceback": "Traceback" in po.stderr,
                                   "stderr_last_line": (po.stderr.strip().splitlines() or [""])[-1][:200],
                                   "invalid": (ao or {}).get("invalid", [])[:3]}
        rows.append(row)
        print(f"{cid:40s} {row['status']!s:15s} {'as required' if row['as_required'] else 'NOT AS REQUIRED'}"
              + (f"  | frozen audit: {row['frozen_audit']['status']} tb={row['frozen_audit']['traceback']}"
                 if cid in CODEX else ""))
        shutil.copy(os.path.join(scratch, cid, "audit_r2", "audit.json") if a else os.devnull,
                    os.path.join(result, f"{cid}.audit_r2.json"))
    doc = {"n": len(rows), "as_required": sum(r["as_required"] for r in rows), "cases": rows}
    json.dump(doc, open(os.path.join(result, "matrix.json"), "w"), indent=1, sort_keys=True)
    print(f"as required {doc['as_required']} / {doc['n']}")
    return 0 if doc["as_required"] == doc["n"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
