"""Isolated classical-control measurement subprocess.

This module imports no Phase 2 codec, search, model or oracle code. It invokes the
unchanged ``common.classical_compile`` once, then validates that compilation with
the pinned machine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify_policy(spec: dict) -> None:
    expected_id = "luminal-phase2-recovery-1.0"
    if spec.get("amendment_id") != expected_id:
        raise ValueError("classical measurement requires the frozen amendment")
    lock = json.loads((ROOT / "plan/phase2_recovery/LOCK.json").read_text())
    if lock.get("amendment_id") != expected_id:
        raise ValueError("recovery lock identity changed")
    digests = {}
    for name, digest in lock["files"].items():
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f"frozen policy digest mismatch: {name}")
        digests[name] = actual
    if spec.get("amendment_files") != digests:
        raise ValueError("worker amendment hashes differ from the frozen policy")


def measure(spec: dict) -> dict:
    verify_policy(spec)
    if spec.get("arm") != "classical" or spec.get("budget_seconds") is not None or spec.get("search_seed") is not None:
        raise ValueError("classical control must be unbudgeted and unseeded")
    cpu_started = time.process_time()
    import machine

    program = machine.load_program(spec["program_path"])
    started = time.perf_counter()
    import common
    import_seconds = time.perf_counter() - started
    started = time.perf_counter()
    compiled = common.classical_compile(program)
    compile_seconds = time.perf_counter() - started
    started = time.perf_counter()
    cycles = machine.check_compilation(program, compiled)
    for case in program["cases"]:
        machine.check_case(program, compiled, case)
    scratch = machine.scratch_footprint(program, compiled)
    validate_seconds = time.perf_counter() - started
    import compare_direct
    return {
        "kind": "phase2_measurement_result",
        "stage": spec["stage"], "corpus": spec["corpus"],
        "program_name": program["name"], "program_sha256": spec["program_sha256"],
        "domain_sha256": spec.get("domain_sha256"), "codec": None,
        "arm": "classical", "budget_seconds": None, "search_seed": None,
        "repetition": spec["repetition"], "attempt": spec.get("attempt", 0),
        "cycles": cycles, "scratch": scratch, "product": cycles * scratch,
        "cases": len(program["cases"]), "import_seconds": import_seconds,
        "bootstrap_seconds": None, "compile_seconds": compile_seconds,
        "cpu_seconds": time.process_time() - cpu_started, "validate_seconds": validate_seconds,
        "peak_rss_bytes": compare_direct.peak_rss_bytes(),
        "peak_rss_conversion": "darwin:bytes" if sys.platform == "darwin" else "posix:kilobytes",
        "limits": None, "optimisation": {}, "discrepancy_count": 0,
        "original_incumbent_sha256": None, "best_incumbent_sha256": None,
        "correctness": "PASS",
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    arguments = parser.parse_args(argv)
    try:
        result = measure(json.loads(arguments.spec))
    except Exception as exc:  # retained by Harness as a failed worker row
        print(f"classical worker failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
