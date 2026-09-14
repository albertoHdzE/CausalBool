"""Run and seal prerequisites; a saved success flag alone cannot open the gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from .io import atomic_write_json, read_json
from .joint_study import ROOT, study_provenance
from .records import seal
from .program_benchmark import validate_program_benchmark
from .release import run_release_gate


def validate_preflight(root):
    path = Path(root) / "preflight/report.json"
    try:
        report = read_json(path)
        errors = []
        if report["provenance"] != study_provenance():
            errors.append("stale_preflight_sources")
        if not report["passed"] or report["errors"]:
            errors.append("preflight_failed")
        for filename, digest in report["artifact_hashes"].items():
            if hashlib.sha256((path.parent / filename).read_bytes()).hexdigest() != digest:
                errors.append(f"changed_preflight_artifact:{filename}")
        if set(report["artifact_hashes"]) != {"pytest.xml", "walkthrough.executed.ipynb", "evidence.json"}:
            errors.append("missing_preflight_artifacts")
        counts = report.get("tests", {})
        if not counts.get("tests") or any(counts.get(k) != 0 for k in ("errors", "failures", "skipped")):
            errors.append("missing_or_failed_test_evidence")
        return {"valid": not errors, "errors": errors}
    except (OSError, ValueError, KeyError) as exc:
        return {"valid": False, "errors": [f"preflight_unavailable:{exc}"]}


def run_preflight(root):
    root = Path(root).resolve() / "preflight"
    root.mkdir(parents=True, exist_ok=True)
    provenance = study_provenance()
    errors = []
    junit = root / "pytest.xml"
    commands = [
        [sys.executable, "-m", "pytest", "doppel-challenge/tests",
         "tests/analysis/test_description_length_is_algorithmic.py",
         "tests/analysis/test_description_lengths_values.py", "-q", f"--junitxml={junit}"],
        [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute",
         "--ExecutePreprocessor.timeout=300", "--output", str(root / "walkthrough.executed.ipynb"),
         "doppel-challenge/notebooks/01_exact_n8_walkthrough.ipynb"],
    ]
    logs = []
    for command in commands:
        try:
            proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=900)
            logs.append({"command": command, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
            if proc.returncode:
                errors.append("prerequisite_command_failed")
                break
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"prerequisite_command_error:{exc}")
            break
    tests = {}
    try:
        suites = list(ET.parse(junit).getroot().iter("testsuite"))
        tests = {k: sum(int(s.get(k, "0")) for s in suites) for k in ("tests", "failures", "errors", "skipped")}
        if not tests["tests"] or any(tests[k] for k in ("failures", "errors", "skipped")):
            errors.append("tests_failed_or_skipped")
        notebook = json.loads((root / "walkthrough.executed.ipynb").read_text())
        if any(o.get("output_type") == "error" for c in notebook["cells"] for o in c.get("outputs", [])):
            errors.append("notebook_error")
        if any(c.get("execution_count") is None for c in notebook["cells"] if c["cell_type"] == "code" and "".join(c["source"]).strip()):
            errors.append("notebook_incomplete")
    except (OSError, ValueError, ET.ParseError) as exc:
        errors.append(f"verification_artifact_error:{exc}")
    benchmark = read_json(ROOT / "doppel-challenge/results/shared_program/shared_program_benchmark.json")
    benchmark_audit = validate_program_benchmark(benchmark)
    legacy_audit = run_release_gate(ROOT / "doppel-challenge/results/exact_small")
    if not benchmark_audit["valid"] or not benchmark["release_ready"] or legacy_audit["status"] != "passed":
        errors.append("existing_artifact_audit_failed")
    if provenance != study_provenance():
        errors.append("sources_changed_during_preflight")
    evidence = {"logs": logs, "benchmark_audit": benchmark_audit, "legacy_audit": legacy_audit,
                "benchmark_sha256": benchmark["sha256"]}
    atomic_write_json(root / "evidence.json", seal(evidence))
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
              (junit, root / "walkthrough.executed.ipynb", root / "evidence.json") if p.exists()}
    report = seal({"record_kind": "joint_study_preflight", "provenance": provenance,
                   "passed": not errors, "errors": errors, "tests": tests, "artifact_hashes": hashes})
    atomic_write_json(root / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "doppel-challenge/results/joint_degree5_v2")
    args = parser.parse_args()
    report = run_preflight(args.out_dir)
    print(json.dumps({k: report[k] for k in ("passed", "errors", "tests")}, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
