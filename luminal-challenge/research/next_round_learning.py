"""Harness and evaluator of the Stage L mechanism test (next round 1.0, section 7).

Evaluator side: this module reads oracles. It draws the oracle-supplied
training objects, builds the common pool from TRAINING ONLY (through the ranker
module, so the pool is the ranker's own), writes two files per fixture --

- ``RANKER_INPUT.json``: training codes and J, bit width, domain digest, pool.
  The only file a ranker process reads.
- ``EVALUATOR.json``: held-out labels of every pool entry, the elite threshold,
  and the endpoint-sensitivity diagnostic. Never given to a ranker.

-- and later scores the ranker's orderings.

Definitions fixed in the plan and restated here as code:

- training draw: 20 feasible objects uniformly without replacement from the
  SORTED physical identities, ``random.Random(stable_seed([2026092603,
  fixture_sha256])).sample``; ``fixture_sha256`` is the sha256 of the fixture's
  ``record.json`` as listed in its manifest (``record_sha256``);
- elite threshold: the existing ``schema_ranker.labels`` rule on the 20
  training J (the ceil(0.1 * 20) = 2nd order statistic);
- useful pool entry: a pool index whose object is a held-out feasible object
  with J <= that threshold (distinct objects; training objects never count);
- primary endpoint: novel elite yield at 32 = useful distinct objects among the
  first min(32, N) proposals, divided by 32 (invalid proposals consume
  positions, short pools leave empty positions);
- sensitivity: with k = min(32, N), max = min(k, M), min = max(0, k - (N - M));
  a fixture distinguishes orderings iff max - min > 0.
"""

from __future__ import annotations

import collections
import hashlib
import json
import math
import random
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from research import next_round_common as nrc
from research import next_round_ranker as nrr
from research import optimization_common as oc
from research import run_structural_experiments as rse
from research import structural_encoding as se

OLD_RUN = nrc.RESULTS / "objective_index_20260924"
PREFIX = nrc.LEARNING["primary_prefix"]
TRAINING = nrc.LEARNING["training_count"]


def manifest_fixtures(manifest_path: Path) -> List[dict]:
    manifest = json.loads(Path(manifest_path).read_text())
    if manifest["status"] != "PASS" or manifest.get("collision_block"):
        raise RuntimeError(f"{manifest_path}: fixtures are {manifest['status']}")
    return manifest["fixtures"]


def training_draw(identities: Sequence[str], fixture_sha256: str) -> List[str]:
    ordered = sorted(identities)
    if len(ordered) < TRAINING:
        raise ValueError(f"only {len(ordered)} feasible objects")
    rng = random.Random(nrc.stable_seed([nrc.SEED_TRAINING_DRAW, fixture_sha256]))
    return rng.sample(ordered, TRAINING)


def design(fixture_dir: Path, fixture: dict, out_dir: Path) -> dict:
    """Training draw, common pool, held-out labels and sensitivity of one fixture."""

    fixture_dir, out_dir = Path(fixture_dir), Path(out_dir)
    record_path, oracle_path = fixture_dir / "record.json", fixture_dir / "oracle.json"
    if oc.file_sha256(record_path) != fixture["record_sha256"]:
        raise ValueError(f"{fixture['fixture_id']}: record hash differs from manifest")
    if oc.file_sha256(oracle_path) != fixture["oracle_sha256"]:
        raise ValueError(f"{fixture['fixture_id']}: oracle hash differs from manifest")
    record = json.loads(record_path.read_text())
    oracle = json.loads(oracle_path.read_text())
    domain = se.Domain.from_record(record)
    domain_sha256 = domain.digest()
    if domain_sha256 != oracle["domain_sha256"]:
        raise ValueError("domain digest differs from the oracle's")
    bits = se.layout(domain, nrr.sr.CODEC).width
    by_identity = {item["identity"]: item for item in oracle["feasible"]}
    by_index = {int(item["structural_rank_index"]): item for item in oracle["feasible"]}
    if len(by_identity) != len(oracle["feasible"]) or len(by_index) != len(by_identity):
        raise ValueError("oracle identities or indices are not distinct")
    fixture_sha256 = fixture["record_sha256"]
    drawn = training_draw(list(by_identity), fixture_sha256)
    training = sorted((int(by_identity[i]["structural_rank_index"]), by_identity[i]["product"])
                      for i in drawn)
    indices = [i for i, _ in training]
    products = [p for _, p in training]
    pool = nrr.common_pool(bits, indices, products, domain_sha256)
    threshold = pool["threshold"]
    training_set = set(drawn)
    entries = []
    decode_mismatches = 0
    useful_identities = set()
    for index in pool["pool"]:
        item = by_index.get(index)
        decoded = se.decode(domain, index, nrr.sr.CODEC)
        complete = decoded.status == se.COMPLETE
        if complete != (item is not None) or (
                complete and se.canonical_json(decoded.compilation) != item["identity"]):
            decode_mismatches += 1
        if item is None:
            entries.append({"index": str(index), "label": "not_feasible", "status":
                            decoded.status})
            continue
        heldout = item["identity"] not in training_set
        useful = heldout and item["product"] <= threshold
        if useful:
            useful_identities.add(item["identity"])
        entries.append({"index": str(index), "label": "feasible", "heldout": heldout,
                        "product": item["product"], "identity_sha256": hashlib.sha256(
                            item["identity"].encode()).hexdigest(), "useful": useful})
    n, m = len(pool["pool"]), len(useful_identities)
    k = min(PREFIX, n)
    best_max, best_min = min(k, m), max(0, k - (n - m))
    min_train = min(products)
    heldout_products = [item["product"] for ident, item in by_identity.items()
                        if ident not in training_set]
    labels_all = [1 if p <= threshold else 0 for p in products]
    sensitivity = {
        "N_pool": n, "M_useful": m, "k": k, "max_count": best_max, "min_count": best_min,
        "range": best_max - best_min, "informative": best_max - best_min > 0,
        "constant_labels": len(set(labels_all)) == 1, "no_useful_pool_objects": m == 0,
        "short_pool": n < PREFIX, "training_positives": sum(labels_all),
        "heldout_below_training_minimum": sum(p < min_train for p in heldout_products),
        "pool_feasible_heldout": sum(1 for e in entries if e.get("heldout")),
        "pool_not_feasible": sum(1 for e in entries if e["label"] == "not_feasible"),
        "decode_mismatches": decode_mismatches}
    ranker_input = {"fixture_id": fixture["fixture_id"], "bits": bits,
                    "domain_sha256": domain_sha256,
                    "training_indices": [str(i) for i in indices],
                    "training_products": products, "pool": [str(i) for i in pool["pool"]],
                    "pool_sha256": pool["pool_sha256"]}
    evaluator = {"fixture_id": fixture["fixture_id"], "family": fixture["family"],
                 "fixture_sha256": fixture_sha256, "domain_sha256": domain_sha256,
                 "n_feasible": len(by_identity), "n_heldout": len(heldout_products),
                 "training_identities_sha256": [hashlib.sha256(i.encode()).hexdigest()
                                                for i in sorted(drawn)],
                 "elite_threshold": threshold, "min_training_J": min_train,
                 "min_heldout_J": min(heldout_products) if heldout_products else None,
                 "pool_entries": entries, "sensitivity": sensitivity,
                 "pool": {k2: pool[k2] for k2 in ("hamming", "random", "draws",
                                                  "universe_exhausted", "size", "pool_sha256")}}
    out = out_dir / fixture["fixture_id"]
    out.mkdir(parents=True, exist_ok=True)
    ranker_sha = oc.write_immutable_json(out / "RANKER_INPUT.json", ranker_input)
    evaluator_sha = oc.write_immutable_json(out / "EVALUATOR.json", evaluator)
    return {"fixture_id": fixture["fixture_id"], "family": fixture["family"],
            "program_sha256": fixture["program_sha256"], "seed": fixture["seed"],
            "ranker_input": str((out / "RANKER_INPUT.json").resolve()),
            "ranker_input_sha256": ranker_sha, "evaluator_sha256": evaluator_sha,
            "sensitivity": sensitivity}


def design_gate(designs: Sequence[dict], minimum: int, per_family_minimum: int,
                families_required: Sequence[str]) -> dict:
    informative = [d for d in designs if d["sensitivity"]["informative"]]
    by_family = collections.Counter(d["family"] for d in informative)
    ok = (len(informative) >= minimum
          and all(by_family.get(f, 0) >= per_family_minimum for f in families_required))
    return {"fixtures": len(designs), "informative": len(informative),
            "informative_by_family": dict(sorted(by_family.items())),
            "minimum": minimum, "per_family_minimum": per_family_minimum,
            "status": "PASS" if ok else "DESIGN_INSUFFICIENT",
            "uninformative": [{"fixture_id": d["fixture_id"], **{k: d["sensitivity"][k] for k in (
                "N_pool", "M_useful", "range", "constant_labels", "no_useful_pool_objects",
                "short_pool")}} for d in designs if not d["sensitivity"]["informative"]]}


# --------------------------------------------------------------------------
# Scoring (evaluator only)
# --------------------------------------------------------------------------


def score(ordered: Sequence[str], evaluator: dict) -> dict:
    labels = {e["index"]: e for e in evaluator["pool_entries"]}
    if sorted(ordered) != sorted(labels):
        raise ValueError("ordering is not a permutation of the frozen pool")
    prefix = list(ordered[:PREFIX])
    useful = set()
    heldout_js = []
    for index in prefix:
        entry = labels[index]
        if entry.get("useful"):
            useful.add(entry["identity_sha256"])
        if entry.get("heldout"):
            heldout_js.append(entry["product"])
    best = min(heldout_js) if heldout_js else None
    return {"yield": len(useful) / PREFIX, "useful_distinct": len(useful),
            "positions": len(prefix), "best_heldout_J_in_prefix": best,
            "best_J_over_training_minimum": (best / evaluator["min_training_J"]
                                             if best is not None else None),
            "saturated": (evaluator["min_heldout_J"] is None
                          or evaluator["min_heldout_J"] >= evaluator["min_training_J"])}


def contrasts(scores: Dict[str, Dict[str, float]], families: Dict[str, str]) -> dict:
    """Paired yield differences tree minus control; 98.33% family-stratified intervals."""

    randoms = [o for o in nrr.ORDERINGS if o.startswith("random_")]
    out = {}
    passed = True
    for name, control in (("tree_minus_hamming", lambda s: s["hamming"]),
                          ("tree_minus_random_mean",
                           lambda s: statistics.mean(s[r] for r in randoms)),
                          ("tree_minus_shuffled_tree", lambda s: s["shuffled_tree"])):
        per_fixture = {f: s["tree"] - control(s) for f, s in scores.items()}
        boot = rse.family_stratified_bootstrap(per_fixture, families, nrc.RESAMPLES,
                                               nrc.SEED_BOOTSTRAP,
                                               list(nrc.LEARNING_PERCENTILES))
        low, high = boot["intervals"][f"{nrc.LEARNING_PERCENTILES[0]}-"
                                      f"{nrc.LEARNING_PERCENTILES[1]}"]
        point = boot["point_estimate"]
        ok = low > 0 and point >= nrc.LEARNING["minimum_yield_difference"]
        passed &= ok
        out[name] = {"estimate": point, "interval_98_333": [low, high], "fixtures":
                     len(per_fixture), "positive": sum(v > 0 for v in per_fixture.values()),
                     "zero": sum(v == 0 for v in per_fixture.values()),
                     "negative": sum(v < 0 for v in per_fixture.values()), "passes": ok}
    out["mechanism_signal"] = "PASS" if passed else "FAIL_OR_INCONCLUSIVE"
    return out


def mean_or_none(values: List[Optional[float]]) -> Optional[float]:
    kept = [v for v in values if v is not None and not math.isnan(v)]
    return statistics.mean(kept) if kept else None
