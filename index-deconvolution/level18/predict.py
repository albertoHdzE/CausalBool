"""predict.py  (Level 18)

Turn a clock model into discrete predictions, score them against the oracle, and simulate
a causal trade -- the machinery behind the granular walkthrough notebook.

The clock model (a three-number Hawkes) emits a causal intensity lambda(t): the predicted
turn-rate on each future day, built only from the past. To predict discrete turns we fire
on the highest-intensity days, spaced by a refractory period, up to the rate the model
expects -- then match those predicted turns to the oracle's actual turns within a small
tolerance and read off precision and recall. The trade simulator buys on a predicted
trough and sells on a predicted peak, causally, and returns the equity path.

Standard library only; deterministic.
"""

from __future__ import annotations


def predicted_events(intensity: list[float], t_start: int, refractory: int,
                     n_expected: int) -> list[int]:
    """Fire predicted turns on the highest-intensity days from ``t_start``.

    Greedy: take days in order of decreasing intensity, skipping any within
    ``refractory`` days of an already-fired day, until ``n_expected`` are fired. This
    yields a spread-out set of predicted turns whose count matches the model's own rate.
    """
    cand = sorted(range(t_start, len(intensity)), key=lambda t: intensity[t], reverse=True)
    picked: list[int] = []
    for t in cand:
        if len(picked) >= n_expected:
            break
        if all(abs(t - p) >= refractory for p in picked):
            picked.append(t)
    return sorted(picked)


def match_events(predicted: list[int], actual: list[int], tol: int) -> dict:
    """Greedy nearest match within ``tol``; returns precision, recall, F1, counts."""
    actual = sorted(actual)
    used = [False] * len(actual)
    matched = 0
    for p in sorted(predicted):
        best, bd = -1, tol + 1
        for i, a in enumerate(actual):
            if not used[i] and abs(a - p) <= tol and abs(a - p) < bd:
                best, bd = i, abs(a - p)
        if best >= 0:
            used[best] = True
            matched += 1
    precision = matched / len(predicted) if predicted else 0.0
    recall = matched / len(actual) if actual else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "matched": matched,
            "n_pred": len(predicted), "n_actual": len(actual)}


def trade_sim(price: list[float], buy_days: list[int], sell_days: list[int],
              cost: float = 0.0005, start: int = 0) -> dict:
    """Causal long/flat trade: buy on a predicted trough, sell on a predicted peak.

    Returns the equity path (mark-to-market), the position series (1 long, 0 flat), the
    realised buy/sell days, and the terminal wealth, alongside buy-and-hold on the same
    window.
    """
    buyset, sellset = set(buy_days), set(sell_days)
    cash, shares, holding = 1.0, 0.0, False
    equity, positions = [], []
    did_buy, did_sell = [], []
    p0 = price[start] if start < len(price) else price[0]
    for t in range(start, len(price)):
        if not holding and t in buyset:
            shares = cash * (1 - cost) / price[t]
            cash = 0.0
            holding = True
            did_buy.append(t)
        elif holding and t in sellset:
            cash = shares * price[t] * (1 - cost)
            shares = 0.0
            holding = False
            did_sell.append(t)
        equity.append(cash if not holding else shares * price[t])
        positions.append(1 if holding else 0)
    bh = [price[t] / p0 for t in range(start, len(price))]
    return {"equity": equity, "positions": positions, "buys": did_buy, "sells": did_sell,
            "final": equity[-1] if equity else 1.0, "buy_hold": bh,
            "bh_final": bh[-1] if bh else 1.0}
