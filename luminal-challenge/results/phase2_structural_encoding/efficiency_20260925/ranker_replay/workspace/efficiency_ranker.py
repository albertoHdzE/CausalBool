"""Oracle-free ranker boundary for the guarded replay (efficiency phase, R3).

Plan ``CLAUDE_PHASE2_EFFICIENCY_PHASE.md`` section 3, R3. The next-round ranker
(``research/next_round_ranker.py``) reached ``research.structural_oracle``
transitively (``schema_ranker -> optimization_models -> ... ->
run_structural_experiments``), so the checker flagged every one of its 420
processes as ``ORACLE_LEAK``: oracle CAPABILITY, not demonstrated access.

This module is the dependency boundary. It holds ONLY the pure helpers that
``next_round_ranker.order`` executes, extracted from their owners with the
algorithm bodies unchanged; the one change is that a qualified reference to
another owner (``sr.fit_tree``, ``om.elite_threshold``, ``nrc.SEED_POOL``...)
becomes the unqualified name of the extracted helper or constant. Its imports
are the standard library and the production cube owner ``schema_index``
(itself standard-library only). It reads no oracle, evaluator, fixture,
program or machine file, and it trains, pools, seeds, ties and orders exactly
as the owners do. ``PROVENANCE`` names the owner of every extracted
definition; ``research_tests/test_efficiency_ranker.py`` proves each one
AST-identical to its owner after that renaming, and stores both hashes.

Nothing here is new learning: no fitting policy, pool construction, seed,
tree definition or tie-break differs from the owners. The replay is an
isolation verification of the 420 retained orderings, not a new experiment.

Usage inside the guarded minimal workspace (``efficiency_replay`` builds it)::

    python efficiency_ranker.py --spec JSON
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
import random
import sys
import time
from typing import List, Optional, Sequence, Tuple

import schema_index as si

KIND = "efficiency_ranker_replay"

# Owner of each extracted definition: (module file, qualified name in it).
PROVENANCE = {
    "stable_seed": ("research/objective_index_common.py", "stable_seed"),
    "elite_threshold": ("research/optimization_models.py", "elite_threshold"),
    "labels": ("research/schema_ranker.py", "labels"),
    "_gini": ("research/schema_ranker.py", "_gini"),
    "Leaf": ("research/schema_ranker.py", "Leaf"),
    "SchemaTree": ("research/schema_ranker.py", "SchemaTree"),
    "fit_tree": ("research/schema_ranker.py", "fit_tree"),
    "shuffled_labels": ("research/schema_ranker.py", "shuffled_labels"),
    "order_pool": ("research/schema_ranker.py", "order_pool"),
    "ordering_digest": ("research/schema_ranker.py", "ordering_digest"),
    "seeds": ("research/next_round_ranker.py", "seeds"),
    "training_labels": ("research/next_round_ranker.py", "training_labels"),
    "order": ("research/next_round_ranker.py", "order"),
}

# Qualified owner names replaced by the unqualified extracted names.
RENAMES = {
    "om.elite_threshold": "elite_threshold",
    "sr.labels": "labels", "sr.fit_tree": "fit_tree", "sr.order_pool": "order_pool",
    "sr.shuffled_labels": "shuffled_labels", "sr.ordering_digest": "ordering_digest",
    "nrc.stable_seed": "stable_seed", "nrc.SEED_POOL": "SEED_POOL",
    "nrc.SEED_SHUFFLED": "SEED_SHUFFLED", "nrc.RANDOM_ORDER_SEEDS": "RANDOM_ORDER_SEEDS",
}

# Constants, with their owners (checked equal by the test suite).
MAX_DEPTH = 3                       # schema_ranker.MAX_DEPTH
MIN_CHILD = 4                       # schema_ranker.MIN_CHILD
ELITE_FRACTION = 0.1                # schema_ranker.ELITE_FRACTION
SEED_POOL = 2026092604              # next_round_common.SEED_POOL
SEED_SHUFFLED = 2026092605          # next_round_common.SEED_SHUFFLED
RANDOM_ORDER_SEEDS: Tuple[int, ...] = tuple(range(2026092610, 2026092620))
ORDERINGS = ("tree", "hamming", "shuffled_tree", "ascending") + tuple(
    f"random_{seed}" for seed in RANDOM_ORDER_SEEDS)


# --------------------------------------------------------------------------
# objective_index_common / optimization_models
# --------------------------------------------------------------------------


def stable_seed(parts: object) -> int:
    """Protocol section 7: sha256 of compact sorted-key JSON, first 16 hex digits."""

    text = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)


def elite_threshold(products: Sequence[int], fraction: float = 0.1) -> int:
    ordered = sorted(products)
    return ordered[max(1, math.ceil(fraction * len(ordered))) - 1]


# --------------------------------------------------------------------------
# schema_ranker
# --------------------------------------------------------------------------


def labels(products: Sequence[int]) -> Tuple[int, List[int]]:
    """``(threshold, labels)``: 1 at or below the ceil(0.1 n)-th order statistic."""

    threshold = elite_threshold(products, ELITE_FRACTION)
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
# next_round_ranker
# --------------------------------------------------------------------------


def seeds(domain_sha256: str) -> dict:
    return {"pool": stable_seed([SEED_POOL, domain_sha256]),
            "shuffled": stable_seed([SEED_SHUFFLED, domain_sha256]),
            "random": {seed: stable_seed([seed, domain_sha256])
                       for seed in RANDOM_ORDER_SEEDS}}


def training_labels(products: Sequence[int]):
    return labels(products)


def order(ordering: str, bits: int, indices: Sequence[int], products: Sequence[int],
          pool: Sequence[int], domain_sha256: str) -> dict:
    """One ordering of the common pool, with its own costs and model description."""

    if ordering not in ORDERINGS:
        raise ValueError(f"unknown ordering {ordering!r}")
    started = time.perf_counter()
    ranked = sorted(zip(indices, products))
    indices = [i for i, _ in ranked]
    products = [p for _, p in ranked]
    threshold, y = training_labels(products)
    elite = sorted({i for i, label in zip(indices, y) if label})
    info: dict = {"threshold": threshold, "positives": sum(y), "elite": len(elite)}
    fit_seconds = 0.0
    if ordering in ("tree", "shuffled_tree"):
        labels = y if ordering == "tree" else shuffled_labels(y, seeds(domain_sha256)
                                                              ["shuffled"])
        fit_started = time.perf_counter()
        tree = fit_tree(bits, indices, labels)
        fit_seconds = time.perf_counter() - fit_started
        info["tree"] = tree.describe()
        info["constant_tree"] = len({leaf.score for leaf in tree.leaves}) <= 1
        info["labels_sha256"] = hashlib.sha256(json.dumps(labels).encode()).hexdigest()
        ordered = order_pool(pool, "tree", tree=tree)
    elif ordering == "hamming":
        ordered = order_pool(pool, "hamming", elite=elite)
    elif ordering == "ascending":
        ordered = order_pool(pool, "ascending")
    else:
        tag = int(ordering.split("_", 1)[1])
        ordered = order_pool(pool, "random", random_seed=seeds(domain_sha256)["random"][tag])
    if sorted(ordered) != sorted(pool) or len(set(ordered)) != len(ordered):
        raise AssertionError("an ordering must be a permutation of the common pool")
    return {"ordering": ordering, "ordered": [str(i) for i in ordered],
            "ordering_sha256": ordering_digest(ordered), "fit_seconds": fit_seconds,
            "seconds": time.perf_counter() - started, "info": info}


# --------------------------------------------------------------------------
# Replay entry point (new; not an extraction)
# --------------------------------------------------------------------------


def replay(spec: dict) -> dict:
    """One ordering from one frozen ranker input; the input hash is verified."""

    if spec.get("kind") != KIND:
        raise ValueError("not an efficiency ranker replay spec")
    with open(spec["ranker_input"], "rb") as handle:
        raw = handle.read()
    if hashlib.sha256(raw).hexdigest() != spec["ranker_input_sha256"]:
        raise ValueError("ranker input differs from its recorded hash")
    data = json.loads(raw)
    result = order(spec["ordering"], data["bits"], [int(i) for i in data["training_indices"]],
                   data["training_products"], [int(i) for i in data["pool"]],
                   data["domain_sha256"])
    return {"kind": KIND + "_result", "fixture_id": data["fixture_id"],
            "loaded_modules": sorted(sys.modules), **result}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    args = parser.parse_args(argv)
    result = replay(json.loads(args.spec))
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
