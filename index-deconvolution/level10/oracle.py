"""oracle.py  (Level 10)

The perfect trader -- God's answer key -- and the set of it that causality can reach.

Given a price path, the *oracle* is the in-hindsight optimal buy/sell schedule that
maximises terminal wealth under a proportional transaction cost.  With zero cost the
oracle is trivial and useless (capture every up-tick); with a realistic per-trade
cost ``kappa`` it only trades when a swing clears the cost, and the buy/sell points
become a sparse set of troughs and peaks.  Crucially it is computed *with the future
visible*: it is the answer key, not a strategy.

THE DEFINITION (settled 2026-08-22; source of truth is
``series-deconvolution/GLOSSARY.md`` section 1, which outranks every paper and notebook
in this programme on a definition):

    A PIVOT is a position that a CAUSAL process -- one with no look-ahead --
    reproduces EXACTLY.  What no such process reaches is the RESIDUAL.

This is the programme's founding object, not a Level-10 invention: see
``PROTOCOL_order_discovery.md`` lines 142-148 ("the positions that a discovered process
reproduces exactly are the pivots ... the positions that no process reaches are the
residual") and bitacora 14 ("the points and segments where local determinism holds
exactly are the gold").  Specialised to finance:

    A FINANCIAL PIVOT is an oracle action point that the causal, one-pass
    directional-change construction at theta = c recovers exactly.
    The RESIDUAL is the part of the answer key that REQUIRES the future.

    DC(theta = c)  is a SUBSET of  oracle(kappa),      c = round_trip_cost(kappa)

- Containment, NOT identity: the oracle is the strictly larger set.  Measured here:
  ~0.4% superset, 11/12 exact, the 12th a measure-zero break-even tie.  Measured in
  ``series-deconvolution`` over 12 series x 4 theta: 56,500/56,509 = 0.9998 contained,
  exact on 42/48 pairs, oracle residual 1.37%.  Both on the record; neither is quoted
  as the other.
- It requires theta == c.  Comparing a theta against a mismatched kappa measures nothing.

CORRECTION HISTORY -- read this before re-editing, two errors have already been made
here in opposite directions:

1. This docstring once asserted bitacora 21's "flagship hypothesis" that the oracle set
   *is* the pivot set.  Retracted by bitacora 22: containment, not identity.
2. The 2026-08-21 fix then over-corrected, calling the relation "a GEOMETRIC IDENTITY,
   NOT A MARKET FACT ... its only worth is interpretive".  **That also is wrong**, and
   it is logged as confusion source #3 in ``GLOSSARY.md`` section 2.  It merged two
   different things.  The containment is CONSTITUTIVE OF THE DEFINITION -- a pivot just
   *is* an oracle point recovered causally, so containment holding on GBM, on shuffled
   returns and on a pure sine is EXPECTED and CORRECT: it says the causal construction
   never invents points outside the answer key, which is what a sound recovery method
   must do.  What is *not* evidence about markets is the AGREEMENT RATE.  Keep the
   definition; discard only "look, they agree, therefore markets have structure".

Note also that the walk implemented in ``level5/pivots.py`` is HOW pivots are recovered,
not WHAT THEY ARE.  Defining a pivot as "whatever that walk returns" is confusion
source #1.

See TRANSFERENCE.md, "STATE AT HANDBACK (Level 10 adversarial audit + 100 stocks)".

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
