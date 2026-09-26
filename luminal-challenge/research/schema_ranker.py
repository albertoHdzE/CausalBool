"""A supervised schema ranker over canonical index bits (protocol section 7).

A deterministic depth-3 binary decision tree is fitted to ALL labelled training
objects (good and poor) over the original ``structural_rank`` index bits. A
leaf is a schema: its tested coordinates form the decimal anchor and its
untested coordinates the free-coordinate mask, built with the ``schema_index``
cube owner (``universe``/``split``). The leaves partition the whole B-bit
universe. They carry an ESTIMATED quality, never a feasibility guarantee: a
coordinate free in a prediction leaf preserves that leaf's prediction only.

A prediction only ORDERS proposals. It never prunes, certifies an improvement
or bypasses validation. This module imports no oracle, no fixture evaluator
and no split map; the test suite asserts that statically.

Contents:

- ``labels`` / ``fit_tree`` / ``SchemaTree``: the learner (exact rational Gini,
  lowest-coordinate tie-break, both children >= 4, stop at depth 3, pure node,
  no admissible split or gain <= 0; leaf score (positives+1)/(count+2));
- ``candidate_pool``: the common novel pool (Hamming 1 then 2, then uniform
  draws), identical for every learner and control arm;
- ``order_pool``: tree, ascending, hamming, shuffled_tree and random orders;
- ``rank_and_propose``: the fixture learner run (wall-time or fixed-work),
  paying for every step it takes.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import itertools
import json
import random
import time
from typing import Callable, List, Optional, Sequence, Tuple

import machine

import schema_index as si

from research import objective_index_common as oic
from research import optimization_models as om
from research import structural_encoding as se


__all__ = [
    "ARMS", "MAX_DEPTH", "MIN_CHILD", "MIN_TRAINING", "labels", "fit_tree", "SchemaTree",
    "candidate_pool", "order_pool", "arm_seeds", "rank_and_propose", "shuffled_labels",
]

MAX_DEPTH = 3
MIN_CHILD = 4
MIN_TRAINING = 20
HAMMING_MAX = 256
RANDOM_MAX = 256
RANDOM_DRAWS_MAX = 8192
ELITE_FRACTION = 0.1
CODEC = "structural_rank"
ARMS = ("tree", "ascending", "hamming", "shuffled_tree", "empirical_cover", "random")
FIXED_WORK_CHECKPOINTS = (8, 32, 128)


# --------------------------------------------------------------------------
# Labels and the tree
# --------------------------------------------------------------------------


def labels(products: Sequence[int]) -> Tuple[int, List[int]]:
    """``(threshold, labels)``: 1 at or below the ceil(0.1 n)-th order statistic."""

    threshold = om.elite_threshold(products, ELITE_FRACTION)
    return threshold, [1 if product <= threshold else 0 for product in products]


def _gini(positive: int, count: int) -> Fraction:
    if count == 0:
        return Fraction(0)
    p = Fraction(positive, count)
    return 1 - p * p - (1 - p) * (1 - p)


@dataclass(frozen=True)
class Leaf:
    cube: si.Cube
    count: int
    positive: int
    depth: int

    @property
    def score(self) -> Fraction:
        return Fraction(self.positive + 1, self.count + 2)


@dataclass(frozen=True)
class SchemaTree:
    bits: int
    leaves: Tuple[Leaf, ...]
    splits: Tuple[dict, ...]

    def leaf_of(self, index: int) -> Leaf:
        for leaf in self.leaves:
            if leaf.cube.contains(index):
                return leaf
        raise ValueError(f"index {index} is outside the {self.bits}-bit universe")

    def predict(self, index: int) -> Fraction:
        return self.leaf_of(index).score

    def describe(self) -> dict:
        return {"bits": self.bits,
                "leaves": [{"schema": leaf.cube.label(), "anchor": leaf.cube.anchor,
                            "free_mask": leaf.cube.free_mask, "count": leaf.count,
                            "positive": leaf.positive, "depth": leaf.depth,
                            "score": [leaf.score.numerator, leaf.score.denominator]}
                           for leaf in self.leaves],
                "splits": list(self.splits)}


def fit_tree(bits: int, indices: Sequence[int], labels_: Sequence[int]) -> SchemaTree:
    """The deterministic depth-3 tree; no hyperparameter is searched."""

    if len(indices) != len(labels_):
        raise ValueError("one label per training index is required")
    data = list(zip(indices, labels_))
    leaves: List[Leaf] = []
    splits: List[dict] = []

    def grow(cube: si.Cube, rows: List[Tuple[int, int]], used: Tuple[int, ...], depth: int):
        positive = sum(label for _, label in rows)
        count = len(rows)
        if depth >= MAX_DEPTH or positive in (0, count):
            leaves.append(Leaf(cube, count, positive, depth))
            return
        parent = _gini(positive, count)
        best = None
        for coordinate in range(bits):
            if coordinate in used:
                continue
            bit = 1 << coordinate
            left = [row for row in rows if not row[0] & bit]
            right = [row for row in rows if row[0] & bit]
            if len(left) < MIN_CHILD or len(right) < MIN_CHILD:
                continue
            weighted = (Fraction(len(left), count) * _gini(sum(l for _, l in left), len(left))
                        + Fraction(len(right), count)
                        * _gini(sum(l for _, l in right), len(right)))
            gain = parent - weighted
            if best is None or gain > best[0]:
                best = (gain, coordinate, left, right)
        if best is None or best[0] <= 0:
            leaves.append(Leaf(cube, count, positive, depth))
            return
        gain, coordinate, left, right = best
        splits.append({"depth": depth, "schema": cube.label(), "coordinate": coordinate,
                       "gain": [gain.numerator, gain.denominator], "left": len(left),
                       "right": len(right)})
        zero, one = si.split(cube, coordinate)
        grow(zero, left, used + (coordinate,), depth + 1)
        grow(one, right, used + (coordinate,), depth + 1)

    grow(si.universe(bits), data, (), 0)
    return SchemaTree(bits=bits, leaves=tuple(leaves), splits=tuple(splits))


def shuffled_labels(labels_: Sequence[int], seed: int) -> List[int]:
    """A class-count-preserving permutation of the labels."""

    permuted = list(labels_)
    random.Random(seed).shuffle(permuted)
    return permuted


# --------------------------------------------------------------------------
# The common novel pool and its orderings
# --------------------------------------------------------------------------


def arm_seeds(domain_hash: str) -> dict:
    """Protocol section 7 seeds, all through ``stable_seed``."""

    pid = oic.PROTOCOL_ID
    return {"pool": oic.stable_seed([pid, domain_hash, oic.SEED_POOL]),
            "shuffled": oic.stable_seed([pid, domain_hash, oic.SEED_SHUFFLED]),
            "random": {tag: oic.stable_seed([pid, domain_hash, tag])
                       for tag in oic.RANDOM_ORDER_SEEDS}}


def candidate_pool(bits: int, training: Sequence[int], elite: Sequence[int], seed: int,
                   check: Optional[Callable[[], None]] = None) -> dict:
    """Up to 256 Hamming-1-then-2 neighbours of the elite plus up to 256 draws.

    Neighbours are generated distance-major, elite ascending, coordinate tuples
    lexicographic, keeping the first 256 distinct indices outside the whole
    training set. Then at most 8,192 uniform B-bit draws add up to 256 new
    indices, stopping early if the universe is exhausted. No oracle filtering.
    """

    training_set = set(training)
    chosen: List[int] = []
    seen = set()
    for distance in (1, 2):
        if len(chosen) >= HAMMING_MAX:
            break
        for anchor in sorted(set(elite)):
            if len(chosen) >= HAMMING_MAX:
                break
            for coordinates in itertools.combinations(range(bits), distance):
                if check is not None:
                    check()
                candidate = anchor
                for coordinate in coordinates:
                    candidate ^= 1 << coordinate
                if candidate in training_set or candidate in seen:
                    continue
                seen.add(candidate)
                chosen.append(candidate)
                if len(chosen) >= HAMMING_MAX:
                    break
    hamming = len(chosen)
    rng = random.Random(seed)
    universe = 1 << bits
    draws = added = 0
    exhausted = False
    while added < RANDOM_MAX and draws < RANDOM_DRAWS_MAX:
        if len(training_set | seen) >= universe:
            exhausted = True
            break
        if check is not None:
            check()
        draws += 1
        candidate = rng.getrandbits(bits) if bits else 0
        if candidate in training_set or candidate in seen:
            continue
        seen.add(candidate)
        added += 1
    pool = sorted(seen)
    digest = hashlib.sha256(json.dumps(pool, separators=(",", ":")).encode()).hexdigest()
    return {"pool": pool, "hamming": hamming, "random": added, "draws": draws,
            "universe_exhausted": exhausted, "pool_sha256": digest, "size": len(pool)}


def order_pool(pool: Sequence[int], arm: str, *, elite: Sequence[int] = (),
               tree: Optional[SchemaTree] = None, random_seed: Optional[int] = None
               ) -> List[int]:
    """One ordering of the SAME pool."""

    if arm in ("tree", "shuffled_tree"):
        if tree is None:
            raise ValueError(f"{arm} requires a fitted tree")
        return sorted(pool, key=lambda index: (-tree.predict(index), index))
    if arm == "ascending":
        return sorted(pool)
    if arm == "hamming":
        anchors = sorted(set(elite))
        return sorted(pool, key=lambda index: (min(((index ^ e).bit_count() for e in anchors),
                                                   default=0), index))
    if arm == "random":
        if random_seed is None:
            raise ValueError("random ordering requires a seed")
        ordered = list(pool)
        random.Random(random_seed).shuffle(ordered)
        return ordered
    raise ValueError(f"unknown ordering {arm!r}")


def ordering_digest(ordered: Sequence[int]) -> str:
    return hashlib.sha256(json.dumps(list(ordered), separators=(",", ":")).encode()).hexdigest()


# --------------------------------------------------------------------------
# The fixture learner run
# --------------------------------------------------------------------------


class _Expired(Exception):
    pass


def rank_and_propose(
    domain: se.Domain,
    training: Sequence[Tuple[dict, int]],
    arm: str,
    budget_seconds: Optional[float],
    random_tag: Optional[int] = None,
    fixed_work: bool = False,
    clock: Callable[[], float] = time.perf_counter,
) -> dict:
    """One arm on one fixture: pay for training, pool, model, proposals, checks.

    ``training`` is the harness-supplied list of ``(compilation, product)``.
    Wall-time mode stops at ``budget_seconds``; fixed-work mode walks the whole
    ordered pool with no wall limit (the external process limit still applies)
    and records every proposal so prefixes can be scored. Objects are validated
    only when their product is below the best training label: only those can
    change the endpoint. Every validated object is reported; the evaluator,
    not this function, decides whether it was a test object.
    """

    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}")
    if arm == "random" and random_tag not in oic.RANDOM_ORDER_SEEDS:
        raise ValueError("random requires one of the ten protocol seeds")
    started = clock()
    deadline = None if fixed_work else started + float(budget_seconds)
    phases = {"training_prep_seconds": 0.0, "pool_seconds": 0.0, "model_seconds": 0.0,
              "ordering_seconds": 0.0, "proposal_seconds": 0.0, "decode_seconds": 0.0,
              "validation_seconds": 0.0}
    counts = {"proposed": 0, "novel": 0, "duplicate_or_training": 0, "invalid_code": 0,
              "dead_end": 0, "interrupted": 0, "complete": 0, "complete_at_or_below_elite": 0,
              "not_better": 0, "validated": 0, "validation_rejected": 0,
              "late_validation": 0, "pool_exhausted": False}
    found: List[dict] = []
    trace: List[dict] = []
    discrepancies: List[dict] = []
    info: dict = {"arm": arm, "random_tag": random_tag, "fixed_work": fixed_work}

    def check() -> None:
        if deadline is not None and clock() >= deadline:
            raise _Expired

    def finish(status: str, reason: str) -> dict:
        return {"status": status, "reason": reason, "counts": counts, "phases": phases,
                "found": found, "trace": trace, "discrepancies": discrepancies,
                "seconds": clock() - started, "info": info}

    proposal_started: Optional[float] = None
    bits = se.layout(domain, CODEC).width
    domain_hash = domain.digest()
    seeds = arm_seeds(domain_hash)
    info.update(bits=bits, domain_sha256=domain_hash)
    try:
        # Common training preparation, charged to every arm.
        prep = clock()
        indices: List[int] = []
        products: List[int] = []
        for compilation, product in training:
            check()
            indices.append(se.encode(domain, compilation, CODEC))
            products.append(product)
        order = sorted(range(len(indices)), key=lambda i: indices[i])
        indices = [indices[i] for i in order]
        products = [products[i] for i in order]
        threshold, y = labels(products)
        elite = sorted({index for index, label in zip(indices, y) if label})
        min_train = min(products)
        phases["training_prep_seconds"] = clock() - prep
        info.update(min_training_J=min_train, elite_threshold=threshold, elite_size=len(elite),
                    training_distinct=len(set(indices)), positives=sum(y))

        if arm == "empirical_cover":
            # Proposes only already observed elite indices: never novel.
            for index in elite:
                counts["proposed"] += 1
                counts["duplicate_or_training"] += 1
                if fixed_work:
                    trace.append({"index": str(index), "status": "TRAINING"})
            counts["pool_exhausted"] = True
            return finish("PASS", "empirical cover proposes no novel index")

        pool_started = clock()
        pool = candidate_pool(bits, indices, elite, seeds["pool"], check)
        phases["pool_seconds"] = clock() - pool_started
        info.update(pool_sha256=pool["pool_sha256"], pool_size=pool["size"],
                    pool_hamming=pool["hamming"], pool_random=pool["random"],
                    pool_draws=pool["draws"], pool_universe_exhausted=pool["universe_exhausted"])

        tree = None
        if arm in ("tree", "shuffled_tree"):
            model_started = clock()
            if len(set(indices)) < MIN_TRAINING:
                phases["model_seconds"] = clock() - model_started
                info["model"] = "MODEL_UNAVAILABLE"
                return finish("MODEL_UNAVAILABLE",
                              f"{len(set(indices))} distinct training objects < {MIN_TRAINING}")
            fit_labels = y
            if arm == "shuffled_tree":
                fit_labels = shuffled_labels(y, seeds["shuffled"])
                info["shuffled_labels_sha256"] = hashlib.sha256(
                    json.dumps(fit_labels).encode()).hexdigest()
            check()
            tree = fit_tree(bits, indices, fit_labels)
            phases["model_seconds"] = clock() - model_started
            info["tree"] = tree.describe()

        ordering_started = clock()
        ordered = order_pool(pool["pool"], "tree" if arm == "shuffled_tree" else arm,
                             elite=elite, tree=tree,
                             random_seed=seeds["random"].get(random_tag))
        phases["ordering_seconds"] = clock() - ordering_started
        info["ordering_sha256"] = ordering_digest(ordered)
        excluded = set(indices)
        proposal_started = clock()
        for index in ordered:
            check()
            counts["proposed"] += 1
            if index in excluded:
                counts["duplicate_or_training"] += 1
                continue
            counts["novel"] += 1
            decode_started = clock()
            result = se.decode(domain, index, CODEC)
            phases["decode_seconds"] += clock() - decode_started
            entry = {"index": str(index), "status": result.status}
            if result.status == se.INVALID_CODE:
                counts["invalid_code"] += 1
            elif result.status == se.DEAD_END:
                counts["dead_end"] += 1
            elif result.status != se.COMPLETE:
                counts["interrupted"] += 1
            else:
                counts["complete"] += 1
                entry.update(product=result.product, identity=result.identity)
                if result.product <= threshold:
                    counts["complete_at_or_below_elite"] += 1
                if result.product >= min_train:
                    counts["not_better"] += 1
                else:
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
                        entry["validated"] = False
                    else:
                        phases["validation_seconds"] += clock() - validation_started
                        if deadline is not None and clock() >= deadline:
                            # Paid for past the deadline: accounted, never credited.
                            counts["late_validation"] += 1
                            entry["validated"] = "late"
                        else:
                            counts["validated"] += 1
                            entry["validated"] = True
                            found.append({"index": str(index),
                                          "identity": se.canonical_json(result.compilation),
                                          "product": result.product,
                                          "seconds": clock() - started})
            if fixed_work:
                if entry.get("identity"):
                    entry["identity_json"] = se.canonical_json(result.compilation)
                trace.append(entry)
        counts["pool_exhausted"] = True
        phases["proposal_seconds"] = clock() - proposal_started
    except _Expired:
        if proposal_started is not None:
            phases["proposal_seconds"] = clock() - proposal_started
        status = "FAIL" if discrepancies else "PASS"
        return finish(status, "the budget expired")
    status = "FAIL" if discrepancies else "PASS"
    return finish(status, "the ordered pool was exhausted")
