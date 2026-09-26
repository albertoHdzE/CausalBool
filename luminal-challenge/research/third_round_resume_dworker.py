"""One fresh-process measurement of R0 or C1 (Stages D and C of the third round).

Modes (parent protocol ``mode_keys``):

- ``work:10000``: fixed work -- A4 catalog, DFS, constant logical clock for every
  global/query/slice expiry, aggregate 10,000 nodes, 100,000 validations,
  2,048-node slices, every other R0 limit unchanged. The decision fingerprint
  (search trace, incumbent, certificate stream, statuses, aggregate, stop reason)
  is returned for exact pair parity.
- ``wall:0.01`` / ``wall:0.1`` / ``wall:1.0``: R0's defaults (query .1 s, 2 ms /
  2,048-node slices, 8 resident, 4,096 frontier, 1,000,000 nodes, 100,000
  validations) with that optimisation allowance, real clock.
- ``peak_memory``: tracemalloc peak of the fixed-work call plus its fingerprint.

``compile_call_seconds`` is a separate real ``perf_counter`` around the COMPLETE
compile call: derive, direct bootstrap, set-up, search with validation, final
compilation. Import time is recorded separately. Correctness is checked AFTER the
timed call with the pinned machine (every case), outside the timing.

Only the arm's solver module is imported (C1 imports R0's module through the BS1
kernel, whose classes subclass R0's ``Propagation``; the R0 process never loads C1).
"""

from __future__ import annotations

import time

_IMPORT_STARTED = time.perf_counter()

import argparse  # noqa: E402
import hashlib  # noqa: E402
import importlib  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402

import machine  # noqa: E402

import direct_compiler as dcomp  # noqa: E402
import direct_contract as dc  # noqa: E402

from research import structural_encoding as se  # noqa: E402

ARMS = {"R0": "research.efficiency_search", "C1": "research.third_round_candidate"}
FIXED = {"aggregate_nodes": 10_000, "aggregate_validations": 100_000, "slice_nodes": 2048}


class _Constant:
    def __call__(self) -> float:
        return 0.0


def program_of(spec: dict) -> dict:
    if spec.get("program_path"):
        return machine.load_program(spec["program_path"])
    from tests_direct import generate_programs as gp
    return gp.additional_program(int(spec["seed"]))


def compile_call(module, program: dict, mode: str, trace=None):
    facts = dc.derive(program)
    compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
    times = se.issue_cycles_of(program, compiled["bundles"])
    addresses = dict(compiled["scratch"])
    stats = module.PropagationStats()
    if mode in ("work:10000", "peak_memory"):
        best_t, best_a, record = module.multiscale_optimise(
            program, facts, times, addresses, budget_seconds=0.1,
            node_ceiling=FIXED["aggregate_nodes"],
            validation_ceiling=FIXED["aggregate_validations"],
            slice_nodes=FIXED["slice_nodes"], clock=_Constant(), stats=stats, trace=trace,
            catalog="a4", traversal="dfs")
    elif mode.startswith("wall:"):
        best_t, best_a, record = module.multiscale_optimise(
            program, facts, times, addresses, budget_seconds=float(mode.split(":")[1]),
            stats=stats, trace=trace, catalog="a4", traversal="dfs")
    else:
        raise ValueError(mode)
    final = dc.compilation(facts, best_t, best_a)
    return final, record, facts, stats


def fingerprint(record, trace, compiled, facts) -> dict:
    return {"trace_sha256": hashlib.sha256(repr(trace).encode()).hexdigest(),
            "trace_length": len(trace),
            "incumbent_sha256": se.object_digest(se.normalise_compilation(facts, compiled)),
            "certificates": record["propagation"]["certificate_stream_sha256"],
            "certificate_count": record["propagation"]["certificate_stream_length"],
            "statuses": record["statuses"], "aggregate": record["aggregate"],
            "stopped_because": record["stopped_because"]}


def measure(spec: dict) -> dict:
    module = importlib.import_module(ARMS[spec["arm_id"]])
    program = program_of(spec)
    mode = spec["mode_key"]
    fixed = mode in ("work:10000", "peak_memory")
    trace = [] if fixed else None
    if mode == "peak_memory":
        import tracemalloc
        tracemalloc.start()
    started = time.perf_counter()
    compiled, record, facts, stats = compile_call(module, program, mode, trace)
    seconds = time.perf_counter() - started
    out = {"compile_call_seconds": seconds}
    if mode == "peak_memory":
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        out = {"tracemalloc_peak_bytes": peak, "compile_call_seconds_under_tracemalloc": seconds}
    cycles = machine.check_compilation(program, compiled)
    cases = 0
    for case in program["cases"]:
        machine.check_case(program, compiled, case)
        cases += 1
    scratch = machine.scratch_footprint(program, compiled)
    out.update({
        "solver_version": module.VERSION, "solver_file": module.__file__,
        "import_seconds": _IMPORT_SECONDS, "cycles": cycles, "scratch": scratch,
        "J": cycles * scratch, "cases": cases,
        "nodes": record["aggregate"]["nodes"], "validations": record["aggregate"]["validations"],
        "certificates": stats.stream_length, "statuses": record["statuses"],
        "stopped_because": record["stopped_because"],
        "optimisation_seconds": record["seconds"], "overshoot_seconds": record["overshoot_seconds"],
        "unknown_queries": sum(v for k, v in record["statuses"].items() if k.startswith("UNKNOWN")),
        "construction_overrun_count": record.get("construction_overrun_count"),
        "construction_interruption_count": record.get("construction_interruption_count"),
        "interrupted_validation_total": record.get("interrupted_validation_total"),
        "discrepancy_count": record["discrepancy_count"],
        "frontier_peak_max": max((q.get("frontier_peak", 0) for q in record.get("queries", [])),
                                 default=0),
        "incumbent_sha256": se.object_digest(se.normalise_compilation(facts, compiled)),
        "correctness": "PASS" if record["discrepancy_count"] == 0 else "FAIL",
        "loaded_solvers": sorted(n for n in ARMS.values() if n in sys.modules)})
    if fixed:
        out["fingerprint"] = fingerprint(record, trace, compiled, facts)
    return out


_IMPORT_SECONDS = time.perf_counter() - _IMPORT_STARTED


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    args = parser.parse_args(argv)
    sys.stdout.write(json.dumps(measure(json.loads(args.spec)), sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
