# Bitacora 22 — Level 10, Adversarial Audit: Break the Theorem, Then Scale to 100 Stocks

Date: 2026-07-13
Status: complete and verified

## The brief

Change of stance. Having found the oracle result (bitacora 21), the task was to turn
hostile: assume it is wrong or oversold, attack it, and keep only what survives. If it
survived, stay sceptical and scale from the twelve survivor series to one hundred
stocks downloaded fresh, and document the whole thing for a naive reader in an
executable notebook. This bitacora records the attacks, the verdicts, and the
scale-up.

## The three attacks on the "theorem"

Attack 1 -- is the equivalence a market fact, or a construction identity? I ran the
containment DC(theta=c) subset-of oracle(c) not only on the stocks but on a geometric
random walk, on i.i.d. lognormal noise, and on a smooth sine wave.

    stocks (100)  0.9998
    GBM           0.9996
    pure noise    1.0000
    sine wave     1.0000

The containment is ~1.0 on everything. The "theorem" is therefore a deterministic
geometric identity, true of any wiggly line, and it says nothing whatever about
markets. Bitacora 21 called it "the headline" and said it "closes the flagship"; that
was overselling. The honest statement is: the perfect trader's action points are the
directional-change pivots at threshold theta = c by construction, on any sequence, and
the only value of the identity is interpretive -- it licenses calling the pivot clock
the perfect-opportunity clock, and reading transaction cost as a reversal scale. It is
real and it is exact, but it is geometry, not a discovery. I record this against my own
earlier framing.

Attack 2 -- is the optimiser even correct? I checked the O(N) dynamic programme against
a brute-force enumeration of every alternating buy/sell schedule on 200 short random
series across four cost levels. The terminal wealth was identical on 200 of 200. The
machinery is sound; the deflation in Attack 1 is about framing, not a bug.

Attack 3 -- does the out-of-sample forecast leak the oracle's look-ahead? The oracle is
computed with full look-ahead. I re-ran the held-out Hawkes-beats-Poisson forecast
using instead the fully causal directional-change pivots (no look-ahead at all). The
gains were the same: oracle +0.0465 against pivot +0.0470 nats per event on the 100
stocks. Two conclusions, both honest: there is no look-ahead cheat (the causal set
forecasts just as well), and equally there is no new information -- the oracle forecast
is the plain pivot forecast of bitacora 20 relabelled.

## The scale-up: 100 stocks, freshly downloaded

`level10/download_100.py` fetches long daily histories for 100 diverse US large-caps
from Yahoo v8 (explicit period1/period2, interval=1d, not range=max), saved in the
project loader's format. `level10/exp31_stress_100.py` runs the full audit, every claim
against the return-shuffle null, with GBM and noise controls. The panel is genuinely
broader than the twelve survivors (more sectors, some shorter and messier histories),
which is the point: a survivor sample flatters.

The one real market claim -- the clock self-excites -- survives, slightly weaker.

    branching ratio n = 0.613   (twelve survivors: 0.685; bitacora 20: 0.69)
    shuffle null      n = 0.014
    self-exciting on 99 of 100 stocks
    Fano clustering exponent 0.494  (bitacora 17: ~0.5)

The self-excitation is not a survivor artefact: it holds on 99 of 100 stocks, at a
branching ratio far above the shuffle. It is modestly weaker on the broad panel (0.61
vs 0.69), exactly the honest direction -- the twelve hand-inherited survivors were a
little rosier than the field. This is the load-bearing result of the whole programme
and it passes the scale-up.

The forecast survives too, and remains inherited. The held-out Hawkes beats Poisson on
94 of 100 stocks (sign-test p = 2e-21), mean +0.047 nats per event -- positive, robust,
but as Attack 3 showed it is the causal pivot clock, not anything the oracle adds. The
GBM control clock has branching ratio 0.000 and reads as the null, so the instrument is
not manufacturing self-excitation from any monotone-ish path.

The n(c) cost-scale curve -- the only candidate new object from bitacora 21 -- partly
survives.

    c = 0.005:  n = 0.261 +/- 0.200
    c = 0.010:  n = 0.488 +/- 0.169
    c = 0.020:  n = 0.613 +/- 0.141
    c = 0.040:  n = 0.623 +/- 0.119
    c = 0.080:  n = 0.548 +/- 0.152

The hump is real in the sense that 88 of 100 stocks peak at an interior cost, but on the
broad panel the peak sits on a plateau across c = 0.02 to 0.04 rather than the sharp
c = 0.02 peak the survivors showed, and the fine-scale collapse (n = 0.26 at c = 0.005)
is even steeper. As flagged in bitacora 21, the finest scale is partly instrument-
limited: at c = 0.005 there is a pivot every few days and the single-exponential Hawkes
decay grid tops out at a 250-day timescale, so fast excitation is clipped. Honest
verdict: opportunity clustering is strongest at percent-level costs and weakens at
both ends, a robust qualitative shape, but the precise peak and the fine-scale point
should not be over-read until the multi-scale kernel (open door 2) is fitted.

## The honest scorecard

| claim | verdict | evidence on 100 stocks |
|---|---|---|
| Perfect trades = pivots at theta = c | true but geometry | containment ~1.0 on stocks, GBM and noise alike |
| Clock self-excites (bursts) | real market signal | n = 0.61 vs shuffle 0.01, 99/100 |
| Clock forecasts next turn out of sample | real but inherited | 94/100, p = 2e-21; = causal pivot clock, no look-ahead cheat |
| n(c) hump (cost as scale) | suggestive | interior peak on 88/100; fine scale instrument-limited |
| Predict up/down direction | impossible | not attempted; proven dead earlier |

What survives the hostile audit is modest and honest: the perfect-trader equivalence is
a geometric identity, not a market fact (my bitacora 21 framing corrected); the genuine
market structure is the self-exciting burst clock, which holds on 99 of 100 stocks
though weaker than the survivor sample suggested; the forecast is real but is the plain
pivot result; and the cost-as-scale hump is qualitatively robust but quantitatively
soft at the extremes. Nothing predicts direction, and nothing here claims to.

## The notebook

`notebooks/09_oracle_perfect_trader.ipynb` walks a naive reader through the whole story
with plots, tables and plain-language explanation: what a pivot is, the perfect trader,
the equivalence and its geometric deflation (the sine-wave and noise controls shown
explicitly), the burst clock, the honest out-of-sample forecast with the causal-versus-
look-ahead check, the cost-as-scale hump, and a blunt scorecard. It has the shared
from-anywhere bootstrap, reads the committed slimmed 100-stock panel and the results
JSON, and was executed end to end from a foreign working directory (nine embedded
plots, zero errors). `notebooks/build_09.py` regenerates it.

## Verification

Reproduce: `python level10/download_100.py` then `python level10/exp31_stress_100.py`
(writes `results/exp31_stress_100.json`); `python notebooks/build_09.py` rebuilds the
notebook; execute it with the CausalBool kernel. Tests:
`python -m pytest level10 level9 level8 level7 level6 level5 level4 level3 level2 tests -q`
is 87 / 87 (unchanged; the audit adds experiment and data scripts, not core logic).
Levels 1 to 9 untouched.
