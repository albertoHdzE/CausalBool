"""The NEW structural controller of optimization protocol 1.0.

This module owns exactly what the protocol authorises to be new: the query cap,
the ``matched``/``wider`` domain policies, the aggregate work ceilings, the
corrected query-expiry continuation and the ``cached`` engineering build. It
owns no codec, no search, no bound, no window order and no domain record:

- targets come from ``direct_optimizer.targets_for`` and the four-operation
  windows from ``direct_optimizer.windows_for`` (production owners);
- the physical domain of a window comes from
  ``run_structural_experiments.matched_window_record`` (research owner), now
  parameterised by its time slack with the accepted default preserved;
- the traversal and its admissible bound are ``structural_search.search``;
- covers and one-coordinate expansion are ``structural_models``.

The frozen control is **not** this module. It is the accepted
``final_source_v2`` snapshot, imported first on ``sys.path`` by
``optimization_frozen_worker``; nothing here is ever measured under its name.

Corrections relative to the frozen controller, for NEW arms only:

1. A query whose own allowance ``min(0.1 s, remaining)`` expires during domain
   construction is recorded as ``QUERY_EXPIRED`` and the fixed traversal
   advances. Only the overall deadline, the query cap or an aggregate ceiling
   stops the pass. The frozen controller stopped the whole pass there.
2. Aggregate ceilings of 1,000,000 charged search nodes and 100,000 candidate
   validations per optimisation call, counted over every query.
"""

from __future__ import annotations

import time
from typing import Callable, Dict, Iterator, List, Optional, Sequence, Tuple

import machine

import direct_constraints as dk
import direct_contract as dc
import direct_optimizer as dopt
import schema_index as si

from research import run_structural_experiments as rse
from research import structural_encoding as se
from research import structural_models as sm
from research import structural_search as ss


__all__ = [
    "QUERY_CAPS", "DOMAIN_POLICIES", "CONFIGS", "BUILDS", "NODE_CEILING",
    "VALIDATION_CEILING", "config_id", "parse_config", "windows_of_size", "query_plan",
    "optimise", "model_proposals",
]


QUERY_CAPS: Tuple[Optional[int], ...] = (32, 128, 512, None)
DOMAIN_POLICIES = ("matched", "wider")
WIDER_WINDOW = 8
MATCHED_SLACK = dk.TIME_SLACK
WIDER_SLACK = 4
NODE_CEILING = 1_000_000
VALIDATION_CEILING = 100_000
BUILDS = ("reference", "cached")
QUERY_SECONDS = 0.1

# The existing per-query safety limits of the accepted research protocol.
PER_QUERY_LIMITS = {
    "query_max_cover": 4096,
    "search_max_nodes": 1_000_000,
    "search_max_candidate_validations": 100_000,
    "query_max_visited": 50_000,
    "cover_max_cubes": 65_536,
    "cover_seconds_per_set": 10,
}


def config_id(cap: Optional[int], policy: str) -> str:
    return f"cap{'null' if cap is None else cap}_{policy}"


def parse_config(identifier: str) -> Tuple[Optional[int], str]:
    head, policy = identifier.split("_", 1)
    cap_text = head[len("cap"):]
    cap = None if cap_text == "null" else int(cap_text)
    if cap not in QUERY_CAPS or policy not in DOMAIN_POLICIES:
        raise ValueError(f"not an authorised configuration: {identifier!r}")
    return cap, policy


CONFIGS = tuple(config_id(cap, policy) for cap in QUERY_CAPS for policy in DOMAIN_POLICIES)


def windows_of_size(
    facts: dc.ProgramFacts,
    times: Dict[int, int],
    addresses: Dict[str, int],
    scratch_first: bool,
    size: int,
) -> List[Tuple[int, ...]]:
    """``direct_optimizer.windows_for`` with the window size as a parameter.

    The production owner hard-codes ``WINDOW_SIZE = 4`` and may not be edited.
    This is the same ordering rule -- latest issue, highest footprint, then
    source-contiguous windows with starts advancing by two -- at another size.
    ``research_tests/test_phase2_optimization.py`` asserts equality with the
    owner at size 4 on every development program, so the two cannot drift.
    """

    latest = sorted(range(facts.count), key=lambda op_id: (-times[op_id], op_id))
    time_window = tuple(sorted(latest[:size]))
    highest = sorted(
        facts.value_names,
        key=lambda name: (-(addresses[name] + facts.width[name]), facts.producers[name]),
    )
    scratch_window = tuple(sorted({facts.producers[name] for name in highest[:size]}))
    source: List[Tuple[int, ...]] = []
    for start in range(0, facts.count, 2):
        candidate = tuple(range(start, min(start + size, facts.count)))
        if candidate:
            source.append(candidate)
    ordered: List[Tuple[int, ...]] = []
    leading = [scratch_window, time_window] if scratch_first else [time_window, scratch_window]
    for window in leading + source:
        if window and window not in ordered:
            ordered.append(window)
    return ordered


def query_plan(
    facts: dc.ProgramFacts,
    times: Dict[int, int],
    addresses: Dict[str, int],
    scratch_first: bool,
    policy: str,
) -> List[Tuple[Tuple[int, ...], int]]:
    """``(window, time_slack)`` pairs for one target, in traversal order.

    ``matched`` is exactly the accepted four-operation window list at slack 2.
    ``wider`` runs that list first, then appends the eight-operation windows
    that are not identical to an original tuple, each at slack 4.
    """

    if policy not in DOMAIN_POLICIES:
        raise ValueError(f"unknown domain policy {policy!r}")
    base = dopt.windows_for(facts, times, addresses, scratch_first=scratch_first)
    plan = [(tuple(window), MATCHED_SLACK) for window in base]
    if policy == "wider":
        seen = set(tuple(window) for window in base)
        for window in windows_of_size(facts, times, addresses, scratch_first, WIDER_WINDOW):
            if window in seen:
                continue
            seen.add(window)
            plan.append((window, WIDER_SLACK))
    return plan


# --------------------------------------------------------------------------
# Model proposals (depth 1 and depth 2)
# --------------------------------------------------------------------------


def model_proposals(
    depth: int,
    bits: int,
    cover: Sequence[si.Cube],
    excluded: set,
    budget_check: Optional[Callable[[], None]] = None,
    accounting: Optional[dict] = None,
) -> Iterator[Tuple[int, bool]]:
    """``(index, is_duplicate)`` from the depth-1 or depth-1-then-2 expansion.

    Depth 1 is ``structural_models.proposals("model_expand", ...)``. Depth 2
    first walks that same stream, then calls the same ``expand_cubes`` rule on
    the depth-1 cubes and walks the new cubes' ordered union, dropping cubes
    already emitted at depth 1 and every index that a depth-1 cube contains.
    The index suppression test is a membership check against the depth-1 cube
    list, so the accounting is bounded by the cube count and never by ``2**B``.
    """

    if depth not in (1, 2):
        raise ValueError("only depths 1 and 2 are authorised")
    accounting = accounting if accounting is not None else {}
    accounting.setdefault("suppressed_indices", 0)
    accounting.setdefault("suppressed_cubes", 0)
    first = sm.expand_cubes(cover, bits)
    accounting["depth1_cubes"] = len(first)
    for index in sm.ordered_union(first, budget_check):
        yield index, index in excluded
    if depth == 1:
        return
    first_keys = {(cube.anchor, cube.free_mask) for cube in first}
    second: List[si.Cube] = []
    for cube in sm.expand_cubes(first, bits):
        if (cube.anchor, cube.free_mask) in first_keys:
            accounting["suppressed_cubes"] += 1
            continue
        second.append(cube)
    accounting["depth2_cubes"] = len(second)
    for index in sm.ordered_union(second, budget_check):
        if any(cube.contains(index) for cube in first):
            accounting["suppressed_indices"] += 1
            if budget_check is not None:
                budget_check()
            continue
        yield index, index in excluded


# --------------------------------------------------------------------------
# The controller
# --------------------------------------------------------------------------


class _Expired(Exception):
    pass


def _status_key(status: str) -> str:
    return {"SAT": "SAT", "UNSAT": "UNSAT", "UNKNOWN": "UNKNOWN_SEARCH", "FAIL": "FAIL"}[status]


def optimise(
    program: dict,
    facts: dc.ProgramFacts,
    times: Dict[int, int],
    addresses: Dict[str, int],
    *,
    config: str,
    budget_seconds: float,
    search_arm: str = "structural_bound",
    build: str = "reference",
    model_depth: Optional[int] = None,
    query_seconds: float = QUERY_SECONDS,
    node_ceiling: int = NODE_CEILING,
    validation_ceiling: int = VALIDATION_CEILING,
    limits: Optional[dict] = None,
    clock: Callable[[], float] = time.perf_counter,
    elite_fraction: float = 0.1,
) -> Tuple[Dict[int, int], Dict[str, int], dict]:
    """Improve the direct bootstrap incumbent under one NEW configuration.

    ``search_arm`` is ``structural_bound`` (selected policy) or
    ``structural_dfs`` (the bound ablation). ``model_depth`` enables the
    conditional model compiler arm with the ``_model_optimise`` split: the first
    half of each query allowance runs the ordinary structural search and the
    second half walks the expansion of an exact cover of its elite observations.
    """

    if search_arm not in ("structural_bound", "structural_dfs"):
        raise ValueError(f"unknown search arm {search_arm!r}")
    if build not in BUILDS:
        raise ValueError(f"unknown build {build!r}")
    cap, policy = parse_config(config)
    limits = dict(PER_QUERY_LIMITS if limits is None else limits)
    memo: Optional[dict] = {} if build == "cached" else None

    started = clock()
    deadline = started + budget_seconds
    statuses = {"SAT": 0, "UNSAT": 0, "UNKNOWN_SEARCH": 0, "UNKNOWN_CONSTRUCTION": 0,
                "QUERY_EXPIRED": 0, "INFEASIBLE": 0, "FAIL": 0}
    queries: List[dict] = []
    improvements: List[dict] = []
    rejected: List[dict] = []
    interrupted: List[dict] = []
    attempted: set = set()
    totals = {"nodes": 0, "validations": 0, "case_checks": 0, "pruned": 0, "completions": 0,
              "model_proposals": 0, "model_validations": 0, "model_unavailable": 0,
              "model_accepted": 0, "search_accepted": 0}
    stopped = "pass_complete"
    best_times, best_addresses = dict(times), dict(addresses)

    def meter_budget(remaining: float) -> Optional[si.Budget]:
        nodes_left = node_ceiling - totals["nodes"]
        validations_left = validation_ceiling - totals["validations"]
        if nodes_left < 2 or validations_left < 1:
            return None
        # Charged nodes include the one that trips the meter, so the meter is
        # given one fewer than what is left and the aggregate never exceeds the
        # ceiling. Validations are counted only once paid for.
        return si.Budget(
            seconds=max(remaining, 1e-9),
            max_cover=limits["query_max_cover"],
            max_visited=min(limits["search_max_nodes"], nodes_left - 1),
            max_records=min(limits["search_max_candidate_validations"], validations_left),
        )

    def aggregate_exhausted() -> Optional[str]:
        if node_ceiling - totals["nodes"] < 2:
            return "aggregate_nodes"
        if validation_ceiling - totals["validations"] < 1:
            return "aggregate_validations"
        return None

    improved = True
    while improved:
        improved = False
        cycles = max(best_times.values()) + 1
        memory = dc.footprint(facts, best_addresses)
        product = cycles * memory
        digest = se.object_digest({"t": {str(k): v for k, v in sorted(best_times.items())},
                                   "a": dict(sorted(best_addresses.items()))})
        for target_cycles, target_memory in dopt.targets_for(facts, cycles, memory):
            plan = query_plan(facts, best_times, best_addresses,
                              scratch_first=target_memory < memory, policy=policy)
            for window, slack in plan:
                if cap is not None and len(attempted) >= cap:
                    stopped = "query_cap"
                    break
                if clock() >= deadline:
                    stopped = "deadline"
                    break
                exhausted = aggregate_exhausted()
                if exhausted:
                    stopped = exhausted
                    break
                key = (digest, window, target_cycles, target_memory, slack)
                if key in attempted:
                    continue
                attempted.add(key)
                # The query allowance is fixed before construction and never renewed.
                query_started = clock()
                allowance = min(query_seconds, deadline - query_started)
                if allowance <= 0:
                    stopped = "deadline"
                    interrupted.append({"phase": "before_construction", "window": list(window)})
                    break
                query_deadline = query_started + allowance
                search_deadline = (query_started + allowance / 2) if model_depth else query_deadline
                entry = {"window": list(window), "slack": slack,
                         "target": [target_cycles, target_memory], "allowance_seconds": allowance}
                try:
                    record = rse.matched_window_record(
                        f"{program['name']}::{'-'.join(map(str, window))}"
                        f"::{target_cycles}x{target_memory}::s{slack}",
                        policy, program, facts, best_times, best_addresses,
                        window, target_cycles, target_memory, time_slack=slack,
                    )
                    domain = se.Domain.from_record(record, memo=memo)
                except dk.Infeasible as exc:
                    statuses["INFEASIBLE"] += 1
                    entry.update(status="INFEASIBLE", reason=str(exc))
                    queries.append(entry)
                    continue
                except se.DomainError as exc:
                    statuses["UNKNOWN_CONSTRUCTION"] += 1
                    entry.update(status="UNKNOWN_CONSTRUCTION", reason=str(exc))
                    queries.append(entry)
                    continue
                entry["domain_sha256"] = domain.digest()
                entry["bits"] = se.layout(domain, "structural_rank").width
                remaining = search_deadline - clock()
                entry["remaining_after_construction_seconds"] = remaining
                if remaining <= 0:
                    interrupted.append({"phase": "after_construction", "window": list(window),
                                        "domain_sha256": entry["domain_sha256"]})
                    if clock() >= deadline:
                        statuses["UNKNOWN_CONSTRUCTION"] += 1
                        entry.update(status="UNKNOWN_CONSTRUCTION",
                                     reason="the overall deadline expired during construction")
                        queries.append(entry)
                        stopped = "deadline"
                        break
                    # Correction 1: the query allowance, not the overall budget,
                    # ran out. Record it and advance the fixed traversal.
                    statuses["QUERY_EXPIRED"] += 1
                    entry.update(status="QUERY_EXPIRED",
                                 reason="the query allowance expired during construction")
                    queries.append(entry)
                    continue
                budget = meter_budget(remaining)
                if budget is None:
                    stopped = aggregate_exhausted() or "aggregate_nodes"
                    queries.append(dict(entry, status="NOT_RUN", reason=stopped))
                    break
                observations: List[dict] = []
                report = ss.search(domain, record["incumbent"], search_arm, budget,
                                   deadline=search_deadline,
                                   observe=observations.append if model_depth else None)
                totals["nodes"] += report.nodes
                totals["validations"] += report.validations
                totals["case_checks"] += report.case_checks
                totals["pruned"] += report.pruned
                totals["completions"] += report.completions
                entry.update(status=report.status, reason=report.reason, nodes=report.nodes,
                             validations=report.validations, pruned=report.pruned,
                             completions=report.completions)
                statuses[_status_key(report.status)] += 1
                rejected.extend(report.rejected_completions)
                if report.interrupted_validations:
                    interrupted.append({"phase": "validation", "window": list(window),
                                        "count": report.interrupted_validations})
                ceiling_hit = (report.status == "UNKNOWN" and "budget exhausted" in report.reason
                               and "time" not in report.reason)
                best_here = product
                pair = None
                source = None
                if report.improved and report.best_product is not None \
                        and report.best_product < product:
                    best_here = report.best_product
                    pair = (report.best_times, report.best_addresses)
                    source = "search"
                if model_depth and not ceiling_hit:
                    model_pair, model_product, model_entry = _model_half(
                        domain, observations, best_here, model_depth, query_deadline,
                        limits, totals, validation_ceiling, rejected, interrupted, clock,
                        elite_fraction, window,
                    )
                    entry["model"] = model_entry
                    if model_pair is not None:
                        pair, best_here, source = model_pair, model_product, "model"
                queries.append(entry)
                if ceiling_hit and aggregate_exhausted():
                    # The meter was capped at what the aggregate had left, so a
                    # tripped meter with nothing left is the aggregate ceiling.
                    stopped = aggregate_exhausted()
                if pair is not None:
                    best_times, best_addresses = dict(pair[0]), dict(pair[1])
                    totals[f"{source}_accepted"] += 1
                    improvements.append({"window": list(window), "slack": slack,
                                         "target": [target_cycles, target_memory],
                                         "from": product, "to": best_here, "source": source})
                    improved = True
                    break
                if stopped != "pass_complete":
                    break
            if improved or stopped != "pass_complete":
                break
        if stopped != "pass_complete":
            break

    elapsed = clock() - started
    record = {
        "controller": "optimization_search.optimise",
        "config": config,
        "query_cap": cap,
        "domain_policy": policy,
        "search_arm": search_arm,
        "build": build,
        "model_depth": model_depth,
        "budget_seconds": budget_seconds,
        "query_seconds": query_seconds,
        "attempted_queries": len(attempted),
        "recorded_queries": len(queries),
        "statuses": statuses,
        "accepted": len(improvements),
        "improvements": improvements,
        "rejected_completions": rejected,
        "discrepancy_count": len(rejected),
        "stopped_because": stopped,
        "limiting_resource": stopped,
        "seconds": elapsed,
        "overshoot_seconds": elapsed - budget_seconds,
        "interrupted_attempts": interrupted,
        "interrupted_attempt_count": len(interrupted),
        "aggregate": dict(totals),
        "ceilings": {"nodes": node_ceiling, "validations": validation_ceiling},
        "budget_renewals": 0,
        "queries": queries,
    }
    return best_times, best_addresses, record


def _model_half(domain, observations, best_product, depth, query_deadline, limits, totals,
                validation_ceiling, rejected, interrupted, clock, elite_fraction, window):
    """The second half of one query: cover the elite and walk its expansion.

    Returns ``(pair or None, product, entry)``. A query with no complete
    observation, or whose cover cannot be completed, retains the incumbent and
    runs no substitute search.
    """

    codec = "structural_rank"
    bits = se.layout(domain, codec).width
    if not observations:
        totals["model_unavailable"] += 1
        return None, best_product, {"status": "NOT_APPLICABLE",
                                    "reason": "no complete observation in the search half"}
    products = [item["product"] for item in observations]
    threshold = rse._elite_threshold(products, elite_fraction)
    elite = [item for item in observations if item["product"] <= threshold]
    if clock() >= query_deadline:
        totals["model_unavailable"] += 1
        interrupted.append({"phase": "before_model_construction", "window": list(window)})
        return None, best_product, {"status": "NOT_APPLICABLE", "threshold": threshold,
                                    "reason": "the query allowance expired before the model"}
    indices: List[int] = []
    for item in elite:
        if clock() >= query_deadline:
            totals["model_unavailable"] += 1
            interrupted.append({"phase": "model_encoding", "window": list(window)})
            return None, best_product, {"status": "NOT_APPLICABLE",
                                        "reason": "elite encoding interrupted"}
        try:
            indices.append(se.encode(domain, item["compilation"], codec))
        except se.DomainError:
            continue
    indices = sorted(set(indices))
    cover_seconds = min(limits["cover_seconds_per_set"], query_deadline - clock())
    if not indices or cover_seconds <= 0:
        totals["model_unavailable"] += 1
        return None, best_product, {"status": "NOT_APPLICABLE", "elite": len(indices),
                                    "reason": "no encodable elite or no time for the cover"}
    cover = sm.exact_cover(indices, bits, limits["cover_max_cubes"], cover_seconds)
    entry = {"threshold": threshold, "elite": len(indices), "cover_status": cover.status,
             "cover_cubes": len(cover.cubes), "depth": depth}
    if cover.status != "COMPLETE":
        entry.update(status="INCONCLUSIVE", reason=f"the elite cover is {cover.status}")
        return None, best_product, entry

    def check() -> None:
        if clock() >= query_deadline:
            raise _Expired

    evaluated = set(indices)
    accounting: dict = {}
    counts = {"attempted": 0, "duplicate": 0, "invalid_code": 0, "dead_end": 0,
              "interrupted": 0, "complete": 0, "validations": 0, "exhausted": False,
              "cap_reached": None}
    best_pair = None
    stream = model_proposals(depth, bits, cover.cubes, evaluated, check, accounting)
    try:
        while True:
            check()
            if counts["attempted"] >= limits["query_max_visited"]:
                counts["cap_reached"] = "query_max_visited"
                break
            try:
                index, duplicate = next(stream)
            except StopIteration:
                counts["exhausted"] = True
                break
            counts["attempted"] += 1
            totals["model_proposals"] += 1
            if duplicate or index in evaluated:
                counts["duplicate"] += 1
                continue
            evaluated.add(index)
            result = se.decode(domain, index, codec)
            if result.status != se.COMPLETE:
                counts[{se.INVALID_CODE: "invalid_code", se.DEAD_END: "dead_end",
                        se.INTERRUPTED: "interrupted"}[result.status]] += 1
                continue
            counts["complete"] += 1
            if result.product is None or result.product >= best_product:
                continue
            check()
            if totals["validations"] >= validation_ceiling:
                counts["cap_reached"] = "aggregate_validations"
                break
            counts["validations"] += 1
            totals["validations"] += 1
            totals["model_validations"] += 1
            try:
                machine.check_compilation(domain.program, result.compilation)
                for case in domain.program["cases"]:
                    machine.check_case(domain.program, result.compilation, case)
                    totals["case_checks"] += 1
            except (machine.CompileError, machine.ProgramError) as exc:
                rejected.append({"identity": result.identity, "index": str(index),
                                 "error": str(exc), "source": f"model_depth{depth}"})
                continue
            if clock() >= query_deadline:
                interrupted.append({"phase": "model_validation", "window": list(window)})
                break
            best_product = result.product
            best_pair = (dict(result.times), dict(result.addresses))
    except _Expired:
        interrupted.append({"phase": "model_proposals", "window": list(window)})
    entry.update(status="PASS", counts=counts, accounting=accounting)
    return best_pair, best_product, entry
