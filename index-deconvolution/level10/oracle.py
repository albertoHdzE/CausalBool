"""oracle.py  (Level 10)

The perfect trader, and the theorem that its action points are the pivots.

Given a price path, the *oracle* is the in-hindsight optimal buy/sell schedule that
maximises terminal wealth under a proportional transaction cost.  With zero cost the
oracle is trivial and useless (capture every up-tick); with a realistic per-trade
cost ``kappa`` it only trades when a swing clears the cost, and the buy/sell points
become a sparse set of troughs and peaks.  The flagship hypothesis (TRANSFERENCE
sec. 6) is that this set *is* the directional-change pivot set at a reversal
threshold fixed by the cost.

The optimiser is an exact O(N) two-state dynamic programme (the classic
trade-with-fee recursion, in log-wealth so it is stable over multi-decade paths):

    flat[t] = max( flat[t-1],                              stay in cash
                   long[t-1] + log p[t] + log(1-kappa) )   sell today
    long[t] = max( long[t-1],                              stay invested (share count fixed)
                   flat[t-1] - log p[t] + log(1-kappa) )   buy today

``flat[t]`` is the best log-cash ending day t in cash; ``long[t]`` is the best
log-share-count ending day t holding one position (share count is invariant while
held, which is why the multiplicative price cancels out of "stay invested").  A cost
``kappa`` is charged on each transaction's traded value, so a round trip multiplies
capital by (p_sell / p_buy)(1-kappa)^2; it clears cost when p_sell / p_buy >
(1-kappa)^-2 ~ 1 + 2*kappa.  The *round-trip cost* used to match the pivot threshold
is therefore c = (1-kappa)^-2 - 1.

Backtracking the arg-max recovers the exact buy and sell days.  Everything is
deterministic and standard-library only.
"""

from __future__ import annotations

import math

NEG_INF = float("-inf")


def round_trip_cost(kappa: float) -> float:
    """Relative round-trip cost c for a per-transaction proportional cost kappa."""
    return (1.0 - kappa) ** -2 - 1.0


def kappa_for_round_trip(c: float) -> float:
    """Inverse of round_trip_cost: the per-transaction kappa giving round-trip c."""
    return 1.0 - (1.0 + c) ** -0.5


def optimal_trades(prices: list[float], kappa: float) -> dict:
    """Exact in-hindsight optimal trade schedule under proportional cost kappa.

    Returns a dict with the sorted ``buys`` and ``sells`` (indices into ``prices``),
    the terminal ``log_wealth`` (starting from one unit of cash, ending in cash), and
    the round-trip cost ``c``.  Buys and sells strictly alternate, buy first.
    """
    n = len(prices)
    if n == 0:
        return {"buys": [], "sells": [], "log_wealth": 0.0, "c": round_trip_cost(kappa)}
    lc = math.log(1.0 - kappa)
    logp = [math.log(p) for p in prices]

    flat = 0.0           # best log-cash, currently in cash (start in cash)
    long = NEG_INF       # best log-share-count, currently holding
    # choice bits per day: did flat come from a sell? did long come from a buy?
    sold = [False] * n
    bought = [False] * n
    for t in range(n):
        sell_val = long + logp[t] + lc if long > NEG_INF else NEG_INF
        buy_val = flat - logp[t] + lc
        new_flat = flat
        if sell_val > new_flat:
            new_flat = sell_val
            sold[t] = True
        new_long = long
        if buy_val > new_long:
            new_long = buy_val
            bought[t] = True
        flat, long = new_flat, new_long

    # backtrack from the end in cash (optimal terminal state is always flat:
    # holding at the end could only be improved by a costless liquidation, and
    # log(1-kappa) < 0 makes never having bought at least as good).
    buys: list[int] = []
    sells: list[int] = []
    holding = False
    for t in range(n - 1, -1, -1):
        if not holding and sold[t]:
            sells.append(t)
            holding = True
        elif holding and bought[t]:
            buys.append(t)
            holding = False
    buys.reverse()
    sells.reverse()
    return {"buys": buys, "sells": sells, "log_wealth": flat, "c": round_trip_cost(kappa)}


def oracle_points(prices: list[float], kappa: float) -> list[int]:
    """The union of oracle buy and sell indices, sorted -- the occurrence set."""
    tr = optimal_trades(prices, kappa)
    return sorted(tr["buys"] + tr["sells"])


def match_sets(a: list[int], b: list[int], tol: int = 0) -> dict:
    """Overlap of two index sets within a tolerance (Jaccard and matched counts).

    A member of ``a`` matches a member of ``b`` if they lie within ``tol`` indices;
    each element is matched at most once (greedy nearest, both sorted).
    """
    a = sorted(a)
    b = sorted(b)
    used_b = [False] * len(b)
    matched = 0
    j0 = 0
    for x in a:
        best_j, best_d = -1, tol + 1
        j = j0
        while j < len(b) and b[j] <= x + tol:
            if not used_b[j] and abs(b[j] - x) <= tol and abs(b[j] - x) < best_d:
                best_j, best_d = j, abs(b[j] - x)
            j += 1
        # advance j0 past elements that can no longer match any future x
        while j0 < len(b) and b[j0] < x - tol:
            j0 += 1
        if best_j >= 0:
            used_b[best_j] = True
            matched += 1
    union = len(a) + len(b) - matched
    return {"matched": matched, "n_a": len(a), "n_b": len(b),
            "jaccard": matched / union if union else 1.0,
            "recall_a": matched / len(a) if a else 1.0,
            "recall_b": matched / len(b) if b else 1.0}
