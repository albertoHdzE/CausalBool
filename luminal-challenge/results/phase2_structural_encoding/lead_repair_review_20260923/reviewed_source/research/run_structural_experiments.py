"""The phase 2 experiment runner: corpus freeze, stage machine and evidence.

This module owns the command line, the subprocess harness, the frozen corpora
and the P0-P5 orchestration. It owns no algorithm: domains, codecs, options,
search, bounds, covers and proposals all come from their declared owners, and
the independent oracle is reached only through ``research.structural_oracle``.

Nothing here is an acceptance mode. It produces reviewable research evidence in
a new run directory and refuses to overwrite one. The checker
``research.check_structural_evidence`` recomputes every gate from the raw rows;
a banner printed here establishes nothing.

Usage, from ``luminal-challenge``::

    PYTHONPATH=.reference:. python3 -m research.run_structural_experiments \\
      --stage all --run-id RUN_ID --contract plan/phase2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import statistics
import subprocess
import sys
import time
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import machine

import compare_direct as official
import direct_compiler as dcomp
import direct_constraints as dk
import direct_contract as dc
import direct_optimizer as dopt
import schema_index as si
import verify_direct as verification

from research import structural_encoding as se
from research import structural_models as sm
from research import structural_oracle as so
from research import structural_search as ss


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
RESULTS = ROOT / "results" / "phase2_structural_encoding"
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

# The pinned upstream reference commit. ``reference.json`` records it under
# ``commit`` and ``plan/INDEX_ONLY_PLAN.md`` asserts the same string; both files
# are hash-locked in BASELINE_LOCK.json, so the two are independent statements of
# the same pin and ``verify_locks`` requires all three to agree.
REFERENCE_COMMIT = "573b8a85f4bdb8c3d8ba9f180d5f98dac875c902"

# The declared schema of ``reference.json``: entries live under ``sha256``, keyed
# by a path relative to ``.reference/``. Reading any other key silently verifies
# nothing, which is the failure this constant exists to prevent.
REFERENCE_MANIFEST_KEY = "sha256"

# The lead review and its scoped repair amendment. They are inputs to every run
# made under the amendment, so their hashes are recorded in the manifest and the
# checker verifies both presence and integrity. The original locked
# ``plan/phase2/`` package is unedited and is recorded separately.
AMENDMENT_FILES = (
    "results/phase2_structural_encoding/lead_review_20260923/LEAD_REVIEW.md",
    "results/phase2_structural_encoding/lead_review_20260923/REPAIR_HANDOFF.md",
)

STAGES = ("preflight", "p0", "p1", "p2", "p3", "p4", "p5")
ALL_STAGES = STAGES + ("all",)

ACCEPTED_ARMS = ("accepted_bootstrap", "accepted_default", "accepted_budgeted")
STRUCTURAL_ARMS = ("structural_dfs", "structural_bound", "structural_expanded")
MODEL_ARM = "structural_model"

PASS, FAIL, INCONCLUSIVE, NOT_RUN, NOT_APPLICABLE, BLOCKED = (
    "PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN", "NOT_APPLICABLE", "BLOCKED_BY_GATE"
)

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2


class StageBlocked(Exception):
    """A gate or a missing dependency stops this stage."""

    def __init__(self, status: str, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


# --------------------------------------------------------------------------
# Small shared helpers
# --------------------------------------------------------------------------


def file_digest(path: Path) -> Optional[str]:
    """SHA256 of actual file bytes, distinct from an object digest."""

    path = Path(path)
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(se.canonical_json(row) + "\n")
            count += 1
    return count


def read_jsonl(path: Path) -> List[dict]:
    rows: List[dict] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def git_state() -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.run(
                ["git", *args], cwd=str(REPO), capture_output=True, text=True, timeout=60
            ).stdout
        except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
            return f"<git unavailable: {exc}>"

    diff = run("diff", "HEAD")
    return {
        "head": run("rev-parse", "HEAD").strip(),
        "status": run("status", "--short"),
        "diff": diff,
        "diff_sha256": hashlib.sha256(diff.encode("utf-8")).hexdigest(),
        "untracked": run("ls-files", "--others", "--exclude-standard"),
    }


def percentile(sorted_values: Sequence[float], fraction: float) -> float:
    """Linear interpolation at index ``(N-1)*p``, fixed before any result is seen."""

    if not sorted_values:
        return float("nan")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = (len(sorted_values) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return float(sorted_values[low])
    weight = position - low
    return float(sorted_values[low] * (1 - weight) + sorted_values[high] * weight)


def geometric_mean(values: Sequence[float]) -> float:
    if not values:
        return float("nan")
    return math.exp(sum(math.log(value) for value in values) / len(values))


# --------------------------------------------------------------------------
# Contract inputs
# --------------------------------------------------------------------------


class Contract:
    """The frozen delegation inputs, loaded once and never rewritten."""

    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)
        if not self.directory.is_dir():
            raise StageBlocked(FAIL, f"contract directory {directory} does not exist")
        self.protocol = json.loads((self.directory / "PROTOCOL.json").read_text())
        self.fixtures = json.loads((self.directory / "FIXTURES.json").read_text())["fixtures"]
        self.baseline_lock = json.loads((self.directory / "BASELINE_LOCK.json").read_text())
        self.package_lock = json.loads((self.directory / "PACKAGE_LOCK.json").read_text())
        self.acceptance = json.loads((self.directory / "ACCEPTANCE_MATRIX.json").read_text())

    # -- frozen policy accessors -----------------------------------------

    @property
    def seeds(self) -> dict:
        return self.protocol["seeds"]

    @property
    def budgets(self) -> dict:
        return self.protocol["budgets"]

    @property
    def statistics(self) -> dict:
        return self.protocol["statistics"]

    def verify_locks(self) -> dict:
        """Every locked file, hashed from disk. Any mismatch blocks dependants.

        The reference manifest is read through its *declared* schema. Until the
        2026-09-23 repair this loop read ``reference['files']``, a key the
        manifest does not have, so it iterated nothing and reported PASS with a
        count that hid an empty scan. Every gate here prints its denominator and
        an empty required scan is a failure, never a pass.
        """

        findings: List[str] = []
        checked = 0
        counts: Dict[str, int] = {}
        for label, lock in (("package", self.package_lock), ("baseline", self.baseline_lock)):
            entries = lock["files"]
            if not entries:
                findings.append(f"{label}: the lock declares no files")
            counts[label] = len(entries)
            for relative, expected in sorted(entries.items()):
                actual = file_digest(REPO / relative)
                checked += 1
                if actual is None:
                    findings.append(f"{label}: missing {relative}")
                elif actual != expected:
                    findings.append(f"{label}: hash mismatch {relative}")

        manifest_path = ROOT / "reference.json"
        reference = json.loads(manifest_path.read_text())
        entries = reference.get(REFERENCE_MANIFEST_KEY)
        if not isinstance(entries, dict) or not entries:
            findings.append(
                f"reference: {manifest_path.name} has no nonempty "
                f"{REFERENCE_MANIFEST_KEY!r} map"
            )
            entries = {}
        counts["reference"] = len(entries)
        for relative, expected in sorted(entries.items()):
            actual = file_digest(ROOT / ".reference" / relative)
            checked += 1
            if actual is None:
                findings.append(f"reference: missing {relative}")
            elif actual != expected:
                findings.append(f"reference: hash mismatch {relative}")

        # Membership, not merely agreement: a manifest that lost half its entries
        # would otherwise still verify every entry it kept.
        on_disk = {
            str(path.relative_to(ROOT / ".reference"))
            for path in sorted((ROOT / ".reference").rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        }
        unlisted = sorted(on_disk - set(entries))
        if unlisted:
            findings.append(f"reference: {len(unlisted)} files are not in the manifest: "
                            f"{unlisted[:5]}")

        recorded_commit = reference.get("commit")
        checked += 1
        if recorded_commit != REFERENCE_COMMIT:
            findings.append(
                f"reference: pinned commit is {recorded_commit!r}, "
                f"the protocol pins {REFERENCE_COMMIT!r}"
            )
        plan_path = ROOT / "plan" / "INDEX_ONLY_PLAN.md"
        checked += 1
        if not plan_path.is_file():
            findings.append("reference: the canonical index plan is missing")
        elif REFERENCE_COMMIT not in plan_path.read_text():
            findings.append(
                "reference: the canonical index plan does not name the pinned commit"
            )

        return {
            "checked": checked,
            "entry_counts": counts,
            "reference_commit": recorded_commit,
            "reference_files_on_disk": len(on_disk),
            "findings": findings,
            "status": FAIL if findings else PASS,
        }


def source_snapshot() -> dict:
    """Hashes of the research sources and of the production sources they reuse."""

    research = {
        path.name: file_digest(path)
        for path in sorted((ROOT / "research").glob("*.py"))
    }
    # The research tests live in ``research_tests/``, not ``tests_direct/``: the
    # frozen historical evidence checker discovers every top-level file of the
    # latter by glob and compares it against a provenance record written before
    # phase 2 existed. Lead repair decision, 2026-09-23.
    tests = {
        path.name: file_digest(path)
        for path in sorted((ROOT / "research_tests").glob("*.py"))
    }
    production = {
        Path(name).name: file_digest(ROOT / name)
        for name in sorted(str(item) for item in verification.SOURCES)
    }
    payload = {"research": research, "tests": tests, "production": production}
    payload["snapshot_sha256"] = se.object_digest(payload)
    return payload


# --------------------------------------------------------------------------
# Domain construction
# --------------------------------------------------------------------------


def fixture_domain(record: dict) -> se.Domain:
    return se.Domain.from_record(record)


def physical_address_domain(facts: dc.ProgramFacts, name: str, ceiling: int) -> List[int]:
    """Every legal physical base for one value below ``ceiling`` words.

    Vectors take aligned multiples of ``machine.VLEN``; scalars take every word.
    Nothing here is filtered by the state, so this is a *declared* domain.
    """

    width = facts.width[name]
    if width == machine.VLEN:
        return [base for base in range(0, ceiling - width + 1, machine.VLEN)]
    return list(range(0, ceiling - width + 1))


def whole_program_record(
    identifier: str,
    family: str,
    program: dict,
    facts: dc.ProgramFacts,
    incumbent: dict,
) -> dict:
    """The declared whole-program domain of P1 and of the expanded arm.

    All operations, issue cycles ``0 .. horizon-1``, every aligned physical
    scratch base, and the incumbent kept for option ordering. It contains the
    bootstrap and it can have dead ends.
    """

    return {
        "id": identifier,
        "family": family,
        "program": program,
        "selected_operations": list(range(facts.count)),
        "time_domains": {str(op_id): list(range(facts.horizon)) for op_id in range(facts.count)},
        "address_domains": {
            name: physical_address_domain(facts, name, machine.SCRATCH_WORDS)
            for name in facts.value_names
        },
        "fixed_times": {},
        "fixed_addresses": {},
        "incumbent": incumbent,
        "target": None,
    }


def matched_window_record(
    identifier: str,
    family: str,
    program: dict,
    facts: dc.ProgramFacts,
    times: Dict[int, int],
    addresses: Dict[str, int],
    window: Sequence[int],
    target_cycles: int,
    target_memory: int,
) -> dict:
    """The identical physical domain the accepted ``JointQuery`` would state.

    The time domain is the incumbent plus or minus ``direct_constraints.TIME_SLACK``
    clipped to the target, and the address domain is every legal base below the
    target footprint. These come from the accepted query's own definitions, so
    the structural arm and the absolute-query control compare like with like.
    A fixed decision that already violates the target makes the query
    ``INFEASIBLE``, exactly as it does for the accepted optimiser.
    """

    window = tuple(sorted(set(window)))
    ceiling = min(facts.horizon, target_cycles) - 1

    for op_id in range(facts.count):
        if op_id in window:
            continue
        if times[op_id] >= target_cycles:
            raise dk.Infeasible(
                f"external operation {op_id} issues at {times[op_id]}, at or past "
                f"the target of {target_cycles}"
            )
    for name in facts.value_names:
        if facts.producers[name] in window:
            continue
        if addresses[name] + facts.width[name] > target_memory:
            raise dk.Infeasible(
                f"external value {name!r} ends past the target of {target_memory}"
            )

    time_domains: Dict[str, List[int]] = {}
    for op_id in window:
        low = max(0, times[op_id] - dk.TIME_SLACK)
        high = min(times[op_id] + dk.TIME_SLACK, ceiling)
        if low > high:
            raise dk.Infeasible(
                f"operation {op_id} has no cycle below the target of {target_cycles}"
            )
        time_domains[str(op_id)] = list(range(low, high + 1))

    address_domains: Dict[str, List[int]] = {}
    for op_id in window:
        name = facts.dest[op_id]
        if name is None:
            continue
        bases = physical_address_domain(facts, name, target_memory)
        if not bases:
            raise dk.Infeasible(f"value {name!r} cannot fit a target of {target_memory}")
        address_domains[name] = bases

    selected_values = set(address_domains)
    return {
        "id": identifier,
        "family": family,
        "program": program,
        "selected_operations": list(window),
        "time_domains": time_domains,
        "address_domains": address_domains,
        "fixed_times": {
            str(op_id): times[op_id] for op_id in range(facts.count) if op_id not in window
        },
        "fixed_addresses": {
            name: addresses[name] for name in facts.value_names if name not in selected_values
        },
        "incumbent": dc.compilation(facts, times, addresses),
        "target": [target_cycles, target_memory],
    }


# --------------------------------------------------------------------------
# Corpora
# --------------------------------------------------------------------------


def public_programs() -> List[Tuple[str, dict]]:
    paths = sorted((ROOT / ".reference" / "programs").glob("*.json"))
    if len(paths) != 8:
        raise StageBlocked(FAIL, f"expected eight public programs, found {len(paths)}")
    return [(path.name, machine.load_program(path)) for path in paths]


def heldout_programs(contract: Contract) -> List[dict]:
    """The frozen held-out corpus, generated by its sole owner.

    ``tests_direct.generate_programs.additional_program`` is the generator; it
    is called, never reimplemented. The manifest order is family order from
    ``FAMILIES``, then increasing seed.
    """

    from tests_direct import generate_programs as gp

    first = contract.protocol["heldout"]["seed_first"]
    last = contract.protocol["heldout"]["seed_last"]
    per_family = contract.protocol["heldout"]["programs_per_family"]

    entries: List[dict] = []
    for seed in range(first, last + 1):
        program = gp.additional_program(seed)
        machine.validate_program(program)
        baseline = machine.serial_compile(program)
        machine.check_compilation(program, baseline)
        for case in program["cases"]:
            machine.check_case(program, baseline, case)
        entries.append(
            {
                "seed": seed,
                "family": gp.FAMILIES[seed % 5],
                "name": program["name"],
                "operations": len(program["operations"]),
                "cases": len(program["cases"]),
                "program_sha256": gp.program_digest(program),
                "semantic_sha256": se.program_semantic_digest(program),
                "program": program,
            }
        )

    order = {family: position for position, family in enumerate(gp.FAMILIES)}
    entries.sort(key=lambda entry: (order[entry["family"]], entry["seed"]))
    counts: Dict[str, int] = {}
    for entry in entries:
        counts[entry["family"]] = counts.get(entry["family"], 0) + 1
    if any(count != per_family for count in counts.values()) or len(counts) != len(gp.FAMILIES):
        raise StageBlocked(
            FAIL, f"held-out corpus is not {per_family} per family: {counts}"
        )
    return entries


def heldout_collisions(entries: Sequence[dict]) -> List[dict]:
    """Every semantic collision with an existing or historical program.

    Compared after excluding only the display name. There is no replacement
    seed policy: a collision is a preflight failure.
    """

    from tests_direct import generate_programs as gp

    existing: Dict[str, str] = {}
    for label, programs in (
        ("public", gp.public_programs()),
        ("regression", gp.regression_programs()),
        ("additional", gp.additional_programs()),
        ("stress", gp.stress_programs()),
    ):
        for program in programs:
            existing[se.program_semantic_digest(program)] = f"{label}:{program['name']}"

    for manifest in sorted(
        (ROOT / "results").glob("*/baseline/extra_corpus_manifest.json")
    ):
        payload = json.loads(manifest.read_text())
        for entry in payload.get("programs", []):
            digest = entry.get("sha256")
            if digest:
                # A historical manifest records the full program digest, which
                # includes the display name. It is retained under a distinct key
                # so a match is never confused with a semantic collision.
                existing.setdefault("full:" + digest, f"historical:{manifest.parent.parent.name}")

    collisions: List[dict] = []
    seen: Dict[str, int] = {}
    for entry in entries:
        if entry["semantic_sha256"] in existing:
            collisions.append(
                {
                    "seed": entry["seed"],
                    "kind": "semantic",
                    "against": existing[entry["semantic_sha256"]],
                }
            )
        if "full:" + entry["program_sha256"] in existing:
            collisions.append(
                {
                    "seed": entry["seed"],
                    "kind": "full_digest",
                    "against": existing["full:" + entry["program_sha256"]],
                }
            )
        if entry["semantic_sha256"] in seen:
            collisions.append(
                {
                    "seed": entry["seed"],
                    "kind": "internal",
                    "against": f"seed {seen[entry['semantic_sha256']]}",
                }
            )
        seen[entry["semantic_sha256"]] = entry["seed"]
    return collisions


# --------------------------------------------------------------------------
# Sampling streams (P1)
# --------------------------------------------------------------------------


def raw_bit_stream(
    domain: se.Domain,
    codec: str,
    seed: int,
    attempts: int,
    seconds: float,
    sink: Optional["AttemptSink"] = None,
    identity: Optional[dict] = None,
) -> dict:
    """Uniform draws from the code universe, decoded and counted.

    Every draw is retained. A failed attempt is never resampled invisibly, and
    the process-randomised ``hash()`` never takes part: the stream is a seeded
    ``random.Random`` and nothing else.
    """

    plan = se.layout(domain, codec)
    rng = random.Random(seed)
    return _run_stream(
        domain, codec, plan, attempts, seconds,
        lambda: rng.getrandbits(plan.width) if plan.width else 0,
        stream="raw_bits", seed=seed, sink=sink, identity=identity,
    )


def option_path_stream(
    domain: se.Domain,
    codec: str,
    seed: int,
    attempts: int,
    seconds: float,
    sink: Optional["AttemptSink"] = None,
    identity: Optional[dict] = None,
) -> dict:
    """Sequential uniform choices over the live option list at each decision.

    ``randrange(m)`` is called once per decision with ``m > 1``; no draw is made
    when ``m == 1``; the walk stops when ``m == 0``. The resulting ranks are
    assembled into the fixed layout, and the assembled index is then decoded by
    the ordinary decoder, so the recorded status comes from the same code path
    every other measurement uses.
    """

    plan = se.layout(domain, codec)
    rng = random.Random(seed)

    def draw() -> int:
        state = se.State(domain)
        index = 0
        if state.schedule_conflict() is not None:
            return 0
        for op_id in domain.selected_operations:
            legal = state.time_options(op_id)
            if not legal:
                return index
            rank = rng.randrange(len(legal)) if len(legal) > 1 else 0
            index |= plan.field(("time", op_id)).write(rank)
            state.times[op_id] = legal[rank]
        state.recompute_lifetimes()
        if state.fixed_address_conflict() is not None:
            return index
        for name in state.allocation_order():
            legal = state.address_options(name)
            if not legal:
                return index
            rank = rng.randrange(len(legal)) if len(legal) > 1 else 0
            index |= plan.field(("address", name)).write(rank)
            state.addresses[name] = legal[rank]
        return index

    return _run_stream(
        domain, codec, plan, attempts, seconds, draw, stream="option_paths", seed=seed,
        sink=sink, identity=identity,
    )


class AttemptSink:
    """Writes one raw JSONL row per sampling attempt, as it happens.

    Every attempt reaches disk. Until the 2026-09-23 repair the stream retained
    only totals, fifty distinct completed examples and twenty failures, so its
    160,000 draws could not be reconciled from raw rows at all. There is no cap
    here: a display excerpt is a separate, explicitly named field.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("w", encoding="utf-8")
        self.written = 0

    def write(self, row: dict) -> None:
        self.handle.write(se.canonical_json(row) + "\n")
        self.written += 1

    def close(self) -> None:
        self.handle.close()

    def __enter__(self) -> "AttemptSink":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class _ListSink:
    """The in-memory sink the unit tests use; the same interface as AttemptSink."""

    def __init__(self) -> None:
        self.rows: List[dict] = []
        self.written = 0

    def write(self, row: dict) -> None:
        self.rows.append(row)
        self.written += 1

    def close(self) -> None:
        return None


def _run_stream(domain, codec, plan, attempts, seconds, draw, stream, seed,
                sink=None, identity=None):
    """Returns ``(row, identities)``; the identity set is for the union only.

    Every attempt is streamed to ``sink`` as a raw row, and every completed
    decode is validated on **every** program case with the pinned validator
    before it is counted as a completion. ``se.decode`` checks static
    feasibility and ``machine.check_compilation``; neither of those runs a case,
    so before the 2026-09-23 repair no sampled public compilation was ever
    executed. Case execution is charged to the stream's own time budget, so a
    stream may draw fewer attempts and report itself incomplete rather than
    having its cap changed.

    A completed candidate the case validator rejects is a defect: the artifact is
    retained in ``discrepancies`` and the caller fails. It is never converted to
    ``DEAD_END`` and never dropped.
    """

    if sink is None:
        sink = _ListSink()
    fixed = dict(identity or {})
    fixed.update(
        {
            "stream": stream,
            "seed": seed,
            "codec": codec,
            "domain_id": domain.identifier,
            "domain_sha256": domain.digest(),
            "bits": plan.width,
        }
    )

    counts = {status: 0 for status in se.STATUSES}
    distinct: Dict[str, int] = {}
    multiplicities: Dict[str, int] = {}
    examples: List[dict] = []
    started = time.perf_counter()
    drawn = 0
    complete_rows: List[dict] = []
    case_checks = 0
    case_failures = 0
    discrepancies: List[dict] = []
    cases = list(domain.program["cases"])
    # One sink serves every stream of the stage, so the reconciliation below
    # compares the rows *this* stream contributed, not the file's running total.
    rows_before = sink.written
    for attempt in range(attempts):
        if time.perf_counter() - started > seconds:
            break
        index = draw()
        drawn += 1
        result = se.decode(domain, index, codec)
        counts[result.status] += 1
        row = dict(fixed)
        row.update(
            {
                "attempt": attempt,
                "index": str(index),
                "status": result.status,
                "reason": result.reason,
                "decisions": len(result.decisions),
                "trace_reference": result.trace_reference,
                "compilation_sha256": result.identity,
                "cases_declared": len(cases),
                "cases_checked": 0,
                "case_failures": 0,
            }
        )
        if result.status == se.COMPLETE:
            checked = 0
            failure: Optional[str] = None
            for case in cases:
                try:
                    machine.check_case(domain.program, result.compilation, case)
                except (machine.CompileError, machine.ProgramError) as exc:
                    failure = str(exc)
                    break
                checked += 1
            case_checks += checked
            row["cases_checked"] = checked
            if failure is not None:
                case_failures += 1
                row["case_failures"] = 1
                row["case_failure_reason"] = failure
                discrepancies.append(
                    {
                        "kind": "sampled_completion_failed_case",
                        "stream": stream,
                        "attempt": attempt,
                        "index": str(index),
                        "domain_id": domain.identifier,
                        "domain_sha256": domain.digest(),
                        "codec": codec,
                        "compilation_sha256": result.identity,
                        "times": {str(k): v for k, v in sorted((result.times or {}).items())},
                        "addresses": dict(sorted((result.addresses or {}).items())),
                        "validator_message": failure,
                        "cases_passed_before_failure": checked,
                    }
                )
            multiplicities[result.identity] = multiplicities.get(result.identity, 0) + 1
            if result.identity not in distinct:
                distinct[result.identity] = index
                # The full decoder row of every first sighting, uncapped: this is
                # what makes each completion independently replayable.
                complete_rows.append(result.to_row() | {"attempt": attempt})
        elif len(examples) < 20:
            examples.append(result.to_row() | {"attempt": attempt})
        sink.write(row)
    elapsed = time.perf_counter() - started

    total = sum(counts.values())
    if total != drawn:
        raise StageBlocked(FAIL, "stream accounting does not reconcile")
    written = sink.written - rows_before
    if written != drawn:
        raise StageBlocked(
            FAIL, f"{written} raw rows were written for {drawn} draws"
        )
    return {
        "stream": stream,
        "seed": seed,
        "codec": codec,
        "domain_id": domain.identifier,
        "domain_sha256": domain.digest(),
        "bits": plan.width,
        "attempts_requested": attempts,
        "attempts_drawn": drawn,
        "raw_rows_written": written,
        "complete": counts[se.COMPLETE],
        "invalid_code": counts[se.INVALID_CODE],
        "dead_end": counts[se.DEAD_END],
        "interrupted": counts[se.INTERRUPTED],
        "distinct_complete": len(distinct),
        "max_multiplicity": max(multiplicities.values(), default=0),
        "cases_declared": len(cases),
        "case_checks": case_checks,
        "case_failures": case_failures,
        "discrepancies": discrepancies,
        "discrepancy_count": len(discrepancies),
        "completions": complete_rows,
        "complete_examples_excerpt": complete_rows[:50],
        "failure_examples": examples,
        "identity_multiplicities": {
            key: multiplicities[key] for key in sorted(multiplicities)
        },
        "seconds": elapsed,
        "incomplete": drawn < attempts,
        "incomplete_reason": (
            "time cap reached before the requested attempts" if drawn < attempts else None
        ),
    }, set(distinct)


# --------------------------------------------------------------------------
# Bound admissibility (P2, acceptance check C13)
# --------------------------------------------------------------------------


def bound_admissibility(domain: se.Domain) -> dict:
    """Compare every prefix bound with every completion of that prefix.

    A bound that exceeds any completion's objective is not admissible and the
    pruning arm is unsound. Only the tiny fixtures are small enough for this to
    be exhaustive, which is exactly why the contract asks for it there.
    """

    facts = domain.facts
    violations: List[dict] = []
    checks = 0

    def completions(state: se.State, position: int) -> List[int]:
        nonlocal checks
        if position == len(domain.selected_operations):
            state.recompute_lifetimes()
            if state.fixed_address_conflict() is not None:
                return []
            return allocate(state, state.allocation_order(), 0)
        op_id = domain.selected_operations[position]
        found: List[int] = []
        for value in state.time_options(op_id):
            nxt = state.copy()
            nxt.times[op_id] = value
            found.extend(completions(nxt, position + 1))
        bound = ss.cycle_bound(facts, state.times) * ss.scratch_bound(
            facts, state.addresses, None
        )
        checks += 1
        for objective in found:
            if bound > objective:
                violations.append(
                    {
                        "phase": "schedule",
                        "position": position,
                        "bound": bound,
                        "completion": objective,
                        "times": {str(k): v for k, v in sorted(state.times.items())},
                    }
                )
        return found

    def allocate(state: se.State, order: Sequence[str], position: int) -> List[int]:
        nonlocal checks
        live_width = ss.peak_live_width(facts, state.lifetimes)
        if position == len(order):
            _, _, product = se.objective(facts, state.times, state.addresses)
            return [product]
        name = order[position]
        found: List[int] = []
        for value in state.address_options(name):
            nxt = state.copy()
            nxt.addresses[name] = value
            found.extend(allocate(nxt, order, position + 1))
        bound = ss.cycle_bound(facts, state.times) * ss.scratch_bound(
            facts, state.addresses, live_width
        )
        checks += 1
        for objective in found:
            if bound > objective:
                violations.append(
                    {
                        "phase": "allocate",
                        "position": position,
                        "bound": bound,
                        "completion": objective,
                        "addresses": dict(sorted(state.addresses.items())),
                    }
                )
        return found

    root = se.State(domain)
    if root.schedule_conflict() is not None:
        return {
            "domain_id": domain.identifier,
            "prefixes_checked": 0,
            "completions": 0,
            "violations": [],
            "status": NOT_APPLICABLE,
            "reason": "the fixed decisions contradict each other",
        }
    found = completions(root, 0)
    return {
        "domain_id": domain.identifier,
        "domain_sha256": domain.digest(),
        "prefixes_checked": checks,
        "completions": len(found),
        "violations": violations[:20],
        "violation_count": len(violations),
        "status": FAIL if violations else PASS,
        "reason": (
            "a prefix bound exceeded a completion objective" if violations
            else "no bound exceeded any completion of its prefix"
        ),
    }


# --------------------------------------------------------------------------
# The structural optimisation driver and the measurement worker
# --------------------------------------------------------------------------


def structural_optimise(
    program: dict,
    facts: dc.ProgramFacts,
    times: Dict[int, int],
    addresses: Dict[str, int],
    arm: str,
    budget_seconds: float,
    query_seconds: float,
    max_queries: int,
    limits: dict,
    elite_fraction: float = 0.1,
) -> Tuple[Dict[int, int], Dict[str, int], dict]:
    """Improve the bootstrap incumbent through matched or expanded structural search.

    The matched arms reuse ``direct_optimizer.targets_for`` and ``windows_for``
    on the same current incumbent with the original ``max_queries``, so the only
    thing that differs from the accepted optimiser is the representation and the
    search. Domain construction, decoding and validation are all inside the same
    ``budget_seconds`` deadline; the measured overshoot is reported rather than
    presented as exact wall-clock equality.
    """

    started = time.perf_counter()
    deadline = started + budget_seconds
    statuses = {
        "SAT": 0, "UNSAT": 0, "UNKNOWN_SEARCH": 0,
        "UNKNOWN_CONSTRUCTION": 0, "INFEASIBLE": 0, "FAIL": 0,
    }
    queries: List[dict] = []
    improvements: List[dict] = []
    rejected: List[dict] = []
    attempted: set = set()
    interrupted: List[dict] = []
    stopped = "pass_complete"
    best_times, best_addresses = dict(times), dict(addresses)

    def search_budget(remaining: float) -> si.Budget:
        """The meter's relative allowance, never larger than what is left.

        ``si.Budget`` refuses a non-positive ``seconds``, so an expired interval
        is handled by the caller before this is reached rather than by inventing
        a positive allowance with ``max``. The floor here exists only because the
        owner's dataclass rejects zero; the absolute ``deadline`` passed beside it
        is what actually stops the search.
        """

        return si.Budget(
            seconds=max(remaining, 1e-9),
            max_cover=limits["query_max_cover"],
            max_visited=limits["search_max_nodes"],
            max_records=limits["search_max_candidate_validations"],
        )

    if arm == "structural_expanded":
        incumbent = dc.compilation(facts, best_times, best_addresses)
        attempted.add(("expanded",))
        if time.perf_counter() >= deadline:
            stopped = "deadline"
            interrupted.append({"phase": "before_construction", "window": None})
        else:
            record = whole_program_record(
                f"{program['name']}::expanded", "expanded", program, facts, incumbent
            )
            domain = se.Domain.from_record(record)
            # Construction has just spent part of the allowance. Recompute what
            # is left rather than reusing the figure captured before it.
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                stopped = "deadline"
                interrupted.append(
                    {"phase": "after_construction", "window": None,
                     "domain_sha256": domain.digest()}
                )
            else:
                report = ss.search(
                    domain, incumbent, arm, search_budget(remaining), deadline=deadline
                )
                statuses_key = {
                    "SAT": "SAT", "UNSAT": "UNSAT",
                    "UNKNOWN": "UNKNOWN_SEARCH", "FAIL": "FAIL",
                }[report.status]
                statuses[statuses_key] += 1
                queries.append(
                    {
                        "domain_sha256": domain.digest(),
                        "domain_id": domain.identifier,
                        "bits": se.layout(domain, "structural_rank").width,
                        "window": None,
                        "target": None,
                        "report": report.to_row(),
                    }
                )
                rejected.extend(report.rejected_completions)
                if report.interrupted_validations:
                    interrupted.append(
                        {"phase": "validation", "window": None,
                         "count": report.interrupted_validations}
                    )
                if report.improved and report.best_times is not None:
                    best_times, best_addresses = report.best_times, report.best_addresses
                    improvements.append(
                        {"window": None, "target": None, "product": report.best_product}
                    )
                if report.deadline_expired:
                    stopped = "deadline"
        return best_times, best_addresses, _optimisation_record(
            arm, started, budget_seconds, statuses, queries, improvements,
            rejected, attempted, stopped, max_queries, interrupted,
        )

    if arm == MODEL_ARM:
        return _model_optimise(
            program, facts, best_times, best_addresses, started, deadline,
            budget_seconds, query_seconds, max_queries, limits, search_budget,
            elite_fraction,
        )

    improved = True
    while improved:
        improved = False
        cycles = max(best_times.values()) + 1
        memory = dc.footprint(facts, best_addresses)
        product = cycles * memory
        digest = se.object_digest(
            {
                "t": {str(k): v for k, v in sorted(best_times.items())},
                "a": dict(sorted(best_addresses.items())),
            }
        )
        for target_cycles, target_memory in dopt.targets_for(facts, cycles, memory):
            windows = dopt.windows_for(
                facts, best_times, best_addresses, scratch_first=target_memory < memory
            )
            for window in windows:
                if len(attempted) >= max_queries:
                    stopped = "query_cap"
                    break
                if time.perf_counter() >= deadline:
                    stopped = "deadline"
                    break
                key = (digest, window, target_cycles, target_memory)
                if key in attempted:
                    continue
                attempted.add(key)
                # One absolute allowance per query, established *before* domain
                # construction and never renewed after it.
                query_deadline = min(time.perf_counter() + query_seconds, deadline)
                if time.perf_counter() >= query_deadline:
                    stopped = "deadline"
                    interrupted.append(
                        {"phase": "before_construction", "window": list(window)}
                    )
                    break

                entry = {"window": list(window), "target": [target_cycles, target_memory]}
                try:
                    record = matched_window_record(
                        f"{program['name']}::{'-'.join(map(str, window))}"
                        f"::{target_cycles}x{target_memory}",
                        "matched", program, facts, best_times, best_addresses,
                        window, target_cycles, target_memory,
                    )
                    domain = se.Domain.from_record(record)
                except dk.Infeasible as exc:
                    statuses["INFEASIBLE"] += 1
                    entry.update(status="INFEASIBLE", reason=str(exc), domain_sha256=None)
                    queries.append(entry)
                    continue
                except se.DomainError as exc:
                    statuses["UNKNOWN_CONSTRUCTION"] += 1
                    entry.update(status="UNKNOWN_CONSTRUCTION", reason=str(exc))
                    queries.append(entry)
                    continue

                entry["domain_sha256"] = domain.digest()
                entry["domain_id"] = domain.identifier
                entry["bits"] = se.layout(domain, "structural_rank").width
                # Construction is uninterruptible; expiry is checked immediately
                # after it and what is left is recomputed, never restored.
                remaining = query_deadline - time.perf_counter()
                entry["remaining_after_construction_seconds"] = remaining
                if remaining <= 0:
                    statuses["UNKNOWN_CONSTRUCTION"] += 1
                    entry.update(
                        status="UNKNOWN_CONSTRUCTION",
                        reason="the query allowance expired during domain construction",
                    )
                    queries.append(entry)
                    interrupted.append(
                        {"phase": "after_construction", "window": list(window),
                         "domain_sha256": domain.digest()}
                    )
                    stopped = "deadline"
                    break
                report = ss.search(
                    domain, record["incumbent"], arm, search_budget(remaining),
                    deadline=query_deadline,
                )
                entry["report"] = report.to_row()
                entry["status"] = report.status
                queries.append(entry)
                rejected.extend(report.rejected_completions)
                if report.interrupted_validations:
                    interrupted.append(
                        {"phase": "validation", "window": list(window),
                         "count": report.interrupted_validations}
                    )
                statuses[
                    {"SAT": "SAT", "UNSAT": "UNSAT",
                     "UNKNOWN": "UNKNOWN_SEARCH", "FAIL": "FAIL"}[report.status]
                ] += 1

                if report.improved and report.best_product is not None \
                        and report.best_product < product:
                    best_times, best_addresses = report.best_times, report.best_addresses
                    improvements.append(
                        {
                            "window": list(window),
                            "target": [target_cycles, target_memory],
                            "from": product,
                            "to": report.best_product,
                        }
                    )
                    improved = True
                    break
            if improved or stopped != "pass_complete":
                break
        if stopped != "pass_complete":
            break

    return best_times, best_addresses, _optimisation_record(
        arm, started, budget_seconds, statuses, queries, improvements,
        rejected, attempted, stopped, max_queries, interrupted,
    )


class _Expired(Exception):
    """The query allowance ran out inside a lazily generated proposal stream."""


def _model_optimise(
    program: dict,
    facts: dc.ProgramFacts,
    best_times: Dict[int, int],
    best_addresses: Dict[str, int],
    started: float,
    deadline: float,
    budget_seconds: float,
    query_seconds: float,
    max_queries: int,
    limits: dict,
    search_budget,
    elite_fraction: float = 0.1,
) -> Tuple[Dict[int, int], Dict[str, int], dict]:
    """The conditional ``structural_model`` arm of contract section 5.

    Authorised only when H4 advances. At each matched query the allowance is
    ``A = min(query_seconds, remaining global time)``, fixed once: the first half
    runs ``structural_bound`` on the matched domain and collects every complete
    observation it pays for, the elite top decile of those observations (ties
    included) is frozen, and the second half spends what is left walking the
    one-coordinate expansion of an exact cover of that elite. The phase fractions
    are of that one fixed allowance and are never renewed.

    If the first half produces no complete observation the query records the model
    as unavailable and retains the incumbent. There is no fallback search: that
    would be a second, unbudgeted arm wearing this arm's name.

    No state crosses a query or a program. The model is rebuilt from the
    observations of the query it serves.
    """

    arm = MODEL_ARM
    statuses = {
        "SAT": 0, "UNSAT": 0, "UNKNOWN_SEARCH": 0,
        "UNKNOWN_CONSTRUCTION": 0, "INFEASIBLE": 0, "FAIL": 0,
    }
    queries: List[dict] = []
    improvements: List[dict] = []
    rejected: List[dict] = []
    attempted: set = set()
    interrupted: List[dict] = []
    phases = {
        "search_seconds": 0.0, "model_seconds": 0.0, "proposal_seconds": 0.0,
        "observations": 0, "elite": 0, "proposals": 0, "duplicates": 0,
        "invalid_code": 0, "dead_end": 0, "complete": 0, "validations": 0,
        "case_checks": 0, "model_unavailable": 0, "cover_inconclusive": 0,
    }
    stopped = "pass_complete"
    improved = True
    while improved:
        improved = False
        cycles = max(best_times.values()) + 1
        memory = dc.footprint(facts, best_addresses)
        product = cycles * memory
        digest = se.object_digest(
            {
                "t": {str(k): v for k, v in sorted(best_times.items())},
                "a": dict(sorted(best_addresses.items())),
            }
        )
        for target_cycles, target_memory in dopt.targets_for(facts, cycles, memory):
            windows = dopt.windows_for(
                facts, best_times, best_addresses, scratch_first=target_memory < memory
            )
            for window in windows:
                if len(attempted) >= max_queries:
                    stopped = "query_cap"
                    break
                if time.perf_counter() >= deadline:
                    stopped = "deadline"
                    break
                key = (digest, window, target_cycles, target_memory)
                if key in attempted:
                    continue
                attempted.add(key)

                allowance = min(query_seconds, deadline - time.perf_counter())
                if allowance <= 0:
                    stopped = "deadline"
                    interrupted.append(
                        {"phase": "before_construction", "window": list(window)}
                    )
                    break
                query_started = time.perf_counter()
                query_deadline = query_started + allowance
                half_deadline = query_started + allowance / 2

                entry = {
                    "window": list(window),
                    "target": [target_cycles, target_memory],
                    "allowance_seconds": allowance,
                    "phase_split_seconds": allowance / 2,
                }
                try:
                    record = matched_window_record(
                        f"{program['name']}::{'-'.join(map(str, window))}"
                        f"::{target_cycles}x{target_memory}",
                        "matched", program, facts, best_times, best_addresses,
                        window, target_cycles, target_memory,
                    )
                    domain = se.Domain.from_record(record)
                except dk.Infeasible as exc:
                    statuses["INFEASIBLE"] += 1
                    entry.update(status="INFEASIBLE", reason=str(exc), domain_sha256=None)
                    queries.append(entry)
                    continue
                except se.DomainError as exc:
                    statuses["UNKNOWN_CONSTRUCTION"] += 1
                    entry.update(status="UNKNOWN_CONSTRUCTION", reason=str(exc))
                    queries.append(entry)
                    continue

                codec = "structural_rank"
                bits = se.layout(domain, codec).width
                entry["domain_sha256"] = domain.digest()
                entry["domain_id"] = domain.identifier
                entry["bits"] = bits

                remaining = half_deadline - time.perf_counter()
                if remaining <= 0:
                    statuses["UNKNOWN_CONSTRUCTION"] += 1
                    entry.update(
                        status="UNKNOWN_CONSTRUCTION",
                        reason="the search half expired during domain construction",
                    )
                    queries.append(entry)
                    interrupted.append(
                        {"phase": "after_construction", "window": list(window),
                         "domain_sha256": domain.digest()}
                    )
                    stopped = "deadline"
                    break

                observations: List[dict] = []
                search_started = time.perf_counter()
                report = ss.search(
                    domain, record["incumbent"], "structural_bound",
                    search_budget(remaining), deadline=half_deadline,
                    observe=observations.append,
                )
                phases["search_seconds"] += time.perf_counter() - search_started
                phases["observations"] += len(observations)
                entry["search_report"] = report.to_row()
                entry["observations"] = len(observations)
                rejected.extend(report.rejected_completions)
                if report.interrupted_validations:
                    interrupted.append(
                        {"phase": "validation", "window": list(window),
                         "count": report.interrupted_validations}
                    )
                statuses[
                    {"SAT": "SAT", "UNSAT": "UNSAT",
                     "UNKNOWN": "UNKNOWN_SEARCH", "FAIL": "FAIL"}[report.status]
                ] += 1
                entry["status"] = report.status

                accepted_from = None
                if report.improved and report.best_product is not None \
                        and report.best_product < product:
                    best_times, best_addresses = report.best_times, report.best_addresses
                    accepted_from = "search"

                if not observations:
                    # No paid complete observation, so there is nothing to build a
                    # model from. The incumbent stands and no extra search runs.
                    phases["model_unavailable"] += 1
                    entry["model"] = {
                        "status": NOT_APPLICABLE,
                        "reason": "no complete observation was paid for in the search half",
                    }
                    queries.append(entry)
                    if accepted_from:
                        improvements.append(
                            {"window": list(window),
                             "target": [target_cycles, target_memory],
                             "from": product, "to": report.best_product,
                             "source": accepted_from}
                        )
                        improved = True
                        break
                    continue

                # Freeze the elite top decile of the observations, ties included.
                products = [item["product"] for item in observations]
                threshold = _elite_threshold(products, elite_fraction)
                elite_records = [
                    item for item in observations if item["product"] <= threshold
                ]
                model_started = time.perf_counter()
                elite_indices: List[int] = []
                encode_failures = 0
                for item in elite_records:
                    try:
                        elite_indices.append(se.encode(domain, item["compilation"], codec))
                    except se.DomainError:
                        encode_failures += 1
                elite_indices = sorted(set(elite_indices))
                phases["elite"] += len(elite_indices)
                cover = sm.exact_cover(
                    elite_indices, bits, limits["cover_max_cubes"],
                    max(min(limits["cover_seconds_per_set"],
                            query_deadline - time.perf_counter()), 1e-9),
                )
                phases["model_seconds"] += time.perf_counter() - model_started
                model_entry = {
                    "threshold": threshold,
                    "elite": len(elite_indices),
                    "encode_failures": encode_failures,
                    "cover_status": cover.status,
                    "cover_cubes": len(cover.cubes),
                }
                if cover.status != "COMPLETE":
                    # An interrupted cover is inconclusive, never exact evidence.
                    phases["cover_inconclusive"] += 1
                    model_entry.update(
                        status=INCONCLUSIVE, reason=f"the elite cover is {cover.status}"
                    )
                    entry["model"] = model_entry
                    queries.append(entry)
                    if accepted_from:
                        improvements.append(
                            {"window": list(window),
                             "target": [target_cycles, target_memory],
                             "from": product, "to": report.best_product,
                             "source": accepted_from}
                        )
                        improved = True
                        break
                    continue

                # The proposal half: one-coordinate expansion, walked lazily in
                # ascending order under the remaining part of the fixed allowance.
                proposal_started = time.perf_counter()
                evaluated: set = set(elite_indices)
                counts = {
                    "attempted": 0, "duplicate": 0, "invalid_code": 0,
                    "dead_end": 0, "interrupted": 0, "complete": 0,
                    "validations": 0, "case_checks": 0, "exhausted": False,
                }
                best_product_here = (
                    report.best_product if accepted_from else product
                )
                best_pair = None

                def check() -> None:
                    if time.perf_counter() >= query_deadline:
                        raise _Expired

                stream = sm.proposals(
                    "model_expand", bits, elite_indices, cover.cubes, evaluated,
                    None, budget_check=check,
                )
                try:
                    while True:
                        check()
                        try:
                            index, duplicate = next(stream)
                        except StopIteration:
                            counts["exhausted"] = True
                            break
                        counts["attempted"] += 1
                        if duplicate or index in evaluated:
                            counts["duplicate"] += 1
                            continue
                        evaluated.add(index)
                        result = se.decode(domain, index, codec)
                        if result.status == se.INVALID_CODE:
                            counts["invalid_code"] += 1
                            continue
                        if result.status == se.DEAD_END:
                            counts["dead_end"] += 1
                            continue
                        if result.status == se.INTERRUPTED:
                            counts["interrupted"] += 1
                            continue
                        counts["complete"] += 1
                        if result.product is None or result.product >= best_product_here:
                            continue
                        check()
                        counts["validations"] += 1
                        try:
                            machine.check_compilation(domain.program, result.compilation)
                            for case in domain.program["cases"]:
                                machine.check_case(
                                    domain.program, result.compilation, case
                                )
                                counts["case_checks"] += 1
                        except (machine.CompileError, machine.ProgramError) as exc:
                            rejected.append(
                                {
                                    "identity": result.identity,
                                    "index": str(index),
                                    "error": str(exc),
                                    "source": "model_expand",
                                }
                            )
                            continue
                        if time.perf_counter() >= query_deadline:
                            # Validation crossed the deadline: the incumbent stands
                            # and the attempt is accounted, not accepted.
                            interrupted.append(
                                {"phase": "model_validation", "window": list(window),
                                 "index": str(index)}
                            )
                            break
                        best_product_here = result.product
                        best_pair = (dict(result.times), dict(result.addresses))
                except _Expired:
                    interrupted.append(
                        {"phase": "model_proposals", "window": list(window)}
                    )
                phases["proposal_seconds"] += time.perf_counter() - proposal_started
                for name in ("attempted", "duplicate", "invalid_code", "dead_end",
                             "complete", "validations", "case_checks"):
                    phases[{"attempted": "proposals", "duplicate": "duplicates"}
                           .get(name, name)] += counts[name]
                model_entry.update(status=PASS, counts=counts)
                entry["model"] = model_entry
                queries.append(entry)

                if best_pair is not None:
                    best_times, best_addresses = best_pair
                    accepted_from = "model"
                if accepted_from:
                    improvements.append(
                        {"window": list(window),
                         "target": [target_cycles, target_memory],
                         "from": product, "to": best_product_here,
                         "source": accepted_from}
                    )
                    improved = True
                    break
            if improved or stopped != "pass_complete":
                break
        if stopped != "pass_complete":
            break

    return best_times, best_addresses, _optimisation_record(
        arm, started, budget_seconds, statuses, queries, improvements,
        rejected, attempted, stopped, max_queries, interrupted, phases,
    )


def _optimisation_record(
    arm, started, budget_seconds, statuses, queries, improvements,
    rejected, attempted, stopped, max_queries, interrupted=(), phases=None,
) -> dict:
    elapsed = time.perf_counter() - started
    return {
        "arm": arm,
        "enabled": True,
        "budget_seconds": budget_seconds,
        "max_queries": max_queries,
        "attempted_queries": len(attempted),
        "recorded_queries": len(queries),
        "statuses": statuses,
        "accepted": len(improvements),
        "improvements": improvements,
        "rejected_completions": rejected,
        "discrepancy_count": len(rejected),
        "stopped_because": stopped,
        "seconds": elapsed,
        # Measured overshoot of an uninterruptible call, kept distinct from a
        # renewed budget: no allowance here is ever restored after expiry.
        "overshoot_seconds": elapsed - budget_seconds,
        "interrupted_attempts": list(interrupted),
        "interrupted_attempt_count": len(list(interrupted)),
        "budget_renewals": 0,
        "phases": phases,
        "queries": queries,
    }


WORKER_ARMS = ACCEPTED_ARMS + STRUCTURAL_ARMS + (MODEL_ARM,)


def run_measurement(spec: dict) -> dict:
    """One measurement, in this process. The harness runs it in a fresh one.

    This is an internal entry point. It validates its own identity and refuses
    a spec it does not recognise; it is not an alternative acceptance mode.
    """

    if spec.get("kind") != "phase2_measurement":
        raise StageBlocked(FAIL, "worker spec is not a phase 2 measurement")
    arm = spec["arm"]
    if arm not in WORKER_ARMS:
        raise StageBlocked(FAIL, f"unknown measurement arm {arm!r}")

    import_seconds = spec.get("import_seconds", 0.0)
    program = machine.load_program(spec["program_path"])
    budget = spec.get("budget_seconds")
    limits_payload = spec["limits"]

    cpu_started = time.process_time()
    started = time.perf_counter()
    facts = dc.derive(program)

    if arm in ACCEPTED_ARMS:
        if arm == "accepted_budgeted":
            limits = dcomp.Limits(
                optimise_seconds=budget, query_seconds=min(0.1, budget)
            )
            optimise = True
        else:
            limits = dcomp.DEFAULT_LIMITS
            optimise = arm == "accepted_default"
        compiled, report = dcomp.compile_with_report(program, limits, optimise=optimise)
        bootstrap_seconds = report["bootstrap"]["seconds"]
        optimisation = report.get("optimisation", {})
        times = None
    else:
        bootstrap_compiled, bootstrap_report = dcomp.compile_with_report(
            program, dcomp.DEFAULT_LIMITS, optimise=False
        )
        bootstrap_seconds = bootstrap_report["bootstrap"]["seconds"]
        times = se.issue_cycles_of(program, bootstrap_compiled["bundles"])
        addresses = dict(bootstrap_compiled["scratch"])
        best_times, best_addresses, optimisation = structural_optimise(
            program, facts, times, addresses, arm, budget,
            min(0.1, budget), dcomp.DEFAULT_LIMITS.max_queries, limits_payload,
            elite_fraction=spec.get("elite_fraction", 0.1),
        )
        compiled = dc.compilation(facts, best_times, best_addresses)
        report = {"limits": {"optimise_seconds": budget, "query_seconds": min(0.1, budget)}}
    compile_seconds = time.perf_counter() - started
    cpu_seconds = time.process_time() - cpu_started

    validate_started = time.perf_counter()
    cycles = machine.check_compilation(program, compiled)
    cases = 0
    for case in program["cases"]:
        machine.check_case(program, compiled, case)
        cases += 1
    scratch = machine.scratch_footprint(program, compiled)
    validate_seconds = time.perf_counter() - validate_started

    return {
        "kind": "phase2_measurement_result",
        "stage": spec["stage"],
        "corpus": spec["corpus"],
        "program_name": program["name"],
        "program_sha256": spec["program_sha256"],
        "domain_sha256": spec.get("domain_sha256"),
        "codec": spec.get("codec"),
        "arm": arm,
        "budget_seconds": budget,
        "search_seed": spec.get("search_seed"),
        "repetition": spec["repetition"],
        "attempt": spec.get("attempt", 0),
        "cycles": cycles,
        "scratch": scratch,
        "product": cycles * scratch,
        "cases": cases,
        "import_seconds": import_seconds,
        "bootstrap_seconds": bootstrap_seconds,
        "compile_seconds": compile_seconds,
        "cpu_seconds": cpu_seconds,
        "validate_seconds": validate_seconds,
        "peak_rss_bytes": official.peak_rss_bytes(),
        "peak_rss_conversion": "darwin:bytes" if sys.platform == "darwin" else "posix:kilobytes",
        "limits": report.get("limits"),
        "optimisation": optimisation,
        "discrepancy_count": optimisation.get("discrepancy_count", 0),
        "original_incumbent_sha256": spec.get("incumbent_sha256"),
        "best_incumbent_sha256": se.object_digest(
            se.normalise_compilation(facts, compiled)
        ),
        "correctness": "PASS",
    }


# --------------------------------------------------------------------------
# Subprocess harness
# --------------------------------------------------------------------------


class Harness:
    """Runs one measurement per fresh process and records the exact command."""

    def __init__(self, run_root: Path, timeout: float) -> None:
        self.run_root = Path(run_root)
        self.timeout = timeout
        self.commands: List[dict] = []

    def command_for(self, spec: dict) -> List[str]:
        return [
            sys.executable,
            "-m",
            "research.run_structural_experiments",
            "--worker",
            se.canonical_json(spec),
        ]

    def run(self, spec: dict) -> dict:
        command = self.command_for(spec)
        environment = dict(os.environ)
        environment["PYTHONPATH"] = f"{ROOT / '.reference'}{os.pathsep}{ROOT}"
        started = time.perf_counter()
        timed_out = False
        try:
            proc = subprocess.run(
                command, cwd=str(ROOT), capture_output=True, text=True,
                timeout=self.timeout, env=environment,
            )
            stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            code = None
        process_seconds = time.perf_counter() - started

        row: dict = {
            "stage": spec["stage"],
            "corpus": spec["corpus"],
            "program_sha256": spec["program_sha256"],
            "domain_sha256": spec.get("domain_sha256"),
            "codec": spec.get("codec"),
            "arm": spec["arm"],
            "budget_seconds": spec.get("budget_seconds"),
            "search_seed": spec.get("search_seed"),
            "repetition": spec["repetition"],
            "attempt": spec.get("attempt", 0),
            "exit_code": code,
            "timed_out": timed_out,
            "process_seconds": process_seconds,
            "stderr_tail": stderr[-2000:],
        }
        parsed = None
        if not timed_out and code == 0 and stdout.strip():
            try:
                parsed = json.loads(stdout.strip().splitlines()[-1])
            except json.JSONDecodeError as exc:
                row["failure"] = f"worker stdout was not one JSON object: {exc}"
        if parsed is not None and parsed.get("kind") == "phase2_measurement_result":
            row.update({key: value for key, value in parsed.items() if key != "kind"})
            row["correctness"] = parsed.get("correctness", "PASS")
            row["failed_row"] = False
        else:
            # A crash, a timeout, a missing output or an invalid incumbent is a
            # failed row. It is retained and it blocks a success claim; it is
            # never a timing outlier and never imputed away.
            row.setdefault("failure", "worker produced no valid result")
            row["failed_row"] = True
            row["correctness"] = "FAIL"

        self.commands.append(
            {
                "command": command[:4] + ["<spec>"],
                "spec": spec,
                "exit_code": code,
                "timed_out": timed_out,
                "process_seconds": process_seconds,
            }
        )
        return row


def arm_schedule(
    programs: Sequence[dict],
    budgets: Sequence[float],
    unbudgeted: Sequence[str],
    budgeted: Sequence[str],
    rng: random.Random,
    repetitions: int,
) -> List[Tuple[dict, Optional[float], Optional[int], int, str]]:
    """Balanced arm order, exactly as contract section 9 specifies.

    Programs in manifest order, budgets ascending with the unbudgeted block
    first, then seeds ascending with ``null`` first. Within each block the
    sorted arm list is shuffled once from the stage RNG and rotated by the
    repetition index.
    """

    schedule: List[Tuple[dict, Optional[float], Optional[int], int, str]] = []
    for program in programs:
        for budget in [None] + sorted(budgets):
            arms = sorted(unbudgeted) if budget is None else sorted(budgeted)
            if not arms:
                continue
            for seed in [None]:
                shuffled = list(arms)
                rng.shuffle(shuffled)
                for repetition in range(repetitions):
                    rotation = repetition % len(shuffled)
                    order = shuffled[rotation:] + shuffled[:rotation]
                    for arm in order:
                        schedule.append((program, budget, seed, repetition, arm))
    return schedule


def expected_keys(
    programs: Sequence[dict],
    budgets: Sequence[float],
    unbudgeted: Sequence[str],
    budgeted: Sequence[str],
    repetitions: int,
) -> List[List[object]]:
    """The exact membership a checker must find, derived from frozen policy."""

    keys: List[List[object]] = []
    for program in programs:
        for budget in [None] + sorted(budgets):
            for arm in (sorted(unbudgeted) if budget is None else sorted(budgeted)):
                for repetition in range(repetitions):
                    keys.append([program["program_sha256"], budget, arm, None, repetition])
    return keys


# --------------------------------------------------------------------------
# Stages
# --------------------------------------------------------------------------


class Run:
    """One run directory and the state the stages share through it."""

    def __init__(self, run_id: str, contract: Contract, inputs: Optional[Path]) -> None:
        if not RUN_ID_PATTERN.match(run_id):
            raise StageBlocked(FAIL, "a run id holds only letters, digits, underscore, hyphen")
        self.run_id = run_id
        self.contract = contract
        self.root = RESULTS / run_id
        # Exclusive creation: an existing run is refused, never overwritten.
        self.root.mkdir(parents=True, exist_ok=False)
        (self.root / "logs").mkdir()
        (self.root / "inputs").mkdir()
        self.inputs = Path(inputs) if inputs else None
        self._imported_manifest: Optional[dict] = None
        self.gates: Dict[str, dict] = {}
        # Where each dependency's artifacts actually live. A stage imported with
        # --inputs keeps its own root, so relative paths inside its summary
        # resolve against the run that produced them, not against this one.
        self.prior_root: Dict[str, Path] = {}
        self.started = time.time()
        self.harness = Harness(self.root, contract.budgets["external_process_seconds"])

    # -- stage bookkeeping ------------------------------------------------

    def stage_dir(self, stage: str) -> Path:
        path = self.root / stage
        path.mkdir(parents=True, exist_ok=True)
        return path

    def record(self, stage: str, status: str, reason: str, evidence: dict) -> None:
        self.gates[stage] = {"status": status, "reason": reason, "evidence": evidence}

    # -- dependency import ------------------------------------------------

    @property
    def imported_manifest(self) -> Optional[dict]:
        if self.inputs is None:
            return None
        if self._imported_manifest is None:
            path = self.inputs / "manifest.json"
            if not path.is_file():
                raise StageBlocked(FAIL, f"--inputs {self.inputs} has no manifest")
            self._imported_manifest = json.loads(path.read_text())
        return self._imported_manifest

    def dependency_status(self, stage: str) -> Tuple[str, str]:
        """``(status, source)`` for one dependency, local first, then imported.

        A dependency that neither ran here nor was supplied is ``BLOCKED_BY_GATE``.
        An imported dependency is only usable when the prior run recorded it PASS:
        before the 2026-09-23 repair nothing required that, so a stage could be
        entered on an INCONCLUSIVE dependency simply by passing ``--inputs``.
        """

        if stage in self.gates:
            return self.gates[stage]["status"], "local"
        manifest = self.imported_manifest
        if manifest is None:
            return BLOCKED, "absent"
        recorded = (manifest.get("stage_status") or {}).get(stage)
        if recorded is None:
            return BLOCKED, "absent"
        return recorded, "imported"

    def verify_imported(self, stage: str) -> None:
        """Every integrity condition an imported dependency must satisfy.

        Gate PASS, the required summary digest, an identical immutable contract,
        the same protocol identity, a compatible source snapshot, and the whole
        transitive dependency chain. A missing hash is a failure, never an
        absent expectation.
        """

        manifest = self.imported_manifest
        if manifest is None:
            raise StageBlocked(BLOCKED, f"{stage} was not supplied with --inputs")
        summary_path = self.inputs / stage / "summary.json"
        if not summary_path.is_file():
            raise StageBlocked(
                BLOCKED, f"imported {stage} has no summary.json in {self.inputs}"
            )
        expected = (manifest.get("stage_digests") or {}).get(stage)
        if expected is None:
            raise StageBlocked(
                FAIL,
                f"the imported manifest records no digest for {stage}; a missing hash "
                "is a failure, not an absent expectation",
            )
        actual = file_digest(summary_path)
        if expected != actual:
            raise StageBlocked(
                FAIL, f"imported {stage} summary does not match its manifest hash"
            )
        status = (manifest.get("stage_status") or {}).get(stage)
        if status != PASS:
            raise StageBlocked(
                BLOCKED,
                f"imported dependency {stage} is {status}, not {PASS}; a dependent "
                "stage is blocked whether its inputs are local or imported",
            )
        if manifest.get("protocol_id") != self.contract.protocol["protocol_id"]:
            raise StageBlocked(
                FAIL,
                f"imported run declares protocol {manifest.get('protocol_id')!r}, this "
                f"run uses {self.contract.protocol['protocol_id']!r}",
            )
        mine = {
            name: file_digest(self.contract.directory / name)
            for name in sorted(path.name for path in self.contract.directory.iterdir()
                               if path.is_file())
        }
        theirs = manifest.get("contract_files") or {}
        if not theirs:
            raise StageBlocked(FAIL, "the imported manifest records no contract files")
        differing = sorted(
            name for name in set(mine) | set(theirs) if mine.get(name) != theirs.get(name)
        )
        if differing:
            raise StageBlocked(
                FAIL, f"the imported run used different frozen inputs: {differing[:5]}"
            )
        recorded_snapshot = (manifest.get("source_snapshot") or {}).get("snapshot_sha256")
        if recorded_snapshot is None:
            raise StageBlocked(FAIL, "the imported manifest records no source snapshot")
        if recorded_snapshot != source_snapshot()["snapshot_sha256"]:
            raise StageBlocked(
                FAIL,
                "the imported run was produced by a different research source "
                f"snapshot ({recorded_snapshot}); repairs receive a new run",
            )
        # The whole transitive chain, not just the immediate dependency.
        for upstream in DEPENDENCIES[stage]:
            if upstream in self.gates:
                if self.gates[upstream]["status"] != PASS:
                    raise StageBlocked(
                        BLOCKED,
                        f"{stage}'s transitive dependency {upstream} is "
                        f"{self.gates[upstream]['status']} in this run",
                    )
                continue
            self.verify_imported(upstream)

    def prior(self, stage: str) -> dict:
        """A dependency's own output, from this run or a verified prior run.

        A local dependency must have recorded ``PASS`` in this run; an imported
        one must satisfy every condition in ``verify_imported``. Reading a
        summary is not enough: the gate is the thing that authorises the stage.
        """

        local = self.root / stage / "summary.json"
        if local.is_file():
            status = self.gates.get(stage, {}).get("status")
            if status is not None and status != PASS:
                raise StageBlocked(
                    BLOCKED, f"{stage} ran in this run and is {status}, not {PASS}"
                )
            self.prior_root[stage] = self.root
            return json.loads(local.read_text())
        if self.inputs is not None:
            self.verify_imported(stage)
            self.prior_root[stage] = self.inputs
            return json.loads((self.inputs / stage / "summary.json").read_text())
        raise StageBlocked(BLOCKED, f"{stage} has not run and was not supplied with --inputs")


def stage_preflight(run: Run) -> dict:
    locks = run.contract.verify_locks()
    state = git_state()
    snapshot = source_snapshot()
    payload = {
        "stage": "preflight",
        "locks": locks,
        "git": {key: value for key, value in state.items() if key != "diff"},
        "source_snapshot": snapshot,
        "python": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
        "contract_directory": str(run.contract.directory),
        "protocol_id": run.contract.protocol["protocol_id"],
        "plan_version": run.contract.protocol["plan_version"],
    }
    (run.root / "inputs" / "working_tree.diff").write_text(state["diff"])
    write_json(run.root / "inputs" / "preflight.json", payload)
    if locks["status"] != PASS:
        raise StageBlocked(FAIL, "; ".join(locks["findings"][:5]))
    if run.contract.protocol["plan_version"] != "2.1":
        raise StageBlocked(FAIL, "the protocol does not name plan version 2.1")
    return payload


def infeasible_attribution(programs: Sequence[Tuple[str, dict]]) -> dict:
    """Which fixed decisions make the accepted optimiser's queries INFEASIBLE.

    The accepted ``JointQuery`` is constructed unchanged and its ``Infeasible``
    message is retained. ``INFEASIBLE`` means a fixed decision contradicts the
    requested target; ``UNKNOWN_CONSTRUCTION`` means a construction budget ran
    out. They are different events and are never added together.
    """

    reasons: Dict[str, int] = {}
    per_program: List[dict] = []
    for name, program in programs:
        facts = dc.derive(program)
        compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
        times = se.issue_cycles_of(program, compiled["bundles"])
        addresses = dict(compiled["scratch"])
        cycles = max(times.values()) + 1
        memory = dc.footprint(facts, addresses)
        counts = {"attempted": 0, "infeasible": 0, "constructed": 0}
        local: Dict[str, int] = {}
        for target_cycles, target_memory in dopt.targets_for(facts, cycles, memory):
            for window in dopt.windows_for(
                facts, times, addresses, scratch_first=target_memory < memory
            ):
                counts["attempted"] += 1
                meter = si.Budget(seconds=1.0).start()
                try:
                    dk.JointQuery(
                        facts, times, addresses, window,
                        target_cycles, target_memory, meter, None,
                    ).expression()
                    counts["constructed"] += 1
                except dk.Infeasible as exc:
                    counts["infeasible"] += 1
                    key = re.sub(r"\d+", "N", str(exc))
                    local[key] = local.get(key, 0) + 1
                    reasons[key] = reasons.get(key, 0) + 1
                except si.BudgetExhausted:
                    counts["constructed"] += 0
        per_program.append({"program": name, "counts": counts, "reasons": local})
    return {"per_program": per_program, "reason_totals": reasons}


def historical_status_totals() -> dict:
    """Recompute the optimiser status totals from the retained raw rows.

    Plan section 2 withdraws version 1.0's causal attribution of attempts to
    construction difficulty. This recomputation is what replaces it: the totals
    are read from the accepted run's own rows, not from a summary.
    """

    source = ROOT / "results" / "direct_index_v4_optimization_repair2" / "final" / "runs.json"
    if not source.is_file():
        return {"available": False, "reason": f"{source} is not present"}
    payload = json.loads(source.read_text())
    runs = payload["runs"] if isinstance(payload, dict) and "runs" in payload else payload
    totals = {
        "SAT": 0, "UNSAT": 0, "UNKNOWN_CONSTRUCTION": 0,
        "UNKNOWN_SEARCH": 0, "INFEASIBLE": 0,
    }
    attempted = 0
    rows_with_statuses = 0
    for row in runs:
        record = row.get("optimiser") or {}
        statuses = record.get("statuses") or {}
        if not statuses:
            continue
        rows_with_statuses += 1
        attempted += record.get("attempted", 0) or 0
        for key, value in statuses.items():
            totals[key] = totals.get(key, 0) + value
    accounted = sum(totals.values())
    return {
        "available": True,
        "source": str(source.relative_to(ROOT)),
        "source_sha256": file_digest(source),
        "rows": len(runs),
        "rows_with_statuses": rows_with_statuses,
        "attempted_queries": attempted,
        "status_totals": totals,
        "accounted": accounted,
        "unaccounted": attempted - accounted,
        "infeasible_fraction": (totals["INFEASIBLE"] / attempted) if attempted else None,
        "note": (
            "INFEASIBLE is a fixed-context contradiction and UNKNOWN_CONSTRUCTION is "
            "an exhausted construction budget. They are reported separately and are "
            "never summed into one attribution."
        ),
    }


def stage_p0(run: Run) -> dict:
    contract = run.contract
    directory = run.stage_dir("p0")

    fixtures: List[dict] = []
    for record in contract.fixtures:
        domain = fixture_domain(record)
        incumbent = record["incumbent"]
        cycles = machine.check_compilation(record["program"], incumbent)
        cases = 0
        for case in record["program"]["cases"]:
            machine.check_case(record["program"], incumbent, case)
            cases += 1
        declared = record["cartesian_assignments"]
        actual = domain.cartesian_size()
        if declared != actual:
            raise StageBlocked(
                FAIL, f"fixture {record['id']}: declared {declared} assignments, computed {actual}"
            )
        if actual > contract.budgets["oracle_cartesian_max"]:
            raise StageBlocked(FAIL, f"fixture {record['id']} exceeds the oracle bound")
        fixtures.append(
            {
                "id": record["id"],
                "family": record["family"],
                "domain_sha256": domain.digest(),
                "program_sha256": se.object_digest(record["program"]),
                "semantic_sha256": se.program_semantic_digest(record["program"]),
                "cartesian_assignments": actual,
                "incumbent_cycles": cycles,
                "incumbent_scratch": machine.scratch_footprint(record["program"], incumbent),
                "incumbent_sha256": se.object_digest(
                    se.normalise_compilation(domain.facts, incumbent)
                ),
                "cases_validated": cases,
                "bits": {codec: se.layout(domain, codec).width for codec in se.CODECS},
            }
        )
    if len(fixtures) != contract.baseline_lock["fixture_count"]:
        raise StageBlocked(FAIL, "the fixture count does not match the baseline lock")
    if len({entry["id"] for entry in fixtures}) != len(fixtures):
        raise StageBlocked(FAIL, "fixture identifiers are not distinct")
    total = sum(entry["cartesian_assignments"] for entry in fixtures)
    if total != contract.baseline_lock["fixture_cartesian_total"]:
        raise StageBlocked(FAIL, "the total Cartesian size does not match the baseline lock")

    entries = heldout_programs(contract)
    collisions = heldout_collisions(entries)
    if collisions:
        raise StageBlocked(
            FAIL,
            f"{len(collisions)} held-out collisions and there is no replacement seed policy",
        )
    corpus_dir = run.root / "inputs" / "heldout"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries = []
    for entry in entries:
        path = corpus_dir / f"seed_{entry['seed']}.json"
        path.write_text(se.canonical_json(entry["program"]) + "\n")
        manifest_entries.append(
            {key: value for key, value in entry.items() if key != "program"}
            | {"path": str(path.relative_to(run.root)), "file_sha256": file_digest(path)}
        )

    public_dir = run.root / "inputs" / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    public_entries = []
    for name, program in public_programs():
        path = public_dir / name
        path.write_text(se.canonical_json(program) + "\n")
        public_entries.append(
            {
                "name": name,
                "program_name": program["name"],
                "operations": len(program["operations"]),
                "cases": len(program["cases"]),
                "program_sha256": se.object_digest(program),
                "semantic_sha256": se.program_semantic_digest(program),
                "path": str(path.relative_to(run.root)),
                "file_sha256": file_digest(path),
            }
        )

    summary = {
        "stage": "p0",
        "fixtures": fixtures,
        "fixture_count": len(fixtures),
        "fixture_cartesian_total": total,
        "heldout": {
            "seed_first": contract.protocol["heldout"]["seed_first"],
            "seed_last": contract.protocol["heldout"]["seed_last"],
            "count": len(manifest_entries),
            "collisions": collisions,
            "programs": manifest_entries,
        },
        "public": public_entries,
        "historical_optimiser_statuses": historical_status_totals(),
        "infeasible_attribution": infeasible_attribution(public_programs()),
        "source_snapshot": source_snapshot(),
        "git": {key: value for key, value in git_state().items() if key != "diff"},
    }
    write_json(directory / "summary.json", summary)
    return summary


def stage_p1(run: Run) -> dict:
    """Codec correctness and coverage."""

    contract = run.contract
    directory = run.stage_dir("p1")
    p0 = run.prior("p0")
    budgets = contract.budgets
    sampling = contract.protocol["sampling"]

    oracle_rows: List[dict] = []
    decoder_rows: List[dict] = []
    defects: List[dict] = []
    fixture_summaries: List[dict] = []

    for record in contract.fixtures:
        domain = fixture_domain(record)
        enumeration = so.enumerate_feasible(record, budgets["oracle_cartesian_max"])
        oracle_identities = {entry["identity"] for entry in enumeration["feasible"]}
        oracle_rows.append(
            {key: value for key, value in enumeration.items() if key != "feasible"}
            | {"domain_sha256": domain.digest()}
        )

        per_codec: Dict[str, dict] = {}
        for codec in se.CODECS:
            bits = se.layout(domain, codec).width
            entry: Dict[str, object] = {"bits": bits}
            exhausted = bits <= budgets["exhaust_bit_width_max"]
            counts = {status: 0 for status in se.STATUSES}
            found: Dict[str, int] = {}
            if exhausted:
                for index in range(1 << bits):
                    try:
                        result = se.decode(domain, index, codec)
                    except se.CodecDefect as defect:
                        defects.append(defect.evidence)
                        continue
                    counts[result.status] += 1
                    if result.status == se.COMPLETE:
                        identity = se.canonical_json(result.compilation)
                        if identity in found:
                            defects.append(
                                {
                                    "kind": "duplicate_object",
                                    "domain_id": domain.identifier,
                                    "codec": codec,
                                    "indices": [str(found[identity]), str(index)],
                                }
                            )
                        found[identity] = index
                        if len(decoder_rows) < 2000:
                            decoder_rows.append(result.to_row())
                entry["exhausted"] = True
                entry["counts"] = counts
                entry["valid_codes"] = counts[se.COMPLETE]
                entry["set_equality"] = set(found) == oracle_identities
                entry["missing_from_codec"] = sorted(oracle_identities - set(found))[:5]
                entry["extra_in_codec"] = sorted(set(found) - oracle_identities)[:5]
            else:
                entry["exhausted"] = False
                entry["counts"] = None
                entry["valid_codes"] = None
                entry["set_equality"] = None

            # Round trip every feasible oracle object, whether or not the code
            # universe was exhausted. This is the inverse-map obligation.
            round_trips = 0
            failures: List[dict] = []
            for member in enumeration["feasible"]:
                compilation = json.loads(member["identity"])
                try:
                    index = se.encode(domain, compilation, codec)
                    back = se.decode(domain, index, codec)
                except (se.DomainError, se.CodecDefect) as exc:
                    failures.append({"identity": member["identity"], "error": str(exc)})
                    continue
                if back.status != se.COMPLETE or \
                        se.canonical_json(back.compilation) != member["identity"]:
                    failures.append(
                        {"identity": member["identity"], "status": back.status,
                         "reason": back.reason}
                    )
                    continue
                if se.encode(domain, back.compilation, codec) != index:
                    failures.append({"identity": member["identity"], "error": "not injective"})
                    continue
                round_trips += 1
            entry["round_trips"] = round_trips
            entry["round_trip_failures"] = failures[:10]
            entry["round_trip_failure_count"] = len(failures)
            per_codec[codec] = entry

        origin = None
        if domain.incumbent is not None:
            expected = se.canonical_json(
                se.normalise_compilation(domain.facts, domain.incumbent)
            )
            origin = {}
            for codec in ("static_rank", "structural_rank"):
                result = se.decode(domain, 0, codec)
                origin[codec] = (
                    result.status == se.COMPLETE
                    and se.canonical_json(result.compilation) == expected
                )
        fixture_summaries.append(
            {
                "id": record["id"],
                "family": record["family"],
                "domain_sha256": domain.digest(),
                "oracle_feasible": enumeration["feasible_count"],
                "codecs": per_codec,
                "origin_is_incumbent": origin,
            }
        )

    # -- public sampling streams ----------------------------------------
    streams: List[dict] = []
    public_coverage: List[dict] = []
    stream_discrepancies: List[dict] = []
    union_rows: List[dict] = []
    with AttemptSink(directory / "sampling_attempts.jsonl") as sink:
        for entry in p0["public"]:
            program = machine.load_program(run.prior_root["p0"] / entry["path"])
            facts = dc.derive(program)
            compiled, _ = dcomp.compile_with_report(
                program, dcomp.DEFAULT_LIMITS, optimise=False
            )
            record = whole_program_record(
                entry["name"], "public", program, facts, compiled
            )
            domain = se.Domain.from_record(record)
            fixed = {
                "stage": "p1",
                "corpus": "public",
                "program": entry["name"],
                "program_sha256": entry["program_sha256"],
            }
            raw, raw_identities = raw_bit_stream(
                domain, "structural_rank", contract.seeds["raw_bits"],
                sampling["attempts_per_program_per_stream"],
                sampling["seconds_per_program_per_stream"],
                sink=sink, identity=fixed,
            )
            paths, path_identities = option_path_stream(
                domain, "structural_rank", contract.seeds["option_paths"],
                sampling["attempts_per_program_per_stream"],
                sampling["seconds_per_program_per_stream"],
                sink=sink, identity=fixed,
            )
            for stream in (raw, paths):
                stream["program_sha256"] = entry["program_sha256"]
                stream["program_name"] = entry["name"]
                streams.append(stream)
                stream_discrepancies.extend(
                    item | {"program": entry["name"],
                             "program_sha256": entry["program_sha256"]}
                    for item in stream["discrepancies"]
                )
            # The gate is "distinct completed compilations across the two streams",
            # so the denominator is the union of the two identity sets, not their
            # sum: an object found by both streams is one object.
            union = raw_identities | path_identities
            total_distinct = len(union)
            union_rows.append(
                {
                    "program": entry["name"],
                    "program_sha256": entry["program_sha256"],
                    "domain_sha256": domain.digest(),
                    "identities": sorted(union),
                    "raw_only": sorted(raw_identities - path_identities),
                    "path_only": sorted(path_identities - raw_identities),
                    "in_both": sorted(raw_identities & path_identities),
                }
            )
            public_coverage.append(
                {
                    "program": entry["name"],
                    "program_sha256": entry["program_sha256"],
                    "domain_sha256": domain.digest(),
                    "bits": se.layout(domain, "structural_rank").width,
                    "distinct_complete_union": total_distinct,
                    "distinct_complete_sum": (
                        raw["distinct_complete"] + paths["distinct_complete"]
                    ),
                    "raw_complete": raw["complete"],
                    "path_complete": paths["complete"],
                    "case_checks": raw["case_checks"] + paths["case_checks"],
                    "case_failures": raw["case_failures"] + paths["case_failures"],
                    "meets_minimum": total_distinct
                    >= sampling["minimum_distinct_completed_per_program"],
                    "streams_incomplete": [
                        stream["stream"] for stream in (raw, paths) if stream["incomplete"]
                    ],
                }
            )
        attempts_written = sink.written

    write_jsonl(directory / "oracle_domains.jsonl", oracle_rows)
    write_jsonl(directory / "decoder_rows.jsonl", decoder_rows)
    write_jsonl(directory / "sampling_streams.jsonl", streams)
    write_jsonl(directory / "sampling_identities.jsonl", union_rows)

    equalities = [
        entry["codecs"][codec]["set_equality"]
        for entry in fixture_summaries
        for codec in se.CODECS
        if entry["codecs"][codec]["set_equality"] is not None
    ]
    round_trip_failures = sum(
        entry["codecs"][codec]["round_trip_failure_count"]
        for entry in fixture_summaries
        for codec in se.CODECS
    )
    coverage_met = all(entry["meets_minimum"] for entry in public_coverage)
    total_case_checks = sum(stream["case_checks"] for stream in streams)
    total_completions = sum(stream["complete"] for stream in streams)

    summary = {
        "stage": "p1",
        "fixtures": fixture_summaries,
        "public_coverage": public_coverage,
        "defects": defects,
        "defect_count": len(defects),
        "exhausted_comparisons": len(equalities),
        "set_equality_all": bool(equalities) and all(equalities),
        "round_trip_failures": round_trip_failures,
        "coverage_minimum": sampling["minimum_distinct_completed_per_program"],
        "coverage_met": coverage_met,
        "stream_count": len(streams),
        "sampling_raw_rows": attempts_written,
        "sampling_attempts_drawn": sum(stream["attempts_drawn"] for stream in streams),
        "sampling_completions": total_completions,
        "sampling_case_checks": total_case_checks,
        "sampling_case_failures": sum(stream["case_failures"] for stream in streams),
        "sampling_discrepancies": stream_discrepancies,
        "sampling_discrepancy_count": len(stream_discrepancies),
        "raw_artifacts": {
            name: file_digest(directory / name)
            for name in (
                "oracle_domains.jsonl", "decoder_rows.jsonl",
                "sampling_streams.jsonl", "sampling_attempts.jsonl",
                "sampling_identities.jsonl",
            )
        },
    }
    write_json(directory / "summary.json", summary)

    if stream_discrepancies:
        raise StageBlocked(
            FAIL,
            f"{len(stream_discrepancies)} sampled completions were rejected by the "
            "pinned case validator: see p1/summary.json sampling_discrepancies",
        )
    if defects or round_trip_failures or not summary["set_equality_all"]:
        raise StageBlocked(FAIL, "codec correctness failed: see p1/summary.json")
    if not coverage_met:
        raise StageBlocked(
            INCONCLUSIVE,
            "public sampling did not reach the declared distinct-completion minimum",
        )
    return summary


def _benchmark_corpus(
    run: Run,
    stage: str,
    corpus: str,
    programs: Sequence[dict],
    rng: random.Random,
    extra_arms: Sequence[str] = (),
) -> Tuple[List[dict], dict]:
    """Measure the frozen arm matrix over one corpus, one process per row.

    ``extra_arms`` carries the conditional ``structural_model`` arm when H4 has
    authorised it. It enters the schedule, the expected membership and the rows,
    so an authorised arm is *measured* rather than asserted: before the
    2026-09-23 repair P5 could record that arm PASS while this function scheduled
    only the fixed non-model arms.
    """

    contract = run.contract
    budgets = contract.budgets["optimisation_seconds"]
    repetitions = contract.statistics["timing_repetitions"]
    unbudgeted = ("accepted_bootstrap", "accepted_default")
    budgeted = ("accepted_budgeted",) + STRUCTURAL_ARMS + tuple(extra_arms)

    schedule = arm_schedule(programs, budgets, unbudgeted, budgeted, rng, repetitions)
    rows: List[dict] = []
    for program, budget, seed, repetition, arm in schedule:
        spec = {
            "kind": "phase2_measurement",
            "stage": stage,
            "corpus": corpus,
            "arm": arm,
            "program_path": str(run.prior_root["p0"] / program["path"]),
            "program_sha256": program["program_sha256"],
            "codec": None if arm in ACCEPTED_ARMS else "structural_rank",
            "budget_seconds": budget,
            "search_seed": seed,
            "repetition": repetition,
            "limits": contract.budgets,
            "elite_fraction": contract.statistics["elite_fraction"],
        }
        rows.append(run.harness.run(spec))

    membership = expected_keys(programs, budgets, unbudgeted, budgeted, repetitions)
    model_rows = [row for row in rows if row.get("arm") == MODEL_ARM]
    observed = [
        [row["program_sha256"], row["budget_seconds"], row["arm"],
         row["search_seed"], row["repetition"]]
        for row in rows
    ]
    expected_set = {se.canonical_json(key) for key in membership}
    observed_set = {se.canonical_json(key) for key in observed}
    accounting = {
        "expected_rows": len(membership),
        "actual_rows": len(rows),
        "missing_keys": sorted(expected_set - observed_set)[:20],
        "unexpected_keys": sorted(observed_set - expected_set)[:20],
        "failed_rows": sum(1 for row in rows if row.get("failed_row")),
        "timed_out_rows": sum(1 for row in rows if row.get("timed_out")),
        "discrepancy_rows": sum(1 for row in rows if row.get("discrepancy_count", 0)),
        "membership_exact": expected_set == observed_set and len(rows) == len(membership),
        "arms": sorted({row.get("arm") for row in rows}),
        "model_arm_rows": len(model_rows),
        "model_arm_requested": MODEL_ARM in tuple(extra_arms),
    }
    return rows, accounting


def _quality_table(rows: Sequence[dict], budget: float) -> Dict[str, Dict[str, float]]:
    """Mean product per (arm, program) at one budget, failures excluded loudly."""

    table: Dict[str, Dict[str, List[float]]] = {}
    for row in rows:
        if row.get("failed_row"):
            continue
        if row["arm"] in ACCEPTED_ARMS and row["arm"] != "accepted_budgeted":
            key_budget = None
        else:
            key_budget = row["budget_seconds"]
        if key_budget is not None and key_budget != budget:
            continue
        table.setdefault(row["arm"], {}).setdefault(row["program_sha256"], []).append(
            float(row["product"])
        )
    return {
        arm: {program: statistics.mean(values) for program, values in programs.items()}
        for arm, programs in table.items()
    }


def _median_time_table(rows: Sequence[dict], budget: float, key: str) -> Dict[str, Dict[str, float]]:
    table: Dict[str, Dict[str, List[float]]] = {}
    for row in rows:
        if row.get("failed_row"):
            continue
        if row["arm"] in ("accepted_bootstrap", "accepted_default"):
            key_budget = None
        else:
            key_budget = row["budget_seconds"]
        if key_budget is not None and key_budget != budget:
            continue
        table.setdefault(row["arm"], {}).setdefault(row["program_sha256"], []).append(
            float(row[key])
        )
    return {
        arm: {program: statistics.median(values) for program, values in programs.items()}
        for arm, programs in table.items()
    }


def family_stratified_bootstrap(
    per_program: Dict[str, float],
    families: Dict[str, str],
    resamples: int,
    seed: int,
    percentiles: Sequence[float],
) -> dict:
    """Resample programs within family, weighting families equally.

    The sampling unit is the program. Seeds, technical repetitions and domain
    variants have already been averaged inside the program before this is
    called; they are never treated as independent programs.
    """

    grouped: Dict[str, List[float]] = {}
    for program, value in sorted(per_program.items()):
        grouped.setdefault(families.get(program, "unspecified"), []).append(value)
    grouped = {family: values for family, values in grouped.items() if values}
    if not grouped:
        return {"status": INCONCLUSIVE, "reason": "no eligible programs", "resamples": 0}

    rng = random.Random(seed)
    draws: List[float] = []
    for _ in range(resamples):
        family_means = []
        for family in sorted(grouped):
            values = grouped[family]
            picks = [values[rng.randrange(len(values))] for _ in range(len(values))]
            family_means.append(statistics.mean(picks))
        draws.append(statistics.mean(family_means))
    draws.sort()
    observed = statistics.mean(
        [statistics.mean(grouped[family]) for family in sorted(grouped)]
    )
    return {
        "status": PASS,
        "point_estimate": observed,
        "intervals": {
            f"{low}-{high}": [percentile(draws, low), percentile(draws, high)]
            for low, high in [tuple(percentiles[i:i + 2]) for i in range(0, len(percentiles), 2)]
        },
        "resamples": len(draws),
        "seed": seed,
        "families": {family: len(values) for family, values in sorted(grouped.items())},
        "programs": sum(len(values) for values in grouped.values()),
        "single_program_families": sorted(
            family for family, values in grouped.items() if len(values) == 1
        ),
    }


def paired_log_ratio_analysis(
    rows: Sequence[dict],
    families: Dict[str, str],
    baseline: str,
    candidate: str,
    budget: float,
    contract: Contract,
) -> dict:
    """The primary endpoint: paired ``log(J_control / J_candidate)``."""

    table = _quality_table(rows, budget)
    if baseline not in table or candidate not in table:
        return {
            "status": INCONCLUSIVE,
            "reason": f"one of {baseline!r}/{candidate!r} produced no usable row",
            "baseline_arm": baseline,
            "candidate_arm": candidate,
            "budget_seconds": budget,
        }
    programs = sorted(set(table[baseline]) & set(table[candidate]))
    per_program = {}
    wins = ties = losses = 0
    for program in programs:
        base, cand = table[baseline][program], table[candidate][program]
        if base <= 0 or cand <= 0:
            continue
        per_program[program] = math.log(base / cand)
        if cand < base:
            wins += 1
        elif cand == base:
            ties += 1
        else:
            losses += 1

    stats = contract.statistics
    interval = family_stratified_bootstrap(
        per_program, families, stats["bootstrap_resamples"],
        contract.seeds["bootstrap"],
        list(stats["interval_percentiles"]) + list(stats["h4_gate_interval_percentiles"]),
    )
    return {
        "status": PASS if per_program else INCONCLUSIVE,
        "baseline_arm": baseline,
        "candidate_arm": candidate,
        "budget_seconds": budget,
        "programs": len(per_program),
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "per_program_log_ratio": per_program,
        "interval": interval,
        "endpoint": "paired log(J_control / J_candidate); positive favours the candidate",
    }


def stage_p2(run: Run) -> dict:
    """Representation and search attribution."""

    contract = run.contract
    directory = run.stage_dir("p2")
    p0 = run.prior("p0")
    run.prior("p1")

    # -- tiny fixtures: exhaustive matched-domain oracle comparison ------
    tiny: List[dict] = []
    for record in contract.fixtures:
        domain = fixture_domain(record)
        enumeration = so.enumerate_feasible(record, contract.budgets["oracle_cartesian_max"])
        oracle_min = min(
            (entry["product"] for entry in enumeration["feasible"]), default=None
        )
        arms: Dict[str, dict] = {}
        for arm in ("structural_dfs", "structural_bound"):
            report = ss.search(
                domain, None, arm,
                si.Budget(
                    seconds=contract.budgets["external_process_seconds"],
                    max_cover=contract.budgets["query_max_cover"],
                    max_visited=contract.budgets["search_max_nodes"],
                    max_records=contract.budgets["search_max_candidate_validations"],
                ),
            )
            arms[arm] = report.to_row()
        bounds = bound_admissibility(domain)
        tiny.append(
            {
                "id": record["id"],
                "family": record["family"],
                "domain_sha256": domain.digest(),
                "oracle_feasible": enumeration["feasible_count"],
                "oracle_minimum_product": oracle_min,
                "bits": {codec: se.layout(domain, codec).width for codec in se.CODECS},
                "arms": arms,
                "reaches_oracle_minimum": {
                    arm: arms[arm]["best_product"] == oracle_min for arm in arms
                },
                "bound_admissibility": bounds,
            }
        )

    # -- public programs: the frozen arm matrix --------------------------
    rng = random.Random(contract.seeds["arm_order"])
    rows, accounting = _benchmark_corpus(run, "p2", "public", p0["public"], rng)
    write_jsonl(directory / "benchmark_rows.jsonl", rows)

    families = {entry["program_sha256"]: "public" for entry in p0["public"]}
    primary = contract.budgets["primary_seconds"]
    comparisons = {
        f"{candidate}_vs_{baseline}@{budget}": paired_log_ratio_analysis(
            rows, families, baseline, candidate, budget, contract
        )
        for budget in contract.budgets["optimisation_seconds"]
        for baseline, candidate in (
            ("accepted_budgeted", "structural_bound"),
            ("accepted_budgeted", "structural_dfs"),
            ("accepted_budgeted", "structural_expanded"),
        )
    }

    bound_failures = [entry["id"] for entry in tiny
                      if entry["bound_admissibility"]["status"] == FAIL]
    oracle_misses = [
        entry["id"] for entry in tiny
        if entry["oracle_minimum_product"] is not None
        and not all(entry["reaches_oracle_minimum"].values())
    ]

    summary = {
        "stage": "p2",
        "tiny_fixtures": tiny,
        "bound_admissibility_failures": bound_failures,
        "oracle_minimum_misses": oracle_misses,
        "accounting": accounting,
        "primary_budget_seconds": primary,
        "comparisons": comparisons,
        "median_compile_seconds": {
            str(budget): _median_time_table(rows, budget, "compile_seconds")
            for budget in contract.budgets["optimisation_seconds"]
        },
        "median_process_seconds": {
            str(budget): _median_time_table(rows, budget, "process_seconds")
            for budget in contract.budgets["optimisation_seconds"]
        },
    }
    write_json(directory / "summary.json", summary)

    if bound_failures:
        raise StageBlocked(FAIL, f"bounds are not admissible on {bound_failures}")
    if oracle_misses:
        raise StageBlocked(FAIL, f"search missed the oracle minimum on {oracle_misses}")
    if accounting["failed_rows"] or not accounting["membership_exact"]:
        raise StageBlocked(FAIL, "the P2 benchmark membership or failure accounting is wrong")
    return summary


def _elite_threshold(products: Sequence[int], fraction: float) -> Optional[int]:
    """The smallest integer objective at which at least ``fraction`` qualify.

    All ties at that objective are included, which is why the count is reported
    beside the threshold and never assumed to equal ``fraction * N``.
    """

    if not products:
        return None
    ordered = sorted(products)
    needed = math.ceil(fraction * len(ordered))
    for value in ordered:
        if sum(1 for item in ordered if item <= value) >= needed:
            return value
    return ordered[-1]


def control_serialisation(
    domain: se.Domain,
    identities: Sequence[str],
    subset_size: int,
    codec: str,
    seed: int,
    controls: int,
    budgets: dict,
) -> dict:
    """The P3 control covers: their serialised lengths and their median.

    One owner, called by ``stage_p3`` to produce the numbers and by the evidence
    checker to recompute them from the locked fixture. The RNG is reinitialised
    here for this fixture alone, sampling is without replacement inside each
    control, and all ``controls`` subsets are retained even when two coincide.
    """

    rng = random.Random(seed)
    lengths: List[int] = []
    status = "COMPLETE"
    duplicates: List[Tuple[str, ...]] = []
    for _ in range(controls):
        subset = rng.sample(list(identities), subset_size)
        duplicates.append(tuple(sorted(subset)))
        bits = se.layout(domain, codec).width
        indices = [se.encode(domain, json.loads(identity), codec) for identity in subset]
        cover = sm.exact_cover(
            indices, bits, budgets["cover_max_cubes"], budgets["cover_seconds_per_set"]
        )
        if cover.status != "COMPLETE":
            status = cover.status
            continue
        lengths.append(len(sm.serialise_cover(cover.cubes, bits)))
    return {
        "count": len(lengths),
        "requested": controls,
        "status": status,
        "bytes": lengths,
        "median_bytes": statistics.median(lengths) if lengths else None,
        "duplicate_subsets": controls - len(set(duplicates)),
    }


def p4_contrasts(rows: Sequence[dict], contract: Contract) -> dict:
    """The P4 discovery contrasts, the H4 gate bounds and the advancement flag.

    One owner, called by ``stage_p4`` on the rows it has just measured and by the
    evidence checker on the rows retained on disk. Technical repetitions are
    averaged within seed, then seeds, then the two domain variants inside one
    semantic program digest, and every intermediate denominator is returned.
    """

    stats = contract.statistics
    usable = [
        row for row in rows
        if not row.get("failed_row") and row.get("status") == PASS
    ]

    def endpoint_by_program(arm: str, budget: float) -> Dict[str, float]:
        by_seed: Dict[Tuple[str, str, object], List[float]] = {}
        for row in usable:
            if row["arm"] != arm or row["budget_seconds"] != budget:
                continue
            key = (row["semantic_sha256"], row["fixture_id"], row["search_seed"])
            by_seed.setdefault(key, []).append(float(row["best_test_product"]))
        by_variant: Dict[Tuple[str, str], List[float]] = {}
        for (semantic, fixture, _seed), values in by_seed.items():
            by_variant.setdefault((semantic, fixture), []).append(statistics.mean(values))
        by_program: Dict[str, List[float]] = {}
        for (semantic, _fixture), values in by_variant.items():
            by_program.setdefault(semantic, []).append(statistics.mean(values))
        return {semantic: statistics.mean(values) for semantic, values in by_program.items()}

    families = {
        se.program_semantic_digest(record["program"]): record["family"]
        for record in contract.fixtures
    }

    contrasts: Dict[str, dict] = {}
    for budget in contract.budgets["optimisation_seconds"]:
        candidate = endpoint_by_program("model_expand", budget)
        for control in ("one_bit", "uniform_bits", "empirical_cover"):
            baseline = endpoint_by_program(control, budget)
            shared = sorted(set(candidate) & set(baseline))
            per_program = {
                program: math.log(baseline[program] / candidate[program])
                for program in shared
                if baseline[program] > 0 and candidate[program] > 0
            }
            interval = family_stratified_bootstrap(
                per_program, families, stats["bootstrap_resamples"],
                contract.seeds["bootstrap"],
                list(stats["interval_percentiles"])
                + list(stats["h4_gate_interval_percentiles"]),
            )
            contrasts[f"model_expand_vs_{control}@{budget}"] = {
                "control": control,
                "budget_seconds": budget,
                "programs": len(per_program),
                "per_program_log_ratio": per_program,
                "interval": interval,
            }

    primary = contract.budgets["primary_seconds"]
    gate_key = "%s-%s" % tuple(stats["h4_gate_interval_percentiles"])
    gate_low: Dict[str, Optional[float]] = {}
    for control in ("one_bit", "uniform_bits"):
        entry = contrasts.get(f"model_expand_vs_{control}@{primary}", {})
        intervals = entry.get("interval", {}).get("intervals", {})
        gate_low[control] = intervals.get(gate_key, [None, None])[0]

    families_with_tests = sorted(
        {row["family"] for row in usable if row["counts"]["test_proposals"] >= 0}
    )
    enough_families = (
        len(families_with_tests) >= stats["triage_informative_families_min"]
    )
    advance = enough_families and all(
        value is not None and value > 0 for value in gate_low.values()
    )
    empirical = [row for row in usable if row["arm"] == "empirical_cover"]
    return {
        "usable_rows": len(usable),
        "informative_fixtures": sorted({row["fixture_id"] for row in usable}),
        "families_with_informative_tests": families_with_tests,
        "contrasts": contrasts,
        "primary_budget_seconds": primary,
        "h4_gate_lower_bounds": gate_low,
        "h4_gate_percentiles": stats["h4_gate_interval_percentiles"],
        "empirical_cover_test_discoveries": sum(
            row["counts"]["test_discoveries"] for row in empirical
        ),
        "empirical_cover_exhausted": (
            all(row["counts"]["exhausted"] for row in empirical) if empirical else None
        ),
        "advance_to_model_arm": advance,
    }


def stage_p3(run: Run) -> dict:
    """Complete-domain structure experiment, and the H4 triage."""

    contract = run.contract
    directory = run.stage_dir("p3")
    run.prior("p1")
    stats = contract.statistics
    budgets = contract.budgets

    fixtures: List[dict] = []
    for record in contract.fixtures:
        domain = fixture_domain(record)
        enumeration = so.enumerate_feasible(record, budgets["oracle_cartesian_max"])
        feasible = enumeration["feasible"]
        products = [entry["product"] for entry in feasible]
        informative = bool(feasible) and len(set(products)) > 1
        entry: Dict[str, object] = {
            "id": record["id"],
            "family": record["family"],
            "domain_sha256": domain.digest(),
            "feasible": len(feasible),
            "distinct_objectives": len(set(products)),
            "informative": informative,
            "uninformative_reason": (
                None if informative
                else ("empty feasible set" if not feasible else "all objectives are equal")
            ),
        }
        if not informative:
            fixtures.append(entry)
            continue

        threshold = _elite_threshold(products, stats["elite_fraction"])
        elite_members = [item for item in feasible if item["product"] <= threshold]
        entry["threshold"] = threshold
        entry["elite_count"] = len(elite_members)
        entry["elite_fraction_actual"] = len(elite_members) / len(feasible)

        # The same physical subset is mapped into every codec, so the
        # representations are compared on identical objects.
        identities = sorted(item["identity"] for item in feasible)
        entry["control_count"] = stats["structure_controls"]

        codecs: Dict[str, dict] = {}
        for codec in ("absolute", "static_rank", "structural_rank"):
            bits = se.layout(domain, codec).width
            try:
                elite_indices = [
                    se.encode(domain, json.loads(item["identity"]), codec)
                    for item in elite_members
                ]
            except se.DomainError as exc:
                codecs[codec] = {"bits": bits, "status": FAIL, "reason": str(exc)}
                continue
            cover = sm.exact_cover(
                elite_indices, bits, budgets["cover_max_cubes"],
                budgets["cover_seconds_per_set"],
            )
            elite_bytes = (
                len(sm.serialise_cover(cover.cubes, bits))
                if cover.status == "COMPLETE" else None
            )
            minterm_bytes = len(
                sm.serialise_cover(
                    tuple(si.Cube(bits, index, 0) for index in sorted(set(elite_indices))),
                    bits,
                )
            )
            control = control_serialisation(
                domain, identities, len(elite_members), codec,
                contract.seeds["structure_controls"], stats["structure_controls"],
                budgets,
            )
            median_control = control["median_bytes"]
            entry["control_duplicate_subsets"] = control["duplicate_subsets"]
            codecs[codec] = {
                "bits": bits,
                "status": cover.status,
                "cover": cover.to_row(),
                "elite_bytes": elite_bytes,
                "elite_bits": None if elite_bytes is None else elite_bytes * 8,
                "minterm_bytes": minterm_bytes,
                "control_bytes_count": control["count"],
                "control_status": control["status"],
                "control_median_bytes": median_control,
                "shorter_fraction": (
                    None if (elite_bytes is None or median_control is None)
                    else 1 - elite_bytes / median_control
                ),
                "meets_triage": (
                    None if (elite_bytes is None or median_control is None)
                    else elite_bytes <= stats["triage_ratio_max"] * median_control
                ),
            }
        entry["codecs"] = codecs
        fixtures.append(entry)

    informative = [entry for entry in fixtures if entry.get("informative")]
    qualifying = [
        entry for entry in informative
        if entry.get("codecs", {}).get("structural_rank", {}).get("meets_triage")
    ]
    families = {entry["family"] for entry in informative}
    qualifying_families = {entry["family"] for entry in qualifying}

    enough_families = len(families) >= stats["triage_informative_families_min"]
    enough_fixtures = (
        bool(informative)
        and len(qualifying) >= math.ceil(stats["triage_fraction_min"] * len(informative))
    )
    spans_families = len(qualifying_families) >= stats["triage_informative_families_min"]
    triage_pass = enough_families and enough_fixtures and spans_families

    summary = {
        "stage": "p3",
        "fixtures": fixtures,
        "informative_count": len(informative),
        "informative_families": sorted(families),
        "qualifying_count": len(qualifying),
        "qualifying_families": sorted(qualifying_families),
        "triage": {
            "ratio_max": stats["triage_ratio_max"],
            "fraction_min": stats["triage_fraction_min"],
            "families_min": stats["triage_informative_families_min"],
            "enough_informative_families": enough_families,
            "enough_qualifying_fixtures": enough_fixtures,
            "qualifying_spans_families": spans_families,
            "status": PASS if triage_pass else FAIL,
        },
    }
    write_json(directory / "summary.json", summary)

    if not enough_families:
        raise StageBlocked(
            INCONCLUSIVE,
            f"only {len(families)} informative families, "
            f"{stats['triage_informative_families_min']} are required",
        )
    if not triage_pass:
        raise StageBlocked(
            FAIL,
            "the preregistered triage threshold was not met; the model experiment is "
            "suspended and the encoding and search results stand",
        )
    return summary


def split_fixture(
    enumeration: dict, seed: int, minimum_train: int, minimum_test: int
) -> dict:
    """Disjoint train/validation/test partitions of one complete small domain.

    The permutation is seeded and reinitialised for this fixture alone, and the
    input order is the lexicographic sort of the canonical identities, so the
    split does not depend on enumeration order. A split too small to support
    evaluation is reported as such and never silently reallocated.
    """

    identities = sorted(entry["identity"] for entry in enumeration["feasible"])
    rng = random.Random(seed)
    shuffled = list(identities)
    rng.shuffle(shuffled)
    total = len(shuffled)
    n_train = total // 2
    n_validation = total // 4
    train = shuffled[:n_train]
    validation = shuffled[n_train:n_train + n_validation]
    test = shuffled[n_train + n_validation:]
    return {
        "total": total,
        "n_train": len(train),
        "n_validation": len(validation),
        "n_test": len(test),
        "train": train,
        "validation": validation,
        "test": test,
        "informative": len(train) >= minimum_train and len(test) >= minimum_test,
        "reason": (
            None if (len(train) >= minimum_train and len(test) >= minimum_test)
            else f"train {len(train)} < {minimum_train} or test {len(test)} < {minimum_test}"
        ),
    }


def run_model_measurement(spec: dict, contract: Contract) -> dict:
    """One proposal arm, on one fixture, under one budget and seed.

    The learner receives the training labels and the results of queries it pays
    for. It is never handed the hidden evaluation mapping: that object is built
    here, consulted only to *score* a proposal the arm has already made, and
    never passed into ``structural_models.proposals``.
    """

    record = next(item for item in contract.fixtures if item["id"] == spec["fixture_id"])
    domain = se.Domain.from_record(record)
    codec = "structural_rank"
    bits = se.layout(domain, codec).width
    enumeration = so.enumerate_feasible(record, contract.budgets["oracle_cartesian_max"])
    hidden = so.hidden_evaluation(enumeration)
    by_identity = {entry["identity"]: entry for entry in enumeration["feasible"]}

    split = split_fixture(
        enumeration, contract.seeds["split"],
        contract.statistics["p4_min_train"], contract.statistics["p4_min_test"],
    )
    if not split["informative"]:
        return {
            "kind": "phase2_model_result",
            "fixture_id": spec["fixture_id"],
            "arm": spec["arm"],
            "status": NOT_APPLICABLE,
            "reason": split["reason"],
        }

    train_products = [hidden[identity] for identity in split["train"]]
    ordered = sorted(train_products)
    position = math.ceil(len(ordered) / 10)
    threshold = ordered[max(position, 1) - 1]
    elite_identities = [item for item in split["train"] if hidden[item] <= threshold]

    index_of = {
        identity: se.encode(domain, json.loads(identity), codec)
        for identity in split["train"] + split["validation"] + split["test"]
    }
    identity_of = {index: identity for identity, index in index_of.items()}
    train_indices = {index_of[identity] for identity in split["train"]}
    validation_indices = {index_of[identity] for identity in split["validation"]}
    test_indices = {index_of[identity] for identity in split["test"]}
    elite_indices = sorted(index_of[identity] for identity in elite_identities)

    started = time.perf_counter()
    cover = sm.exact_cover(
        elite_indices, bits, contract.budgets["cover_max_cubes"],
        contract.budgets["cover_seconds_per_set"],
    )
    model_seconds = time.perf_counter() - started
    if cover.status != "COMPLETE":
        return {
            "kind": "phase2_model_result",
            "fixture_id": spec["fixture_id"],
            "arm": spec["arm"],
            "status": INCONCLUSIVE,
            "reason": f"the training elite cover is {cover.status}: {cover.reason}",
        }

    budget = spec["budget_seconds"]
    # Model construction is paid out of the same budget as the queries.
    deadline = started + budget
    excluded = set(train_indices)
    evaluated: Dict[int, str] = {}
    counts = {
        "attempted": 0, "duplicate": 0, "invalid_code": 0, "dead_end": 0,
        "interrupted": 0, "complete": 0, "novel": 0,
        "validation_proposals": 0, "test_proposals": 0, "test_discoveries": 0,
        "exhausted": False,
    }
    best_test_product = min(train_products)
    discoveries: List[dict] = []

    stream = sm.proposals(
        spec["arm"], bits, elite_indices, cover.cubes, excluded, spec.get("search_seed")
    )
    while time.perf_counter() < deadline:
        try:
            index, duplicate = next(stream)
        except StopIteration:
            counts["exhausted"] = True
            break
        counts["attempted"] += 1
        if duplicate or index in evaluated:
            # A repeat is paid for and stays in the denominator; it can never
            # be relabelled as an unseen discovery.
            counts["duplicate"] += 1
            continue
        counts["novel"] += 1
        result = se.decode(domain, index, codec)
        evaluated[index] = result.status
        if result.status == se.INVALID_CODE:
            counts["invalid_code"] += 1
            continue
        if result.status == se.DEAD_END:
            counts["dead_end"] += 1
            continue
        if result.status == se.INTERRUPTED:
            counts["interrupted"] += 1
            continue
        counts["complete"] += 1
        identity = se.canonical_json(result.compilation)
        product = hidden.get(identity)
        if product is None:
            continue
        if index in validation_indices:
            counts["validation_proposals"] += 1
        elif index in test_indices:
            counts["test_proposals"] += 1
            if product <= threshold:
                counts["test_discoveries"] += 1
                discoveries.append({"index": str(index), "product": product})
                best_test_product = min(best_test_product, product)

    elapsed = time.perf_counter() - started
    return {
        "kind": "phase2_model_result",
        "fixture_id": spec["fixture_id"],
        "family": record["family"],
        "domain_sha256": domain.digest(),
        "program_sha256": se.object_digest(record["program"]),
        "semantic_sha256": se.program_semantic_digest(record["program"]),
        "codec": codec,
        "bits": bits,
        "arm": spec["arm"],
        "budget_seconds": budget,
        "search_seed": spec.get("search_seed"),
        "repetition": spec["repetition"],
        "status": PASS,
        "threshold": threshold,
        "elite_size": len(elite_indices),
        "split": {key: split[key] for key in ("total", "n_train", "n_validation", "n_test")},
        "counts": counts,
        "precision_at_threshold": (
            counts["test_discoveries"] / counts["complete"] if counts["complete"] else None
        ),
        "best_test_product": best_test_product,
        "training_best_product": min(train_products),
        "discoveries": discoveries[:50],
        "model_seconds": model_seconds,
        "seconds": elapsed,
        "cover_cubes": len(cover.cubes),
        "peak_rss_bytes": official.peak_rss_bytes(),
    }


def stage_p4(run: Run) -> dict:
    """Discovery beyond observed examples."""

    contract = run.contract
    directory = run.stage_dir("p4")
    run.prior("p1")
    run.prior("p3")
    stats = contract.statistics

    rows: List[dict] = []
    specs: List[dict] = []
    for record in contract.fixtures:
        for budget in contract.budgets["optimisation_seconds"]:
            for arm in sm.MODEL_ARMS:
                seeds = (
                    contract.seeds["search"] if arm == "uniform_bits" else [None]
                )
                for seed in seeds:
                    for repetition in range(stats["timing_repetitions"]):
                        specs.append(
                            {
                                "kind": "phase2_model_measurement",
                                "stage": "p4",
                                "corpus": "fixtures",
                                "fixture_id": record["id"],
                                "arm": arm,
                                "budget_seconds": budget,
                                "search_seed": seed,
                                "repetition": repetition,
                                "contract": str(contract.directory),
                            }
                        )
    for spec in specs:
        rows.append(run.harness.run(spec))
    write_jsonl(directory / "model_rows.jsonl", rows)

    analysis = p4_contrasts(rows, contract)
    advance = analysis["advance_to_model_arm"]

    summary = {
        "stage": "p4",
        "rows": len(rows),
        "failed_rows": sum(1 for row in rows if row.get("failed_row")),
        **analysis,
    }
    write_json(directory / "summary.json", summary)
    if not advance:
        raise StageBlocked(
            INCONCLUSIVE,
            "H4 advancement intervals do not exclude zero against both controls; "
            "the optional P5 model arm is not authorised",
        )
    return summary


def stage_p5(run: Run) -> dict:
    """External validity on public and held-out corpora, analysed separately."""

    contract = run.contract
    directory = run.stage_dir("p5")
    p0 = run.prior("p0")
    run.prior("p1")
    run.prior("p2")

    model_authorised = False
    model_reason = "P4 did not run"
    try:
        p4 = run.prior("p4")
        model_authorised = bool(p4.get("advance_to_model_arm"))
        model_reason = (
            "H4 advancement passed" if model_authorised
            else "H4 advancement intervals did not exclude zero"
        )
    except StageBlocked as blocked:
        model_reason = blocked.reason

    heldout = [
        {
            "path": entry["path"],
            "program_sha256": entry["program_sha256"],
            "family": entry["family"],
            "seed": entry["seed"],
        }
        for entry in p0["heldout"]["programs"]
    ]

    # One RNG for the whole stage; the two corpora are measured in order and
    # are never pooled in any analysis.
    rng = random.Random(contract.seeds["arm_order"])
    extra_arms = (MODEL_ARM,) if model_authorised else ()
    public_rows, public_accounting = _benchmark_corpus(
        run, "p5", "public", p0["public"], rng, extra_arms
    )
    heldout_rows, heldout_accounting = _benchmark_corpus(
        run, "p5", "heldout", heldout, rng, extra_arms
    )
    write_jsonl(directory / "public_rows.jsonl", public_rows)
    write_jsonl(directory / "heldout_rows.jsonl", heldout_rows)

    public_families = {entry["program_sha256"]: "public" for entry in p0["public"]}
    heldout_families = {
        entry["program_sha256"]: entry["family"] for entry in p0["heldout"]["programs"]
    }

    def analyse(rows, families, label) -> dict:
        contrasts = [
            ("accepted_budgeted", "structural_bound"),
            ("accepted_budgeted", "structural_dfs"),
            ("accepted_budgeted", "structural_expanded"),
        ]
        if model_authorised:
            contrasts.append(("structural_bound", MODEL_ARM))
        return {
            f"{candidate}_vs_{baseline}@{budget}": paired_log_ratio_analysis(
                rows, families, baseline, candidate, budget, contract
            )
            for budget in contract.budgets["optimisation_seconds"]
            for baseline, candidate in contrasts
        }

    # The arm's status is what its rows say, not what its authorisation says. A
    # disabled arm is NOT_RUN; an authorised arm with no measured row is a FAIL.
    model_rows = (
        public_accounting["model_arm_rows"] + heldout_accounting["model_arm_rows"]
    )
    if not model_authorised:
        model_status = NOT_RUN
    elif model_rows:
        model_status = PASS
    else:
        model_status = FAIL

    summary = {
        "stage": "p5",
        "model_arm": {
            "arm": MODEL_ARM,
            "status": model_status,
            "authorised": model_authorised,
            "measured_rows": model_rows,
            "reason": (
                model_reason if not model_authorised
                else (
                    f"{model_rows} measured rows across both corpora"
                    if model_rows
                    else "authorised but no row was measured"
                )
            ),
        },
        "public": {
            "rows": len(public_rows),
            "accounting": public_accounting,
            "comparisons": analyse(public_rows, public_families, "public"),
            "note": "public programs are development evidence, not holdout data",
        },
        "heldout": {
            "rows": len(heldout_rows),
            "accounting": heldout_accounting,
            "comparisons": analyse(heldout_rows, heldout_families, "heldout"),
            "programs": len(heldout),
            "families": sorted({entry["family"] for entry in heldout}),
        },
        "primary_budget_seconds": contract.budgets["primary_seconds"],
        "pooled": False,
    }
    write_json(directory / "summary.json", summary)

    failures = public_accounting["failed_rows"] + heldout_accounting["failed_rows"]
    if failures:
        raise StageBlocked(
            FAIL, f"{failures} failed rows are retained and block any success claim"
        )
    if not (public_accounting["membership_exact"] and heldout_accounting["membership_exact"]):
        raise StageBlocked(FAIL, "P5 membership is not exactly the expected key set")
    if model_status == FAIL:
        raise StageBlocked(
            FAIL,
            f"{MODEL_ARM} was authorised by H4 and produced no measured row; an "
            "authorised arm is never PASS without measurements",
        )
    return summary


# --------------------------------------------------------------------------
# Evidence documents
# --------------------------------------------------------------------------


OWNERSHIP_TEXT = """# Ownership record for the phase 2 research system

Written before the code, as the repository's single-owner law requires: locate
the owner first, never after.

## Q1 -- where does the core of each concept live?

| Concept | Owner | This package |
|---|---|---|
| Hardware semantics, independent acceptance | `.reference/machine.py` (pinned) | imported, never restated |
| Derived program facts, lifetimes, assembly, footprint, lower bounds | `direct_contract.py` | imported |
| Cubes, exact set algebra, budgets and meters | `schema_index.py` | imported |
| The absolute-field joint query | `direct_constraints.py` | used unchanged as a control |
| Accepted target and window policy | `direct_optimizer.targets_for`, `windows_for` | called, not copied |
| Accepted compiler, its bootstrap and its limits | `direct_compiler.py` | called, not copied |
| Corpus generation | `tests_direct/generate_programs.additional_program` | called, not copied |
| Peak RSS conversion, file digests | `compare_direct.py` | imported |
| Production source list | `verify_direct.SOURCES` | imported |

New owners created here, each with one responsibility:

| Owner | Responsibility |
|---|---|
| `research/structural_encoding.py` | Domain, fixed layout, options, encode/decode, all four codecs, canonical JSON |
| `research/structural_search.py` | DFS traversal, admissible bounds, acceptance policy |
| `research/structural_models.py` | Cover merge, byte format, proposal policies |
| `research/structural_oracle.py` | Independent enumeration and hidden evaluation |
| `research/run_structural_experiments.py` | CLI, harness, corpora, P0-P5 orchestration |
| `research/check_structural_evidence.py` | Independent artifact checks and gate recomputation |

Owners added by the 2026-09-23 lead repair, each because the checker needed to
recompute a number the runner had produced inline. The rule applied was
enrich-the-owner: the computation moved into one named function in the module
that already owned the stage, and the checker now calls that function on the
*raw rows* instead of holding a second copy of the statistic.

| Owner | Responsibility | Called by |
|---|---|---|
| `run_structural_experiments.AttemptSink` | Streams one raw JSONL row per sampling attempt | `stage_p1` |
| `run_structural_experiments.control_serialisation` | The P3 control covers and their median | `stage_p3`, the checker |
| `run_structural_experiments.p4_contrasts` | The P4 contrasts, H4 bounds and advancement flag | `stage_p4`, the checker |
| `run_structural_experiments._model_optimise` | The conditional half-search/half-model arm | `structural_optimise` |
| `structural_models.ordered_union` | Lazy ascending distinct members of a cube union | `cover_members`, `proposals` |

`cover_members` became the eager form of `ordered_union` rather than a second
traversal, so the exact-cover equality check and the lazy proposal stream cannot
disagree about what a cover denotes.

## Q2 -- does each concept already exist under another name?

Searched by body fragment and by behaviour, not by name.

* *Bundles to issue cycles.* Three test modules and `common.py` each inline the
  same comprehension. The owner that also validates it is
  `machine._collect_issue_cycles`; `structural_encoding.issue_cycles_of` calls
  that one rather than making a fifth copy. `common.py` is a declared exception
  and is barred from the production path, so it is not a candidate owner.
* *Cube algebra.* `schema_index` owns it. Nothing here defines `Cube`,
  `intersect`, `difference` or a cover normaliser.
* *Budgets and deadlines.* `schema_index.Budget`/`Meter` own budgeted work with
  a deadline; the decoder and the search charge against them instead of
  inventing a second meter.
* *Paired bootstrap.* `benchmark_optimization.paired_bootstrap` resamples
  repetition identifiers within a fixed suite. Phase 2's primary interval
  resamples *programs within family with families weighted equally*, which is a
  different estimand over a different sampling unit. They are two statistics,
  so they keep two names and both are reported; neither replaces the other.
* *Lower bounds on C and S.* `direct_contract` owns
  `cycle_lower_bound`, `memory_lower_bound`; `structural_search` composes them
  with prefix information rather than restating them.

## Q3 -- why is a new owner needed rather than enriching an existing one?

Because the contract makes this an *isolated research path* that must not change
production. Enriching `direct_compiler` or `direct_constraints` would put
research code inside the accepted compiler's dependency graph and inside the
release contract. The new owners depend on the production owners; no production
owner depends on them, and `export_direct.py` is unchanged.

The independent oracle is the one place where sharing is forbidden in the other
direction: it may not import the codec, the search or the derived legality
checker, because its whole value is deciding membership by a path that shares no
feasibility predicate with the candidate.

## Q4 -- what executable guard keeps each owner single?

`research/check_structural_evidence.py --architecture` runs in the same commit:

1. an AST scan of `research/` for a second definition of a machine constant, a
   cube type or a cover operation;
2. an import-boundary check that the oracle's module graph excludes
   `research.structural_encoding`, `research.structural_search`,
   `research.structural_models` and `direct_contract`, evaluated at run time in
   a subprocess rather than read off the source;
3. planted-copy and planted-import fixtures, which the guard must reject while
   the unmutated control passes.

The AST scan is supporting evidence with a stated limit: it detects a duplicate
*definition*, not a semantically equivalent reimplementation spelled differently.
The runtime import check is what closes the oracle boundary.
"""


PROOFS_TEXT = """# Proof obligations for the structural codec

Plan section 5.2 lists seven obligations. Each is stated here as an argument
over the implementation and is accompanied by the machine-checked evidence the
run produced. An argument without its evidence file is not discharged.

Throughout, `d` is a `Domain`, `F_d` is the set of normalised compilations that
satisfy its declared domains, its fixed decisions and the pinned machine rules,
and `B` is the width of `layout(d, codec)`.

## 1. Termination

The layout fixes a finite list of decisions: one field per selected operation
and one per selected value, chosen once at `Domain` construction and never
recomputed. Each decision consults a finite option list, a subset of a declared
domain that `Domain.from_record` has already checked to be finite and nonempty.
`decode` therefore performs at most `len(layout.fields)` decisions and each does
bounded work, so it terminates. Budget exhaustion is a separate execution
status, `INTERRUPTED`, and never an infinite loop.

## 2. Soundness

Each constraint is checked exactly once, at the decision that fixes its last
free argument.

* *Precedence.* In a straight-line SSA program every data or memory predecessor
  has a smaller operation identifier, and selected times are assigned in
  ascending identifier order, so at the moment operation `i` is assigned, every
  predecessor is already fixed or already assigned. `State.time_options`
  therefore checks all of them. A *successor* may have a larger identifier; if
  it is external its time is fixed, and the same method checks it now. If it is
  selected, the constraint is re-checked from the other side when that later
  decision is taken.
* *Capacity.* `State.time_options` counts the operations, fixed and assigned,
  already at that cycle on that engine and refuses the option at the limit.
* *Allocation.* Addresses are only offered once every issue time is known, so
  `State.recompute_lifetimes` has the complete inclusive live interval of every
  value, including values whose interval moved because a selected consumer
  moved. `State.address_options` rejects any base whose block overlaps a fixed
  or already-placed block over overlapping lifetimes.
* *Closure.* Nothing is left unchecked: every completed decode is handed to
  `direct_contract.check_feasible` and to `machine.check_compilation`, and a
  rejection raises `CodecDefect` rather than being reported as `DEAD_END`.

Evidence: `p1/summary.json` -- zero defects over every exhausted code universe
and every round trip.

## 3. Completeness over F_d

Take `x` in `F_d` and follow the prescribed decision order. At each decision the
value `x` gives is (i) in the declared domain, by definition of `F_d`, and (ii)
compatible with every already-fixed decision, because `x` is legal under the
pinned machine. Both are exactly the tests `State.time_options` and
`State.address_options` apply, so the value appears in the option list and has a
rank. The induction constructs the full rank sequence, hence an encoding of `x`.

This argument fails the moment options are pruned for quality. That is why
option construction never consults the objective, the incumbent's lifetimes or
an oracle; pruning lives in `structural_search`, outside the codec.

Evidence: `p1/summary.json` -- `set_equality` against the independent oracle on
every fixture whose code universe is at most sixteen bits, and a successful
round trip of every feasible oracle object for every codec at every width.

## 4. Round trip

`encode` replays the same traversal, computing the same option lists from the
same state, and writes each rank into the field that `layout` assigned. `decode`
reads those fields back in the same traversal and reconstructs the same choices.
Hence `decode(encode(x)) = x` for `x` in `F_d`.

Evidence: the round-trip counts in `p1/summary.json`.

## 5. Injectivity

Two distinct successful codes differ in some field. Consider the first decision
at which their field values differ. Up to that point both decodes have made
identical choices, so both compute the *same* option list; distinct ranks into
one list select distinct options, so the resulting compilations differ. No bit
is ignored: `B` is the sum of the field widths and `decode` reads every field
before it can return `COMPLETE`, which the run-time reassembly check in `decode`
confirms on every successful decode. Lane labels are not part of the object, so
no auxiliary multiplicity is hidden.

Evidence: `p1/summary.json` -- no duplicate-object findings over any exhausted
universe; `encode(decode(z)) == z` on every feasible object.

## 6. Domain equivalence

`research/structural_oracle.py` enumerates the declared Cartesian product and
accepts with `machine.check_compilation` and `machine.check_case` alone. It
imports neither the codec nor `direct_contract`, so agreement between the two
sets is not a tautology.

Evidence: `p1/oracle_domains.jsonl` and the `set_equality` field per fixture.

## 7. Origin

`Domain.ordered_domain` places the incumbent's choice first whenever that choice
is present. Under a rank codec the all-zero code takes rank 0 at every decision.
If the incumbent lies in `F_d`, completeness (section 3) puts its choice in every
option list, and it is ordered first, so `decode(0)` is the incumbent.

The property is conditional, and the contract says so: an improvement target may
exclude the incumbent, in which case `decode(0)` legitimately returns `DEAD_END`
at the target predicate. Domains used to study distance from the origin contain
the incumbent and apply the improvement predicate separately.

Evidence: `origin_is_incumbent` per fixture in `p1/summary.json`, and the same
property observed on all eight public whole-program domains.

## 8. Sampled completions execute their program's cases

Added by the 2026-09-23 lead repair, which found that no obligation above
required a sampled public compilation to be *run*. `decode` checks static
feasibility and `machine.check_compilation`; neither executes a case. Sections 2
to 7 are therefore statements about legality and about the map, not about
behaviour, and the earlier claim that the correctness obligations were fully
discharged for the sampled public outputs was too strong.

Every completed decode in a P1 sampling stream is now handed to
`machine.check_case` once per declared case, inside the stream's own time budget.
A rejection is retained as a discrepancy artifact and fails the stage; it is never
converted to `DEAD_END` and never dropped.

Evidence: `sampling_case_checks`, `sampling_case_failures` and
`sampling_discrepancies` in `p1/summary.json`, reconciled row by row against
`cases_checked` in `p1/sampling_attempts.jsonl`, which holds one row per draw.

## What these arguments do not establish

They are statements about *this* codec over *this* declared `F_d`. They do not
show that the encoding is total on binary strings -- it is deliberately partial.
They do not show that every locally legal prefix has a completion; dead ends are
detected and counted, not proved absent. They do not transfer to an online
chronological decoder, which needs new invariants. A counterexample here would
refute this implementation, not all possible structural encodings.
"""


def write_manifest(run: Run, stages_run: Sequence[str], stage_digests: Dict[str, str]) -> dict:
    contract = run.contract
    manifest = {
        "run_id": run.run_id,
        "protocol_id": contract.protocol["protocol_id"],
        "plan_version": contract.protocol["plan_version"],
        "schema_version": contract.protocol["schema_version"],
        "started_epoch": run.started,
        "finished_epoch": time.time(),
        "python": sys.version,
        "platform": platform.platform(),
        "contract_files": {
            name: file_digest(contract.directory / name)
            for name in sorted(path.name for path in contract.directory.iterdir()
                               if path.is_file())
        },
        "plan_sha256": file_digest(ROOT / "plan" / "PHASE2_STRUCTURAL_ENCODING_PLAN.md"),
        "amendment_files": {name: file_digest(ROOT / name) for name in AMENDMENT_FILES},
        "source_snapshot": source_snapshot(),
        "baseline_state": contract.verify_locks(),
        "git": {key: value for key, value in git_state().items() if key != "diff"},
        "stages_run": list(stages_run),
        "stage_status": {stage: entry["status"] for stage, entry in run.gates.items()},
        "stage_digests": stage_digests,
        "row_counts": {},
    }
    for path in sorted(run.root.rglob("*.jsonl")):
        manifest["row_counts"][str(path.relative_to(run.root))] = sum(
            1 for line in path.read_text().splitlines() if line.strip()
        )
    return manifest


def write_handoff(run: Run, manifest: dict, hypotheses: Dict[str, dict]) -> None:
    template = (run.contract.directory / "HANDOFF_TEMPLATE.md").read_text()
    lines: List[str] = []
    lines.append("| Stage | Status | Gate evidence | Dependencies blocked / reason |")
    lines.append("|---|---|---|---|")
    for stage in ("p0", "p1", "p2", "p3", "p4", "p5"):
        entry = run.gates.get(stage, {"status": NOT_RUN, "reason": "not reached"})
        lines.append(
            f"| {stage.upper()} | {entry['status']} | `{stage}/summary.json` | "
            f"{entry['reason']} |"
        )
    stage_table = "\n".join(lines)

    hypothesis_lines = ["| Hypothesis | Disposition | Evidence and limits |", "|---|---|---|"]
    for name in ("H1", "H2", "H3", "H4"):
        entry = hypotheses.get(name, {"status": NOT_RUN, "evidence": "not reached"})
        hypothesis_lines.append(
            f"| {name} | {entry['status']} | {entry['evidence']} |"
        )

    filled = template.replace(
        "| Stage | Status | Gate evidence | Dependencies blocked / reason |\n|---|---|---|---|\n"
        "| P0 | | | |\n| P1 | | | |\n| P2 | | | |\n| P3 | | | |\n| P4 | | | |\n| P5 | | | |",
        stage_table,
    ).replace(
        "| Hypothesis | Supported / unsupported / inconclusive / not run | Evidence and limits |"
        "\n|---|---|---|\n| H1 | | |\n| H2 | | |\n| H3 | | |\n| H4 | | |",
        "\n".join(hypothesis_lines),
    )
    filled = filled.replace(
        "Implementer/model:", f"Implementer/model: Claude Code (Opus 5), run `{run.run_id}`"
    ).replace(
        "Source HEAD, dirty diff SHA256, source snapshot SHA256:",
        "Source HEAD, dirty diff SHA256, source snapshot SHA256: "
        f"`{manifest['git']['head']}`, `{git_state()['diff_sha256']}`, "
        f"`{manifest['source_snapshot']['snapshot_sha256']}`",
    ).replace(
        "Run directory:", f"Run directory: `{run.root.relative_to(ROOT)}`"
    )
    (run.root / "HANDOFF.md").write_text(filled)


def hypothesis_dispositions(run: Run) -> Dict[str, dict]:
    def read(stage: str) -> Optional[dict]:
        path = run.root / stage / "summary.json"
        return json.loads(path.read_text()) if path.is_file() else None

    p1, p2, p3, p4, p5 = (read(stage) for stage in ("p1", "p2", "p3", "p4", "p5"))
    result: Dict[str, dict] = {}

    if p1 is None:
        result["H1"] = {"status": NOT_RUN, "evidence": "P1 did not produce a summary"}
    else:
        sound = (
            p1["defect_count"] == 0
            and p1["round_trip_failures"] == 0
            and p1["set_equality_all"]
        )
        result["H1"] = {
            "status": "supported" if sound and p1["coverage_met"] else
                      ("inconclusive" if sound else "unsupported"),
            "evidence": (
                f"{p1['exhausted_comparisons']} exhausted codec/oracle comparisons with exact "
                f"set equality, {p1['round_trip_failures']} round-trip failures, "
                f"{p1['defect_count']} defects; public coverage met: {p1['coverage_met']}. "
                "Scope is the implemented F_d, not all structural encodings."
            ),
        }

    if p2 is None:
        result["H2"] = {"status": NOT_RUN, "evidence": "P2 did not produce a summary"}
    else:
        key = f"structural_bound_vs_accepted_budgeted@{p2['primary_budget_seconds']}"
        entry = p2["comparisons"].get(key, {})
        interval = entry.get("interval", {}).get("intervals", {}).get("0.025-0.975")
        result["H2"] = {
            "status": (
                "inconclusive" if not interval or interval[0] <= 0 <= interval[1]
                else ("supported" if interval[0] > 0 else "unsupported")
            ),
            "evidence": (
                f"public primary contrast {key}: {entry.get('wins')} wins / "
                f"{entry.get('ties')} ties / {entry.get('losses')} losses over "
                f"{entry.get('programs')} programs, 95% interval {interval}. "
                "Held-out evidence is in p5."
            ),
        }

    if p3 is None:
        result["H3"] = {"status": NOT_RUN, "evidence": "P3 did not produce a summary"}
    else:
        result["H3"] = {
            "status": "supported" if p3["triage"]["status"] == PASS else "unsupported",
            "evidence": (
                f"{p3['qualifying_count']}/{p3['informative_count']} informative fixtures "
                f"met the 20% triage margin across families {p3['qualifying_families']}; "
                f"informative families {p3['informative_families']}. "
                "This is a research triage threshold, not statistical proof."
            ),
        }

    if p4 is None:
        result["H4"] = {
            "status": NOT_RUN,
            "evidence": "P4 did not produce a summary; see its gate reason",
        }
    else:
        result["H4"] = {
            "status": "supported" if p4["advance_to_model_arm"] else "inconclusive",
            "evidence": (
                f"Bonferroni 97.5% lower bounds {p4['h4_gate_lower_bounds']} against both "
                f"controls; empirical-cover test discoveries "
                f"{p4['empirical_cover_test_discoveries']} (an exact cover of observed "
                "elites cannot discover unseen indices)."
            ),
        }
    return result


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------


STAGE_FUNCTIONS = {
    "preflight": stage_preflight,
    "p0": stage_p0,
    "p1": stage_p1,
    "p2": stage_p2,
    "p3": stage_p3,
    "p4": stage_p4,
    "p5": stage_p5,
}

# P0 -> P1 -> {P2, P3}; P3's triage -> P4; P2 -> P5. H4 gates only the optional
# P5 model arm, which is why P4 is not a dependency of P5 here.
DEPENDENCIES = {
    "preflight": (),
    "p0": ("preflight",),
    "p1": ("p0",),
    "p2": ("p1",),
    "p3": ("p1",),
    "p4": ("p1", "p3"),
    "p5": ("p1", "p2"),
}


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="research.run_structural_experiments",
        description="Phase 2 structural-encoding research campaign (P0-P5).",
    )
    parser.add_argument("--stage", choices=ALL_STAGES)
    parser.add_argument("--run-id")
    parser.add_argument("--contract", default="plan/phase2")
    parser.add_argument(
        "--inputs",
        help="a prior run directory, read only, for a single-stage invocation",
    )
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    return parser.parse_args(list(argv))


def main(argv: Sequence[str]) -> int:
    arguments = parse_args(argv)

    if arguments.worker is not None:
        # Internal entry point. It validates its own identity and is not an
        # alternative acceptance mode: it measures one row and says so.
        try:
            spec = json.loads(arguments.worker)
            if spec.get("kind") == "phase2_model_measurement":
                contract = Contract(Path(spec["contract"]))
                result = run_model_measurement(spec, contract)
            else:
                result = run_measurement(spec)
        except (StageBlocked, ValueError, KeyError, OSError,
                machine.CompileError, machine.ProgramError,
                dcomp.CompilationFailure, se.DomainError, se.CodecDefect) as exc:
            print(f"worker failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return EXIT_FAILURE
        sys.stdout.write(se.canonical_json(result) + "\n")
        return EXIT_OK

    if arguments.stage is None or arguments.run_id is None:
        print("usage: --stage STAGE --run-id RUN_ID [--contract DIR] [--inputs RUN]",
              file=sys.stderr)
        return EXIT_USAGE

    contract_path = Path(arguments.contract)
    if not contract_path.is_absolute():
        contract_path = ROOT / contract_path
    try:
        contract = Contract(contract_path)
    except (StageBlocked, OSError, json.JSONDecodeError) as exc:
        print(f"contract inputs unusable: {exc}", file=sys.stderr)
        return EXIT_USAGE

    inputs = None
    if arguments.inputs:
        inputs = Path(arguments.inputs)
        if not inputs.is_absolute():
            inputs = ROOT / inputs
        if not (inputs / "manifest.json").is_file():
            print(f"--inputs {inputs} is not a completed run", file=sys.stderr)
            return EXIT_USAGE
        if arguments.stage == "all":
            print("--inputs applies to a single-stage invocation only", file=sys.stderr)
            return EXIT_USAGE

    try:
        run = Run(arguments.run_id, contract, inputs)
    except FileExistsError:
        print(
            f"run {arguments.run_id} already exists and is never overwritten",
            file=sys.stderr,
        )
        return EXIT_USAGE
    except StageBlocked as exc:
        print(exc.reason, file=sys.stderr)
        return EXIT_USAGE

    (run.root / "OWNERSHIP.md").write_text(OWNERSHIP_TEXT)
    (run.root / "PROOFS.md").write_text(PROOFS_TEXT)

    requested = STAGES if arguments.stage == "all" else (arguments.stage,)
    if arguments.stage != "all" and arguments.stage != "preflight":
        requested = ("preflight", arguments.stage)

    exit_code = EXIT_OK
    stages_run: List[str] = []
    stage_digests: Dict[str, str] = {}

    for stage in requested:
        # Blocking happens *before* the stage body is entered, and an imported
        # dependency is judged by the same rule as a local one. Until the
        # 2026-09-23 repair this block was skipped entirely whenever --inputs was
        # given, so a dependent stage could be started on an INCONCLUSIVE
        # dependency. There is no flag that relaxes this.
        blocked_by: List[str] = []
        integrity: List[str] = []
        for dependency in DEPENDENCIES[stage]:
            status, source = run.dependency_status(dependency)
            if status != PASS:
                blocked_by.append(f"{dependency} ({status}, {source})")
                continue
            if source == "imported":
                try:
                    run.verify_imported(dependency)
                except StageBlocked as failure:
                    if failure.status == FAIL:
                        integrity.append(f"{dependency}: {failure.reason}")
                    else:
                        blocked_by.append(f"{dependency} ({failure.reason})")
        if integrity:
            run.record(
                stage, FAIL, "; ".join(integrity), {"dependencies": list(DEPENDENCIES[stage])}
            )
            exit_code = EXIT_FAILURE
            continue
        if blocked_by:
            run.record(
                stage, BLOCKED,
                f"blocked by {', '.join(blocked_by)}", {"dependencies": blocked_by},
            )
            if exit_code == EXIT_OK:
                exit_code = EXIT_USAGE
            continue
        log = run.root / "logs" / f"{stage}.log"
        started = time.time()
        try:
            summary = STAGE_FUNCTIONS[stage](run)
            run.record(stage, PASS, "gate satisfied", {"seconds": time.time() - started})
            stages_run.append(stage)
        except StageBlocked as blocked:
            run.record(stage, blocked.status, blocked.reason,
                       {"seconds": time.time() - started})
            stages_run.append(stage)
            if blocked.status == FAIL:
                exit_code = EXIT_FAILURE
            elif blocked.status == INCONCLUSIVE and exit_code == EXIT_OK:
                # A mandatory stage that ran but could not establish its gate is
                # incomplete mandatory evidence, not a scientific null result.
                # The two deserve different exit codes and this is the former.
                exit_code = EXIT_USAGE
            elif exit_code == EXIT_OK and blocked.status != PASS:
                exit_code = EXIT_USAGE
        except Exception as exc:  # noqa: BLE001 - a crash is evidence, not a silent stop
            run.record(
                stage, FAIL, f"{type(exc).__name__}: {exc}",
                {"seconds": time.time() - started},
            )
            stages_run.append(stage)
            exit_code = EXIT_FAILURE
            log.write_text(f"{type(exc).__name__}: {exc}\n")
        summary_path = run.root / stage / "summary.json"
        if summary_path.is_file():
            stage_digests[stage] = file_digest(summary_path)

    for stage in STAGES:
        if stage not in run.gates:
            # A dependant is BLOCKED_BY_GATE only when a dependency actually
            # failed or missed its gate. A stage that simply was not requested,
            # and whose dependencies were not requested either, is NOT_RUN.
            blocking = [
                dependency for dependency in DEPENDENCIES[stage]
                if run.gates.get(dependency, {}).get("status")
                in (FAIL, INCONCLUSIVE, BLOCKED)
            ]
            run.record(
                stage,
                BLOCKED if blocking else NOT_RUN,
                f"blocked by {', '.join(blocking)}" if blocking else "not requested",
                {"dependencies": blocking},
            )

    write_jsonl(run.root / "commands.jsonl", run.harness.commands)
    write_json(run.root / "gates.json", run.gates)
    hypotheses = hypothesis_dispositions(run)
    write_json(run.root / "hypotheses.json", hypotheses)
    manifest = write_manifest(run, stages_run, stage_digests)
    write_json(run.root / "manifest.json", manifest)
    write_handoff(run, manifest, hypotheses)

    print(se.canonical_json({
        "run": str(run.root.relative_to(ROOT)),
        "stages": {stage: entry["status"] for stage, entry in sorted(run.gates.items())},
        "hypotheses": {name: entry["status"] for name, entry in sorted(hypotheses.items())},
        "exit": exit_code,
        "note": "this banner establishes nothing; run check_structural_evidence",
    }))
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
