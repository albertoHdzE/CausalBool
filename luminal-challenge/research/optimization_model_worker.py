"""One fixture model measurement per process: the evaluator around a learner.

The evaluator loads the immutable fixture cache -- record, oracle enumeration
and split -- and hands the learner only the domain record and the labelled
TRAINING objects. After the learner returns, the evaluator classifies each
validated object it reported: validation, test, training (a defect: the
learner was told those) or absent from the oracle (a defect). Cache loading and
classification are evaluator costs and are reported separately from the
learner's budgeted seconds.

Usage (internal)::

    PYTHONPATH=.reference:. python -m research.optimization_model_worker --spec JSON
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import time

_IMPORT_STARTED = time.perf_counter()

import compare_direct as official  # noqa: E402

from research import optimization_models as om  # noqa: E402
from research import structural_encoding as se  # noqa: E402

_IMPORT_SECONDS = time.perf_counter() - _IMPORT_STARTED

KIND = "optimization_model_measurement"


def _sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(spec: dict) -> dict:
    if spec.get("kind") != KIND:
        raise ValueError("not a model measurement spec")
    fixture_dir = Path(spec["fixture_dir"])
    load_started = time.perf_counter()
    record_path, oracle_path, split_path = (fixture_dir / "record.json",
                                            fixture_dir / "oracle.json", fixture_dir / "split.json")
    hashes = {"record": _sha(record_path), "oracle": _sha(oracle_path), "split": _sha(split_path)}
    for key, expected in spec["expected_sha256"].items():
        if hashes[key] != expected:
            raise ValueError(f"fixture cache {key} hash differs from the frozen manifest")
    record = json.loads(record_path.read_text())
    oracle = json.loads(oracle_path.read_text())
    parts = json.loads(split_path.read_text())
    products = {item["identity"]: item["product"] for item in oracle["feasible"]}
    membership = {}
    for name in ("train", "validation", "test"):
        for identity in parts[name]:
            membership[identity] = name
    domain = se.Domain.from_record(record)
    training = [(json.loads(identity), products[identity]) for identity in parts["train"]]
    cache_load_seconds = time.perf_counter() - load_started

    # The learner sees the domain and the training labels, nothing else.
    report = om.learn_and_propose(domain, training, spec["learner_arm"],
                                  float(spec["budget_seconds"]), spec.get("search_seed"))

    classify_started = time.perf_counter()
    min_train = min(products[i] for i in parts["train"])
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
    classify_seconds = time.perf_counter() - classify_started
    correctness = "PASS" if not defects and report["status"] != "FAIL" else "FAIL"
    return {
        "kind": KIND + "_result",
        "fixture_id": spec["fixture_id"],
        "family": spec["family"],
        "program_sha256": spec["program_sha256"],
        "arm": spec["arm"],
        "learner_arm": spec["learner_arm"],
        "search_seed": spec.get("search_seed"),
        "budget_seconds": spec["budget_seconds"],
        "repetition": spec["repetition"],
        "learner_status": report["status"],
        "learner_reason": report["reason"],
        "counts": report["counts"],
        "phases": report["phases"],
        "accounting": report["accounting"],
        "bits": report["bits"],
        "elite_size": report["elite_size"],
        "learner_seconds": report["seconds"],
        "min_training_J": min_train,
        "best_validation_J": best["validation"],
        "best_test_J": best["test"],
        "log_train_over_best_validation": math.log(min_train / best["validation"]),
        "log_train_over_best_test": math.log(min_train / best["test"]),
        "discoveries": discoveries,
        "found": report["found"][:64],
        "found_total": len(report["found"]),
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
        print(f"model worker failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(se.canonical_json(result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
