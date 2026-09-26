"""Fixture construction and oracle-only qualification (protocol 1.0, section 6).

The recipe is fixed before either proposal learner runs and consults no model
or control outcome. For every seed in ascending order:

1. generate the program with the unchanged ``additional_program`` and obtain
   the frozen direct bootstrap;
2. order producing operations three ways -- ascending ID, latest issue first
   (ID tie break), descending allocated end address (producer ID tie break);
3. candidate tuples, deduplicated in first-seen order: for each order, its
   first two then its first three producing operations;
4. each tuple at time radius 1 then 2 (incumbent +/- radius clipped to
   ``[0, horizon-1]``), with every other time fixed; each selected result's
   address domain is the sorted union of its incumbent address and the first
   four legal aligned bases in ``[0, 256-width]``; every other address fixed;
5. skip a Cartesian product above 65,536 before enumeration; otherwise
   enumerate it exhaustively with the independent oracle.

The FIRST candidate with a completed oracle, 40-512 feasible objects, at least
two distinct J values and a structural_rank width of at most 20 qualifies the
seed. Every candidate and rejection is retained in order. A family stops
accepting once its quota is filled; later seeds are logged as not needed.

The oracle enumeration, the structural_rank index of every feasible object and
the train/validation/test split are written once per accepted fixture into an
evaluator-only cache. Learner code never imports this module.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import random
import time
from typing import Dict, List, Optional, Sequence, Tuple

import machine

import direct_compiler as dcomp
import direct_contract as dc

from research import optimization_common as oc
from research import run_structural_experiments as rse
from research import structural_encoding as se
from research import structural_oracle as so


CARTESIAN_MAX = 65_536
FEASIBLE_MIN = 40
FEASIBLE_MAX = 512
WIDTH_MAX = 20
DISTINCT_PRODUCTS_MIN = 2
SPLIT_SEED = 2026092402
POOLS = {"development": (820000, 820199, 3), "evaluation": (830000, 830399, 6)}


def bootstrap(program: dict) -> Tuple[dc.ProgramFacts, Dict[int, int], Dict[str, int], dict]:
    facts = dc.derive(program)
    compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
    times = se.issue_cycles_of(program, compiled["bundles"])
    addresses = dict(compiled["scratch"])
    return facts, times, addresses, dc.compilation(facts, times, addresses)


def producing_orders(facts: dc.ProgramFacts, times: Dict[int, int],
                     addresses: Dict[str, int]) -> Dict[str, List[int]]:
    producers = [op for op in range(facts.count) if facts.dest[op] is not None]

    def end(op: int) -> int:
        name = facts.dest[op]
        return addresses[name] + facts.width[name]

    return {
        "ascending_id": sorted(producers),
        "latest_issue": sorted(producers, key=lambda op: (-times[op], op)),
        "highest_end_address": sorted(producers, key=lambda op: (-end(op), op)),
    }


def candidate_tuples(orders: Dict[str, List[int]]) -> List[Tuple[str, int, Tuple[int, ...]]]:
    out: List[Tuple[str, int, Tuple[int, ...]]] = []
    seen = set()
    for name in ("ascending_id", "latest_issue", "highest_end_address"):
        for size in (2, 3):
            chosen = orders[name][:size]
            if len(chosen) < size:
                continue
            selected = tuple(sorted(chosen))
            if selected in seen:
                continue
            seen.add(selected)
            out.append((name, size, selected))
    return out


def domain_record(identifier: str, family: str, program: dict, facts: dc.ProgramFacts,
                  times: Dict[int, int], addresses: Dict[str, int], incumbent: dict,
                  selected: Sequence[int], radius: int) -> dict:
    selected = tuple(sorted(selected))
    time_domains = {
        str(op): list(range(max(0, times[op] - radius), min(facts.horizon - 1, times[op] + radius) + 1))
        for op in selected
    }
    address_domains = {}
    for op in selected:
        name = facts.dest[op]
        legal = rse.physical_address_domain(facts, name, machine.SCRATCH_WORDS)
        address_domains[name] = sorted(set([addresses[name]] + legal[:4]))
    return {
        "id": identifier,
        "family": family,
        "program": program,
        "selected_operations": list(selected),
        "time_domains": time_domains,
        "address_domains": address_domains,
        "fixed_times": {str(op): times[op] for op in range(facts.count) if op not in selected},
        "fixed_addresses": {name: addresses[name] for name in facts.value_names
                            if name not in address_domains},
        "incumbent": incumbent,
        "target": None,
    }


def cartesian(record: dict) -> int:
    size = 1
    for values in list(record["time_domains"].values()) + list(record["address_domains"].values()):
        size *= len(values)
    return size


def round_trips(domain: se.Domain, feasible: Sequence[dict]) -> dict:
    """Every feasible object through all four codecs, both directions."""

    failures: List[dict] = []
    indices: Dict[str, int] = {}
    checked = 0
    for entry in feasible:
        compilation = json.loads(entry["identity"])
        for codec in se.CODECS:
            checked += 1
            try:
                index = se.encode(domain, compilation, codec)
                result = se.decode(domain, index, codec)
            except (se.DomainError, se.CodecDefect) as exc:
                failures.append({"identity": entry["identity"], "codec": codec,
                                 "error": f"{type(exc).__name__}: {exc}"})
                continue
            if result.status != se.COMPLETE or se.canonical_json(result.compilation) != entry["identity"]:
                failures.append({"identity": entry["identity"], "codec": codec,
                                 "error": f"decode status {result.status} or identity mismatch"})
                continue
            if codec == "structural_rank":
                indices[entry["identity"]] = index
    return {"checked": checked, "failures": failures, "structural_rank_index": indices}


def split(identities: Sequence[str], seed: int = SPLIT_SEED) -> Dict[str, List[str]]:
    """Canonical identity sort, then Random(seed) permutation reinitialised here."""

    ordered = sorted(identities)
    rng = random.Random(seed)
    rng.shuffle(ordered)
    n = len(ordered)
    n_train, n_validation = n // 2, n // 4
    return {"train": ordered[:n_train], "validation": ordered[n_train:n_train + n_validation],
            "test": ordered[n_train + n_validation:]}


def elite_threshold(products: Sequence[int], fraction: float = 0.1) -> int:
    """The ceil(0.1 n)-th order statistic of the training labels, ties included."""

    ordered = sorted(products)
    return ordered[max(1, math.ceil(fraction * len(ordered))) - 1]


def existing_semantics(extra_cohorts: Dict[str, Sequence[int]]) -> Dict[str, str]:
    """Semantic digests of every public, historical and protocol cohort."""

    from tests_direct import generate_programs as gp

    existing: Dict[str, str] = {}
    for label, programs in (("public", gp.public_programs()),
                            ("regression", gp.regression_programs()),
                            ("additional", gp.additional_programs()),
                            ("stress", gp.stress_programs())):
        for program in programs:
            existing.setdefault(se.program_semantic_digest(program), f"{label}:{program['name']}")
    for path in sorted((oc.ROOT / ".reference" / "programs").glob("*.json")):
        existing.setdefault(se.program_semantic_digest(machine.load_program(path)),
                            f"public_file:{path.name}")
    for label, seeds in extra_cohorts.items():
        for seed in seeds:
            digest = se.program_semantic_digest(gp.additional_program(seed))
            existing.setdefault(digest, f"{label}:{seed}")
    return existing


def qualify_pool(cohort: str, out_dir: Path, collision_index: Dict[str, str],
                 other_pool_seeds: Sequence[int]) -> dict:
    """Run the fixed recipe over one pool and write its complete ledger."""

    from tests_direct import generate_programs as gp

    first, last, quota = POOLS[cohort]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = out_dir / "FIXTURE_QUALIFICATION.jsonl"
    if ledger_path.exists():
        raise FileExistsError(f"{ledger_path} exists; qualification is written once")
    other_semantics = {se.program_semantic_digest(gp.additional_program(s)): s
                       for s in other_pool_seeds}
    accepted: Dict[str, List[dict]] = {family: [] for family in gp.FAMILIES}
    seen_semantics: Dict[str, int] = {}
    collisions: List[dict] = []
    for seed in range(first, last + 1):
        family = gp.FAMILIES[seed % 5]
        if len(accepted[family]) >= quota:
            oc.append_row(ledger_path, {"cohort": cohort, "seed": seed, "family": family,
                                        "status": "NOT_NEEDED",
                                        "reason": "family quota already filled"})
            continue
        program = gp.additional_program(seed)
        machine.validate_program(program)
        semantic = se.program_semantic_digest(program)
        against = collision_index.get(semantic) or (
            f"other_fixture_pool:{other_semantics[semantic]}" if semantic in other_semantics
            else None) or (f"same_pool:{seen_semantics[semantic]}"
                           if semantic in seen_semantics else None)
        seen_semantics.setdefault(semantic, seed)
        if against:
            collisions.append({"seed": seed, "against": against})
            oc.append_row(ledger_path, {"cohort": cohort, "seed": seed, "family": family,
                                        "status": "REJECTED_COLLISION", "against": against,
                                        "semantic_sha256": semantic})
            continue
        facts, times, addresses, incumbent = bootstrap(program)
        orders = producing_orders(facts, times, addresses)
        candidates = []
        chosen = None
        for order_name, size, selected in candidate_tuples(orders):
            for radius in (1, 2):
                identifier = f"{cohort}:{seed}:{order_name}:{size}:r{radius}"
                record = domain_record(identifier, family, program, facts, times, addresses,
                                       incumbent, selected, radius)
                size_cartesian = cartesian(record)
                entry = {"candidate": identifier, "order": order_name, "size": size,
                         "selected": list(selected), "radius": radius,
                         "cartesian": size_cartesian}
                candidates.append(entry)
                if size_cartesian > CARTESIAN_MAX:
                    entry.update(status="REJECTED", reason="cartesian_above_65536")
                    continue
                domain = se.Domain.from_record(record)
                width = se.layout(domain, "structural_rank").width
                entry["structural_rank_width"] = width
                started = time.perf_counter()
                enumeration = so.enumerate_feasible(record, CARTESIAN_MAX)
                entry["oracle_seconds"] = time.perf_counter() - started
                feasible = enumeration["feasible"]
                products = sorted({item["product"] for item in feasible})
                entry.update(feasible=len(feasible), distinct_products=len(products),
                             product_range=[products[0], products[-1]] if products else None,
                             oracle_rejected=enumeration["rejected"])
                reasons = []
                if not FEASIBLE_MIN <= len(feasible) <= FEASIBLE_MAX:
                    reasons.append("feasible_count_outside_40_512")
                if len(products) < DISTINCT_PRODUCTS_MIN:
                    reasons.append("fewer_than_two_distinct_J")
                if width > WIDTH_MAX:
                    reasons.append("structural_rank_width_above_20")
                if reasons:
                    entry.update(status="REJECTED", reason=",".join(reasons))
                    continue
                started = time.perf_counter()
                trips = round_trips(domain, feasible)
                entry["round_trip_seconds"] = time.perf_counter() - started
                entry["round_trips_checked"] = trips["checked"]
                if trips["failures"]:
                    entry.update(status="REJECTED", reason="codec_round_trip_failure",
                                 round_trip_failures=trips["failures"][:10])
                    continue
                entry["status"] = "QUALIFIED"
                chosen = (record, domain, enumeration, trips, entry)
                break
            if chosen:
                break
        row = {"cohort": cohort, "seed": seed, "family": family, "semantic_sha256": semantic,
               "program_sha256": gp.program_digest(program), "candidates": candidates}
        if chosen is None:
            row.update(status="REJECTED", reason="no candidate qualified")
            oc.append_row(ledger_path, row)
            continue
        record, domain, enumeration, trips, entry = chosen
        fixture_id = f"{cohort}_{seed}"
        fixture_dir = out_dir / fixture_id
        fixture_dir.mkdir(parents=True, exist_ok=False)
        record = dict(record, id=fixture_id)
        record_sha = oc.write_immutable_json(fixture_dir / "record.json", record)
        index_of = trips["structural_rank_index"]
        oracle_payload = {
            "fixture_id": fixture_id,
            "domain_sha256": se.Domain.from_record(record).digest(),
            "cartesian": entry["cartesian"],
            "feasible": [dict(item, structural_rank_index=str(index_of[item["identity"]]))
                         for item in enumeration["feasible"]],
            "oracle_rejected": enumeration["rejected"],
            "oracle_seconds": entry["oracle_seconds"],
            "bits": entry["structural_rank_width"],
        }
        oracle_sha = oc.write_immutable_json(fixture_dir / "oracle.json", oracle_payload)
        parts = split([item["identity"] for item in enumeration["feasible"]])
        split_sha = oc.write_immutable_json(fixture_dir / "split.json", parts)
        products = {item["identity"]: item["product"] for item in enumeration["feasible"]}
        train_products = [products[i] for i in parts["train"]]
        fixture = {"fixture_id": fixture_id, "cohort": cohort, "seed": seed, "family": family,
                   "semantic_sha256": semantic, "program_sha256": gp.program_digest(program),
                   "domain_sha256": oracle_payload["domain_sha256"], "candidate": entry,
                   "record_sha256": record_sha, "oracle_sha256": oracle_sha,
                   "split_sha256": split_sha, "n_feasible": len(enumeration["feasible"]),
                   "n_train": len(parts["train"]), "n_validation": len(parts["validation"]),
                   "n_test": len(parts["test"]), "bits": entry["structural_rank_width"],
                   "min_training_J": min(train_products),
                   "elite_threshold": elite_threshold(train_products),
                   "distinct_products": entry["distinct_products"]}
        accepted[family].append(fixture)
        row.update(status="ACCEPTED", fixture=fixture)
        oc.append_row(ledger_path, row)
    filled = {family: len(items) for family, items in accepted.items()}
    status = "PASS" if all(n == quota for n in filled.values()) else "FIXTURE_DESIGN_INSUFFICIENT"
    manifest = {"cohort": cohort, "pool": [first, last], "quota_per_family": quota,
                "filled": filled, "status": status, "collisions": collisions,
                "collision_block": bool(collisions),
                "fixtures": [f for family in gp.FAMILIES for f in accepted[family]],
                "ledger_sha256": oc.file_sha256(ledger_path)}
    oc.write_immutable_json(out_dir / "MANIFEST.json", manifest)
    return manifest
