"""HID-search-v3a fixed development on retained inputs (BENCHMARK.md section 1).

    PYTHONPATH=experiments:.:../src ../venv/bin/python -B -m search_v3a.development \
        run control|treatment RUN_ID [--resume]   |   compare CONTROL_RUN TREATMENT_RUN

``run`` executes the production runner (``hierarchy.benchmark.run_cases``, real
watchdog, ``python -S`` workers, trace sidecars) for one development study:
  control    hid_full (k = 1) on all 1,792 strings of search-confirm-v2-r1;
  treatment  hid_refine4 (k = 4) on the 208 fixed D2 strings (176 targets, 32 controls).
Inputs come only from decoding each retained raw archive (``search_diagnosis.common.
load_case``, hash-checked). ``compare`` writes the compatibility gate, the treatment
record check and the descriptive development comparison. No efficacy gate, no tuning.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from hierarchy import benchmark as B
from hierarchy import freeze_v2
from hierarchy import report_v3a as R3
from hierarchy.cli_v2 import DETERMINISTIC, _strip_timing
from hierarchy.corpus import Case
from hierarchy.study import get_study
from search_diagnosis.common import load_case, parse_case_id, saved_rows

from . import ledger

ID_ROOT = Path(__file__).resolve().parents[2]
PACKET = ID_ROOT / "protocols" / "hierarchy_search_v3a"
V2_RUN = ID_ROOT / "results" / "hierarchy_search_v2" / "search-confirm-v2-r1"
REFERENCES = V2_RUN / "diagnostics" / "boundary_reference" / "references.json"
STUDIES = {"control": "search-v3a-dev-control", "treatment": "search-v3a-dev-treatment"}
OUT = ID_ROOT / "results" / "hierarchy_search_v3a" / "development"


def contract() -> dict:
    return json.loads((PACKET / "contract.json").read_text())


def case_ids(kind: str) -> list[str]:
    dev = contract()["development"]
    if kind == "control":
        return list(dev["control_case_ids"])
    return list(dev["target_case_ids"]) + list(dev["control_case_ids_for_paired_comparison"])


def load_cases(ids) -> list[Case]:
    out = []
    for cid in ids:
        p = parse_case_id(cid)
        c = load_case(cid)
        out.append(Case(cid, p["role"], p["family"], p["base_length"], p["replicate"],
                        p["ragged"], c.bits))
    return out


def run(kind: str, run_id: str, resume: bool) -> int:
    study = get_study(STUDIES[kind])
    d = study.run_dir(run_id)
    d.mkdir(parents=True, exist_ok=True)
    fp = freeze_v2.dev_fingerprint(study)
    cases = load_cases(case_ids(kind))
    man = "\n".join(json.dumps({"case_id": c.case_id, "input_sha256": c.input_sha256,
                                "n_bits": len(c.bits), "source_run": str(V2_RUN.relative_to(ID_ROOT)),
                                "source": "retained raw archive, decoded and hash-checked"},
                               sort_keys=True) for c in cases) + "\n"
    mp = d / "inputs_manifest.jsonl"
    if mp.exists() and mp.read_text() != man:
        raise SystemExit("retained inputs differ from the stored manifest")
    B.atomic_write(mp, man.encode())
    budget = ledger.SpanBudget("development", f"dev:{kind}:{run_id}")
    t0 = time.time()
    with open(d / "attempts.jsonl", "a") as fh:
        fh.write(json.dumps({"event": "start", "run_id": run_id, "kind": kind, "fingerprint": fp,
                             "resume": resume, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                             "cases": len(cases)}) + "\n")
    stats = B.run_cases(cases, d, run_id, fp, resume, lambda m: None, budget, study=study)
    with open(d / "attempts.jsonl", "a") as fh:
        fh.write(json.dumps({"event": "end", "run_id": run_id, "stats": stats,
                             "wall_s": time.time() - t0}) + "\n")
    print(json.dumps({"run_id": run_id, "stats": stats, "wall_s": round(time.time() - t0),
                      "development_used_s": round(budget.elapsed())}))
    return 0


def _rows(study, run_id: str, ids) -> dict:
    d = study.run_dir(run_id)
    out = {}
    for cid in ids:
        p = d / "rows" / f"{cid}.json"
        out[cid] = {r["method"]: r for r in json.loads(p.read_text())} if p.exists() else {}
    return out


def compatibility(control_run: str) -> dict:
    """All 1,792 hid_full rows against the accepted search-v2 rows, field by field."""
    study = get_study(STUDIES["control"])
    d = study.run_dir(control_run)
    ids = case_ids("control")
    rows = _rows(study, control_run, ids)
    fields = DETERMINISTIC + ("config_sha256", "input_sha256", "n_bits")
    diffs, statuses, archives_ok = [], defaultdict(int), 0
    from hierarchy.search_v2 import ARMS
    for cid in ids:
        new = rows[cid].get("hid_full")
        old = saved_rows(cid)["hid_full"]
        if new is None:
            diffs.append({"case_id": cid, "field": "row_missing"})
            statuses["absent"] += 1
            continue
        statuses[new["status"]] += 1
        for k in fields:
            if new.get(k) != old.get(k):
                diffs.append({"case_id": cid, "field": k})
        if _strip_timing(new.get("search_counters")) != _strip_timing(old.get("search_counters")):
            diffs.append({"case_id": cid, "field": "search_counters (timing removed)"})
        if new.get("archive_path"):
            data = (d / new["archive_path"]).read_bytes()
            old_data = (V2_RUN / old["archive_path"]).read_bytes()
            if data == old_data and B.sha256_bytes(data) == new["archive_sha256"]:
                archives_ok += 1
            else:
                diffs.append({"case_id": cid, "field": "archive_bytes"})
    cfg = ARMS["hid_full"]
    old_cfg = json.loads((V2_RUN / "freeze.json").read_text())["method_configs"]["hid_full"]
    out = {"population": len(ids), "statuses": dict(statuses),
           "archives_byte_identical": archives_ok, "differences": diffs[:500],
           "difference_count": len(diffs),
           "fields_compared": list(fields) + ["search_counters (timing removed)", "archive_bytes"],
           "config_sha256_now": cfg.sha256(), "config_sha256_frozen_v2": old_cfg["sha256"],
           "config_dict_equal": cfg.as_dict() == old_cfg["config"]["search_config"],
           "excluded": "recorded timings (keys ending wall_s, encode/worker wall, RSS) and the new "
                       "separate trace fields"}
    out["pass"] = (out["archives_byte_identical"] == len(ids) == 1792 and not diffs
                   and statuses.get("ok") == len(ids) and out["config_dict_equal"]
                   and out["config_sha256_now"] == out["config_sha256_frozen_v2"])
    return out


def compare(control_run: str, treatment_run: str) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    comp = compatibility(control_run)
    B.atomic_write(OUT / "compatibility.json", json.dumps(comp, indent=1).encode())
    cst, tst = get_study(STUDIES["control"]), get_study(STUDIES["treatment"])
    ids = case_ids("treatment")
    targets = set(contract()["development"]["target_case_ids"])
    crow, trow = _rows(cst, control_run, ids), _rows(tst, treatment_run, ids)
    cdir, tdir = cst.run_dir(control_run), tst.run_dir(treatment_run)
    refs = {it["case_id"]: it for it in json.loads(REFERENCES.read_text())}
    records = []
    for cid in ids:
        p = parse_case_id(cid)
        a, b = crow[cid].get("hid_full"), trow[cid].get("hid_refine4")
        rec = {"case_id": cid, "cell": p["cell"], "unit": p["unit"], "target": cid in targets,
               "n_bits": (a or b or {}).get("n_bits"),
               "full_status": a and a["status"], "refine4_status": b and b["status"],
               "full_bits": a and a["archive_bits"], "refine4_bits": b and b["archive_bits"]}
        for name, row, dd in (("full", a, cdir), ("refine4", b, tdir)):
            rec[f"{name}_trace"] = R3.trace_summary(dd, row, refs.get(cid, {}).get("cuts"),
                                                    contract()["trace"]["supplied_cut_tolerance_bits"])
        records.append(rec)
    treat_ok = sum(1 for r in records if r["refine4_status"] in ("ok", "timeout_raw", "rss_limit_raw"))
    trace_ok = sum(1 for r in records if r["target"] and r["refine4_trace"]["status"] == "complete"
                   and r["full_trace"]["status"] == "complete")
    desc = R3.development_summary(records)
    gate = {"compatibility_pass": comp["pass"],
            "treatment_terminal_records": treat_ok, "treatment_population": len(ids),
            "treatment_errors": [r["case_id"] for r in records
                                 if r["refine4_status"] not in ("ok", "timeout_raw", "rss_limit_raw")],
            "paired_target_traces_complete": trace_ok, "paired_target_strings": len(targets),
            "trace_check_failures": [r["case_id"] for r in records
                                     for k in ("full_trace", "refine4_trace")
                                     if r[k].get("problems")]}
    gate["pass"] = (comp["pass"] and treat_ok == len(ids) == 208 and not gate["treatment_errors"]
                    and trace_ok == len(targets) == 176 and not gate["trace_check_failures"])
    B.atomic_write(OUT / "development_records.json", json.dumps(records, indent=1).encode())
    B.atomic_write(OUT / "development_summary.json", json.dumps(desc, indent=1).encode())
    B.atomic_write(OUT / "engineering_gate.json", json.dumps(gate, indent=1).encode())
    print(json.dumps({"engineering_gate": gate["pass"], "compatibility": comp["pass"],
                      "archives_identical": comp["archives_byte_identical"],
                      "differences": comp["difference_count"],
                      "treatment_terminal": treat_ok, "traces_complete": trace_ok}))
    return 0 if gate["pass"] else 1


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[0] == "run":
        return run(argv[1], argv[2], "--resume" in argv)
    if argv[0] == "compare":
        return compare(argv[1], argv[2])
    raise SystemExit(__doc__)


if __name__ == "__main__":
    raise SystemExit(main())
