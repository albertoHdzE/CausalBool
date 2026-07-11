"""pivots.py  (Level 5)

Representation-free pivots: describe a sequence not by the digits of its values
but by where its salient points occur along two axes -- time and value.

The atomic construction is the directional change.  Walking the sequence, we hold
the current direction and the running extreme reached in that direction.  When the
sequence reverses away from that extreme by at least a relative amount theta, a
pivot is confirmed at the extreme, and the direction flips.  The result is the
sequence of confirmed turning points at scale theta.  Between two pivots the series
is (net) monotone: a leg.  Each leg carries two occurrence coordinates,

    dt  = the index gap  (how long the leg lasted),
    dv  = the value gap  (how far, and in which direction, the value moved),

and nothing else -- no binarisation, no base, no representation of the numbers.
The whole series becomes a list of (dt, dv) pairs, the object the two-axis picture
projects onto its time and value axes.

The threshold is relative (|x / extreme - 1| >= theta), so the construction is
invariant to any multiplicative rescaling of the sequence: pivots of x and of a*x
are identical.  This is the scale-invariance that makes the description agnostic,
and the same invariance that underlies Benford's law.
"""

from __future__ import annotations

from typing import NamedTuple


class Pivot(NamedTuple):
    index: int      # position in the sequence
    value: float    # value at the pivot
    kind: int       # +1 for a local maximum (a peak), -1 for a local minimum


def directional_change_pivots(series: list[float], theta: float) -> list[Pivot]:
    """Confirmed turning points at relative reversal scale ``theta`` (theta > 0).

    A downward pivot (a peak) is confirmed at the running high once the series has
    fallen from that high by a factor theta; an upward pivot (a trough) symmetric.
    The first pivot's direction is set by the first confirmed reversal.  Positive
    series only (relative threshold); for a general series pre-map to positive or
    use an absolute threshold in units of the series' own scale.
    """
    if not series:
        return []
    pivots: list[Pivot] = []
    mode = 0                      # 0 unknown, +1 seeking a peak (going up), -1 seeking a trough
    ext_val = series[0]
    ext_idx = 0
    for i in range(1, len(series)):
        x = series[i]
        if mode >= 0 and x > ext_val:          # extend an up-run
            ext_val, ext_idx = x, i
            mode = 1
        elif mode <= 0 and x < ext_val:        # extend a down-run
            ext_val, ext_idx = x, i
            mode = -1
        if mode == 1 and ext_val > 0 and x <= ext_val * (1 - theta):
            pivots.append(Pivot(ext_idx, ext_val, +1))    # peak confirmed
            mode, ext_val, ext_idx = -1, x, i
        elif mode == -1 and ext_val > 0 and x >= ext_val * (1 + theta):
            pivots.append(Pivot(ext_idx, ext_val, -1))    # trough confirmed
            mode, ext_val, ext_idx = 1, x, i
    return pivots


def legs(pivots: list[Pivot]) -> list[tuple[int, float]]:
    """The (dt, dv) occurrence coordinates between consecutive pivots.

    dt is the index gap (a positive integer); dv is the signed value change.  This
    is the representation-free encoding of the series between its salient points.
    """
    return [(pivots[i + 1].index - pivots[i].index,
             pivots[i + 1].value - pivots[i].value)
            for i in range(len(pivots) - 1)]


def pivot_times(pivots: list[Pivot]) -> list[int]:
    return [p.index for p in pivots]


def pivot_values(pivots: list[Pivot]) -> list[float]:
    return [p.value for p in pivots]
