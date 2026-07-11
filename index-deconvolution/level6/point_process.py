"""point_process.py  (Level 6)

Treat the pivot times as a point process and measure how its events cluster along
the index, across scales.

The central object is the Fano factor F(T) = Var[N_T] / Mean[N_T], the
variance-to-mean ratio of the event count in windows of length T.  For a Poisson
or renewal process (independent inter-event times) F(T) tends to a constant, so
log F(T) against log T is flat.  For a self-similar clustered point process F(T)
grows as a power law F(T) ~ T**alpha, and the exponent alpha (0 < alpha < 1) is a
scale-free measure of the clustering; it corresponds to a count Hurst exponent
H = (1 + alpha) / 2.  Measuring alpha at several reversal scales theta tests whether
the clustering is itself scale-invariant -- the intra-pivot self-similarity.

A generalised Hurst exponent h(q) of the activity signal (the windowed event count)
probes whether one exponent suffices (monofractal, h(q) constant) or a spectrum is
needed (multifractal, h(q) decreasing in q).
"""

from __future__ import annotations

import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "level5"))

from pivots import directional_change_pivots  # noqa: E402


def pivot_indices(series: list[float], theta: float) -> list[int]:
    return [p.index for p in directional_change_pivots(series, theta)]


def _loglog_slope(xs: list[float], ys: list[float]) -> tuple[float, float]:
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx if sxx else 0.0
    intercept = my - slope * mx
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
    return slope, r2


def fano_exponent(times: list[int], n: int, window_sizes: list[int]) -> dict:
    """Fit F(T) ~ T**alpha over the given window sizes; return alpha and R^2."""
    tset = times
    xs, ys = [], []
    for T in window_sizes:
        nb = n // T
        if nb < 4:
            continue
        counts = [0] * nb
        for t in tset:
            k = t // T
            if k < nb:
                counts[k] += 1
        mean = statistics.mean(counts)
        if mean <= 0:
            continue
        f = statistics.pvariance(counts) / mean
        if f > 0:
            xs.append(math.log(T))
            ys.append(math.log(f))
    if len(xs) < 3:
        return {"alpha": float("nan"), "r2": 0.0}
    slope, r2 = _loglog_slope(xs, ys)
    return {"alpha": slope, "r2": r2, "count_hurst": (1 + slope) / 2}


def activity_signal(series: list[float], theta: float, window: int) -> list[int]:
    """Non-overlapping windowed pivot count: the clock's activity along the index."""
    piv = set(pivot_indices(series, theta))
    return [sum(1 for t in range(i, i + window) if t in piv)
            for i in range(0, len(series) - window + 1, window)]


def _dfa_fluctuation(signal: list[float], scale: int, q: float) -> float:
    """q-th order detrended fluctuation of a profile at a given scale."""
    prof = []
    acc = 0.0
    mean = statistics.mean(signal)
    for x in signal:
        acc += x - mean
        prof.append(acc)
    nseg = len(prof) // scale
    if nseg < 1:
        return 0.0
    flucts = []
    for s in range(nseg):
        seg = prof[s * scale:(s + 1) * scale]
        # linear detrend
        xs = list(range(scale))
        mx = statistics.mean(xs)
        my = statistics.mean(seg)
        sxx = sum((x - mx) ** 2 for x in xs)
        b = sum((x - mx) * (y - my) for x, y in zip(xs, seg)) / sxx if sxx else 0.0
        a = my - b * mx
        resid = [seg[i] - (a + b * i) for i in range(scale)]
        f2 = statistics.mean(r * r for r in resid)
        if f2 > 0:                       # drop perfectly flat segments (needed for q<0)
            flucts.append(f2)
    if len(flucts) < 2:
        return 0.0
    if q == 0:
        return math.exp(0.5 * statistics.mean(math.log(f) for f in flucts))
    return (statistics.mean(f ** (q / 2) for f in flucts)) ** (1 / q)


def generalised_hurst(signal: list[float], qs: list[float],
                      scales: list[int]) -> dict[float, float]:
    """MFDFA generalised Hurst h(q): slope of log F_q(s) against log s."""
    out = {}
    for q in qs:
        xs, ys = [], []
        for s in scales:
            if len(signal) // s < 2:
                continue
            fq = _dfa_fluctuation(signal, s, q)
            if fq > 0:
                xs.append(math.log(s))
                ys.append(math.log(fq))
        out[q] = _loglog_slope(xs, ys)[0] if len(xs) >= 3 else float("nan")
    return out
