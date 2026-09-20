"""Staged acceptance runner for the direct-index compiler.

Task L06 of ``plan/INDEX_ONLY_PLAN.md``, section 8.2.

Stages are ``schema``, ``contract``, ``constraints``, ``construction``,
``optimizer``, ``independence``, ``export``, ``acceptance`` and ``all``. The
first seven run their correspondingly owned test modules. ``acceptance``
materialises the corpus and runs it, and the unchanged public suite, against
the standalone export in fresh processes whose import path holds only the
export directory and the supplied machine module.

Every stage records its real command, exit code and counts. A stage that runs
zero tests or zero programs fails. There is no unconditional success banner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent
REFERENCE = ROOT / ".reference"

TEST_STAGES = {
    "schema": "tests_direct.test_schema_index",
    "contract": "tests_direct.test_contract",
    "constraints": "tests_direct.test_constraints",
    "construction": "tests_direct.test_construction",
    "optimizer": "tests_direct.test_optimizer",
    "independence": "tests_direct.test_independence",
    "export": "tests_direct.test_export",
}
STAGE_ORDER = list(TEST_STAGES) + ["acceptance"]
ALL_STAGES = STAGE_ORDER + ["all"]

SOURCES = (
    "schema_index.py",
    "direct_contract.py",
    "direct_constraints.py",
    "direct_optimizer.py",
    "direct_compiler.py",
    "export_direct.py",
    "verify_direct.py",
    "compare_direct.py",
)

RAN_PATTERN = re.compile(r"^Ran (\d+) tests? in", re.MULTILINE)


class StageFailure(Exception):
    pass


def digest(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: List[str], logs: Path, label: str, timeout: float,
        env=None, cwd=None) -> Dict[str, object]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd or ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        code, out, err = completed.returncode, completed.stdout, completed.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        code, timed_out = 124, True
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{label}.stdout.txt").write_text(out, encoding="utf-8")
    (logs / f"{label}.stderr.txt").write_text(err, encoding="utf-8")
    return {
        "command": " ".join(command),
        "exit_code": code,
        "timed_out": timed_out,
        "seconds": time.monotonic() - started,
        "stdout_tail": out[-2000:],
        "stderr_tail": err[-2000:],
    }


def environment() -> Dict[str, str]:
    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = f"{REFERENCE}{os.pathsep}{ROOT}"
    return env


def run_test_stage(name: str, logs: Path, timeout: float) -> Dict[str, object]:
    module = TEST_STAGES[name]
    command = [sys.executable, "-m", "unittest", module, "-v"]
    import os

    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=environment(),
        )
        code, out, err = completed.returncode, completed.stdout, completed.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        code, timed_out = 124, True
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{name}.stdout.txt").write_text(out, encoding="utf-8")
    (logs / f"{name}.stderr.txt").write_text(err, encoding="utf-8")

    match = RAN_PATTERN.search(err) or RAN_PATTERN.search(out)
    count = int(match.group(1)) if match else 0
    status = "PASS" if code == 0 and count > 0 and not timed_out else "FAIL"
    if count == 0:
        status = "FAIL"
    return {
        "stage": name,
        "module": module,
        "status": status,
        "tests": count,
        "command": " ".join(command),
        "exit_code": code,
        "timed_out": timed_out,
        "seconds": time.monotonic() - started,
        "stderr_tail": err[-2000:],
    }


def materialise_corpus(destination: Path) -> Dict[str, object]:
    """Write the corpus to JSON so the acceptance process needs no project code."""

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(REFERENCE))
    from tests_direct import generate_programs as gp

    destination.mkdir(parents=True, exist_ok=True)
    manifest = gp.corpus_manifest()
    programs = gp.corpus()
    written = []
    for index, program in enumerate(programs):
        path = destination / f"{index:03d}_{program['name']}.json"
        path.write_text(json.dumps(program, sort_keys=True), encoding="utf-8")
        written.append(path.name)
    manifest["files"] = written
    return manifest


ACCEPTANCE_WORKER = r'''
import json, sys, time
from pathlib import Path
import machine
import compiler

directory = Path(sys.argv[1])
paths = sorted(directory.glob("*.json"))
checked = cases = 0
failures = []
slowest = 0.0
for path in paths:
    program = machine.load_program(path)
    started = time.monotonic()
    try:
        result = compiler.compile_program(program)
        elapsed = time.monotonic() - started
        machine.check_compilation(program, result)
        for case in program["cases"]:
            machine.check_case(program, result, case)
            cases += 1
    except Exception as exc:
        failures.append({"program": program["name"], "error": repr(exc)})
        continue
    slowest = max(slowest, elapsed)
    checked += 1
print(json.dumps({
    "programs": len(paths),
    "checked": checked,
    "cases": cases,
    "failures": failures,
    "slowest_seconds": slowest,
    "modules": sorted(m for m in sys.modules if not m.startswith("_")),
}))
'''


def run_acceptance(
    output: Path, logs: Path, timeout: float, export_path: Path
) -> List[Dict[str, object]]:
    steps: List[Dict[str, object]] = []
    corpus_directory = output / "corpus"
    manifest = materialise_corpus(corpus_directory)
    (output / "corpus_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    export_directory = export_path.parent

    # 1. The whole corpus, through the export, with only the standard library
    #    and the supplied machine module importable.
    import os
    import tempfile

    worker_env = dict(os.environ)
    worker_env["PYTHONPATH"] = os.pathsep.join([str(export_directory), str(REFERENCE)])
    record = run(
        [sys.executable, "-c", ACCEPTANCE_WORKER, str(corpus_directory)],
        logs,
        "acceptance_corpus",
        timeout=max(timeout, 900),
        env=worker_env,
        cwd=tempfile.gettempdir(),
    )
    # Read the complete log, not the truncated tail kept for the summary:
    # the worker's payload lists every loaded module and is far longer.
    payload = {}
    if record["exit_code"] == 0:
        try:
            payload = json.loads(
                (logs / "acceptance_corpus.stdout.txt").read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            payload = {}
    expected = manifest["expected_size"]
    ok = (
        record["exit_code"] == 0
        and payload.get("checked") == expected
        and not payload.get("failures")
        and payload.get("cases", 0) > 0
    )
    leaked = [
        name
        for name in payload.get("modules", [])
        if name in ("common", "compilers", "index_query", "repertoire_program")
    ]
    if leaked:
        ok = False
    record.update(
        {
            "stage": "acceptance",
            "step": "corpus",
            "status": "PASS" if ok else "FAIL",
            "programs_expected": expected,
            "programs_checked": payload.get("checked", 0),
            "cases_checked": payload.get("cases", 0),
            "failures": payload.get("failures", []),
            "slowest_seconds": payload.get("slowest_seconds"),
            "leaked_modules": leaked,
        }
    )
    record.pop("stdout_tail", None)
    steps.append(record)

    # 2. The unchanged public suite, which imports `compiler` by name.
    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(export_directory), str(REFERENCE)])
    started = time.monotonic()
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(REFERENCE / "tests"),
         "-t", str(REFERENCE), "-v"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=max(timeout, 600),
        env=env,
    )
    (logs / "acceptance_public_suite.stderr.txt").write_text(
        completed.stderr, encoding="utf-8"
    )
    match = RAN_PATTERN.search(completed.stderr)
    count = int(match.group(1)) if match else 0
    steps.append(
        {
            "stage": "acceptance",
            "step": "public_suite",
            "status": "PASS" if completed.returncode == 0 and count > 0 else "FAIL",
            "tests": count,
            "expected_tests": 11,
            "command": "python3 -m unittest discover -s .reference/tests -t .reference",
            "exit_code": completed.returncode,
            "seconds": time.monotonic() - started,
            "stderr_tail": completed.stderr[-2000:],
        }
    )

    # 3. The documented command line, one fresh process per public program,
    #    under the external timeout. Only JSON may reach stdout.
    cli = {"stage": "acceptance", "step": "cli", "programs": [], "status": "PASS"}
    for path in sorted((REFERENCE / "programs").glob("*.json")):
        started = time.monotonic()
        try:
            completed = subprocess.run(
                [sys.executable, str(export_path), str(path)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            timed_out = False
        except subprocess.TimeoutExpired:
            completed = None
            timed_out = True
        entry = {"program": path.name, "timed_out": timed_out}
        if timed_out or completed is None:
            entry.update({"status": "FAIL", "seconds": timeout})
            cli["status"] = "FAIL"
        else:
            try:
                json.loads(completed.stdout)
                clean_json = True
            except json.JSONDecodeError:
                clean_json = False
            good = completed.returncode == 0 and clean_json
            entry.update(
                {
                    "status": "PASS" if good else "FAIL",
                    "exit_code": completed.returncode,
                    "stdout_is_json": clean_json,
                    "stderr_present": bool(completed.stderr.strip()),
                    "seconds": time.monotonic() - started,
                }
            )
            if not good:
                cli["status"] = "FAIL"
        cli["programs"].append(entry)
    if not cli["programs"]:
        cli["status"] = "FAIL"
    steps.append(cli)
    return steps


def main(argv) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", default="all", help="stage to run")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument(
        "--output", default=str(ROOT / "results" / "direct_index_v1" / "verification")
    )
    arguments = parser.parse_args(argv)

    if arguments.stage not in ALL_STAGES:
        print(
            f"unknown stage {arguments.stage!r}; expected one of {', '.join(ALL_STAGES)}",
            file=sys.stderr,
        )
        return 2

    # Absolute: the acceptance worker runs from a neutral directory.
    output = Path(arguments.output).resolve()
    logs = output / "logs"
    output.mkdir(parents=True, exist_ok=True)

    requested = STAGE_ORDER if arguments.stage == "all" else [arguments.stage]
    records: List[Dict[str, object]] = []
    export_path = ROOT / ".build" / "direct_index" / "compiler.py"
    export_record = None

    if any(stage in ("export", "acceptance") for stage in requested):
        sys.path.insert(0, str(ROOT))
        import export_direct

        try:
            export_direct.export(export_path)
            export_record = {
                "status": "PASS",
                "path": str(export_path),
                "sha256": digest(export_path),
                "lines": len(export_path.read_text(encoding="utf-8").splitlines()),
            }
        except (SyntaxError, RuntimeError) as exc:
            export_record = {"status": "FAIL", "error": str(exc)}

    for stage in requested:
        if stage in TEST_STAGES:
            records.append(run_test_stage(stage, logs, arguments.timeout * 60))
        elif stage == "acceptance":
            if export_record is None or export_record["status"] != "PASS":
                records.append(
                    {
                        "stage": "acceptance",
                        "status": "FAIL",
                        "error": "the export is unavailable, so acceptance cannot run",
                    }
                )
                continue
            records.extend(run_acceptance(output, logs, arguments.timeout, export_path))

    failures = [record for record in records if record.get("status") != "PASS"]
    if export_record is not None and export_record["status"] != "PASS":
        failures.append({"stage": "export_assembly", "status": "FAIL"})
    if not records:
        failures.append({"stage": arguments.stage, "status": "FAIL", "error": "no stage ran"})

    summary = {
        "requested_stage": arguments.stage,
        "stages_run": [record.get("stage") for record in records],
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "records": records,
        "export": export_record,
        "python": sys.version,
        "platform": platform.platform(),
        "timeout_seconds": arguments.timeout,
        "reference_commit": json.loads((ROOT / "reference.json").read_text())["commit"],
        "source_sha256": {name: digest(ROOT / name) for name in SOURCES},
        "test_sha256": {
            path.name: digest(path)
            for path in sorted((ROOT / "tests_direct").glob("*.py"))
        },
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )

    for record in records:
        label = record.get("step", record.get("stage"))
        print(
            f"{record.get('stage')}/{label}: {record.get('status')} "
            f"tests={record.get('tests', '-')} programs={record.get('programs_checked', '-')}",
            file=sys.stderr,
        )
    print(f"overall: {summary['status']} ({len(failures)} failing)", file=sys.stderr)
    print(str(output / "summary.json"))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
