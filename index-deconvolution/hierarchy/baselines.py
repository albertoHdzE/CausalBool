"""Comparison codecs (wire annex W4-W7) and the decodable best-baseline portfolio.

These are actual lossless codes measured by their complete archives. The
statistical ones (Bernoulli, first-order context) are comparators only: they are
not description-length variants and never enter the HID model-selection
objective.
"""
from __future__ import annotations

import lzma
import zlib

from . import codes as C
from .candidates import pair_grammar, positions_of, shortest_period
from .model import check_bits
from .wire import Ledger, deltas, envelope, envelope_ledger, pack_bits, put_rank, put_u

BASELINE_METHODS = ("raw", "rle", "gaps", "period", "bernoulli", "context",
                    "zlib", "lzma", "pair_grammar")
METHOD_CODEC = {name: cid for cid, name in C.CODEC_NAMES.items()}


def _rle_payload(bits: str) -> Ledger:
    led = Ledger()
    runs = []
    i = 0
    n = len(bits)
    while i < n:
        j = i
        while j < n and bits[j] == bits[i]:
            j += 1
        runs.append(j - i)
        i = j
    led.add("rle", "first_bit", bytes([int(bits[0])]))
    led.add("rle", "q_runs", put_u(len(runs)))
    led.add("rle", "run_lengths", b"".join(put_u(r) for r in runs))
    return led


def _gaps_payload(bits: str) -> Ledger:
    best = None
    for fg in (0, 1):
        pos = positions_of(bits, str(fg))
        led = Ledger()
        led.add("gaps", "foreground", bytes([fg]))
        led.add("gaps", "q_positions", put_u(len(pos)))
        led.add("gaps", "position_deltas", deltas(pos))
        key = (len(led.payload()), led.payload())
        if best is None or key < best[0]:
            best = (key, led)
    return best[1]


def _period_payload(bits: str) -> Ledger:
    p = shortest_period(bits)
    led = Ledger()
    led.add("period", "period_length", put_u(p))
    led.add("period", f"P(first_period) [{p} bits]", pack_bits(bits[:p]))
    return led


def _bernoulli_payload(bits: str) -> Ledger:
    led = Ledger()
    led.add("bernoulli", "ones", put_u(bits.count("1")))
    led.add("bernoulli", "R(n,ones)", put_rank(bits))
    return led


def context_queues(bits: str) -> tuple[str, str]:
    q = (bytearray(), bytearray())
    for t in range(len(bits) - 1):
        q[bits[t] == "1"].append(ord(bits[t + 1]))
    return q[0].decode("ascii"), q[1].decode("ascii")


def _context_payload(bits: str) -> Ledger:
    q0, q1 = context_queues(bits)
    led = Ledger()
    led.add("context", "first_bit", bytes([int(bits[0])]))
    led.add("context", "m0", put_u(len(q0)))
    led.add("context", "k0", put_u(q0.count("1")))
    led.add("context", "k1", put_u(q1.count("1")))
    led.add("context", "R(m0,k0)", put_rank(q0))
    led.add("context", "R(m1,k1)", put_rank(q1))
    return led


def _zlib_payload(bits: str) -> Ledger:
    led = Ledger()
    led.add("zlib", "zlib stream (header, deflate, adler32)",
            zlib.compress(pack_bits(bits), C.ZLIB_LEVEL))
    return led


def _lzma_payload(bits: str) -> Ledger:
    led = Ledger()
    led.add("lzma", "xz stream (headers, lzma2, crc64, footer)",
            lzma.compress(pack_bits(bits), format=lzma.FORMAT_XZ,
                          check=lzma.CHECK_CRC64, preset=C.LZMA_PRESET))
    return led


def pair_grammar_bits(bits: str) -> tuple[list[tuple[int, int]], list[int]]:
    return pair_grammar([int(c) for c in bits], 2, C.PAIR_MAX_RULES)


def _pair_payload(bits: str) -> Ledger:
    rules, start = pair_grammar_bits(bits)
    led = Ledger()
    led.add("pair", "q_rules", put_u(len(rules)))
    led.add("pair", "rule_pairs", b"".join(put_u(a) + put_u(b) for a, b in rules))
    led.add("pair", "m_start", put_u(len(start)))
    led.add("pair", "start_symbols", b"".join(put_u(s) for s in start))
    return led


_PAYLOADS = {
    "rle": _rle_payload, "gaps": _gaps_payload, "period": _period_payload,
    "bernoulli": _bernoulli_payload, "context": _context_payload,
    "zlib": _zlib_payload, "lzma": _lzma_payload, "pair_grammar": _pair_payload,
}


def baseline_ledger(bits: str, method: str) -> Ledger:
    check_bits(bits)
    if method not in BASELINE_METHODS:
        raise ValueError(f"unknown baseline {method!r}; choose from {BASELINE_METHODS}")
    if not bits or method == "raw":
        payload = pack_bits(bits)
        led = envelope_ledger(C.CODEC_LITERAL, len(bits), payload)
        led.add("payload", f"P(bits) [{len(bits)} bits]", payload)
        return led
    body = _PAYLOADS[method](bits)
    led = envelope_ledger(METHOD_CODEC[method], len(bits), body.payload())
    led.entries.extend(body.entries)
    return led


def encode_baseline(bits: str, method: str) -> bytes:
    """Standalone archive of one baseline (its own mode even when larger than raw)."""
    led = baseline_ledger(bits, method)
    data = b"".join(e[2] for e in led.entries)
    if len(bits) == 0:
        assert data == envelope(C.CODEC_LITERAL, 0, b"")
    return data


def select_best(archives: dict[str, bytes]) -> str:
    """baseline_best: minimum length, ties by codec id then archive bytes."""
    if set(archives) != set(BASELINE_METHODS):
        raise ValueError("baseline_best needs all nine constituent archives")
    return min(archives, key=lambda m: (len(archives[m]), archives[m][4], archives[m]))
