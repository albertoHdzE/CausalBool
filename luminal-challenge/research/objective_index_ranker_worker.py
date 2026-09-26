"""One fixture ranker measurement per process: the evaluator around a learner.

The evaluator loads the immutable fixture cache (record, oracle enumeration,
split), verifies its hashes against the frozen manifest, and hands the learner
(``schema_ranker.rank_and_propose``) only the domain record and the labelled
TRAINING objects. It then classifies what the learner reports:

- wall-time rows: each validated discovery is test, validation, training (a
  defect: the learner was told those) or absent from the oracle (a defect);
  ``best_test_J = min(training_min_J, validated TEST discoveries)``;
- fixed-work rows: every proposal of the whole ordered pool is scored, and the
  descriptive prefix metrics at 8, 32 and 128 unique proposals (or the whole
  pool if shorter) are computed here, from the oracle, never by the learner.

Cache loading and classification are evaluator costs, reported separately
from the learner's seconds; the original oracle enumeration cost is reported
from the frozen cache.

Usage (internal)::

    PYTHONPATH=.reference:. python -m research.objective_index_ranker_worker --spec JSON
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

_IMPORT_STARTED = time.perf_counter()

import compare_direct as official  # noqa: E402

from research import schema_ranker as sr  # noqa: E402
from research import structural_encoding as se  # noqa: E402

_IMPORT_SECONDS = time.perf_counter() - _IMPORT_STARTED

KIND = "objective_index_ranker_measurement"
CHECKPOINTS = sr.FIXED_WORK_CHECKPOINTS


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prefix_metrics(scored: list, min_train: int, threshold: int, checkpoint: int) -> dict:
    """Descriptive metrics of the first ``checkpoint`` novel proposals."""

    head = scored[:checkpoint]
    complete = [s for s in head if s["product"] is not None]
    test = [s for s in complete if s["split"] == "test"]
    best_test_validated = min([s["product"] for s in head
                               if s["split"] == "test" and s.get("validated") is True]
                              + [min_train])
    return {"checkpoint": checkpoint, "proposals": len(head), "complete": len(complete),
            "complete_test": len(test),
            "complete_validation": sum(1 for s in complete if s["split"] == "validation"),
            "elite_level_complete": sum(1 for s in complete if s["product"] <= threshold),
            "elite_level_test": sum(1 for s in test if s["product"] <= threshold),
            "best_complete_J": min((s["product"] for s in complete), default=None),
            "best_test_complete_J": min((s["product"] for s in test), default=None),
            "best_test_J_endpoint": best_test_validated,
            "log_train_over_best_test": math.log(min_train / best_test_validated)}


def measure(spec: dict) -> dict:
    if spec.get("kind") != KIND:
        raise ValueError("not a ranker measurement spec")
    fixture_dir = Path(spec["fixture_dir"])
    load_started = time.perf_counter()
    paths = {name: fixture_dir / f"{name}.json" for name in ("record", "oracle", "split")}
    hashes = {name: _sha(path) for name, path in paths.items()}
    for key, expected in spec["expected_sha256"].items():
        if hashes[key] != expected:
            raise ValueError(f"fixture cache {key} hash differs from the frozen manifest")
    record = json.loads(paths["record"].read_text())
    oracle = json.loads(paths["oracle"].read_text())
    parts = json.loads(paths["split"].read_text())
    products = {item["identity"]: item["product"] for item in oracle["feasible"]}
    membership = {}
    for name in ("train", "validation", "test"):
        for identity in parts[name]:
            membership[identity] = name
    domain = se.Domain.from_record(record)
    training = [(json.loads(identity), products[identity]) for identity in parts["train"]]
    cache_load_seconds = time.perf_counter() - load_started

    fixed_work = spec["budget_seconds"] == "fixed_work"
    # The learner sees the domain and the training labels, nothing else.
    report = sr.rank_and_propose(domain, training, spec["learner_arm"],
                                 None if fixed_work else float(spec["budget_seconds"]),
                                 spec.get("random_tag"), fixed_work=fixed_work)

    classify_started = time.perf_counter()
    min_train = min(products[i] for i in parts["train"])
    threshold = report["info"].get("elite_threshold")
    best = {"validation": min_train, "test": min_train}
    discoveries = {"validation": 0, "test": 0, "train": 0, "absent": 0}
    defects = list(report["discrepancies"])
    for item in report["found"]:
        where = membership.get(item["identity"])
        if where is None:
            discoveries["absent"] += 1
            defects.append({"identity_absent_from_oracle": item["identity"][:200]})
            continue
        if products[item["identity"]] != item["product"]:
            defects.append({"product_mismatch": item["identity"][:200]})
        discoveries[where] += 1
        if where == "train":
            defects.append({"training_object_reported_as_new": item["identity"][:200]})
            continue
        best[where] = min(best[where], item["product"])
    if report["info"].get("min_training_J") not in (None, min_train):
        defects.append({"learner_min_training_J_mismatch": report["info"]["min_training_J"]})
    prefixes = None
    compact_trace = None
    if fixed_work and spec["learner_arm"] != "empirical_cover":
        scored = []
        for entry in report["trace"]:
            identity = entry.get("identity_json")
            split = None
            product = entry.get("product")
            if identity is not None:
                split = membership.get(identity)
                if split is None:
                    defects.append({"complete_decode_absent_from_oracle": identity[:200]})
                elif products[identity] != product:
                    defects.append({"decoded_product_mismatch": identity[:200]})
                if split == "train":
                    defects.append({"pool_contains_training_object": identity[:200]})
            scored.append({"product": product, "split": split,
                           "validated": entry.get("validated")})
        n = len(scored)
        prefixes = [prefix_metrics(scored, min_train, threshold, c) for c in CHECKPOINTS if c < n]
        prefixes.append(dict(prefix_metrics(scored, min_train, threshold, n), whole_pool=True))
        compact_trace = [[s["product"], {"test": "T", "validation": "V", "train": "R",
                                         None: "-"}[s["split"]]] for s in scored]
    classify_seconds = time.perf_counter() - classify_started
    correctness = "PASS" if not defects and report["status"] not in ("FAIL",) else "FAIL"
    return {
        "kind": KIND + "_result",
        "fixture_id": spec["fixture_id"],
        "family": spec["family"],
        "program_sha256": spec["program_sha256"],
        "arm": spec["arm"],
        "learner_arm": spec["learner_arm"],
        "random_tag": spec.get("random_tag"),
        "budget_seconds": spec["budget_seconds"],
        "repetition": spec["repetition"],
        "learner_status": report["status"],
        "learner_reason": report["reason"],
        "counts": report["counts"],
        "phases": report["phases"],
        "info": report["info"],
        "learner_seconds": report["seconds"],
        "min_training_J": min_train,
        "best_validation_J": best["validation"],
        "best_test_J": best["test"],
        "log_train_over_best_validation": math.log(min_train / best["validation"]),
        "log_train_over_best_test": math.log(min_train / best["test"]),
        "discoveries": discoveries,
        "found": report["found"][:64],
        "found_total": len(report["found"]),
        "prefixes": prefixes,
        "trace": compact_trace,
        "defects": defects[:32],
        "defect_count": len(defects),
        "evaluator": {"cache_load_seconds": cache_load_seconds,
                      "classify_seconds": classify_seconds,
                      "oracle_enumeration_seconds_original": oracle["oracle_seconds"],
                      "cache_sha256": hashes},
        "import_seconds": _IMPORT_SECONDS,
        "peak_rss_bytes": official.peak_rss_bytes(),
        "correctness": correctness,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    args = parser.parse_args(argv)
    try:
        result = measure(json.loads(args.spec))
    except Exception as exc:  # retained by the harness as a failed row
        print(f"ranker worker failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(se.canonical_json(result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
