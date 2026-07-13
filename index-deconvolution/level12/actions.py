"""actions.py  (Level 12)

Symbolic action dynamics -- the assessor's idea: forget the *direction* of prices and
ask whether the *actions* (buy / sell / hold / wait) carry a timing pattern, in the
spirit of the behaviour tables and of Holland's schemata.

The key observation that makes the idea precise: a trader must alternate. You cannot
buy twice in a row; every buy is followed by a sell and vice versa. So the *order* of
the action symbols is forced -- B, S, B, S, ... -- and carries essentially zero
information. All of the content is in the *run-lengths between actions*, which is the
clock. This module makes that split explicit and then does the genuinely new thing the
idea suggests: it decomposes the single pivot clock into two interleaved clocks,

    the BUY clock  = the trough pivots  (kind -1): when the perfect entry arrives,
    the SELL clock = the peak pivots    (kind +1): when the perfect exit arrives,

and lets us ask whether one is more self-exciting, or more predictable, than the other.

Standard library only; deterministic.
"""

from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "level5"))

from pivots import directional_change_pivots  # noqa: E402


def buy_sell_times(series: list[float], theta: float) -> tuple[list[int], list[int]]:
    """Split the pivot clock into (buy_times, sell_times) = (troughs, peaks)."""
    piv = directional_change_pivots(series, theta)
    buys = [p.index for p in piv if p.kind == -1]
    sells = [p.index for p in piv if p.kind == +1]
    return buys, sells


def action_order_entropy(series: list[float], theta: float) -> dict:
    """Information in the ACTION-TYPE order, vs in the timing.

    The action-type sequence (B, S, B, S, ...) is (almost) perfectly alternating, so the
    conditional entropy of the next action given the previous is ~0 bits: the 'what' is
    forced. We report that entropy and, for contrast, the entropy of a coarse timing
    symbol (is the next gap shorter or longer than the median), which is where the real
    information lives.
    """
    piv = directional_change_pivots(series, theta)
    kinds = [p.kind for p in piv]
    # conditional entropy H(next kind | previous kind), in bits
    from collections import Counter
    trans = Counter((kinds[i], kinds[i + 1]) for i in range(len(kinds) - 1))
    prev = Counter(kinds[i] for i in range(len(kinds) - 1))
    h_order = 0.0
    for (a, _b), c in trans.items():
        p_joint = c / (len(kinds) - 1)
        p_cond = c / prev[a]
        if p_cond > 0:
            h_order -= p_joint * math.log2(p_cond)
    # timing symbol entropy: next-gap shorter/longer than median (marginal, bits)
    times = [p.index for p in piv]
    gaps = [times[i + 1] - times[i] for i in range(len(times) - 1)]
    if gaps:
        med = sorted(gaps)[len(gaps) // 2]
        short = sum(1 for g in gaps if g < med) / len(gaps)
        h_time = 0.0
        for p in (short, 1 - short):
            if p > 0:
                h_time -= p * math.log2(p)
    else:
        h_time = 0.0
    return {"order_entropy_bits": h_order, "timing_entropy_bits": h_time,
            "n_actions": len(kinds)}


def shortlong_forecast(times: list[int], train_frac: float = 0.6,
                       window: int = 5) -> dict:
    """Out-of-sample forecast of the next gap being 'short' from a trailing window.

    Binarise inter-event gaps as 1 if below the train median ('short'); predict the
    next bit as the majority of the last ``window`` bits; commit on the first
    ``train_frac`` of gaps, evaluate on the rest. Returns accuracy, base rate and their
    difference (the lift). This is the clock-persistence forecast, per sub-clock.
    """
    gaps = [times[i + 1] - times[i] for i in range(len(times) - 1)]
    if len(gaps) < 40:
        return {"acc": float("nan"), "base": float("nan"), "lift": float("nan"),
                "n_test": 0}
    cut = int(train_frac * len(gaps))
    med = sorted(gaps[:cut])[cut // 2]
    bits = [1 if g < med else 0 for g in gaps]
    ones = sum(bits[cut:])
    base = max(ones, len(bits) - cut - ones) / (len(bits) - cut) if len(bits) - cut else 0.0
    correct = 0
    total = 0
    for t in range(cut, len(bits)):
        if t < window:
            continue
        w = bits[t - window:t]
        pred = 1 if sum(w) * 2 >= window else 0
        correct += (pred == bits[t])
        total += 1
    acc = correct / total if total else 0.0
    return {"acc": acc, "base": base, "lift": acc - base, "n_test": total}
