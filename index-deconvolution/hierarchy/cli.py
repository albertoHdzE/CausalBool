"""HID-v1 command line (orchestration only).

Run from the repository root with PYTHONPATH=index-deconvolution:src:

  python -m hierarchy.cli selfcheck
  python -m hierarchy.cli pilot --run-id dev-v1
  python -m hierarchy.cli freeze --run-id confirm-v1
  python -m hierarchy.cli benchmark --run-id confirm-v1 --split confirmation --resume
  python -m hierarchy.cli benchmark --run-id confirm-v1 --split transfer --resume
  python -m hierarchy.cli diagnostics --run-id confirm-v1
  python -m hierarchy.cli report --run-id confirm-v1
  python -m hierarchy.cli verify --run-id confirm-v1
  python -m hierarchy.cli encode --input bits.txt --output bits.isd
  python -m hierarchy.cli decode --input bits.isd --output bits.txt

verify exits 0 for a complete, valid study (whatever its scientific verdict),
2 for engineering invalidity or corrupted/missing artefacts, 3 for an incomplete
declared split.

Every study command takes ``--study`` (default ``hid-v1``, the frozen HID-v1 study).
``--study search-v2`` runs HID-search-v2 through ``cli_v2`` (adds ``regression``):

  python -m hierarchy.cli selfcheck --study search-v2
  python -m hierarchy.cli pilot --study search-v2 --run-id dev-search-v2-pilot
  python -m hierarchy.cli regression --study search-v2 --run-id dev-search-v2-regression
  python -m hierarchy.cli freeze --study search-v2 --run-id search-confirm-v2-r1
  python -m hierarchy.cli benchmark --study search-v2 --run-id search-confirm-v2-r1 \
      --split confirmation --resume
  python -m hierarchy.cli diagnostics|report|verify --study search-v2 --run-id ...
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

EXIT_OK, EXIT_INVALID, EXIT_INCOMPLETE = 0, 2, 3


def _v2(a) -> bool:
    return getattr(a, "study", "hid-v1") != "hid-v1"


def _read_bits_file(path: Path) -> str:
    raw = path.read_bytes()
    if raw.endswith(b"\n"):
        raw = raw[:-1]
    if raw.strip(b"01"):
        raise SystemExit("input must contain only ASCII 0/1 (one terminal newline allowed)")
    return raw.decode("ascii")


def cmd_encode(a) -> int:
    from .infer import infer
    from .benchmark import atomic_write
    bits = _read_bits_file(Path(a.input))
    res = infer(bits)
    atomic_write(Path(a.output), res.archive)
    print(json.dumps({"n_bits": len(bits), "archive_bits": res.archive_bits,
                      "literal_bits": res.literal_bits, "mode": res.mode,
                      "stop_reason": res.stop_reason}))
    return 0


def cmd_decode(a) -> int:
    from .decode import decode_archive
    from .benchmark import atomic_write
    bits = decode_archive(Path(a.input).read_bytes())
    atomic_write(Path(a.output), bits.encode("ascii"))
    return 0


def cmd_selfcheck(a) -> int:
    if _v2(a):
        from . import cli_v2
        return cli_v2.cmd_selfcheck(a)
    from .baselines import BASELINE_METHODS, encode_baseline
    from .decode import decode_archive
    from .infer import ABLATIONS, infer
    from .model import Literal, Model, Repeat
    from .wire import encode_literal, serialize_model
    checks = {}
    checks["golden_hid"] = serialize_model(Model((Literal("1"), Repeat(0, 8))), 8).hex() == \
        "4953443101080702000180020008"
    checks["golden_literal"] = encode_literal("0110").hex() == "4953443100040160"
    smoke = ["", "1", "0110" * 20, ("1" * 8 + "0") * 8, "1011001110001111" * 9 + "01"]
    ok = True
    for s in smoke:
        for m in BASELINE_METHODS:
            ok &= decode_archive(encode_baseline(s, m)) == s
        for cfg in ABLATIONS.values():
            r = infer(s, cfg)
            ok &= decode_archive(r.archive) == s and r.archive_bits <= r.literal_bits
    checks["smoke_round_trips"] = ok
    with tempfile.TemporaryDirectory() as tmp:
        from . import decode as dmod
        shutil.copy(dmod.__file__, Path(tmp) / "decode.py")
        arc = infer(smoke[3]).archive
        (Path(tmp) / "a.bin").write_bytes(arc)
        out = subprocess.run([sys.executable, "-I", "-S", "decode.py", "a.bin"], cwd=tmp,
                             env={"PATH": os.environ.get("PATH", "")},
                             capture_output=True, text=True)
        checks["separate_process_decoder"] = (
            out.returncode == 0 and json.loads(out.stdout)[0]["bits"] == smoke[3])
    print(json.dumps(checks, indent=1))
    return 0 if all(checks.values()) else 1


def cmd_pilot(a) -> int:
    if _v2(a):
        from . import cli_v2
        return cli_v2.cmd_pilot(a)
    from . import benchmark as B
    from . import report as R
    from .corpus import split_cases
    d = B.run_dir(a.run_id)
    if not a.run_id.startswith("dev"):
        raise SystemExit("pilot run ids must start with 'dev'")
    d.mkdir(parents=True, exist_ok=True)
    log = d / "logs"
    log.mkdir(exist_ok=True)
    t0 = time.time()
    if not (d / "rows").exists():
        # Deliberate interruption, then resume: the resume path is exercised for real.
        B.benchmark(a.run_id, "development", resume=False, stop_after=a.interrupt_after,
                    require_freeze=False)
    B.benchmark(a.run_id, "development", resume=True, require_freeze=False)
    # Fresh uninterrupted replay of the first cases, compared field by field.
    cases, _ = split_cases("development")
    replay_id = a.run_id + "-replay"
    rd = B.run_dir(replay_id)
    if rd.exists():
        shutil.rmtree(rd)
    rd.mkdir(parents=True)
    B.run_cases(cases[:a.replay_cases], rd, replay_id, "development-unfrozen", False,
                lambda m: None)
    det = ("status", "archive_sha256", "archive_bits", "decode_ok", "selected_codec_id",
           "selected_method", "rule_count", "dag_depth", "candidate_count",
           "deterministic_work", "stop_reason", "search_counters", "trace")
    diffs = []
    for c in cases[:a.replay_cases]:
        x = {r["method"]: r for r in json.loads(B.case_rows_path(d, c).read_text())}
        y = {r["method"]: r for r in json.loads(B.case_rows_path(rd, c).read_text())}
        for m in x:
            for k in det:
                if x[m][k] != y[m][k]:
                    diffs.append({"case": c.case_id, "method": m, "field": k})
    B.atomic_write(d / "resume_check.json", json.dumps({
        "interrupted_after_cases": a.interrupt_after, "replayed_cases": a.replay_cases,
        "deterministic_fields": det, "differences": diffs,
        "identical": not diffs}, indent=1).encode())
    print(f"resume/replay identical: {not diffs} ({len(diffs)} differences)")
    if a.oracle:
        res = B.run_oracle(d / "oracle.json")
        print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("rows", "examples")}
                          for k, v in res["tables"].items()}))
    from . import validation as V
    val, _ = V.validate_run(a.run_id, ["development"], frozen=False)
    summary = R.summarise(val, V.production_design(["development"]), "development")
    summary["status"] = "development pilot (exploratory, not confirmatory)"
    B.atomic_write(d / "summary.json", json.dumps(summary, indent=1, default=float).encode())
    print(f"pilot done in {time.time() - t0:.0f} s; rows in {d}")
    return 0


def cmd_freeze(a) -> int:
    if _v2(a):
        from . import cli_v2
        return cli_v2.cmd_freeze(a)
    from . import benchmark as B
    fr = B.write_freeze(a.run_id)
    print(f"froze {a.run_id}: sha256 {B.freeze_sha(fr)}")
    return 0


def cmd_benchmark(a) -> int:
    if _v2(a):
        from . import cli_v2
        return cli_v2.cmd_benchmark(a)
    from . import benchmark as B
    allowed = ("development",) if a.run_id.startswith("dev") else ("confirmation", "transfer")
    if a.split not in allowed:
        raise SystemExit(f"run id {a.run_id} may benchmark only {allowed}")
    stats = B.benchmark(a.run_id, a.split, a.resume, log=print if not a.quiet else (lambda m: None))
    print(json.dumps(stats))
    return 0


def cmd_diagnostics(a) -> int:
    if _v2(a):
        from . import cli_v2
        return cli_v2.cmd_diagnostics(a)
    from . import benchmark as B
    from . import diagnostics as D
    fr, fsha, problems = B.load_and_validate_freeze(a.run_id, purpose="diagnostics")
    if problems:
        raise SystemExit("freeze validation failed: " + "; ".join(problems))
    d = B.run_dir(a.run_id)
    t0 = time.time()
    if a.run_id.startswith("dev"):         # pipeline smoke run: development data only
        from .corpus import HELD_OUT
        out = D.run(workers=B.MAX_WORKERS, split="development", replicate=0,
                    families=tuple(f for f in D.DIAG_FAMILIES if f not in HELD_OUT))
    else:
        out = D.run(workers=B.MAX_WORKERS)
    out["freeze_sha256"] = fsha
    out["historical_audit33"] = {
        "path": "diagnostics_historical_audit33.json",
        "note": "bitacora-33 audit rerun to a new path; the original JSON is untouched"}
    D.historical_audit(d / "diagnostics_historical_audit33.json")
    out["wall_s"] = time.time() - t0
    B.atomic_write(d / "diagnostics.json", json.dumps(out, indent=1).encode())
    budget = B.Budget(d, B.TOTAL_BUDGET_S)
    budget.used += out["wall_s"]
    budget.save()
    print(f"diagnostics written; claim status {out['claim_status']}")
    return 0


def _exit_code(validation: dict) -> int:
    if not validation["engineering_valid"]:
        return EXIT_INVALID
    return EXIT_OK if validation["complete"] else EXIT_INCOMPLETE


def _report_state(summary: dict, validation: dict) -> None:
    summary["study_complete"] = bool(validation["complete"])
    summary["engineering_status"] = "valid" if validation["engineering_valid"] else "invalid"
    summary["completeness"] = "complete" if validation["complete"] else "incomplete"
    summary["scientific_verdict"] = summary.get("primary", {}).get("verdict")


def cmd_report(a) -> int:
    """Validate the run (shared path with verify), then write the summary and ledgers.

    Exit 0 complete and valid (any verdict), 2 invalid, 3 incomplete; the files are
    written in every case, with gates recorded, unless the frozen environment
    differs, in which case nothing is written."""
    if _v2(a):
        from . import cli_v2
        return cli_v2.cmd_report(a)
    from . import benchmark as B
    from . import report as R
    from . import validation as V
    d = B.run_dir(a.run_id)
    splits = _splits(a.run_id)
    fr = json.loads((d / "freeze.json").read_text()) if (d / "freeze.json").exists() else {}
    env_problems = B.check_environment(fr.get("environment", {}), "report") if fr else []
    if env_problems:
        raise SystemExit("report refused, environment differs from the freeze: "
                         + "; ".join(env_problems))
    val, ctx = V.validate_run(a.run_id, splits, frozen=True)
    summary = R.summarise(val, ctx["design"], primary_split=splits[0])
    summary["freeze_sha256"] = ctx["freeze_sha256"]
    summary["freeze_problems"] = ctx.get("freeze_problems", [])
    diag = json.loads((d / "diagnostics.json").read_text()) if (d / "diagnostics.json").exists() else None
    if diag:
        summary["bdm_diagnostics"] = {f: {k: v for k, v in o.items()
                                          if k in ("adaptive_p", "selected_config", "T0",
                                                   "r_null_at_or_below")}
                                      for f, o in diag["objects"].items()}
        summary["bdm_holm"] = diag["holm"]
    _report_state(summary, val)
    rows = sorted((r for m in val["_index"].values() for r in m.values()),
                  key=lambda r: (r["case_id"], r["method"]))
    ledgers = R.representative_ledgers(d, rows)
    led = R.claim_ledger(summary, diag, a.run_id)
    # everything is computed before anything is written: no mix of fresh and stale files
    B.atomic_write(d / "summary.json", json.dumps(summary, indent=1, default=float).encode())
    B.atomic_write(d / "ledgers.json", json.dumps(ledgers, indent=1).encode())
    B.atomic_write(d / "claim_ledger.json", json.dumps(led, indent=1, default=float).encode())
    code = _exit_code(val)
    print(json.dumps({"engineering": summary["engineering_status"],
                      "complete": summary["study_complete"],
                      "verdict": summary["scientific_verdict"],
                      "primary": {k: summary.get("primary", {}).get(k)
                                  for k in ("estimate_mean_saving_per_input_bit", "ci95")},
                      "exit_code": code}, default=float))
    return code


SUMMARY_KEYS_CHECKED = ("primary", "ablations", "transfer_structured_aggregate",
                        "controls_aggregate", "all_families_confirmation_aggregate",
                        "families_confirmation", "transfer", "controls_vs_statistical_codes",
                        "status_counts")


def cmd_verify(a) -> int:
    """Read-only verification of a stored run (writes only verification.json).

    Shares ``validation.validate_run`` with ``report``; additionally decodes a
    stratified sample in a separate process, checks the required artefacts and that
    summary.json and claim_ledger.json are exactly what the rows imply. The current
    environment is reported, never enforced, and the freeze is never rewritten.

    Any earlier verification.json is first replaced by a ``not_verified`` record, so
    a verification that does not finish can never leave an older success behind."""
    if _v2(a):
        from . import cli_v2
        return cli_v2.cmd_verify(a)
    from . import benchmark as B
    from . import report as R
    from . import validation as V
    d = B.run_dir(a.run_id)
    v = {"run_id": a.run_id, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "commands": [], "problems": []}
    _write_verification(d, dict(v, engineering_status="not_verified", exit_code=None,
                                note="verification started and has not finished"))
    splits = _splits(a.run_id)
    val, ctx = V.validate_run(a.run_id, splits, frozen=True)
    v["freeze_sha256"] = ctx["freeze_sha256"]
    v["freeze_problems"] = ctx.get("freeze_problems", [])
    invalid = list(val["invalid"])
    incomplete = list(val["incomplete"])
    pub = V.public(val)
    v["validation"] = {k: pub[k] for k in ("engineering_valid", "complete", "expected_rows",
                                           "present_rows", "archives_checked",
                                           "distinct_archives_decoded", "missing_units",
                                           "missing_methods", "duplicates", "unknown")}
    v["validation"]["censored"] = pub["censored"][:200]
    v["archives_decoded_against_regenerated_inputs"] = val["archives_checked"]
    rows = sorted((r for m in val["_index"].values() for r in m.values()),
                  key=lambda r: (r["case_id"], r["method"]))
    v["separate_process_decode"] = _separate_process_sample(d, rows)
    if v["separate_process_decode"].get("unavailable"):
        invalid.append("separate-process sample: archives unavailable for "
                       f"{len(v['separate_process_decode']['unavailable'])} strata")
    if not v["separate_process_decode"]["all_ok"]:
        invalid.append("separate-process decoder disagreed on the stratified sample")
    for name in ("summary.json", "claim_ledger.json", "diagnostics.json", "corpus_manifest.jsonl",
                 "cases.jsonl", "freeze.json"):
        if not (d / name).exists():
            invalid.append(f"required artefact missing: {name}")
    summ = json.loads((d / "summary.json").read_text()) if (d / "summary.json").exists() else {}
    fr = ctx.get("freeze") or {}
    env_cmp = B.environment_comparison(fr.get("environment", {}))
    v["verification_environment"] = {k: c["current"] for k, c in env_cmp.items()}
    v["environment_differences"] = {k: c for k, c in env_cmp.items() if not c["equal"]}
    v["environment_problems_by_purpose"] = {
        p: B.check_environment(fr.get("environment", {}), p) for p in B.ENVIRONMENT_REQUIRED}
    if summ:
        if v["environment_problems_by_purpose"]["report"]:
            v["summary_recomputed"] = "skipped: verification environment differs from the frozen report environment"
        else:
            fresh = R.summarise(val, ctx["design"], primary_split=splits[0])
            stale = [k for k in SUMMARY_KEYS_CHECKED
                     if json.loads(json.dumps(fresh.get(k), default=float))
                     != summ.get(k)]
            for k, want in (("engineering_status", "valid" if val["engineering_valid"] else "invalid"),
                            ("study_complete", bool(val["complete"])),
                            ("scientific_verdict", fresh["primary"]["verdict"])):
                if summ.get(k) != want:
                    stale.append(k)
            v["summary_recomputed"] = {"stale_keys": stale, "agrees": not stale}
            if stale:
                invalid.append(f"summary.json disagrees with the rows: {stale}")
            if (d / "claim_ledger.json").exists():
                diag = json.loads((d / "diagnostics.json").read_text()) if (d / "diagnostics.json").exists() else None
                led = json.loads(json.dumps(R.claim_ledger(summ, diag, a.run_id), default=float))
                if led != json.loads((d / "claim_ledger.json").read_text()):
                    invalid.append("claim_ledger.json disagrees with summary.json")
    v["scientific_verdict"] = summ.get("scientific_verdict")
    v["engineering_status"] = "invalid" if invalid else "valid"
    v["completeness"] = "incomplete" if incomplete else "complete"
    v["invalid_count"] = len(invalid)
    v["incomplete_count"] = len(incomplete)
    v["invalid_reasons"] = invalid[:200]
    v["incomplete_reasons"] = incomplete[:200]
    if a.full:
        v["commands"] = _run_checks()
        if any(c["exit_code"] != 0 for c in v["commands"] if c.get("required", True)):
            v["problems"].append("a required check command failed")
    v["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    code = EXIT_INVALID if invalid else (EXIT_INCOMPLETE if incomplete else EXIT_OK)
    if v["problems"] and code == EXIT_OK:
        code = EXIT_INVALID
    v["exit_code"] = code
    _write_verification(d, v)
    print(json.dumps({k: v[k] for k in ("engineering_status", "completeness",
                                        "scientific_verdict", "exit_code",
                                        "archives_decoded_against_regenerated_inputs")}))
    return code


def _write_verification(d: Path, v: dict) -> None:
    out = d / "verification.json"
    tmp = out.with_name(".verification.json.tmp")
    tmp.write_text(json.dumps(v, indent=1, default=float))
    os.replace(tmp, out)


def _splits(run_id: str) -> list[str]:
    return ["development"] if run_id.startswith("dev") else ["confirmation", "transfer"]


def _separate_process_sample(d: Path, rows, inputs: dict | None = None) -> dict:
    """Decode one archive per (split, family, method) with only decode.py present.

    A sampled archive file that is absent is listed under ``unavailable`` and the
    sample is not ``all_ok``; it is never replaced by another stratum member."""
    from . import decode as dmod
    from .corpus import split_cases
    want = {}
    for r in rows:
        if r["archive_path"] and r["method"] != "baseline_best":
            key = (r["split"], r["family"], r["method"], r["status"])
            want.setdefault(key, r)
    if inputs is None:
        inputs = {}
        for split in {k[0] for k in want}:
            for c in split_cases(split)[0]:
                inputs[c.case_id] = c.bits
    unavailable = []
    with tempfile.TemporaryDirectory() as tmp:
        box = Path(tmp)
        shutil.copy(dmod.__file__, box / "decode.py")
        names = {}
        for i, r in enumerate(want.values()):
            src = d / r["archive_path"]
            if not src.is_file():
                unavailable.append(f"{r['case_id']}:{r['method']} archive file missing")
                continue
            name = f"s{i:05d}.bin"
            shutil.copy(src, box / name)
            names[name] = r
        if not names:
            return {"sampled": 0, "all_ok": False, "unavailable": unavailable}
        out = subprocess.run([sys.executable, "-I", "-S", "decode.py"] + sorted(names),
                             cwd=box, env={"PATH": os.environ.get("PATH", "")},
                             capture_output=True, text=True)
        res = json.loads(out.stdout) if out.returncode == 0 else []
    ok = [x["ok"] and x["bits"] == inputs[names[x["path"]]["case_id"]] for x in res]
    sample = {"sampled": len(names), "decoded": len(res), "all_ok": bool(res) and all(ok)
              and len(res) == len(names) and not unavailable,
              "strata": "one archive per (split, family, method, status), including fallbacks"}
    failed = [f"{names[x['path']]['case_id']}:{names[x['path']]['method']} "
              + (f"{x['error']}: {x['message']}" if not x["ok"]
                 else "decoded to a different input")
              for x, good in zip(res, ok) if not good]
    if failed:
        sample["failed"] = failed
    if unavailable:
        sample["unavailable"] = unavailable
    return sample


def _run_checks() -> list[dict]:
    repo = Path(__file__).resolve().parents[2]
    env = dict(os.environ, PYTHONPATH=f"{repo / 'index-deconvolution'}{os.pathsep}{repo / 'src'}")
    cmds = [
        ("pytest", [sys.executable, "-m", "pytest", "index-deconvolution/hierarchy/tests",
                    "tests/analysis/test_description_lengths_values.py", "-q", "--tb=short",
                    "-p", "no:cacheprovider"], True),
        ("ruff", ["ruff", "check", "--output-format=concise", "index-deconvolution/hierarchy",
                  "src/description_lengths.py", "tests/analysis/test_description_lengths_values.py",
                  "index-deconvolution/notebooks/build_15.py",
                  "index-deconvolution/notebooks/build_16.py"], True),
        ("check_core_index", ["zsh", "tools/check_core_index.sh"], True),
        ("check_test_manifest", ["zsh", "tools/check_test_manifest.sh"], False),
        ("check_single_engine", ["zsh", "tools/check_single_engine.sh"], False),
    ]
    out = []
    for name, cmd, required in cmds:
        t0 = time.time()
        p = subprocess.run(cmd, cwd=repo, env=env, capture_output=True, text=True)
        tail = (p.stdout + p.stderr).strip().splitlines()[-3:]
        out.append({"name": name, "command": " ".join(cmd[1:] if cmd[0] == sys.executable
                                                      else cmd),
                    "exit_code": p.returncode, "tail": tail, "seconds": round(time.time() - t0, 1),
                    "required": required})
    for nb in ("15_shifted_zero_bdm_probe.ipynb", "16_hierarchical_index_generalization.ipynb"):
        path = repo / "index-deconvolution" / "notebooks" / nb
        if not path.exists():
            out.append({"name": f"notebook {nb}", "exit_code": 1, "tail": ["missing"],
                        "required": True})
            continue
        cells = json.loads(path.read_text())["cells"]
        code = [c for c in cells if c["cell_type"] == "code"]
        errs = sum(1 for c in code for o in c.get("outputs", []) if o.get("output_type") == "error")
        unexecuted = sum(1 for c in code if c.get("execution_count") is None)
        out.append({"name": f"notebook {nb}", "exit_code": 0 if not errs and not unexecuted else 1,
                    "tail": [f"{len(code)} code cells, {errs} error outputs, "
                             f"{unexecuted} unexecuted"], "required": True})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hierarchy.cli", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    study_parsers = []
    study_parsers.append(sub.add_parser("selfcheck"))
    p = sub.add_parser("pilot")
    study_parsers.append(p)
    p.add_argument("--run-id", required=True)
    p.add_argument("--interrupt-after", type=int, default=8)
    p.add_argument("--replay-cases", type=int, default=12)
    p.add_argument("--no-oracle", dest="oracle", action="store_false")
    p = sub.add_parser("regression")
    study_parsers.append(p)
    p.add_argument("--run-id", required=True)
    p.add_argument("--resume", action="store_true")
    p = sub.add_parser("freeze")
    study_parsers.append(p)
    p.add_argument("--run-id", required=True)
    p.add_argument("--prefreeze-dir", default=None)
    p = sub.add_parser("benchmark")
    study_parsers.append(p)
    p.add_argument("--run-id", required=True)
    p.add_argument("--split", required=True)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--quiet", action="store_true")
    for name in ("diagnostics", "report"):
        p = sub.add_parser(name)
        study_parsers.append(p)
        p.add_argument("--run-id", required=True)
    p = sub.add_parser("verify")
    study_parsers.append(p)
    p.add_argument("--run-id", required=True)
    p.add_argument("--full", action="store_true",
                   help="also run tests, lint, guards and notebook checks")
    for name in ("encode", "decode"):
        p = sub.add_parser(name)
        p.add_argument("--input", required=True)
        p.add_argument("--output", required=True)
    for p in study_parsers:
        p.add_argument("--study", default="hid-v1",
                       help="study specification (hid-v1 default, search-v2)")
    a = ap.parse_args(argv)
    if a.cmd == "regression":
        if not _v2(a):
            raise SystemExit("regression exists only for --study search-v2")
        from . import cli_v2
        return cli_v2.cmd_regression(a)
    return {"selfcheck": cmd_selfcheck, "pilot": cmd_pilot, "freeze": cmd_freeze,
            "benchmark": cmd_benchmark, "diagnostics": cmd_diagnostics, "report": cmd_report,
            "verify": cmd_verify, "encode": cmd_encode, "decode": cmd_decode}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
