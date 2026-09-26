"""The proposal learner of the NEW H4 study (optimization protocol 1.0).

A learner receives a declared domain, the labelled training objects the harness
supplies, an arm and a budget. It pays for everything it does: encoding the
training objects, building the elite, the cover (for the arms that use one),
proposing, decoding and validating. It returns the validated objects it found
that beat the best training label. It never sees the oracle table, the split
map or any hidden threshold: this module imports neither
``research.structural_oracle`` nor ``research.optimization_fixtures``, and the
test suite asserts that statically.

Arms: ``empirical_cover``, ``model_depth1``, ``model_depth2``, ``one_bit`` and
``uniform_bits``. The selected model arm is whichever depth development froze.
"""

from __future__ import annotations

import math
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import machine

from research import optimization_search as osr
from research import structural_encoding as se
from research import structural_models as sm


ARMS = ("empirical_cover", "model_depth1", "model_depth2", "one_bit", "uniform_bits")
CODEC = "structural_rank"
MAX_CUBES = 65_536


class _Expired(Exception):
    pass


def elite_threshold(products: Sequence[int], fraction: float = 0.1) -> int:
    ordered = sorted(products)
    return ordered[max(1, math.ceil(fraction * len(ordered))) - 1]


def learn_and_propose(
    domain: se.Domain,
    training: Sequence[Tuple[dict, int]],
    arm: str,
    budget_seconds: float,
    search_seed: Optional[int] = None,
    clock: Callable[[], float] = time.perf_counter,
) -> dict:
    """Run one arm under one budget and report what it paid for and found.

    ``training`` is a list of ``(compilation, product)`` pairs supplied by the
    harness. Candidate objects are validated only when their product is below
    the best training label, the only objects that can change either endpoint.
    """

    if arm not in ARMS:
        raise ValueError(f"unknown learner arm {arm!r}")
    started = clock()
    deadline = started + budget_seconds
    counts = {"attempted": 0, "duplicate": 0, "novel": 0, "invalid_code": 0, "dead_end": 0,
              "interrupted": 0, "complete": 0, "complete_at_or_below_elite": 0, "not_better": 0, "validated": 0,
              "validation_rejected": 0, "exhausted": False}
    phases = {"training_prep_seconds": 0.0, "model_seconds": 0.0, "proposal_seconds": 0.0,
              "decode_seconds": 0.0, "validation_seconds": 0.0}
    found: List[dict] = []
    discrepancies: List[dict] = []
    status = "PASS"
    reason = ""
    accounting: dict = {}
    bits = se.layout(domain, CODEC).width

    # Common training preparation, charged to every arm.
    prep_started = clock()
    train_indices: List[int] = []
    products: List[int] = []
    try:
        for compilation, product in training:
            if clock() >= deadline:
                raise _Expired
            train_indices.append(se.encode(domain, compilation, CODEC))
            products.append(product)
    except _Expired:
        phases["training_prep_seconds"] = clock() - prep_started
        return _report(arm, "INCONCLUSIVE", "budget expired during training preparation",
                       counts, phases, found, discrepancies, started, clock, bits, None, None,
                       accounting, None)
    min_train = min(products)
    threshold = elite_threshold(products)
    elite = sorted({index for index, product in zip(train_indices, products)
                    if product <= threshold})
    excluded = set(train_indices)
    phases["training_prep_seconds"] = clock() - prep_started

    cover_cubes: Sequence = ()
    if arm in ("empirical_cover", "model_depth1", "model_depth2"):
        model_started = clock()
        remaining = deadline - clock()
        if remaining <= 0:
            phases["model_seconds"] = clock() - model_started
            return _report(arm, "INCONCLUSIVE", "budget expired before cover construction",
                           counts, phases, found, discrepancies, started, clock, bits, min_train,
                           threshold, accounting, len(elite))
        cover = sm.exact_cover(elite, bits, MAX_CUBES, remaining)
        phases["model_seconds"] = clock() - model_started
        if cover.status != "COMPLETE" or clock() >= deadline:
            return _report(arm, "INCONCLUSIVE", f"elite cover {cover.status}: {cover.reason}",
                           counts, phases, found, discrepancies, started, clock, bits, min_train,
                           threshold, accounting, len(elite))
        cover_cubes = cover.cubes
        accounting["cover_cubes"] = len(cover.cubes)

    def check() -> None:
        if clock() >= deadline:
            raise _Expired

    if arm == "model_depth1":
        stream = osr.model_proposals(1, bits, cover_cubes, excluded, check, accounting)
    elif arm == "model_depth2":
        stream = osr.model_proposals(2, bits, cover_cubes, excluded, check, accounting)
    else:
        stream = sm.proposals(arm, bits, elite, cover_cubes, excluded, search_seed,
                              budget_check=check)

    evaluated: set = set()
    proposal_started = clock()
    try:
        while True:
            check()
            try:
                index, duplicate = next(stream)
            except StopIteration:
                counts["exhausted"] = True
                break
            counts["attempted"] += 1
            if duplicate or index in evaluated:
                counts["duplicate"] += 1
                continue
            evaluated.add(index)
            counts["novel"] += 1
            check()
            decode_started = clock()
            result = se.decode(domain, index, CODEC)
            phases["decode_seconds"] += clock() - decode_started
            if result.status == se.INVALID_CODE:
                counts["invalid_code"] += 1
                continue
            if result.status == se.DEAD_END:
                counts["dead_end"] += 1
                continue
            if result.status != se.COMPLETE:
                counts["interrupted"] += 1
                continue
            counts["complete"] += 1
            if result.product <= threshold:
                counts["complete_at_or_below_elite"] += 1
            if result.product >= min_train:
                counts["not_better"] += 1
                continue
            check()
            validation_started = clock()
            try:
                machine.check_compilation(domain.program, result.compilation)
                for case in domain.program["cases"]:
                    machine.check_case(domain.program, result.compilation, case)
            except (machine.CompileError, machine.ProgramError) as exc:
                phases["validation_seconds"] += clock() - validation_started
                counts["validation_rejected"] += 1
                discrepancies.append({"index": str(index), "error": str(exc)})
                continue
            phases["validation_seconds"] += clock() - validation_started
            if clock() >= deadline:
                # Paid for past the deadline: accounted, never credited.
                counts["interrupted"] += 1
                break
            counts["validated"] += 1
            found.append({"index": str(index), "identity": se.canonical_json(result.compilation),
                          "product": result.product,
                          "seconds": clock() - started})
    except _Expired:
        pass
    phases["proposal_seconds"] = clock() - proposal_started
    if discrepancies:
        status, reason = "FAIL", "a decoded completion failed pinned validation"
    return _report(arm, status, reason, counts, phases, found, discrepancies, started, clock,
                   bits, min_train, threshold, accounting, len(elite))


def _report(arm, status, reason, counts, phases, found, discrepancies, started, clock, bits,
            min_train, threshold, accounting, elite_size) -> dict:
    return {"arm": arm, "status": status, "reason": reason, "counts": counts,
            "phases": phases, "found": found, "discrepancies": discrepancies,
            "seconds": clock() - started, "bits": bits, "min_training_J": min_train,
            "elite_threshold": threshold, "elite_size": elite_size, "accounting": accounting}
