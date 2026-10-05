"""search-diagnosis-v1 commands (run from ``index-deconvolution/``)::

  PYTHONPATH=experiments:.:../src ../venv/bin/python -m search_diagnosis.cli identity
  ... cli d1                      saved-result map (no encoding)
  ... cli run --section D2|D3|D4  isolated jobs, durable records, resumable
  ... cli analyse                 tables, flags and numbers.json from saved artifacts
  ... cli preserve-after          re-hash protected trees/files, compare with before
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from hierarchy.benchmark import CategoryBudget, environment, sha256_bytes, sha256_file

from . import analysis as A
from . import common as K
from . import runner as R

ATTEMPT = "a1"


def _closure_files() -> list:
    files = sorted(p for p in K.PKG.rglob("*.py") if "__pycache__" not in p.parts)
    files += sorted((K.ID_ROOT / "hierarchy").glob("*.py"))
    files += [K.ID_ROOT / "experiments" / "preserve_confirm_v1_r1_sources.py",
              K.PROTOCOL, K.KICKOFF, K.CONTRACT, K.DELEGATION]
    return files


def _identity_core() -> dict:
    from .kernels import CONFIGS
    rel = lambda p: str(p.relative_to(K.REPO))                     # noqa: E731
    adapters = {rel(p): sha256_file(p) for p in sorted(K.PKG.glob("*.py"))}
    owners = {rel(p): sha256_file(p) for p in sorted((K.ID_ROOT / "hierarchy").glob("*.py"))}
    packet = {rel(p): sha256_file(p) for p in (K.PROTOCOL, K.KICKOFF, K.CONTRACT, K.DELEGATION)}
    design = {"D1": K.design_case_ids(), **{s: K.section_ids(s) for s in ("D2", "D3", "D4")}}
    return {"phase_id": "search-diagnosis-v1", "run_id": K.RUN_ID,
            "evidence_role": K.EVIDENCE_ROLE, "baseline_run": rel(K.BASE_RUN),
            "baseline_freeze_sha256": K.BASE_FREEZE, "adapters": adapters, "owners": owners,
            "packet": packet, "boundary_configs": {k: v.as_dict() for k, v in CONFIGS.items()},
            "limits": {"wall_s": R.WALL_LIMIT_S, "rss_bytes": R.RSS_LIMIT,
                       "max_workers": R.MAX_WORKERS, "allowances_s": R.ALLOWANCES},
            "design_sha256": K.canonical_sha(design)}, design


def cmd_identity(a) -> int:
    d = K.RUN_DIR / "identity"
    core, design = _identity_core()
    sha = K.canonical_sha(core)
    p = d / "identity.json"
    if p.exists():
        old = json.loads(p.read_text())
        if old["identity_sha256"] != sha:
            print(f"identity changed ({old['identity_sha256'][:12]} -> {sha[:12]}): a coding "
                  "repair after launch needs a new attempt id; refusing", file=sys.stderr)
            return 2
        print(f"identity unchanged {sha}")
        return 0
    c = K.contract()
    checks = {"D1_cases": len(design["D1"]), "D2_targets": len(design["D2"]["targets"]),
              "D2_controls": len(design["D2"]["controls"]),
              "D3_strings": len(design["D3"]["targets"]), "D4_strings": len(design["D4"]["targets"])}
    want = {"D1_cases": c["D1"]["cases"], "D2_targets": c["D2"]["target_strings"],
            "D2_controls": c["D2"]["control_strings"], "D3_strings": c["D3"]["strings"],
            "D4_strings": c["D4"]["strings"]}
    if checks != want:
        print(f"design membership {checks} != contract {want}", file=sys.stderr)
        return 2
    refs = K.references()
    cuts_ok = all(len(refs[i]["cuts"]) <= 5 and refs[i]["available"]
                  for i in design["D3"]["targets"])
    inputs = []
    for cid in design["D1"]:
        rows = K.saved_rows(cid)
        case = K.load_case(cid, rows)
        inputs.append({"case_id": cid, "input_sha256": case.input_sha256, "n_bits": len(case.bits),
                       "archives": {m: rows[m]["archive_sha256"] for m in
                                    ("raw", "hid_full", "period", "pair_grammar", "baseline_best")}})
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_closure_tar", K.ID_ROOT / "experiments" / "preserve_confirm_v1_r1_sources.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.PREFIX = "search-diagnosis-v1-closure/"          # this private instance only
    tar = mod.build_tar([(str(f.relative_to(K.REPO)), f.read_bytes()) for f in _closure_files()])
    d.mkdir(parents=True, exist_ok=True)
    (d / "executable_closure.tar").write_bytes(tar)
    K.write_json(d / "design.json", design)
    (d / "input_manifest.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n"
                                                    for r in inputs))
    K.write_json(d / "environment.json", environment())
    rec = dict(core, identity_sha256=sha, recorded_utc=K.utc(), attempt_id=ATTEMPT,
               membership=checks, d3_supplied_cuts_at_most_5=cuts_ok,
               input_manifest_sha256=sha256_file(d / "input_manifest.jsonl"),
               executable_closure_sha256=sha256_bytes(tar),
               closure_members=len(_closure_files()),
               note="diagnostic implementation identity over ALREADY INSPECTED inputs; not a "
                    "claim that any input is unseen")
    K.write_json(p, rec)
    print(f"identity {sha} ({len(inputs)} inputs, closure {len(tar)} bytes)")
    return 0


REPORTING_ADAPTERS = ("analysis.py", "cli.py", "report.py")      # read saved records; never run a job


def _identity(scope: str = "full") -> dict:
    """``full``: everything recorded must match (job launch, D1). ``execution``: every
    owner, packet, config, design and job-executing adapter must match; a changed
    reporting adapter is allowed and recorded in identity/reporting_revisions.json."""
    rec = json.loads((K.RUN_DIR / "identity" / "identity.json").read_text())
    core, _ = _identity_core()
    if K.canonical_sha(core) == rec["identity_sha256"]:
        return rec
    rep = {k for k in core["adapters"] if k.rsplit("/", 1)[-1] in REPORTING_ADAPTERS}
    strip = lambda d: {k: v for k, v in d.items() if k not in ("adapters",)}  # noqa: E731
    same_exec = (strip(core) == {k: rec[k] for k in strip(core)} and
                 {k: v for k, v in core["adapters"].items() if k not in rep} ==
                 {k: v for k, v in rec["adapters"].items() if k not in rep})
    if scope != "execution" or not same_exec:
        raise SystemExit("sources/config/design differ from the recorded identity; refusing")
    K.write_json(K.RUN_DIR / "identity" / "reporting_revisions.json", {
        "recorded_identity_sha256": rec["identity_sha256"],
        "reason": "reporting-only adapters changed after the jobs ran (no job re-executed); "
                  "the launched bytes are in identity/executable_closure.tar",
        "changed": {k: {"at_launch": rec["adapters"].get(k), "now": core["adapters"][k]}
                    for k in sorted(rep) if rec["adapters"].get(k) != core["adapters"][k]},
        "checked_utc": K.utc()})
    return rec


def cmd_d1(a) -> int:
    _identity()
    t0 = time.monotonic()
    d1 = A.d1_map()
    tables = A.d1_tables(d1)
    out = K.RUN_DIR / "d1"
    K.write_json(out / "d1_cases.json", d1["per_case"])
    K.write_json(out / "d1_tables.json", tables)
    K.write_json(out / "d1_checks.json", {"cases": len(d1["ids"]), "rows": d1["rows_read"],
                                          "problems": d1["problems"]})
    R.charge("diagnostic_jobs", "D1 saved-result map", time.monotonic() - t0)
    print(f"D1 cases {len(d1['ids'])} rows {d1['rows_read']} problems {len(d1['problems'])}; "
          f"accepted primary reproduced {tables['accepted_primary_reproduction']['estimate']!r}")
    return 0 if not d1["problems"] else 1


def _jobs(section: str):
    if section == "D2":
        ids = sorted(K.section_ids("D2")["targets"] + K.section_ids("D2")["controls"])
        for cid in ids:
            case = K.load_case(cid)
            yield case, "B0", {}
            yield case, "B8", {}
    elif section == "D3":
        refs = K.references()
        for cid in K.section_ids("D3")["targets"]:
            yield K.load_case(cid), "D3", {"cuts": refs[cid]["cuts"]}
    else:
        for cid in K.section_ids("D4")["targets"]:
            rows = K.saved_rows(cid)
            for m in ("period", "pair_grammar"):
                K.saved_archive(rows[m])                      # hash/length check
            yield K.load_case(cid, rows), "D4", {
                m: str(K.BASE_RUN / rows[m]["archive_path"]) for m in ("period", "pair_grammar")}


def cmd_run(a) -> int:
    ident = _identity()
    budget = CategoryBudget(R.phase_study(), "diagnostic_jobs", f"run {a.section}", K.RUN_ID)
    t = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    stats = R.run_jobs(list(_jobs(a.section)), a.section, ident["identity_sha256"], ATTEMPT,
                       budget=budget, log=(lambda s: None) if a.quiet else print)
    budget.save()
    with open(K.RUN_DIR / "attempts.jsonl", "a") as fh:
        fh.write(json.dumps({"attempt_id": ATTEMPT, "section": a.section, "started_utc": t,
                             "finished_utc": K.utc(), "stats": stats,
                             "identity_sha256": ident["identity_sha256"]}) + "\n")
    print(f"{a.section}: {stats}; diagnostic_jobs used {R.used('diagnostic_jobs'):.1f} s")
    return 0


def cmd_analyse(a) -> int:
    _identity("execution")
    out = K.RUN_DIR / "analysis"
    b = report_build(K.RUN_DIR)
    for name in ("d2_rows", "d2_summary", "d3_rows", "d4_rows", "d4_summary", "resources",
                 "flags", "key_numbers"):
        K.write_json(out / f"{name}.json", b[name])
    K.write_json(K.RUN_DIR / "DECISION.json", b["decision"])
    print({k: v["value"] for k, v in b["flags"].items() if "value" in v})
    print("recommendation:", b["decision"]["recommendation"])
    print(json.dumps({s: r["status"] for s, r in b["resources"].items()}))
    return 0


def report_build(run_dir) -> dict:
    """Load every intended job record of ``run_dir`` (absent -> None) and the D1 tables,
    then run the one reporting pipeline ``report.build``. Reads only."""
    from .report import build
    d2ids = K.section_ids("D2")
    ids = {"targets": d2ids["targets"], "controls": d2ids["controls"],
           "d4": K.section_ids("D4")["targets"]}
    d1 = run_dir / "d1"
    return build(A.load_records("D2", sorted(ids["targets"] + ids["controls"]), ("B0", "B8"),
                                run_dir),
                 A.load_records("D3", ids["targets"], ("D3",), run_dir),
                 A.load_records("D4", ids["d4"], ("D4",), run_dir),
                 json.loads((d1 / "d1_cases.json").read_text()),
                 json.loads((d1 / "d1_tables.json").read_text()),
                 len(json.loads((d1 / "d1_checks.json").read_text())["problems"]),
                 K.references(), ids)


def cmd_preserve_after(a) -> int:
    before = json.loads((K.RUN_DIR / "preservation" / "preservation_before.json").read_text())
    after, status = K.preservation_record()
    (K.RUN_DIR / "preservation" / "git_status_after.txt").write_text(status)
    K.write_json(K.RUN_DIR / "preservation" / "preservation_after.json", after)
    cmp = K.compare_preservation(before, after)
    allowed = {"files:index-deconvolution/notebooks/README.md"}   # the one appended entry (protocol §2)
    cmp["allowed_changed"] = sorted(d for d in cmp["differences"] if d in allowed)
    cmp["unexpected_differences"] = sorted(d for d in cmp["differences"] if d not in allowed)
    cmp["unchanged"] = not cmp["unexpected_differences"]
    K.write_json(K.RUN_DIR / "preservation" / "preservation_comparison.json", cmp)
    print(json.dumps(cmp))
    return 0 if cmp["unchanged"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="search_diagnosis.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("identity").set_defaults(fn=cmd_identity)
    sub.add_parser("d1").set_defaults(fn=cmd_d1)
    r = sub.add_parser("run")
    r.add_argument("--section", choices=("D2", "D3", "D4"), required=True)
    r.add_argument("--quiet", action="store_true")
    r.set_defaults(fn=cmd_run)
    sub.add_parser("analyse").set_defaults(fn=cmd_analyse)
    sub.add_parser("preserve-after").set_defaults(fn=cmd_preserve_after)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
