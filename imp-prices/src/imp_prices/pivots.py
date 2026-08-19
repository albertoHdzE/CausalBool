"""Directional-change pivots, with the confirmation lag made explicit.

Phase 2 re-targets from the regime to the **clock**: not which way the price
moves, but *when* it reverses. The encoding is representation-free — a pivot is
defined by a relative move, so it does not depend on how the number is written —
and it is the encoding under which nine levels of the deconvolution programme
found structure that survived its nulls twelve times out of twelve.

**The trap this module exists to close.** A directional-change pivot happens at
one time and becomes *knowable* at a later one. In an upward phase the running
maximum is a candidate peak; it is only confirmed as a peak once the price has
fallen from it by the threshold. So every pivot carries two timestamps:

``extreme_time``
    when the turning point actually occurred.
``confirm_time``
    when an observer could first have known it did. Always strictly later.

Using ``extreme_time`` to build a forecasting feature is look-ahead bias. It is
the same error class GWP3 caught in the source dissertation, where decoding a
hold-out window as a whole produced a nominal one-month-ahead accuracy of 100 per
cent. Here it would be subtler and easier to miss, because the pivot is genuinely
in the past — it is only the *knowledge* of it that is not.

:func:`known_pivots` is the only accessor a forecasting feature may use, and
:func:`leak_opportunities` measures how often the distinction bites, so that the
guard is never vacuous.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Pivot:
    """One turning point, with the two timestamps kept apart."""

    extreme_index: int      #: when the turning point occurred
    confirm_index: int      #: when it could first have been known
    extreme_price: float
    kind: str               #: "peak" or "trough"

    @property
    def lag(self) -> int:
        return self.confirm_index - self.extreme_index


class NonPositivePriceError(ValueError):
    """Raised when a relative-threshold method is handed a non-positive price.

    Found in Phase 3 by rendering the series before quoting any number. WTI
    closed at **-37.63 on 2020-04-20**, and every part of this encoding breaks on
    it *silently*:

    * the downturn test ``p <= ext * (1 - theta)`` **inverts** when ``ext`` is
      negative, so the threshold sits above the extreme and any higher price
      "confirms" a reversal;
    * ``log`` of a non-positive price is undefined, so the return-shuffle null
      propagates nan and loses most of its path;
    * nothing raises. The detector returned 550 pivots including a *trough* at
      -37.63, with **seven pivots inside a fifteen-day window** around the print
      — a burst of spurious reversals biasing towards the clustering hypothesis
      under test.

    A method whose arithmetic assumes positivity must refuse non-positive input
    rather than produce numbers from it. Callers declare a handling policy
    explicitly via :func:`clean_prices`.
    """


def validate_prices(prices) -> np.ndarray:
    """Reject input a relative-threshold method cannot meaningfully process."""
    p = np.asarray(prices, dtype=float)
    if not np.all(np.isfinite(p)):
        raise NonPositivePriceError(
            f"{int((~np.isfinite(p)).sum())} non-finite prices; declare a policy")
    bad = np.where(p <= 0)[0]
    if len(bad):
        raise NonPositivePriceError(
            f"{len(bad)} non-positive price(s) at index {bad[:5].tolist()} "
            f"(min {p.min():.2f}). A relative threshold is undefined here; use "
            f"clean_prices() and report the exclusion.")
    return p


def clean_prices(prices, dates=None, pad: int = 0):
    """The declared policy: drop non-positive prices, and report what was dropped.

    ``pad`` additionally drops ``pad`` observations either side, so that a
    sensitivity check can show the result does not depend on the neighbourhood of
    the excluded print. Nothing is winsorised or interpolated: inventing a price
    where the market printed a negative one would put a number into the series
    that no one could have traded.
    """
    p = np.asarray(prices, dtype=float)
    keep = np.isfinite(p) & (p > 0)
    if pad:
        drop = ~keep
        for k in range(1, pad + 1):
            drop |= np.roll(drop, k) | np.roll(drop, -k)
        keep = ~drop
    report = dict(n_in=len(p), n_out=int(keep.sum()), n_dropped=int((~keep).sum()),
                  pad=pad,
                  dropped_dates=[str(d.date()) if hasattr(d, "date") else str(d)
                                 for d in (np.asarray(dates)[~keep] if dates is not None
                                           else [])][:10])
    return p[keep], (np.asarray(dates)[keep] if dates is not None else None), report


def directional_change(prices, theta: float) -> list[Pivot]:
    """Confirmed directional-change pivots at relative threshold ``theta``.

    The threshold is *relative*, so the encoding is scale-invariant: a 10 per
    cent reversal is the same event at 20 dollars and at 120. That is what makes
    the representation free of the number's magnitude, and it is why this
    encoding was reached from Benford-like scale invariance in Level 5.

    The initial direction is not assumed. The series is scanned from the start
    until the first move of at least ``theta`` in either direction, and that move
    sets the mode; before it there is no basis for calling the phase up or down,
    and assuming one would plant an artefact at the left edge.
    """
    p = validate_prices(prices)
    if len(p) < 2 or theta <= 0:
        return []

    mode = None
    for t in range(1, len(p)):
        if p[t] >= p[0] * (1 + theta):
            mode, ext, ext_t, start = "up", p[t], t, t
            break
        if p[t] <= p[0] * (1 - theta):
            mode, ext, ext_t, start = "down", p[t], t, t
            break
    else:
        return []

    pivots: list[Pivot] = []
    for t in range(start + 1, len(p)):
        if mode == "up":
            if p[t] > ext:
                ext, ext_t = p[t], t
            elif p[t] <= ext * (1 - theta):
                pivots.append(Pivot(ext_t, t, float(ext), "peak"))
                mode, ext, ext_t = "down", p[t], t
        else:
            if p[t] < ext:
                ext, ext_t = p[t], t
            elif p[t] >= ext * (1 + theta):
                pivots.append(Pivot(ext_t, t, float(ext), "trough"))
                mode, ext, ext_t = "up", p[t], t
    return pivots


def known_pivots(pivots: list[Pivot], t: int) -> list[Pivot]:
    """The pivots an observer standing at time ``t`` could actually know about.

    **This is the only accessor a forecasting feature may use.** Selecting on
    ``extreme_index`` instead would admit turning points that have happened but
    have not yet been confirmed, which is look-ahead.
    """
    return [q for q in pivots if q.confirm_index <= t]


def leaked_pivots(pivots: list[Pivot], t: int) -> list[Pivot]:
    """Pivots that have *occurred* by ``t`` but are not yet confirmed.

    Never to be used in a feature. Provided so that the size of the temptation
    can be measured rather than assumed small.
    """
    return [q for q in pivots if q.extreme_index <= t < q.confirm_index]


def leak_opportunities(pivots: list[Pivot], n: int) -> dict:
    """How often, and by how much, the two accessors disagree.

    A guard that never bites is a guard that proves nothing. If this returned
    zero the confirmed-only rule would be vacuous and the tests asserting it
    would pass for the wrong reason.
    """
    if not pivots:
        return dict(n_pivots=0, n_times_with_leak=0, fraction_of_time=0.0,
                    mean_lag=float("nan"), max_lag=0, min_lag=0)
    leak_times = sum(1 for t in range(n) if leaked_pivots(pivots, t))
    lags = [q.lag for q in pivots]
    return dict(n_pivots=len(pivots),
                n_times_with_leak=leak_times,
                fraction_of_time=round(leak_times / n, 4),
                mean_lag=round(float(np.mean(lags)), 3),
                max_lag=int(np.max(lags)), min_lag=int(np.min(lags)))


def legs(pivots: list[Pivot]) -> pd.DataFrame:
    """Completed legs between consecutive pivots: the clock and the driver.

    ``dt`` is the waiting time between turning points — the *clock*, which the
    programme found forecastable. ``dv`` is the relative move over the leg — the
    *driver*, which it found carries no memory beyond the fat-tailed marginal.
    ``known_at`` is the confirmation time of the leg's closing pivot, and is the
    earliest moment the leg may be used for anything.
    """
    rows = []
    for a, b in zip(pivots, pivots[1:]):
        rows.append(dict(start_index=a.extreme_index, end_index=b.extreme_index,
                         known_at=b.confirm_index,
                         dt=b.extreme_index - a.extreme_index,
                         dv=(b.extreme_price - a.extreme_price) / a.extreme_price,
                         kind=b.kind))
    return pd.DataFrame(rows)


def short_wait_target(leg_table: pd.DataFrame, min_history: int = 8) -> pd.DataFrame:
    """The Phase 2 target: will the next wait be short?

    Short means below the **running median** of the waits observed so far, so the
    target is near-balanced by construction. That is the whole point of the
    re-target: the monthly regime target is 66 to 73 per cent stagnant, which
    defeats accuracy as a measure (ledger A11, A13), while a median split cannot.

    The median uses only waits already known at the time of the decision, so the
    threshold itself is causal. Using a full-sample median would be a second,
    quieter form of look-ahead.
    """
    dt = leg_table["dt"].to_numpy()
    rows = []
    for i in range(min_history, len(dt) - 1):
        past = dt[:i + 1]
        rows.append(dict(leg=i,
                         known_at=int(leg_table["known_at"].iloc[i]),
                         running_median=float(np.median(past)),
                         next_dt=int(dt[i + 1]),
                         short=int(dt[i + 1] < np.median(past))))
    return pd.DataFrame(rows)
