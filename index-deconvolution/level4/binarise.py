"""binarise.py  (Level 4)

Agnostic multi-bit binarisation of an arbitrary numeric sequence.

The protocol's neutral binarisation writes each value in a fixed number of bits,
turning a one-dimensional sequence of numbers into a two-dimensional binary array:
one axis is the index (position along the sequence), the other is the bit position
within a value.  Each bit position is then a candidate unit whose occurrence set
(the positions where that bit is 1) can be examined for arithmetic structure.

Nothing here knows what the numbers mean.  The only operations used are order
statistics (rank / quantile) and the first difference, both of which are
scale-free and domain-free.  Several binarisations are provided precisely because
the method must not depend on any one of them; the unit-survival test decides
which bit columns carry structure.
"""

from __future__ import annotations

from typing import Callable


def _rank_bits(values: list[float], nbits: int) -> list[list[int]]:
    """Map each value to a ``nbits``-bit integer by its rank, MSB first.

    Rank (quantile) coding is scale-free: only the order of the values is used, so
    the result is invariant to any monotone rescaling of the sequence.  The most
    significant bit splits the sequence at its median, the next bits refine within
    each half, and so on -- a neutral positional code.
    """
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    rank = [0] * n
    for r, i in enumerate(order):
        # quantile in [0, 1) mapped to an integer in [0, 2**nbits)
        rank[i] = min(2 ** nbits - 1, int((r / n) * (2 ** nbits)))
    cols = [[(rank[i] >> (nbits - 1 - b)) & 1 for i in range(n)]
            for b in range(nbits)]
    return cols  # cols[b] is bit column b (b=0 is the most significant)


def _gray_bits(values: list[float], nbits: int) -> list[list[int]]:
    """Rank code in reflected Gray code: successive magnitude bands differ in one
    bit, so each bit column is a cleaner band-membership unit than in plain binary
    (where a small change can flip several bits at a band boundary)."""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    gray = [0] * n
    for r, i in enumerate(order):
        v = min(2 ** nbits - 1, int((r / n) * (2 ** nbits)))
        gray[i] = v ^ (v >> 1)
    return [[(gray[i] >> (nbits - 1 - b)) & 1 for i in range(n)] for b in range(nbits)]


def magnitude_bands(values: list[float], nbits: int = 3, scale_free: bool = True,
                    gray: bool = True) -> list[list[int]]:
    """Bit columns of the step-size magnitude at several resolutions (Gray by
    default).  Column 0 is the coarsest (above/below median); deeper columns
    resolve finer bands within each half."""
    d = relative_difference(values) if scale_free else first_difference(values)
    mag = [abs(x) for x in d]
    return _gray_bits(mag, nbits) if gray else _rank_bits(mag, nbits)


def first_difference(values: list[float]) -> list[float]:
    """Neutral detrending: x[t] - x[t-1].  Length shrinks by one.

    Invariant to an affine rescaling x -> a x + b of the whole sequence, but NOT
    to multiplicative growth within the sequence: if the values drift over orders
    of magnitude, the additive difference inherits that drift.  For such a sequence
    use ``relative_difference`` instead, and see ``trend_contamination``.
    """
    return [values[t] - values[t - 1] for t in range(1, len(values))]


def relative_difference(values: list[float]) -> list[float]:
    """Scale-free difference (x[t] - x[t-1]) / x[t-1] for a positive sequence.

    This is the canonical scale-invariant analogue of the first difference: it is
    invariant to any multiplicative rescaling, so it does not inherit a secular
    growth of the values.  It is defined only where the previous value is non-zero;
    a zero divisor contributes a zero difference.  Nothing here is domain-specific
    -- it is simply the right neutral operation for a multiplicative sequence, the
    way the plain first difference is right for an additive one.
    """
    out = []
    for t in range(1, len(values)):
        prev = values[t - 1]
        out.append((values[t] - prev) / prev if prev != 0 else 0.0)
    return out


def trend_contamination(values: list[float]) -> float:
    """Guard against a magnitude unit that merely tracks the level (a trend).

    Returns the difference between the fraction of large additive steps in the
    second half of the sequence and in the first half.  For a stationary
    magnitude process this is near zero; a value near +/-0.5 means the "large
    move" unit is really a step function following the level, and the additive
    difference must be replaced by the relative one.
    """
    d = [abs(x) for x in first_difference(values)]
    if not d:
        return 0.0
    import statistics as _st
    m = _st.median(d)
    bits = [1 if x > m else 0 for x in d]
    h = len(bits) // 2
    if h == 0:
        return 0.0
    return sum(bits[h:]) / (len(bits) - h) - sum(bits[:h]) / h


def binarisations(values: list[float], nbits: int = 3) -> dict[str, list[list[int]]]:
    """Return several admissible binarisations of a raw numeric sequence.

    Each entry maps a name to a list of bit columns (candidate units).  The names
    describe the construction only; they carry no domain meaning.

      * ``raw``      -- rank bits of the values themselves (captures level/trend).
      * ``diff_sign``-- one column: the sign of the first difference.
      * ``diff_mag`` -- rank bits of the magnitude of the first difference
                        (captures the size of the step, ignoring its direction).

    The ``diff`` binarisations are one position shorter than ``raw`` because the
    first difference consumes one sample; callers that compare across
    binarisations should align on the shorter length.
    """
    out: dict[str, list[list[int]]] = {}
    out["raw"] = _rank_bits(values, nbits)
    d = first_difference(values)
    out["diff_sign"] = [[1 if x > 0 else 0 for x in d]]
    out["diff_mag"] = _rank_bits([abs(x) for x in d], nbits)
    return out


def top_magnitude_bit(values: list[float], scale_free: bool = False) -> list[int]:
    """The single most significant magnitude bit of the step size.

    1 where the step size is above its own median, 0 otherwise.  This is the
    coarsest volatility unit and the one whose occurrence set is studied in detail.
    With ``scale_free`` the relative difference is used, so the unit does not
    inherit a multiplicative trend in the values; use it for sequences that grow
    over orders of magnitude (see ``trend_contamination``).
    """
    d = relative_difference(values) if scale_free else first_difference(values)
    return _rank_bits([abs(x) for x in d], nbits=1)[0]


def sign_bit(values: list[float]) -> list[int]:
    """The sign unit of the first difference (the direction bit)."""
    return binarisations(values, nbits=1)["diff_sign"][0]
