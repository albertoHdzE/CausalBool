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
    # Additive stage for the optimization phase: the measurement harness's own
    # regressions. Acceptance semantics of every stage above are unchanged; a
    # stage running zero tests still fails and there is still no success banner.
    "benchmark": "tests_direct.test_benchmark_harness",
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

# The frozen public suite. A run that reports any other number is not it.
EXPECTED_PUBLIC_TESTS = 11


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


def public_suite_verdict(exit_code: int, stderr: str, timed_out: bool) -> Dict[str, object]:
    """The frozen public suite passes only at exactly the expected count.

    Accepting "any positive number" would let a suite that silently shrank, or
    one discovered from the wrong directory, still read PASS.
    """

    match = RAN_PATTERN.search(stderr or "")
    count = int(match.group(1)) if match else 0
    passed = exit_code == 0 and count == EXPECTED_PUBLIC_TESTS and not timed_out
    return {
        "status": "PASS" if passed else "FAIL",
        "tests": count,
        "expected_tests": EXPECTED_PUBLIC_TESTS,
        "timed_out": timed_out,
        "exit_code": exit_code,
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


PROHIBITED = ("common", "compilers", "index_query", "repertoire_program", "direct_compiler")

# One input per process. Started with -I -S from a neutral directory holding
# only the export and the pinned machine module, so the development tree is
# unreachable and per-input interpreter start, import and serialisation cost
# is inside the measured external limit.
ISOLATED_WORKER = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import machine

def prohibited(*args, **kwargs):
    raise AssertionError("serial_compile was called by the direct export")

machine.serial_compile = prohibited
import compiler

program = machine.load_program(sys.argv[2])
before = json.dumps(program, sort_keys=True)
compiled, report = compiler.compile_with_report(program)
assert json.dumps(program, sort_keys=True) == before, "the input program was modified"
machine.check_compilation(program, compiled)
cases = 0
for case in program["cases"]:
    machine.check_case(program, compiled, case)
    cases += 1
banned = {"common", "compilers", "index_query", "repertoire_program", "direct_compiler"}
leaked = sorted(name for name in sys.modules if name.split(".")[0] in banned)
optimisation = report.get("optimisation", {})
print(json.dumps({
    "cases": cases,
    "cycles": len(compiled["bundles"]),
    "footprint": report["footprint"],
    "bootstrap": report.get("bootstrap", {}),
    "discrepancy_count": report.get("discrepancy_count", 0),
    "validation_errors": optimisation.get("validation_errors", []),
    "target_discrepancies": optimisation.get("target_discrepancies", []),
    "accepted": optimisation.get("accepted", 0),
    "statuses": optimisation.get("statuses", {}),
    "seconds": report.get("seconds"),
    "compiler_path": compiler.__file__,
    "leaked": leaked,
}))
'''


def run_isolated_corpus(
    corpus_directory: Path,
    export_path: Path,
    timeout: float,
    output: Path,
    expected: int,
) -> Dict[str, object]:
    """Compile every corpus input in its own fresh, isolated process.

    A single long-lived process would let a slow input hide behind the others
    and would never pay per-input interpreter start and import cost, which the
    external limit does include. Each record keeps the input hash, exit code,
    wall time, case count and the compilation's own diagnostics, so one failure
    fails the stage without discarding the rest.
    """

    import shutil
    import tempfile

    paths = sorted(corpus_directory.glob("*.json"))
    runs: List[Dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="direct-isolated-") as directory:
        neutral = Path(directory)
        shutil.copyfile(export_path, neutral / "compiler.py")
        shutil.copyfile(REFERENCE / "machine.py", neutral / "machine.py")
        for path in paths:
            started = time.monotonic()
            entry: Dict[str, object] = {
                "program": path.name,
                "sha256": digest(path),
            }
            try:
                completed = subprocess.run(
                    [sys.executable, "-I", "-S", "-c", ISOLATED_WORKER,
                     str(neutral), str(path)],
                    cwd=str(neutral),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                entry["exit_code"] = completed.returncode
                if completed.returncode == 0:
                    try:
                        payload = json.loads(completed.stdout)
                    except json.JSONDecodeError:
                        payload = {}
                        entry["error"] = "worker output was not JSON"
                    entry["result"] = payload
                    good = (
                        bool(payload)
                        and payload.get("cases", 0) > 0
                        and payload.get("discrepancy_count", 0) == 0
                        and not payload.get("leaked")
                    )
                    entry["status"] = "PASS" if good else "FAIL"
                    if not good and "error" not in entry:
                        entry["error"] = (
                            "discrepancy or module leak recorded by the compilation"
                        )
                else:
                    entry["status"] = "FAIL"
                    entry["stderr_tail"] = completed.stderr[-1500:]
            except subprocess.TimeoutExpired:
                entry["status"] = "FAIL"
                entry["error"] = f"process exceeded the external {timeout} s limit"
                entry["timed_out"] = True
            entry["process_seconds"] = time.monotonic() - started
            runs.append(entry)

    passed = [entry for entry in runs if entry["status"] == "PASS"]
    failures = [entry for entry in runs if entry["status"] != "PASS"]
    discrepancies = [
        entry
        for entry in runs
        if entry.get("result", {}).get("discrepancy_count", 0)
    ]
    payload = {
        "programs": len(runs),
        "expected": expected,
        "passed": len(passed),
        "failures": failures,
        "timeout_seconds": timeout,
        "export_sha256": digest(export_path),
        "max_process_seconds": max((e["process_seconds"] for e in runs), default=0.0),
        "cases": sum(e.get("result", {}).get("cases", 0) for e in runs),
        "accepted_improvements": sum(
            e.get("result", {}).get("accepted", 0) for e in runs
        ),
        "runs": runs,
    }
    (output / "isolated_corpus.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )

    ok = len(runs) == expected and not failures and not discrepancies and runs
    return {
        "stage": "acceptance",
        "step": "corpus",
        "status": "PASS" if ok else "FAIL",
        "programs_expected": expected,
        "programs_checked": len(passed),
        "cases_checked": payload["cases"],
        "failures": [e["program"] for e in failures],
        "discrepancies": [e["program"] for e in discrepancies],
        "max_process_seconds": payload["max_process_seconds"],
        "accepted_improvements": payload["accepted_improvements"],
        "evidence": str(output / "isolated_corpus.json"),
    }


def run_acceptance(
    output: Path, logs: Path, timeout: float, export_path: Path
) -> List[Dict[str, object]]:
    steps: List[Dict[str, object]] = []
    logs.mkdir(parents=True, exist_ok=True)
    corpus_directory = output / "corpus"
    manifest = materialise_corpus(corpus_directory)
    (output / "corpus_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    export_directory = export_path.parent
    import os

    # 1. Every corpus input in its own fresh process, each under the external
    #    limit, with diagnostics read back from the same compilation that was
    #    measured.
    corpus_record = run_isolated_corpus(
        corpus_directory, export_path, timeout, output, manifest["expected_size"]
    )
    steps.append(corpus_record)

    # 2. The unchanged public suite, which imports `compiler` by name.
    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(export_directory), str(REFERENCE)])
    started = time.monotonic()
    public_timed_out = False
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(REFERENCE / "tests"),
             "-t", str(REFERENCE), "-v"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=max(timeout, 600),
            env=env,
        )
        public_code, public_err = completed.returncode, completed.stderr
    except subprocess.TimeoutExpired as exc:
        # Caught rather than propagated: an escaping exception would leave the
        # previous summary on disk, still reading PASS.
        public_timed_out = True
        public_code = 124
        public_err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    (logs / "acceptance_public_suite.stderr.txt").write_text(public_err, encoding="utf-8")
    verdict = public_suite_verdict(public_code, public_err, public_timed_out)
    verdict.update(
        {
            "stage": "acceptance",
            "step": "public_suite",
            "command": "python3 -m unittest discover -s .reference/tests -t .reference",
            "seconds": time.monotonic() - started,
            "stderr_tail": public_err[-2000:],
        }
    )
    steps.append(verdict)

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

    summary_path = output / "summary.json"
    # Claim the file first. If this run aborts, dies or times out, what remains
    # on disk says so rather than showing the previous run's verdict.
    summary_path.write_text(
        json.dumps(
            {
                "status": "IN_PROGRESS",
                "requested_stage": arguments.stage,
                "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "note": "a run was started and has not recorded a verdict",
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

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
    summary_path.write_text(
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
