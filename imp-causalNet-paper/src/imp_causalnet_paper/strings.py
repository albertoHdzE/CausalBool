"""Figure 1A-B: deconvolution of a string built from two generating mechanisms.

Section 3.1 of arXiv:1802.09904v8 gives the string verbatim::

    0101010101010101010101010101010101010101010101010101110100101010100000001001100111100110000011100110

the first half being ``01`` repeated 25 times (the "regular segment", blue in
Fig. 1A) and the second half a random-looking segment (red).  Fig. 1B repeats the
analysis on the reversal, to show that "the methods are invariant to direction,
given that the algorithmic probability and complexity of a string and its
reversal ... preserve the complexity and mechanistic origin of each object".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .complexity import bdm_1d

__all__ = ["PAPER_STRING", "REGULAR_SEGMENT", "StringFootprint", "string_footprint"]

PAPER_STRING = (
    "0101010101010101010101010101010101010101010101010101"
    "110100101010100000001001100111100110000011100110"
)
assert len(PAPER_STRING) == 100 and PAPER_STRING[:50] == "01" * 25

#: The first 50 characters, ``'01'`` repeated 25 times.
REGULAR_SEGMENT = "01" * 25


@dataclass
class StringFootprint:
    bits: str
    values: np.ndarray
    base: float

    @property
    def ranking(self) -> list[tuple[int, float]]:
        order = np.argsort(self.values, kind="stable")[::-1]
        return [(int(i) + 1, float(self.values[i])) for i in order]


def string_footprint(bits: str | list[int]) -> StringFootprint:
    """Per-position information value ``BDM(s) - BDM(s with bit i flipped)``.

    This is the one-dimensional counterpart of ``CausalDeconvolution``: the same
    single-symbol perturbation, evaluated with the 12-bit CTM table that the
    paper specifies for strings.
    """
    if isinstance(bits, str):
        arr = np.array([int(c) for c in bits], dtype=int)
    else:
        arr = np.asarray(bits, dtype=int)
    base = bdm_1d(arr)
    values = np.empty(arr.size, dtype=float)
    for i in range(arr.size):
        arr[i] ^= 1
        values[i] = base - bdm_1d(arr)
        arr[i] ^= 1
    return StringFootprint("".join(str(int(b)) for b in arr), values, base)
