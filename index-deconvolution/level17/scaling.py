"""scaling.py  (Level 17)

Expanding the pattern-discovery method: a rigorous constant/law hunt in the clock.

The original method did not stop at the (n+1)/n ratio -- each canonical gate added a
different lens (band unions, parity partitions, Hamming-weight thresholds, place-values,
complements, the phi bit-reversal). In that spirit we do not replay a gate; we hunt, by
counting and measuring, for the stable relationships the market clock actually carries,
and we hold every candidate to a null so numerology cannot masquerade as a law.

Three representation-free measurements, plus honest scepticism about a fourth:

  1. the self-similarity exponent alpha (Fano F(T) ~ T^alpha): is it a stable constant?
  2. the inter-turn gap LAW: exponential (renewal), lognormal, or power-law? fit by
     maximum likelihood and chosen by AIC; the shuffle should read exponential.
  3. the proliferation exponent E (turn count N(theta) ~ theta^-E across reversal
     scales): a scaling law of the directional-change construction.
  4. (kept as a caution) the nested ratio r of Level 16 is model- and grid-dependent,
     unlike the exponents above; it is not a representation-free constant.

Standard library only; deterministic. MLE fits use closed forms (Clauset for the
power law).
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

from pivots import directional_change_pivots  # noqa: E402
from point_process import pivot_indices, fano_exponent  # noqa: E402

WINDOWS = [10, 20, 40, 80, 160, 320]


def gaps_of(events: list[int]) -> list[int]:
    return [events[i + 1] - events[i] for i in range(len(events) - 1)
            if events[i + 1] - events[i] > 0]


def _ll_exponential(x: list[float]) -> tuple[float, dict]:
    m = statistics.mean(x)
    if m <= 0:
        return -1e18, {}
    rate = 1.0 / m
    ll = sum(math.log(rate) - rate * xi for xi in x)
    return ll, {"rate": rate, "k": 1}


def _ll_lognormal(x: list[float]) -> tuple[float, dict]:
    lx = [math.log(xi) for xi in x if xi > 0]
    if len(lx) < 2:
        return -1e18, {}
    mu = statistics.mean(lx)
    sig = statistics.pstdev(lx)
    if sig <= 0:
        return -1e18, {}
    ll = sum(-math.log(xi) - math.log(sig * math.sqrt(2 * math.pi))
             - (math.log(xi) - mu) ** 2 / (2 * sig * sig) for xi in x if xi > 0)
    return ll, {"mu": mu, "sigma": sig, "k": 2}


def _ll_powerlaw(x: list[float], xmin: float | None = None) -> tuple[float, dict]:
    xs = sorted(x)
    if xmin is None:
        xmin = xs[0]
    xt = [xi for xi in x if xi >= xmin]
    n = len(xt)
    if n < 5:
        return -1e18, {}
    s = sum(math.log(xi / xmin) for xi in xt)
    if s <= 0:
        return -1e18, {}
    alpha = 1.0 + n / s                      # Clauset MLE
    ll = sum(math.log((alpha - 1) / xmin) - alpha * math.log(xi / xmin) for xi in xt)
    return ll, {"alpha": alpha, "xmin": xmin, "k": 1, "n_tail": n}


def law_of_gaps(x: list[float]) -> dict:
    """Fit exponential / lognormal / power-law to a gap sample; choose by AIC."""
    x = [xi for xi in x if xi > 0]
    if len(x) < 20:
        return {"law": "insufficient", "n": len(x)}
    fits = {}
    for name, fn in (("exponential", _ll_exponential), ("lognormal", _ll_lognormal),
                     ("powerlaw", _ll_powerlaw)):
        ll, par = fn(x)
        k = par.get("k", 1)
        fits[name] = {"loglik": ll, "aic": 2 * k - 2 * ll, "params": par}
    law = min(fits, key=lambda nm: fits[nm]["aic"])
    return {"law": law, "aic": {nm: fits[nm]["aic"] for nm in fits},
            "params": {nm: fits[nm]["params"] for nm in fits}, "n": len(x)}


def gap_law(events: list[int]) -> dict:
    """Fit exponential / lognormal / power-law to the gaps; choose by AIC.

    Returns the winning law, each model's AIC, and the fitted parameters. A renewal
    (memoryless) clock is exponential; a heavy-tailed clustered clock is lognormal or
    power-law.
    """
    x = [float(g) for g in gaps_of(events)]
    if len(x) < 20:
        return {"law": "insufficient", "n": len(x)}
    fits = {}
    for name, fn in (("exponential", _ll_exponential), ("lognormal", _ll_lognormal),
                     ("powerlaw", _ll_powerlaw)):
        ll, par = fn(x)
        k = par.get("k", 1)
        fits[name] = {"loglik": ll, "aic": 2 * k - 2 * ll, "params": par}
    law = min(fits, key=lambda nm: fits[nm]["aic"])
    return {"law": law, "aic": {nm: fits[nm]["aic"] for nm in fits},
            "params": {nm: fits[nm]["params"] for nm in fits}, "n": len(x)}


def proliferation_exponent(series: list[float], thetas: list[float]) -> dict:
    """Fit N(theta) ~ theta^-E across reversal scales; return E and R^2."""
    xs, ys = [], []
    for th in thetas:
        n = len(pivot_indices(series, th))
        if n > 0:
            xs.append(math.log(th))
            ys.append(math.log(n))
    if len(xs) < 3:
        return {"E": float("nan"), "r2": 0.0}
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxx = sum((a - mx) ** 2 for a in xs)
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    slope = sxy / sxx if sxx else 0.0
    inter = my - slope * mx
    ss_res = sum((b - (slope * a + inter)) ** 2 for a, b in zip(xs, ys))
    ss_tot = sum((b - my) ** 2 for b in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
    return {"E": -slope, "r2": r2}


def alpha_at(series: list[float], theta: float) -> float:
    return fano_exponent(pivot_indices(series, theta), len(series), WINDOWS).get("alpha", float("nan"))


# ---------------------------------------------------------------------------
# Universality by data collapse: one law + a per-stock scale, not a model per stock
# ---------------------------------------------------------------------------

def normalised_gaps(events: list[int]) -> list[float]:
    """Gaps rescaled by their own mean -- the per-stock scale removed (dimensionless)."""
    g = [float(x) for x in gaps_of(events)]
    if not g:
        return []
    m = statistics.mean(g)
    return [x / m for x in g] if m > 0 else []


def ecdf_ks(a: list[float], b: list[float]) -> float:
    """Two-sample Kolmogorov-Smirnov distance between two samples' CDFs."""
    if not a or not b:
        return 1.0
    import bisect
    sa, sb = sorted(a), sorted(b)
    grid = sorted(set(sa + sb))
    na, nb = len(sa), len(sb)
    d = 0.0
    for x in grid:
        d = max(d, abs(bisect.bisect_right(sa, x) / na - bisect.bisect_right(sb, x) / nb))
    return d


def collapse_test(per_stock_norm: list[list[float]]) -> dict:
    """Do the per-stock normalised gap distributions collapse onto one universal curve?

    Pools all normalised gaps into a reference, then measures each stock's KS distance to
    the pooled reference. Small, tight KS across stocks = a universal law with per-stock
    scale. Returns the pooled reference sample and the KS statistics.
    """
    pooled = [x for s in per_stock_norm for x in s]
    if not pooled:
        return {"mean_ks": float("nan"), "max_ks": float("nan"), "pooled": []}
    ks = [ecdf_ks(s, pooled) for s in per_stock_norm if s]
    return {"mean_ks": statistics.mean(ks) if ks else float("nan"),
            "max_ks": max(ks) if ks else float("nan"),
            "ks_all": ks, "pooled_n": len(pooled)}
