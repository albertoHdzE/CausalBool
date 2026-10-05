"""Negative checks for the R3 pipeline tests: do they catch the old defect and its variants?

Each probe copies the frozen report-r2 source into a fresh temporary tree (saved
artifacts reached through symlinks, read only), applies ONE change, runs
``tests/test_reporting_pipeline.py`` and records which tests fail and why.

  a1_reporting_code   analysis.py and report.py as used for a1's reports (the active
                      files), plus only the pipeline glue ``build`` the tests call
  M1..M6              single mutations of the repaired code

A probe passes when every expected test fails. Writes only verification/negative_probes.json
of this closure and its temporary trees.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLOSURE = HERE.parent
ID = CLOSURE.parents[3]
REPO = ID.parent
SRC = CLOSURE / "report-r2" / "source" / "search_diagnosis"
ACTIVE = ID / "experiments" / "search_diagnosis"
TEST = "experiments/search_diagnosis/tests/test_reporting_pipeline.py"

A1_GLUE = '''

def build(rec2, rec3, rec4, d1_cases, d1_tables, d1_problems, refs, ids):
    """Probe-only glue: the report-r2 pipeline order over the a1 reporting functions."""
    from . import analysis as A
    targets, controls, ids4 = ids["targets"], ids["controls"], ids["d4"]
    ids2 = sorted(targets + controls)
    d2 = A.d2_rows(rec2, ids2)
    s2 = A.d2_summary(d2, targets, controls)
    d3 = A.d3_rows(rec3, targets, d2, refs)
    d4 = A.d4_rows(rec4, ids4)
    s4 = A.d4_summary(d4, ids4)
    res = {"D2": A.resource_summary(rec2), "D3": A.resource_summary(rec3),
           "D4": A.resource_summary(rec4)}
    flags = A.decision_quantities(d1_cases, d2, s2, d3, d4, s4, res, targets, controls, ids4)
    dec, numbers = decision(flags, d1_tables, s2, s4, res, d1_problems)
    return {"d2_rows": d2, "d2_summary": s2, "d3_rows": d3, "d4_rows": d4, "d4_summary": s4,
            "resources": res, "flags": flags, "decision": dec, "key_numbers": numbers}
'''

MUTATIONS = {
    "M1_unavailable_B8_counted_as_zero_opportunity": (
        "analysis.py",
        '''        if "B8_bits" in row:
            row["opportunity_per_input_bit"]''',
        '''        if "B8_bits" not in row:
            row["opportunity_per_input_bit"] = 0.0
        if "B8_bits" in row:
            row["opportunity_per_input_bit"]''',
        ["test_d2_target_timeout_keeps_cell_partial_never_zero"]),
    "M2_incomplete_takes_precedence_over_invalid": (
        "report.py",
        '''    if not valid:
        rec = "INVALID"
    elif not complete:
        rec = "INCOMPLETE"''',
        '''    if not complete:
        rec = "INCOMPLETE"
    elif not valid:
        rec = "INVALID"''',
        ["test_invalid_takes_precedence_over_missing"]),
    "M3_unavailable_translation_counted_as_H_eq_T": (
        "analysis.py",
        '''            k["hid_loses_translation_unavailable"] += "T" not in r
            if "T" not in r:
                continue''',
        '''            k["hid_loses_translation_unavailable"] += 0
            if "T" not in r:
                k["hid_loses_and_H_eq_T"] += 1
                k["hid_loses_and_H_eq_T_identical_bytes"] += 1
                continue''',
        ["test_d4_graph_limit_of_portfolio_winner_is_unavailable_not_H_eq_T"]),
    "M4_wrong_decode_treated_as_unavailable": (
        "analysis.py",
        '''    if st == "error" and str(r.get("exception") or "").startswith("wrong_decode"):''',
        '''    if False:''',
        ["test_wrong_decode_is_invalid_not_unavailable"]),
    "M5_equal_length_read_as_equal_bytes": (
        "analysis.py",
        '''                               T_bytes_equal_H=r["archives"][m]["sha256"] ==
                               rows["hid_full"]["archive_sha256"],''',
        '''                               T_bytes_equal_H=True,''',
        ["test_complete_run_keeps_every_a1_number"]),
    "M6_rule_evaluated_on_partial_evidence": (
        "report.py",
        '''    elif not complete:
        rec = "INCOMPLETE"''',
        '''    elif False:
        rec = "INCOMPLETE"''',
        ["test_missing_d2_control_b8_is_incomplete_not_keyerror",
         "test_d2_target_timeout_keeps_cell_partial_never_zero",
         "test_d3_missing_record_is_partial",
         "test_d4_graph_limit_of_portfolio_winner_is_unavailable_not_H_eq_T",
         "test_d4_missing_job_removes_both_conversions"]),
}

A1_EXPECTED = {   # the supervisor's three probes, now as tests: the old code must raise these
    "test_missing_d2_control_b8_is_incomplete_not_keyerror": "KeyError: 'B8_bits'",
    "test_d3_missing_record_is_partial": "KeyError: 'cheapest_all'",
    "test_d4_graph_limit_of_portfolio_winner_is_unavailable_not_H_eq_T": "KeyError: 'T'",
}


def tree(tmp: Path) -> Path:
    idr = tmp / "index-deconvolution"
    (idr / "experiments").mkdir(parents=True)
    (idr / "results" / "hierarchy_search_diagnosis").mkdir(parents=True)
    shutil.copytree(SRC, idr / "experiments" / "search_diagnosis",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(ID / "experiments" / "preserve_confirm_v1_r1_sources.py", idr / "experiments")
    for p in ("hierarchy", "protocols", "PROTOCOL_hierarchy_search_diagnosis.md",
              "KICKOFF_hierarchy_search_diagnosis.md", "PROTOCOL_order_discovery.md",
              "results/hierarchy_search_v2", "results/hierarchy_search_diagnosis/search-diagnosis-v1-r1"):
        (idr / p).symlink_to(ID / p)
    return idr


def pytest(idr: Path) -> dict:
    t0 = time.monotonic()
    r = subprocess.run([str(REPO / "venv/bin/python"), "-m", "pytest", TEST, "-q", "--tb=line",
                        "-rf", "-p", "no:cacheprovider"], cwd=idr, capture_output=True, text=True,
                       env={"PYTHONPATH": f"experiments:.:{REPO / 'src'}",
                            "PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"}, check=False)
    failed = sorted(set(re.findall(r"FAILED \S+::(\w+)", r.stdout)))
    errors = {}
    for ln in r.stdout.splitlines():           # --tb=line: "<path>:<line>: <Exception>: <msg>"
        m = re.match(r"^(/\S+|\S+\.py):\d+: (.*)$", ln)
        if m:
            errors.setdefault("lines", []).append(m.group(2))
    return {"exit": r.returncode, "failed": failed, "summary": r.stdout.strip().splitlines()[-1],
            "error_lines": errors.get("lines", []), "elapsed_s": round(time.monotonic() - t0, 2)}


def main() -> int:
    out = {}
    base = Path(tempfile.mkdtemp(prefix="sd_closure_probes_"))
    idr = tree(base / "repaired")
    out["repaired_control"] = dict(pytest(idr), expected_failures=[])
    out["repaired_control"]["pass"] = out["repaired_control"]["exit"] == 0
    idr = tree(base / "a1_reporting_code")
    pk = idr / "experiments" / "search_diagnosis"
    shutil.copy(ACTIVE / "analysis.py", pk / "analysis.py")
    (pk / "report.py").write_text((ACTIVE / "report.py").read_text() + A1_GLUE)
    r = pytest(idr)
    r["expected_old_defects"] = A1_EXPECTED
    r["old_defects_raised"] = {t: any(e in ln for ln in r["error_lines"]) and t in r["failed"]
                               for t, e in A1_EXPECTED.items()}
    r["pass"] = all(r["old_defects_raised"].values())
    out["a1_reporting_code"] = r
    for name, (f, old, new, expect) in MUTATIONS.items():
        idr = tree(base / name)
        p = idr / "experiments" / "search_diagnosis" / f
        s = p.read_text()
        assert s.count(old) == 1, name
        p.write_text(s.replace(old, new))
        r = pytest(idr)
        r["expected_failures"] = expect
        r["pass"] = set(expect) <= set(r["failed"])
        out[name] = r
    shutil.rmtree(base)
    (CLOSURE / "verification" / "negative_probes.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: {"pass": v["pass"], "summary": v["summary"]} for k, v in out.items()},
                     indent=1))
    return 0 if all(v["pass"] for v in out.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
