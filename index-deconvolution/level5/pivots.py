"""pivots.py  (Level 5)

Representation-free pivots: describe a sequence not by the digits of its values
but by where its salient points occur along two axes -- time and value.

WHAT A PIVOT IS (settled 2026-08-22; the source of truth is
``GOVERNANCE/GLOSSARY.md`` (in-repo synchronized copy; canonical at ``series-deconvolution/GLOSSARY.md``) section 1, which outranks every paper and notebook
in this programme on a definition):

    A PIVOT is a position that a CAUSAL process -- one with no look-ahead --
    reproduces EXACTLY.  What no such process reaches is the RESIDUAL.

In finance the answer key is the *oracle*, the in-hindsight optimal buy/sell schedule
under round-trip cost c, computed WITH the future visible (``level10/oracle.py``).  A
FINANCIAL PIVOT is an oracle action point that a causal one-pass process recovers
exactly; the RESIDUAL is the part of the answer key that requires the future.

WHAT FOLLOWS IS THE RECOVERY METHOD, NOT THE DEFINITION.  This module implements the
directional-change construction, which is *how* pivots are recovered at scale theta --
run it with theta = c and it returns financial pivots.  Defining a pivot as "whatever
this walk returns" is logged as confusion source #1 in ``GOVERNANCE/GLOSSARY.md`` section 2, and
this docstring is one of the two places that made that error.  The distinction matters
because the walk is a procedure that always returns *something*, whereas the definition
carries a claim that can fail: that the returned positions are exactly right.

Do not pair *pivot* with *sumandos*.  ``pivot``/``residual`` is a partition by causal
reachability and is LOSSY.  ``decimal family``/``sumandos`` is the Boolean indexing
method's compressed form and is LOSSLESS -- Dec(L,S) = {l+s} reconstructs the repertoire
exactly.  There is no residual in the Boolean method and no sumando in finance
(``GOVERNANCE/GLOSSARY.md`` section 1c, confusion source #5).

THE CONSTRUCTION.  Walking the sequence, we hold the current direction and the running
extreme reached in that direction.  When the sequence reverses away from that extreme by
at least a relative amount theta, a pivot is confirmed at the extreme, and the direction
flips.  The result is the sequence of confirmed turning points at scale theta -- causal
by construction: the walk never reads an index ahead of the one it is standing on, which
is precisely what makes its output eligible to be called pivots.  Between two pivots the series
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
    """Causal, one-pass RECOVERY of the pivots at relative reversal scale ``theta``.

    Not the definition -- see the module docstring.  A pivot is a position a causal
    process reproduces exactly; run at ``theta = c`` this walk recovers the financial
    pivots, the subset of the oracle's action points that causality can reach.

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
