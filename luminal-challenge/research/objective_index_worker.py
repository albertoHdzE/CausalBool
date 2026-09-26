"""One NEW-arm compiler measurement per process (objective-index protocol 1.0).

Measures ``objective_index_search.optimise`` (A1-A4) -- or, when the fixture
gate has enabled it, the conditional learned compiler pair -- from the
original direct bootstrap on one program under one budget, then validates the
returned compilation with the pinned machine on every case. The frozen A0 and
the accepted controls are measured by ``optimization_frozen_worker`` in the
frozen workspace, never here.

Usage (internal; the runner builds the spec)::

    PYTHONPATH=.reference:. python -m research.objective_index_worker --spec JSON
"""

from __future__ import annotations

import argparse
import json
import sys
import time

_IMPORT_STARTED = time.perf_counter()

import machine  # noqa: E402

import compare_direct as official  # noqa: E402
import direct_compiler as dcomp  # noqa: E402
import direct_contract as dc  # noqa: E402

from research import objective_index_search as ois  # noqa: E402
from research import structural_encoding as se  # noqa: E402

_IMPORT_SECONDS = time.perf_counter() - _IMPORT_STARTED

KIND = "objective_index_measurement"
STATUS_CODES = {"SAT": "S", "UNSAT": "U", "UNKNOWN_SEARCH": "K", "INFEASIBLE": "I",
                "UNKNOWN_CONSTRUCTION": "C", "QUERY_EXPIRED": "Q", "FAIL": "F",
                "NOT_RUN": "N", "NO_STRICT_IMPROVEMENT": "P", "UNKNOWN": "K"}


def imported_sources() -> dict:
    names = ("research", "research.objective_index_search", "research.objective_index_common",
             "research.structural_search", "research.structural_encoding",
             "research.run_structural_experiments", "research.schema_ranker",
             "research.objective_index_learned", "direct_compiler", "direct_contract",
             "direct_optimizer", "direct_constraints", "schema_index", "machine")
    return {name: getattr(sys.modules.get(name), "__file__", None) for name in names
            if name in sys.modules}


def compact(record: dict) -> dict:
    """The optimisation record with its per-query list summarised."""

    queries = record.get("queries", [])
    out = {key: value for key, value in record.items() if key != "queries"}
    out["query_status_sequence"] = "".join(STATUS_CODES.get(q.get("status"), "?")
                                           for q in queries[:2048])
    out["query_bits_max"] = max((q.get("bits", 0) or 0 for q in queries), default=0)
    out["rejected_completions"] = record.get("rejected_completions", [])[:16]
    if record.get("arm") == "A4_multiscale_search":
        out["query_policies"] = {}
        for q in queries:
            key = f"{q.get('policy')}|{q.get('status')}"
            out["query_policies"][key] = out["query_policies"].get(key, 0) + 1
        out["frontier_peak_max"] = max((q.get("frontier_peak", 0) for q in queries), default=0)
    return out


def measure(spec: dict) -> dict:
    if spec.get("kind") != KIND:
        raise ValueError("not an objective-index measurement spec")
    program = machine.load_program(spec["program_path"])
    budget = float(spec["budget_seconds"])
    arm = spec["solver_arm"]
    cpu_started = time.process_time()
    started = time.perf_counter()
    facts = dc.derive(program)
    bootstrap_compiled, bootstrap_report = dcomp.compile_with_report(
        program, dcomp.DEFAULT_LIMITS, optimise=False)
    bootstrap_seconds = bootstrap_report["bootstrap"]["seconds"]
    times = se.issue_cycles_of(program, bootstrap_compiled["bundles"])
    addresses = dict(bootstrap_compiled["scratch"])
    if spec.get("learned"):
        from research import objective_index_learned as oil

        best_times, best_addresses, record = oil.optimise(
            program, facts, times, addresses, arm=arm, budget_seconds=budget,
            labels_mode=spec["learned"])
    else:
        best_times, best_addresses, record = ois.optimise(
            program, facts, times, addresses, arm=arm, budget_seconds=budget)
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
    return {
        "kind": KIND + "_result",
        "program_name": program["name"],
        "program_sha256": spec["program_sha256"],
        "solver_arm": arm,
        "learned": spec.get("learned"),
        "budget_seconds": budget,
        "repetition": spec["repetition"],
        "cycles": cycles,
        "scratch": scratch,
        "product": cycles * scratch,
        "cases": cases,
        "import_seconds": _IMPORT_SECONDS,
        "bootstrap_seconds": bootstrap_seconds,
        "compile_seconds": compile_seconds,
        "cpu_seconds": cpu_seconds,
        "validate_seconds": validate_seconds,
        "optimisation_seconds": record["seconds"],
        "overshoot_seconds": record["overshoot_seconds"],
        "peak_rss_bytes": official.peak_rss_bytes(),
        "optimisation": compact(record),
        "discrepancy_count": discrepancies,
        "best_incumbent_sha256": se.object_digest(se.normalise_compilation(facts, compiled)),
        "imported_sources": imported_sources(),
        # A validator rejection seen during search is a defect even though the
        # returned incumbent itself validated: it overrides a clean final check.
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
