"""Tiny bounded oracle: exhaustive minimum over a deliberately small language.

Language (protocol 5.3): expression TREES of <= 3 nodes built from LITERAL,
binary CONCAT and REPEAT(copies >= 2); literals nonempty; every intermediate
expansion within the length bound; children are earlier nodes; NO sharing, AP,
schema, transform or patch. The trees are therefore exactly

    L(w),  R(L(w), c),  R(R(L(w), c1), c2),  C(L(a), L(b)).

Archives are serialized by this module's own minimal writer (independent of
wire.py) and cross-checked against the production serializer by the tests.
The minimum is over THIS language only -- not over all HID DAGs and not K.
"""
from __future__ import annotations

from itertools import product


def _u(v: int) -> bytes:
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        out.append(b | (0x80 if v else 0))
        if not v:
            return bytes(out)


def _p(s: str) -> bytes:
    if not s:
        return b""
    k = (len(s) + 7) // 8
    return (int(s, 2) << (8 * k - len(s))).to_bytes(k, "big")


def _env(codec: int, n: int, payload: bytes) -> bytes:
    return b"ISD1" + bytes([codec]) + _u(n) + _u(len(payload)) + payload


def _lit(w: str) -> bytes:
    return b"\x00" + _u(len(w)) + _p(w)


def raw_archive(s: str) -> bytes:
    return _env(0, len(s), _p(s))


def tree_archives(words, max_len: int):
    """Yield (program text, output, archive) for every tree in the language."""
    for w in words:
        yield f"L({w})", w, _env(1, len(w), _u(1) + _lit(w))
        for c in range(2, max_len // len(w) + 1):
            out = w * c
            yield (f"R(L({w}),{c})", out,
                   _env(1, len(out), _u(2) + _lit(w) + b"\x02" + _u(0) + _u(c)))
            for c2 in range(2, max_len // len(out) + 1):
                out2 = out * c2
                yield (f"R(R(L({w}),{c}),{c2})", out2,
                       _env(1, len(out2), _u(3) + _lit(w) + b"\x02" + _u(0) + _u(c)
                            + b"\x02" + _u(1) + _u(c2)))
    for a in words:
        for b in words:
            if len(a) + len(b) <= max_len:
                out = a + b
                yield (f"C(L({a}),L({b}))", out,
                       _env(1, len(out), _u(3) + _lit(a) + _lit(b) + b"\x01" + _u(2)
                            + _u(0) + _u(1)))


def all_words(lo: int, hi: int) -> list[str]:
    return ["".join(t) for k in range(lo, hi + 1) for t in product("01", repeat=k)]


def minimum_map(words, max_len: int) -> dict[str, dict]:
    """Grammar-only minimum per generated output, with the raw-inclusive minimum."""
    best: dict[str, tuple[int, bytes, str]] = {}
    for prog, out, arc in tree_archives(words, max_len):
        key = (len(arc), arc, prog)
        if out not in best or key < best[out]:
            best[out] = key
    table = {}
    for out, (_, arc, prog) in best.items():
        raw = raw_archive(out)
        table[out] = {
            "grammar_only_bits": 8 * len(arc), "grammar_only_program": prog,
            "grammar_only_archive_hex": arc.hex(), "raw_bits": 8 * len(raw),
            "raw_inclusive_bits": 8 * min(len(arc), len(raw)),
            "raw_inclusive_mode": "hid" if len(arc) < len(raw) else "raw"}
    return table


def oracle_n8() -> dict[str, dict]:
    """Every target of length 0..8; unrepresented targets marked as such."""
    table = minimum_map(all_words(1, 8), 8)
    out = {"": {"grammar_only_bits": None, "grammar_only_program": "unrepresented",
                "raw_bits": 8 * len(raw_archive("")),
                "raw_inclusive_bits": 8 * len(raw_archive("")), "raw_inclusive_mode": "raw"}}
    for s in all_words(1, 8):
        out[s] = table.get(s) or {
            "grammar_only_bits": None, "grammar_only_program": "unrepresented",
            "raw_bits": 8 * len(raw_archive(s)), "raw_inclusive_bits": 8 * len(raw_archive(s)),
            "raw_inclusive_mode": "raw"}
    return out


def oracle_generated64() -> dict[str, dict]:
    """Programs with literal leaves of length 1..4 and output length <= 64."""
    return minimum_map(all_words(1, 4), 64)
