"""blindplay.py  (Level 15)

Play the buy and sell behaviour formulae blindly on historical data, out of sample, and
probe -- graphically and rigorously -- whether they work.

Two questions, kept strictly apart because they have opposite answers:

  TIMING. Fit the three-number formula on the past only; on unseen future days, does its
  intensity rank the days by how likely a turn is to arrive soon, better than a
  memoryless (Poisson) baseline and better than a return-shuffle? Scored by the ROC area
  (0.5 = no skill) and the Brier score, with a reliability curve for calibration.

  MONEY. If you actually act on the confirmed signals causally -- no look-ahead -- does
  the equity beat buy-and-hold? Compared against the look-ahead oracle (which cheats by
  construction) to show the gap between hindsight and a blind, causal play.

Standard library only; deterministic. The intensity is accumulated by the same O(N)
recursion as the Level 9 likelihood, so the whole held-out grid is linear.
"""

from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "level5"))

from pivots import directional_change_pivots  # noqa: E402


def oos_event_forecast(event_times: list[int], n_days: int, mu: float, alpha: float,
                       beta: float, t_train: int, horizon: int = 10,
                       step: int = 1) -> tuple[list[float], list[int]]:
    """Causal out-of-sample forecast of 'a turn within the next ``horizon`` days'.

    For each held-out day t > t_train the predicted score is 1 - exp(-lambda(t)*horizon),
    with lambda(t) built only from events strictly before t (causal). The label is 1 if a
    real event falls in (t, t+horizon]. Returns (scores, labels). Poisson gives a constant
    score, hence an ROC area of 0.5 by construction.
    """
    ev = sorted(event_times)
    scores: list[float] = []
    labels: list[int] = []
    # pointer into ev for the causal intensity accumulator A(t) = sum_{ti<t} exp(-beta(t-ti))
    A = 0.0
    last = 0
    ei = 0                                   # next event index not yet folded into A
    # precompute event membership for labels
    ev_set = ev
    j = 0                                    # pointer for label search
    import bisect
    for t in range(1, n_days):
        # advance A to time t, folding in any events that occurred at day <= t-1
        dt = t - last
        A *= math.exp(-beta * dt)
        while ei < len(ev) and ev[ei] <= t - 1:
            A += math.exp(-beta * (t - ev[ei]))
            ei += 1
        last = t
        if t <= t_train or t % step != 0:
            continue
        lam = mu + alpha * A
        scores.append(1.0 - math.exp(-lam * horizon))
        lo = bisect.bisect_right(ev_set, t)
        hit = lo < len(ev_set) and ev_set[lo] <= t + horizon
        labels.append(1 if hit else 0)
    return scores, labels


def roc_auc(scores: list[float], labels: list[int]) -> float:
    """Area under the ROC curve via the rank-sum (Mann-Whitney) identity."""
    n = len(scores)
    pos = sum(labels)
    neg = n - pos
    if pos == 0 or neg == 0:
        return 0.5
    order = sorted(range(n), key=lambda i: scores[i])
    # average ranks (handle ties)
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    sum_pos = sum(ranks[i] for i in range(n) if labels[i] == 1)
    return (sum_pos - pos * (pos + 1) / 2.0) / (pos * neg)


def brier(scores: list[float], labels: list[int]) -> float:
    if not scores:
        return float("nan")
    return sum((s - y) ** 2 for s, y in zip(scores, labels)) / len(scores)


def reliability(scores: list[float], labels: list[int], nbins: int = 10) -> list[dict]:
    """Calibration: mean predicted probability vs observed frequency, per bin."""
    bins = [[] for _ in range(nbins)]
    for s, y in zip(scores, labels):
        b = min(nbins - 1, int(s * nbins))
        bins[b].append((s, y))
    out = []
    for b in range(nbins):
        if bins[b]:
            ps = sum(s for s, _ in bins[b]) / len(bins[b])
            fs = sum(y for _, y in bins[b]) / len(bins[b])
            out.append({"pred": ps, "obs": fs, "n": len(bins[b])})
    return out


def causal_dc_equity(series: list[float], theta: float, cost: float = 0.0) -> dict:
    """Blind, causal trend play: act when a directional change CONFIRMS (not at the peak).

    Walking forward: hold the running extreme; when the price has reversed by theta from
    it, the turn is confirmed -- sell (if holding) on a confirmed peak, buy (if flat) on a
    confirmed trough -- acting at the confirmation price, which necessarily lags the
    extreme. Returns the terminal wealth multiple, net of a per-transaction cost.
    """
    if len(series) < 2:
        return {"wealth": 1.0, "n_trades": 0}
    cash, shares = 1.0, 0.0
    holding = False
    mode = 0
    ext = series[0]
    for i in range(1, len(series)):
        x = series[i]
        if mode >= 0 and x > ext:
            ext, mode = x, 1
        elif mode <= 0 and x < ext:
            ext, mode = x, -1
        if mode == 1 and ext > 0 and x <= ext * (1 - theta):
            if holding:                                 # confirmed peak -> exit
                cash = shares * x * (1 - cost)
                shares, holding = 0.0, False
            mode, ext = -1, x
        elif mode == -1 and ext > 0 and x >= ext * (1 + theta):
            if not holding:                             # confirmed trough -> enter
                shares = cash * (1 - cost) / x
                cash, holding = 0.0, True
            mode, ext = 1, x
    wealth = cash if not holding else shares * series[-1] * (1 - cost)
    return {"wealth": wealth, "n_trades": 0}


def buy_hold(series: list[float]) -> float:
    return series[-1] / series[0] if series and series[0] > 0 else 1.0
