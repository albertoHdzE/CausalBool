"""behaviour.py  (Level 14)

Behaviour tables and behaviour formulae for the BUY and the SELL patterns.

The assessor's picture: a market's turning points are two interleaved patterns -- the
buy pattern (the troughs, where a perfect entry falls) and the sell pattern (the peaks,
where a perfect exit falls). Each is an occurrence set, and the programme's task is to
build its behaviour table (the arithmetic of where its events fall) and read off a
behaviour formula (a compressed generator), exactly as it does for a cellular automaton.

Two regimes, and the honest distinction between them:

  * The controlled regime (a periodic or geometric occurrence set) admits an EXACT
    behaviour formula: the gaps are constant (a period) or their ratios are constant (a
    geometric law). The behaviour table's ratio column is flat, and three symbols
    reproduce the set to the last event.

  * A market occurrence set does NOT admit such an exact formula -- its gaps are noisy,
    the ratio column scatters -- but it admits a STATISTICAL behaviour formula: the
    three-number self-exciting Hawkes generator (Level 9), which compresses hundreds of
    events into three numbers, regenerates their clustering, and forecasts the next
    event out of sample. This module builds and tests both readings, so the notebook can
    show, probe and test the map rigorously and report which formula each pattern obeys.

Standard library only; reuses the Level 9 Hawkes and Level 6 Fano exponent.
"""

from __future__ import annotations

import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "level5"))
sys.path.insert(0, os.path.join(ROOT, "level6"))
sys.path.insert(0, os.path.join(ROOT, "level9"))

from pivots import directional_change_pivots  # noqa: E402
from point_process import fano_exponent  # noqa: E402
from hawkes import fit_hawkes, simulate, oos_loglik, poisson_loglik  # noqa: E402

WINDOWS = [10, 20, 40, 80, 160, 320]


def buy_sell_occurrences(series: list[float], theta: float) -> tuple[list[int], list[int]]:
    """The buy pattern (trough times) and the sell pattern (peak times)."""
    piv = directional_change_pivots(series, theta)
    buys = [p.index for p in piv if p.kind == -1]
    sells = [p.index for p in piv if p.kind == +1]
    return buys, sells


def behaviour_table(times: list[int], max_rows: int | None = None) -> list[dict]:
    """The behaviour table of an occurrence set.

    Columns: ordinal n; position t_n; gap g_n = t_n - t_{n-1}; ratio r_n = g_n / g_{n-1}.
    A constant gap column is a period; a constant ratio column is a geometric,
    self-similar law -- the exact behaviour formulae of the controlled regime.
    """
    rows = []
    for n in range(len(times)):
        gap = times[n] - times[n - 1] if n >= 1 else None
        prev_gap = times[n - 1] - times[n - 2] if n >= 2 else None
        ratio = (gap / prev_gap) if (gap is not None and prev_gap) else None
        rows.append({"ordinal": n + 1, "position": times[n], "gap": gap, "ratio": ratio})
    return rows[:max_rows] if max_rows else rows


def exact_formula_score(times: list[int]) -> dict:
    """How close is the occurrence set to an EXACT (periodic or geometric) formula?

    Returns the coefficient of variation of the gaps (0 = perfectly periodic) and of the
    gap ratios (0 = perfectly geometric); ``exact`` is True if either is near zero. A
    market scores high (no exact formula); a periodic or geometric control scores ~0.
    """
    gaps = [times[i + 1] - times[i] for i in range(len(times) - 1)]
    gaps = [g for g in gaps if g > 0]
    if len(gaps) < 3:
        return {"cv_gaps": float("nan"), "cv_ratios": float("nan"), "exact": False}
    mg = statistics.mean(gaps)
    cv_gaps = statistics.pstdev(gaps) / mg if mg else float("nan")
    ratios = [gaps[i + 1] / gaps[i] for i in range(len(gaps) - 1) if gaps[i] > 0]
    mr = statistics.mean(ratios) if ratios else float("nan")
    cv_ratios = (statistics.pstdev(ratios) / mr) if ratios and mr else float("nan")
    exact = (cv_gaps < 0.05) or (cv_ratios < 0.05)
    return {"cv_gaps": cv_gaps, "cv_ratios": cv_ratios, "exact": exact}


def hawkes_formula(times: list[int], T: float) -> dict:
    """The three-number statistical behaviour formula (mu, alpha, beta)."""
    return fit_hawkes([float(t) for t in times], T)


def compression(times: list[int], T: float) -> dict:
    """Description length of the formula versus of the raw occurrence set, in bits.

    The raw set needs ~ n * log2(T) bits (each event's position). The Hawkes formula
    needs three numbers (~ 3 * 32 bits). The ratio shows the compression.
    """
    n = len(times)
    raw_bits = n * math.log2(T) if T > 1 else 0.0
    formula_bits = 3 * 32.0
    return {"raw_bits": raw_bits, "formula_bits": formula_bits,
            "ratio": raw_bits / formula_bits if formula_bits else 0.0, "n_events": n}


def _ecdf_ks(a: list[float], b: list[float]) -> float:
    """Two-sample Kolmogorov-Smirnov statistic (max CDF gap)."""
    if not a or not b:
        return 1.0
    sa, sb = sorted(a), sorted(b)
    grid = sorted(set(sa + sb))
    na, nb = len(sa), len(sb)
    import bisect
    d = 0.0
    for x in grid:
        fa = bisect.bisect_right(sa, x) / na
        fb = bisect.bisect_right(sb, x) / nb
        d = max(d, abs(fa - fb))
    return d


def regeneration(times: list[int], T: float, fit: dict, seed: int = 1) -> dict:
    """Simulate the formula and compare with the real occurrence set.

    Returns the KS distance between real and simulated inter-event gaps, and the Fano
    clustering exponent of each. A good formula matches both.
    """
    sim = simulate(fit["mu"], fit["alpha"], fit["beta"], T, seed=seed)
    real_gaps = [float(times[i + 1] - times[i]) for i in range(len(times) - 1)]
    sim_i = sorted(int(x) for x in sim)
    sim_gaps = [float(sim_i[i + 1] - sim_i[i]) for i in range(len(sim_i) - 1)]
    real_fano = fano_exponent(list(times), int(T), WINDOWS).get("alpha", float("nan"))
    sim_fano = fano_exponent(sim_i, int(T), WINDOWS).get("alpha", float("nan"))
    return {"ks_gaps": _ecdf_ks(real_gaps, sim_gaps),
            "real_fano": real_fano, "sim_fano": sim_fano, "sim_events": len(sim)}


def oos_forecast(times: list[int], T: float, train_frac: float = 0.7) -> dict:
    """Held-out log-likelihood gain of the Hawkes formula over Poisson, per event."""
    t = [float(x) for x in times]
    T_tr = T * train_frac
    train = [x for x in t if x <= T_tr]
    if len(train) < 10 or len(t) - len(train) < 5:
        return {"oos_gain": float("nan"), "n_test": 0}
    ftr = fit_hawkes(train, T_tr)
    h_ll, n_test = oos_loglik(t, T, T_tr, ftr["mu"], ftr["alpha"], ftr["beta"])
    mu_p = len(train) / T_tr
    p_ll = poisson_loglik(t, T, mu_p) - poisson_loglik(train, T_tr, mu_p)
    return {"oos_gain": (h_ll - p_ll) / n_test if n_test else float("nan"), "n_test": n_test}


def intensity(times: list[int], fit: dict, grid: list[float]) -> list[float]:
    """The fitted Hawkes intensity lambda(t) on a grid -- for the 'match' plot."""
    mu, alpha, beta = fit["mu"], fit["alpha"], fit["beta"]
    out = []
    ts = [float(t) for t in times]
    for g in grid:
        s = sum(math.exp(-beta * (g - ti)) for ti in ts if ti < g)
        out.append(mu + alpha * s)
    return out
