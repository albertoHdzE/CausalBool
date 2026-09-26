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

    def check_commands(self, manifest: dict) -> None:
        """Recorded commands, their exit codes, and the logs they refer to.

        A nonzero exit or a timeout is a failure here. Until the 2026-09-23
        repair this counted them and then reported PASS regardless, so a run
        whose every worker crashed could still be labelled complete.
        """

        commands = self.load("commands.jsonl") or []
        failed = [
            entry for entry in commands
            if entry.get("exit_code") not in (0, None) or entry.get("timed_out")
        ]
        if failed:
            self.fail(
                "commands.exit_codes",
                f"{len(failed)} of {len(commands)} recorded commands exited nonzero "
                "or timed out",
                {"first": failed[:3]},
            )
        else:
            self.ok("commands.recorded", {"count": len(commands)})

        # Every stage that ran must have left the log file the run names for it,
        # and a stage recorded in the manifest as run must have a gate.
        for stage in manifest.get("stages_run", []):
            gate = (self.load("gates.json") or {}).get(stage)
            if gate is None:
                self.fail("commands.stage_gate", f"{stage} ran with no gate record")
        missing_logs = [
            stage for stage in manifest.get("stages_run", [])
            if (self.root / "logs" / f"{stage}.log").exists()
            and not (self.root / "logs" / f"{stage}.log").read_text().strip()
        ]
        if missing_logs:
            self.fail(
                "commands.logs",
                f"{missing_logs} left an empty log file, which records nothing",
            )
        row_counts = manifest.get("row_counts") or {}
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
            for codec, codec_entry in codec_entries.items():
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
        self.recheck_sampling_legality(p0, attempts)
        return summary

    def recheck_sampling_legality(
        self, p0: Optional[dict], attempts: Sequence[dict]
    ) -> None:
        """Re-decode every retained sampling attempt and re-execute its cases.

        This is the independent recomputation of legality the contract asks for:
        the domain is rebuilt from the frozen program copy, every retained index
        is decoded again, and the status is compared with the recorded one. A
        completed attempt is re-validated on every program case. A disagreement
        is a finding, and an empty scan is a finding too.
        """

        if p0 is None:
            self.inconclusive(
                "p1.legality_recompute", "P0 produced no summary, so no domain can be rebuilt"
            )
            return
        by_program: Dict[str, List[dict]] = {}
        for row in attempts:
            by_program.setdefault(row.get("program"), []).append(row)
        if not by_program:
            self.fail("p1.legality_recompute", "no retained attempt was re-decoded")
            return

        import direct_compiler as dcomp
        import direct_contract as dc

        disagreements: List[dict] = []
        decoded = 0
        cases_run = 0
        for entry in p0.get("public", []):
            rows = by_program.get(entry["name"], [])
            if not rows:
                self.fail(
                    "p1.legality_recompute",
                    f"{entry['name']} has no retained sampling attempt",
                )
                continue
            frozen = self.root / str(entry.get("path", ""))
            if frozen.is_file():
                program = machine.load_program(frozen)
            else:
                # An imported P0 keeps its frozen copy in the run that produced
                # it. The locked reference program is the same object either way,
                # and its hash is checked against the record below.
                program = dict(runner.public_programs())[entry["name"]]
            if se.object_digest(program) != entry.get("program_sha256"):
                self.fail(
                    "p1.legality_recompute",
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
            for row in rows:
                if row.get("domain_sha256") != digest:
                    disagreements.append(
                        {"program": entry["name"], "attempt": row.get("attempt"),
                         "kind": "domain_digest"}
                    )
                    continue
                result = se.decode(domain, int(row["index"]), row["codec"])
                decoded += 1
                if result.status != row.get("status"):
                    disagreements.append(
                        {"program": entry["name"], "attempt": row.get("attempt"),
                         "kind": "status", "recorded": row.get("status"),
                         "recomputed": result.status}
                    )
                    continue
                if result.status != se.COMPLETE:
                    continue
                if result.identity != row.get("compilation_sha256"):
                    disagreements.append(
                        {"program": entry["name"], "attempt": row.get("attempt"),
                         "kind": "identity"}
                    )
                    continue
                for case in program["cases"]:
                    try:
                        machine.check_case(program, result.compilation, case)
                    except (machine.CompileError, machine.ProgramError) as exc:
                        disagreements.append(
                            {"program": entry["name"], "attempt": row.get("attempt"),
                             "kind": "case", "error": str(exc)}
                        )
                        break
                    cases_run += 1
        if disagreements:
            self.fail(
                "p1.legality_recompute",
                f"{len(disagreements)} retained attempts do not reproduce",
                disagreements[:10],
            )
        else:
            self.ok(
                "p1.legality_recompute",
                {"attempts_redecoded": decoded, "case_executions": cases_run},
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

    incomplete: List[str] = []
    try:
        manifest = checker.check_structure()
        checker.check_provenance(manifest)
        checker.check_amendment(manifest)
        checker.check_stage_digests(manifest)
        checker.check_commands(manifest)
        gates = checker.require("gates.json")
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
