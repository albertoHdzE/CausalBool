"""HID-v1 canonical serialization (wire annex W1, W3, W4 deltas, W5 ranks).

Every field is written through a ``Ledger`` that keeps the exact bytes and a
label, so a per-field cost table is the archive itself cut into pieces, never
an analytic estimate: ``b"".join(ledger bytes) == archive`` is asserted.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import codes as C
from .model import (APUnion, Concat, Literal, Model, Patch, Repeat, SchemaUnion,
                    Xform, check_bits)


# ---------------------------------------------------------------------------
# Primitive fields
# ---------------------------------------------------------------------------

def put_u(v: int) -> bytes:
    """Canonical unsigned LEB128 of 0 <= v <= 2^63-1 (bool refused)."""
    if isinstance(v, bool) or not isinstance(v, int):
        raise TypeError(f"U field needs an int, got {type(v).__name__}")
    if v < 0 or v > C.MAX_U:
        raise ValueError(f"U field value {v} outside [0, 2^63-1]")
    out = bytearray()
    while True:
        byte = v & 0x7F
        v >>= 7
        if v:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def pack_bits(s: str) -> bytes:
    """P(s): MSB-first packing; unused low bits of the last byte are zero."""
    if not s:
        return b""
    nbytes = (len(s) + 7) // 8
    return (int(s, 2) << (8 * nbytes - len(s))).to_bytes(nbytes, "big")


def rank_width_bytes(m: int, k: int) -> int:
    from math import comb
    total = comb(m, k)
    return ((total - 1).bit_length() + 7) // 8


def lex_rank(bits: str) -> int:
    """Lexicographic rank (0 < 1) of ``bits`` among strings of its length and weight.

    Integer only. Walks the string once, keeping C(a, kk) up to date with exact
    multiplicative updates instead of recomputing binomials.
    """
    from math import comb
    m = len(bits)
    kk = bits.count("1")
    if m == 0:
        return 0
    rank = 0
    a = m - 1
    cur = comb(a, kk)                       # strings with a 0 here, kk ones after
    for ch in bits:
        if ch == "1":
            rank += cur
            nxt = cur * kk // a if a else 0      # C(a-1, kk-1)
            kk -= 1
        else:
            nxt = cur * (a - kk) // a if a else 0  # C(a-1, kk)
        cur = nxt
        a -= 1
    return rank


def put_rank(bits: str) -> bytes:
    """R(m, k) field for ``bits``: big-endian right-aligned rank, ceil(w/8) bytes."""
    width = rank_width_bytes(len(bits), bits.count("1"))
    return lex_rank(bits).to_bytes(width, "big") if width else b""


def deltas(positions) -> bytes:
    """W4 position deltas: first position, then gaps minus one."""
    out = bytearray()
    prev = None
    for p in positions:
        out += put_u(p if prev is None else p - prev - 1)
        prev = p
    return bytes(out)


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------

@dataclass
class Ledger:
    entries: list[tuple[str, str, bytes]] = field(default_factory=list)

    def add(self, owner: str, label: str, data: bytes) -> None:
        self.entries.append((owner, label, bytes(data)))

    def payload(self) -> bytes:
        return b"".join(e[2] for e in self.entries)

    def rows(self) -> list[dict]:
        return [{"owner": o, "field": f, "bytes": len(b), "hex": b.hex()}
                for o, f, b in self.entries]


def envelope_ledger(codec_id: int, n: int, payload: bytes) -> Ledger:
    led = Ledger()
    led.add("envelope", "magic", C.MAGIC)
    led.add("envelope", "codec_id", bytes([codec_id]))
    led.add("envelope", "output_n_bits", put_u(n))
    led.add("envelope", "payload_n_bytes", put_u(len(payload)))
    return led


def envelope(codec_id: int, n: int, payload: bytes) -> bytes:
    if n == 0 and (codec_id != C.CODEC_LITERAL or payload):
        raise ValueError("the empty string has only the literal empty archive")
    return C.MAGIC + bytes([codec_id]) + put_u(n) + put_u(len(payload)) + payload


def encode_literal(bits: str) -> bytes:
    check_bits(bits)
    return envelope(C.CODEC_LITERAL, len(bits), pack_bits(bits))


def literal_ledger(bits: str) -> Ledger:
    check_bits(bits)
    payload = pack_bits(bits)
    led = envelope_ledger(C.CODEC_LITERAL, len(bits), payload)
    led.add("payload", f"P(bits) [{len(bits)} bits + {8 * len(payload) - len(bits)} pad]",
            payload)
    return led


# ---------------------------------------------------------------------------
# HID DAG (W3)
# ---------------------------------------------------------------------------

def model_payload_ledger(model: Model) -> Ledger:
    led = Ledger()
    led.add("dag", "q_rules", put_u(len(model.rules)))
    for i, r in enumerate(model.rules):
        own = f"rule{i}"
        led.add(own, "opcode", bytes([r.op]))
        if isinstance(r, Literal):
            led.add(own, "length", put_u(len(r.bits)))
            pad = 8 * ((len(r.bits) + 7) // 8) - len(r.bits)
            led.add(own, f"P(bits) [{len(r.bits)} bits + {pad} pad]", pack_bits(r.bits))
        elif isinstance(r, Concat):
            led.add(own, "arity", put_u(len(r.children)))
            led.add(own, "child_ids", b"".join(put_u(c) for c in r.children))
        elif isinstance(r, Repeat):
            led.add(own, "child_id", put_u(r.child))
            led.add(own, "copies", put_u(r.copies))
        elif isinstance(r, APUnion):
            led.add(own, "length", put_u(r.length))
            led.add(own, "foreground", bytes([r.foreground]))
            led.add(own, "q_ap", put_u(len(r.aps)))
            led.add(own, "ap_triples", b"".join(
                put_u(s) + put_u(t) + put_u(c) for s, t, c in r.aps))
        elif isinstance(r, SchemaUnion):
            led.add(own, "length", put_u(r.length))
            led.add(own, "foreground", bytes([r.foreground]))
            led.add(own, "q_schema", put_u(len(r.pairs)))
            led.add(own, "mask_value_pairs", b"".join(
                put_u(m) + put_u(v) for m, v in r.pairs))
        elif isinstance(r, Patch):
            led.add(own, "child_id", put_u(r.child))
            led.add(own, "q_flip", put_u(len(r.positions)))
            led.add(own, "position_deltas", deltas(r.positions))
        elif isinstance(r, Xform):
            led.add(own, "child_id", put_u(r.child))
            led.add(own, "flags", bytes([r.flags]))
            led.add(own, "right_rotation", put_u(r.rotation))
        else:                                   # pragma: no cover - Model validates
            raise TypeError(type(r))
    return led


def model_ledger(model: Model, n_bits: int) -> Ledger:
    if isinstance(n_bits, bool) or not isinstance(n_bits, int) or n_bits < 1:
        raise ValueError("a HID archive needs n_bits >= 1")
    lengths = model.lengths()
    if lengths[-1] != n_bits:
        raise ValueError(f"root expands to {lengths[-1]} bits, not {n_bits}")
    if max(lengths) > n_bits:
        raise ValueError("a rule expands beyond n")
    body = model_payload_ledger(model)
    led = envelope_ledger(C.CODEC_HID, n_bits, body.payload())
    led.entries.extend(body.entries)
    return led


def serialize_model(model: Model, n_bits: int) -> bytes:
    led = model_ledger(model, n_bits)
    data = b"".join(e[2] for e in led.entries)
    return data


def model_payload(model: Model) -> bytes:
    """Payload bytes only (used by the search as a proposal heuristic)."""
    return model_payload_ledger(model).payload()
