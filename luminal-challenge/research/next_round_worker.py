"""One successor-solver measurement per process (next round 1.0).

Imports the SUCCESSOR ``research.next_round_search`` explicitly (never the
frozen ``objective_index_search``), measures one ablation cell -- or, after
Stage E, the frozen engineering variant -- from the original direct bootstrap
on one program, then validates the returned compilation with the pinned
machine on every case.

The earlier ``cap512_wider`` optimizer is not measured here: its rows come
from the unchanged ``research.optimization_worker``; classical, the accepted
bootstrap and serial come from the unchanged frozen-workspace worker.

Spec fields: ``catalog``, ``traversal``, ``variant`` (``null`` or
``"engineered"``), ``budget_seconds``; ``work_limit`` switches to the fixed-work
diagnostic (aggregate node ceiling, no wall allowance except the external
safety limit). Every cost is recorded separately: import, bootstrap,
optimisation, the complete compile call and final validation; the runner adds
the fresh-process wall time.

Usage (internal; the runner builds the spec)::

    PYTHONPATH=.reference:. python -m research.next_round_worker --spec JSON
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time

_IMPORT_STARTED = time.perf_counter()

import machine  # noqa: E402

import compare_direct as official  # noqa: E402
import direct_compiler as dcomp  # noqa: E402
import direct_contract as dc  # noqa: E402

from research import next_round_search as nrs  # noqa: E402
from research import structural_encoding as se  # noqa: E402

_IMPORT_SECONDS = time.perf_counter() - _IMPORT_STARTED

KIND = "next_round_measurement"
UNLIMITED = 1e9
VARIANTS = {None: "research.next_round_search", "engineered": "research.next_round_engineered"}


def solver(variant):
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}")
    return nrs if variant is None else importlib.import_module(VARIANTS[variant])


def imported_sources() -> dict:
    names = ("research", "research.next_round_search", "research.next_round_engineered",
             "research.objective_index_search", "research.objective_index_common",
             "research.structural_search", "research.structural_encoding",
             "research.run_structural_experiments", "direct_compiler", "direct_contract",
             "direct_optimizer", "direct_constraints", "schema_index", "machine")
    return {name: getattr(sys.modules.get(name), "__file__", None) for name in names
            if name in sys.modules}


STATUS_CODES = {"SAT": "S", "UNSAT": "U", "UNKNOWN_SEARCH": "K", "INFEASIBLE": "I",
                "UNKNOWN_CONSTRUCTION": "C", "QUERY_EXPIRED": "Q", "FAIL": "F",
                "NOT_RUN": "N", "NO_STRICT_IMPROVEMENT": "P", "UNKNOWN": "K"}


def compact(record: dict) -> dict:
    """The A4 branch of ``objective_index_worker.compact``, restated.

    Restated (15 lines) rather than imported because importing that worker
    loads the frozen solver into this process, and the isolation probe must
    show that only the successor is loaded. The repaired per-query lists are
    kept, truncated at 256 entries (their totals are exact in the record).
    """

    queries = record.get("queries", [])
    out = {key: value for key, value in record.items() if key != "queries"}
    out["query_status_sequence"] = "".join(STATUS_CODES.get(q.get("status"), "?")
                                           for q in queries[:2048])
    out["query_bits_max"] = max((q.get("bits", 0) or 0 for q in queries), default=0)
    out["rejected_completions"] = record.get("rejected_completions", [])[:16]
    out["query_policies"] = {}
    for q in queries:
        key = f"{q.get('policy')}|{q.get('status')}"
        out["query_policies"][key] = out["query_policies"].get(key, 0) + 1
    out["frontier_peak_max"] = max((q.get("frontier_peak", 0) for q in queries), default=0)
    for field in ("interrupted_validations_per_query", "construction_interruptions"):
        out[field] = record.get(field, [])[:256]
    return out


def optimise_kwargs(spec: dict) -> dict:
    kwargs = {"catalog": spec["catalog"], "traversal": spec["traversal"]}
    if spec.get("work_limit") is not None:
        kwargs.update(budget_seconds=UNLIMITED, query_seconds=UNLIMITED,
                      slice_seconds=UNLIMITED, node_ceiling=int(spec["work_limit"]))
    else:
        kwargs["budget_seconds"] = float(spec["budget_seconds"])
    return kwargs


def measure(spec: dict) -> dict:
    if spec.get("kind") != KIND:
        raise ValueError("not a next-round measurement spec")
    module = solver(spec.get("variant"))
    program = machine.load_program(spec["program_path"])
    cpu_started = time.process_time()
    started = time.perf_counter()
    facts = dc.derive(program)
    bootstrap_compiled, bootstrap_report = dcomp.compile_with_report(
        program, dcomp.DEFAULT_LIMITS, optimise=False)
    bootstrap_seconds = bootstrap_report["bootstrap"]["seconds"]
    times = se.issue_cycles_of(program, bootstrap_compiled["bundles"])
    addresses = dict(bootstrap_compiled["scratch"])
    before_optimise = time.perf_counter()
    stats = nrs.PropagationStats()
    best_times, best_addresses, record = module.multiscale_optimise(
        program, facts, times, addresses, stats=stats, **optimise_kwargs(spec))
    optimise_wall = time.perf_counter() - before_optimise
    compiled = dc.compilation(facts, best_times, best_addresses)
    compile_seconds = time.perf_counter() - started
    cpu_seconds = time.process_time() - cpu_started

    validate_started = time.perf_counter()
    cycles = machine.check_compilation(program, compiled)
    cases = 0
    for case in program["cases"]:
        machine.check_case(program, compiled, case)
        cases += 1
    scratch = machine.scratch_footprint(program, compiled)
    validate_seconds = time.perf_counter() - validate_started
    discrepancies = record["discrepancy_count"]
    bootstrap_cycles = max(times.values()) + 1
    bootstrap_scratch = dc.footprint(facts, addresses)
    return {
        "kind": KIND + "_result",
        "program_name": program["name"],
        "program_sha256": spec["program_sha256"],
        "catalog": spec["catalog"],
        "traversal": spec["traversal"],
        "variant": spec.get("variant"),
        "solver_version": getattr(module, "VERSION", None),
        "budget_seconds": spec.get("budget_seconds"),
        "work_limit": spec.get("work_limit"),
        "repetition": spec["repetition"],
        "cycles": cycles,
        "scratch": scratch,
        "product": cycles * scratch,
        "cases": cases,
        "bootstrap_cycles": bootstrap_cycles,
        "bootstrap_scratch": bootstrap_scratch,
        "bootstrap_product": bootstrap_cycles * bootstrap_scratch,
        "import_seconds": _IMPORT_SECONDS,
        "bootstrap_seconds": bootstrap_seconds,
        "bootstrap_wall_seconds": before_optimise - started,
        "optimisation_seconds": record["seconds"],
        "optimise_call_seconds": optimise_wall,
        "compile_seconds": compile_seconds,
        "cpu_seconds": cpu_seconds,
        "validate_seconds": validate_seconds,
        "overshoot_seconds": record["overshoot_seconds"],
        "peak_rss_bytes": official.peak_rss_bytes(),
        "work": {"charged_nodes": record["aggregate"]["nodes"],
                 "validations": record["aggregate"]["validations"],
                 "case_checks": record["aggregate"]["case_checks"],
                 "propagation_certificates": stats.stream_length,
                 "propagation_removed_values": sum(stats.removed_values.values()),
                 "definition": "charged node = one frontier pop (report.nodes); propagation "
                               "work = emitted deletion/prune certificates and removed values; "
                               "validations = paid candidate validations"},
        "trajectory": [[i["elapsed_seconds"], i["to"]] for i in record["improvements"]],
        "optimisation": compact(record),
        "discrepancy_count": discrepancies,
        "best_incumbent_sha256": se.object_digest(se.normalise_compilation(facts, compiled)),
        "imported_sources": imported_sources(),
        "correctness": "PASS" if discrepancies == 0 else "FAIL",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    args = parser.parse_args(argv)
    try:
        result = measure(json.loads(args.spec))
    except Exception as exc:  # retained by the harness as a failed row
        print(f"worker failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(se.canonical_json(result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
