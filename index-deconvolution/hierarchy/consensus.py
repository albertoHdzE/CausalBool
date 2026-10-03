"""HID-search-v2 template proposals (SEARCH.md section 2): stages P, C, D and G.

Inputs are the bit string and plain frozen parameters, nothing else: no family,
period, seed, noise mask, boundary or earlier archive. Every proposal is an
ordinary HID-v1 node graph built with the existing ``NodeFactory``; it transmits
the template word, its repeat count, the exact tail and EVERY residual error, so
the decoder reconstructs the observed string, never a cleaned one.

Template words:
  first block (P)  w = x[:p];
  consensus (C,D,G) phase j is 1 exactly when more than half of x[j::p] is 1
                   (a tie gives 0).
y = w repeated and truncated to n. A proposal is rejected when x and y differ in
more than floor(n / residual_divisor) positions.

Builders:
  periodic(b, p)   q, t = divmod(len(b), p); q < 2 -> Literal(b); otherwise
                   Repeat(Literal(b[:p]), q) followed by Literal(b[-t:]) if t > 0.
                   ``b`` is a slice of y, so a block's word carries its phase.
  local            aligned 1,024-bit blocks; a block whose own mismatch count
                   exceeds min(local_patch_max, floor(L/16)) is Literal(x block),
                   otherwise Patch(periodic(y block), mismatches); blocks are
                   concatenated in order (zero-error patches collapse).
  global           Patch(periodic(y), all mismatches); only the floor(n/16) gate.
"""
from __future__ import annotations

from bisect import bisect_left

from .candidates import positions_of
from .model import Node, NodeFactory


def original_grid(n: int, grid, period_max: int) -> tuple[int, ...]:
    """The original noisy-period grid intersected with 1..min(period_max, n//2)."""
    top = min(period_max, n // 2)
    return tuple(p for p in grid if 1 <= p <= top)


def dense_grid(n: int, period_max: int) -> tuple[int, ...]:
    return tuple(range(1, min(period_max, n // 2) + 1))


def first_block_word(x: str, p: int) -> str:
    return x[:p]


def consensus_word(x: str, p: int) -> str:
    """Per-phase majority over x[j::p]; ties choose 0."""
    out = []
    for j in range(p):
        col = x[j::p]
        out.append("1" if 2 * col.count("1") > len(col) else "0")
    return "".join(out)


def tile(w: str, n: int) -> str:
    return (w * (n // len(w) + 1))[:n]


class Residual:
    """Mismatch count and (when admissible) positions between x and a template."""

    __slots__ = ("word", "y", "count", "positions")

    def __init__(self, x: str, x_int: int, word: str, limit: int) -> None:
        n = len(x)
        self.word = word
        self.y = tile(word, n)
        diff = x_int ^ int(self.y, 2)
        self.count = diff.bit_count()
        self.positions = None
        if self.count <= limit:
            self.positions = positions_of(format(diff, "b").zfill(n), "1") if self.count else []


def periodic(f: NodeFactory, b: str, p: int) -> Node:
    q, t = divmod(len(b), p)
    if q < 2:
        return f.literal(b)
    body = f.repeat(f.literal(b[:p]), q)
    return f.concat([body, f.literal(b[-t:])]) if t else body


def local_proposal(f: NodeFactory, x: str, res: Residual, p: int, block: int,
                   patch_max: int, divisor: int) -> Node:
    n = len(x)
    pos = res.positions
    kids = []
    for a in range(0, n, block):
        b = min(n, a + block)
        L = b - a
        lo, hi = bisect_left(pos, a), bisect_left(pos, b)
        local = [q - a for q in pos[lo:hi]]
        if len(local) > min(patch_max, L // divisor):
            kids.append(f.literal(x[a:b]))
        else:
            kids.append(f.patch(periodic(f, res.y[a:b], p), local))
    return f.concat(kids)


def global_proposal(f: NodeFactory, res: Residual, p: int) -> Node:
    return f.patch(periodic(f, res.y, p), res.positions)
