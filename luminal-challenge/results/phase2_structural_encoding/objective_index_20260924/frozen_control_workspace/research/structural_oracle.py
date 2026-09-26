"""An independent finite-domain enumerator, and the hidden evaluator of P4.

This module is deliberately isolated. It imports **only the pinned ``machine``
module and the standard library**. It does not import the codec, the search, the
model, or ``direct_contract``'s derived legality checker, because its whole
purpose is to decide membership of ``F_d`` by a path that shares no feasibility
predicate with the candidate (plan section 8, P1: "Do not call candidate
transition logic from the oracle").

It therefore assembles its own ``{"scratch": ..., "bundles": ...}`` dictionaries
from the raw program and asks ``machine.check_compilation``, ``machine.check_case``
and ``machine.scratch_footprint`` whether they are legal. Everything it knows
about latency, capacity, alignment and lifetimes it learns by being told "no".

``research/check_structural_evidence.py`` enforces this import boundary at run
time, and a planted import in a temporary copy must make that guard fail.
"""

from __future__ import annotations

import itertools
import json
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

import machine


__all__ = [
    "OracleError",
    "OracleExhausted",
    "enumerate_feasible",
    "assignments",
    "build_compilation",
    "accepts",
    "hidden_evaluation",
]


class OracleError(ValueError):
    """The oracle was handed something it cannot enumerate."""


class OracleExhausted(Exception):
    """The declared Cartesian product exceeded the permitted bound."""


def _result_kinds(program: dict) -> Dict[str, str]:
    return machine.result_kinds(program)


def _engine_of(program: dict, op_id: int) -> str:
    return machine.OP_SPECS[program["operations"][op_id]["op"]]["engine"]


def assignments(record: dict, maximum: int) -> Iterator[Tuple[Dict[int, int], Dict[str, int]]]:
    """Every point of the declared Cartesian product, in a fixed order.

    The count is the product of the declared domain sizes *before* any legality
    filtering, which is exactly what ``cartesian_assignments`` records.
    """

    time_keys = sorted(int(key) for key in record["time_domains"])
    address_keys = sorted(record["address_domains"])
    time_lists = [sorted(record["time_domains"][str(key)]) for key in time_keys]
    address_lists = [sorted(record["address_domains"][name]) for name in address_keys]

    total = 1
    for values in time_lists + address_lists:
        if not values:
            raise OracleError("a declared domain was empty")
        total *= len(values)
    if total > maximum:
        raise OracleExhausted(
            f"declared Cartesian product of {total} exceeds the bound {maximum}"
        )

    fixed_times = {int(key): value for key, value in record["fixed_times"].items()}
    fixed_addresses = dict(record["fixed_addresses"])

    for combination in itertools.product(*(time_lists + address_lists)):
        times = dict(fixed_times)
        addresses = dict(fixed_addresses)
        for position, key in enumerate(time_keys):
            times[key] = combination[position]
        for position, name in enumerate(address_keys):
            addresses[name] = combination[len(time_keys) + position]
        yield times, addresses


def build_compilation(program: dict, times: Dict[int, int], addresses: Dict[str, int]) -> dict:
    """A candidate dictionary assembled from first principles.

    Operations are listed in increasing identifier within each engine and
    trailing empty bundles are omitted, which is the normal form of plan
    section 3. No derived-facts module takes part.
    """

    span = max(times.values()) + 1
    bundles: List[Dict[str, List[int]]] = [{} for _ in range(span)]
    for op_id in sorted(times):
        engine = _engine_of(program, op_id)
        bundles[times[op_id]].setdefault(engine, []).append(op_id)
    while bundles and not bundles[-1]:
        bundles.pop()
    return {"scratch": dict(addresses), "bundles": bundles}


def accepts(program: dict, compilation: dict, check_cases: bool = True):
    """``(cycles, scratch, cases)`` when the pinned validator accepts, else ``None``."""

    try:
        cycles = machine.check_compilation(program, compilation)
        cases = 0
        if check_cases:
            for case in program["cases"]:
                machine.check_case(program, compilation, case)
                cases += 1
        scratch = machine.scratch_footprint(program, compilation)
    except (machine.CompileError, machine.ProgramError, ValueError, KeyError, IndexError):
        return None
    return cycles, scratch, cases


def enumerate_feasible(
    record: dict,
    maximum: int,
    check_cases: bool = True,
) -> dict:
    """Enumerate ``F_d`` independently of the candidate codec.

    Returns the accepted objects with their objectives and the exact
    denominators: attempted points, rejected points and the declared Cartesian
    size. A target, when declared, is applied as a separate predicate *after*
    legality, so a target miss never hides an illegal object.
    """

    program = record["program"]
    machine.validate_program(program)
    target = record.get("target")

    feasible: List[dict] = []
    attempted = 0
    rejected = 0
    target_missed = 0
    for times, addresses in assignments(record, maximum):
        attempted += 1
        compilation = build_compilation(program, times, addresses)
        verdict = accepts(program, compilation, check_cases=check_cases)
        if verdict is None:
            rejected += 1
            continue
        cycles, scratch, cases = verdict
        if target is not None and (cycles > target[0] or scratch > target[1]):
            target_missed += 1
            continue
        identity = json.dumps(
            {
                "bundles": [
                    {engine: sorted(ids) for engine, ids in sorted(bundle.items()) if ids}
                    for bundle in compilation["bundles"]
                ],
                "scratch": {name: addresses[name] for name in sorted(addresses)},
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        feasible.append(
            {
                "identity": identity,
                "times": {str(key): value for key, value in sorted(times.items())},
                "addresses": {name: addresses[name] for name in sorted(addresses)},
                "cycles": cycles,
                "scratch": scratch,
                "product": cycles * scratch,
                "cases": cases,
            }
        )

    feasible.sort(key=lambda entry: entry["identity"])
    identities = [entry["identity"] for entry in feasible]
    if len(set(identities)) != len(identities):
        raise OracleError("the enumeration produced two objects with one identity")
    return {
        "domain_id": record["id"],
        "cartesian_assignments": attempted,
        "declared_cartesian": record.get("cartesian_assignments"),
        "rejected": rejected,
        "target_missed": target_missed,
        "feasible_count": len(feasible),
        "feasible": feasible,
        "cases_checked": check_cases,
    }


def hidden_evaluation(enumeration: dict) -> Dict[str, int]:
    """The hidden objective of every feasible object, keyed by identity.

    The evaluator may see this; the learner may not. The learner only ever
    receives the labels of its training split and the results of queries it has
    paid for, which the runner enforces by never handing this mapping to a
    proposal arm.
    """

    return {entry["identity"]: entry["product"] for entry in enumeration["feasible"]}
