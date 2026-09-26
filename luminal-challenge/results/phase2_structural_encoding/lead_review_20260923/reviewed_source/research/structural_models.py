"""Exact covers of index sets, their serialisation, and proposal generalisation.

Three separate things live here, and the plan is emphatic that they are separate
(section 7): building an exact cover of a *known* set measures representability;
proposing *unseen* indices is a different operation that a cover alone cannot
perform. "An exact cover of a finite observed set generates only that set."

Cube algebra belongs to ``schema_index``; this module never defines a second
one. The merge heuristic, the byte format and the four proposal policies are
what it owns.

The serialised length is the one declared algorithmic description length of plan
section 7: the length in bits of an actual deterministic lossless serialisation.
It is not an entropy, and cube count is a structural diagnostic reported with its
denominator, never a second complexity definition.
"""

from __future__ import annotations

from dataclasses import dataclass, field as _dataclass_field
import random
import time
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple

import schema_index as si

from research import structural_encoding as se


__all__ = [
    "MODEL_ARMS",
    "CoverResult",
    "SerialisationError",
    "exact_cover",
    "serialise_cover",
    "deserialise_cover",
    "cover_members",
    "expand_cubes",
    "proposals",
]


MODEL_ARMS = ("empirical_cover", "model_expand", "one_bit", "uniform_bits")


class SerialisationError(ValueError):
    """The byte stream is not a well-formed cover."""


@dataclass
class CoverResult:
    """One cover, its exactness evidence and what it cost to build."""

    bits: int
    cubes: Tuple[si.Cube, ...]
    status: str
    reason: str
    merges: int
    candidates_examined: int
    seconds: float
    exact: Optional[bool] = None
    disjoint: Optional[bool] = None

    def as_pairs(self) -> List[Tuple[int, int]]:
        return sorted((cube.anchor, cube.free_mask) for cube in self.cubes)

    def to_row(self) -> dict:
        return {
            "bits": self.bits,
            "cube_count": len(self.cubes),
            "status": self.status,
            "reason": self.reason,
            "merges": self.merges,
            "candidates_examined": self.candidates_examined,
            "seconds": self.seconds,
            "exact": self.exact,
            "disjoint": self.disjoint,
            "pairs": [list(pair) for pair in self.as_pairs()],
        }


# --------------------------------------------------------------------------
# Exact cover
# --------------------------------------------------------------------------


def exact_cover(
    indices: Iterable[int],
    bits: int,
    max_cubes: int,
    seconds: float,
) -> CoverResult:
    """The frozen cover heuristic of plan section 7.

    Start with minterms; repeatedly merge equal-mask cubes differing in one
    fixed coordinate, choosing the smallest eligible ``(coordinate, anchor,
    free_mask)``, until no merge remains. Two disjoint cubes of equal mask that
    differ in exactly one fixed coordinate have a union that is itself a cube,
    so the invariant "the cover is exactly the set, and its cubes are pairwise
    disjoint" survives every step. That makes this a reproducible heuristic,
    not a minimum-cover theorem.

    An interrupted construction is ``INCONCLUSIVE``. It is never reported as
    exact evidence, and never as a compression success.
    """

    started = time.perf_counter()
    members = sorted(set(indices))
    limit = (1 << bits) - 1 if bits else 0
    for index in members:
        if index < 0 or index > limit:
            raise ValueError(f"index {index} is outside the {bits}-bit universe")
    if len(members) > max_cubes:
        return CoverResult(
            bits=bits,
            cubes=(),
            status="INCONCLUSIVE",
            reason=f"{len(members)} minterms exceed the cube budget {max_cubes}",
            merges=0,
            candidates_examined=0,
            seconds=time.perf_counter() - started,
        )

    # anchors, grouped by free mask. Membership tests are what the scan costs.
    groups: Dict[int, Set[int]] = {0: set(members)}
    merges = 0
    examined = 0
    status = "COMPLETE"
    reason = "no eligible merge remains"

    while True:
        if time.perf_counter() - started > seconds:
            status = "INCONCLUSIVE"
            reason = "cover construction exhausted its time budget"
            break
        # The smallest eligible ``(coordinate, anchor, free_mask)``, in that
        # order of precedence: the coordinate decides first, then the anchor of
        # the merged cube, then its free mask.
        best: Optional[Tuple[int, int, int]] = None
        for coordinate in range(bits):
            bit = 1 << coordinate
            for mask in sorted(groups):
                if mask & bit:
                    continue
                anchors = groups[mask]
                for anchor in sorted(anchors):
                    examined += 1
                    if anchor & bit:
                        continue
                    if (anchor | bit) not in anchors:
                        continue
                    candidate = (coordinate, anchor, mask | bit)
                    if best is None or candidate[1:] < best[1:]:
                        best = candidate
                    break
            if best is not None:
                break
        if best is None:
            break
        coordinate, anchor, new_mask = best
        bit = 1 << coordinate
        old_mask = new_mask ^ bit
        groups[old_mask].discard(anchor)
        groups[old_mask].discard(anchor | bit)
        if not groups[old_mask]:
            del groups[old_mask]
        groups.setdefault(new_mask, set()).add(anchor)
        merges += 1
        total = sum(len(anchors) for anchors in groups.values())
        if total > max_cubes:
            status = "INCONCLUSIVE"
            reason = f"cover grew past {max_cubes} cubes"
            break

    # Sorted by ``(anchor, free_mask)``: the same order the byte format uses, so
    # a cover and its round trip are equal as sequences and not merely as sets.
    cubes = tuple(
        si.Cube(bits, anchor, mask)
        for anchor, mask in sorted(
            (anchor, mask) for mask, anchors in groups.items() for anchor in anchors
        )
    )
    result = CoverResult(
        bits=bits,
        cubes=cubes,
        status=status,
        reason=reason,
        merges=merges,
        candidates_examined=examined,
        seconds=time.perf_counter() - started,
    )
    if status == "COMPLETE":
        # Exactness and disjointness are verified by expansion. These universes
        # are small by construction; on a larger one this check would itself
        # need a budget and would then be inconclusive, not assumed.
        expanded: List[int] = []
        for cube in cubes:
            expanded.extend(cube.members())
        result.exact = sorted(expanded) == members and len(set(expanded)) == len(expanded)
        result.disjoint = len(set(expanded)) == len(expanded)
        if not result.exact:
            result.status = "FAIL"
            result.reason = "the constructed cover is not exactly the requested set"
    return result


def cover_members(cubes: Sequence[si.Cube]) -> List[int]:
    """Every index denoted by a cover, in ascending order, deduplicated."""

    members: Set[int] = set()
    for cube in cubes:
        members.update(cube.members())
    return sorted(members)


# --------------------------------------------------------------------------
# Serialisation
# --------------------------------------------------------------------------


def _put_varint(value: int) -> bytes:
    """Shortest unsigned base-128 varint, little-endian groups."""

    if value < 0:
        raise SerialisationError("a varint encodes a non-negative integer")
    out = bytearray()
    while True:
        chunk = value & 0x7F
        value >>= 7
        if value:
            out.append(chunk | 0x80)
        else:
            out.append(chunk)
            return bytes(out)


def _take_varint(data: bytes, position: int) -> Tuple[int, int]:
    value = 0
    shift = 0
    start = position
    while True:
        if position >= len(data):
            raise SerialisationError("the stream ended inside a varint")
        byte = data[position]
        position += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            break
        shift += 7
        if position - start > 10:
            raise SerialisationError("varint is implausibly long")
    # An overlong encoding is a different byte string for the same number, so
    # accepting it would make the format lossy in the direction that matters:
    # two streams would deserialise to one object.
    if _put_varint(value) != data[start:position]:
        raise SerialisationError("overlong varint")
    return value, position


def serialise_cover(cubes: Sequence[si.Cube], bits: int) -> bytes:
    """The declared lossless format of plan section 7.

    Unsigned base-128 varints for ``B`` and the cube count, then sorted unique
    ``(anchor, free_mask)`` pairs as two little-endian ``ceil(B/8)``-byte
    integers each, zero padded.
    """

    pairs = sorted((cube.anchor, cube.free_mask) for cube in cubes)
    if len(set(pairs)) != len(pairs):
        raise SerialisationError("a cover may not repeat a cube")
    for cube in cubes:
        if cube.n != bits:
            raise SerialisationError("every cube must have the declared width")
    width = (bits + 7) // 8
    out = bytearray()
    out += _put_varint(bits)
    out += _put_varint(len(pairs))
    for anchor, free_mask in pairs:
        out += anchor.to_bytes(width, "little")
        out += free_mask.to_bytes(width, "little")
    return bytes(out)


def deserialise_cover(data: bytes) -> Tuple[Tuple[si.Cube, ...], int]:
    """The exact inverse. Anything else is an error, never a repair."""

    if not isinstance(data, (bytes, bytearray)):
        raise SerialisationError("a cover is deserialised from bytes")
    data = bytes(data)
    bits, position = _take_varint(data, 0)
    count, position = _take_varint(data, position)
    width = (bits + 7) // 8
    limit = (1 << bits) - 1 if bits else 0
    pairs: List[Tuple[int, int]] = []
    for _ in range(count):
        if position + 2 * width > len(data):
            raise SerialisationError("the stream ended inside a cube")
        anchor = int.from_bytes(data[position:position + width], "little")
        position += width
        free_mask = int.from_bytes(data[position:position + width], "little")
        position += width
        if anchor > limit or free_mask > limit:
            raise SerialisationError("nonzero padding above the declared width")
        pairs.append((anchor, free_mask))
    if position != len(data):
        raise SerialisationError("extra bytes after the last cube")
    if pairs != sorted(pairs):
        raise SerialisationError("cubes must be stored in sorted order")
    if len(set(pairs)) != len(pairs):
        raise SerialisationError("a cover may not repeat a cube")
    return tuple(si.Cube(bits, anchor, free_mask) for anchor, free_mask in pairs), bits


# --------------------------------------------------------------------------
# Proposal generalisation
# --------------------------------------------------------------------------


def expand_cubes(cubes: Sequence[si.Cube], bits: int) -> Tuple[si.Cube, ...]:
    """Free exactly one fixed coordinate from each cube, deduplicated.

    Cubes are visited in ``(anchor, free_mask)`` order and coordinates in
    ascending order, which fixes the order in which proposals appear. This is
    the deterministic conditional proposal rule of plan section 7; a more
    elaborate learner needs a dated amendment before it may be evaluated.
    """

    produced: List[si.Cube] = []
    seen: Set[Tuple[int, int]] = set()
    for cube in sorted(cubes, key=lambda c: (c.anchor, c.free_mask)):
        for coordinate in range(bits):
            bit = 1 << coordinate
            if cube.free_mask & bit:
                continue
            anchor = cube.anchor & ~bit
            key = (anchor, cube.free_mask | bit)
            if key in seen:
                continue
            seen.add(key)
            produced.append(si.Cube(bits, anchor, cube.free_mask | bit))
    return tuple(produced)


def proposals(
    arm: str,
    bits: int,
    elite: Sequence[int],
    cover: Sequence[si.Cube],
    excluded: Set[int],
    search_seed: Optional[int],
) -> Iterator[Tuple[int, bool]]:
    """Lazily yield ``(index, is_duplicate)`` for one proposal arm.

    Nothing here materialises ``2**B``. ``excluded`` holds every index the arm
    is forbidden to re-ask -- the whole training split, and everything it has
    already paid for -- so a repeat is yielded as a duplicate and still counted
    rather than being silently skipped. The caller stops when its budget stops it.
    """

    if arm not in MODEL_ARMS:
        raise ValueError(f"unknown model arm {arm!r}")
    limit = 1 << bits

    if arm == "empirical_cover":
        # An exact cover of the observed elite denotes exactly that elite. This
        # arm exists to demonstrate that, and it reports exhaustion.
        for index in cover_members(cover):
            yield index, index in excluded
        return

    if arm == "model_expand":
        for index in cover_members(expand_cubes(cover, bits)):
            yield index, index in excluded
        return

    if arm == "one_bit":
        candidates: Set[int] = set()
        for index in elite:
            for coordinate in range(bits):
                candidates.add(index ^ (1 << coordinate))
        for index in sorted(candidates):
            yield index, index in excluded
        return

    if search_seed is None:
        raise ValueError("uniform_bits requires a search seed")
    rng = random.Random(search_seed)
    while True:
        # ``getrandbits(B)`` already lands in the code universe, so no modulo
        # mapping is applied: that would bias the draw and is exactly what the
        # codec forbids. Every draw is a paid attempt, including a repeat and
        # including one that will decode to an invalid code.
        index = rng.getrandbits(bits) if bits else 0
        yield index, index in excluded
