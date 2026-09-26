"""One NEW-arm compiler measurement per process (optimization protocol 1.0).

Measures ``optimization_search.optimise`` from the frozen direct bootstrap on
one program under one configuration, budget, build and search arm, then
validates the returned compilation with the pinned machine on every case. The
frozen control is measured by ``optimization_frozen_worker``, never here.

Usage (internal; the runner builds the spec)::

    PYTHONPATH=.reference:. python -m research.optimization_worker --spec JSON
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

from research import optimization_search as osr  # noqa: E402
from research import structural_encoding as se  # noqa: E402

_IMPORT_SECONDS = time.perf_counter() - _IMPORT_STARTED

KIND = "optimization_new_measurement"
STATUS_CODES = {"SAT": "S", "UNSAT": "U", "UNKNOWN": "K", "INFEASIBLE": "I",
                "UNKNOWN_CONSTRUCTION": "C", "QUERY_EXPIRED": "Q", "FAIL": "F",
                "NOT_RUN": "N"}


def imported_sources() -> dict:
    """Actual file paths of the research and production modules in this process."""

    names = ("research", "research.optimization_search", "research.structural_search",
             "research.structural_encoding", "research.structural_models",
             "research.run_structural_experiments", "direct_compiler", "direct_contract",
             "direct_optimizer", "direct_constraints", "schema_index", "machine")
    return {name: getattr(sys.modules.get(name), "__file__", None) for name in names}


def compact(record: dict) -> dict:
    """The optimisation record without its per-query list, which is summarised."""

    queries = record.get("queries", [])
    out = {key: value for key, value in record.items() if key != "queries"}
    out["query_status_sequence"] = "".join(STATUS_CODES.get(q.get("status"), "?")
                                           for q in queries)
    out["query_bits_max"] = max((q.get("bits", 0) for q in queries), default=0)
    out["model_queries"] = [q["model"] for q in queries if "model" in q][:64]
    return out


def measure(spec: dict) -> dict:
    if spec.get("kind") != KIND:
        raise ValueError("not a NEW-arm measurement spec")
    program = machine.load_program(spec["program_path"])
    budget = float(spec["budget_seconds"])
    cpu_started = time.process_time()
    started = time.perf_counter()
    facts = dc.derive(program)
    bootstrap_compiled, bootstrap_report = dcomp.compile_with_report(
        program, dcomp.DEFAULT_LIMITS, optimise=False)
    bootstrap_seconds = bootstrap_report["bootstrap"]["seconds"]
    times = se.issue_cycles_of(program, bootstrap_compiled["bundles"])
    addresses = dict(bootstrap_compiled["scratch"])
    best_times, best_addresses, record = osr.optimise(
        program, facts, times, addresses,
        config=spec["config"], budget_seconds=budget, search_arm=spec["search_arm"],
        build=spec["build"], model_depth=spec.get("model_depth"),
    )
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
        "arm": spec["arm"],
        "config": spec["config"],
        "build": spec["build"],
        "search_arm": spec["search_arm"],
        "model_depth": spec.get("model_depth"),
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
