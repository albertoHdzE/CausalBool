# Level 10 — The Oracle / Perfect-Trader Behaviour Table

The flagship of the behaviour-table programme (TRANSFERENCE §6): build the behaviour
table of the *in-hindsight optimal trades* and test whether it *is* the clock.

## The objects

- `oracle.py` — the perfect trader. `optimal_trades(prices, kappa)` is an exact O(N)
  two-state dynamic programme (the trade-with-fee recursion, in log-wealth) that
  returns the in-hindsight optimal buy/sell schedule under a proportional
  per-transaction cost `kappa`. `oracle_points` is the union of buy and sell indices
  (the occurrence set). `round_trip_cost`/`kappa_for_round_trip` convert between the
  per-transaction cost and the relative round-trip cost `c = (1-kappa)^-2 - 1`.
  `match_sets` measures the overlap of two index sets within a tolerance.

- `exp30_oracle_clock.py` — the experiment. Reuses `level5` (pivots, controls),
  `level6` (Fano exponent) and `level9` (Hawkes fit, OOS). Writes
  `results/exp30_oracle_clock.json`. Accepts `--quiet`.

## The theorem (verified, exact one direction)

For a per-round-trip cost `c`, the directional-change pivots at reversal threshold
`theta = c` are **exactly a subset** of the oracle action points (100 % containment,
tol = 0, on every long series). Reason: the DC construction confirms a trough at `L`
only after a rise to `L(1+theta)`, so two consecutive pivots span `H/L >= 1+theta =
1+c >= (1-kappa)^-2`, exactly the oracle's profitability threshold — the oracle must
take every DC round trip. The oracle is a slight (~1–2 %) superset, the extra points
being swings a globally-optimal DP catches that the greedy, causal DC construction
misses. So: **the perfect trader's action points are the pivots at a threshold set by
transaction cost**, and the cost is a renormalisation scale.

## Guardrail

The oracle is computed with look-ahead **by construction** (it is the answer key). It
is used only as a *target to explain and to forecast out of sample* — never as a
predictor feature. The Hawkes forecast sees only past oracle event times.

## Run

```
python level10/exp30_oracle_clock.py            # full report
python level10/exp30_oracle_clock.py --quiet    # JSON only
python -m pytest level10 -q                      # tests
```
