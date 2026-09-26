"""Frozen-control measurement worker (optimization protocol 1.0, section 2).

This file is copied, byte for byte and hash-recorded, into the root of a
frozen-control workspace whose ``research/`` directory is a verified copy of
the accepted ``final_source_v2`` snapshot and whose ``plan/`` is a link to the
protected plan tree. Run there, ``import research`` resolves to the accepted
snapshot and every production dependency resolves to the protected, lock
verified modules of ``luminal-challenge``. Nothing from the current, possibly
modified research tree can be imported: the script removes its own directory
from ``sys.path`` and refuses to run if ``research`` resolves anywhere else.

Arms:

- ``frozen_phase2`` -> accepted ``run_measurement`` with arm ``structural_bound``;
- ``accepted_bootstrap``, ``accepted_default``, ``accepted_budgeted`` -> the
  same accepted entry point, which calls the unchanged production compiler;
- ``classical`` -> the accepted isolated classical worker's ``measure``;
- ``serial`` -> ``machine.serial_compile``, the score denominator.

Usage::

    python WORKSPACE/optimization_frozen_worker.py --workspace WORKSPACE \
        --challenge LUMINAL_ROOT --spec JSON
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

KIND = "optimization_frozen_measurement"
ARM_MAP = {"frozen_phase2": "structural_bound", "accepted_bootstrap": "accepted_bootstrap",
           "accepted_default": "accepted_default", "accepted_budgeted": "accepted_budgeted"}


def _configure(workspace: Path, challenge: Path) -> None:
    here = str(Path(__file__).resolve().parent)
    kept = [entry for entry in sys.path
            if entry and Path(entry).resolve() != Path(here) and "luminal-challenge/research"
            not in entry]
    sys.path[:] = [str(workspace), str(challenge / ".reference"), str(challenge)] + kept


def _imported(workspace: Path) -> dict:
    out = {}
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, "__file__", None)
        if not path:
            continue
        if name == "research" or name.startswith("research.") or name in (
                "machine", "direct_compiler", "direct_contract", "direct_optimizer",
                "direct_constraints", "schema_index", "common", "compare_direct"):
            # Paths only: hashing here would add work to control processes that
            # NEW-arm processes do not pay. Hashes come from the isolation probe.
            out[name] = path
    research = out.get("research", "")
    if not Path(research).resolve().is_relative_to(workspace.resolve()):
        raise RuntimeError(f"research resolved outside the frozen workspace: {research}")
    return out


def measure(spec: dict, workspace: Path) -> dict:
    if spec.get("kind") != KIND:
        raise ValueError("not a frozen-control spec")
    arm = spec["arm"]
    if arm == "serial":
        import machine
        import compare_direct

        program = machine.load_program(spec["program_path"])
        started = time.perf_counter()
        compiled = machine.serial_compile(program)
        compile_seconds = time.perf_counter() - started
        cycles = machine.check_compilation(program, compiled)
        for case in program["cases"]:
            machine.check_case(program, compiled, case)
        scratch = machine.scratch_footprint(program, compiled)
        result = {"program_name": program["name"], "cycles": cycles, "scratch": scratch,
                  "product": cycles * scratch, "cases": len(program["cases"]),
                  "compile_seconds": compile_seconds, "import_seconds": 0.0,
                  "peak_rss_bytes": compare_direct.peak_rss_bytes(), "correctness": "PASS",
                  "discrepancy_count": 0, "optimisation": {}}
    elif arm == "classical":
        from research import classical_measurement_worker as cw

        inner = dict(spec["inner"])
        result = cw.measure(inner)
    else:
        from research import run_structural_experiments as rse

        inner = dict(spec["inner"])
        if inner.get("arm") != ARM_MAP[arm]:
            raise ValueError("frozen arm and accepted worker arm disagree")
        result = rse.run_measurement(inner)
        optimisation = result.get("optimisation") or {}
        queries = optimisation.pop("queries", None)
        if queries is not None:
            optimisation["query_status_sequence"] = "".join(
                {"SAT": "S", "UNSAT": "U", "UNKNOWN": "K", "INFEASIBLE": "I",
                 "UNKNOWN_CONSTRUCTION": "C", "FAIL": "F"}.get(
                    q.get("status") or q.get("report", {}).get("status"), "?")
                for q in queries)
        result["optimisation"] = optimisation
    result = dict(result)
    result.pop("kind", None)
    result.update(kind=KIND + "_result", arm=arm, program_sha256=spec["program_sha256"],
                  budget_seconds=spec.get("budget_seconds"), repetition=spec["repetition"],
                  imported_sources=_imported(workspace))
    if result.get("discrepancy_count"):
        result["correctness"] = "FAIL"
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--challenge", required=True)
    parser.add_argument("--spec", required=True)
    args = parser.parse_args(argv)
    workspace, challenge = Path(args.workspace), Path(args.challenge)
    if not workspace.is_absolute() or not challenge.is_absolute():
        print("frozen worker failed: workspace and challenge paths must be absolute",
              file=sys.stderr)
        return 1
    _configure(workspace, challenge)
    try:
        result = measure(json.loads(args.spec), workspace)
    except Exception as exc:  # retained by the harness as a failed row
        print(f"frozen worker failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":"),
                                allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
