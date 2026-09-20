"""Bounded joint improvement over the direct compiler's own incumbent.

Task L05 of ``plan/INDEX_ONLY_PLAN.md``, sections 5.4 and 5.5.

For an incumbent of ``C`` bundles and footprint ``S`` the objective is to
minimise ``P = C * S``. For a fixed program that is exactly equivalent to
maximising the program's contribution to the official combined score, because
that contribution is a constant minus ``log(C * S)`` divided by twice the
number of programs.

Nothing here weakens a result. A satisfying witness is decoded, independently
validated, and measured again; only a strict product improvement is accepted.
``UNKNOWN`` leaves the incumbent exactly as it was, and a witness that fails
validation is recorded as a discrepancy that blocks release rather than being
quietly discarded.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Sequence, Tuple

import machine

import direct_constraints as dk
import direct_contract as dc
import schema_index as si


__all__ = ["optimise", "targets_for", "windows_for", "WINDOW_SIZE"]


WINDOW_SIZE = 4

# Headroom kept back from the total budget for validation, serialisation and
# process overhead, as section 5.5 requires. The external 20 second timeout
# remains the acceptance authority.
_RESERVE_SECONDS = 1.0


def _digest(times: Dict[int, int], addresses: Dict[str, int]) -> str:
    payload = repr((sorted(times.items()), sorted(addresses.items()))).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def targets_for(facts: dc.ProgramFacts, cycles: int, memory: int) -> List[Tuple[int, int]]:
    """The target pairs of section 5.4, in their declared order."""

    product = cycles * memory
    cycle_floor = facts.cycle_lower_bound()
    memory_floor = facts.memory_lower_bound()

    candidates: List[Tuple[int, int]] = [(cycles - 1, memory), (cycles, memory - 1)]
    candidates.append((cycles + 1, (product - 1) // (cycles + 1)))
    if cycles - 1 > 0:
        candidates.append(
            (cycles - 1, min(machine.SCRATCH_WORDS, (product - 1) // (cycles - 1)))
        )

    chosen: List[Tuple[int, int]] = []
    for target_cycles, target_memory in candidates:
        if target_cycles < 1 or target_memory < 1:
            continue
        if target_cycles < cycle_floor or target_memory < memory_floor:
            continue
        if target_cycles > facts.horizon:
            continue
        if target_memory > machine.SCRATCH_WORDS:
            continue
        if target_cycles * target_memory >= product:
            continue
        if (target_cycles, target_memory) in chosen:
            continue
        chosen.append((target_cycles, target_memory))
    return chosen


def windows_for(
    facts: dc.ProgramFacts,
    times: Dict[int, int],
    addresses: Dict[str, int],
    scratch_first: bool,
) -> List[Tuple[int, ...]]:
    """The candidate windows of section 5.4, deduplicated in order."""

    latest = sorted(range(facts.count), key=lambda op_id: (-times[op_id], op_id))
    time_window = tuple(sorted(latest[:WINDOW_SIZE]))

    highest = sorted(
        facts.value_names,
        key=lambda name: (-(addresses[name] + facts.width[name]), facts.producers[name]),
    )
    scratch_window = tuple(
        sorted({facts.producers[name] for name in highest[:WINDOW_SIZE]})
    )

    # Starts advance by two and each window is truncated at the operation
    # count, which keeps the final nonempty shorter window. Breaking out as
    # soon as a full window reached the end would drop that tail: for six
    # operations it would omit (4, 5).
    source: List[Tuple[int, ...]] = []
    for start in range(0, facts.count, 2):
        candidate = tuple(range(start, min(start + WINDOW_SIZE, facts.count)))
        if candidate:
            source.append(candidate)

    ordered: List[Tuple[int, ...]] = []
    leading = [scratch_window, time_window] if scratch_first else [time_window, scratch_window]
    for window in leading + source:
        if window and window not in ordered:
            ordered.append(window)
    return ordered


def optimise(
    program: dict,
    facts: dc.ProgramFacts,
    times: Dict[int, int],
    addresses: Dict[str, int],
    limits,
    deadline,
    counters,
) -> Tuple[Dict[int, int], Dict[str, int], dict]:
    """Improve the incumbent through bounded joint queries.

    Returns the best validated schedule and allocation together with a record
    of what was attempted. The incumbent passed in has already been validated
    by the caller, so returning it unchanged is always safe.
    """

    statuses = {
        "SAT": 0,
        "UNSAT": 0,
        "UNKNOWN_CONSTRUCTION": 0,
        "UNKNOWN_SEARCH": 0,
        "INFEASIBLE": 0,
    }
    reasons: Dict[str, int] = {}
    improvements: List[dict] = []
    validation_errors: List[dict] = []
    target_discrepancies: List[dict] = []
    attempted: set = set()
    stopped = "pass_complete"
    started = deadline.elapsed

    allowance = min(
        limits.optimise_seconds, deadline.seconds - started - _RESERVE_SECONDS
    )
    horizon = started + allowance

    best_times = dict(times)
    best_addresses = dict(addresses)

    improved = True
    while improved:
        improved = False
        cycles = max(best_times.values()) + 1
        memory = dc.footprint(facts, best_addresses)
        product = cycles * memory
        digest = _digest(best_times, best_addresses)

        for target_cycles, target_memory in targets_for(facts, cycles, memory):
            windows = windows_for(
                facts, best_times, best_addresses, scratch_first=target_memory < memory
            )
            for window in windows:
                if len(attempted) >= limits.max_queries:
                    stopped = "query_cap"
                    break
                if deadline.elapsed >= horizon:
                    stopped = "deadline"
                    break
                key = (digest, window, target_cycles, target_memory)
                if key in attempted:
                    continue
                # An attempted query is one whose construction has started.
                attempted.add(key)

                remaining = min(limits.query_seconds, horizon - deadline.elapsed)
                if remaining <= 0:
                    stopped = "deadline"
                    break
                meter = si.Budget(
                    seconds=remaining,
                    max_cover=limits.max_cover,
                    max_visited=limits.max_visited,
                    max_records=limits.max_records,
                ).start()

                try:
                    query = dk.JointQuery(
                        facts,
                        best_times,
                        best_addresses,
                        window,
                        target_cycles,
                        target_memory,
                        meter,
                    )
                    expression = query.expression()
                except dk.Infeasible:
                    statuses["INFEASIBLE"] += 1
                    continue
                except si.BudgetExhausted as exc:
                    # The expression could not even be built within budget.
                    statuses["UNKNOWN_CONSTRUCTION"] += 1
                    reasons[exc.reason] = reasons.get(exc.reason, 0) + 1
                    continue

                result = si.solve(expression, query.n, meter=meter)
                counters.absorb(meter, 0)
                if result.is_unknown:
                    # Budget exhaustion is not a statement about solutions.
                    statuses["UNKNOWN_SEARCH"] += 1
                    continue
                if result.is_unsat:
                    # Only this neighbourhood is excluded, nothing wider.
                    statuses["UNSAT"] += 1
                    continue

                statuses["SAT"] += 1
                try:
                    candidate_times, candidate_addresses = query.decode(result.cube)
                    dc.check_feasible(facts, candidate_times, candidate_addresses)
                    compiled = dc.compilation(facts, candidate_times, candidate_addresses)
                    machine.check_compilation(program, compiled)
                except (ValueError, dc.ContractError, machine.CompileError) as exc:
                    # The query said this witness meets the criteria and the
                    # validator disagrees. That is a defect: record it, keep
                    # the incumbent, and let the release verifier fail.
                    validation_errors.append(
                        {
                            "window": list(window),
                            "target": [target_cycles, target_memory],
                            "error": str(exc),
                        }
                    )
                    continue

                actual_cycles = len(compiled["bundles"])
                actual_memory = dc.footprint(facts, candidate_addresses)
                actual_product = actual_cycles * actual_memory

                # The acceptance expression encodes both target bounds, so a
                # satisfying witness that misses either one is a disagreement
                # between the query and the measurement, not an ordinary
                # unsuccessful optimisation. Record it; the release gate fails
                # on it. Measuring first and rejecting on product alone would
                # hide the defect, because every generated target already
                # requires a strict product improvement.
                if actual_cycles > target_cycles or actual_memory > target_memory:
                    target_discrepancies.append(
                        {
                            "window": list(window),
                            "target": [target_cycles, target_memory],
                            "actual_cycles": actual_cycles,
                            "actual_memory": actual_memory,
                            "reason": (
                                f"witness satisfied the query but measured "
                                f"({actual_cycles}, {actual_memory}) against target "
                                f"({target_cycles}, {target_memory})"
                            ),
                        }
                    )
                    continue

                if actual_product >= product:
                    # Within target, but not a strict improvement of the
                    # measured product. Nothing is accepted, and this is not a
                    # discrepancy.
                    continue

                improvements.append(
                    {
                        "window": list(window),
                        "target": [target_cycles, target_memory],
                        "from": {"cycles": cycles, "footprint": memory, "product": product},
                        "to": {
                            "cycles": actual_cycles,
                            "footprint": actual_memory,
                            "product": actual_product,
                        },
                    }
                )
                best_times = candidate_times
                best_addresses = candidate_addresses
                improved = True
                break
            if improved or stopped != "pass_complete":
                break
        if stopped != "pass_complete":
            break

    record = {
        "enabled": True,
        "attempted_queries": len(attempted),
        "statuses": statuses,
        "unknown_reasons": reasons,
        "accepted": len(improvements),
        "improvements": improvements,
        "validation_errors": validation_errors,
        "target_discrepancies": target_discrepancies,
        "discrepancy_count": len(validation_errors) + len(target_discrepancies),
        "stopped_because": stopped,
        "seconds": deadline.elapsed - started,
        "allowance_seconds": allowance,
    }
    return best_times, best_addresses, record
