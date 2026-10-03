"""Command implementations for non-legacy studies (``--study search-v2``).

Thin orchestration over the shared owners: ``benchmark`` (runner, workers, rows),
``validation.validate_run`` (the one gate shared by report and verify), ``report_v2``
(analysis adapter over ``report``), ``diagnostics_v2`` and ``freeze_v2``. Every
experimental job is charged to the study's durable execution ledger.

Exit codes as in cli.py: 0 complete and valid (any verdict), 2 invalid, 3 incomplete.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .cli import (EXIT_INCOMPLETE, EXIT_INVALID, EXIT_OK, _exit_code,
                  _separate_process_sample, _write_verification)
from .study import REPO, get_study


def _study(a):
    return get_study(a.study)


def _log(quiet: bool):
    return (lambda m: None) if quiet else print


def _result_rel(study) -> str:
    root = study.result_root.resolve()
    return root.relative_to(REPO).as_posix() if REPO in root.parents else \
        f"<result root of {study.name}>"


# ---------------------------------------------------------------------------
# selfcheck
# ---------------------------------------------------------------------------

def contract_check(study) -> dict:
    """The executable registry and constants agree with study_contract.json."""
    from .search_v2 import ARMS, ORIGINAL_GRID
    c = json.loads((REPO / "index-deconvolution/protocols/hierarchy_search_v2/"
                    "study_contract.json").read_text())
    out = {}
    out["hid_methods"] = list(study.hid_methods) == c["hid_methods"]
    out["baselines"] = list(study.baselines) == c["baseline_methods"]
    out["rows_per_case"] = len(study.all_methods) == c["rows_per_case"]
    out["stages"] = {k: list(v.stages) for k, v in ARMS.items()} == c["stages"]
    s, b = c["search"], c["boundary"]
    cfg = ARMS["hid_full"]
    out["search_constants"] = (
        list(ORIGINAL_GRID) == s["original_period_grid"] and cfg.period_max == s["period_max"]
        and cfg.residual_divisor == s["residual_divisor"]
        and cfg.local_block_bits == s["local_block_bits"]
        and cfg.local_patch_max == s["local_patch_max"] and cfg.max_rules == s["max_rules"]
        and cfg.max_depth == s["max_depth"]
        and cfg.consensus_tie_bit == s["consensus_tie_bit"]
        and cfg.first_local_candidate_cap == s["first_local_candidate_cap"]
        and cfg.consensus_local_candidate_cap == s["consensus_local_candidate_cap"]
        and cfg.consensus_global_candidate_cap == s["consensus_global_candidate_cap"]
        and len(ORIGINAL_GRID) + 256 + 256 == s["template_candidate_cap_total"])
    bc = cfg.boundary
    out["boundary_constants"] = (
        bc.max_segments == b["max_segments"] and bc.parent_min_bits == b["parent_min_bits"]
        and bc.child_min_bits == b["child_min_bits"]
        and bc.coarse_grid_denominator == b["coarse_grid_denominator"]
        and bc.max_refinement_levels == b["max_refinement_levels"]
        and bc.refinement_grid_denominator == b["refinement_grid_denominator"]
        and -bc.refinement_offset == b["refinement_offset_min"]
        and bc.refinement_offset == b["refinement_offset_max"]
        and bc.root_trial_cap == b["root_trial_cap_including_initial"]
        and bc.cached_leaf_cap == b["cached_leaf_cap"]
        and bc.length_charge_multiplier == b["shortest_period_length_charge_multiplier"])
    roles_ok = True
    for r, spec in c["roles"].items():
        rs = study.role(r)
        roles_ok &= (rs.rng_namespace == spec["rng_namespace"] and list(rs.families) == spec["families"]
                     and list(rs.base_lengths) == spec["base_lengths"]
                     and list(rs.replicates) == spec["replicates"]
                     and 2 * len(rs.families) * len(rs.base_lengths) * len(rs.replicates)
                     == spec["expected_strings"])
    out["roles"] = roles_ok
    res = study.resources
    out["resources"] = (res.wall_limit_s == c["resources"]["worker_wall_seconds"]
                        and res.rss_limit_bytes == c["resources"]["worker_rss_bytes"]
                        and res.max_workers == c["resources"]["max_workers"]
                        and res.allowance("development") == c["resources"]["development_wall_seconds"]
                        and res.allowance("reserved") == c["resources"]["reserved_wall_seconds"]
                        and res.allowance("diagnostics_verification")
                        == c["resources"]["diagnostics_verification_wall_seconds"])
    dev = c["development"]
    pilot = sum(2 * len(study.role(r).families) * len(study.role(r).base_lengths)
                * len(study.role(r).replicates) for r in study.run_roles("dev-search-v2-pilot"))
    reg = sum(2 * len(study.role(r).families) * len(study.role(r).base_lengths)
              * len(study.role(r).replicates) for r in study.run_roles("dev-search-v2-regression"))
    out["development_counts"] = pilot == dev["pilot_strings"] and reg == dev["regression_strings"]
    return out


def cmd_selfcheck(a) -> int:
    from .baselines import BASELINE_METHODS, encode_baseline
    from .decode import decode_archive
    from .model import Literal, Model, Repeat
    from .search_v2 import ARMS, infer_v2
    from .wire import encode_literal, serialize_model
    study = _study(a)
    checks = {}
    checks["golden_hid"] = serialize_model(Model((Literal("1"), Repeat(0, 8))), 8).hex() == \
        "4953443101080702000180020008"
    checks["golden_literal"] = encode_literal("0110").hex() == "4953443100040160"
    smoke = ["", "1", "0110" * 20, ("1" * 8 + "0") * 8, "1011001110001111" * 9 + "01",
             ("0" * 62 + "1") * 40]
    ok = True
    for s in smoke:
        for m in BASELINE_METHODS:
            ok &= decode_archive(encode_baseline(s, m)) == s
        prev = None
        for name, cfg in ARMS.items():
            r = infer_v2(s, cfg)
            ok &= decode_archive(r.archive) == s and r.archive_bits <= r.literal_bits
            ok &= prev is None or r.archive_bits <= prev
            prev = r.archive_bits
    checks["smoke_round_trips_and_nesting"] = ok
    with tempfile.TemporaryDirectory() as tmp:
        from . import decode as dmod
        shutil.copy(dmod.__file__, Path(tmp) / "decode.py")
        arc = infer_v2(smoke[5], ARMS["hid_full"]).archive
        (Path(tmp) / "a.bin").write_bytes(arc)
        out = subprocess.run([sys.executable, "-I", "-S", "decode.py", "a.bin"], cwd=tmp,
                             env={"PATH": os.environ.get("PATH", "")},
                             capture_output=True, text=True)
        checks["separate_process_decoder"] = (
            out.returncode == 0 and json.loads(out.stdout)[0]["bits"] == smoke[5])
    checks["contract"] = contract_check(study)
    print(json.dumps(checks, indent=1))
    flat = [v for v in checks.values() if not isinstance(v, dict)] + \
        list(checks["contract"].values())
    return 0 if all(flat) else 1


# ---------------------------------------------------------------------------
# development: pilot and regression (unfrozen, development fingerprint)
# ---------------------------------------------------------------------------

DETERMINISTIC = ("status", "archive_sha256", "archive_bits", "decode_ok", "selected_codec_id",
                 "selected_method", "rule_count", "dag_depth", "candidate_count",
                 "deterministic_work", "best_source", "trace")


def _strip_timing(t):
    if isinstance(t, dict):
        return {k: _strip_timing(v) for k, v in t.items() if not k.endswith("wall_s")}
    if isinstance(t, list):
        return [_strip_timing(v) for v in t]
    return t


def _development(a, kind: str, interrupt_after: int | None, replay_cases: int) -> int:
    from . import benchmark as B
    from . import freeze_v2
    from . import report_v2 as R2
    from . import validation as V
    study = _study(a)
    if not a.run_id.startswith(f"dev-search-v2-{kind}"):
        raise SystemExit(f"{kind} run ids must start with dev-search-v2-{kind}")
    d = study.run_dir(a.run_id)
    d.mkdir(parents=True, exist_ok=True)
    fp = freeze_v2.dev_fingerprint(study)
    roles = study.run_roles(a.run_id)
    budget = B.CategoryBudget(study, "development", kind, a.run_id)
    t0 = time.time()
    attempt = {"run_id": a.run_id, "kind": kind, "fingerprint": fp, "roles": roles,
               "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    fresh = not (d / "rows").exists()
    if fresh and interrupt_after:
        # deliberate interruption, then resume: the resume path is exercised for real
        B.benchmark(a.run_id, roles[0], resume=False, stop_after=interrupt_after,
                    require_freeze=False, study=study, budget=budget, fsha=fp,
                    log=_log(getattr(a, "quiet", False)))
    for role in roles:
        B.benchmark(a.run_id, role, resume=True if not fresh or interrupt_after else
                    getattr(a, "resume", False), require_freeze=False, study=study,
                    budget=budget, fsha=fp, log=_log(getattr(a, "quiet", False)))
    if replay_cases:
        cases, _ = study.role_cases(roles[0], d)
        rid = a.run_id + "-replay"
        rd = study.run_dir(rid)
        if rd.exists():
            raise SystemExit(f"{rd} exists; attempts are retained, choose a new run id")
        rd.mkdir(parents=True)
        B.run_cases(cases[:replay_cases], rd, rid, fp, False, lambda m: None, budget,
                    study=study)
        diffs = []
        for c in cases[:replay_cases]:
            x = {r["method"]: r for r in json.loads(B.case_rows_path(d, c).read_text())}
            y = {r["method"]: r for r in json.loads(B.case_rows_path(rd, c).read_text())}
            for m in x:
                for k in DETERMINISTIC + ("search_counters",):
                    if _strip_timing(x[m][k]) != _strip_timing(y[m][k]):
                        diffs.append({"case": c.case_id, "method": m, "field": k})
        B.atomic_write(d / "resume_check.json", json.dumps({
            "interrupted_after_cases": interrupt_after, "replayed_cases": replay_cases,
            "deterministic_fields": list(DETERMINISTIC) + ["search_counters (timing removed)"],
            "differences": diffs, "identical": not diffs}, indent=1).encode())
        print(f"resume/replay identical: {not diffs} ({len(diffs)} differences)")
    val, ctx = V.validate_run(a.run_id, roles, frozen=False, study=study, unfrozen_sha=fp)
    summary = R2.summarise(val, ctx["design"], d)
    summary["status"] = f"development {kind} (exploratory, previously inspected inputs; not confirmatory)"
    summary["fingerprint"] = fp
    summary["engineering_status"] = "valid" if val["engineering_valid"] else "invalid"
    summary["completeness"] = "complete" if val["complete"] else "incomplete"
    summary["search_v2_checks"] = {k: v for k, v in val.get("search_v2_checks", {}).items()
                                   if k != "resource_nesting_breaks"}
    B.atomic_write(d / "summary.json", json.dumps(summary, indent=1, default=float).encode())
    budget.save()
    attempt.update(finished_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   wall_s=time.time() - t0, engineering_valid=val["engineering_valid"],
                   complete=val["complete"], invalid=val["invalid"][:50],
                   development_seconds_used=budget.elapsed())
    with open(study.result_root / "development_attempts.jsonl", "a") as fh:
        fh.write(json.dumps(attempt, default=str) + "\n")
    print(json.dumps({"run_id": a.run_id, "engineering_valid": val["engineering_valid"],
                      "complete": val["complete"], "wall_s": round(time.time() - t0),
                      "development_s_used": round(budget.elapsed())}))
    return _exit_code(val)


def cmd_pilot(a) -> int:
    return _development(a, "pilot", a.interrupt_after, a.replay_cases)


def cmd_regression(a) -> int:
    return _development(a, "regression", None, 0)


# ---------------------------------------------------------------------------
# freeze, benchmark
# ---------------------------------------------------------------------------

def cmd_freeze(a) -> int:
    from . import freeze_v2
    study = _study(a)
    if a.run_id.startswith("dev"):
        raise SystemExit("development runs are not frozen")
    pre = Path(a.prefreeze_dir).resolve() if a.prefreeze_dir else study.result_root / "prefreeze"
    fr = freeze_v2.write(study, a.run_id, pre)
    print(f"froze {study.name}:{a.run_id}: sha256 {freeze_v2.freeze_sha(fr)}")
    return 0


def cmd_benchmark(a) -> int:
    from . import benchmark as B
    study = _study(a)
    if a.run_id.startswith("dev"):
        raise SystemExit("use pilot/regression for development runs")
    if a.split not in study.run_roles(a.run_id):
        raise SystemExit(f"run id {a.run_id} may benchmark only {study.run_roles(a.run_id)}")
    budget = B.CategoryBudget(study, "reserved", f"benchmark:{a.split}", a.run_id)
    if budget.expired():
        raise SystemExit("reserved execution allowance exhausted; the run is preserved as is")
    stats = B.benchmark(a.run_id, a.split, a.resume, log=_log(a.quiet), study=study,
                        budget=budget)
    budget.save()
    print(json.dumps(dict(stats, reserved_s_used=round(budget.elapsed()))))
    return 0


# ---------------------------------------------------------------------------
# validation shared by diagnostics, report, verify
# ---------------------------------------------------------------------------

def _validate(study, run_id: str, purpose=None):
    from . import freeze_v2
    from . import validation as V
    roles = study.run_roles(run_id)
    if run_id.startswith("dev"):
        return V.validate_run(run_id, roles, frozen=False, study=study,
                              unfrozen_sha=freeze_v2.dev_fingerprint(study)), roles
    return V.validate_run(run_id, roles, frozen=True, study=study, purpose=purpose), roles


def cmd_diagnostics(a) -> int:
    from . import benchmark as B
    from . import diagnostics_v2 as D
    study = _study(a)
    d = study.run_dir(a.run_id)
    budget = B.CategoryBudget(study, "diagnostics_verification", "diagnostics", a.run_id)
    if not a.run_id.startswith("dev"):
        fr, fsha, problems = B.load_and_validate_freeze(a.run_id, "diagnostics", study)
        if problems:
            raise SystemExit("freeze validation failed: " + "; ".join(problems))
    (val, ctx), roles = _validate(study, a.run_id)
    out = D.run(study, a.run_id, val, roles)
    out["freeze_sha256"] = ctx["freeze_sha256"]
    out["engineering_valid_at_diagnostics"] = val["engineering_valid"]
    out["complete_at_diagnostics"] = val["complete"]
    B.atomic_write(d / "diagnostics.json", json.dumps(out, indent=1, default=float).encode())
    budget.save()
    print(json.dumps({"diagnostics": str(d / "diagnostics.json"),
                      "boundary_references": out["supplied_boundary_references"]["available"],
                      "wall_s": round(out["wall_s"])}))
    return 0


def _report_state(summary: dict, val: dict) -> None:
    summary["study_complete"] = bool(val["complete"])
    summary["engineering_status"] = "valid" if val["engineering_valid"] else "invalid"
    summary["completeness"] = "complete" if val["complete"] else "incomplete"
    summary["scientific_verdict"] = (summary.get("primary") or {}).get("verdict")


def build_report(study, run_id: str, val, ctx) -> tuple[dict, list, list]:
    from . import report as R
    from . import report_v2 as R2
    d = study.run_dir(run_id)
    summary = R2.summarise(val, ctx["design"], d)
    summary["freeze_sha256"] = ctx["freeze_sha256"]
    summary["freeze_problems"] = ctx.get("freeze_problems", [])
    _report_state(summary, val)
    rows = sorted((r for m in val["_index"].values() for r in m.values()),
                  key=lambda r: (r["case_id"], r["method"]))
    ledgers = R.representative_ledgers(d, rows)
    led = R2.claim_ledger(summary, run_id, _result_rel(study))
    return summary, ledgers, led


def cmd_report(a) -> int:
    from . import benchmark as B
    study = _study(a)
    d = study.run_dir(a.run_id)
    budget = B.CategoryBudget(study, "diagnostics_verification", "report", a.run_id)
    if (d / "freeze.json").exists():
        fr = json.loads((d / "freeze.json").read_text())
        env = B.check_environment(fr.get("environment", {}), "report")
        if env:
            raise SystemExit("report refused, environment differs from the freeze: " + "; ".join(env))
    (val, ctx), roles = _validate(study, a.run_id)
    summary, ledgers, led = build_report(study, a.run_id, val, ctx)
    B.atomic_write(d / "summary.json", json.dumps(summary, indent=1, default=float).encode())
    B.atomic_write(d / "ledgers.json", json.dumps(ledgers, indent=1).encode())
    B.atomic_write(d / "claim_ledger.json", json.dumps(led, indent=1, default=float).encode())
    budget.save()
    code = _exit_code(val)
    p = summary.get("primary") or {}
    print(json.dumps({"engineering": summary["engineering_status"],
                      "complete": summary["study_complete"], "verdict": p.get("verdict"),
                      "primary": {k: p.get(k) for k in ("estimate_mean_saving_per_input_bit",
                                                        "ci95")},
                      "exit_code": code}, default=float))
    return code


SUMMARY_KEYS_V2 = ("primary", "contrasts", "all_family_confirmation", "structured_transfer",
                   "all_stress", "transfer_by_size", "cells", "status_rates", "nesting",
                   "cost_components", "round_trips")


def cmd_verify(a) -> int:
    """Read-only verification (writes only verification.json, first as not_verified)."""
    from . import benchmark as B
    study = _study(a)
    d = study.run_dir(a.run_id)
    budget = B.CategoryBudget(study, "diagnostics_verification", "verify", a.run_id)
    v = {"run_id": a.run_id, "study": study.name,
         "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "commands": [], "problems": []}
    _write_verification(d, dict(v, engineering_status="not_verified", exit_code=None,
                                note="verification started and has not finished"))
    (val, ctx), roles = _validate(study, a.run_id)
    v["scope"] = "whole_run"
    v["roles"] = roles
    v["freeze_sha256"] = ctx["freeze_sha256"]
    v["freeze_problems"] = ctx.get("freeze_problems", [])
    invalid, incomplete = list(val["invalid"]), list(val["incomplete"])
    from . import validation as V
    pub = V.public(val)
    v["validation"] = {k: pub[k] for k in ("engineering_valid", "complete", "expected_rows",
                                           "present_rows", "archives_checked",
                                           "distinct_archives_decoded", "missing_units",
                                           "missing_methods", "duplicates", "unknown")}
    v["validation"]["censored"] = pub["censored"][:200]
    v["search_v2_checks"] = {k: val.get("search_v2_checks", {}).get(k) for k in
                             ("nesting_pairs_checked", "resource_nesting_break_count")}
    rows = sorted((r for m in val["_index"].values() for r in m.values()),
                  key=lambda r: (r["case_id"], r["method"]))
    inputs = {}
    for role in roles:
        for c in study.role_cases(role, d)[0]:
            inputs[c.case_id] = c.bits
    v["separate_process_decode"] = _separate_process_sample(d, rows, inputs)
    if v["separate_process_decode"].get("unavailable"):
        invalid.append("separate-process sample: archives unavailable")
    if not v["separate_process_decode"]["all_ok"]:
        invalid.append("separate-process decoder disagreed on the stratified sample")
    required = ["summary.json", "claim_ledger.json", "corpus_manifest.jsonl", "cases.jsonl"]
    if not a.run_id.startswith("dev"):
        required += ["freeze.json", "diagnostics.json", "source_snapshot.tar"]
    for name in required:
        if not (d / name).exists():
            invalid.append(f"required artefact missing: {name}")
    fr = ctx.get("freeze") or {}
    env_cmp = B.environment_comparison(fr.get("environment", {})) if fr else {}
    v["environment_differences"] = {k: c for k, c in env_cmp.items() if not c["equal"]}
    v["environment_problems_by_purpose"] = {
        p: B.check_environment(fr.get("environment", {}), p) for p in B.ENVIRONMENT_REQUIRED} if fr else {}
    summ = json.loads((d / "summary.json").read_text()) if (d / "summary.json").exists() else {}
    if summ:
        if fr and v["environment_problems_by_purpose"]["report"]:
            v["summary_recomputed"] = "skipped: environment differs from the frozen report environment"
        else:
            fresh, _, led = build_report(study, a.run_id, val, ctx)
            norm = json.loads(json.dumps(fresh, default=float))
            stale = [k for k in SUMMARY_KEYS_V2 if norm.get(k) != summ.get(k)]
            for k in ("engineering_status", "study_complete", "scientific_verdict"):
                if summ.get(k) != norm.get(k):
                    stale.append(k)
            v["summary_recomputed"] = {"stale_keys": stale, "agrees": not stale}
            if stale:
                invalid.append(f"summary.json disagrees with the rows: {stale}")
            if (d / "claim_ledger.json").exists():
                if json.loads(json.dumps(led, default=float)) != \
                        json.loads((d / "claim_ledger.json").read_text()):
                    invalid.append("claim_ledger.json disagrees with the rows")
    v["scientific_verdict"] = summ.get("scientific_verdict")
    v["engineering_status"] = "invalid" if invalid else "valid"
    v["completeness"] = "incomplete" if incomplete else "complete"
    v["invalid_count"], v["incomplete_count"] = len(invalid), len(incomplete)
    v["invalid_reasons"], v["incomplete_reasons"] = invalid[:200], incomplete[:200]
    if a.full:
        v["commands"] = run_checks()
        if any(c["exit_code"] != 0 for c in v["commands"] if c.get("required", True)):
            v["problems"].append("a required check command failed")
    code = EXIT_INVALID if invalid else (EXIT_INCOMPLETE if incomplete else EXIT_OK)
    if v["problems"] and code == EXIT_OK:
        code = EXIT_INVALID
    v["exit_code"] = code
    v["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    budget.save()
    v["diagnostics_verification_s_used"] = budget.elapsed()
    _write_verification(d, v)
    print(json.dumps({k: v[k] for k in ("engineering_status", "completeness",
                                        "scientific_verdict", "exit_code")}))
    return code


V2_LINT = ("index-deconvolution/hierarchy", "index-deconvolution/notebooks/build_17.py",
           "index-deconvolution/experiments/audit_search_v2_primary.py",
           "index-deconvolution/experiments/preserve_confirm_v1_r1_sources.py")


def run_checks() -> list[dict]:
    env = dict(os.environ, PYTHONPATH=f"{REPO / 'index-deconvolution'}{os.pathsep}{REPO / 'src'}")
    cmds = [
        ("pytest", [sys.executable, "-m", "pytest", "index-deconvolution/hierarchy/tests",
                    "tests/analysis/test_description_lengths_values.py", "-q", "--tb=short",
                    "-p", "no:cacheprovider"], True),
        ("ruff", ["ruff", "check", "--output-format=concise", *V2_LINT], True),
        ("check_core_index", ["zsh", "tools/check_core_index.sh"], True),
        ("check_test_manifest", ["zsh", "tools/check_test_manifest.sh"], False),
        ("check_single_engine", ["zsh", "tools/check_single_engine.sh"], False),
    ]
    out = []
    for name, cmd, required in cmds:
        t0 = time.time()
        p = subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True)
        tail = (p.stdout + p.stderr).strip().splitlines()[-6:]
        out.append({"name": name, "command": " ".join(cmd[1:] if cmd[0] == sys.executable else cmd),
                    "exit_code": p.returncode, "tail": tail, "seconds": round(time.time() - t0, 1),
                    "required": required})
    nb = REPO / "index-deconvolution" / "notebooks" / "17_hierarchy_search_v2.ipynb"
    if not nb.exists():
        out.append({"name": "notebook 17", "exit_code": 1, "tail": ["missing"], "required": True})
    else:
        cells = json.loads(nb.read_text())["cells"]
        code = [c for c in cells if c["cell_type"] == "code"]
        errs = sum(1 for c in code for o in c.get("outputs", []) if o.get("output_type") == "error")
        unexecuted = sum(1 for c in code if c.get("execution_count") is None)
        out.append({"name": "notebook 17", "exit_code": 0 if not errs and not unexecuted else 1,
                    "tail": [f"{len(code)} code cells, {errs} error outputs, {unexecuted} unexecuted"],
                    "required": True})
    return out
