"""R4 / W1.1 — segmented gate-grammar codec for 1-D binary strings.

Implements §4 of `experiments/r4_segmented_grammar/PROTOCOL.md` (FROZEN
2026-08-25): the transmitted components of L_G(x), each carrying its own Kraft /
prefix-free check, plus the JOIN protocol.

AC-R4-1 governs this file: the join/Kraft test must be green **before any
length is quoted anywhere**. Accordingly `codelength()` refuses to return a
number unless `self_check()` passes. That is not decoration — an
un-Kraft-checked codelength is not a codelength, because any "compression" it
reports can be manufactured by letting two components share prefixes, and
Addendum A3 pins C2 ≥ 1.00 precisely so that a violation shows up as
sub-entropy output on iid fair bits.

Design commitments, each of which is checked rather than asserted:

* **Prefix-freeness is proven by decoding, not by construction.** Every code
  here has a decoder, and the tests round-trip it. A code that decodes
  unambiguously from a stream, at every position, with no length passed
  alongside, is prefix-free; that is a stronger statement than a Kraft sum,
  which is necessary but not sufficient.
* **Kraft sums are computed, not derived on paper.** `kraft_sum` measures the
  actual emitted lengths.
* **Nothing is free.** Cut positions, dictionary indices and the repetition
  pointer are all realised as emitted bits (§4.6).

The segmenter (§5) is W1.2 and is deliberately NOT in this module: AC-R4-1 has
to be green first.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field

__all__ = [
    "BitWriter", "BitReader", "elias_gamma", "elias_delta",
    "kraft_sum", "is_prefix_free", "Components", "GrammarCodec",
    "KraftViolation", "load_catalogue",
]


class KraftViolation(RuntimeError):
    """Raised when a component's code fails its Kraft / prefix-free check."""


# ---------------------------------------------------------------------------
# bit plumbing
# ---------------------------------------------------------------------------

class BitWriter:
    def __init__(self) -> None:
        self.bits: list[int] = []

    def write(self, bits) -> "BitWriter":
        self.bits.extend(int(b) & 1 for b in bits)
        return self

    def write_raw(self, value: int, width: int) -> "BitWriter":
        """Fixed-width field. Prefix-free only because the width is known to the
        decoder from what was already transmitted -- never used standalone."""
        if width < 0:
            raise ValueError("negative width")
        if width and not (0 <= value < (1 << width)):
            raise ValueError(f"{value} does not fit in {width} bits")
        for k in range(width - 1, -1, -1):
            self.bits.append((value >> k) & 1)
        return self

    def __len__(self) -> int:
        return len(self.bits)

    def tolist(self) -> list[int]:
        return list(self.bits)


class BitReader:
    def __init__(self, bits) -> None:
        self.bits = list(bits)
        self.pos = 0

    def read_bit(self) -> int:
        if self.pos >= len(self.bits):
            raise EOFError("bit stream exhausted")
        b = self.bits[self.pos]
        self.pos += 1
        return b

    def read_raw(self, width: int) -> int:
        v = 0
        for _ in range(width):
            v = (v << 1) | self.read_bit()
        return v

    def exhausted(self) -> bool:
        return self.pos >= len(self.bits)


# ---------------------------------------------------------------------------
# self-delimiting integer codes (§4.2, §4.3 "coded self-delimitingly")
# ---------------------------------------------------------------------------

def elias_gamma(n: int) -> list[int]:
    """Elias gamma for n >= 1. |gamma(n)| = 2*floor(log2 n) + 1."""
    if n < 1:
        raise ValueError("elias_gamma requires n >= 1")
    b = bin(n)[2:]
    return [0] * (len(b) - 1) + [int(c) for c in b]


def decode_gamma(r: BitReader) -> int:
    zeros = 0
    while r.read_bit() == 0:
        zeros += 1
    v = 1
    for _ in range(zeros):
        v = (v << 1) | r.read_bit()
    return v


def elias_delta(n: int) -> list[int]:
    """Elias delta for n >= 1: asymptotically shorter than gamma, still
    prefix-free. Used where the alphabet is unbounded (segment lengths)."""
    if n < 1:
        raise ValueError("elias_delta requires n >= 1")
    b = bin(n)[2:]
    return elias_gamma(len(b)) + [int(c) for c in b[1:]]


def decode_delta(r: BitReader) -> int:
    length = decode_gamma(r)
    v = 1
    for _ in range(length - 1):
        v = (v << 1) | r.read_bit()
    return v


# ---------------------------------------------------------------------------
# the checks that AC-R4-1 is about
# ---------------------------------------------------------------------------

def kraft_sum(codes) -> float:
    """Sum 2^-|c| over the emitted codewords. Necessary for prefix-freeness."""
    return sum(2.0 ** -len(c) for c in codes)


def is_prefix_free(codes) -> tuple[bool, tuple | None]:
    """Exhaustive pairwise prefix test. Returns (ok, offending_pair_or_None).

    Kraft <= 1 does NOT imply prefix-freeness, so this is checked separately
    rather than inferred from the sum.
    """
    seen: dict[tuple, int] = {}
    for i, c in enumerate(codes):
        seen[tuple(c)] = i
    for i, c in enumerate(codes):
        t = tuple(c)
        for k in range(1, len(t)):
            j = seen.get(t[:k])
            if j is not None and j != i:
                return False, (j, i)
    return True, None


# ---------------------------------------------------------------------------
# catalogue
# ---------------------------------------------------------------------------

def load_catalogue(path: str | None = None) -> dict:
    """The mirror-tested catalogue is the authority chain (SUCCESSOR_PLAN v0.2):
    W1.3/W1.4 generators must consume THIS file and nothing else."""
    if path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(os.path.dirname(here))
        path = os.path.join(root, "experiments", "r4_segmented_grammar",
                            "catalogue_from_gates.json")
    with open(path) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# the codelength components (§4.1 - §4.6)
# ---------------------------------------------------------------------------

@dataclass
class Components:
    """Per-component bit counts. Kept separate so each can be Kraft-checked and
    so the accounting is auditable rather than a single opaque total."""
    header: int = 0
    dictionary: int = 0
    occurrences: int = 0
    cuts: int = 0
    residuals: int = 0
    detail: dict = field(default_factory=dict)

    def total(self) -> int:
        return (self.header + self.dictionary + self.occurrences
                + self.cuts + self.residuals)

    def as_dict(self) -> dict:
        d = {"header": self.header, "dictionary": self.dictionary,
             "occurrences": self.occurrences, "cuts": self.cuts,
             "residuals": self.residuals, "total": self.total()}
        d.update(self.detail)
        return d


@dataclass
class Segment:
    """One segment of the parse. ``mech`` is a catalogue index, or None for an
    honest LUT fallback (§4.5). A fallback is NEVER a recovered mechanism."""
    start: int
    length: int
    mech: int | None
    residual_bits: list[int] = field(default_factory=list)

    @property
    def is_fallback(self) -> bool:
        return self.mech is None


class GrammarCodec:
    """Encoder/decoder for L_G(x) under the frozen grammar G.

    The decoder exists so that prefix-freeness can be PROVEN by round-trip
    rather than argued. `codelength` will not return a number until
    `self_check()` has passed (AC-R4-1).
    """

    def __init__(self, catalogue: dict | None = None, granularity: int = 8):
        self.catalogue = catalogue if catalogue is not None else load_catalogue()
        self.mechanisms = self.catalogue["mechanisms"]
        self.granularity = granularity
        self._checked = False
        self._check_report: dict = {}

    # -- components ---------------------------------------------------------

    def encode(self, n: int, segments: list[Segment]) -> tuple[list[int], Components]:
        """Emit the full message. Every field below is a real emitted bit."""
        c = Components()
        w = BitWriter()

        # 1. header: n, segment count S, catalogue id, granularity knob
        h = BitWriter()
        h.write(elias_delta(n))
        h.write(elias_delta(len(segments)))
        h.write(elias_delta(int(self.catalogue.get("n_mechanisms", len(self.mechanisms)))))
        h.write(elias_delta(self.granularity))
        c.header = len(h)
        w.write(h.tolist())

        # 2. mechanism dictionary: each DISTINCT mechanism once, in order of
        #    first occurrence; |D| coded self-delimitingly
        order: list[int] = []
        for s in segments:
            if s.mech is not None and s.mech not in order:
                order.append(s.mech)
        d = BitWriter()
        d.write(elias_delta(len(order) + 1))          # +1 so |D| = 0 is codable
        idx_w = self._index_width(len(self.mechanisms))
        for m in order:
            d.write_raw(m, idx_w)
        c.dictionary = len(d)
        w.write(d.tolist())

        # 3. occurrence list: dictionary index + length, ascending position.
        #    This IS the "~log2 #segments" repetition pointer of §4.6 -- it is
        #    charged here and nowhere assumed free.
        ptr_w = self._index_width(max(len(order), 1)) if order else 0
        o = BitWriter()
        for s in segments:
            o.write([0] if s.is_fallback else [1])
            if not s.is_fallback:
                o.write_raw(order.index(s.mech), ptr_w)
            o.write(elias_delta(s.length))
        c.occurrences = len(o)
        w.write(o.tolist())

        # 4. cut positions: k interior cuts, ceil(log2 n) bits each
        cut_w = max(1, math.ceil(math.log2(max(n, 2))))
        k = max(len(segments) - 1, 0)
        cu = BitWriter()
        cu.write(elias_delta(k + 1))
        for s in segments[1:]:
            cu.write_raw(s.start, cut_w)
        c.cuts = len(cu)
        w.write(cu.tolist())

        # 5. residuals: 0 for exact, else raw copy at 1 bit per symbol
        r = BitWriter()
        for s in segments:
            if s.is_fallback:
                if len(s.residual_bits) != s.length:
                    raise ValueError("fallback residual must cover the segment")
                r.write(s.residual_bits)
        c.residuals = len(r)
        w.write(r.tolist())

        c.detail = {
            "n_segments": len(segments),
            "dictionary_size": len(order),
            "n_fallback_segments": sum(1 for s in segments if s.is_fallback),
            "index_width_bits": idx_w,
            "pointer_width_bits": ptr_w,
            "cut_width_bits": cut_w,
        }
        return w.tolist(), c

    def decode(self, bits: list[int]) -> tuple[int, list[Segment]]:
        """Inverse of `encode`. Its existence is the prefix-free proof."""
        r = BitReader(bits)
        n = decode_delta(r)
        n_seg = decode_delta(r)
        # AUDIT03/R1.4: these two fields were read and DISCARDED, and idx_w was
        # taken from this decoder's own catalogue. The size was therefore
        # charged in every message and used in none, so a decoder holding a
        # DIFFERENT catalogue would silently mis-read every mechanism index
        # instead of refusing. The charge was right -- transmitting the size is
        # what makes the index width derivable, and it is why the fixed-width
        # index is legitimate -- but the implementation was not honouring it.
        # Now the transmitted value is used, and a mismatch refuses loudly.
        n_mech = decode_delta(r)              # catalogue size, as transmitted
        granularity = decode_delta(r)         # granularity knob
        if n_mech != len(self.mechanisms):
            raise ValueError(
                f"catalogue mismatch: message declares {n_mech} mechanisms, "
                f"this decoder holds {len(self.mechanisms)}")
        if granularity != self.granularity:
            raise ValueError(
                f"granularity mismatch: message declares {granularity}, "
                f"this decoder is configured for {self.granularity}")

        n_dict = decode_delta(r) - 1
        idx_w = self._index_width(n_mech)
        order = [r.read_raw(idx_w) for _ in range(n_dict)]

        ptr_w = self._index_width(max(len(order), 1)) if order else 0
        flags, mechs, lengths = [], [], []
        for _ in range(n_seg):
            is_mech = r.read_bit()
            flags.append(is_mech)
            mechs.append(order[r.read_raw(ptr_w)] if is_mech else None)
            lengths.append(decode_delta(r))

        cut_w = max(1, math.ceil(math.log2(max(n, 2))))
        k = decode_delta(r) - 1
        starts = [0] + [r.read_raw(cut_w) for _ in range(k)]

        segments = []
        for i in range(n_seg):
            resid = ([r.read_bit() for _ in range(lengths[i])]
                     if mechs[i] is None else [])
            segments.append(Segment(start=starts[i], length=lengths[i],
                                    mech=mechs[i], residual_bits=resid))
        return n, segments

    @staticmethod
    def _index_width(size: int) -> int:
        return math.ceil(math.log2(max(size, 2)))

    # -- AC-R4-1 ------------------------------------------------------------

    def self_check(self, max_int: int = 4096) -> dict:
        """The gate. Every component's code is Kraft-checked AND prefix-tested,
        and the JOIN is verified by decoding composed messages back.

        Returns a report; raises KraftViolation on failure.
        """
        report: dict = {}

        for name, enc in (("elias_gamma", elias_gamma), ("elias_delta", elias_delta)):
            codes = [enc(i) for i in range(1, max_int + 1)]
            ks = kraft_sum(codes)
            pf, offender = is_prefix_free(codes)
            # round-trip from a concatenated stream, with NO lengths alongside
            dec = decode_gamma if name == "elias_gamma" else decode_delta
            w = BitWriter()
            for c in codes:
                w.write(c)
            rd = BitReader(w.tolist())
            rt = all(dec(rd) == i for i in range(1, max_int + 1)) and rd.exhausted()
            report[name] = {"kraft_sum": ks, "kraft_ok": ks <= 1.0 + 1e-12,
                            "prefix_free": pf, "offending_pair": offender,
                            "stream_roundtrip": rt, "n_codes": len(codes)}
            if not (report[name]["kraft_ok"] and pf and rt):
                raise KraftViolation(f"{name} failed: {report[name]}")

        report["join"] = self._join_check()
        self._check_report = report
        self._checked = True
        return report

    def _join_check(self) -> dict:
        """End-to-end: compose messages, decode them back, require equality.

        Covers the awkward corners on purpose -- zero mechanisms (all
        fallback), a single segment, repeated mechanisms (which is what the
        dictionary and pointer exist for), and a fallback adjacent to a
        mechanism segment.
        """
        cases: list[tuple[int, list[Segment]]] = []
        m0, m1 = 0, min(1, len(self.mechanisms) - 1)

        cases.append((8, [Segment(0, 8, m0)]))
        cases.append((8, [Segment(0, 8, None, [1, 0, 1, 1, 0, 0, 1, 0])]))
        cases.append((16, [Segment(0, 8, m0), Segment(8, 8, m1)]))
        cases.append((16, [Segment(0, 8, m0), Segment(8, 8, m0)]))
        cases.append((24, [Segment(0, 8, m0),
                           Segment(8, 8, None, [0] * 8),
                           Segment(16, 8, m1)]))
        cases.append((32, [Segment(0, 8, m1), Segment(8, 8, m1),
                           Segment(16, 8, None, [1] * 8), Segment(24, 8, m0)]))

        results = []
        for n, segs in cases:
            bits, comp = self.encode(n, segs)
            n2, segs2 = self.decode(bits)
            same = (n2 == n and len(segs2) == len(segs) and all(
                a.start == b.start and a.length == b.length and a.mech == b.mech
                and list(a.residual_bits) == list(b.residual_bits)
                for a, b in zip(segs, segs2)))
            # the accounting must equal the emitted stream, exactly
            accounted = comp.total() == len(bits)
            results.append({"n": n, "segments": len(segs), "bits": len(bits),
                            "roundtrip": same, "accounting_exact": accounted})
            if not (same and accounted):
                raise KraftViolation(f"join check failed on {segs}: {results[-1]}")
        return {"cases": results, "all_passed": True}

    # -- the guarded number -------------------------------------------------

    def codelength(self, n: int, segments: list[Segment]) -> tuple[int, Components]:
        """L_G(x) in bits. Refuses until AC-R4-1 has passed in this process."""
        if not self._checked:
            raise KraftViolation(
                "AC-R4-1: self_check() must pass before any length is quoted. "
                "An un-Kraft-checked codelength is not a codelength.")
        bits, comp = self.encode(n, segments)
        if comp.total() != len(bits):
            raise KraftViolation(
                f"accounting {comp.total()} != emitted {len(bits)}")
        return len(bits), comp
