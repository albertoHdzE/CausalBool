"""The phase 2 research codec: state-relative coordinates for compilations.

This module owns exactly four things, per the implementation contract, section 4:

* ``Domain`` -- a finite domain specification ``d`` and its validation;
* ``layout`` -- the fixed field layout of a domain under one codec;
* ``options`` -- the deterministic ordered option list at one decision;
* ``decode``/``encode`` -- the partial coordinate maps for all four codecs.

It owns nothing else. Hardware semantics stay in the pinned ``machine`` module,
derived program facts and lifetimes stay in ``direct_contract``, and budgets and
cube algebra stay in ``schema_index``. Canonical JSON lives here because it is a
serialisation convention shared by the search, the models, the runner and the
checker; the independent oracle deliberately does not import this module, so it
never sees a candidate feasibility predicate (contract section 4).

The codec is deliberately **partial** on binary strings. Plan section 5.1: a
finite feasible set need not have power-of-two cardinality, so invalid codes are
expected, counted and never padded away. Status precedence at a decision is
fixed by the contract: empty options are ``DEAD_END`` first, then an out-of-range
rank is ``INVALID_CODE``. A code that decodes completely but yields a
compilation the pinned validator rejects is a defect, not a ``DEAD_END``: it
raises ``CodecDefect`` so the stage fails with the counterexample retained.
"""

from __future__ import annotations

from dataclasses import dataclass, field as _dataclass_field
import hashlib
import json
from typing import Dict, List, Optional, Sequence, Tuple

import machine

import direct_contract as dc
import schema_index as si


__all__ = [
    "CODECS",
    "COMPLETE",
    "INVALID_CODE",
    "DEAD_END",
    "INTERRUPTED",
    "DomainError",
    "CodecDefect",
    "Domain",
    "FieldSpec",
    "Layout",
    "State",
    "DecodeResult",
    "layout",
    "options",
    "decode",
    "encode",
    "canonical_json",
    "object_digest",
    "normalise_compilation",
    "compilation_identity",
    "program_semantic_digest",
    "issue_cycles_of",
    "objective",
]


CODECS = ("absolute", "static_rank", "vector_block", "structural_rank")

COMPLETE = "COMPLETE"
INVALID_CODE = "INVALID_CODE"
DEAD_END = "DEAD_END"
INTERRUPTED = "INTERRUPTED"

STATUSES = (COMPLETE, INVALID_CODE, DEAD_END, INTERRUPTED)

# The block index of a vector address under the ``vector_block`` codec. Thirty
# two blocks of ``machine.VLEN`` words cover the whole scratchpad exactly, so
# five bits suffice and the scaling ``a = VLEN * b`` never truncates.
VECTOR_BLOCK_WIDTH = 5


class DomainError(ValueError):
    """An input domain, index or compilation was malformed or out of range.

    This is a caller error, never a decode outcome. A malformed domain is not
    an empty feasible set: the contract requires contradictory fixtures to be
    expressed through fixed constraints, not through a malformed ``Domain``.
    """


class CodecDefect(AssertionError):
    """A fully decoded compilation was rejected by an independent check.

    Plan section 5.1: "A decoded compilation rejected by the independent
    validator is a correctness defect." It is retained and it fails the stage;
    it is never translated into ``DEAD_END``.
    """

    def __init__(self, reason: str, evidence: dict) -> None:
        super().__init__(reason)
        self.reason = reason
        self.evidence = evidence


# --------------------------------------------------------------------------
# Canonical data conventions (contract section 9)
# --------------------------------------------------------------------------


def canonical_json(value: object) -> str:
    """UTF-8 canonical form, without a trailing newline."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def object_digest(value: object) -> str:
    """SHA256 of the canonical bytes of an object.

    Distinct from a file digest, which hashes actual file bytes. Callers state
    which of the two they mean.
    """

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def program_semantic_digest(program: dict) -> str:
    """The digest of a program with only its top-level display name removed.

    Operation identifiers, constants, buffers and cases are all retained, so two
    programs that differ in anything but their name have different digests.
    """

    stripped = {key: value for key, value in program.items() if key != "name"}
    return object_digest(stripped)


def normalise_compilation(facts: dc.ProgramFacts, compiled: dict) -> dict:
    """Bundles by increasing operation ID within each engine, trailing empties cut.

    Plan section 3. Internal empty bundles are part of the object -- they are
    the idle cycles that make ``C`` what it is -- and only *trailing* empties are
    removed. Lane labels are not part of the compilation object, so the engine
    keys are the only structure retained.
    """

    if not isinstance(compiled, dict):
        raise DomainError("a compilation must be an object")
    bundles = compiled.get("bundles")
    scratch = compiled.get("scratch")
    if not isinstance(bundles, list) or not isinstance(scratch, dict):
        raise DomainError("a compilation requires a bundles list and a scratch mapping")

    cleaned: List[Dict[str, List[int]]] = []
    for cycle, bundle in enumerate(bundles):
        if not isinstance(bundle, dict):
            raise DomainError(f"bundle {cycle} must be an object")
        engines: Dict[str, List[int]] = {}
        for engine, op_ids in bundle.items():
            if engine not in machine.ENGINE_LIMITS:
                raise DomainError(f"bundle {cycle} names unknown engine {engine!r}")
            if not isinstance(op_ids, list):
                raise DomainError(f"bundle {cycle} engine {engine} must hold a list")
            ordered = sorted(op_ids)
            if len(set(ordered)) != len(ordered):
                raise DomainError(f"bundle {cycle} repeats an operation")
            # An empty engine bundle carries no information; the engine key is
            # dropped so that two spellings of the same object cannot differ.
            if ordered:
                engines[engine] = ordered
        cleaned.append(engines)
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    if not cleaned:
        raise DomainError("a compilation must emit at least one bundle")

    placed = [op_id for bundle in cleaned for ids in bundle.values() for op_id in ids]
    if sorted(placed) != list(range(facts.count)):
        raise DomainError("every operation must appear exactly once in the bundles")
    if set(scratch) != set(facts.value_names):
        raise DomainError("every produced value requires exactly one scratch address")
    return {
        "bundles": cleaned,
        "scratch": {name: scratch[name] for name in sorted(scratch)},
    }


def compilation_identity(facts: dc.ProgramFacts, compiled: dict) -> str:
    """The canonical digest of a normalised compilation."""

    return object_digest(normalise_compilation(facts, compiled))


def issue_cycles_of(program: dict, bundles: Sequence[dict]) -> Dict[int, int]:
    """The issue cycle of every operation, from the pinned owner of that inverse.

    ``machine._collect_issue_cycles`` is the only implementation of this
    inversion that also enforces the engine, duplicate and missing-operation
    rules while doing it. Restating the two-line comprehension here would make a
    second owner of a machine fact, which the repository's single-owner rule
    forbids; the pinned file is hash-locked, so the private name cannot drift.
    """

    return machine._collect_issue_cycles(program, list(bundles))


def objective(facts: dc.ProgramFacts, times: Dict[int, int], addresses: Dict[str, int]):
    """``(C, S, J)`` for a complete schedule and allocation."""

    cycles = max(times.values()) + 1
    scratch = dc.footprint(facts, addresses)
    return cycles, scratch, cycles * scratch


# --------------------------------------------------------------------------
# Domain
# --------------------------------------------------------------------------


def _plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _checked_domain(values: object, label: str) -> Tuple[int, ...]:
    if not isinstance(values, (list, tuple)):
        raise DomainError(f"{label}: a domain must be a list of integers")
    items = list(values)
    if not items:
        raise DomainError(f"{label}: a declared domain must be nonempty")
    for item in items:
        if not _plain_int(item):
            raise DomainError(f"{label}: domains hold plain integers, not {item!r}")
        if item < 0:
            raise DomainError(f"{label}: negative domain value {item}")
    if items != sorted(set(items)):
        raise DomainError(f"{label}: domains must be sorted, unique and explicit")
    return tuple(items)


@dataclass(frozen=True)
class Domain:
    """One finite domain specification ``d`` of plan section 3.

    ``F_d`` is every normalised compilation that satisfies these declared
    domains, the fixed decisions and the pinned machine rules. An *empty* ``F_d``
    is a legitimate fixture; a malformed domain is not.
    """

    identifier: str
    family: str
    program: dict
    facts: dc.ProgramFacts
    selected_operations: Tuple[int, ...]
    selected_values: Tuple[str, ...]
    time_domains: Dict[int, Tuple[int, ...]]
    address_domains: Dict[str, Tuple[int, ...]]
    fixed_times: Dict[int, int]
    fixed_addresses: Dict[str, int]
    incumbent: Optional[dict]
    incumbent_times: Optional[Dict[int, int]]
    incumbent_addresses: Optional[Dict[str, int]]
    target: Optional[Tuple[int, int]]
    record: dict

    # -- construction ------------------------------------------------------

    @staticmethod
    def from_record(record: dict) -> "Domain":
        if not isinstance(record, dict):
            raise DomainError("a domain record must be an object")
        for key in ("id", "program", "selected_operations", "time_domains",
                    "address_domains", "fixed_times", "fixed_addresses"):
            if key not in record:
                raise DomainError(f"domain record is missing {key!r}")

        program = record["program"]
        machine.validate_program(program)
        facts = dc.derive(program)

        selected = record["selected_operations"]
        if not isinstance(selected, (list, tuple)):
            raise DomainError("selected_operations must be a list")
        selected_ops = tuple(selected)
        for op_id in selected_ops:
            if not _plain_int(op_id) or not 0 <= op_id < facts.count:
                raise DomainError(f"unknown selected operation {op_id!r}")
        if selected_ops != tuple(sorted(set(selected_ops))):
            raise DomainError("selected_operations must be sorted and unique")

        time_domains: Dict[int, Tuple[int, ...]] = {}
        for key, values in record["time_domains"].items():
            op_id = _key_to_op(key, facts.count)
            time_domains[op_id] = _checked_domain(values, f"time domain {op_id}")
            for value in time_domains[op_id]:
                if value >= facts.horizon:
                    raise DomainError(
                        f"time domain {op_id}: {value} is at or past horizon "
                        f"{facts.horizon}"
                    )

        fixed_times: Dict[int, int] = {}
        for key, value in record["fixed_times"].items():
            op_id = _key_to_op(key, facts.count)
            if not _plain_int(value) or not 0 <= value < facts.horizon:
                raise DomainError(f"fixed time for operation {op_id} is out of range")
            fixed_times[op_id] = value

        if set(time_domains) != set(selected_ops):
            raise DomainError("a time domain is required for exactly the selected operations")
        if set(time_domains) & set(fixed_times):
            raise DomainError("an operation cannot be both selected and fixed in time")
        if set(time_domains) | set(fixed_times) != set(range(facts.count)):
            raise DomainError("every operation needs exactly one variable or fixed time")

        # The selected values are exactly the results of the selected operations.
        expected_values = tuple(
            facts.dest[op_id] for op_id in selected_ops if facts.dest[op_id] is not None
        )
        address_domains: Dict[str, Tuple[int, ...]] = {}
        for name, values in record["address_domains"].items():
            if name not in facts.value_names:
                raise DomainError(f"address domain names unknown value {name!r}")
            width = facts.width[name]
            address_domains[name] = _checked_domain(values, f"address domain {name}")
            for value in address_domains[name]:
                _check_address(name, value, width)
        if tuple(sorted(address_domains)) != tuple(sorted(expected_values)):
            raise DomainError(
                "selected values must be exactly the results of the selected operations"
            )

        fixed_addresses: Dict[str, int] = {}
        for name, value in record["fixed_addresses"].items():
            if name not in facts.value_names:
                raise DomainError(f"fixed address names unknown value {name!r}")
            if not _plain_int(value):
                raise DomainError(f"fixed address for {name!r} must be an integer")
            _check_address(name, value, facts.width[name])
            fixed_addresses[name] = value
        if set(address_domains) & set(fixed_addresses):
            raise DomainError("a value cannot be both selected and fixed in address")
        if set(address_domains) | set(fixed_addresses) != set(facts.value_names):
            raise DomainError("every value needs exactly one variable or fixed address")

        incumbent = record.get("incumbent")
        incumbent_times: Optional[Dict[int, int]] = None
        incumbent_addresses: Optional[Dict[str, int]] = None
        if incumbent is not None:
            if not isinstance(incumbent, dict) or "bundles" not in incumbent \
                    or "scratch" not in incumbent:
                raise DomainError("a malformed incumbent is not a legal domain input")
            try:
                machine.check_compilation(program, incumbent)
            except (machine.CompileError, machine.ProgramError) as exc:
                raise DomainError(f"the incumbent is not a legal compilation: {exc}") from exc
            incumbent_times = issue_cycles_of(program, incumbent["bundles"])
            incumbent_addresses = dict(incumbent["scratch"])
            for op_id, fixed in fixed_times.items():
                if incumbent_times[op_id] != fixed:
                    raise DomainError(
                        f"the incumbent contradicts the fixed time of operation {op_id}"
                    )
            for name, fixed in fixed_addresses.items():
                if incumbent_addresses[name] != fixed:
                    raise DomainError(
                        f"the incumbent contradicts the fixed address of value {name!r}"
                    )

        target = record.get("target")
        if target is not None:
            if not isinstance(target, (list, tuple)) or len(target) != 2 \
                    or not all(_plain_int(value) and value >= 1 for value in target):
                raise DomainError("a target must be a pair of positive integers")
            target = (int(target[0]), int(target[1]))

        return Domain(
            identifier=str(record["id"]),
            family=str(record.get("family", "unspecified")),
            program=program,
            facts=facts,
            selected_operations=selected_ops,
            selected_values=tuple(sorted(address_domains)),
            time_domains=time_domains,
            address_domains=address_domains,
            fixed_times=fixed_times,
            fixed_addresses=fixed_addresses,
            incumbent=incumbent,
            incumbent_times=incumbent_times,
            incumbent_addresses=incumbent_addresses,
            target=target,
            record=record,
        )

    # -- derived views -----------------------------------------------------

    @property
    def address_order(self) -> Tuple[str, ...]:
        """Selected address fields in producer-ID order: the offset order."""

        return tuple(sorted(self.address_domains, key=lambda name: self.facts.producers[name]))

    def cartesian_size(self) -> int:
        size = 1
        for values in self.time_domains.values():
            size *= len(values)
        for values in self.address_domains.values():
            size *= len(values)
        return size

    def digest(self) -> str:
        """The canonical digest of the declared domain, program included."""

        return object_digest(
            {
                "id": self.identifier,
                "family": self.family,
                "program": self.program,
                "selected_operations": list(self.selected_operations),
                "time_domains": {str(k): list(v) for k, v in sorted(self.time_domains.items())},
                "address_domains": {k: list(v) for k, v in sorted(self.address_domains.items())},
                "fixed_times": {str(k): v for k, v in sorted(self.fixed_times.items())},
                "fixed_addresses": dict(sorted(self.fixed_addresses.items())),
                "incumbent": self.incumbent,
                "target": list(self.target) if self.target else None,
            }
        )

    def ordered_domain(self, key: Tuple[str, object]) -> Tuple[int, ...]:
        """The declared domain of one decision, incumbent choice first.

        Contract section 4: "Both order incumbent choice first if present, then
        remaining choices numerically."
        """

        kind, which = key
        if kind == "time":
            values = self.time_domains[which]
            preferred = self.incumbent_times.get(which) if self.incumbent_times else None
        else:
            values = self.address_domains[which]
            preferred = (
                self.incumbent_addresses.get(which) if self.incumbent_addresses else None
            )
        return _incumbent_first(values, preferred)

    def decision_keys(self) -> Tuple[Tuple[str, object], ...]:
        """Every decision, in **offset** order: times by op ID, then addresses."""

        return tuple(("time", op_id) for op_id in self.selected_operations) + tuple(
            ("address", name) for name in self.address_order
        )


def _key_to_op(key: object, count: int) -> int:
    if _plain_int(key):
        op_id = key
    elif isinstance(key, str):
        try:
            op_id = int(key)
        except ValueError as exc:
            raise DomainError(f"operation key {key!r} is not an integer") from exc
    else:
        raise DomainError(f"operation key {key!r} is not an integer")
    if not 0 <= op_id < count:
        raise DomainError(f"operation key {key!r} is out of range")
    return op_id


def _check_address(name: str, value: int, width: int) -> None:
    if value < 0:
        raise DomainError(f"value {name!r}: negative address {value}")
    if width == machine.VLEN and value % machine.VLEN != 0:
        raise DomainError(f"vector {name!r}: address {value} is not aligned")
    if value + width > machine.SCRATCH_WORDS:
        raise DomainError(
            f"value {name!r}: address {value} ends past {machine.SCRATCH_WORDS}"
        )


def _incumbent_first(values: Sequence[int], preferred: Optional[int]) -> Tuple[int, ...]:
    ordered = sorted(values)
    if preferred is not None and preferred in ordered:
        return (preferred,) + tuple(value for value in ordered if value != preferred)
    return tuple(ordered)


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldSpec:
    """One field of the fixed layout.

    A width of zero is legal and occupies no bits: contract section 4, "Zero-width
    rank constants occupy no bits." No ``schema_index.Field`` is constructed for
    it, because that owner forbids a zero width.
    """

    key: Tuple[str, object]
    offset: int
    width: int

    def read(self, index: int) -> int:
        if self.width == 0:
            return 0
        return (index >> self.offset) & ((1 << self.width) - 1)

    def write(self, value: int) -> int:
        if self.width == 0:
            if value != 0:
                raise DomainError(f"{self.key}: a zero-width field only admits 0")
            return 0
        if not 0 <= value < (1 << self.width):
            raise DomainError(f"{self.key}: field value {value} does not fit {self.width} bits")
        return value << self.offset


@dataclass(frozen=True)
class Layout:
    """The fixed field layout of one domain under one codec.

    The layout is fixed for the entire ``Domain``: all selected time fields in
    operation-ID order, then all selected address fields in producer-ID order,
    LSB-first. Each field owns its offset independently of the traversal order
    used when decoding, which depends on the decoded schedule. Contract section
    4: "Never pack fields in this schedule-dependent traversal order."
    """

    codec: str
    width: int
    fields: Tuple[FieldSpec, ...]
    by_key: Dict[Tuple[str, object], FieldSpec]

    def field(self, key: Tuple[str, object]) -> FieldSpec:
        return self.by_key[key]


def _rank_width(size: int) -> int:
    """Bits reserved for a rank into a declared domain of ``size`` members."""

    if size < 1:
        raise DomainError("a rank field requires a nonempty declared domain")
    return (size - 1).bit_length()


def layout(domain: Domain, codec: str) -> Layout:
    """The fixed layout of ``domain`` under ``codec``."""

    if codec not in CODECS:
        raise DomainError(f"unknown codec {codec!r}")
    fields: List[FieldSpec] = []
    offset = 0
    for key in domain.decision_keys():
        kind, which = key
        if codec in ("static_rank", "structural_rank"):
            width = _rank_width(len(domain.ordered_domain(key)))
        elif kind == "time":
            # The canonical time width of the whole program, not of this domain.
            width = dc.time_width(domain.facts.horizon)
        elif codec == "vector_block" and domain.facts.width[which] == machine.VLEN:
            width = VECTOR_BLOCK_WIDTH
        else:
            width = dc.ADDRESS_WIDTH
        fields.append(FieldSpec(key=key, offset=offset, width=width))
        offset += width
    return Layout(
        codec=codec,
        width=offset,
        fields=tuple(fields),
        by_key={spec.key: spec for spec in fields},
    )


# --------------------------------------------------------------------------
# Transition state and option construction
# --------------------------------------------------------------------------


class State:
    """The prefix state of one decode.

    It carries the fixed decisions, the choices made so far, and nothing else.
    No oracle lookup and no objective enters option construction: contract
    section 4, "Codec legality and quality are separate predicates."
    """

    __slots__ = ("domain", "times", "addresses", "lifetimes", "counters")

    def __init__(self, domain: Domain) -> None:
        self.domain = domain
        self.times: Dict[int, int] = dict(domain.fixed_times)
        self.addresses: Dict[str, int] = dict(domain.fixed_addresses)
        self.lifetimes: Optional[Dict[str, Tuple[int, int]]] = None
        self.counters: Dict[str, int] = {
            "option_constructions": 0,
            "options_considered": 0,
            "legality_checks": 0,
        }

    def copy(self) -> "State":
        """A branch of the same traversal.

        The choices are copied; the counters are **shared on purpose**. A
        depth-first search branches thousands of times, and per-branch counters
        would report the cost of one root-to-leaf path instead of the cost of
        the whole traversal. Work done anywhere in the tree is charged once.
        """

        clone = State.__new__(State)
        clone.domain = self.domain
        clone.times = dict(self.times)
        clone.addresses = dict(self.addresses)
        clone.lifetimes = self.lifetimes
        clone.counters = self.counters
        return clone

    # -- scheduling --------------------------------------------------------

    def schedule_conflict(self) -> Optional[str]:
        """A contradiction among the decisions already in place, if any.

        Called once at initialisation so that a fixed/fixed contradiction is a
        ``DEAD_END`` before any field is read, as the contract requires.
        """

        facts = self.domain.facts
        for op_id, cycle in sorted(self.times.items()):
            for predecessor, lag in facts.predecessors[op_id].items():
                if predecessor in self.times and cycle < self.times[predecessor] + lag:
                    return (
                        f"operation {op_id} issues at {cycle}, before operation "
                        f"{predecessor} is ready at {self.times[predecessor] + lag}"
                    )
        usage: Dict[Tuple[str, int], int] = {}
        for op_id, cycle in self.times.items():
            key = (facts.engine[op_id], cycle)
            usage[key] = usage.get(key, 0) + 1
            if usage[key] > machine.ENGINE_LIMITS[key[0]]:
                return f"cycle {cycle} exceeds the {key[0]} issue limit"
        return None

    def time_options(self, op_id: int) -> Tuple[int, ...]:
        """Every declared time for ``op_id`` compatible with what is fixed.

        Predecessors always have smaller identifiers in a straight-line SSA
        program, so every predecessor is fixed or already assigned by the time
        this runs. Successors may have larger identifiers, and an *external*
        successor -- one whose time is fixed -- constrains this choice now.
        Constraints against later selected operations stay obligations for
        those later decisions, which is what keeps the codec complete over F_d.
        """

        facts = self.domain.facts
        declared = self.domain.ordered_domain(("time", op_id))
        self.counters["option_constructions"] += 1
        usage: Dict[Tuple[str, int], int] = {}
        for other, cycle in self.times.items():
            key = (facts.engine[other], cycle)
            usage[key] = usage.get(key, 0) + 1

        legal: List[int] = []
        engine = facts.engine[op_id]
        limit = machine.ENGINE_LIMITS[engine]
        for candidate in declared:
            self.counters["options_considered"] += 1
            self.counters["legality_checks"] += 1
            ok = True
            for predecessor, lag in facts.predecessors[op_id].items():
                if predecessor in self.times and candidate < self.times[predecessor] + lag:
                    ok = False
                    break
            if ok:
                for successor, lag in facts.successors[op_id]:
                    if successor in self.times and candidate + lag > self.times[successor]:
                        ok = False
                        break
            if ok and usage.get((engine, candidate), 0) >= limit:
                ok = False
            if ok:
                legal.append(candidate)
        return tuple(legal)

    # -- allocation --------------------------------------------------------

    def recompute_lifetimes(self) -> None:
        """Complete lifetimes once every issue time is known.

        The lifetime of a *fixed* value can change here, because a selected
        consumer may have moved. Contract section 4 and plan section 5.1 both
        require that; the fixed/fixed overlap check below is what catches it.
        """

        self.lifetimes = dc.lifetimes(self.domain.facts, self.times)

    def fixed_address_conflict(self) -> Optional[str]:
        facts = self.domain.facts
        fixed = sorted(self.domain.fixed_addresses)
        for i, first in enumerate(fixed):
            for second in fixed[i + 1:]:
                self.counters["legality_checks"] += 1
                if self._collides(first, self.addresses[first], second):
                    return (
                        f"fixed values {first!r} and {second!r} share scratch while "
                        f"both are live, after the selected reads moved"
                    )
        return None

    def _collides(self, name: str, base: int, other: str) -> bool:
        facts = self.domain.facts
        other_base = self.addresses[other]
        width = facts.width[name]
        other_width = facts.width[other]
        if not (base < other_base + other_width and other_base < base + width):
            return False
        start, end = self.lifetimes[name]
        other_start, other_end = self.lifetimes[other]
        return start <= other_end and other_start <= end

    def allocation_order(self) -> Tuple[str, ...]:
        """Vectors first, then scalars, by ``(write_cycle, producer_id)``.

        This traversal order is schedule-dependent and matches the accepted
        bootstrap's convention. It never changes a field's offset.
        """

        facts = self.domain.facts
        selected = list(self.domain.address_domains)
        vectors = [name for name in selected if facts.width[name] == machine.VLEN]
        scalars = [name for name in selected if facts.width[name] != machine.VLEN]

        def ordering(name: str) -> Tuple[int, int]:
            return (self.lifetimes[name][0], facts.producers[name])

        return tuple(sorted(vectors, key=ordering) + sorted(scalars, key=ordering))

    def address_options(self, name: str) -> Tuple[int, ...]:
        """Every declared address for ``name`` free of fixed and placed blocks.

        Lifetimes are the full inclusive intervals, so an equal last-read and
        new-write conflict and an adjacent non-overlap does not.
        """

        declared = self.domain.ordered_domain(("address", name))
        self.counters["option_constructions"] += 1
        placed = sorted(self.addresses)
        legal: List[int] = []
        for candidate in declared:
            self.counters["options_considered"] += 1
            ok = True
            for other in placed:
                self.counters["legality_checks"] += 1
                if self._collides(name, candidate, other):
                    ok = False
                    break
            if ok:
                legal.append(candidate)
        return tuple(legal)


def options(domain: Domain, prefix: State, decision: Tuple[str, object]) -> Tuple[int, ...]:
    """The deterministic ordered option list ``O(s)`` at one decision.

    Public because the search, the tests and the proofs all need exactly this
    list, and a second construction of it would be a second owner of the codec's
    transition relation.
    """

    if prefix.domain is not domain:
        raise DomainError("the prefix state belongs to a different domain")
    kind, which = decision
    if kind == "time":
        return prefix.time_options(which)
    if kind == "address":
        if prefix.lifetimes is None:
            raise DomainError("address options require a completed schedule")
        return prefix.address_options(which)
    raise DomainError(f"unknown decision kind {kind!r}")


# --------------------------------------------------------------------------
# Decode
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class DecodeResult:
    """The outcome of one decode.

    Only ``COMPLETE`` carries a compilation, ``C``/``S``/``J`` and a canonical
    index. Every outcome carries its consumed decisions, counters, reason and a
    trace reference.
    """

    status: str
    codec: str
    domain_id: str
    index: int
    bits: int
    reason: str
    decisions: Tuple[dict, ...]
    counters: Dict[str, int]
    trace_reference: str
    compilation: Optional[dict] = None
    times: Optional[Dict[int, int]] = None
    addresses: Optional[Dict[str, int]] = None
    cycles: Optional[int] = None
    scratch: Optional[int] = None
    product: Optional[int] = None
    canonical_index: Optional[int] = None
    identity: Optional[str] = None

    def to_row(self) -> dict:
        """The decoder row required by contract section 7."""

        return {
            "index": str(self.index),
            "bits": self.bits,
            "status": self.status,
            "reason": self.reason,
            "codec": self.codec,
            "domain_id": self.domain_id,
            "decisions": len(self.decisions),
            "option_counts": [record["option_count"] for record in self.decisions],
            "counters": dict(self.counters),
            "trace_reference": self.trace_reference,
            "compilation_sha256": self.identity,
            "cycles": self.cycles,
            "scratch": self.scratch,
            "product": self.product,
            "canonical_index": None if self.canonical_index is None else str(self.canonical_index),
        }


def _resolve(
    codec: str,
    key: Tuple[str, object],
    raw: int,
    declared: Tuple[int, ...],
    legal: Tuple[int, ...],
    is_vector: bool,
):
    """Map one field value to a physical choice, with the fixed precedence.

    Returns ``(value, None, '')`` on success, or ``(None, status, reason)``.
    Empty options are checked first, then rank validity: this is what makes the
    otherwise overlapping ``DEAD_END`` and ``INVALID_CODE`` cases disjoint.
    """

    if not legal:
        return None, DEAD_END, f"{key}: no legal option remains"

    if codec == "structural_rank":
        if raw >= len(legal):
            return None, INVALID_CODE, f"{key}: rank {raw} is past {len(legal)} options"
        return legal[raw], None, ""

    if codec == "static_rank":
        if raw >= len(declared):
            return None, INVALID_CODE, (
                f"{key}: rank {raw} is past {len(declared)} declared choices"
            )
        value = declared[raw]
    else:
        value = raw * machine.VLEN if (codec == "vector_block" and is_vector) else raw
        if value not in declared:
            return None, INVALID_CODE, f"{key}: {value} is outside the declared domain"

    if value not in legal:
        return None, DEAD_END, f"{key}: {value} is declared but not legal in this state"
    return value, None, ""


def _trace_reference(decisions: Sequence[dict]) -> str:
    return object_digest(list(decisions))


def _result(status, domain, codec, index, plan, decisions, state, reason, **extra) -> DecodeResult:
    counters = dict(state.counters)
    counters["decisions_consumed"] = len(decisions)
    counters["decisions_total"] = len(plan.fields)
    return DecodeResult(
        status=status,
        codec=codec,
        domain_id=domain.identifier,
        index=index,
        bits=plan.width,
        reason=reason,
        decisions=tuple(decisions),
        counters=counters,
        trace_reference=_trace_reference(decisions),
        **extra,
    )


def decode(
    domain: Domain,
    index: int,
    codec: str,
    budget: Optional[si.Budget] = None,
    meter: Optional[si.Meter] = None,
) -> DecodeResult:
    """Decode one code into a compilation, or into an explicit failure code.

    ``budget``/``meter`` are the ``schema_index`` owner's limits. Exhaustion is
    ``INTERRUPTED``, which is an execution status and never a mathematical
    output of the codec.
    """

    plan = layout(domain, codec)
    if not _plain_int(index):
        raise DomainError(f"an index must be a plain integer, not {index!r}")
    if not 0 <= index < (1 << plan.width):
        raise DomainError(
            f"index {index} is outside the {plan.width}-bit code universe"
        )

    if meter is None and budget is not None:
        meter = budget.start()

    facts = domain.facts
    state = State(domain)
    decisions: List[dict] = []

    conflict = state.schedule_conflict()
    if conflict is not None:
        return _result(DEAD_END, domain, codec, index, plan, decisions, state,
                       f"fixed decisions contradict each other: {conflict}")

    try:
        for op_id in domain.selected_operations:
            if meter is not None:
                meter.record()
            key = ("time", op_id)
            spec = plan.field(key)
            declared = domain.ordered_domain(key)
            legal = state.time_options(op_id)
            if meter is not None:
                meter.visit(max(1, len(declared)))
            raw = spec.read(index)
            value, status, reason = _resolve(codec, key, raw, declared, legal, False)
            decisions.append(
                {
                    "kind": "time",
                    "key": op_id,
                    "offset": spec.offset,
                    "width": spec.width,
                    "field_value": raw,
                    "option_count": len(legal),
                    "declared_count": len(declared),
                    "chosen": value,
                }
            )
            if status is not None:
                return _result(status, domain, codec, index, plan, decisions, state, reason)
            state.times[op_id] = value

        state.recompute_lifetimes()
        conflict = state.fixed_address_conflict()
        if conflict is not None:
            return _result(DEAD_END, domain, codec, index, plan, decisions, state, conflict)

        for name in state.allocation_order():
            if meter is not None:
                meter.record()
            key = ("address", name)
            spec = plan.field(key)
            declared = domain.ordered_domain(key)
            legal = state.address_options(name)
            if meter is not None:
                meter.visit(max(1, len(declared)))
            raw = spec.read(index)
            is_vector = facts.width[name] == machine.VLEN
            value, status, reason = _resolve(codec, key, raw, declared, legal, is_vector)
            decisions.append(
                {
                    "kind": "address",
                    "key": name,
                    "offset": spec.offset,
                    "width": spec.width,
                    "field_value": raw,
                    "option_count": len(legal),
                    "declared_count": len(declared),
                    "chosen": value,
                }
            )
            if status is not None:
                return _result(status, domain, codec, index, plan, decisions, state, reason)
            state.addresses[name] = value
    except si.BudgetExhausted as exc:
        return _result(INTERRUPTED, domain, codec, index, plan, decisions, state, exc.reason)

    cycles, scratch, product = objective(facts, state.times, state.addresses)

    # The target is an explicit predicate of the domain, applied after the
    # object exists. Missing it is a DEAD_END, not a validator discrepancy.
    if domain.target is not None:
        target_cycles, target_scratch = domain.target
        if cycles > target_cycles or scratch > target_scratch:
            return _result(
                DEAD_END, domain, codec, index, plan, decisions, state,
                f"target ({target_cycles}, {target_scratch}) missed by "
                f"({cycles}, {scratch})",
            )

    compiled = dc.compilation(facts, state.times, state.addresses)
    try:
        dc.check_feasible(facts, state.times, state.addresses)
        machine.check_compilation(domain.program, compiled)
    except (dc.ContractError, machine.CompileError, machine.ProgramError) as exc:
        raise CodecDefect(
            f"code {index} decoded completely but was rejected: {exc}",
            {
                "domain_id": domain.identifier,
                "domain_sha256": domain.digest(),
                "codec": codec,
                "index": str(index),
                "bits": plan.width,
                "times": {str(k): v for k, v in sorted(state.times.items())},
                "addresses": dict(sorted(state.addresses.items())),
                "decisions": list(decisions),
                "validator_message": str(exc),
            },
        ) from exc

    normalised = normalise_compilation(facts, compiled)

    # Reassemble the code from the field values actually consumed. This is a
    # layout check, not the injectivity proof: it fails if two fields share an
    # offset, if a width is wrong, or if any bit of the index was never read.
    # The real obligation, ``encode(decode(z)) == z``, recomputes the option
    # lists independently and is discharged in P1 and in the unit tests; doing
    # it inside every decode would double the cost of every timed search.
    canonical = 0
    for record in decisions:
        canonical |= record["field_value"] << record["offset"]
    if canonical != index:
        raise CodecDefect(
            f"code {index} reassembles as {canonical}: the layout loses bits",
            {
                "domain_id": domain.identifier,
                "codec": codec,
                "index": str(index),
                "canonical_index": str(canonical),
                "decisions": list(decisions),
            },
        )

    return _result(
        COMPLETE, domain, codec, index, plan, decisions, state, "complete",
        compilation=normalised,
        times=dict(state.times),
        addresses=dict(state.addresses),
        cycles=cycles,
        scratch=scratch,
        product=product,
        canonical_index=canonical,
        identity=object_digest(normalised),
    )


# --------------------------------------------------------------------------
# Encode
# --------------------------------------------------------------------------


def encode(domain: Domain, compiled: dict, codec: str) -> int:
    """The inverse map on ``F_d``.

    ``compiled`` is normalised first and every comparison is made against that
    normalised object. A compilation outside ``F_d`` is rejected: duplicate or
    missing operations are errors, never normalisation opportunities.
    """

    plan = layout(domain, codec)
    facts = domain.facts
    normalised = normalise_compilation(facts, compiled)
    times = issue_cycles_of(domain.program, normalised["bundles"])
    addresses = dict(normalised["scratch"])

    for op_id, fixed in domain.fixed_times.items():
        if times[op_id] != fixed:
            raise DomainError(f"operation {op_id} contradicts its fixed time")
    for name, fixed in domain.fixed_addresses.items():
        if addresses[name] != fixed:
            raise DomainError(f"value {name!r} contradicts its fixed address")

    state = State(domain)
    if state.schedule_conflict() is not None:
        raise DomainError("the fixed decisions of this domain are contradictory")

    index = 0
    for op_id in domain.selected_operations:
        key = ("time", op_id)
        value = times[op_id]
        declared = domain.ordered_domain(key)
        legal = state.time_options(op_id)
        index |= plan.field(key).write(_field_value(codec, key, value, declared, legal, False))
        state.times[op_id] = value

    state.recompute_lifetimes()
    if state.fixed_address_conflict() is not None:
        raise DomainError("this schedule puts two fixed allocations in conflict")

    for name in state.allocation_order():
        key = ("address", name)
        value = addresses[name]
        declared = domain.ordered_domain(key)
        legal = state.address_options(name)
        is_vector = facts.width[name] == machine.VLEN
        index |= plan.field(key).write(
            _field_value(codec, key, value, declared, legal, is_vector)
        )
        state.addresses[name] = value

    if domain.target is not None:
        cycles, scratch, _ = objective(facts, state.times, state.addresses)
        if cycles > domain.target[0] or scratch > domain.target[1]:
            raise DomainError("this compilation misses the domain's target")
    return index


def _field_value(
    codec: str,
    key: Tuple[str, object],
    value: int,
    declared: Tuple[int, ...],
    legal: Tuple[int, ...],
    is_vector: bool,
) -> int:
    if value not in legal:
        raise DomainError(f"{key}: {value} is not a legal choice, so this object is outside F_d")
    if codec == "structural_rank":
        return legal.index(value)
    if codec == "static_rank":
        return declared.index(value)
    if codec == "vector_block" and is_vector:
        if value % machine.VLEN != 0:
            raise DomainError(f"{key}: {value} is not an aligned vector block")
        return value // machine.VLEN
    return value
