"""occurrence_geometry.py  (Level 5)

The behaviour table of the representation-free pivots: the arithmetic of where the
salient points occur along time and value.

Three process columns, each a named, closed-form quantity:

  * FRACTAL DIMENSION D.  The number of pivots at reversal scale theta scales as
    N(theta) ~ theta**(-D).  D is read as minus the slope of log N against log
    theta.  It is a scale-free descriptor of how salient points proliferate as the
    scale is refined: a smooth trend gives D -> 1, a Brownian (quadratic-variation)
    path gives D = 2, a rougher path gives D > 2.  It replaces the binarisation's
    place-value column with a genuine self-similarity exponent.

  * BENFORD LAW on the gaps.  The leading significant digit of the occurrence gaps
    (dt and |dv|) follows P(d) = log10(1 + 1/d) when the process is scale-
    invariant.  The deviation from that log law (a total-variation distance) is a
    single number that says how far the occurrence gaps are from pure
    scale-invariance -- the number-theoretic signature the two-axis picture points
    at.

  * INTRINSIC-TIME MEMORY.  Re-indexing time by pivot events (each leg is one
    tick), the memory of the driver (the |dv| sequence) and of the clock (the dt
    sequence) are measured separately.  Where the memory concentrates -- in how big
    the moves are, or in how long they take -- localises the information.
"""

from __future__ import annotations

import math

from pivots import directional_change_pivots, legs


# ---------------------------------------------------------------------------
# Fractal dimension from the pivot-count scaling law
# ---------------------------------------------------------------------------

def pivot_count_scaling(series: list[float], thetas: list[float]) -> list[tuple[float, int]]:
    return [(t, len(directional_change_pivots(series, t))) for t in thetas]


def fractal_dimension(series: list[float], thetas: list[float]) -> dict:
    """Fit N(theta) ~ theta**(-D) in log-log; return D and the fit quality R^2."""
    pts = [(t, n) for t, n in pivot_count_scaling(series, thetas) if n >= 2]
    if len(pts) < 3:
        return {"D": float("nan"), "r2": 0.0, "points": pts}
    xs = [math.log(t) for t, _ in pts]
    ys = [math.log(n) for _, n in pts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx if sxx else 0.0
    intercept = my - slope * mx
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
    return {"D": -slope, "r2": r2, "points": pts}


# ---------------------------------------------------------------------------
# Benford's law on the occurrence gaps
# ---------------------------------------------------------------------------

BENFORD = [math.log10(1 + 1 / d) for d in range(1, 10)]


def leading_digit(x: float) -> int:
    x = abs(x)
    if x == 0:
        return 0
    while x < 1:
        x *= 10
    while x >= 10:
        x /= 10
    return int(x)


def benford_distance(values: list[float]) -> dict:
    """Total-variation distance of the leading-digit histogram from Benford."""
    counts = [0] * 9
    tot = 0
    for v in values:
        d = leading_digit(v)
        if 1 <= d <= 9:
            counts[d - 1] += 1
            tot += 1
    if tot == 0:
        return {"tv": float("nan"), "n": 0, "hist": counts}
    freq = [c / tot for c in counts]
    tv = 0.5 * sum(abs(f - b) for f, b in zip(freq, BENFORD))
    return {"tv": tv, "n": tot, "hist": freq}


# ---------------------------------------------------------------------------
# Intrinsic-time memory: where does the structure live, clock or driver?
# ---------------------------------------------------------------------------

def _autocorr1(xs: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs)
    if var == 0:
        return 0.0
    return sum((xs[t] - m) * (xs[t + 1] - m) for t in range(n - 1)) / var


def intrinsic_time_memory(series: list[float], theta: float) -> dict:
    """Lag-1 memory of the driver (|dv|) and the clock (dt) in event time."""
    lg = legs(directional_change_pivots(series, theta))
    if len(lg) < 4:
        return {"n_legs": len(lg), "driver_ac1": 0.0, "clock_ac1": 0.0}
    dt = [float(a) for a, _ in lg]
    dv = [abs(b) for _, b in lg]
    return {"n_legs": len(lg),
            "driver_ac1": _autocorr1(dv),   # do big moves follow big moves?
            "clock_ac1": _autocorr1(dt)}    # do long waits follow long waits?
