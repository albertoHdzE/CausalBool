"""Fixture qualification for the objective-index protocol 1.0 (section 8).

Inherits ONLY the deterministic construction/qualification recipe of the
superseded optimization plan (its section 6), with the substitutions this
protocol makes: development pool 920000-920199 (three per family), evaluation
pool 930000-930399 (six per family), split seed 2026092503. Everything else --
bootstrap, producing orders, candidate tuples, the domain record, Cartesian
size, four-codec round trips, the split rule and the elite threshold -- is
called from ``optimization_fixtures``, the recipe's owner, not restated.

``qualify_pool`` generalises the owner's loop by its pool bounds, quota and
split seed; ``optimization_fixtures.qualify_pool`` hard-codes them and belongs
to a frozen earlier release that must stay byte-identical. The parity run
recorded in THEORY/PRUNING evidence re-qualifies the old development pool with
the old parameters and compares the ledger with the old release byte for byte.

This module is evaluator-side. Learner code (``schema_ranker``) never imports it.
"""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Dict, List, Sequence

import machine

from research import optimization_common as oc
from research import optimization_fixtures as ofx
from research import structural_encoding as se
from research import structural_oracle as so


POOLS = {"development": (920000, 920199, 3), "evaluation": (930000, 930399, 6)}
SPLIT_SEED = 2026092503


def qualify_pool(cohort: str, out_dir: Path, collision_index: Dict[str, str],
                 other_pool_seeds: Sequence[int], first: int, last: int, quota: int,
                 split_seed: int) -> dict:
    """The recipe over one pool, written once with its complete ledger."""

    from tests_direct import generate_programs as gp

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
        facts, times, addresses, incumbent = ofx.bootstrap(program)
        orders = ofx.producing_orders(facts, times, addresses)
        candidates = []
        chosen = None
        for order_name, size, selected in ofx.candidate_tuples(orders):
            for radius in (1, 2):
                identifier = f"{cohort}:{seed}:{order_name}:{size}:r{radius}"
                record = ofx.domain_record(identifier, family, program, facts, times, addresses,
                                           incumbent, selected, radius)
                size_cartesian = ofx.cartesian(record)
                entry = {"candidate": identifier, "order": order_name, "size": size,
                         "selected": list(selected), "radius": radius,
                         "cartesian": size_cartesian}
                candidates.append(entry)
                if size_cartesian > ofx.CARTESIAN_MAX:
                    entry.update(status="REJECTED", reason="cartesian_above_65536")
                    continue
                domain = se.Domain.from_record(record)
                width = se.layout(domain, "structural_rank").width
                entry["structural_rank_width"] = width
                started = time.perf_counter()
                enumeration = so.enumerate_feasible(record, ofx.CARTESIAN_MAX)
                entry["oracle_seconds"] = time.perf_counter() - started
                feasible = enumeration["feasible"]
                products = sorted({item["product"] for item in feasible})
                entry.update(feasible=len(feasible), distinct_products=len(products),
                             product_range=[products[0], products[-1]] if products else None,
                             oracle_rejected=enumeration["rejected"])
                reasons = []
                if not ofx.FEASIBLE_MIN <= len(feasible) <= ofx.FEASIBLE_MAX:
                    reasons.append("feasible_count_outside_40_512")
                if len(products) < ofx.DISTINCT_PRODUCTS_MIN:
                    reasons.append("fewer_than_two_distinct_J")
                if width > ofx.WIDTH_MAX:
                    reasons.append("structural_rank_width_above_20")
                if reasons:
                    entry.update(status="REJECTED", reason=",".join(reasons))
                    continue
                started = time.perf_counter()
                trips = ofx.round_trips(domain, feasible)
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
        parts = ofx.split([item["identity"] for item in enumeration["feasible"]], split_seed)
        split_sha = oc.write_immutable_json(fixture_dir / "split.json", parts)
        products = {item["identity"]: item["product"] for item in enumeration["feasible"]}
        train_products = [products[i] for i in parts["train"]]
        test_products = [products[i] for i in parts["test"]]
        fixture = {"fixture_id": fixture_id, "cohort": cohort, "seed": seed, "family": family,
                   "semantic_sha256": semantic, "program_sha256": gp.program_digest(program),
                   "domain_sha256": oracle_payload["domain_sha256"], "candidate": entry,
                   "record_sha256": record_sha, "oracle_sha256": oracle_sha,
                   "split_sha256": split_sha, "split_seed": split_seed,
                   "n_feasible": len(enumeration["feasible"]),
                   "n_train": len(parts["train"]), "n_validation": len(parts["validation"]),
                   "n_test": len(parts["test"]), "bits": entry["structural_rank_width"],
                   "min_training_J": min(train_products),
                   "elite_threshold": ofx.elite_threshold(train_products),
                   "distinct_products": entry["distinct_products"],
                   # Design descriptors, from the frozen oracle/split only: whether
                   # any test object lies strictly below the best training label.
                   "test_headroom_objects": sum(1 for p in test_products
                                                if p < min(train_products))}
        accepted[family].append(fixture)
        row.update(status="ACCEPTED", fixture=fixture)
        oc.append_row(ledger_path, row)
    filled = {family: len(items) for family, items in accepted.items()}
    status = "PASS" if all(n == quota for n in filled.values()) else "DESIGN_INSUFFICIENT"
    manifest = {"cohort": cohort, "pool": [first, last], "quota_per_family": quota,
                "split_seed": split_seed, "filled": filled, "status": status,
                "collisions": collisions, "collision_block": bool(collisions),
                "fixtures": [f for family in gp.FAMILIES for f in accepted[family]],
                "ledger_sha256": oc.file_sha256(ledger_path)}
    oc.write_immutable_json(out_dir / "MANIFEST.json", manifest)
    return manifest


def collision_index(extra: Dict[str, Sequence[int]]) -> Dict[str, str]:
    """Public, historical and every protocol cohort (``optimization_fixtures`` owner)."""

    return ofx.existing_semantics(extra)


def qualify(run: Path, cohort: str) -> dict:
    """Oracle-only qualification of one of this protocol's pools."""

    first, last, quota = POOLS[cohort]
    other = POOLS["evaluation" if cohort == "development" else "development"]
    index = collision_index({
        "old_development": range(800000, 800100),
        "old_fresh_compiler": range(810000, 810200),
        "old_fixture_development_pool": range(820000, 820200),
        "old_fixture_evaluation_pool": range(830000, 830400),
        "compiler_evaluation": range(910000, 910200),
    })
    started = time.perf_counter()
    manifest = qualify_pool(cohort, Path(run) / "fixtures" / cohort, index,
                            range(other[0], other[1] + 1), first, last, quota, SPLIT_SEED)
    oc.append_row(Path(run) / "fixtures" / "qualification_runs.jsonl",
                  {"cohort": cohort, "seconds": time.perf_counter() - started,
                   "status": manifest["status"], "filled": manifest["filled"],
                   "collisions": len(manifest["collisions"]),
                   "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    return manifest


def parity_with_owner(tmp: Path) -> dict:
    """Re-qualify the OLD development pool with the OLD parameters; compare ledgers.

    Guards the generalised loop against drift from ``optimization_fixtures``:
    every ledger line and every fixture file must equal the old release's bytes.
    """

    old = oc.RESULTS / "optimization_20260924" / "fixtures" / "development"
    index = ofx.existing_semantics({"old_development": range(800000, 800100),
                                    "compiler_evaluation": range(810000, 810200)})
    manifest = qualify_pool("development", Path(tmp), index, range(830000, 830400),
                            820000, 820199, 3, ofx.SPLIT_SEED)

    def strip(line: str) -> dict:
        row = json.loads(line)
        for candidate in row.get("candidates", []):
            candidate.pop("oracle_seconds", None)
            candidate.pop("round_trip_seconds", None)
        if "fixture" in row:
            row["fixture"].pop("split_seed", None)
            row["fixture"].pop("test_headroom_objects", None)
            row["fixture"]["candidate"].pop("oracle_seconds", None)
            row["fixture"]["candidate"].pop("round_trip_seconds", None)
            row["fixture"].pop("oracle_sha256", None)
        return row

    new_lines = [strip(x) for x in (Path(tmp) / "FIXTURE_QUALIFICATION.jsonl").read_text().splitlines()]
    old_lines = [strip(x) for x in (old / "FIXTURE_QUALIFICATION.jsonl").read_text().splitlines()]
    files_equal = 0
    files_checked = 0
    for fixture in manifest["fixtures"]:
        for name in ("record.json", "split.json", "oracle.json"):
            files_checked += 1
            a = json.loads((Path(tmp) / fixture["fixture_id"] / name).read_text())
            b = json.loads((old / fixture["fixture_id"] / name).read_text())
            if name == "oracle.json":
                a.pop("oracle_seconds", None)
                b.pop("oracle_seconds", None)
            files_equal += a == b
    return {"ledger_lines": len(new_lines), "ledger_equal_modulo_timings": new_lines == old_lines,
            "files_checked": files_checked, "files_equal": files_equal,
            "status": "PASS" if new_lines == old_lines and files_checked
            and files_equal == files_checked else "FAIL"}
