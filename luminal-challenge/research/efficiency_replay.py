"""Guarded, oracle-free replay of the 420 retained orderings (efficiency phase, R3).

Isolation verification, NOT a new experiment: every original ordering input of
``next_round_20260925/stages/L_orderings`` is replayed exactly once, with the
oracle-free boundary ``research/efficiency_ranker.py``, and must reproduce the
retained ordered indices, ordering digest and model description. No new fixture
cohort, fitting policy, seed or efficacy hypothesis; the original rows stay
the evidence of record, and the learning outcomes are recounted by the
successor auditor, not re-estimated here.

The minimal workspace (``<run>/ranker_replay/workspace``) holds exactly two
code files -- ``efficiency_ranker.py`` and the production ``schema_index.py``,
byte copies with hashes -- a guard entry ``guard.py``, and one hash-checked copy
of each fixture's ``RANKER_INPUT.json`` (never its ``EVALUATOR.json``). Each
replay is a fresh ``python -I -S`` process whose guard, before anything else:

- installs a meta-path finder that REFUSES every import whose top-level name is
  neither standard library (``sys.stdlib_module_names``) nor one of the two
  workspace modules, so no oracle, evaluator, fixture, research, machine or
  production module can load;
- installs an audit hook that classifies every ``open``: standard-library and
  workspace code reads are ``code``; the one declared ranker input is
  ``ranker_input``; anything else is REFUSED (``PermissionError``) and logged.

``--control`` runs two planted violations through the same guard (importing
``research.structural_oracle``; opening the fixture's ``EVALUATOR.json``) and
requires both to be refused: a guard that denies nothing proves nothing.

Usage::

    PYTHONPATH=.reference:. python -m research.efficiency_replay --run DIR
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from research import efficiency_common as ec
from research import optimization_common as oc

SOURCE_RUN = ec.NEXT_ROUND_RUN
STAGE = "ranker_isolation_replay"
PYTHON = sys.executable

GUARD = r'''
import json, os, sys
WORKSPACE = os.path.dirname(os.path.abspath(__file__))
ALLOWED_MODULES = {"efficiency_ranker", "schema_index"}
EVENTS = {"code": 0, "ranker_input": [], "refused_opens": [], "refused_imports": []}
DECLARED = os.environ.get("EFFICIENCY_RANKER_INPUT", "")
BASES = tuple(os.path.realpath(p) for p in {sys.base_prefix, sys.prefix, sys.exec_prefix})


class Deny:
    def find_spec(self, name, path=None, target=None):
        top = name.split(".")[0]
        if top in sys.stdlib_module_names or top in ALLOWED_MODULES:
            return None
        EVENTS["refused_imports"].append(name)
        raise ImportError(f"guard: import of {name!r} refused")


def classify(path):
    real = os.path.realpath(path)
    if DECLARED and real == os.path.realpath(DECLARED):
        return "ranker_input"
    if real.startswith(BASES):
        return "code"
    if real.startswith(os.path.join(WORKSPACE, "")) and (
            real.endswith((".py", ".pyc")) or os.path.basename(os.path.dirname(real))
            == "__pycache__" or os.path.isdir(real)):
        return "code"
    return None


def hook(event, args):
    if event != "open" or not args or not isinstance(args[0], (str, bytes, os.PathLike)):
        return
    path = os.fsdecode(args[0])
    kind = classify(path)
    if kind == "ranker_input":
        EVENTS["ranker_input"].append(path)
    elif kind == "code":
        EVENTS["code"] += 1
    else:
        EVENTS["refused_opens"].append(path)
        raise PermissionError(f"guard: open of {path!r} refused")


sys.meta_path.insert(0, Deny())
sys.path[:] = [WORKSPACE] + [p for p in sys.path if os.path.realpath(p).startswith(BASES)]
sys.addaudithook(hook)

mode = sys.argv[1]
result = {"mode": mode}
try:
    if mode == "replay":
        import efficiency_ranker
        result["replay"] = efficiency_ranker.replay(json.loads(sys.argv[2]))
    elif mode == "control_import":
        import research.structural_oracle  # noqa: F401  (must be refused)
        result["violation"] = "import succeeded"
    elif mode == "control_open":
        with open(sys.argv[2], "rb") as handle:  # must be refused
            handle.read(1)
        result["violation"] = "open succeeded"
    result["status"] = "OK"
except BaseException as exc:
    result["status"] = "REFUSED" if isinstance(exc, (ImportError, PermissionError)) else "ERROR"
    result["error"] = f"{type(exc).__name__}: {exc}"
result["events"] = EVENTS
result["loaded_modules"] = sorted(sys.modules)
sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
'''

CODE_FILES = {"efficiency_ranker.py": "research/efficiency_ranker.py",
              "schema_index.py": "schema_index.py"}


def original_rows() -> list:
    """The 420 retained ordering rows, read strictly (a torn line is an error)."""

    path = SOURCE_RUN / "stages" / "L_orderings" / "rows.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if len(rows) != ec.EXPECTED_ROWS[STAGE]:
        raise RuntimeError(f"expected {ec.EXPECTED_ROWS[STAGE]} ordering rows, found {len(rows)}")
    return rows


def build_workspace(out: Path) -> dict:
    workspace = out / "workspace"
    if workspace.exists():
        raise FileExistsError(f"refusing to reuse {workspace}")
    (workspace / "inputs").mkdir(parents=True)
    manifest = {"code": {}, "inputs": {}}
    for name, source in CODE_FILES.items():
        shutil.copyfile(ec.ROOT / source, workspace / name)
        manifest["code"][name] = {"source": source,
                                  "sha256": oc.file_sha256(ec.ROOT / source),
                                  "copy_sha256": oc.file_sha256(workspace / name)}
    (workspace / "guard.py").write_text(GUARD)
    manifest["code"]["guard.py"] = {"sha256": oc.file_sha256(workspace / "guard.py")}
    evaluation = json.loads((SOURCE_RUN / "learning" / "DESIGN_EVALUATION.json").read_text())
    for design in evaluation["designs"]:
        source = Path(design["ranker_input"])
        digest = oc.file_sha256(source)
        if digest != design["ranker_input_sha256"]:
            raise RuntimeError(f"{design['fixture_id']}: ranker input hash differs")
        target = workspace / "inputs" / design["fixture_id"] / "RANKER_INPUT.json"
        target.parent.mkdir()
        shutil.copyfile(source, target)
        manifest["inputs"][design["fixture_id"]] = {
            "source": str(source), "sha256": digest, "copy_sha256": oc.file_sha256(target),
            "evaluator_copied": False}
    listing = sorted(str(p.relative_to(workspace)) for p in workspace.rglob("*") if p.is_file())
    manifest["listing"] = listing
    oc.write_immutable_json(out / "WORKSPACE_MANIFEST.json", manifest)
    return manifest


def guarded(workspace: Path, argv: list, declared: str = "") -> dict:
    started = time.perf_counter()
    proc = subprocess.run([PYTHON, "-I", "-S", str(workspace / "guard.py"), *argv],
                          cwd=str(workspace), capture_output=True, text=True,
                          env={"EFFICIENCY_RANKER_INPUT": declared, "PATH": "/usr/bin:/bin"},
                          timeout=ec.EXTERNAL_SECONDS)
    seconds = time.perf_counter() - started
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = None
    return {"exit_code": proc.returncode, "seconds": seconds, "payload": payload,
            "stderr_tail": proc.stderr[-2000:]}


def controls(run: Path, workspace: Path) -> dict:
    evaluation = json.loads((SOURCE_RUN / "learning" / "DESIGN_EVALUATION.json").read_text())
    first = evaluation["designs"][0]
    evaluator = Path(first["ranker_input"]).with_name("EVALUATOR.json")
    out = {}
    for mode, argv in (("control_import", []), ("control_open", [str(evaluator)])):
        result = guarded(workspace, [mode, *argv])
        ec.charge(run, STAGE + "_control", mode, result["seconds"])
        payload = result["payload"] or {}
        out[mode] = {"status": payload.get("status"), "error": payload.get("error"),
                     "events": payload.get("events"), "exit_code": result["exit_code"],
                     "refused": payload.get("status") == "REFUSED"}
    out["status"] = "PASS" if all(v["refused"] for k, v in out.items()) else "FAIL"
    return out


# Module-name COMPONENTS (not substrings) that mark oracle or evaluator
# capability. Attempt 1 matched substrings, so the standard library's
# ``importlib.machinery`` matched ``machine`` and every row was marked failed
# although each reproduced its ordering; see ``evaluate`` and the disclosure.
ORACLE_MARKERS = ("structural_oracle", "next_round_learning", "objective_index_fixtures",
                  "optimization_fixtures", "machine", "research")
ALLOWED_NON_STDLIB = ("__main__", "efficiency_ranker", "schema_index")


def oracle_like(modules) -> list:
    return sorted(m for m in modules if any(part in ORACLE_MARKERS for part in m.split(".")))


def run(run_path: Path) -> dict:
    run_path = Path(run_path)
    out = run_path / "ranker_replay"
    if (out / "rows.jsonl").exists():
        raise FileExistsError("the replay runs exactly once; rows already exist")
    manifest = build_workspace(out)
    workspace = out / "workspace"
    control = controls(run_path, workspace)
    oc.write_immutable_json(out / "GUARD_CONTROLS.json", control)
    if control["status"] != "PASS":
        raise RuntimeError("the guard failed to refuse a planted violation")
    evaluation = json.loads((SOURCE_RUN / "learning" / "DESIGN_EVALUATION.json").read_text())
    designs = {d["fixture_id"]: d for d in evaluation["designs"]}
    rows = original_rows()
    summary = collections.Counter()
    for row in rows:
        if ec.cap_reached(run_path):
            raise RuntimeError("measurement wall cap reached")
        original = row["result"]
        fixture = original["fixture_id"]
        design = designs[fixture]
        target = workspace / "inputs" / fixture / "RANKER_INPUT.json"
        spec = {"kind": "efficiency_ranker_replay", "ranker_input": str(target),
                "ranker_input_sha256": design["ranker_input_sha256"],
                "ordering": original["ordering"]}
        result = guarded(workspace, ["replay", json.dumps(spec)], str(target))
        ec.charge(run_path, STAGE, row["key"], result["seconds"])
        payload = result["payload"] or {}
        replay = payload.get("replay") or {}
        events = payload.get("events") or {}
        loaded = payload.get("loaded_modules") or []
        record = {
            "key": row["key"], "fixture_id": fixture, "ordering": original["ordering"],
            "exit_code": result["exit_code"], "status": payload.get("status"),
            "error": payload.get("error"), "process_seconds": result["seconds"],
            "original_ordering_sha256": original["ordering_sha256"],
            "replay_ordering_sha256": replay.get("ordering_sha256"),
            "ordered_identical": replay.get("ordered") == original["ordered"],
            "digest_identical": replay.get("ordering_sha256") == original["ordering_sha256"],
            "info_identical": replay.get("info") == original["info"],
            "code_opens": events.get("code"), "ranker_input_opens": events.get("ranker_input"),
            "refused_opens": events.get("refused_opens"),
            "refused_imports": events.get("refused_imports"),
            "loaded_non_stdlib": sorted(m for m in loaded
                                        if m.split(".")[0] not in sys.stdlib_module_names),
            "loaded_oracle_like": oracle_like(loaded),
            "stderr_tail": result["stderr_tail"][-400:],
        }
        record["pass"] = row_passes(record, workspace)["pass"]
        oc.append_row(out / "rows.jsonl", record)
        summary["rows"] += 1
        summary["pass"] += record["pass"]
    keys = [r["key"] for r in rows]
    report = {
        "stage": STAGE, "label": "isolation verification of retained orderings; not a fresh "
                                 "statistical confirmation",
        "expected": ec.EXPECTED_ROWS[STAGE], "replayed": summary["rows"],
        "passed": summary["pass"], "distinct_keys": len(set(keys)),
        "source_rows_sha256": oc.file_sha256(SOURCE_RUN / "stages" / "L_orderings" / "rows.jsonl"),
        "workspace_code": manifest["code"], "guard_controls": control["status"],
        "status": ("PASS" if summary["rows"] == summary["pass"] == ec.EXPECTED_ROWS[STAGE]
                   and len(set(keys)) == len(keys) else "FAIL"),
    }
    oc.write_immutable_json(out / "REPLAY_REPORT.json", report)
    return report


def row_passes(record: dict, workspace: Path) -> dict:
    """The corrected predicate, from retained raw fields only (no re-execution)."""

    target = str(workspace / "inputs" / record["fixture_id"] / "RANKER_INPUT.json")
    checks = {
        "exit_zero": record["exit_code"] == 0, "status_ok": record["status"] == "OK",
        "ordered_identical": record["ordered_identical"] is True,
        "digest_identical": record["digest_identical"] is True,
        "info_identical": record["info_identical"] is True,
        "no_refused_open": record["refused_opens"] == [],
        "no_refused_import": record["refused_imports"] == [],
        "only_allowed_non_stdlib_modules": set(record["loaded_non_stdlib"])
        <= set(ALLOWED_NON_STDLIB),
        "no_oracle_component_module": oracle_like(record["loaded_non_stdlib"]) == [],
        "one_declared_input_read": record["ranker_input_opens"] == [target],
    }
    return {"pass": all(checks.values()), "failed_checks": sorted(k for k, v in checks.items()
                                                                  if not v)}


def evaluate(run_path: Path) -> dict:
    """Re-evaluate the retained attempt-1 rows with the corrected predicate."""

    out = Path(run_path) / "ranker_replay"
    path = out / "rows.jsonl"
    lines = path.read_text().splitlines()
    rows = [json.loads(line) for line in lines]          # strict: a torn row raises
    workspace = out / "workspace"
    source = {r["key"]: r for r in original_rows()}
    evaluated = [dict(key=r["key"], **row_passes(r, workspace)) for r in rows]
    keys = [r["key"] for r in rows]
    failed = collections.Counter(c for e in evaluated for c in e["failed_checks"])
    report = {
        "attempt": 1, "re_executed": False,
        "predicate": "row_passes (component-exact oracle markers; allowed non-stdlib modules "
                     f"{list(ALLOWED_NON_STDLIB)})",
        "rows_sha256": oc.file_sha256(path), "rows": len(rows),
        "expected": ec.EXPECTED_ROWS[STAGE], "keys_equal_source": sorted(keys) == sorted(source),
        "distinct_keys": len(set(keys)), "passed": sum(e["pass"] for e in evaluated),
        "failed_checks": dict(failed),
        "digest_identical": sum(r["digest_identical"] for r in rows),
        "ordered_identical": sum(r["ordered_identical"] for r in rows),
        "info_identical": sum(r["info_identical"] for r in rows),
        "loaded_non_stdlib_sets": dict(collections.Counter(
            ",".join(r["loaded_non_stdlib"]) for r in rows)),
        "original_substring_predicate_false_positive": dict(collections.Counter(
            ",".join(r["loaded_oracle_like"]) for r in rows)),
    }
    report["status"] = ("PASS" if report["rows"] == report["expected"] == report["passed"]
                        == report["distinct_keys"] and report["keys_equal_source"] else "FAIL")
    oc.write_immutable_json(out / "REPLAY_EVALUATION.json", report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--evaluate", action="store_true",
                        help="re-evaluate retained rows; never re-executes a replay")
    args = parser.parse_args(argv)
    if args.evaluate:
        report = evaluate(Path(args.run).resolve())
        print(json.dumps({k: report[k] for k in ("status", "rows", "passed", "failed_checks")}))
        return 0 if report["status"] == "PASS" else 1
    report = run(Path(args.run).resolve())
    print(json.dumps({k: report[k] for k in ("status", "expected", "replayed", "passed",
                                             "guard_controls")}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
