"""Independent checks over a phase 2 run, and independent gate recomputation.

This checker never trusts the run. It derives the expected membership, seeds,
denominators and thresholds from the *locked* inputs, recomputes every gate from
the raw rows, and refuses a report-provided denominator, seed or resample count
as policy. A success banner in the run establishes nothing here.

Two report fields are deliberately distinct, because conflating them is the
failure this exists to stop:

* ``artifacts_complete`` -- the evidence is present, internally consistent and
  matches the frozen inputs;
* ``scientific_success`` -- the hypotheses actually advanced.

A reproducible null result has the first true and the second false. It is a
complete and legitimate outcome.

Exit codes follow the contract: 0 complete with valid evidence, 1 a correctness
or integrity failure, 2 missing inputs or incomplete mandatory evidence.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import machine

import schema_index as si

from research import structural_encoding as se
from research import structural_models as sm
from research import structural_oracle as so
from research import run_structural_experiments as runner


EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2

# The oracle's whole value is deciding membership by a path that shares no
# feasibility predicate with the candidate. These are the modules it may not
# reach, directly or transitively.
ORACLE_FORBIDDEN = (
    "research.structural_encoding",
    "research.structural_search",
    "research.structural_models",
    "direct_contract",
    "direct_constraints",
    "direct_compiler",
    "schema_index",
)

# Names whose single owner is elsewhere. A *definition* of one of these inside
# ``research/`` is a second owner.
OWNED_ELSEWHERE = {
    "Cube": "schema_index",
    "intersect": "schema_index",
    "difference": "schema_index",
    "normalise_cover": "schema_index",
    "universe_mask": "schema_index",
    "Budget": "schema_index",
    "Meter": "schema_index",
    "check_compilation": "machine",
    "check_case": "machine",
    "scratch_footprint": "machine",
    "serial_compile": "machine",
    "lifetimes": "direct_contract",
    "assemble_bundles": "direct_contract",
    "footprint": "direct_contract",
    "check_feasible": "direct_contract",
    "targets_for": "direct_optimizer",
    "windows_for": "direct_optimizer",
    "additional_program": "tests_direct.generate_programs",
}

MACHINE_CONSTANTS = {"VLEN": 8, "SCRATCH_WORDS": 256, "ENGINE_LIMITS": None, "OP_SPECS": None}


class Finding(Exception):
    """A check failed. Its message is the reason, and it is always retained."""


class Checker:
    """One independent pass over one run directory."""

    def __init__(self, run_root: Path, contract_dir: Path) -> None:
        self.root = Path(run_root)
        if not self.root.is_dir():
            raise Finding(f"run directory {run_root} does not exist")
        self.contract = runner.Contract(contract_dir)
        self.findings: List[dict] = []
        # A gate that ran and could not be established is *incomplete mandatory
        # evidence*, not a correctness or integrity failure. The contract gives
        # the two different exit codes, so they are kept in different lists; a
        # reviewer reading exit 1 must be able to conclude something is broken.
        self.incompletes: List[dict] = []
        self.checks: List[dict] = []

    # -- bookkeeping -------------------------------------------------------

    def ok(self, name: str, detail: object = None) -> None:
        self.checks.append({"check": name, "status": "PASS", "detail": detail})

    def fail(self, name: str, reason: str, detail: object = None) -> None:
        self.findings.append({"check": name, "reason": reason, "detail": detail})
        self.checks.append({"check": name, "status": "FAIL", "detail": reason})

    def inconclusive(self, name: str, reason: str, detail: object = None) -> None:
        self.incompletes.append({"check": name, "reason": reason, "detail": detail})
        self.checks.append({"check": name, "status": "INCONCLUSIVE", "detail": reason})

    def load(self, relative: str) -> Optional[object]:
        path = self.root / relative
        if not path.is_file():
            return None
        text = path.read_text()
        if not text.strip():
            return None
        if relative.endswith(".jsonl"):
            return runner.read_jsonl(path)
        return json.loads(text)

    def require(self, relative: str) -> object:
        payload = self.load(relative)
        if payload is None:
            raise Finding(f"required artifact {relative} is missing or empty")
        return payload

    # -- structure and provenance -----------------------------------------

    def check_structure(self) -> dict:
        required = ("manifest.json", "gates.json", "HANDOFF.md",
                    "OWNERSHIP.md", "PROOFS.md", "commands.jsonl")
        missing = [name for name in required if not (self.root / name).exists()]
        if missing:
            self.fail("structure.required_files", f"missing {missing}")
        else:
            self.ok("structure.required_files", list(required))
        for name in ("logs", "inputs"):
            if not (self.root / name).is_dir():
                self.fail("structure.directories", f"missing directory {name}")
        manifest = self.require("manifest.json")
        return manifest

    def check_provenance(self, manifest: dict) -> None:
        """Contract, plan, package and source hashes, recomputed from disk."""

        for name, recorded in sorted(manifest.get("contract_files", {}).items()):
            actual = runner.file_digest(self.contract.directory / name)
            if actual != recorded:
                self.fail(
                    "provenance.contract_file",
                    f"{name} hashes {actual}, the manifest recorded {recorded}",
                )
        plan = runner.file_digest(
            runner.ROOT / "plan" / "PHASE2_STRUCTURAL_ENCODING_PLAN.md"
        )
        if plan != manifest.get("plan_sha256"):
            self.fail("provenance.plan", "the scientific plan hash changed since the run")
        else:
            self.ok("provenance.plan", plan)

        snapshot = runner.source_snapshot()
        recorded = manifest.get("source_snapshot", {})
        for section in ("research", "tests", "production"):
            for name, digest in sorted(snapshot.get(section, {}).items()):
                if recorded.get(section, {}).get(name) != digest:
                    self.fail(
                        "provenance.source_snapshot",
                        f"{section}/{name} does not match the recorded snapshot",
                    )
        if recorded.get("snapshot_sha256") != snapshot["snapshot_sha256"]:
            self.fail("provenance.snapshot_digest", "the source snapshot digest changed")
        else:
            self.ok("provenance.snapshot_digest", snapshot["snapshot_sha256"])

        locks = self.contract.verify_locks()
        if locks["status"] != runner.PASS:
            self.fail("provenance.protected_files", "; ".join(locks["findings"][:5]))
        else:
            self.ok("provenance.protected_files", locks["checked"])

    def check_commands(self) -> None:
        commands = self.load("commands.jsonl") or []
        bad = [
            entry for entry in commands
            if entry.get("exit_code") not in (0, None) or entry.get("timed_out")
        ]
        self.ok("commands.recorded", {"count": len(commands), "nonzero_or_timed_out": len(bad)})

    # -- P0 ----------------------------------------------------------------

    def check_p0(self) -> Optional[dict]:
        summary = self.load("p0/summary.json")
        if summary is None:
            return None
        expected_ids = {record["id"] for record in self.contract.fixtures}
        actual_ids = {entry["id"] for entry in summary["fixtures"]}
        if actual_ids != expected_ids:
            self.fail(
                "p0.fixture_membership",
                f"missing {sorted(expected_ids - actual_ids)}, "
                f"extra {sorted(actual_ids - expected_ids)}",
            )
        else:
            self.ok("p0.fixture_membership", len(actual_ids))
        if len(summary["fixtures"]) != len(self.contract.fixtures):
            self.fail("p0.fixture_count", "a fixture was duplicated or dropped")

        for record in self.contract.fixtures:
            domain = se.Domain.from_record(record)
            entry = next(
                (item for item in summary["fixtures"] if item["id"] == record["id"]), None
            )
            if entry is None:
                continue
            if entry["domain_sha256"] != domain.digest():
                self.fail("p0.domain_digest", f"{record['id']} digest changed")
            if entry["cartesian_assignments"] != domain.cartesian_size():
                self.fail("p0.cartesian", f"{record['id']} Cartesian size is wrong")

        heldout = summary["heldout"]
        first = self.contract.protocol["heldout"]["seed_first"]
        last = self.contract.protocol["heldout"]["seed_last"]
        expected_seeds = set(range(first, last + 1))
        actual_seeds = {entry["seed"] for entry in heldout["programs"]}
        if actual_seeds != expected_seeds:
            self.fail(
                "p0.heldout_membership",
                f"missing {sorted(expected_seeds - actual_seeds)[:5]}, "
                f"extra {sorted(actual_seeds - expected_seeds)[:5]}",
            )
        else:
            self.ok("p0.heldout_membership", len(actual_seeds))
        if heldout["collisions"]:
            self.fail("p0.heldout_collisions", f"{len(heldout['collisions'])} collisions")

        # Regenerate a sample independently and compare semantic digests. A
        # renamed duplicate has the same semantic digest and is caught here.
        from tests_direct import generate_programs as gp

        for entry in heldout["programs"][:: max(1, len(heldout["programs"]) // 10)]:
            program = gp.additional_program(entry["seed"])
            if se.program_semantic_digest(program) != entry["semantic_sha256"]:
                self.fail(
                    "p0.heldout_provenance",
                    f"seed {entry['seed']} does not regenerate to its recorded digest",
                )
        digests = [entry["semantic_sha256"] for entry in heldout["programs"]]
        if len(set(digests)) != len(digests):
            self.fail("p0.heldout_distinct", "two held-out programs are semantically equal")
        else:
            self.ok("p0.heldout_distinct", len(digests))

        totals = summary.get("historical_optimiser_statuses", {})
        if totals.get("available") and totals.get("unaccounted") != 0:
            self.fail(
                "p0.status_accounting",
                f"{totals['unaccounted']} attempted queries are unaccounted for",
            )
        else:
            self.ok("p0.status_accounting", totals.get("status_totals"))
        return summary

    # -- P1 ----------------------------------------------------------------

    def check_p1(self) -> Optional[dict]:
        summary = self.load("p1/summary.json")
        if summary is None:
            return None
        sampling = self.contract.protocol["sampling"]

        for entry in summary["fixtures"]:
            record = next(
                item for item in self.contract.fixtures if item["id"] == entry["id"]
            )
            domain = se.Domain.from_record(record)
            enumeration = so.enumerate_feasible(
                record, self.contract.budgets["oracle_cartesian_max"]
            )
            if enumeration["feasible_count"] != entry["oracle_feasible"]:
                self.fail(
                    "p1.oracle_recount",
                    f"{entry['id']}: recounted {enumeration['feasible_count']} feasible "
                    f"objects, the run recorded {entry['oracle_feasible']}",
                )
            identities = {item["identity"] for item in enumeration["feasible"]}
            for codec, codec_entry in entry["codecs"].items():
                bits = se.layout(domain, codec).width
                if bits != codec_entry["bits"]:
                    self.fail("p1.bits", f"{entry['id']}/{codec}: recomputed B is {bits}")
                if codec_entry["round_trip_failure_count"]:
                    self.fail(
                        "p1.round_trip",
                        f"{entry['id']}/{codec}: {codec_entry['round_trip_failure_count']} "
                        "round-trip failures",
                    )
                if codec_entry["round_trips"] != len(identities):
                    self.fail(
                        "p1.round_trip_denominator",
                        f"{entry['id']}/{codec}: {codec_entry['round_trips']} round trips "
                        f"against {len(identities)} feasible objects",
                    )
                if codec_entry["exhausted"]:
                    counts = codec_entry["counts"]
                    total = sum(counts.values())
                    if total != (1 << bits):
                        self.fail(
                            "p1.universe_accounting",
                            f"{entry['id']}/{codec}: statuses total {total}, "
                            f"the universe is {1 << bits}",
                        )
                    if not codec_entry["set_equality"]:
                        self.fail(
                            "p1.set_equality",
                            f"{entry['id']}/{codec}: the codec's set is not the oracle's",
                        )
        if summary["defect_count"]:
            self.fail("p1.defects", f"{summary['defect_count']} codec defects retained")
        else:
            self.ok("p1.defects", 0)

        streams = self.load("p1/sampling_streams.jsonl") or []
        expected_streams = 2 * len(summary["public_coverage"])
        if len(streams) != expected_streams:
            self.fail(
                "p1.stream_membership",
                f"{len(streams)} streams recorded, {expected_streams} expected",
            )
        for stream in streams:
            total = (
                stream["complete"] + stream["invalid_code"]
                + stream["dead_end"] + stream["interrupted"]
            )
            if total != stream["attempts_drawn"]:
                self.fail(
                    "p1.stream_accounting",
                    f"{stream['program_name']}/{stream['stream']}: statuses total {total} "
                    f"against {stream['attempts_drawn']} draws -- an attempt was hidden",
                )
            if stream["attempts_drawn"] > stream["attempts_requested"]:
                self.fail("p1.stream_overdraw", "more attempts than the frozen request")
            if stream["seed"] not in (
                self.contract.seeds["raw_bits"], self.contract.seeds["option_paths"]
            ):
                self.fail("p1.stream_seed", f"stream used unfrozen seed {stream['seed']}")
        self.ok("p1.stream_accounting", len(streams))

        minimum = sampling["minimum_distinct_completed_per_program"]
        short = [
            entry["program"] for entry in summary["public_coverage"]
            if entry["distinct_complete_union"] < minimum
        ]
        if short:
            self.inconclusive(
                "p1.coverage",
                f"{len(short)} public programs below {minimum} distinct completions: {short}",
                {
                    "programs": short,
                    "consequence": (
                        "P1's public coverage requirement applies before P2-P5, so "
                        "those stages are correctly BLOCKED_BY_GATE. Revising the "
                        "domain or the sampling policy needs a lead amendment."
                    ),
                },
            )
        else:
            self.ok("p1.coverage", minimum)
        return summary

    # -- P2 ----------------------------------------------------------------

    def check_benchmark_rows(self, label: str, rows: Sequence[dict],
                             programs: Sequence[dict]) -> None:
        """Exact membership, from frozen policy rather than from the report."""

        budgets = self.contract.budgets["optimisation_seconds"]
        repetitions = self.contract.statistics["timing_repetitions"]
        unbudgeted = ("accepted_bootstrap", "accepted_default")
        budgeted = ("accepted_budgeted",) + runner.STRUCTURAL_ARMS
        expected = {
            se.canonical_json(key)
            for key in runner.expected_keys(
                programs, budgets, unbudgeted, budgeted, repetitions
            )
        }
        observed = [
            se.canonical_json(
                [row.get("program_sha256"), row.get("budget_seconds"), row.get("arm"),
                 row.get("search_seed"), row.get("repetition")]
            )
            for row in rows
        ]
        if len(observed) != len(set(observed)):
            self.fail(f"{label}.duplicate_rows", "a row identity appears more than once")
        missing = expected - set(observed)
        extra = set(observed) - expected
        if missing or extra:
            self.fail(
                f"{label}.membership",
                f"{len(missing)} missing and {len(extra)} unexpected rows",
                {"missing": sorted(missing)[:5], "extra": sorted(extra)[:5]},
            )
        else:
            self.ok(f"{label}.membership", len(expected))

        failed = [row for row in rows if row.get("failed_row")]
        if failed:
            self.fail(
                f"{label}.failed_rows",
                f"{len(failed)} failed rows are retained and block a success claim",
            )
        discrepancies = [row for row in rows if row.get("discrepancy_count", 0)]
        if discrepancies:
            self.fail(
                f"{label}.discrepancies",
                f"{len(discrepancies)} rows carry a validator discrepancy",
            )
        for row in rows:
            if row.get("failed_row"):
                continue
            for field in ("cycles", "scratch", "product", "cases"):
                value = row.get(field)
                if value is None or (isinstance(value, float) and not math.isfinite(value)):
                    self.fail(f"{label}.metrics", f"{field} is undefined in a completed row")
                    break
            if row.get("product") != (row.get("cycles") or 0) * (row.get("scratch") or 0):
                self.fail(f"{label}.objective", "C*S does not equal the recorded product")
            if row.get("cases", 0) <= 0:
                self.fail(f"{label}.cases", "a completed row validated zero cases")

    def check_p2(self, p0: Optional[dict]) -> Optional[dict]:
        summary = self.load("p2/summary.json")
        if summary is None:
            return None
        rows = self.load("p2/benchmark_rows.jsonl") or []
        if not rows:
            self.fail("p2.empty_scan", "no benchmark rows: an empty scan is never a pass")
            return summary
        if p0 is not None:
            self.check_benchmark_rows("p2", rows, p0["public"])

        for entry in summary["tiny_fixtures"]:
            record = next(
                item for item in self.contract.fixtures if item["id"] == entry["id"]
            )
            domain = se.Domain.from_record(record)
            bounds = runner.bound_admissibility(domain)
            if bounds["status"] == runner.FAIL:
                self.fail(
                    "p2.bound_admissibility",
                    f"{entry['id']}: a prefix bound exceeds a completion objective",
                )
            enumeration = so.enumerate_feasible(
                record, self.contract.budgets["oracle_cartesian_max"]
            )
            minimum = min(
                (item["product"] for item in enumeration["feasible"]), default=None
            )
            if minimum != entry["oracle_minimum_product"]:
                self.fail(
                    "p2.oracle_minimum",
                    f"{entry['id']}: recomputed minimum {minimum}, "
                    f"recorded {entry['oracle_minimum_product']}",
                )
            for arm, report in entry["arms"].items():
                if minimum is not None and report["best_product"] != minimum:
                    self.fail(
                        "p2.search_optimality",
                        f"{entry['id']}/{arm}: exhaustive search returned "
                        f"{report['best_product']} against an oracle minimum of {minimum}",
                    )
                if report["rejected_completions"]:
                    self.fail(
                        "p2.rejected_completions",
                        f"{entry['id']}/{arm}: a completed candidate was rejected",
                    )
        self.ok("p2.tiny_fixtures", len(summary["tiny_fixtures"]))
        self.check_intervals("p2", summary.get("comparisons", {}))
        return summary

    def check_intervals(self, label: str, comparisons: Dict[str, dict]) -> None:
        """Bootstrap policy comes from the protocol, never from the report."""

        stats = self.contract.statistics
        for name, entry in sorted(comparisons.items()):
            interval = entry.get("interval") or {}
            if interval.get("status") != runner.PASS:
                continue
            if interval.get("seed") != self.contract.seeds["bootstrap"]:
                self.fail(
                    f"{label}.bootstrap_seed",
                    f"{name} used seed {interval.get('seed')}, the protocol fixes "
                    f"{self.contract.seeds['bootstrap']}",
                )
            if interval.get("resamples") != stats["bootstrap_resamples"]:
                self.fail(
                    f"{label}.bootstrap_resamples",
                    f"{name} used {interval.get('resamples')} resamples, the protocol "
                    f"fixes {stats['bootstrap_resamples']}",
                )
            keys = set(interval.get("intervals", {}))
            expected = {
                "%s-%s" % tuple(stats["interval_percentiles"]),
                "%s-%s" % tuple(stats["h4_gate_interval_percentiles"]),
            }
            if not expected <= keys:
                self.fail(
                    f"{label}.interval_percentiles",
                    f"{name} does not carry both {sorted(expected)}; found {sorted(keys)}",
                )

    # -- P3 ----------------------------------------------------------------

    def check_p3(self) -> Optional[dict]:
        summary = self.load("p3/summary.json")
        if summary is None:
            return None
        stats = self.contract.statistics
        budgets = self.contract.budgets

        for entry in summary["fixtures"]:
            record = next(
                item for item in self.contract.fixtures if item["id"] == entry["id"]
            )
            domain = se.Domain.from_record(record)
            enumeration = so.enumerate_feasible(record, budgets["oracle_cartesian_max"])
            products = [item["product"] for item in enumeration["feasible"]]
            informative = bool(products) and len(set(products)) > 1
            if informative != entry["informative"]:
                self.fail(
                    "p3.informative",
                    f"{entry['id']}: recomputed informative={informative}",
                )
            if not informative:
                continue
            threshold = runner._elite_threshold(products, stats["elite_fraction"])
            if threshold != entry["threshold"]:
                self.fail(
                    "p3.threshold",
                    f"{entry['id']}: recomputed threshold {threshold}, "
                    f"recorded {entry['threshold']}",
                )
            elite = [item for item in enumeration["feasible"] if item["product"] <= threshold]
            if len(elite) != entry["elite_count"]:
                self.fail(
                    "p3.threshold_ties",
                    f"{entry['id']}: recomputed elite size {len(elite)}, recorded "
                    f"{entry['elite_count']} -- a tie at the threshold was dropped",
                )
            if entry["control_count"] != stats["structure_controls"]:
                self.fail(
                    "p3.control_denominator",
                    f"{entry['id']}: {entry['control_count']} controls against the frozen "
                    f"{stats['structure_controls']}",
                )
            for codec, codec_entry in entry.get("codecs", {}).items():
                if codec_entry.get("status") != "COMPLETE":
                    continue
                bits = se.layout(domain, codec).width
                indices = [se.encode(domain, json.loads(item["identity"]), codec)
                           for item in elite]
                cover = sm.exact_cover(
                    indices, bits, budgets["cover_max_cubes"],
                    budgets["cover_seconds_per_set"],
                )
                if cover.status != "COMPLETE" or not cover.exact:
                    self.fail(
                        "p3.cover_exactness",
                        f"{entry['id']}/{codec}: the recomputed cover is not exact",
                    )
                    continue
                recomputed = len(sm.serialise_cover(cover.cubes, bits))
                if recomputed != codec_entry["elite_bytes"]:
                    self.fail(
                        "p3.serialisation_length",
                        f"{entry['id']}/{codec}: recomputed {recomputed} bytes, "
                        f"recorded {codec_entry['elite_bytes']}",
                    )
                members = sm.cover_members(cover.cubes)
                if members != sorted(set(indices)):
                    self.fail(
                        "p3.cover_equality",
                        f"{entry['id']}/{codec}: the cover denotes a different set",
                    )
                blob = sm.serialise_cover(cover.cubes, bits)
                back, width = sm.deserialise_cover(blob)
                if back != cover.cubes or width != bits:
                    self.fail("p3.serialisation_round_trip", f"{entry['id']}/{codec}")

        informative = [entry for entry in summary["fixtures"] if entry.get("informative")]
        qualifying = [
            entry for entry in informative
            if entry.get("codecs", {}).get("structural_rank", {}).get("meets_triage")
        ]
        expected_pass = (
            len({entry["family"] for entry in informative})
            >= stats["triage_informative_families_min"]
            and len(qualifying) >= math.ceil(stats["triage_fraction_min"] * len(informative))
            and len({entry["family"] for entry in qualifying})
            >= stats["triage_informative_families_min"]
        )
        recorded = summary["triage"]["status"] == runner.PASS
        if expected_pass != recorded:
            self.fail(
                "p3.triage",
                f"recomputed triage pass={expected_pass}, the run recorded {recorded}",
            )
        else:
            self.ok("p3.triage", {"pass": expected_pass, "qualifying": len(qualifying)})
        return summary

    # -- P4 ----------------------------------------------------------------

    def check_p4(self) -> Optional[dict]:
        summary = self.load("p4/summary.json")
        if summary is None:
            return None
        rows = self.load("p4/model_rows.jsonl") or []
        if not rows:
            self.fail("p4.empty_scan", "no model rows: an empty scan is never a pass")
            return summary

        stats = self.contract.statistics
        expected = set()
        for record in self.contract.fixtures:
            for budget in self.contract.budgets["optimisation_seconds"]:
                for arm in sm.MODEL_ARMS:
                    seeds = self.contract.seeds["search"] if arm == "uniform_bits" else [None]
                    for seed in seeds:
                        for repetition in range(stats["timing_repetitions"]):
                            expected.add(
                                se.canonical_json(
                                    [record["id"], arm, budget, seed, repetition]
                                )
                            )
        observed = [
            se.canonical_json(
                [row.get("fixture_id"), row.get("arm"), row.get("budget_seconds"),
                 row.get("search_seed"), row.get("repetition")]
            )
            for row in rows
        ]
        if set(observed) != expected or len(observed) != len(set(observed)):
            self.fail(
                "p4.membership",
                f"{len(expected - set(observed))} missing, "
                f"{len(set(observed) - expected)} unexpected, "
                f"{len(observed) - len(set(observed))} duplicated",
            )
        else:
            self.ok("p4.membership", len(expected))

        for row in rows:
            if row.get("status") != runner.PASS:
                continue
            counts = row.get("counts", {})
            partitioned = (
                counts.get("duplicate", 0) + counts.get("invalid_code", 0)
                + counts.get("dead_end", 0) + counts.get("interrupted", 0)
                + counts.get("complete", 0)
            )
            if partitioned != counts.get("attempted", 0):
                self.fail(
                    "p4.proposal_accounting",
                    f"{row['fixture_id']}/{row['arm']}: outcomes total {partitioned} "
                    f"against {counts.get('attempted')} attempts",
                )
            if counts.get("novel", 0) + counts.get("duplicate", 0) != counts.get("attempted", 0):
                self.fail(
                    "p4.novelty_accounting",
                    f"{row['fixture_id']}/{row['arm']}: novel plus duplicate is not attempted",
                )
            if row["arm"] == "empirical_cover" and counts.get("test_discoveries", 0):
                self.fail(
                    "p4.empirical_cover_novelty",
                    "an exact cover of observed elites reported an unseen discovery",
                )
            if row.get("best_test_product") is None or \
                    row["best_test_product"] > row["training_best_product"]:
                self.fail(
                    "p4.endpoint",
                    f"{row['fixture_id']}/{row['arm']}: the endpoint is worse than the "
                    "training-best incumbent it starts from",
                )
            if row["arm"] == "uniform_bits" and \
                    row.get("search_seed") not in self.contract.seeds["search"]:
                self.fail("p4.search_seed", "a stochastic arm used an unfrozen seed")

        self.check_intervals("p4", summary.get("contrasts", {}))
        gate = summary.get("h4_gate_percentiles")
        if list(gate or []) != list(stats["h4_gate_interval_percentiles"]):
            self.fail(
                "p4.gate_percentiles",
                f"the advancement gate used {gate}, the protocol fixes "
                f"{stats['h4_gate_interval_percentiles']}",
            )
        else:
            self.ok("p4.gate_percentiles", gate)
        return summary

    # -- P5 ----------------------------------------------------------------

    def check_p5(self, p0: Optional[dict]) -> Optional[dict]:
        summary = self.load("p5/summary.json")
        if summary is None:
            return None
        if summary.get("pooled"):
            self.fail("p5.pooling", "public and held-out results must not be pooled")
        public = self.load("p5/public_rows.jsonl") or []
        heldout = self.load("p5/heldout_rows.jsonl") or []
        if not public or not heldout:
            self.fail("p5.empty_scan", "a P5 corpus produced no rows")
        if p0 is not None:
            self.check_benchmark_rows("p5_public", public, p0["public"])
            self.check_benchmark_rows(
                "p5_heldout", heldout,
                [
                    {"program_sha256": entry["program_sha256"]}
                    for entry in p0["heldout"]["programs"]
                ],
            )
        self.check_intervals("p5_public", summary.get("public", {}).get("comparisons", {}))
        self.check_intervals("p5_heldout", summary.get("heldout", {}).get("comparisons", {}))
        return summary

    # -- dependency truth --------------------------------------------------

    def check_dependencies(self, gates: dict) -> None:
        """A dependant may not be PASS when its dependency was not."""

        for stage, dependencies in runner.DEPENDENCIES.items():
            status = gates.get(stage, {}).get("status")
            if status != runner.PASS:
                continue
            for dependency in dependencies:
                upstream = gates.get(dependency, {}).get("status")
                if upstream != runner.PASS:
                    self.fail(
                        "gates.dependency",
                        f"{stage} is PASS while its dependency {dependency} is {upstream}",
                    )
        # P5's non-model comparison does not depend on P3 or P4, so an
        # independent P5 must still have been attempted when P3 or P4 missed.
        if gates.get("p2", {}).get("status") == runner.PASS and \
                gates.get("p5", {}).get("status") == runner.NOT_RUN:
            self.fail(
                "gates.independent_p5",
                "P2 passed but the non-model P5 comparison, which does not depend on "
                "P3 or P4, was not run",
            )
        self.ok("gates.dependency", {stage: entry.get("status")
                                     for stage, entry in sorted(gates.items())})


# --------------------------------------------------------------------------
# Architecture guard
# --------------------------------------------------------------------------


def architecture_report(package: Path) -> dict:
    """Static ownership scan plus a runtime import-boundary check.

    The static scan is supporting evidence with a stated limit: it detects a
    duplicate *definition*, not a semantically equivalent reimplementation
    spelled differently. It cannot prove semantic absence of duplication and is
    never reported as though it did. The runtime check is what actually closes
    the oracle's import boundary, because it observes the module graph the
    interpreter really built.
    """

    package = Path(package)
    findings: List[dict] = []
    scanned: List[str] = []

    for path in sorted(package.glob("*.py")):
        scanned.append(path.name)
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                owner = OWNED_ELSEWHERE.get(node.name)
                if owner:
                    findings.append(
                        {
                            "kind": "duplicate_owner",
                            "file": path.name,
                            "line": node.lineno,
                            "name": node.name,
                            "owner": owner,
                        }
                    )
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in MACHINE_CONSTANTS:
                        findings.append(
                            {
                                "kind": "machine_constant",
                                "file": path.name,
                                "line": node.lineno,
                                "name": target.id,
                                "owner": "machine",
                            }
                        )

    # The oracle's declared import boundary, checked statically first.
    oracle = package / "structural_oracle.py"
    if oracle.is_file():
        tree = ast.parse(oracle.read_text(), filename=str(oracle))
        for node in ast.walk(tree):
            names: List[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module] + [
                    f"{node.module}.{alias.name}" for alias in node.names
                ]
            for name in names:
                for forbidden in ORACLE_FORBIDDEN:
                    root = forbidden.split(".")[-1]
                    if name == forbidden or name.endswith("." + root) or name == root:
                        findings.append(
                            {
                                "kind": "oracle_import",
                                "file": oracle.name,
                                "line": node.lineno,
                                "name": name,
                            }
                        )

    runtime = runtime_import_check(package)
    if runtime.get("leaked"):
        findings.append({"kind": "oracle_runtime_import", "leaked": runtime["leaked"]})

    return {
        "scanned": scanned,
        "scanned_count": len(scanned),
        "findings": findings,
        "status": runner.FAIL if findings else runner.PASS,
        "runtime": runtime,
        "limits": (
            "The AST scan detects a duplicate definition or a restated machine "
            "constant. It does not and cannot prove the semantic absence of "
            "duplication: a reimplementation under a different name passes it. The "
            "runtime check observes the module graph after import and is what "
            "closes the oracle boundary."
        ),
    }


def runtime_import_check(package: Path) -> dict:
    """Import the oracle in a fresh interpreter and read its real module graph."""

    package = Path(package)
    script = (
        "import json,sys\n"
        f"sys.path.insert(0, {str(package.parent)!r})\n"
        f"sys.path.insert(0, {str(runner.ROOT / '.reference')!r})\n"
        f"import importlib.util as u\n"
        f"spec = u.spec_from_file_location('isolated_oracle', {str(package / 'structural_oracle.py')!r})\n"
        "module = u.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        f"forbidden = {list(ORACLE_FORBIDDEN)!r}\n"
        "leaked = sorted(n for n in sys.modules if n in forbidden)\n"
        "print(json.dumps({'leaked': leaked, 'modules': len(sys.modules)}))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        return {"leaked": ["<import failed>"], "stderr": proc.stderr[-2000:]}
    return json.loads(proc.stdout.strip().splitlines()[-1])


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="research.check_structural_evidence",
        description="Independent checks and gate recomputation over a phase 2 run.",
    )
    parser.add_argument("--run")
    parser.add_argument("--contract", default="plan/phase2")
    parser.add_argument(
        "--architecture", action="store_true",
        help="run only the ownership and import-boundary guard",
    )
    parser.add_argument("--output", help="write the report here as well as to stdout")
    arguments = parser.parse_args(list(argv))

    contract_path = Path(arguments.contract)
    if not contract_path.is_absolute():
        contract_path = runner.ROOT / contract_path

    if arguments.architecture:
        report = architecture_report(runner.ROOT / "research")
        print(json.dumps(report, indent=2, sort_keys=True))
        return EXIT_OK if report["status"] == runner.PASS else EXIT_FAILURE

    if not arguments.run:
        print("usage: --run RUN_DIRECTORY [--contract DIR] | --architecture",
              file=sys.stderr)
        return EXIT_USAGE

    run_path = Path(arguments.run)
    if not run_path.is_absolute():
        run_path = runner.ROOT / run_path

    try:
        checker = Checker(run_path, contract_path)
    except (Finding, OSError, json.JSONDecodeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, indent=2))
        return EXIT_USAGE

    incomplete: List[str] = []
    try:
        manifest = checker.check_structure()
        checker.check_provenance(manifest)
        checker.check_commands()
        gates = checker.require("gates.json")
        p0 = checker.check_p0()
        p1 = checker.check_p1()
        p2 = checker.check_p2(p0)
        p3 = checker.check_p3()
        p4 = checker.check_p4()
        p5 = checker.check_p5(p0)
        checker.check_dependencies(gates)
        architecture = architecture_report(runner.ROOT / "research")
        if architecture["status"] != runner.PASS:
            checker.fail("architecture", "the ownership guard found a violation",
                         architecture["findings"])
        else:
            checker.ok("architecture", architecture["scanned_count"])
    except Finding as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, indent=2))
        return EXIT_USAGE
    except (OSError, json.JSONDecodeError, KeyError, ValueError,
            machine.CompileError, se.DomainError) as exc:
        print(json.dumps(
            {"status": "FAIL", "reason": f"{type(exc).__name__}: {exc}"}, indent=2
        ))
        return EXIT_FAILURE

    for stage, summary in (("p0", p0), ("p1", p1), ("p2", p2),
                           ("p3", p3), ("p4", p4), ("p5", p5)):
        status = gates.get(stage, {}).get("status")
        if summary is None and status in (runner.PASS,):
            incomplete.append(stage)
            checker.fail(f"{stage}.missing_summary", "a PASS stage produced no summary")
        if status == runner.INCONCLUSIVE:
            incomplete.append(stage)

    hypotheses = checker.load("hypotheses.json") or {}
    scientific = all(
        hypotheses.get(name, {}).get("status") == "supported"
        for name in ("H1", "H2", "H3", "H4")
    )
    report = {
        "run": str(run_path),
        "contract": str(contract_path),
        "checks_run": len(checker.checks),
        "findings": checker.findings,
        "finding_count": len(checker.findings),
        "inconclusive": checker.incompletes,
        "inconclusive_count": len(checker.incompletes),
        "artifacts_internally_consistent": not checker.findings,
        "artifacts_complete": not checker.findings and not incomplete,
        "scientific_success": bool(scientific),
        "stage_status": {stage: entry.get("status") for stage, entry in sorted(gates.items())},
        "hypotheses": {name: entry.get("status") for name, entry in sorted(hypotheses.items())},
        "architecture": architecture,
        "note": (
            "artifacts_complete and scientific_success are different statements. "
            "A reproducible null result has the first true and the second false. "
            "artifacts_internally_consistent says only that nothing contradicts "
            "anything else; a stage may still be INCONCLUSIVE, which is exit 2."
        ),
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if arguments.output:
        Path(arguments.output).write_text(text + "\n")
    if checker.findings:
        return EXIT_FAILURE
    if incomplete:
        return EXIT_USAGE
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
