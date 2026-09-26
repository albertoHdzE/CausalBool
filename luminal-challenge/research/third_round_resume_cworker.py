"""Stage C fresh-process worker: R0/C1 through ``third_round_resume_dworker`` (unchanged),
or the isolated serial public comparator (``machine.serial_compile``, the score
denominator) for ``arm_id == "serial"``. Serial compilation exists only here.
"""

from __future__ import annotations

import time

_IMPORT_STARTED = time.perf_counter()

import argparse  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402

import machine  # noqa: E402

_IMPORT_SECONDS = time.perf_counter() - _IMPORT_STARTED


def serial(spec: dict) -> dict:
    program = machine.load_program(spec["program_path"])
    started = time.perf_counter()
    compiled = machine.serial_compile(program)
    seconds = time.perf_counter() - started
    cycles = machine.check_compilation(program, compiled)
    cases = 0
    for case in program["cases"]:
        machine.check_case(program, compiled, case)
        cases += 1
    scratch = machine.scratch_footprint(program, compiled)
    return {"compile_call_seconds": seconds, "cycles": cycles, "scratch": scratch,
            "J": cycles * scratch, "cases": cases, "correctness": "PASS",
            "discrepancy_count": 0, "import_seconds": _IMPORT_SECONDS,
            "solver_version": "machine.serial_compile",
            "loaded_solvers": sorted(n for n in ("research.efficiency_search",
                                                 "research.third_round_candidate")
                                     if n in sys.modules)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    args = parser.parse_args(argv)
    spec = json.loads(args.spec)
    if spec["arm_id"] == "serial":
        out = serial(spec)
    else:
        from research import third_round_resume_dworker as dw
        out = dw.measure(spec)
    sys.stdout.write(json.dumps(out, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
