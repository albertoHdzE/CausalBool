"""Depth-first search over structural decision coordinates, with proved bounds.

This module owns the traversal, the admissible bounds and the acceptance policy
of the research arms. It owns no codec: option lists come from
``structural_encoding.options``, so the pruned and unpruned arms cannot drift
apart in what they consider locally legal. Contract section 5: "Identical local
feasibility checks apply to unpruned and pruned arms."

The reference traversal is depth-first in decision order with ascending option
ranks, no restarts, no beam, no learned bound and no adaptive window. The
incumbent used for rank ordering is fixed for the whole query, so accepting a
better solution never reinterprets an index that has already been constructed.

Verdict scoping follows plan section 6. Exhausting the declared finite domain,
with pruning only by bounds proved admissible, is ``UNSAT`` for the existence of
a strict improvement *within that domain*. A budget stopping the traversal is
``UNKNOWN`` and is never reported as ``UNSAT``.
"""

from __future__ import annotations

from dataclasses import dataclass, field as _dataclass_field
from typing import Dict, List, Optional, Sequence, Tuple

import machine

import direct_contract as dc
import schema_index as si

from research import structural_encoding as se


__all__ = [
    "ARMS",
    "SearchReport",
    "search",
    "cycle_bound",
    "scratch_bound",
    "peak_live_width",
]


# ``structural_expanded`` is the bounded search run on an explicitly enlarged
# domain. It is the same algorithm as ``structural_bound``; only the declared
# domain differs, and the runner is what builds that domain. Keeping it a named
# arm here would invite the reader to attribute its results to a better search.
ARMS = ("structural_dfs", "structural_bound", "structural_expanded")

_PRUNING_ARMS = ("structural_bound", "structural_expanded")


def cycle_bound(facts: dc.ProgramFacts, times: Dict[int, int]) -> int:
    """``L_C``: a lower bound on ``C`` over every completion of this prefix.

    ``facts.cycle_lower_bound()`` is the dependency/engine bound on the whole
    program. Any operation already assigned or fixed at cycle ``t`` forces at
    least ``t + 1`` emitted bundles, and no completion can remove it. The
    maximum term is omitted when nothing is placed, as the contract requires.
    """

    bound = facts.cycle_lower_bound()
    if times:
        bound = max(bound, 1 + max(times.values()))
    return bound


def scratch_bound(
    facts: dc.ProgramFacts,
    addresses: Dict[str, int],
    live_width: Optional[int] = None,
) -> int:
    """``L_S``: a lower bound on ``S`` over every completion of this prefix.

    The widest single result must fit, and any block already placed ending at
    ``a + w`` forces a footprint of at least that. Once the schedule is complete
    the peak simultaneous live width is also a bound, because values live at the
    same cycle need disjoint blocks. It is a bound, not an achievable value:
    vector alignment can make it unreachable, which is why it is only ever used
    to prune and never reported as a footprint.
    """

    bound = facts.memory_lower_bound()
    for name, base in addresses.items():
        bound = max(bound, base + facts.width[name])
    if live_width is not None:
        bound = max(bound, live_width)
    return bound


def peak_live_width(facts: dc.ProgramFacts, live: Dict[str, Tuple[int, int]]) -> int:
    """The largest total width of values live in one cycle."""

    if not live:
        return 0
    last = max(end for _, end in live.values())
    first = min(start for start, _ in live.values())
    peak = 0
    for cycle in range(first, last + 1):
        total = 0
        for name, (start, end) in live.items():
            if start <= cycle <= end:
                total += facts.width[name]
        peak = max(peak, total)
    return peak


@dataclass
class SearchReport:
    """Everything one search consumed and everything it concluded."""

    arm: str
    domain_id: str
    domain_sha256: str
    status: str = "UNKNOWN"
    reason: str = ""
    incumbent_product: Optional[int] = None
    best_product: Optional[int] = None
    best_cycles: Optional[int] = None
    best_scratch: Optional[int] = None
    best_times: Optional[Dict[int, int]] = None
    best_addresses: Optional[Dict[str, int]] = None
    best_compilation: Optional[dict] = None
    best_identity: Optional[str] = None
    best_index: Optional[str] = None
    improved: bool = False
    nodes: int = 0
    pruned: int = 0
    completions: int = 0
    validations: int = 0
    case_checks: int = 0
    duplicate_lookups: int = 0
    duplicate_hits: int = 0
    option_constructions: int = 0
    options_considered: int = 0
    legality_checks: int = 0
    dead_ends: int = 0
    rejected_completions: List[dict] = _dataclass_field(default_factory=list)
    seconds: float = 0.0

    def to_row(self) -> dict:
        row = dict(self.__dict__)
        row["best_times"] = (
            None if self.best_times is None
            else {str(key): value for key, value in sorted(self.best_times.items())}
        )
        row["best_addresses"] = (
            None if self.best_addresses is None else dict(sorted(self.best_addresses.items()))
        )
        return row


class _Stop(Exception):
    """The traversal ran out of budget."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def search(
    domain: se.Domain,
    incumbent: Optional[dict],
    arm: str,
    budget: si.Budget,
) -> SearchReport:
    """Search ``F_d`` for a strict product improvement on ``incumbent``.

    ``incumbent`` is a compilation. Only a strictly smaller ``C*S`` is accepted;
    an equal product retains the earlier incumbent, so the search never churns
    between objects of the same quality. Every accepted candidate is validated
    by the pinned machine on every case first.
    """

    if arm not in ARMS:
        raise ValueError(f"unknown search arm {arm!r}")
    facts = domain.facts
    prune = arm in _PRUNING_ARMS

    report = SearchReport(arm=arm, domain_id=domain.identifier, domain_sha256=domain.digest())
    meter = budget.start()

    best_product: Optional[int] = None
    if incumbent is not None:
        normalised = se.normalise_compilation(facts, incumbent)
        times = se.issue_cycles_of(domain.program, normalised["bundles"])
        addresses = dict(normalised["scratch"])
        cycles, scratch, product = se.objective(facts, times, addresses)
        report.incumbent_product = product
        report.best_product = product
        report.best_cycles = cycles
        report.best_scratch = scratch
        report.best_times = times
        report.best_addresses = addresses
        report.best_compilation = normalised
        report.best_identity = se.object_digest(normalised)
        best_product = product

    state = se.State(domain)
    conflict = state.schedule_conflict()
    if conflict is not None:
        report.status = "UNSAT"
        report.reason = f"the fixed decisions contradict each other: {conflict}"
        report.seconds = meter.elapsed
        return report

    seen: Dict[str, int] = {}

    def charge_node() -> None:
        report.nodes += 1
        try:
            meter.visit()
        except si.BudgetExhausted as exc:
            raise _Stop(exc.reason) from exc

    def consider(candidate_state: se.State) -> None:
        """Validate a complete candidate and accept it only if it is better."""

        nonlocal best_product
        report.completions += 1
        cycles, scratch, product = se.objective(facts, candidate_state.times,
                                                candidate_state.addresses)
        if domain.target is not None and (
            cycles > domain.target[0] or scratch > domain.target[1]
        ):
            return

        compiled = dc.compilation(facts, candidate_state.times, candidate_state.addresses)
        normalised = se.normalise_compilation(facts, compiled)
        identity = se.object_digest(normalised)
        report.duplicate_lookups += 1
        if identity in seen:
            # A duplicate costs its lookup and is still counted. In a decision
            # tree traversal it should never happen; if it does, the traversal
            # is not injective and the count says so.
            report.duplicate_hits += 1
            return
        seen[identity] = product

        # Only a strict improvement is worth paying validation for, but the
        # candidate is counted as a completion either way, so the denominator
        # never shrinks.
        if best_product is not None and product >= best_product:
            return

        try:
            meter.record()
        except si.BudgetExhausted as exc:
            raise _Stop(exc.reason) from exc
        report.validations += 1
        try:
            machine.check_compilation(domain.program, normalised)
            for case in domain.program["cases"]:
                machine.check_case(domain.program, normalised, case)
                report.case_checks += 1
        except (machine.CompileError, machine.ProgramError) as exc:
            # A completed candidate the validator rejects is a defect, retained
            # and surfaced; it is never silently dropped.
            report.rejected_completions.append(
                {
                    "identity": identity,
                    "times": {str(k): v for k, v in sorted(candidate_state.times.items())},
                    "addresses": dict(sorted(candidate_state.addresses.items())),
                    "error": str(exc),
                }
            )
            return

        best_product = product
        report.best_product = product
        report.best_cycles = cycles
        report.best_scratch = scratch
        report.best_times = dict(candidate_state.times)
        report.best_addresses = dict(candidate_state.addresses)
        report.best_compilation = normalised
        report.best_identity = identity
        report.improved = True
        try:
            report.best_index = str(se.encode(domain, normalised, "structural_rank"))
        except se.DomainError:
            report.best_index = None

    def bound_prunes(current: se.State, live_width: Optional[int]) -> bool:
        if not prune or best_product is None:
            return False
        lower = cycle_bound(facts, current.times) * scratch_bound(
            facts, {name: current.addresses[name] for name in current.addresses}, live_width
        )
        if lower >= best_product:
            report.pruned += 1
            return True
        return False

    def descend_addresses(current: se.State, order: Sequence[str], position: int) -> None:
        charge_node()
        if position == len(order):
            consider(current)
            return
        name = order[position]
        legal = se.options(domain, current, ("address", name))
        if not legal:
            report.dead_ends += 1
            return
        live_width = peak_live_width(facts, current.lifetimes)
        for value in legal:
            nxt = current.copy()
            nxt.addresses[name] = value
            if bound_prunes(nxt, live_width):
                continue
            descend_addresses(nxt, order, position + 1)

    def descend_times(current: se.State, position: int) -> None:
        charge_node()
        if position == len(domain.selected_operations):
            current.recompute_lifetimes()
            if current.fixed_address_conflict() is not None:
                report.dead_ends += 1
                return
            order = current.allocation_order()
            if bound_prunes(current, peak_live_width(facts, current.lifetimes)):
                return
            descend_addresses(current, order, 0)
            return
        op_id = domain.selected_operations[position]
        legal = se.options(domain, current, ("time", op_id))
        if not legal:
            report.dead_ends += 1
            return
        for value in legal:
            nxt = current.copy()
            nxt.times[op_id] = value
            if bound_prunes(nxt, None):
                continue
            descend_times(nxt, position + 1)

    try:
        descend_times(state, 0)
    except _Stop as stop:
        report.status = "UNKNOWN"
        report.reason = stop.reason
    except RecursionError:
        report.status = "UNKNOWN"
        report.reason = "traversal depth exceeded the interpreter's recursion limit"
    else:
        # The declared finite domain was exhausted, pruned only by bounds that
        # are admissible over every completion. That excludes this domain and
        # nothing wider.
        report.status = "SAT" if report.improved else "UNSAT"
        report.reason = (
            "a strictly better validated compilation was found"
            if report.improved
            else "the declared domain holds no strict improvement"
        )

    report.option_constructions = state.counters["option_constructions"]
    report.options_considered = state.counters["options_considered"]
    report.legality_checks = state.counters["legality_checks"]
    report.seconds = meter.elapsed
    if report.rejected_completions:
        report.status = "FAIL"
        report.reason = "a completed candidate was rejected by the pinned validator"
    return report
