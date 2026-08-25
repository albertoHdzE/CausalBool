"""spectral.py  (Level 11)

The Fourier question, answered honestly.

The Fourier transform decomposes a signal into periodic sinusoids and exposes *linear*
structure -- periodicities and the autocorrelation spectrum. Two facts the programme
already established predict what it must find:

  * daily returns carry no linear predictability (direction is unforecastable), so
    their power spectrum should be flat -- white noise, no line to exploit;
  * the volatility clock is a self-similar long-memory process (fractal Fano exponent,
    Level 6), so the spectrum of the *activity/volatility* signal should be red,
    a 1/f^beta power law, with beta > 0.

So Fourier should split the series into an incompressible white part (the returns) and
a structured red part (the clock) -- confirming, in a second language, the same split
the pivot analysis found, and offering no periodic component to trade.

Standard library only: an iterative radix-2 Cooley-Tukey FFT, a Welch-averaged
periodogram, and a log-log slope for the 1/f fit.
"""

from __future__ import annotations

import cmath
import math
import statistics


def _fft(x: list[complex]) -> list[complex]:
    """Iterative radix-2 FFT; len(x) must be a power of two."""
    n = len(x)
    if n & (n - 1) != 0:
        raise ValueError("length must be a power of two")
    a = list(x)
    j = 0
    for i in range(1, n):                                 # bit-reversal permutation
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        ang = -2j * math.pi / length
        wlen = cmath.exp(ang)
        for i in range(0, n, length):
            w = 1 + 0j
            for k in range(i, i + length // 2):
                u = a[k]
                v = a[k + length // 2] * w
                a[k] = u + v
                a[k + length // 2] = u - v
                w *= wlen
        length <<= 1
    return a


def _next_pow2(n: int) -> int:
    p = 1
    while p < n:
        p <<= 1
    return p


def periodogram(signal: list[float]) -> tuple[list[float], list[float]]:
    """Welch-averaged power spectrum of a real signal (Hann window, 50% overlap).

    Returns (frequencies in cycles/sample over (0, 0.5], power). The signal is
    de-meaned; segments are the largest power of two that fits, averaged for a smooth,
    low-variance estimate.
    """
    x = [v - statistics.fmean(signal) for v in signal]
    n = len(x)
    seg = _next_pow2(max(16, n // 8))
    if seg > n:
        seg = _next_pow2(n) // 2 or 16
    step = seg // 2
    win = [0.5 - 0.5 * math.cos(2 * math.pi * i / (seg - 1)) for i in range(seg)]
    wnorm = sum(w * w for w in win)
    acc = [0.0] * (seg // 2)
    m = 0
    start = 0
    while start + seg <= n:
        chunk = [x[start + i] * win[i] for i in range(seg)]
        X = _fft([complex(v) for v in chunk])
        for f in range(1, seg // 2 + 1 - 1 + 1):
            if f < seg // 2:
                acc[f] += (X[f].real ** 2 + X[f].imag ** 2) / wnorm
        m += 1
        start += step
    if m == 0:
        return [], []
    freqs = [f / seg for f in range(1, seg // 2)]
    power = [acc[f] / m for f in range(1, seg // 2)]
    return freqs, power


def loglog_slope(freqs: list[float], power: list[float],
                 fmin: float = 0.0, fmax: float = 0.5) -> dict:
    """Slope of log(power) vs log(freq): the spectral exponent (0 = white, <0 = red)."""
    xs, ys = [], []
    for f, p in zip(freqs, power):
        if fmin < f <= fmax and p > 0:
            xs.append(math.log(f))
            ys.append(math.log(p))
    if len(xs) < 4:
        return {"slope": float("nan"), "r2": 0.0}
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx if sxx else 0.0
    inter = my - slope * mx
    ss_res = sum((y - (slope * x + inter)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
    return {"slope": slope, "r2": r2}
