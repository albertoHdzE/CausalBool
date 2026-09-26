"""Separate profiling runs of the development arms (next round 1.0, plan section 4).

One process profiles one arm on one program at one budget with ``cProfile``
and attributes every second of exclusive (``tottime``) time to exactly one
cost category. These rows are never timing rows: profiling slows the solver,
so under a wall-clock budget a profiled run does less work than a timed one.
The reconciliation reports the profiled total against the wall time of the
same profiled call, and the report compares category SHARES, not seconds,
with the timing rows.

Categories (declared before any profile was read):

- ``domain_construction``: caps, records, catalogs and window plans, codec
  domain building, propagation set-up, query initialisation;
- ``propagation``: the four propagation rules and their certificates (for the
  earlier optimizer, its structural bounds, the analogue of pruning);
- ``frontier``: node expansion (legal options, state copies, lifetimes,
  allocation order) and queueing (heap/stack pushes and pops, recursion);
- ``encoding_digest``: candidate materialisation, normalisation, canonical
  JSON, digests and index encoding;
- ``validation``: the pinned machine (``machine.py``);
- ``orchestration``: controllers, slices, meters, clocks and everything else.

Built-in functions and shared helper modules (``direct_contract``,
``direct_optimizer``, ``direct_constraints``, ``schema_index``, ``bisect``,
``heapq``, ``hashlib``, ``json``) have no category of their own: their time is
split over their callers' categories in proportion to the time each caller
edge spent in them (recursively through helper callers).

Usage (internal; the runner builds the spec)::

    PYTHONPATH=.reference:. python -m research.next_round_profile --spec JSON
"""

from __future__ import annotations

import argparse
import cProfile
import json
import os
import pstats
import sys
import time
from typing import Dict, Tuple

import machine

import direct_compiler as dcomp
import direct_contract as dc

from research import next_round_common as nrc
from research import next_round_search as nrs
from research import optimization_search as osr
from research import structural_encoding as se

KIND = "next_round_profile"
CATEGORIES = ("domain_construction", "propagation", "frontier", "encoding_digest",
              "validation", "orchestration")
HELPER_FILES = ("direct_contract.py", "direct_optimizer.py", "direct_constraints.py",
                "schema_index.py", "bisect.py", "heapq.py", "hashlib.py", "json/__init__.py",
                "json/encoder.py", "copy.py", "typing.py", "enum.py", "functools.py")

SEARCH_FILES = ("next_round_search.py", "next_round_engineered.py", "objective_index_search.py")
BY_NAME = {
    "domain_construction": {
        "product_caps", "neighborhood_record", "capped_record", "product_record",
        "product_window_plan", "build_catalog", "a3_catalog", "memory_group", "_k_queue",
        "initialize", "root", "query_plan", "windows_of_size", "from_record", "_checked_domain",
        "_plain_int", "_key_to_op", "_check_address", "_incumbent_first", "address_order",
        "cartesian_size", "ordered_domain", "decision_keys", "physical_address_domain",
        "matched_window_record", "schedule_conflict"},
    "propagation": {
        "times_fixpoint", "addresses_fixpoint", "product_bound", "compulsory_peak",
        "_static_max", "prune", "address_pairs", "_t", "_a", "emit", "cycle_bound",
        "scratch_bound", "peak_live_width", "bound_prunes", "_ss_prunes"},
    "frontier": {
        "children", "is_leaf", "heap_key", "push", "pop", "options", "copy", "time_options",
        "address_options", "recompute_lifetimes", "fixed_address_conflict", "_collides",
        "allocation_order", "descend_times", "descend_addresses", "charge_node", "dfs"},
    "encoding_digest": {
        "canonical_json", "object_digest", "normalise_compilation", "compilation_identity",
        "encode", "_field_value", "layout", "_rank_width", "field", "read", "write",
        "digest", "program_semantic_digest", "_digest_of", "_new_report", "objective",
        "consider", "compilation", "issue_cycles_of"},
}


def own_category(filename: str, name: str):
    """A category for a function we classify directly, or ``None`` for helpers."""

    base = filename.replace(os.sep, "/")
    if base.endswith("/machine.py"):
        return "validation"
    if filename == "~" or any(base.endswith("/" + h) or base.endswith(h) for h in HELPER_FILES):
        # ``direct_contract.compilation`` materialises a candidate: classified.
        if base.endswith("direct_contract.py") and name == "compilation":
            return "encoding_digest"
        return None
    if name == "__init__":
        if base.endswith(SEARCH_FILES) or base.endswith("structural_encoding.py"):
            return "domain_construction"
    for category, names in BY_NAME.items():
        if name in names:
            return category
    return "orchestration"


def attribute(stats: pstats.Stats) -> Tuple[Dict[str, float], Dict[str, list], float]:
    """Split every function's exclusive time over the six categories."""

    raw = stats.stats  # {func: (cc, nc, tt, ct, callers)}
    memo: Dict[tuple, Dict[str, float]] = {}

    def shares(func, depth=0) -> Dict[str, float]:
        """Fractions of ``func``'s time by category (1.0 in total)."""

        filename, _, name = func
        category = own_category(filename, name)
        if category is not None:
            return {category: 1.0}
        if func in memo:
            return memo[func]
        memo[func] = {"orchestration": 1.0}  # cycle guard
        callers = raw[func][4]
        weights: Dict[str, float] = {}
        total = 0.0
        for caller, edge in callers.items():
            tt = edge[2] if len(edge) > 2 else 0.0
            if tt <= 0 or depth > 12:
                continue
            total += tt
            for cat, share in shares(caller, depth + 1).items():
                weights[cat] = weights.get(cat, 0.0) + tt * share
        result = ({cat: w / total for cat, w in weights.items()} if total > 0
                  else {"orchestration": 1.0})
        memo[func] = result
        return result

    seconds = {category: 0.0 for category in CATEGORIES}
    top: Dict[str, list] = {category: [] for category in CATEGORIES}
    grand = 0.0
    for func, (cc, nc, tt, ct, callers) in raw.items():
        grand += tt
        for category, share in shares(func).items():
            seconds[category] += tt * share
            top[category].append((tt * share, f"{os.path.basename(func[0])}:{func[2]}"))
    for category in top:
        top[category] = [[name, round(value, 6)] for value, name in
                         sorted(top[category], reverse=True)[:8] if value > 0]
    return seconds, top, grand


def profile(spec: dict) -> dict:
    if spec.get("kind") != KIND:
        raise ValueError("not a next-round profile spec")
    program = machine.load_program(spec["program_path"])
    budget = float(spec["budget_seconds"])
    facts = dc.derive(program)
    compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
    times = se.issue_cycles_of(program, compiled["bundles"])
    addresses = dict(compiled["scratch"])
    target = spec["target"]
    profiler = cProfile.Profile()
    started = time.perf_counter()
    profiler.enable()
    if target == nrc.EARLIER:
        best_t, best_a, record = osr.optimise(
            program, facts, times, addresses, config=nrc.EARLIER_SPEC["config"],
            budget_seconds=budget, search_arm=nrc.EARLIER_SPEC["search_arm"],
            build=nrc.EARLIER_SPEC["build"], model_depth=nrc.EARLIER_SPEC["model_depth"])
    else:
        cell = nrc.CELLS[target]
        best_t, best_a, record = nrs.multiscale_optimise(
            program, facts, times, addresses, budget_seconds=budget,
            catalog=cell["catalog"], traversal=cell["traversal"])
    profiler.disable()
    wall = time.perf_counter() - started
    stats = pstats.Stats(profiler)
    seconds, top, grand = attribute(stats)
    final = dc.compilation(facts, best_t, best_a)
    cycles = machine.check_compilation(program, final)
    for case in program["cases"]:
        machine.check_case(program, final, case)
    scratch = machine.scratch_footprint(program, final)
    return {"kind": KIND + "_result", "program_sha256": spec["program_sha256"],
            "target": target, "budget_seconds": budget, "profiled_call_wall_seconds": wall,
            "profiled_tottime_total": grand,
            "reconciliation_ratio": grand / wall if wall > 0 else None,
            "category_seconds": seconds,
            "category_shares": {k: (v / grand if grand > 0 else None) for k, v in seconds.items()},
            "top_functions": top, "cycles": cycles, "scratch": scratch,
            "product": cycles * scratch,
            "nodes": record["aggregate"]["nodes"] if "aggregate" in record else None,
            "validations": (record["aggregate"]["validations"] if "aggregate" in record
                            else None),
            "discrepancy_count": record["discrepancy_count"],
            "correctness": "PASS" if record["discrepancy_count"] == 0 else "FAIL"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    args = parser.parse_args(argv)
    try:
        result = profile(json.loads(args.spec))
    except Exception as exc:  # retained by the harness as a failed row
        print(f"profile failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(se.canonical_json(result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
