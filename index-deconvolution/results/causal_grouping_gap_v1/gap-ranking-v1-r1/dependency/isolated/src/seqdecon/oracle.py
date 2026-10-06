"""The in-hindsight optimal trader — God's answer key — and the part causality reaches.

Given a price path, the *oracle* is the in-hindsight optimal buy/sell schedule that
maximises terminal wealth under a proportional transaction cost ``kappa``. With zero
cost it is useless (capture every up-tick); with a realistic cost it trades only when a
swing clears the cost, so its action points are a sparse set of troughs and peaks. It is
computed **with the future visible**: an answer key, not a strategy.

**The definition** (GLOSSARY.md §1, which outranks every other document here):

    A PIVOT is a position a CAUSAL process -- one with no look-ahead -- reproduces
    EXACTLY. What no such process reaches is the RESIDUAL.

In finance, therefore:

    financial pivots  =  DC(theta = c)  ⊆  oracle(kappa),   c = round_trip_cost(kappa)

— **containment, not identity, with the oracle the strictly larger set.** The residual
is the part of the answer key that *requires* the future: swings a look-ahead optimiser
catches and a greedy one-pass construction cannot. Measured over 12 series × 4 theta with
theta matched to c: 56,500/56,509 = 0.9998 contained, exact on 42 of 48 pairs, oracle
residual 1.37%.

**c is the primitive, theta is derived.** The physically given quantity is the round-trip
cost; the reversal scale follows from it as ``theta := c``. Driving the oracle from a
chosen threshold inverts that. Follow `level10/exp30_oracle_clock.py`, which fixes
``C_MAIN`` / ``C_GRID`` and computes ``kappa = kappa_for_round_trip(c)``.

**Two errors have been made about this relation, in opposite directions. Read both
before re-editing.** (1) bitácora 21 stated it as an *identity*; retracted by bitácora 22.
(2) The correction then over-shot, calling it "a geometric identity, not a market fact,
whose only worth is interpretive" — logged as confusion source #3 in GLOSSARY.md §2. That
merged two different things. That every **pivot** lies inside the oracle is
**constitutive of the definition** — a pivot just is an oracle point recovered causally —
while the measured rate is the **fidelity of the θ-walk as a recovery method**: 56,500 of
its 56,509 outputs are pivots; the 9 exceptions are 6 exact ties (co-optimal schedules the
DP's tie-break excludes) and 3 genuine walk errors, which are therefore not pivots
(`results/containment_exceptions.json`). The fidelity being ~1 on GBM, on return-shuffled
prices and on a pure sine is **expected and correct** — it says the causal construction
rarely invents points outside the answer key, which is what a sound recovery method must
do. What is *not* evidence about markets is the **agreement rate**. Keep the definition;
discard only "look, they agree, therefore markets have structure".

The oracle is also a legitimate *occurrence extractor* in its own right — a slightly
larger event set than the pivots, and whether its extra points are compressible is open.

Algorithm copied in behaviour from `index-deconvolution/level10/oracle.py`; the plumbing
is rebuilt per `TRANSFERENCE.md` §5, and notebook 01 R3 asserts our output is **identical**
to that module's, element for element, whenever the sibling repository is present. Exact
O(N) two-state dynamic programme, in log-wealth so it is stable over multi-decade paths:

    flat[t] = max( flat[t-1],  long[t-1] + log p[t] + log(1-kappa) )   # sell today
    long[t] = max( long[t-1],  flat[t-1] - log p[t] + log(1-kappa) )   # buy today

A round trip multiplies capital by ``(p_sell/p_buy)(1-kappa)^2``, so it clears cost when
``p_sell/p_buy > (1-kappa)^-2``. The round-trip cost that matches a pivot threshold is
therefore ``c = (1-kappa)^-2 - 1``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

NEG_INF = float("-inf")


def round_trip_cost(kappa: float) -> float:
    """Relative round-trip cost ``c`` for a per-transaction proportional cost kappa."""
    return (1.0 - kappa) ** -2 - 1.0


def kappa_for_round_trip(c: float) -> float:
    """Inverse of :func:`round_trip_cost` — the kappa giving round-trip cost ``c``."""
    return 1.0 - (1.0 + c) ** -0.5


def optimal_trades(prices: Sequence[float], kappa: float) -> dict:
    """Exact in-hindsight optimal trade schedule under proportional cost ``kappa``.

    Returns sorted ``buys`` and ``sells`` (indices into ``prices``), the terminal
    ``log_wealth`` starting and ending in cash, and the round-trip cost ``c``. Buys and
    sells strictly alternate, buy first.
    """
    n = len(prices)
    if n == 0:
        return {"buys": [], "sells": [], "log_wealth": 0.0, "c": round_trip_cost(kappa)}
    if min(prices) <= 0:
        raise ValueError("oracle requires a strictly positive price path")

    lc = math.log(1.0 - kappa)
    logp = [math.log(p) for p in prices]

    flat, long = 0.0, NEG_INF
    sold = [False] * n
    bought = [False] * n
    for t in range(n):
        sell_val = long + logp[t] + lc if long > NEG_INF else NEG_INF
        buy_val = flat - logp[t] + lc
        new_flat = flat
        if sell_val > new_flat:
            new_flat, sold[t] = sell_val, True
        new_long = long
        if buy_val > new_long:
            new_long, bought[t] = buy_val, True
        flat, long = new_flat, new_long

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


def oracle_points(prices: Sequence[float], kappa: float) -> list[int]:
    """Union of oracle buy and sell indices, sorted — **an occurrence extractor**."""
    tr = optimal_trades(prices, kappa)
    return sorted(tr["buys"] + tr["sells"])


def match_sets(a: Sequence[int], b: Sequence[int], tol: int = 0) -> dict:
    """Overlap of two index sets within ``tol`` indices — greedy nearest, each used once.

    **This is a diagnostic and must never be a scorer (G1).** It returns a
    tolerance-Jaccard, which is a similarity, not a code length. Use it to *see* how far
    the oracle and the pivots agree; use MDL to decide whether anything counts.
    """
    a, b = sorted(a), sorted(b)
    used = [False] * len(b)
    matched = 0
    j0 = 0
    for x in a:
        best_j, best_d = -1, tol + 1
        j = j0
        while j < len(b) and b[j] <= x + tol:
            if not used[j] and abs(b[j] - x) <= tol and abs(b[j] - x) < best_d:
                best_j, best_d = j, abs(b[j] - x)
            j += 1
        while j0 < len(b) and b[j0] < x - tol:
            j0 += 1
        if best_j >= 0:
            used[best_j] = True
            matched += 1
    union = len(a) + len(b) - matched
    return {
        "matched": matched,
        "n_a": len(a),
        "n_b": len(b),
        "jaccard": matched / union if union else 1.0,
        "recall_a": matched / len(a) if a else 1.0,
        "recall_b": matched / len(b) if b else 1.0,
    }
