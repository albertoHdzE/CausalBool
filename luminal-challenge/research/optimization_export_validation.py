"""Stage E: fresh validation of the standalone export in isolated workspaces.

1. Regenerate ``compiler.py`` from the frozen measured source and check its
   component hashes against FROZEN_SELECTION.json.
2. Copy the pinned public workspace (machine, programs, tests, score.py) into a
   temporary directory, drop the export in as ``compiler.py``, assert that
   ``import compiler`` resolves to the export, then run the unchanged pinned
   public tests and ``score.py``.
3. Measure the export through its documented CLI: eight public programs and the
   200 fresh programs, three repetitions each (624 rows), each a fresh process
   with the 20 second limit. stdout must be exactly one schedule JSON object.
   Every output is validated on every case, and bounded by the valid direct
   bootstrap incumbent of the same program (the controller only accepts strict
   improvements over it).

Usage::

    PYTHONPATH=.reference:. python -m research.optimization_export_validation --run DIR
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import machine

from research import optimization_common as oc

TIMEOUT = 20.0


def build(run: Path, frozen: dict, label: str, model_depth=None) -> dict:
    out_dir = run / "export" / label
    output = out_dir / "compiler.py"
    argv = [oc.PYTHON, "-m", "research.optimization_export", "--config",
            frozen["search"]["config"], "--build", frozen["search"]["build"], "--output",
            str(output)]
    if model_depth is not None:
        argv += ["--model-depth", str(model_depth)]
    meta = oc.run_logged(f"export_{label}", argv, out_dir / "commands")
    manifest = json.loads((out_dir / "compiler_MANIFEST.json").read_text())
    research = frozen["sources"]["research"]
    production = frozen["sources"]["production"]
    mismatched = []
    for name, digest in manifest["components_sha256"].items():
        expected = research.get(name) or production.get(name)
        if expected != digest:
            mismatched.append(name)
    generator_ok = manifest["generator_sha256"] == research.get("research/optimization_export.py")
    return {"exit_code": meta["exit_code"], "path": str(output),
            "sha256": oc.file_sha256(output), "manifest": manifest,
            "component_mismatches": mismatched, "generator_matches_freeze": generator_ok}


def workspace(export_path: Path) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="luminal_export_"))
    reference = oc.ROOT / ".reference"
    for name in ("machine.py", "score.py", "README.md"):
        shutil.copy2(reference / name, tmp / name)
    shutil.copytree(reference / "programs", tmp / "programs")
    shutil.copytree(reference / "tests", tmp / "tests",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(export_path, tmp / "compiler.py")
    return tmp


def pinned_checks(tmp: Path, out_dir: Path) -> dict:
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": ""}
    identity = subprocess.run(
        [oc.PYTHON, "-c", "import compiler, machine, json; print(json.dumps("
         "{'compiler': compiler.__file__, 'machine': machine.__file__, "
         "'config': compiler.EXPORT_CONFIG, 'build': compiler.EXPORT_BUILD}))"],
        cwd=str(tmp), capture_output=True, text=True, env=env)
    tests = oc.run_logged("pinned_public_tests",
                          [oc.PYTHON, "-m", "unittest", "tests.test_public_programs",
                           "tests.test_machine", "-v"], out_dir, env=env, cwd=tmp)
    score = oc.run_logged("pinned_score", [oc.PYTHON, "score.py"], out_dir, env=env, cwd=tmp)
    ident = json.loads(identity.stdout) if identity.returncode == 0 else {}
    return {"identity": ident,
            "compiler_is_export": Path(ident.get("compiler", "")).resolve() ==
            (tmp / "compiler.py").resolve(),
            "pinned_tests_exit": tests["exit_code"], "score_exit": score["exit_code"],
            "score_stdout": (out_dir / "pinned_score.stdout").read_text()[-1500:],
            "tests_sha256": {p.name: oc.file_sha256(p) for p in sorted((tmp / "tests").glob("*.py"))},
            "score_sha256": oc.file_sha256(tmp / "score.py"),
            "machine_sha256": oc.file_sha256(tmp / "machine.py")}


def measure_rows(run: Path, tmp: Path, label: str, entries: list, reps: int) -> list:
    rows_path = run / "export" / label / "rows.jsonl"
    done = {r["key"] for r in oc.read_rows(rows_path)}
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": ""}
    for entry in entries:
        program = machine.load_program(entry["program_path"])
        for rep in range(reps):
            key = f"{entry['program_sha256']}|export_{label}|0.1|{rep}"
            if key in done:
                continue
            started = time.perf_counter()
            timed_out = False
            try:
                proc = subprocess.run([oc.PYTHON, "compiler.py", entry["program_path"]],
                                      cwd=str(tmp), capture_output=True, text=True,
                                      timeout=TIMEOUT, env=env)
                stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
            except subprocess.TimeoutExpired as exc:
                timed_out, code = True, None
                stdout = exc.stdout if isinstance(exc.stdout, str) else ""
                stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            seconds = time.perf_counter() - started
            row = {"key": key, "program_sha256": entry["program_sha256"],
                   "family": entry["family"], "corpus": entry["corpus"], "repetition": rep,
                   "exit_code": code, "timed_out": timed_out, "process_seconds": seconds,
                   "stderr_tail": stderr[-500:]}
            try:
                if stdout.count("\n") != 1 or not stdout.endswith("\n"):
                    raise ValueError("stdout is not exactly one JSON line")
                compiled = json.loads(stdout)
                cycles = machine.check_compilation(program, compiled)
                for case in program["cases"]:
                    machine.check_case(program, compiled, case)
                scratch = machine.scratch_footprint(program, compiled)
                row.update(cycles=cycles, scratch=scratch, product=cycles * scratch,
                           program_name=program["name"], correctness="PASS")
            except Exception as exc:  # retained as a failed row
                row.update(correctness="FAIL", failure=f"{type(exc).__name__}: {exc}")
            row["failed_row"] = row["correctness"] != "PASS" or code != 0 or timed_out
            oc.append_row(rows_path, row)
    return oc.read_rows(rows_path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--label", default="nonmodel")
    args = parser.parse_args(argv)
    run = Path(args.run).resolve()
    frozen = json.loads((run / "FROZEN_SELECTION.json").read_text())
    depth = frozen["model"]["selected_depth"] if args.label == "model" else None
    report = {"label": args.label}
    built_path = run / "export" / args.label / "compiler.py"
    if built_path.exists():
        report["build"] = {"path": str(built_path), "sha256": oc.file_sha256(built_path),
                           "note": "existing export reused; regenerate check below"}
    else:
        report["build"] = build(run, frozen, args.label, depth)
    # Determinism: regenerate into a temporary path and compare bytes.
    with tempfile.TemporaryDirectory() as regen:
        again = Path(regen) / "compiler.py"
        argv2 = [oc.PYTHON, "-m", "research.optimization_export", "--config",
                 frozen["search"]["config"], "--build", frozen["search"]["build"],
                 "--output", str(again)] + (["--model-depth", str(depth)] if depth else [])
        subprocess.run(argv2, cwd=str(oc.ROOT), capture_output=True, text=True,
                       env={"PATH": os.environ.get("PATH", ""),
                            "PYTHONPATH": f"{oc.ROOT / '.reference'}:{oc.ROOT}"})
        report["deterministic_regeneration"] = oc.file_sha256(again) == oc.file_sha256(built_path)
    tmp = workspace(built_path)
    report["workspace"] = str(tmp)
    report["pinned"] = pinned_checks(tmp, run / "export" / args.label / "pinned")
    public = [dict(e, corpus="public") for e in json.loads(
        (run / "stages" / "D_public" / "STAGE_MANIFEST.json").read_text())["extra"]["programs"]]
    pinned_public = {p.stem: p for p in (run / "inputs" / "public").glob("*.json")}
    from tests_direct import generate_programs as gp

    for e in public:
        match = [p for p in pinned_public.values()
                 if gp.program_digest(machine.load_program(p)) == e["program_sha256"]]
        e["program_path"] = str(match[0])
    fresh = [dict(e, corpus="fresh") for e in
             json.loads((run / "FRESH_COHORT.json").read_text())["programs"]]
    rows = measure_rows(run, tmp, args.label, public + fresh, 3)
    report["rows"] = len(rows)
    report["expected_rows"] = 624
    report["failed_rows"] = sum(r["failed_row"] for r in rows)
    # Bound by the valid bootstrap incumbent, and compare with research rows.
    boot = {}
    research = {}
    for stage in ("D_fresh_compiler", "D_public"):
        for r in oc.read_rows(run / "stages" / stage / "rows.jsonl"):
            if r["arm"] == "accepted_bootstrap" and not r["failed_row"]:
                boot[r["program_sha256"]] = r["product"]
            if r["arm"] == "selected_nonmodel" and r["budget_seconds"] == 0.1 and \
                    not r["failed_row"]:
                research.setdefault(r["program_sha256"], set()).add(r["product"])
    above = [r["key"] for r in rows if not r["failed_row"] and
             r["product"] > boot[r["program_sha256"]]]
    differs = [r["key"] for r in rows if not r["failed_row"] and
               r["product"] not in research.get(r["program_sha256"], set())]
    report["outputs_above_bootstrap"] = above
    report["outputs_outside_research_J_set"] = {"count": len(differs), "first": differs[:10],
                                                "note": "budget-sensitive; reported, not a "
                                                        "failure by itself"}
    serial = {}
    from research import optimization_stage_a as sa

    frozen_serial = sa.frozen_serial()
    scores = []
    for rep in range(3):
        chosen = [r for r in rows if r["corpus"] == "public" and r["repetition"] == rep]
        if len(chosen) == 8 and not any(r["failed_row"] for r in chosen):
            sp = math.exp(sum(math.log(frozen_serial[r["program_name"]]["cycles"] / r["cycles"])
                              for r in chosen) / 8)
            sc = math.exp(sum(math.log(frozen_serial[r["program_name"]]["scratch"] /
                                       r["scratch"]) for r in chosen) / 8)
            scores.append(math.sqrt(sp * sc))
        else:
            scores.append(None)
    report["export_public_scores"] = scores
    times = sorted(r["process_seconds"] for r in rows if not r["failed_row"])
    report["process_seconds"] = {"median": times[len(times) // 2] if times else None,
                                 "max": times[-1] if times else None}
    report["status"] = ("PASS" if report["rows"] == 624 and report["failed_rows"] == 0 and
                        not above and report["pinned"]["compiler_is_export"] and
                        report["pinned"]["pinned_tests_exit"] == 0 and
                        report["pinned"]["score_exit"] == 0 and
                        report["deterministic_regeneration"] and
                        not report["build"].get("component_mismatches") else "FAIL")
    oc.write_json(run / "export" / args.label / "EXPORT_VALIDATION.json", report)
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps({k: report[k] for k in ("status", "rows", "failed_rows",
                                             "export_public_scores")}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
