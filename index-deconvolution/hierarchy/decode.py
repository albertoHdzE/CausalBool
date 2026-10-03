"""HID-v1 independent decoder for every codec in the wire annex (W1-W7).

Standard library only and self-contained: this file imports nothing from the
hierarchy package, keeps its own copy of the constants, its own field parser,
rank/unrank and graph evaluator. It can be copied alone into an empty
directory and run as ``python decode.py ARCHIVE...``; the separate-process test
does exactly that, with the search, corpus and original strings unavailable.

Inputs are archive bytes and explicit resource limits, nothing else.

Resource limits (documented in README.md):
  max_output_bits  envelope n (default 16,777,216);
  max_rules        HID q (default 1,000,000);
  intermediate     sum of all HID rule lengths <= 64 * max(1, n), and the same
                   bound on pair-grammar rule expansions;
  AP marks         sum of AP counts over all rules <= 64 * max(1, n);
  schema work      sum over schema rules of q_schema * length <= 4096 * max(1, n);
  payload bytes    payload_n_bytes must equal the bytes actually present; the
                   decoder holds the archive in memory, so the caller bounds input
                   size (the benchmark never reads archives above 16 MiB).
Exceeding a limit raises ResourceLimitError; nothing partial is returned.
"""
from __future__ import annotations

import lzma
import math
import sys
import zlib

MAGIC = b"ISD1"
MAX_U = 2 ** 63 - 1
CODEC_IDS = {"raw": 0, "hid": 1, "rle": 2, "gaps": 3, "period": 4, "bernoulli": 5,
             "context": 6, "zlib": 7, "lzma": 8, "pair_grammar": 9}
OPCODES = {"LITERAL": 0, "CONCAT": 1, "REPEAT": 2, "AP_UNION": 3,
           "SCHEMA_UNION": 4, "PATCH": 5, "XFORM": 6}


class ArchiveError(ValueError):
    """The archive is malformed or violates the format."""


class ResourceLimitError(ArchiveError):
    """A valid-looking archive exceeds an explicit decoder resource limit."""


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def byte(self) -> int:
        if self.pos >= len(self.data):
            raise ArchiveError("truncated: expected a byte")
        b = self.data[self.pos]
        self.pos += 1
        return b

    def take(self, k: int) -> bytes:
        if k < 0 or self.pos + k > len(self.data):
            raise ArchiveError("truncated: field runs past the end")
        out = self.data[self.pos:self.pos + k]
        self.pos += k
        return out

    def u(self) -> int:
        value = 0
        shift = 0
        start = self.pos
        while True:
            b = self.byte()
            value |= (b & 0x7F) << shift
            shift += 7
            if not b & 0x80:
                break
            if shift > 63:
                raise ArchiveError("U field overflows 2^63-1")
        if self.pos - start > 1 and b == 0:
            raise ArchiveError("non-canonical U: redundant leading zero group")
        if value > MAX_U:
            raise ArchiveError("U field overflows 2^63-1")
        return value

    def done(self) -> bool:
        return self.pos == len(self.data)


def _unpack(raw: bytes, nbits: int) -> str:
    if len(raw) != (nbits + 7) // 8:
        raise ArchiveError("packed field has the wrong byte count")
    if nbits == 0:
        return ""
    v = int.from_bytes(raw, "big")
    pad = 8 * len(raw) - nbits
    if v & ((1 << pad) - 1):
        raise ArchiveError("nonzero padding bits")
    return format(v >> pad, "b").zfill(nbits)


def _unrank(m: int, k: int, raw: bytes) -> str:
    if k < 0 or k > m:
        raise ArchiveError("rank weight outside 0..m")
    total = math.comb(m, k)
    width = ((total - 1).bit_length() + 7) // 8
    if len(raw) != width:
        raise ArchiveError("rank field has the wrong byte count")
    rank = int.from_bytes(raw, "big") if width else 0
    if rank >= total:
        raise ArchiveError("rank out of range")
    out = bytearray()
    a = m - 1
    kk = k
    cur = math.comb(a, kk) if m else 0
    for _ in range(m):
        if rank < cur:
            out.append(48)
            cur = cur * (a - kk) // a if a else 0
        else:
            rank -= cur
            out.append(49)
            cur = cur * kk // a if a else 0
            kk -= 1
        a -= 1
    return out.decode("ascii")


def _rank_len(m: int, k: int) -> int:
    return ((math.comb(m, k) - 1).bit_length() + 7) // 8


def _flip(ch: str) -> str:
    return "1" if ch == "0" else "0"


# ---------------------------------------------------------------------------
# HID DAG
# ---------------------------------------------------------------------------

def _decode_hid(p: _Reader, n: int, max_rules: int) -> str:
    q = p.u()
    if q < 1:
        raise ArchiveError("HID needs q >= 1")
    if q > max_rules:
        raise ResourceLimitError(f"q={q} exceeds max_rules={max_rules}")
    budget = 64 * max(1, n)
    recs = []
    lens = []
    total = 0
    ap_marks = 0
    schema_work = 0
    for i in range(q):
        op = p.byte()
        if op == 0:
            length = p.u()
            if length < 1:
                raise ArchiveError("LITERAL length must be positive")
            if length > n:
                raise ArchiveError("rule longer than n")
            bits = _unpack(p.take((length + 7) // 8), length)
            recs.append((0, bits))
        elif op == 1:
            arity = p.u()
            if arity < 2:
                raise ArchiveError("CONCAT arity must be >= 2")
            if arity > len(p.data):
                raise ArchiveError("truncated: CONCAT arity exceeds payload")
            kids = [p.u() for _ in range(arity)]
            for c in kids:
                if c >= i:
                    raise ArchiveError("forward or self reference")
            length = 0
            for c in kids:
                length += lens[c]
                if length > n:
                    raise ArchiveError("rule longer than n")
            recs.append((1, kids))
        elif op == 2:
            c = p.u()
            copies = p.u()
            if c >= i:
                raise ArchiveError("forward or self reference")
            if copies < 2:
                raise ArchiveError("REPEAT copies must be >= 2")
            if copies > n // lens[c]:
                raise ArchiveError("rule longer than n")
            length = lens[c] * copies
            recs.append((2, c, copies))
        elif op == 3:
            length = p.u()
            fg = p.byte()
            qa = p.u()
            if length < 1 or length > n:
                raise ArchiveError("AP_UNION length outside 1..n")
            if fg > 1:
                raise ArchiveError("foreground must be 0 or 1")
            if qa > len(p.data):
                raise ArchiveError("truncated: q_ap exceeds payload")
            aps = []
            for _ in range(qa):
                t = (p.u(), p.u(), p.u())
                start, step, count = t
                if step < 1 or count < 1:
                    raise ArchiveError("AP step and count must be >= 1")
                if count > length or start + (count - 1) * step >= length:
                    raise ArchiveError("AP leaves its domain")
                if aps and not aps[-1] < t:
                    raise ArchiveError("AP entries not strictly sorted")
                aps.append(t)
                ap_marks += count
                if ap_marks > budget:
                    raise ResourceLimitError("AP marks exceed 64 * max(1, n)")
            recs.append((3, length, fg, aps))
        elif op == 4:
            length = p.u()
            fg = p.byte()
            qs = p.u()
            if length < 1 or length > n:
                raise ArchiveError("SCHEMA_UNION length outside 1..n")
            if fg > 1:
                raise ArchiveError("foreground must be 0 or 1")
            if qs > len(p.data):
                raise ArchiveError("truncated: q_schema exceeds payload")
            d = (length - 1).bit_length()
            pairs = []
            for _ in range(qs):
                t = (p.u(), p.u())
                mask, value = t
                if mask >> d:
                    raise ArchiveError("schema mask beyond d coordinates")
                if value & ~mask:
                    raise ArchiveError("schema value outside its mask")
                if value >= length:
                    raise ArchiveError("schema matches no valid address")
                if pairs and not pairs[-1] < t:
                    raise ArchiveError("schema pairs not strictly sorted")
                pairs.append(t)
            schema_work += qs * length
            if schema_work > 4096 * max(1, n):
                raise ResourceLimitError("schema evaluation exceeds 4096 * max(1, n)")
            recs.append((4, length, fg, pairs))
        elif op == 5:
            c = p.u()
            qf = p.u()
            if c >= i:
                raise ArchiveError("forward or self reference")
            if qf < 1:
                raise ArchiveError("PATCH q_flip must be >= 1")
            length = lens[c]
            if qf > length:
                raise ArchiveError("PATCH has more flips than positions")
            pos = []
            for j in range(qf):
                dlt = p.u()
                x = dlt if j == 0 else pos[-1] + dlt + 1
                if x >= length:
                    raise ArchiveError("PATCH position out of range")
                pos.append(x)
            recs.append((5, c, pos))
        elif op == 6:
            c = p.u()
            flags = p.byte()
            r = p.u()
            if c >= i:
                raise ArchiveError("forward or self reference")
            if flags & ~3:
                raise ArchiveError("XFORM reserved flag bits set")
            length = lens[c]
            if r >= length:
                raise ArchiveError("XFORM rotation >= child length")
            if flags == 0 and r == 0:
                raise ArchiveError("XFORM identity record")
            recs.append((6, c, flags, r))
        else:
            raise ArchiveError(f"unknown opcode {op}")
        lens.append(length)
        total += length
        if total > budget:
            raise ResourceLimitError("intermediate bits exceed 64 * max(1, n)")
    if not p.done():
        raise ArchiveError("trailing bytes after the last rule")
    if lens[-1] != n:
        raise ArchiveError(f"root expands to {lens[-1]} bits, envelope says {n}")
    reach = [False] * q
    reach[-1] = True
    for i in range(q - 1, -1, -1):
        if not reach[i]:
            raise ArchiveError(f"rule {i} unreachable from the root")
        rec = recs[i]
        if rec[0] == 1:
            for c in rec[1]:
                reach[c] = True
        elif rec[0] in (2, 5, 6):
            reach[rec[1]] = True
    vals: list[str] = []
    for rec in recs:
        kind = rec[0]
        if kind == 0:
            vals.append(rec[1])
        elif kind == 1:
            vals.append("".join(vals[c] for c in rec[1]))
        elif kind == 2:
            vals.append(vals[rec[1]] * rec[2])
        elif kind == 3:
            _, length, fg, aps = rec
            cells = [str(1 - fg)] * length
            for start, step, count in aps:
                for j in range(count):
                    cells[start + j * step] = str(fg)
            vals.append("".join(cells))
        elif kind == 4:
            _, length, fg, pairs = rec
            fgc, bgc = str(fg), str(1 - fg)
            vals.append("".join(
                fgc if any((i & m) == v for m, v in pairs) else bgc
                for i in range(length)))
        elif kind == 5:
            cells = list(vals[rec[1]])
            for x in rec[2]:
                cells[x] = _flip(cells[x])
            vals.append("".join(cells))
        else:
            s = vals[rec[1]]
            flags, r = rec[2], rec[3]
            if flags & 1:
                s = "".join(_flip(ch) for ch in s)
            if flags & 2:
                s = s[::-1]
            if r:
                s = s[len(s) - r:] + s[:len(s) - r]
            vals.append(s)
    return vals[-1]


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------

def _decode_rle(p: _Reader, n: int) -> str:
    first = p.byte()
    if first > 1:
        raise ArchiveError("first_bit must be 0 or 1")
    q = p.u()
    if q < 1:
        raise ArchiveError("RLE needs q_runs >= 1")
    if q > n:
        raise ArchiveError("more runs than bits")
    out = []
    total = 0
    bit = first
    for _ in range(q):
        k = p.u()
        if k < 1:
            raise ArchiveError("zero-length run")
        total += k
        if total > n:
            raise ArchiveError("runs exceed n")
        out.append(str(bit) * k)
        bit ^= 1
    if total != n:
        raise ArchiveError("runs do not sum to n")
    return "".join(out)


def _read_positions(p: _Reader, q: int, n: int) -> list[int]:
    pos: list[int] = []
    for j in range(q):
        d = p.u()
        x = d if j == 0 else pos[-1] + d + 1
        if x >= n:
            raise ArchiveError("position out of range")
        pos.append(x)
    return pos


def _decode_gaps(p: _Reader, n: int) -> str:
    fg = p.byte()
    if fg > 1:
        raise ArchiveError("foreground must be 0 or 1")
    q = p.u()
    if q > n:
        raise ArchiveError("more positions than bits")
    cells = [str(1 - fg)] * n
    for x in _read_positions(p, q, n):
        cells[x] = str(fg)
    return "".join(cells)


def _decode_period(p: _Reader, n: int) -> str:
    plen = p.u()
    if plen < 1 or plen > n:
        raise ArchiveError("period_length outside 1..n")
    w = _unpack(p.take((plen + 7) // 8), plen)
    return (w * (n // plen + 1))[:n]


def _decode_bernoulli(p: _Reader, n: int) -> str:
    ones = p.u()
    if ones > n:
        raise ArchiveError("ones exceeds n")
    return _unrank(n, ones, p.take(_rank_len(n, ones)))


def _decode_context(p: _Reader, n: int) -> str:
    first = p.byte()
    if first > 1:
        raise ArchiveError("first_bit must be 0 or 1")
    m0 = p.u()
    if m0 > n - 1:
        raise ArchiveError("m0 exceeds n-1")
    m1 = n - 1 - m0
    k0 = p.u()
    k1 = p.u()
    if k0 > m0 or k1 > m1:
        raise ArchiveError("queue weight exceeds queue length")
    q0 = _unrank(m0, k0, p.take(_rank_len(m0, k0)))
    q1 = _unrank(m1, k1, p.take(_rank_len(m1, k1)))
    queues = (q0, q1)
    heads = [0, 0]
    out = [str(first)]
    last = first
    for _ in range(n - 1):
        if heads[last] >= len(queues[last]):
            raise ArchiveError("context queue underflow")
        ch = queues[last][heads[last]]
        heads[last] += 1
        out.append(ch)
        last = 1 if ch == "1" else 0
    if heads[0] != m0 or heads[1] != m1:
        raise ArchiveError("context queues not fully consumed")
    return "".join(out)


def _decode_stdlib(payload: bytes, n: int, codec: int) -> str:
    want = (n + 7) // 8
    if codec == 7:
        d = zlib.decompressobj()
        try:
            raw = d.decompress(payload, want + 1)
        except zlib.error as exc:
            raise ArchiveError(f"zlib: {exc}") from None
        if len(raw) > want or d.unconsumed_tail:
            raise ArchiveError("zlib stream decompresses beyond ceil(n/8)")
        if not d.eof or d.unused_data:
            raise ArchiveError("zlib stream incomplete or followed by unused data")
    else:
        d = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
        try:
            raw = d.decompress(payload, max_length=want + 1)
        except lzma.LZMAError as exc:
            raise ArchiveError(f"lzma: {exc}") from None
        if len(raw) > want:
            raise ArchiveError("xz stream decompresses beyond ceil(n/8)")
        if not d.eof or d.unused_data:
            raise ArchiveError("xz stream incomplete or followed by unused data")
        if d.check != lzma.CHECK_CRC64:
            raise ArchiveError("xz stream does not use CHECK_CRC64")
    return _unpack(raw, n)


def _decode_pair(p: _Reader, n: int) -> str:
    q = p.u()
    if q > len(p.data):
        raise ArchiveError("truncated: q_rules exceeds payload")
    rules = []
    lens = [1, 1]
    budget = 64 * max(1, n)
    total = 0
    for i in range(q):
        rid = i + 2
        a, b = p.u(), p.u()
        if a >= rid or b >= rid:
            raise ArchiveError("pair rule references itself or a later rule")
        length = lens[a] + lens[b]
        if length > n:
            raise ArchiveError("pair rule longer than n")
        total += length
        if total > budget:
            raise ResourceLimitError("pair-grammar expansions exceed 64 * max(1, n)")
        rules.append((a, b))
        lens.append(length)
    m = p.u()
    if m > len(p.data):
        raise ArchiveError("truncated: m_start exceeds payload")
    start = [p.u() for _ in range(m)]
    reach = [False] * (q + 2)
    out_len = 0
    for s in start:
        if s >= q + 2:
            raise ArchiveError("start symbol references an unknown rule")
        reach[s] = True
        out_len += lens[s]
    if out_len != n:
        raise ArchiveError("pair grammar does not expand to n bits")
    for rid in range(q + 1, 1, -1):
        if not reach[rid]:
            raise ArchiveError(f"pair rule {rid} unreachable")
        a, b = rules[rid - 2]
        reach[a] = reach[b] = True
    vals = ["0", "1"]
    for a, b in rules:
        vals.append(vals[a] + vals[b])
    return "".join(vals[s] for s in start)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def decode_archive(data: bytes, *, max_output_bits: int = 16777216,
                   max_rules: int = 1000000) -> str:
    """Decode one complete archive to its exact '0'/'1' string."""
    if type(data) is not bytes:
        raise TypeError(f"archive must be bytes, got {type(data).__name__}")
    r = _Reader(data)
    if r.take(4) != MAGIC:
        raise ArchiveError("wrong magic")
    codec = r.byte()
    n = r.u()
    if n > max_output_bits:
        raise ResourceLimitError(f"n={n} exceeds max_output_bits={max_output_bits}")
    plen = r.u()
    if len(data) - r.pos != plen:
        raise ArchiveError("payload length does not match the bytes present")
    payload = data[r.pos:]
    if codec > 9:
        raise ArchiveError(f"unknown codec {codec}")
    if n == 0:
        if codec != 0 or plen:
            raise ArchiveError("the empty string has only the literal empty archive")
        return ""
    p = _Reader(payload)
    if codec == 0:
        return _unpack(payload, n)
    if codec in (7, 8):
        return _decode_stdlib(payload, n, codec)
    if codec == 1:
        out = _decode_hid(p, n, max_rules)
    elif codec == 2:
        out = _decode_rle(p, n)
    elif codec == 3:
        out = _decode_gaps(p, n)
    elif codec == 4:
        out = _decode_period(p, n)
    elif codec == 5:
        out = _decode_bernoulli(p, n)
    elif codec == 6:
        out = _decode_context(p, n)
    else:
        out = _decode_pair(p, n)
    if not p.done():
        raise ArchiveError("trailing payload bytes")
    if len(out) != n:
        raise ArchiveError("decoded length differs from the envelope")
    return out


def _main(paths: list[str]) -> int:
    import json
    results = []
    for path in paths:
        with open(path, "rb") as fh:
            data = fh.read()
        try:
            results.append({"path": path, "ok": True, "bits": decode_archive(data)})
        except ArchiveError as exc:
            results.append({"path": path, "ok": False, "error": type(exc).__name__,
                            "message": str(exc)})
    json.dump(results, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
