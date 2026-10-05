"""HID-search-v3a commands (run from ``index-deconvolution/``)::

  P="PYTHONPATH=experiments:.:../src ../venv/bin/python -B -m search_v3a.prospective"
  $P preflight            packet re-check, integration equalities, exposure inventory
  $P freeze               freeze_v2.write for search-v3a:search-confirm-v3a-r1
  $P run [--resume]       generate the 256 reserved strings (validated freeze only) and
                          execute the fixed 2,816-job queue (+256 portfolio rows)
  $P report               validation, primary decision, descriptive tables, REPORT.md
  $P verify               read-only re-validation, recomputed summary, decoder sample

Development lives in ``search_v3a.development``; the arithmetic audit in
``search_v3a.audit``; the controller span ledger in ``search_v3a.ledger``.
Exit codes: 0 complete and valid (any verdict), 2 invalid, 3 incomplete.
"""
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
import time
from pathlib import Path

from hierarchy import benchmark as B
from hierarchy import freeze_v2
from hierarchy import report_v3a as R3
from hierarchy import validation as V
from hierarchy.study import get_study

from . import ledger

ID_ROOT = Path(__file__).resolve().parents[2]
REPO = ID_ROOT.parent
PACKET = ID_ROOT / "protocols" / "hierarchy_search_v3a"
RUN_ID = "search-confirm-v3a-r1"
STUDY = "search-v3a"
EXIT_OK, EXIT_INVALID, EXIT_INCOMPLETE = 0, 2, 3
MARKERS = ("search_v3a_confirmation", "search_v3a_transfer", "search_v3a_stress",
           "search_v3a_controls")
KEY_PATTERNS = ("boundary-F12-4096-60", "boundary_large-F12-", "boundary_stress-S02-",
                "controls-F0", "controls-F1", "|F12|4096|60", "|F12|16384|70", "|F12|65536|70",
                "|F12|131072|70", "|S02|4096|80", "|S02|65536|80")


def _study():
    return get_study(STUDY)


def _write_json(path: Path, obj) -> None:
    B.atomic_write(path, (json.dumps(obj, indent=1, sort_keys=True, default=float) + "\n").encode())


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------

def exposure_inventory() -> dict:
    """Every local file naming a reserved namespace or a reserved case/unit key."""
    pats = list(MARKERS) + list(KEY_PATTERNS)
    roots = [ID_ROOT]
    cmd = ["grep", "-rIlF", "--exclude-dir=__pycache__", "--exclude-dir=.git",
           "--exclude-dir=venv", *sum((["-e", p] for p in pats), [])] + [str(r) for r in roots]
    out = subprocess.run(cmd, capture_output=True, text=True)
    files = sorted(Path(f).relative_to(REPO).as_posix() for f in out.stdout.split())
    allowed_prefix = ("index-deconvolution/protocols/hierarchy_search_v3a/",
                      "index-deconvolution/PROTOCOL_hierarchy_search_v3a.md",
                      "index-deconvolution/KICKOFF_hierarchy_search_v3a.md",
                      "index-deconvolution/hierarchy/", "index-deconvolution/experiments/search_v3a/",
                      "index-deconvolution/results/hierarchy_search_v3a/search-confirm-v3a-r1/ledger/",
                      "index-deconvolution/results/hierarchy_search_v3a/search-confirm-v3a-r1/prefreeze/")
    drafts = ("NEXT_PROTOCOL_DRAFT.md",
              # prose diff of that draft (review closure of search-diagnosis-v1)
              "search-diagnosis-v1-r1/patches/R1R2_prose_corrections.informational.diff")
    classified = []
    for f in files:
        if f.startswith(allowed_prefix):
            kind = "protocol_or_source_mention"
        elif f.endswith(drafts):
            kind = "protocol_draft_mention"
        else:
            kind = "REVIEW"
        classified.append({"path": f, "class": kind})
    review = [c for c in classified if c["class"] == "REVIEW"]
    generated = [c for c in review if any(s in c["path"] for s in
                                          ("/rows/", "cases.jsonl", "corpus_manifest", "/archives/",
                                           "/traces/", "/logs/"))]
    return {"patterns": pats, "searched": [str(r.relative_to(REPO)) for r in roots],
            "grep_exit": out.returncode, "files": classified, "needs_review": review,
            "generated_artifacts_mentioning": generated,
            "exposed": bool(generated),
            "definition": "mentions in protocol drafts/sources are not exposure; generated rows, "
                          "manifests, archives, traces or logs naming a reserved namespace or key "
                          "would be"}


def cmd_preflight(a) -> int:
    out = ID_ROOT / "results/hierarchy_search_v3a" / RUN_ID / "prefreeze"
    out.mkdir(parents=True, exist_ok=True)
    pk = subprocess.run([sys.executable, "-B", str(PACKET / "check_packet.py")], cwd=REPO,
                        capture_output=True, text=True)
    pkr = json.loads(pk.stdout)
    from . import preserve
    integ = preserve.integration_equalities()
    exp = exposure_inventory()
    exp_freeze = freeze_v2.exposure_check(_study(), _study().run_dir(RUN_ID))
    res = {"packet_check": pkr, "packet_check_exit": pk.returncode,
           "packet_expected_post_edit_failures": sorted(k for k, v in pkr["checks"].items() if not v),
           "integration": {k: integ[k] for k in ("denominator", "passed", "all_equal")},
           "exposure_inventory": exp, "freeze_exposure_check": exp_freeze}
    allowed = {"source_hashes_unchanged", "new_run_not_started", "notebook20_unoccupied"}
    # Protected files that changed: only the BDM workstream's notebook 19 pair may differ,
    # and only as a disclosed concurrent change by another workstream (never reverted).
    init = json.loads((PACKET / "INITIAL_SOURCE_STATE.json").read_text())
    changed = sorted(k for k, v in init["protected_file_hashes"].items()
                     if not (REPO / k).is_file() or B.sha256_file(REPO / k) != v)
    external = {"index-deconvolution/notebooks/build_19.py",
                "index-deconvolution/notebooks/19_bdm_and_index_complexity.ipynb"}
    res["protected_changed"] = changed
    res["protected_changed_external_disclosed"] = {
        k: {"mtime_local": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime((REPO / k).stat().st_mtime)),
            "owner": "BDM workstream (notebook 19 allocation, INITIAL_SOURCE_STATE note)",
            "attribution": "not written by this phase; not reverted; outside the study closure"}
        for k in changed if k in external}
    if changed and set(changed) <= external:
        allowed.add("protected_file_hashes_unchanged")
    res["packet_unexpected_failures"] = sorted(set(res["packet_expected_post_edit_failures"]) - allowed)
    res["pass"] = (not res["packet_unexpected_failures"] and integ["all_equal"]
                   and not exp["exposed"] and exp_freeze["clean"])
    _write_json(out / "preflight.json", res)
    _write_json(out / "exposure_inventory.json", exp)
    print(json.dumps({"pass": res["pass"], "packet_post_edit_failures":
                      res["packet_expected_post_edit_failures"],
                      "integration": res["integration"], "review_files": len(exp["needs_review"]),
                      "exposed": exp["exposed"]}))
    return 0 if res["pass"] else 1


# ---------------------------------------------------------------------------
# freeze and run
# ---------------------------------------------------------------------------

def cmd_freeze(a) -> int:
    study = _study()
    pre = study.run_dir(RUN_ID) / "prefreeze"
    fr = freeze_v2.write(study, RUN_ID, pre)
    print(f"froze {study.name}:{RUN_ID}: sha256 {freeze_v2.freeze_sha(fr)}")
    return 0


def intended_cases() -> list[dict]:
    return json.loads((PACKET / "intended_cases.json").read_text())["cases"]


def cmd_run(a) -> int:
    study = _study()
    d = study.run_dir(RUN_ID)
    fr, fsha, problems = B.load_and_validate_freeze(RUN_ID, "benchmark", study)
    if problems:
        raise SystemExit("freeze validation failed: " + "; ".join(problems))
    budget = ledger.SpanBudget("prospective", f"run:{RUN_ID}")
    if budget.expired():
        raise SystemExit("prospective allowance exhausted; the run is preserved as is")
    all_cases = []
    for role in study.run_roles(RUN_ID):
        cases, manifest = study.role_cases(role, d)
        mp = d / f"corpus_manifest.{role}.jsonl"
        text = "\n".join(json.dumps(m, sort_keys=True) for m in manifest) + "\n"
        if mp.exists() and mp.read_text() != text:
            raise SystemExit(f"regenerated {role} corpus differs from the stored manifest")
        B.atomic_write(mp, text.encode())
        all_cases += cases
    want = [(c["case_id"], c["n_bits"]) for c in intended_cases()]
    have = [(c.case_id, len(c.bits)) for c in all_cases]
    if want != have:
        raise SystemExit("generated cases differ from intended_cases.json (membership/order)")
    dup = {}
    for c in all_cases:
        dup.setdefault(c.input_sha256, []).append(c.case_id)
    jobs = [{"case_id": c.case_id, "method": m} for c in all_cases for m in study.job_methods(c)]
    _write_json(d / "intended_jobs.json", {"jobs": jobs, "encoder_jobs": len(jobs),
                                           "derived_portfolio_rows": len(all_cases),
                                           "total_rows": len(jobs) + len(all_cases)})
    _write_json(d / "input_checks.json", {
        "strings": len(all_cases), "hash_duplicates": {h: v for h, v in dup.items() if len(v) > 1},
        "membership_and_order_equal_intended": True,
        "note": "duplicates are reported, never resampled"})
    with open(d / "attempts.jsonl", "a") as fh:
        fh.write(json.dumps({"event": "start", "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                             "resume": a.resume, "freeze_sha256": fsha}) + "\n")
    (d / "logs").mkdir(parents=True, exist_ok=True)
    logf = open(d / "logs" / "benchmark.log", "a")

    def log(m):
        logf.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {m}\n")
        logf.flush()
    t0 = time.time()
    stats = B.run_cases(all_cases, d, RUN_ID, fsha, a.resume, log, budget, study=study)
    logf.close()
    B._merge_outputs(d, study, RUN_ID)
    with open(d / "attempts.jsonl", "a") as fh:
        fh.write(json.dumps({"event": "end", "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                             "stats": stats, "wall_s": time.time() - t0}) + "\n")
    print(json.dumps(dict(stats, wall_s=round(time.time() - t0),
                          prospective_used_s=round(budget.elapsed()))))
    return 0


# ---------------------------------------------------------------------------
# report and verify
# ---------------------------------------------------------------------------

def _validate(purpose):
    study = _study()
    return V.validate_run(RUN_ID, study.run_roles(RUN_ID), frozen=True, study=study,
                          purpose=purpose)


def _csv(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode()


def build(val, ctx) -> tuple[dict, list, list]:
    d = _study().run_dir(RUN_ID)
    summary, strings, units = R3.summarise(val, ctx["design"], d)
    summary["freeze_sha256"] = ctx["freeze_sha256"]
    summary["freeze_problems"] = ctx.get("freeze_problems", [])
    return summary, strings, units


def decision_record(summary: dict) -> dict:
    p = summary["primary"]
    return {"study": STUDY, "run_id": RUN_ID, "freeze_sha256": summary["freeze_sha256"],
            "verdict": p["verdict"], "estimate_bits_per_input_bit": p.get("estimate_bits_per_input_bit"),
            "ci99": p.get("ci99"), "bootstrap": p.get("bootstrap"),
            "required_units": p["required_units"], "available_units": p["available_units"],
            "cells": p["cells"], "engineering_valid": p["engineering_valid"],
            "complete": p["complete"], "reason": p.get("reason"),
            "censored_baselines": summary["censored_baselines"],
            "portfolio_conclusion_blocked_by_censoring":
                summary["portfolio_conclusion_blocked_by_censoring"],
            "scope": "k=4 versus k=1 full HID on the fixed mixture of six declared cells; not "
                     "superiority over the portfolio, not all families, not causal identification",
            "status": "ready for Codex review; not yet accepted"}


def cmd_report(a) -> int:
    d = _study().run_dir(RUN_ID)
    fr = json.loads((d / "freeze.json").read_text())
    env = B.check_environment(fr.get("environment", {}), "report")
    if env:
        raise SystemExit("report refused, environment differs from the freeze: " + "; ".join(env))
    val, ctx = _validate("report")
    summary, strings, units = build(val, ctx)
    _write_json(d / "summary.json", summary)
    _write_json(d / "DECISION.json", decision_record(summary))
    B.atomic_write(d / "tables" / "per_string.csv", _csv(strings))
    B.atomic_write(d / "tables" / "per_unit.csv", _csv(units))
    B.atomic_write(d / "tables" / "per_cell.json",
                   (json.dumps(summary["cells"], indent=1) + "\n").encode())
    code = EXIT_INVALID if not val["engineering_valid"] else (
        EXIT_INCOMPLETE if not val["complete"] else EXIT_OK)
    print(json.dumps({"verdict": summary["primary"]["verdict"],
                      "estimate": summary["primary"].get("estimate_bits_per_input_bit"),
                      "ci99": summary["primary"].get("ci99"),
                      "engineering_valid": val["engineering_valid"], "complete": val["complete"],
                      "exit_code": code}))
    return code


def cmd_verify(a) -> int:
    from hierarchy.cli import _separate_process_sample
    study = _study()
    d = study.run_dir(RUN_ID)
    v = {"run_id": RUN_ID, "study": STUDY, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    _write_json(d / "verification.json", dict(v, status="not_verified",
                                              note="verification started and has not finished"))
    val, ctx = _validate(None)
    invalid, incomplete = list(val["invalid"]), list(val["incomplete"])
    pub = V.public(val)
    v["validation"] = {k: pub[k] for k in ("engineering_valid", "complete", "expected_rows",
                                           "present_rows", "archives_checked",
                                           "distinct_archives_decoded", "missing_units",
                                           "missing_methods", "duplicates", "unknown")}
    v["validation"]["censored"] = pub["censored"][:200]
    v["trace_checks"] = val.get("trace_checks", {}).get("trace_status_counts")
    v["freeze_sha256"], v["freeze_problems"] = ctx["freeze_sha256"], ctx.get("freeze_problems", [])
    rows = sorted((r for m in val["_index"].values() for r in m.values()),
                  key=lambda r: (r["case_id"], r["method"]))
    inputs = {}
    for role in study.run_roles(RUN_ID):
        inputs.update({c.case_id: c.bits for c in study.role_cases(role, d)[0]})
    v["separate_process_decode"] = _separate_process_sample(d, rows, inputs)
    if not v["separate_process_decode"].get("all_ok"):
        invalid.append("separate-process decoder sample failed or unavailable")
    for name in ("summary.json", "DECISION.json", "cases.jsonl", "corpus_manifest.jsonl",
                 "freeze.json", "source_snapshot.tar", "intended_jobs.json"):
        if not (d / name).exists():
            invalid.append(f"required artefact missing: {name}")
    fr = ctx.get("freeze") or {}
    v["environment_differences"] = {k: c for k, c in B.environment_comparison(
        fr.get("environment", {})).items() if not c["equal"]} if fr else {}
    saved = json.loads((d / "summary.json").read_text()) if (d / "summary.json").exists() else None
    if saved is not None:
        fresh, _, _ = build(val, ctx)
        fresh = json.loads(json.dumps(fresh, default=float))
        stale = sorted(k for k in set(fresh) | set(saved) if fresh.get(k) != saved.get(k))
        v["summary_recomputed"] = {"stale_keys": stale, "agrees": not stale}
        if stale:
            invalid.append(f"summary.json disagrees with the rows: {stale}")
        dec = json.loads((d / "DECISION.json").read_text()) if (d / "DECISION.json").exists() else None
        if dec != json.loads(json.dumps(decision_record(fresh), default=float)):
            invalid.append("DECISION.json disagrees with the recomputed decision")
    v["engineering_status"] = "invalid" if invalid else "valid"
    v["completeness"] = "incomplete" if incomplete else "complete"
    v["invalid_count"], v["incomplete_count"] = len(invalid), len(incomplete)
    v["invalid_reasons"], v["incomplete_reasons"] = invalid[:200], incomplete[:200]
    v["scientific_verdict"] = (saved or {}).get("primary", {}).get("verdict")
    code = EXIT_INVALID if invalid else (EXIT_INCOMPLETE if incomplete else EXIT_OK)
    v["exit_code"] = code
    v["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _write_json(d / "verification.json", v)
    print(json.dumps({k: v[k] for k in ("engineering_status", "completeness",
                                        "scientific_verdict", "exit_code")}))
    return code


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("preflight", "freeze", "run", "report", "verify"))
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args(argv)
    return {"preflight": cmd_preflight, "freeze": cmd_freeze, "run": cmd_run,
            "report": cmd_report, "verify": cmd_verify}[a.command](a)


if __name__ == "__main__":
    raise SystemExit(main())
