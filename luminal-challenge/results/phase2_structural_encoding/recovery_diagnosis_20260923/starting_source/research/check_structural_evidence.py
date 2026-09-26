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
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import machine

import schema_index as si

from research import structural_encoding as se
from research import structural_evidence as sev
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


def _close(left: object, right: object, tolerance: float = 1e-12) -> bool:
    """Exact for everything but floats, where the last bit of a sum may differ.

    The bootstrap is seeded, so a recomputation reproduces the same draws. Only
    the order of a floating-point summation can differ, which is why this is a
    relative tolerance of ``1e-12`` rather than an interval of indifference.
    """

    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if math.isnan(float(left)) and math.isnan(float(right)):
            return True
        return math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance)
    return left == right


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

    def check_stage_digests(self, manifest: dict) -> None:
        """Every stage summary on disk must match the manifest digest it claims.

        Until the 2026-09-23 repair nothing compared a stage summary against the
        digest the manifest recorded for it, so a summary could be edited after
        the run and still be read as evidence. A hash agreeing is necessary and
        not sufficient: the content checks below derive their expectations from
        the locked inputs, not from the file.
        """

        recorded = manifest.get("stage_digests")
        if not isinstance(recorded, dict):
            self.fail("provenance.stage_digests", "the manifest records no stage digests")
            return
        for stage in ("preflight", "p0", "p1", "p2", "p3", "p4", "p5"):
            path = self.root / stage / "summary.json"
            actual = runner.file_digest(path) if path.is_file() else None
            claimed = recorded.get(stage)
            if actual is None and claimed is None:
                continue
            if actual is None:
                self.fail(
                    "provenance.stage_digests",
                    f"the manifest records a digest for {stage} but its summary is gone",
                )
            elif claimed is None:
                self.fail(
                    "provenance.stage_digests",
                    f"{stage}/summary.json exists with no digest in the manifest",
                )
            elif claimed != actual:
                self.fail(
                    "provenance.stage_digests",
                    f"{stage}/summary.json hashes {actual}, the manifest recorded {claimed}",
                )
        self.ok("provenance.stage_digests", sorted(recorded))

    def check_amendment(self, manifest: dict) -> None:
        """The lead review and its scoped repair amendment, present and intact."""

        recorded = manifest.get("amendment_files")
        if not isinstance(recorded, dict) or not recorded:
            self.fail(
                "provenance.amendment",
                "the manifest records no amendment files; a run made under the "
                "2026-09-23 repair handoff must record its hash",
            )
            return
        expected = set(runner.AMENDMENT_FILES)
        if set(recorded) != expected:
            self.fail(
                "provenance.amendment_membership",
                f"recorded {sorted(recorded)}, the amendment is {sorted(expected)}",
            )
        for name in sorted(expected & set(recorded)):
            actual = runner.file_digest(runner.ROOT / name)
            if actual is None:
                self.fail("provenance.amendment", f"{name} is missing from disk")
            elif actual != recorded[name]:
                self.fail(
                    "provenance.amendment",
                    f"{name} hashes {actual}, the manifest recorded {recorded[name]}",
                )
        self.ok("provenance.amendment", sorted(recorded))

    def check_provenance(self, manifest: dict) -> None:
        """Contract, plan, package and source hashes, recomputed from disk."""

        if not manifest.get("contract_files"):
            self.fail("provenance.contract_files", "the manifest records no contract files")
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

    def check_commands(self, manifest: dict, gates: dict) -> None:
        """Exact command and log requirements, per stage, for both kinds of work.

        Two kinds of work exist and they are judged differently. A stage that runs
        entirely in this process launches no subprocess, and must therefore record
        none: it says so through its work record rather than leaving an absence to
        be interpreted. A stage that launches measurement workers must account for
        every one of them -- an expected count derived from frozen policy, a
        terminal exit code, and a retained log that actually exists.

        Until the 2026-09-23 repair review this method accepted ``exit_code=None``
        outright, never resolved a ``log`` reference, and its "missing logs" list
        in fact selected *existing but empty* stage logs, so a command record with
        a null exit and an absent log produced zero findings.
        """

        commands = self.load("commands.jsonl") or []
        work = manifest.get("work_records")
        if not isinstance(work, dict):
            self.fail(
                "commands.work_records",
                "the manifest records no per-stage work records, so declared and "
                "performed work cannot be compared",
            )
            work = {}

        ran = [
            stage for stage, entry in sorted(gates.items())
            if entry.get("status") in (
                runner.PASS, runner.FAIL, runner.INCONCLUSIVE
            )
        ]
        for stage in ran:
            if stage not in work:
                self.fail(
                    "commands.work_records",
                    f"{stage} ran and declared no work record",
                )

        by_stage: Dict[str, List[dict]] = {}
        for row in commands:
            stage = row.get("stage")
            if stage not in sev.STAGES:
                self.fail(
                    "commands.stage",
                    f"a command record names stage {stage!r}, which the stage machine "
                    "does not declare",
                )
                continue
            by_stage.setdefault(stage, []).append(row)

        for stage in sev.INTERNAL_STAGES:
            rows = by_stage.get(stage, [])
            if rows:
                self.fail(
                    "commands.internal_stage",
                    f"{stage} runs in this process and must launch no measurement "
                    f"worker, yet {len(rows)} command records name it",
                )
        for stage in sev.WORKER_STAGES:
            rows = by_stage.get(stage, [])
            entry = work.get(stage) or {}
            declared = entry.get("declared_subprocesses")
            recorded = entry.get("recorded_commands")
            if gates.get(stage, {}).get("status") not in (
                runner.PASS, runner.FAIL, runner.INCONCLUSIVE
            ):
                if rows:
                    self.fail(
                        "commands.unrun_stage",
                        f"{stage} did not run yet {len(rows)} command records name it",
                    )
                continue
            if declared is None:
                self.fail(
                    "commands.declared_work",
                    f"{stage} launches workers and declared no subprocess count",
                )
            elif declared != len(rows):
                self.fail(
                    "commands.worker_membership",
                    f"{stage} declared {declared} measurement subprocesses and "
                    f"{len(rows)} command records are retained",
                )
            if recorded is not None and recorded != len(rows):
                self.fail(
                    "commands.work_record_count",
                    f"{stage}'s work record counts {recorded} commands, "
                    f"{len(rows)} are retained",
                )

            # Counts alone can be made to agree after deleting a worker record.
            # Join command task identities to the retained measurement rows.
            result_files = {
                "p2": ("p2/benchmark_rows.jsonl",),
                "p4": ("p4/model_rows.jsonl",),
                "p5": ("p5/public_rows.jsonl", "p5/heldout_rows.jsonl"),
            }[stage]
            result_rows: List[dict] = []
            for relative in result_files:
                result_rows.extend(self.load(relative) or [])

            def task_identity(item: dict) -> Tuple[object, ...]:
                return tuple(
                    item.get(field, 0 if field == "attempt" else None)
                    for field in (
                        "stage", "corpus", "program_sha256", "fixture_id", "arm",
                        "budget_seconds", "search_seed", "repetition", "attempt",
                    )
                )

            specs = [row.get("spec") for row in rows]
            if any(not isinstance(spec, dict) for spec in specs):
                self.fail(
                    "commands.worker_spec",
                    f"{stage} has a worker command with no structured task spec",
                )
            else:
                command_keys = [task_identity(spec) for spec in specs]
                result_keys = [task_identity(item) for item in result_rows]
                if len(command_keys) != len(set(command_keys)):
                    self.fail(
                        "commands.worker_duplicate",
                        f"{stage} has duplicate measurement command identities",
                    )
                if sorted(map(repr, command_keys)) != sorted(map(repr, result_keys)):
                    self.fail(
                        "commands.worker_membership",
                        f"{stage} command identities do not exactly match retained "
                        f"measurement rows ({len(command_keys)} commands, "
                        f"{len(result_keys)} rows)",
                    )

        for row in commands:
            label = (
                f"{row.get('stage')}/{row.get('kind')}"
            )
            exit_code = row.get("exit_code")
            timed_out = bool(row.get("timed_out"))
            if timed_out:
                self.fail(
                    "commands.timed_out",
                    f"{label}: a measurement timed out; a timeout is a failed row",
                )
            elif not isinstance(exit_code, int) or isinstance(exit_code, bool):
                self.fail(
                    "commands.exit_code_missing",
                    f"{label}: exit code {exit_code!r} is not terminal; a completed "
                    "command has an integer exit code",
                )
            elif exit_code != 0:
                self.fail(
                    "commands.exit_codes",
                    f"{label}: exited {exit_code}",
                )
            if not row.get("completed", True) and not timed_out:
                self.fail(
                    "commands.incomplete",
                    f"{label}: the record is not marked completed and did not time out",
                )
            reference = row.get("log")
            if reference is None:
                self.fail(
                    "commands.log_reference",
                    f"{label}: the record names no retained log",
                )
                continue
            resolved = self.root / str(reference)
            try:
                resolved.resolve().relative_to(self.root.resolve())
                contained = True
            except ValueError:
                contained = False
            if not contained or not resolved.is_file():
                self.fail(
                    "commands.log_missing",
                    f"{label}: the referenced log {reference} is absent or outside "
                    "the run directory",
                )
            elif not resolved.read_bytes().strip():
                self.fail(
                    "commands.log_empty",
                    f"{label}: the referenced log {reference} is empty",
                )
        self.ok(
            "commands.recorded",
            {
                "commands": len(commands),
                "per_stage": {stage: len(rows) for stage, rows in sorted(by_stage.items())},
                "work_records": sorted(work),
            },
        )

        # A stage crash log, when the run wrote one, must record something.
        for stage in sev.STAGES:
            path = self.root / "logs" / f"{stage}.log"
            if path.exists() and not path.read_text().strip():
                self.fail(
                    "commands.empty_log",
                    f"logs/{stage}.log exists and is empty, which records nothing",
                )

        row_counts = manifest.get("row_counts")
        if row_counts is None:
            self.fail("commands.row_counts", "the manifest records no row counts")
            row_counts = {}
        on_disk = {
            str(path.relative_to(self.root))
            for path in sorted(self.root.rglob("*.jsonl"))
        }
        if set(row_counts) != on_disk:
            self.fail(
                "commands.row_count_membership",
                f"{sorted(on_disk - set(row_counts))[:5]} are on disk without a "
                f"recorded count and {sorted(set(row_counts) - on_disk)[:5]} are "
                "recorded without a file",
            )
        for relative, recorded in sorted(row_counts.items()):
            path = self.root / relative
            if not path.is_file():
                self.fail("commands.row_counts", f"{relative} is recorded and missing")
                continue
            actual = sum(1 for line in path.read_text().splitlines() if line.strip())
            if actual != recorded:
                self.fail(
                    "commands.row_counts",
                    f"{relative} holds {actual} rows, the manifest recorded {recorded}",
                )
        self.ok("commands.row_counts", len(row_counts))

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

        # The public corpus is the eight pinned reference programs. Deriving it
        # independently is what stops an emptied or trimmed public list from
        # being read as the whole corpus downstream.
        locked_public = {
            name: se.object_digest(program) for name, program in runner.public_programs()
        }
        reported_public = {
            entry.get("name"): entry.get("program_sha256")
            for entry in summary.get("public", [])
        }
        if reported_public != locked_public:
            self.fail(
                "p0.public_membership",
                f"the public corpus is {sorted(locked_public)}; the run recorded "
                f"{sorted(reported_public)} with "
                f"{sum(1 for k, v in locked_public.items() if reported_public.get(k) != v)} "
                "hash disagreements",
            )
        else:
            self.ok("p0.public_membership", len(locked_public))
        for entry in summary.get("public", []):
            path = self.root / str(entry.get("path", ""))
            if not path.is_file():
                self.fail("p0.public_artifact", f"{entry.get('name')} has no frozen copy")
            elif runner.file_digest(path) != entry.get("file_sha256"):
                self.fail(
                    "p0.public_artifact",
                    f"{entry.get('name')}'s frozen copy does not match its recorded hash",
                )

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

    def check_p1(self, p0: Optional[dict]) -> Optional[dict]:
        summary = self.load("p1/summary.json")
        if summary is None:
            return None
        sampling = self.contract.protocol["sampling"]

        # Membership from the *locked* twelve fixtures, never from the reported
        # rows. Reading it from the report is what let an emptied fixture list
        # pass as a complete comparison before the 2026-09-23 repair.
        expected_ids = [record["id"] for record in self.contract.fixtures]
        reported = {entry["id"]: entry for entry in summary.get("fixtures", [])}
        missing = [name for name in expected_ids if name not in reported]
        extra = sorted(set(reported) - set(expected_ids))
        if missing or extra:
            self.fail(
                "p1.fixture_membership",
                f"{len(missing)} of the {len(expected_ids)} locked fixtures are absent "
                f"and {len(extra)} are unexpected",
                {"missing": missing, "extra": extra},
            )
        else:
            self.ok("p1.fixture_membership", len(expected_ids))

        # Required raw artifacts, present and nonempty, with the digests the
        # summary claims for them. Deleting one is a failure, not a smaller scan.
        raw_names = (
            "oracle_domains.jsonl", "decoder_rows.jsonl", "sampling_streams.jsonl",
            "sampling_attempts.jsonl", "sampling_identities.jsonl",
        )
        claimed = summary.get("raw_artifacts") or {}
        for name in raw_names:
            path = self.root / "p1" / name
            if not path.is_file() or not path.read_text().strip():
                self.fail(
                    "p1.raw_artifacts",
                    f"p1/{name} is missing or empty; P1's conclusions have no raw support",
                )
                continue
            actual = runner.file_digest(path)
            if claimed.get(name) is None:
                self.fail("p1.raw_artifact_hash", f"the summary records no hash for {name}")
            elif claimed[name] != actual:
                self.fail(
                    "p1.raw_artifact_hash",
                    f"p1/{name} hashes {actual}, the summary recorded {claimed[name]}",
                )
        self.ok("p1.raw_artifacts", list(raw_names))

        expected_decoder_rows: Set[str] = set()
        expected_oracle_rows: Dict[str, dict] = {}
        for record in self.contract.fixtures:
            entry = reported.get(record["id"])
            if entry is None:
                continue
            domain = se.Domain.from_record(record)
            if entry.get("domain_sha256") != domain.digest():
                self.fail(
                    "p1.domain_digest",
                    f"{record['id']}: the recorded domain digest is not this domain's",
                )
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
            expected_oracle_rows[domain.digest()] = {
                "domain_id": domain.identifier,
                "domain_sha256": domain.digest(),
                "feasible_count": enumeration["feasible_count"],
                "declared_cartesian": enumeration.get("declared_cartesian"),
                "cartesian_assignments": enumeration.get("cartesian_assignments"),
            }
            codec_entries = entry.get("codecs") or {}
            if set(codec_entries) != set(se.CODECS):
                self.fail(
                    "p1.codec_membership",
                    f"{record['id']}: recorded codecs {sorted(codec_entries)} are not "
                    f"the four declared {sorted(se.CODECS)}",
                )
            # The origin claim, recomputed rather than trusted: index 0 must
            # decode to the incumbent under both rank codecs when one exists.
            if domain.incumbent is not None:
                expected_origin = se.canonical_json(
                    se.normalise_compilation(domain.facts, domain.incumbent)
                )
                recomputed_origin = {}
                for codec in ("static_rank", "structural_rank"):
                    result = se.decode(domain, 0, codec)
                    recomputed_origin[codec] = (
                        result.status == se.COMPLETE
                        and se.canonical_json(result.compilation) == expected_origin
                    )
                if entry.get("origin_is_incumbent") != recomputed_origin:
                    self.fail(
                        "p1.origin_is_incumbent",
                        f"{record['id']}: recomputed {recomputed_origin}, the run recorded "
                        f"{entry.get('origin_is_incumbent')}",
                    )
            elif entry.get("origin_is_incumbent") is not None:
                self.fail(
                    "p1.origin_is_incumbent",
                    f"{record['id']} has no incumbent yet claims an origin property",
                )
            # Every finite-universe decode and every round trip, re-executed.
            # Nothing here reads `exhausted`, `set_equality`, `counts` or
            # `round_trips` as a fact: they are compared against this
            # recomputation, and the expected decoder-row membership comes out of
            # it. Until the 2026-09-23 repair review these assertions were
            # trusted, so `decoder_rows.jsonl` could be replaced by `{}` with a
            # matching hash and the checker returned the valid-control outcome.
            for codec in se.CODECS:
                codec_entry = codec_entries.get(codec)
                if codec_entry is None:
                    continue
                bits = se.layout(domain, codec).width
                if bits != codec_entry.get("bits"):
                    self.fail("p1.bits", f"{entry['id']}/{codec}: recomputed B is {bits}")
                exhausted = bits <= self.contract.budgets["exhaust_bit_width_max"]
                if bool(codec_entry.get("exhausted")) != exhausted:
                    self.fail(
                        "p1.exhaustion_flag",
                        f"{entry['id']}/{codec}: recomputed exhausted={exhausted}, the "
                        f"run recorded {codec_entry.get('exhausted')}",
                    )
                if exhausted:
                    counts = {status: 0 for status in se.STATUSES}
                    found: Dict[str, int] = {}
                    duplicates = 0
                    defects = 0
                    for index in range(1 << bits):
                        try:
                            result = se.decode(domain, index, codec)
                        except se.CodecDefect:
                            defects += 1
                            continue
                        counts[result.status] += 1
                        if result.status == se.COMPLETE:
                            key = se.canonical_json(result.compilation)
                            if key in found:
                                duplicates += 1
                            found[key] = index
                            expected_decoder_rows.add(
                                se.canonical_json(
                                    [domain.digest(), codec, str(index)]
                                )
                            )
                    if defects:
                        self.fail(
                            "p1.recomputed_defects",
                            f"{entry['id']}/{codec}: {defects} codes decode completely "
                            "and are rejected by the validator",
                        )
                    if duplicates:
                        self.fail(
                            "p1.recomputed_duplicates",
                            f"{entry['id']}/{codec}: {duplicates} duplicate objects",
                        )
                    recorded_counts = codec_entry.get("counts") or {}
                    if {key: recorded_counts.get(key) for key in counts} != counts:
                        self.fail(
                            "p1.recomputed_counts",
                            f"{entry['id']}/{codec}: recomputed {counts}, the run "
                            f"recorded {recorded_counts}",
                        )
                    if sum(counts.values()) != (1 << bits):
                        self.fail(
                            "p1.universe_accounting",
                            f"{entry['id']}/{codec}: statuses total "
                            f"{sum(counts.values())}, the universe is {1 << bits}",
                        )
                    if codec_entry.get("valid_codes") != counts[se.COMPLETE]:
                        self.fail(
                            "p1.recomputed_valid_codes",
                            f"{entry['id']}/{codec}: recomputed "
                            f"{counts[se.COMPLETE]} valid codes, the run recorded "
                            f"{codec_entry.get('valid_codes')}",
                        )
                    equality = set(found) == identities
                    if not equality:
                        self.fail(
                            "p1.set_equality",
                            f"{entry['id']}/{codec}: the codec's set is not the "
                            f"oracle's ({len(found)} against {len(identities)})",
                        )
                    if bool(codec_entry.get("set_equality")) != equality:
                        self.fail(
                            "p1.recomputed_set_equality",
                            f"{entry['id']}/{codec}: recomputed set_equality="
                            f"{equality}, the run recorded "
                            f"{codec_entry.get('set_equality')}",
                        )
                else:
                    for field in ("counts", "valid_codes", "set_equality"):
                        if codec_entry.get(field) is not None:
                            self.fail(
                                "p1.unexhausted_claim",
                                f"{entry['id']}/{codec}: {field} is reported for a "
                                "universe too wide to exhaust",
                            )

                # Round trips, re-executed for every feasible oracle object.
                round_trips = 0
                failures = 0
                for member in enumeration["feasible"]:
                    compilation = json.loads(member["identity"])
                    try:
                        index = se.encode(domain, compilation, codec)
                        back = se.decode(domain, index, codec)
                    except (se.DomainError, se.CodecDefect):
                        failures += 1
                        continue
                    if back.status != se.COMPLETE or \
                            se.canonical_json(back.compilation) != member["identity"]:
                        failures += 1
                        continue
                    if se.encode(domain, back.compilation, codec) != index:
                        failures += 1
                        continue
                    round_trips += 1
                if failures:
                    self.fail(
                        "p1.round_trip",
                        f"{entry['id']}/{codec}: {failures} recomputed round-trip "
                        "failures",
                    )
                if round_trips != len(identities):
                    self.fail(
                        "p1.round_trip_denominator",
                        f"{entry['id']}/{codec}: {round_trips} recomputed round trips "
                        f"against {len(identities)} feasible objects",
                    )
                if codec_entry.get("round_trips") != round_trips or \
                        codec_entry.get("round_trip_failure_count") != failures:
                    self.fail(
                        "p1.recomputed_round_trips",
                        f"{entry['id']}/{codec}: recomputed {round_trips} round trips "
                        f"and {failures} failures, the run recorded "
                        f"{codec_entry.get('round_trips')} and "
                        f"{codec_entry.get('round_trip_failure_count')}",
                    )

        # The finite-domain raw files, reconciled exactly against that
        # recomputation and against the locked fixtures.
        self.check_finite_domain_rows(expected_decoder_rows, expected_oracle_rows)

        if summary["defect_count"]:
            self.fail("p1.defects", f"{summary['defect_count']} codec defects retained")
        else:
            self.ok("p1.defects", 0)

        # -- sampling: membership from the locked public corpus ---------------
        streams = self.load("p1/sampling_streams.jsonl") or []
        attempts = self.load("p1/sampling_attempts.jsonl") or []
        unions = self.load("p1/sampling_identities.jsonl") or []
        locked_public = [name for name, _ in runner.public_programs()]
        if p0 is not None:
            corpus = [entry["name"] for entry in p0.get("public", [])]
        else:
            corpus = locked_public
        if sorted(corpus) != sorted(locked_public):
            self.fail(
                "p1.public_corpus",
                f"P0's public corpus {sorted(corpus)} is not the locked "
                f"{sorted(locked_public)}",
            )
            corpus = locked_public
        expected_streams = 2 * len(locked_public)
        if len(streams) != expected_streams:
            self.fail(
                "p1.stream_membership",
                f"{len(streams)} streams recorded, {expected_streams} expected for the "
                f"{len(locked_public)} locked public programs",
            )
        expected_stream_keys = {
            se.canonical_json([name, stream])
            for name in locked_public for stream in ("raw_bits", "option_paths")
        }
        observed_stream_keys = [
            se.canonical_json([stream.get("program_name"), stream.get("stream")])
            for stream in streams
        ]
        if set(observed_stream_keys) != expected_stream_keys or \
                len(observed_stream_keys) != len(set(observed_stream_keys)):
            self.fail(
                "p1.stream_keys",
                f"{len(expected_stream_keys - set(observed_stream_keys))} expected "
                f"(program, stream) pairs are absent and "
                f"{len(set(observed_stream_keys) - expected_stream_keys)} are unexpected",
            )

        # Recomputation from the raw rows. Every reported total is derived here
        # from `sampling_attempts.jsonl` and compared; an emptied stream file or a
        # trimmed coverage list cannot survive this because the expectation comes
        # from the locked corpus, not from the report.
        from collections import Counter

        raw_counts: Dict[Tuple[str, str], Counter] = {}
        raw_cases: Dict[Tuple[str, str], int] = {}
        raw_case_failures: Dict[Tuple[str, str], int] = {}
        raw_identities: Dict[str, Set[str]] = {}
        raw_attempt_ids: Dict[Tuple[str, str], Set[int]] = {}
        for row in attempts:
            key = (row.get("program"), row.get("stream"))
            raw_counts.setdefault(key, Counter())[row.get("status")] += 1
            raw_cases[key] = raw_cases.get(key, 0) + int(row.get("cases_checked") or 0)
            raw_case_failures[key] = (
                raw_case_failures.get(key, 0) + int(row.get("case_failures") or 0)
            )
            raw_attempt_ids.setdefault(key, set()).add(row.get("attempt"))
            if row.get("status") == se.COMPLETE and row.get("compilation_sha256"):
                raw_identities.setdefault(row.get("program"), set()).add(
                    row["compilation_sha256"]
                )
            if row.get("status") == se.COMPLETE and not int(row.get("cases_checked") or 0) \
                    and not int(row.get("case_failures") or 0):
                self.fail(
                    "p1.case_denominator",
                    f"{key}: a completed sampled attempt validated zero cases",
                )
        if not attempts:
            self.fail(
                "p1.raw_attempts",
                "no raw sampling attempts are retained, so no reported total can be "
                "reconciled from raw evidence",
            )

        for stream in streams:
            key = (stream.get("program_name"), stream.get("stream"))
            total = (
                stream["complete"] + stream["invalid_code"]
                + stream["dead_end"] + stream["interrupted"]
            )
            if total != stream["attempts_drawn"]:
                self.fail(
                    "p1.stream_accounting",
                    f"{key}: statuses total {total} against {stream['attempts_drawn']} "
                    "draws -- an attempt was hidden",
                )
            if stream["attempts_drawn"] > stream["attempts_requested"]:
                self.fail("p1.stream_overdraw", "more attempts than the frozen request")
            if stream["attempts_requested"] != sampling["attempts_per_program_per_stream"]:
                self.fail(
                    "p1.stream_request",
                    f"{key}: requested {stream['attempts_requested']} attempts, the "
                    f"protocol fixes {sampling['attempts_per_program_per_stream']}",
                )
            if stream["seed"] not in (
                self.contract.seeds["raw_bits"], self.contract.seeds["option_paths"]
            ):
                self.fail("p1.stream_seed", f"stream used unfrozen seed {stream['seed']}")
            observed = raw_counts.get(key, Counter())
            if sum(observed.values()) != stream["attempts_drawn"]:
                self.fail(
                    "p1.raw_reconciliation",
                    f"{key}: {sum(observed.values())} raw rows against "
                    f"{stream['attempts_drawn']} reported draws",
                )
            for status, field in (
                (se.COMPLETE, "complete"), (se.INVALID_CODE, "invalid_code"),
                (se.DEAD_END, "dead_end"), (se.INTERRUPTED, "interrupted"),
            ):
                if observed.get(status, 0) != stream[field]:
                    self.fail(
                        "p1.raw_status_counts",
                        f"{key}: raw rows hold {observed.get(status, 0)} {status} against "
                        f"a reported {stream[field]}",
                    )
            if len(raw_attempt_ids.get(key, set())) != stream["attempts_drawn"]:
                self.fail(
                    "p1.raw_attempt_indices",
                    f"{key}: attempt indices are not distinct across its raw rows",
                )
            if raw_cases.get(key, 0) != stream.get("case_checks"):
                self.fail(
                    "p1.raw_case_checks",
                    f"{key}: raw rows hold {raw_cases.get(key, 0)} case executions against "
                    f"a reported {stream.get('case_checks')}",
                )
            if raw_case_failures.get(key, 0) != stream.get("case_failures"):
                self.fail(
                    "p1.raw_case_failures",
                    f"{key}: raw rows hold {raw_case_failures.get(key, 0)} case failures "
                    f"against a reported {stream.get('case_failures')}",
                )
            if stream.get("case_failures"):
                self.fail(
                    "p1.case_discrepancy",
                    f"{key}: {stream['case_failures']} sampled completions were rejected "
                    "by the pinned case validator",
                )
        self.ok(
            "p1.stream_accounting",
            {"streams": len(streams), "raw_rows": len(attempts),
             "case_executions": sum(raw_cases.values())},
        )
        if summary.get("sampling_discrepancy_count"):
            self.fail(
                "p1.sampling_discrepancies",
                f"{summary['sampling_discrepancy_count']} sampled completions failed a case",
            )

        # The union denominator, recomputed from the retained identities rather
        # than read from `public_coverage`.
        union_rows = {row.get("program"): row for row in unions}
        minimum = sampling["minimum_distinct_completed_per_program"]
        coverage = {entry["program"]: entry for entry in summary.get("public_coverage", [])}
        if sorted(coverage) != sorted(locked_public):
            self.fail(
                "p1.coverage_membership",
                f"public coverage covers {sorted(coverage)}, the locked corpus is "
                f"{sorted(locked_public)}",
            )
        recomputed_short: List[str] = []
        for name in locked_public:
            recomputed = raw_identities.get(name, set())
            listed = set((union_rows.get(name) or {}).get("identities") or [])
            if name not in union_rows:
                self.fail("p1.union_rows", f"{name} has no retained identity union")
            elif listed != recomputed:
                self.fail(
                    "p1.union_recount",
                    f"{name}: the retained union holds {len(listed)} identities, the raw "
                    f"rows hold {len(recomputed)}",
                )
            entry = coverage.get(name)
            if entry is None:
                recomputed_short.append(name)
                continue
            if entry.get("distinct_complete_union") != len(recomputed):
                self.fail(
                    "p1.coverage_recount",
                    f"{name}: reported {entry.get('distinct_complete_union')} distinct "
                    f"completions, the raw rows hold {len(recomputed)}",
                )
            if entry.get("meets_minimum") != (len(recomputed) >= minimum):
                self.fail(
                    "p1.coverage_flag",
                    f"{name}: meets_minimum={entry.get('meets_minimum')} against a "
                    f"recomputed {len(recomputed)} >= {minimum}",
                )
            if len(recomputed) < minimum:
                recomputed_short.append(name)
        if bool(summary.get("coverage_met")) != (not recomputed_short):
            self.fail(
                "p1.coverage_met",
                f"the run recorded coverage_met={summary.get('coverage_met')} while "
                f"{len(recomputed_short)} programs are short on recomputation",
            )
        short = recomputed_short
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
        self.check_sampling_replay(p0, streams, attempts)
        return summary

    def check_finite_domain_rows(
        self, expected_decoder: Set[str], expected_oracle: Dict[str, dict]
    ) -> None:
        """Parse the finite-domain raw files and reconcile them exactly.

        ``expected_decoder`` is the set of ``(domain, codec, index)`` keys the
        checker's own exhaustive re-decode produced; ``expected_oracle`` is one row
        per locked fixture with independently recounted numbers. Requiring the file
        to be nonempty with a matching digest was not enough: the review replaced
        all 282 decoder rows with a single ``{}`` object, re-hashed it, and the
        checker returned the valid-control outcome.
        """

        oracle_rows = self.load("p1/oracle_domains.jsonl") or []
        keyed: Dict[str, dict] = {}
        for row in oracle_rows:
            if not isinstance(row, dict) or "domain_sha256" not in row:
                self.fail(
                    "p1.oracle_row_shape",
                    f"an oracle row is not a domain record: {str(row)[:120]}",
                )
                continue
            if row["domain_sha256"] in keyed:
                self.fail(
                    "p1.oracle_row_duplicate",
                    f"domain {row['domain_sha256'][:12]} appears twice",
                )
            keyed[row["domain_sha256"]] = row
        if set(keyed) != set(expected_oracle):
            self.fail(
                "p1.oracle_membership",
                f"{len(set(expected_oracle) - set(keyed))} locked fixture domains are "
                f"absent from oracle_domains.jsonl and "
                f"{len(set(keyed) - set(expected_oracle))} are unexpected",
            )
        for digest, expected in sorted(expected_oracle.items()):
            row = keyed.get(digest)
            if row is None:
                continue
            for field, value in expected.items():
                if value is None:
                    continue
                if row.get(field) != value:
                    self.fail(
                        "p1.oracle_row_recount",
                        f"{expected['domain_id']}: {field} is {row.get(field)!r}, "
                        f"recomputed {value!r}",
                    )
        self.ok("p1.oracle_membership", len(expected_oracle))

        decoder_rows = self.load("p1/decoder_rows.jsonl") or []
        observed: List[str] = []
        for row in decoder_rows:
            if not isinstance(row, dict) or not {
                "domain_sha256", "codec", "index", "status"
            } <= set(row):
                self.fail(
                    "p1.decoder_row_shape",
                    f"a decoder row is missing its identity: {sorted(row) if isinstance(row, dict) else type(row).__name__}",
                )
                continue
            if row.get("status") != se.COMPLETE:
                self.fail(
                    "p1.decoder_row_status",
                    f"decoder_rows.jsonl holds a {row.get('status')} row; it records the "
                    "valid codes of the exhausted universes",
                )
                continue
            observed.append(
                se.canonical_json([row["domain_sha256"], row["codec"], str(row["index"])])
            )
        duplicates = len(observed) - len(set(observed))
        if duplicates:
            self.fail(
                "p1.decoder_row_duplicates",
                f"{duplicates} decoder rows repeat a (domain, codec, index) identity",
            )
        missing = expected_decoder - set(observed)
        extra = set(observed) - expected_decoder
        if missing or extra:
            self.fail(
                "p1.decoder_membership",
                f"{len(missing)} expected decoder rows are absent and {len(extra)} are "
                f"unexpected against {len(expected_decoder)} recomputed valid codes",
                {"missing": sorted(missing)[:5], "extra": sorted(extra)[:5]},
            )
        else:
            self.ok("p1.decoder_membership", len(expected_decoder))

    def check_sampling_replay(
        self, p0: Optional[dict], streams: Sequence[dict], attempts: Sequence[dict]
    ) -> None:
        """Replay each stream's declared seeded draws and reconcile every row.

        The retained indices must *be* the declared sequence, in order, with
        contiguous attempt numbers, the stream's own frozen seed, the fixed codec
        and the fixed domain. Before the 2026-09-23 repair review the checker
        accepted any distinct indices whose stream named a seed drawn from either
        stream's seed list. Every completion is re-validated on every case.
        """

        if p0 is None:
            self.inconclusive(
                "p1.sampling_replay",
                "P0 produced no summary, so no sampling domain can be rebuilt",
            )
            return

        import direct_compiler as dcomp
        import direct_contract as dc

        seeds = {
            "raw_bits": self.contract.seeds["raw_bits"],
            "option_paths": self.contract.seeds["option_paths"],
        }
        requested = self.contract.protocol["sampling"]["attempts_per_program_per_stream"]
        by_key: Dict[Tuple[str, str], List[dict]] = {}
        for row in attempts:
            by_key.setdefault((row.get("program"), row.get("stream")), []).append(row)
        if not by_key:
            self.fail("p1.sampling_replay", "no retained attempt was replayed")
            return

        recorded_streams = {
            (stream.get("program_name"), stream.get("stream")): stream
            for stream in streams
        }
        expected_keys = {
            (name, stream_name)
            for name, _program in runner.public_programs()
            for stream_name in runner.STREAMS
        }
        if set(by_key) != expected_keys:
            self.fail(
                "p1.attempt_stream_membership",
                f"raw attempts have {len(set(by_key) & expected_keys)} expected stream "
                f"keys, {len(set(by_key) - expected_keys)} unexpected, and "
                f"{len(expected_keys - set(by_key))} missing",
                {
                    "unexpected": sorted(set(by_key) - expected_keys)[:5],
                    "missing": sorted(expected_keys - set(by_key))[:5],
                },
            )
        replayed = 0
        cases_run = 0
        for entry in p0.get("public", []):
            frozen = self.root / str(entry.get("path", ""))
            if frozen.is_file():
                program = machine.load_program(frozen)
            else:
                program = dict(runner.public_programs())[entry["name"]]
            if se.object_digest(program) != entry.get("program_sha256"):
                self.fail(
                    "p1.sampling_replay",
                    f"{entry['name']}'s program does not hash to its recorded digest",
                )
                continue
            facts = dc.derive(program)
            compiled, _ = dcomp.compile_with_report(
                program, dcomp.DEFAULT_LIMITS, optimise=False
            )
            record = runner.whole_program_record(
                entry["name"], "public", program, facts, compiled
            )
            domain = se.Domain.from_record(record)
            digest = domain.digest()
            for stream_name in runner.STREAMS:
                key = (entry["name"], stream_name)
                rows = by_key.get(key, [])
                stream = recorded_streams.get(key)
                if not rows:
                    self.fail(
                        "p1.sampling_replay",
                        f"{key} has no retained sampling attempt",
                    )
                    continue
                if stream is None:
                    self.fail("p1.sampling_replay", f"{key} has no stream summary")
                    continue
                if stream.get("seed") != seeds[stream_name]:
                    self.fail(
                        "p1.stream_specific_seed",
                        f"{key}: the stream records seed {stream.get('seed')}, the "
                        f"protocol fixes {seeds[stream_name]} for this stream",
                    )
                if stream.get("attempts_requested") != requested:
                    self.fail(
                        "p1.stream_request",
                        f"{key}: requested {stream.get('attempts_requested')}, the "
                        f"protocol fixes {requested}",
                    )
                ordered = sorted(rows, key=lambda item: item.get("attempt", -1))
                numbers = [row.get("attempt") for row in ordered]
                if numbers != list(range(len(ordered))):
                    self.fail(
                        "p1.attempt_numbering",
                        f"{key}: attempt numbers are not contiguous from zero",
                    )
                    continue
                for row in ordered:
                    if row.get("codec") != "structural_rank":
                        self.fail(
                            "p1.sampling_codec",
                            f"{key}: a row records codec {row.get('codec')!r}",
                        )
                        break
                    if row.get("domain_sha256") != digest:
                        self.fail(
                            "p1.sampling_domain",
                            f"{key}: a row records a domain that is not this program's",
                        )
                        break
                    if row.get("seed") != seeds[stream_name]:
                        self.fail(
                            "p1.sampling_seed",
                            f"{key}: a row records seed {row.get('seed')}",
                        )
                        break
                expected_indices = runner.stream_indices(
                    domain, "structural_rank", stream_name, seeds[stream_name],
                    len(ordered),
                )
                retained = [int(row["index"]) for row in ordered]
                if retained != expected_indices:
                    first = next(
                        (position for position, (a, b) in
                         enumerate(zip(retained, expected_indices)) if a != b),
                        None,
                    )
                    self.fail(
                        "p1.draw_sequence",
                        f"{key}: the retained indices are not the declared seeded "
                        f"draws; first disagreement at attempt {first}",
                    )
                    continue
                # The draws are the declared ones; now the outcomes.
                multiplicities: Dict[str, int] = {}
                statuses = {status: 0 for status in se.STATUSES}
                cases_here = 0
                for row in ordered:
                    result = se.decode(domain, int(row["index"]), "structural_rank")
                    replayed += 1
                    statuses[result.status] += 1
                    if result.status != row.get("status"):
                        self.fail(
                            "p1.replay_status",
                            f"{key} attempt {row.get('attempt')}: recorded "
                            f"{row.get('status')}, recomputed {result.status}",
                        )
                        break
                    if result.status != se.COMPLETE:
                        continue
                    if result.identity != row.get("compilation_sha256"):
                        self.fail(
                            "p1.replay_identity",
                            f"{key} attempt {row.get('attempt')}: identity disagrees",
                        )
                        break
                    multiplicities[result.identity] = (
                        multiplicities.get(result.identity, 0) + 1
                    )
                    for case in program["cases"]:
                        try:
                            machine.check_case(program, result.compilation, case)
                        except (machine.CompileError, machine.ProgramError) as exc:
                            self.fail(
                                "p1.replay_case",
                                f"{key} attempt {row.get('attempt')}: the pinned case "
                                f"validator rejects a completion: {exc}",
                            )
                            break
                        cases_here += 1
                        cases_run += 1
                    if row.get("cases_checked") != len(program["cases"]):
                        self.fail(
                            "p1.replay_case_count",
                            f"{key} attempt {row.get('attempt')}: recorded "
                            f"{row.get('cases_checked')} case executions against "
                            f"{len(program['cases'])} declared cases",
                        )
                        break
                recorded_multiplicities = stream.get("identity_multiplicities") or {}
                if recorded_multiplicities != {
                    name: multiplicities[name] for name in sorted(multiplicities)
                }:
                    self.fail(
                        "p1.identity_multiplicities",
                        f"{key}: recomputed {len(multiplicities)} identities with "
                        f"{sum(multiplicities.values())} sightings, the run recorded "
                        f"{len(recorded_multiplicities)} with "
                        f"{sum(recorded_multiplicities.values())}",
                    )
                if stream.get("case_checks") != cases_here:
                    self.fail(
                        "p1.replay_case_total",
                        f"{key}: recomputed {cases_here} case executions, the run "
                        f"recorded {stream.get('case_checks')}",
                    )
        extra_keys = sorted(set(by_key) - {
            (entry["name"], stream_name)
            for entry in p0.get("public", []) for stream_name in runner.STREAMS
        })
        if extra_keys:
            self.fail(
                "p1.sampling_extra_rows",
                f"{len(extra_keys)} raw sampling groups are not declared public "
                f"(program, stream) pairs: {extra_keys[:5]}",
            )
        self.ok(
            "p1.sampling_replay",
            {"attempts_replayed": replayed, "case_executions": cases_run},
        )

    # -- P2 ----------------------------------------------------------------

    def check_benchmark_rows(self, label: str, rows: Sequence[dict],
                             programs: Sequence[dict],
                             extra_arms: Sequence[str] = ()) -> None:
        """Exact membership, from frozen policy rather than from the report.

        ``extra_arms`` is the conditional model arm. When H4 authorises it, its
        rows are *required*, not optional: that is what stops a PASS with no
        measurement behind it.
        """

        budgets = self.contract.budgets["optimisation_seconds"]
        repetitions = self.contract.statistics["timing_repetitions"]
        unbudgeted = ("accepted_bootstrap", "accepted_default")
        budgeted = ("accepted_budgeted",) + runner.STRUCTURAL_ARMS + tuple(extra_arms)
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
        expected_tiny = {record["id"] for record in self.contract.fixtures}
        actual_tiny = {entry["id"] for entry in summary["tiny_fixtures"]}
        if actual_tiny != expected_tiny:
            self.fail(
                "p2.tiny_membership",
                f"missing {sorted(expected_tiny - actual_tiny)}, "
                f"extra {sorted(actual_tiny - expected_tiny)}",
            )
        else:
            self.ok("p2.tiny_fixtures", len(actual_tiny))
        self.check_intervals("p2", summary.get("comparisons", {}))
        if p0 is not None:
            self.recompute_comparisons(
                "p2", summary.get("comparisons", {}), rows,
                {entry["program_sha256"]: "public" for entry in p0["public"]},
            )
        return summary

    def recompute_comparisons(
        self,
        label: str,
        comparisons: Dict[str, dict],
        rows: Sequence[dict],
        families: Dict[str, str],
    ) -> None:
        """Recompute every paired interval from the raw benchmark rows.

        ``check_intervals`` below checks that the declared seed, resample count
        and percentile labels were used. That is a check on the labels, not on
        the numbers, which is why the 2026-09-23 review called these branches
        unmeasured. This method recomputes the point estimate, both intervals and
        the win/tie/loss counts from the raw rows and compares them exactly; the
        bootstrap is seeded, so exact agreement is the correct expectation.
        """

        if not comparisons:
            self.fail(f"{label}.comparisons_empty", "no comparison was reported to recompute")
            return
        if not rows:
            self.fail(
                f"{label}.comparison_rows",
                "comparisons are reported with no raw rows to recompute them from",
            )
            return
        checked = 0
        for name, entry in sorted(comparisons.items()):
            baseline = entry.get("baseline_arm")
            candidate = entry.get("candidate_arm")
            budget = entry.get("budget_seconds")
            if baseline is None or candidate is None or budget is None:
                self.fail(
                    f"{label}.comparison_identity",
                    f"{name} does not name its arms and budget",
                )
                continue
            if budget not in self.contract.budgets["optimisation_seconds"]:
                self.fail(
                    f"{label}.comparison_budget",
                    f"{name} used budget {budget}, the protocol declares "
                    f"{self.contract.budgets['optimisation_seconds']}",
                )
            recomputed = runner.paired_log_ratio_analysis(
                rows, families, baseline, candidate, budget, self.contract
            )
            checked += 1
            for field in ("status", "programs", "wins", "ties", "losses"):
                if recomputed.get(field) != entry.get(field):
                    self.fail(
                        f"{label}.comparison_recount",
                        f"{name}: recomputed {field}={recomputed.get(field)}, the run "
                        f"recorded {entry.get(field)}",
                    )
            mine = recomputed.get("interval") or {}
            theirs = entry.get("interval") or {}
            if mine.get("status") != theirs.get("status"):
                self.fail(
                    f"{label}.comparison_interval_status",
                    f"{name}: recomputed interval status {mine.get('status')}, recorded "
                    f"{theirs.get('status')}",
                )
                continue
            if mine.get("status") != runner.PASS:
                continue
            if not _close(mine.get("point_estimate"), theirs.get("point_estimate")):
                self.fail(
                    f"{label}.comparison_point_estimate",
                    f"{name}: recomputed {mine.get('point_estimate')}, recorded "
                    f"{theirs.get('point_estimate')}",
                )
            recomputed_intervals = mine.get("intervals") or {}
            recorded_intervals = theirs.get("intervals") or {}
            if set(recomputed_intervals) != set(recorded_intervals):
                self.fail(
                    f"{label}.comparison_interval_keys",
                    f"{name}: recomputed {sorted(recomputed_intervals)}, recorded "
                    f"{sorted(recorded_intervals)}",
                )
            for key in sorted(set(recomputed_intervals) & set(recorded_intervals)):
                pair, other = recomputed_intervals[key], recorded_intervals[key]
                if len(pair) != len(other) or not all(
                    _close(a, b) for a, b in zip(pair, other)
                ):
                    self.fail(
                        f"{label}.comparison_interval",
                        f"{name} {key}: recomputed {pair}, recorded {other}",
                    )
            if mine.get("programs") != theirs.get("programs") or \
                    mine.get("families") != theirs.get("families"):
                self.fail(
                    f"{label}.comparison_denominator",
                    f"{name}: recomputed {mine.get('programs')} programs in families "
                    f"{mine.get('families')}, recorded {theirs.get('programs')} in "
                    f"{theirs.get('families')}",
                )
        self.ok(f"{label}.comparison_recount", checked)

    def recompute_p4_contrasts(self, summary: dict, rows: Sequence[dict]) -> None:
        """Recompute the P4 contrasts, gate bounds and advancement from raw rows.

        The gate is what authorises the conditional P5 model arm, so recomputing
        it from the retained rows rather than reading ``advance_to_model_arm`` is
        the check that matters.
        """

        if not rows:
            self.fail("p4.contrast_rows", "contrasts are reported with no raw model rows")
            return
        recomputed = runner.p4_contrasts(rows, self.contract)
        for field in (
            "usable_rows", "informative_fixtures", "families_with_informative_tests",
            "empirical_cover_test_discoveries", "empirical_cover_exhausted",
            "advance_to_model_arm", "primary_budget_seconds",
        ):
            if recomputed.get(field) != summary.get(field):
                self.fail(
                    "p4.contrast_recount",
                    f"recomputed {field}={recomputed.get(field)!r}, the run recorded "
                    f"{summary.get(field)!r}",
                )
        mine = recomputed["h4_gate_lower_bounds"]
        theirs = summary.get("h4_gate_lower_bounds") or {}
        if set(mine) != set(theirs) or not all(
            _close(mine[key], theirs.get(key)) for key in mine
        ):
            self.fail(
                "p4.gate_bounds",
                f"recomputed H4 lower bounds {mine}, the run recorded {theirs}",
            )
        reported = summary.get("contrasts") or {}
        if set(reported) != set(recomputed["contrasts"]):
            self.fail(
                "p4.contrast_membership",
                f"recomputed {sorted(recomputed['contrasts'])}, recorded {sorted(reported)}",
            )
        for name in sorted(set(reported) & set(recomputed["contrasts"])):
            mine_entry = recomputed["contrasts"][name]
            their_entry = reported[name]
            if mine_entry["programs"] != their_entry.get("programs"):
                self.fail(
                    "p4.contrast_denominator",
                    f"{name}: recomputed {mine_entry['programs']} programs, recorded "
                    f"{their_entry.get('programs')}",
                )
            mine_interval = mine_entry["interval"].get("intervals") or {}
            their_interval = (their_entry.get("interval") or {}).get("intervals") or {}
            if set(mine_interval) != set(their_interval):
                self.fail(
                    "p4.contrast_interval_keys",
                    f"{name}: recomputed {sorted(mine_interval)}, recorded "
                    f"{sorted(their_interval)}",
                )
            for key in sorted(set(mine_interval) & set(their_interval)):
                if not all(
                    _close(a, b)
                    for a, b in zip(mine_interval[key], their_interval[key])
                ):
                    self.fail(
                        "p4.contrast_interval",
                        f"{name} {key}: recomputed {mine_interval[key]}, recorded "
                        f"{their_interval[key]}",
                    )
        self.ok("p4.contrast_recount", sorted(recomputed["contrasts"]))

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

        expected_ids = {record["id"] for record in self.contract.fixtures}
        actual_ids = {entry["id"] for entry in summary.get("fixtures", [])}
        if actual_ids != expected_ids:
            self.fail(
                "p3.fixture_membership",
                f"missing {sorted(expected_ids - actual_ids)}, "
                f"extra {sorted(actual_ids - expected_ids)}",
            )
        else:
            self.ok("p3.fixture_membership", len(actual_ids))

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

                # The controls, rebuilt from the frozen seed and re-measured:
                # their median is what the triage margin is a ratio against, and
                # a label check on the seed does not establish the number. The
                # computation has one owner in the runner; what makes this
                # independent is that the inputs come from the locked fixture.
                control = runner.control_serialisation(
                    domain,
                    sorted(item["identity"] for item in enumeration["feasible"]),
                    len(elite), codec, self.contract.seeds["structure_controls"],
                    stats["structure_controls"], budgets,
                )
                if control["count"] != codec_entry.get("control_bytes_count"):
                    self.fail(
                        "p3.control_recount",
                        f"{entry['id']}/{codec}: recomputed {control['count']} complete "
                        f"controls, recorded {codec_entry.get('control_bytes_count')}",
                    )
                median_control = control["median_bytes"]
                control_status = control["status"]
                if not _close(median_control, codec_entry.get("control_median_bytes")):
                    self.fail(
                        "p3.control_median",
                        f"{entry['id']}/{codec}: recomputed median {median_control}, "
                        f"recorded {codec_entry.get('control_median_bytes')}",
                    )
                if control_status != codec_entry.get("control_status"):
                    self.fail(
                        "p3.control_status",
                        f"{entry['id']}/{codec}: recomputed control status "
                        f"{control_status}, recorded {codec_entry.get('control_status')}",
                    )
                expected_triage = (
                    None if (recomputed is None or median_control is None)
                    else recomputed <= stats["triage_ratio_max"] * median_control
                )
                if expected_triage != codec_entry.get("meets_triage"):
                    self.fail(
                        "p3.triage_margin",
                        f"{entry['id']}/{codec}: recomputed meets_triage="
                        f"{expected_triage}, recorded {codec_entry.get('meets_triage')}",
                    )

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
        self.recompute_p4_contrasts(summary, rows)
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
        model_arm = summary.get("model_arm") or {}
        extra_arms = (runner.MODEL_ARM,) if model_arm.get("authorised") else ()
        if p0 is not None:
            self.check_benchmark_rows("p5_public", public, p0["public"], extra_arms)
            self.check_benchmark_rows(
                "p5_heldout", heldout,
                [
                    {"program_sha256": entry["program_sha256"]}
                    for entry in p0["heldout"]["programs"]
                ],
                extra_arms,
            )
        self.check_intervals("p5_public", summary.get("public", {}).get("comparisons", {}))
        self.check_intervals("p5_heldout", summary.get("heldout", {}).get("comparisons", {}))
        if p0 is not None:
            self.recompute_comparisons(
                "p5_public", summary.get("public", {}).get("comparisons", {}), public,
                {entry["program_sha256"]: "public" for entry in p0["public"]},
            )
            self.recompute_comparisons(
                "p5_heldout", summary.get("heldout", {}).get("comparisons", {}), heldout,
                {
                    entry["program_sha256"]: entry["family"]
                    for entry in p0["heldout"]["programs"]
                },
            )
        # The conditional model arm may be PASS only with real measurements.
        model = model_arm
        model_rows = [row for row in public + heldout if row.get("arm") == runner.MODEL_ARM]
        if model.get("status") == runner.PASS and not model_rows:
            self.fail(
                "p5.model_arm_unmeasured",
                f"{runner.MODEL_ARM} is recorded PASS with no rows; a disabled arm is "
                "NOT_RUN, never PASS without measurements",
            )
        if model.get("authorised") and not model_rows:
            self.fail(
                "p5.model_arm_missing_rows",
                "the model arm is authorised and produced no benchmark row",
            )
        if model_rows and not model.get("authorised"):
            self.fail(
                "p5.model_arm_unauthorised",
                f"{len(model_rows)} model rows exist while H4 did not authorise the arm",
            )
        self.ok("p5.model_arm", {"status": model.get("status"), "rows": len(model_rows)})
        return summary

    # -- preflight ---------------------------------------------------------

    def check_preflight(self) -> Optional[dict]:
        """The preflight record, which lives in ``inputs/`` rather than a stage dir."""

        payload = self.load("inputs/preflight.json")
        if payload is None:
            return None
        locks = payload.get("locks") or {}
        recomputed = self.contract.verify_locks()
        if locks.get("status") != runner.PASS:
            self.fail(
                "preflight.locks",
                f"the run recorded lock status {locks.get('status')}",
            )
        elif recomputed["status"] != runner.PASS:
            self.fail(
                "preflight.locks",
                "; ".join(recomputed["findings"][:5]),
            )
        elif locks.get("checked") != recomputed["checked"]:
            self.fail(
                "preflight.lock_denominator",
                f"the run checked {locks.get('checked')} locked files, recomputed "
                f"{recomputed['checked']}",
            )
        if payload.get("plan_version") != "2.1":
            self.fail(
                "preflight.plan_version",
                f"the run records plan version {payload.get('plan_version')!r}",
            )
        if payload.get("protocol_id") != self.contract.protocol["protocol_id"]:
            self.fail(
                "preflight.protocol_id",
                f"the run records protocol {payload.get('protocol_id')!r}",
            )
        self.ok("preflight.locks", recomputed["checked"])
        return payload

    # -- imported dependencies --------------------------------------------

    def check_imported_links(self, manifest: dict) -> Dict[str, dict]:
        """Resolve every imported dependency link the run recorded.

        An imported stage is evidence that lives in another run. The new run must
        say so, name it, and carry the digest and the independent validation that
        authorised it; the checker then re-resolves the link rather than treating
        the artifacts as locally generated. A link that does not resolve is a
        finding, and the stage it claims to supply derives FAIL.
        """

        links = manifest.get("imported_dependencies")
        if links is None:
            return {}
        if not isinstance(links, dict):
            self.fail("imports.shape", "imported_dependencies is not a mapping")
            return {}
        resolved: Dict[str, dict] = {}
        validation_cache: Dict[str, Tuple[int, dict, str]] = {}
        for stage, link in sorted(links.items()):
            if stage not in sev.STAGES:
                self.fail(
                    "imports.stage",
                    f"an imported link names stage {stage!r}, which the stage machine "
                    "does not declare",
                )
                continue
            prior = Path(link.get("run", ""))
            if not prior.is_absolute():
                prior = runner.ROOT / prior
            summary = prior / stage / "summary.json"
            if not summary.is_file():
                self.fail(
                    "imports.unresolved",
                    f"{stage} is recorded as imported from {link.get('run')}, which "
                    "holds no such summary",
                )
                continue
            actual = runner.file_digest(summary)
            if actual != link.get("summary_sha256"):
                self.fail(
                    "imports.digest",
                    f"the imported {stage} summary now hashes {actual}, the link "
                    f"recorded {link.get('summary_sha256')}",
                )
                continue
            prior_manifest = prior / "manifest.json"
            if runner.file_digest(prior_manifest) != link.get("manifest_sha256"):
                self.fail(
                    "imports.prior_manifest",
                    f"the imported run's manifest changed since {stage} was imported",
                )
                continue
            if link.get("derived_verdict") != runner.PASS:
                self.fail(
                    "imports.verdict",
                    f"{stage} was imported with derived verdict "
                    f"{link.get('derived_verdict')!r}; only a derived PASS authorises "
                    "a dependent stage",
                )
                continue
            if link.get("checker_exit_code") not in (0, 2):
                self.fail(
                    "imports.validation",
                    f"{stage}'s import validation exited "
                    f"{link.get('checker_exit_code')!r}",
                )
                continue
            report_digest = link.get("checker_report_sha256")
            if not isinstance(report_digest, str) or len(report_digest) != 64 or any(
                char not in "0123456789abcdef" for char in report_digest
            ):
                self.fail(
                    "imports.validation_digest",
                    f"{stage} has no valid hash for the evidence report that authorised it",
                )
                continue
            mine = {name: runner.file_digest(runner.ROOT / name)
                    for name in runner.AMENDMENT_FILES}
            if (link.get("amendment_files") or {}) != mine:
                self.fail(
                    "imports.amendment",
                    f"{stage} was imported from a run with different amendment inputs",
                )
                continue
            # A stored PASS and a hash of a past checker report are still claims.
            # Re-run the independent checker on the imported source, recursively
            # resolving its own imports, then compare the fresh report digest and
            # the derived stage verdict with the link. This makes the child
            # checker's imported provenance transitive and independently
            # resolvable after the original worker process has exited.
            prior_key = str(prior.resolve())
            validated = validation_cache.get(prior_key)
            if validated is None:
                depth = int(os.environ.get(runner.IMPORT_DEPTH_VARIABLE, "0"))
                if depth >= runner.MAX_IMPORT_DEPTH:
                    self.fail(
                        "imports.depth",
                        f"validating {stage} would exceed the imported-run depth "
                        f"limit {runner.MAX_IMPORT_DEPTH}",
                    )
                    continue
                environment = dict(os.environ)
                environment[runner.IMPORT_DEPTH_VARIABLE] = str(depth + 1)
                environment["PYTHONPATH"] = (
                    f"{runner.ROOT / '.reference'}{os.pathsep}{runner.ROOT}"
                )
                command = [
                    sys.executable, "-m", "research.check_structural_evidence",
                    "--run", prior_key, "--contract", str(self.contract.directory),
                ]
                try:
                    checked = subprocess.run(
                        command, cwd=str(runner.ROOT), capture_output=True,
                        text=True,
                        timeout=self.contract.budgets["external_process_seconds"] * 60,
                        env=environment,
                    )
                except subprocess.TimeoutExpired:
                    self.fail(
                        "imports.validation_timeout",
                        f"rechecking imported run {prior_key} timed out",
                    )
                    continue
                try:
                    report = json.loads(checked.stdout)
                except json.JSONDecodeError:
                    self.fail(
                        "imports.validation_report",
                        f"rechecking imported run {prior_key} produced no JSON report "
                        f"(exit {checked.returncode}): {checked.stderr[-500:]}",
                    )
                    continue
                digest = hashlib.sha256(checked.stdout.encode("utf-8")).hexdigest()
                validated = (checked.returncode, report, digest)
                validation_cache[prior_key] = validated
            exit_code, report, digest = validated
            if exit_code not in (EXIT_OK, EXIT_USAGE) or report.get("findings"):
                self.fail(
                    "imports.validation",
                    f"the imported {stage} source fails its fresh evidence check "
                    f"(exit {exit_code}, {len(report.get('findings') or [])} findings)",
                )
                continue
            if digest != report_digest or exit_code != link.get("checker_exit_code"):
                self.fail(
                    "imports.validation_digest",
                    f"the fresh checker report for {stage} differs from the report "
                    "that authorised the import",
                )
                continue
            outcomes = {
                item.get("stage"): item
                for item in (report.get("stage_outcomes") or [])
            }
            if outcomes.get(stage, {}).get("verdict") != runner.PASS:
                self.fail(
                    "imports.recomputed_verdict",
                    f"the fresh checker derives {stage} as "
                    f"{outcomes.get(stage, {}).get('verdict')!r}, not PASS",
                )
                continue
            resolved[stage] = dict(link) | {"summary_path": str(summary)}
        if resolved:
            self.ok("imports.resolved", sorted(resolved))
        return resolved

    # -- evidence-derived verdicts ----------------------------------------

    def findings_for(self, stage: str) -> List[dict]:
        prefix = f"{stage}."
        return [
            item for item in self.findings
            if str(item.get("check", "")).startswith(prefix)
        ]

    def incompletes_for(self, stage: str) -> List[dict]:
        prefix = f"{stage}."
        return [
            item for item in self.incompletes
            if str(item.get("check", "")).startswith(prefix)
        ]

    def derive_outcomes(
        self,
        manifest: dict,
        gates: dict,
        summaries: Dict[str, Optional[dict]],
        imported: Dict[str, dict],
    ) -> List[sev.StageOutcome]:
        """One verdict per stage, derived from checked evidence.

        This is the repair the 2026-09-23 review required. Completeness and the
        exit status are computed from these verdicts, never from the labels in
        ``gates.json``: relabelling P1 as PASS while its recomputed coverage is
        short is now a reconciliation finding rather than an exit-0 run.
        """

        request = manifest.get("cli_request")
        problems = sev.validate_request(request)
        if problems:
            for reason in problems:
                self.fail("request.invalid", reason)
            request = request if isinstance(request, dict) else {}
        elif request.get("run_id") != manifest.get("run_id"):
            self.fail(
                "request.run_id",
                f"the request names run {request.get('run_id')!r}, while the manifest "
                f"names {manifest.get('run_id')!r}",
            )
        required = set(sev.required_stages(request if isinstance(request, dict) else {}))
        recorded_required = manifest.get("required_stages")
        if recorded_required is None:
            self.fail(
                "request.required_stages",
                "the manifest records no required stage set derived from its request",
            )
        elif set(recorded_required) != required:
            self.fail(
                "request.required_stages",
                f"the manifest records required stages {sorted(recorded_required)}, "
                f"the recorded request implies {sorted(required)}",
            )
        executed = manifest.get("stages_run")
        if not isinstance(executed, list):
            self.fail("request.stages_run", "the manifest records no executed-stage list")
        else:
            unexpected = sorted(set(executed) - required)
            if unexpected:
                self.fail(
                    "request.stages_run",
                    f"the run executed stages {unexpected} outside the requested set "
                    f"{sorted(required)}",
                )

        outcomes: List[sev.StageOutcome] = []
        verdicts: Dict[str, str] = {}
        for stage in sev.STAGES:
            recorded = (gates.get(stage) or {}).get("status")
            if stage in required and stage not in gates:
                self.fail(
                    "gates.missing_required",
                    f"{stage} is required by the recorded request and has no gate entry",
                )
            link = imported.get(stage)
            if link is not None:
                verdict, reason = runner.PASS, (
                    f"imported from {link.get('run_relative') or link.get('run')} "
                    f"with derived verdict PASS"
                )
                outcome = sev.StageOutcome(
                    stage=stage, verdict=verdict, reason=reason, recorded=recorded,
                    required=stage in required,
                    imported_from=link.get("run_relative") or link.get("run"),
                    evidence={"checker_report_sha256": link.get("checker_report_sha256")},
                )
                # An imported stage did not run here, so the local label is
                # legitimately BLOCKED_BY_GATE or absent; the comparison that
                # matters was made when it was imported and is re-resolved above.
                outcome.recorded = None
                outcomes.append(outcome)
                verdicts[stage] = verdict
                continue
            findings = self.findings_for(stage)
            incompletes = self.incompletes_for(stage)
            has_evidence = summaries.get(stage) is not None
            if findings:
                verdict = runner.FAIL
                reason = f"{len(findings)} finding(s): {findings[0]['check']}"
            elif not has_evidence:
                # A gate written NOT_RUN for an unrequested stage is the expected
                # record, even when a dependency it never needed in this CLI call
                # would block it. An explicitly requested dependent stage is
                # recorded BLOCKED_BY_GATE and remains subject to dependency
                # reconciliation below.
                if stage not in required:
                    if recorded == runner.NOT_RUN:
                        verdict = runner.NOT_RUN
                        reason = "not required by this command-line request"
                    else:
                        blocking = sev.derive_blocked(stage, verdicts)
                        if blocking:
                            verdict = runner.BLOCKED
                            reason = f"blocked by {', '.join(blocking)}"
                        else:
                            verdict = runner.NOT_RUN
                            reason = "no evidence for this stage in this run"
                else:
                    blocking = sev.derive_blocked(stage, verdicts)
                    if blocking:
                        verdict = runner.BLOCKED
                        reason = f"blocked by {', '.join(blocking)}"
                    else:
                        verdict = runner.FAIL
                        reason = "required stage produced no summary"
            elif incompletes:
                verdict = runner.INCONCLUSIVE
                reason = incompletes[0]["reason"]
            else:
                blocking = sev.derive_blocked(stage, verdicts)
                if blocking:
                    verdict = runner.FAIL
                    reason = (
                        f"evidence exists while its dependencies "
                        f"{', '.join(blocking)} do not pass"
                    )
                else:
                    verdict = runner.PASS
                    reason = "its evidence passes every applicable check"
            outcome = sev.StageOutcome(
                stage=stage, verdict=verdict, reason=reason, recorded=recorded,
                required=stage in required,
                evidence={
                    "findings": len(findings),
                    "inconclusive": len(incompletes),
                    "summary": has_evidence,
                },
            )
            outcomes.append(outcome)
            verdicts[stage] = verdict

        for outcome in outcomes:
            if outcome.imported_from is not None:
                # This process did not run the imported stage; its source run's
                # gate/evidence reconciliation was independently repeated while
                # resolving the link above. The local NOT_RUN label is expected.
                continue
            reason = sev.reconcile(outcome)
            if reason is not None:
                self.fail("gates.reconciliation", reason)
        if not any(item["check"] == "gates.reconciliation" for item in self.findings):
            self.ok(
                "gates.reconciliation",
                {outcome.stage: outcome.verdict for outcome in outcomes},
            )
        return outcomes

    def check_hypotheses(self, summaries: Dict[str, Optional[dict]]) -> Dict[str, dict]:
        """Recompute the hypothesis labels from the summaries and compare."""

        recomputed = runner.hypothesis_dispositions(self.root)
        recorded = self.load("hypotheses.json") or {}
        if set(recorded) != set(recomputed):
            self.fail(
                "hypotheses.membership",
                f"the run records {sorted(recorded)}, recomputed {sorted(recomputed)}",
            )
        for name in sorted(set(recorded) & set(recomputed)):
            if recorded[name].get("status") != recomputed[name]["status"]:
                self.fail(
                    "hypotheses.status",
                    f"{name} is recorded {recorded[name].get('status')!r} while its "
                    f"evidence implies {recomputed[name]['status']!r}",
                )
        self.ok(
            "hypotheses.recomputed",
            {name: entry["status"] for name, entry in sorted(recomputed.items())},
        )
        return recomputed

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


def self_protocol_statuses(checker: Checker) -> Tuple[str, ...]:
    """The status vocabulary the protocol declares, read from the locked file."""

    return tuple(checker.contract.protocol["status_values"])


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

    try:
        manifest = checker.check_structure()
        checker.check_provenance(manifest)
        checker.check_amendment(manifest)
        checker.check_stage_digests(manifest)
        gates = checker.require("gates.json")
        checker.check_commands(manifest, gates)
        recorded_status = manifest.get("stage_status") or {}
        for stage, entry in sorted(gates.items()):
            if stage in recorded_status and recorded_status[stage] != entry.get("status"):
                checker.fail(
                    "gates.manifest_agreement",
                    f"{stage} is {entry.get('status')} in gates.json and "
                    f"{recorded_status[stage]} in the manifest",
                )
        for stage, entry in sorted(gates.items()):
            if entry.get("status") not in self_protocol_statuses(checker):
                checker.fail(
                    "gates.status_vocabulary",
                    f"{stage} carries status {entry.get('status')!r}, which the protocol "
                    "does not declare",
                )
        imported = checker.check_imported_links(manifest)
        preflight = checker.check_preflight()
        p0 = checker.check_p0()
        p1 = checker.check_p1(p0)
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
        summaries = {
            "preflight": preflight, "p0": p0, "p1": p1,
            "p2": p2, "p3": p3, "p4": p4, "p5": p5,
        }
        hypotheses = checker.check_hypotheses(summaries)
        outcomes = checker.derive_outcomes(manifest, gates, summaries, imported)
    except Finding as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, indent=2))
        return EXIT_USAGE
    except (OSError, json.JSONDecodeError, KeyError, ValueError,
            machine.CompileError, se.DomainError) as exc:
        print(json.dumps(
            {"status": "FAIL", "reason": f"{type(exc).__name__}: {exc}"}, indent=2
        ))
        return EXIT_FAILURE

    derived = sev.completeness(outcomes, checker.findings)
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
        "artifacts_complete": derived["artifacts_complete"],
        "scientific_success": bool(scientific),
        "stage_outcomes": [outcome.to_row() for outcome in outcomes],
        "stage_verdicts": {outcome.stage: outcome.verdict for outcome in outcomes},
        "required_stages": derived["required_stages"],
        "required_unmet": derived["required_unmet"],
        "required_failed": derived["required_failed"],
        "imported_dependencies": {
            stage: link.get("run_relative") or link.get("run")
            for stage, link in sorted(imported.items())
        },
        "stage_status": {stage: entry.get("status") for stage, entry in sorted(gates.items())},
        "hypotheses": {name: entry.get("status") for name, entry in sorted(hypotheses.items())},
        "architecture": architecture,
        "note": (
            "Every stage verdict in stage_outcomes is derived from this run's "
            "evidence; stage_status is what the run wrote down, kept beside it. "
            "artifacts_complete and scientific_success are different statements: a "
            "reproducible null result has the first true and the second false."
        ),
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if arguments.output:
        Path(arguments.output).write_text(text + "\n")
    # The exit status is derived from the verdicts, not from recorded labels.
    return derived["exit_code"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
