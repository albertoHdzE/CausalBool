"""Ranker side of the Stage L mechanism test (next round 1.0, plan section 7).

This module never reads an oracle, a held-out label or a fixture evaluator
file. Its only inputs are what the plan allows a ranker to see: the training
codes and their J, the domain metadata (bit width, domain digest) and the
unlabelled common pool. Everything learned is the EXISTING owner's, unchanged
and untuned: ``schema_ranker.labels`` (elite at the ceil(0.1 n)-th training
order statistic), ``fit_tree`` (depth-3 exact-Gini schema tree),
``candidate_pool`` (Hamming 1-then-2 neighbours of the elite plus uniform
draws), ``order_pool`` and ``shuffled_labels``.

What differs from the earlier protocol is only how SEEDS are derived: this
protocol keys them as PROTOCOL.json ``seed_keys`` states --
``stable_seed([pool_seed, domain_sha256])``, ``stable_seed([shuffled_labels_seed,
domain_sha256])`` and ``stable_seed([random_order_seed, domain_sha256])`` -- so
``schema_ranker.arm_seeds`` (keyed by the earlier protocol id) is not used.

The fourteen orderings: tree, hamming, shuffled_tree, ascending and ten
seeded random permutations of the SAME pool.

Usage (internal; the runner builds the spec)::

    PYTHONPATH=.reference:. python -m research.next_round_ranker --spec JSON
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Sequence

from research import next_round_common as nrc
from research import schema_ranker as sr

KIND = "next_round_ranker"
ORDERINGS = ("tree", "hamming", "shuffled_tree", "ascending") + tuple(
    f"random_{seed}" for seed in nrc.RANDOM_ORDER_SEEDS)


def seeds(domain_sha256: str) -> dict:
    return {"pool": nrc.stable_seed([nrc.SEED_POOL, domain_sha256]),
            "shuffled": nrc.stable_seed([nrc.SEED_SHUFFLED, domain_sha256]),
            "random": {seed: nrc.stable_seed([seed, domain_sha256])
                       for seed in nrc.RANDOM_ORDER_SEEDS}}


def training_labels(products: Sequence[int]):
    return sr.labels(products)


def common_pool(bits: int, indices: Sequence[int], products: Sequence[int],
                domain_sha256: str) -> dict:
    """The common pool, identical for every ordering (built from training only)."""

    threshold, y = training_labels(products)
    elite = sorted({i for i, label in zip(indices, y) if label})
    pool = sr.candidate_pool(bits, indices, elite, seeds(domain_sha256)["pool"])
    return dict(pool, elite=elite, threshold=threshold)


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
        labels = y if ordering == "tree" else sr.shuffled_labels(y, seeds(domain_sha256)
                                                                  ["shuffled"])
        fit_started = time.perf_counter()
        tree = sr.fit_tree(bits, indices, labels)
        fit_seconds = time.perf_counter() - fit_started
        info["tree"] = tree.describe()
        info["constant_tree"] = len({leaf.score for leaf in tree.leaves}) <= 1
        info["labels_sha256"] = hashlib.sha256(json.dumps(labels).encode()).hexdigest()
        ordered = sr.order_pool(pool, "tree", tree=tree)
    elif ordering == "hamming":
        ordered = sr.order_pool(pool, "hamming", elite=elite)
    elif ordering == "ascending":
        ordered = sr.order_pool(pool, "ascending")
    else:
        tag = int(ordering.split("_", 1)[1])
        ordered = sr.order_pool(pool, "random", random_seed=seeds(domain_sha256)["random"][tag])
    if sorted(ordered) != sorted(pool) or len(set(ordered)) != len(ordered):
        raise AssertionError("an ordering must be a permutation of the common pool")
    return {"ordering": ordering, "ordered": [str(i) for i in ordered],
            "ordering_sha256": sr.ordering_digest(ordered), "fit_seconds": fit_seconds,
            "seconds": time.perf_counter() - started, "info": info}


def measure(spec: dict) -> dict:
    if spec.get("kind") != KIND:
        raise ValueError("not a ranker spec")
    path = Path(spec["ranker_input"])
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != spec["ranker_input_sha256"]:
        raise ValueError("ranker input changed after the freeze")
    data = json.loads(raw)
    indices = [int(i) for i in data["training_indices"]]
    pool = [int(i) for i in data["pool"]]
    result = order(spec["ordering"], data["bits"], indices, data["training_products"], pool,
                   data["domain_sha256"])
    return {"kind": KIND + "_result", "program_sha256": spec["program_sha256"],
            "fixture_id": data["fixture_id"], "correctness": "PASS",
            "loaded_modules_with_oracle_access": sorted(
                name for name in sys.modules if name.endswith(("structural_oracle",
                                                               "next_round_learning",
                                                               "objective_index_fixtures",
                                                               "optimization_fixtures"))),
            **result}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    args = parser.parse_args(argv)
    try:
        result = measure(json.loads(args.spec))
    except Exception as exc:  # retained by the harness as a failed row
        print(f"ranker failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
