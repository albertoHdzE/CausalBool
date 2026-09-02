# Bitácora 06 — Phase 2: the right sign, and not enough data to prove it

**Date:** 2026-08-18
**Status:** Gate 2.0 passed; B6 **not supported**. 92 tests passing.
`results/phase2_gate.json` (sha `b9f4826f1b86b6bc`),
`results/phase2_forecast.json` (sha `27c84648ccaf15cc`).
**Ledger entries produced:** C23–C26.

---

## 1. The re-target, and why it was designed this way

Phase 1 closed with the monthly regime target exhausted: no deterministic
structure beyond persistence (C9, C10), and nothing gate-like in the panel (C20).
Phase 2 changes the question from *which way* the price moves to *when it
reverses* — the clock, where the deconvolution programme found structure that
survived its nulls twelve times out of twelve.

Two design properties were pre-declared and both delivered.

**A near-balanced target.** The monthly regime target is 66 to 73 per cent
stagnant, which makes raw accuracy uninformative — that is anchor A11 and A13,
and it is why GWP3's 75.9 per cent was indistinguishable from persistence. The
short-wait bit splits the waiting times at their *running* median, so it is near
balanced by construction. Measured on the panel: base rates of 0.396 to 0.467.
The base-rate trap is gone.

**A representation-free encoding.** A directional-change pivot is defined by a
*relative* move, so it does not depend on how the number is written. The test
suite asserts this directly: multiplying every price by 37.5 leaves every pivot
index and kind unchanged.

## 2. The confirmed-only rule, which was the whole first build

A directional-change pivot happens at one time and becomes *knowable* at a later
one. In an upward phase the running maximum is only a peak once the price has
fallen from it by the threshold. Every pivot therefore carries two timestamps,
and using the earlier one in a forecasting feature is look-ahead.

This is subtler than the error GWP3 caught in the source dissertation, because
the turning point genuinely is in the past — only the knowledge of it is not. So
the guard is not merely implemented, it is **measured**:

| | monthly WTI spot |
| --- | --- |
| mean confirmation lag | 1.3 months at θ = 0.05, rising to 5.3 at θ = 0.25 |
| maximum lag | 3 months at θ = 0.05, **19 months** at θ = 0.25 |
| fraction of the series inside a leak window | **31 to 52 per cent** |

A third to a half of the sample sits in a window where a pivot has occurred but
is not yet knowable. A naive implementation would not have been slightly
contaminated; it would have been contaminated most of the time.

And the leak is **exploitable**, which is asserted as a test rather than assumed:
a rule that peeks at unconfirmed pivots predicts the next step's direction at
better than 55 per cent, against 50 for anything causal. Knowing that an
unconfirmed peak exists is knowing the price has already turned. That test exists
so the guard can never become a formality.

A second, quieter form of leakage is also closed: the median that defines "short"
is a *running* median over waits already seen, not a full-sample one, and the
test suite recomputes it from the prefix to check.

## 3. Gate 2.0 — the sample can support the question, barely

| θ | pivots | legs | usable target rows | base rate |
| --- | --- | --- | --- | --- |
| 0.05 | 58 | 57 | 48 | 0.396 |
| 0.08 | 40 | 39 | 30 | 0.467 |
| 0.10 | 38 | 37 | 28 | 0.464 |
| 0.15 | 29 | 28 | 19 | 0.579 |
| 0.20 | 19 | 18 | 9 | 0.444 |

Monthly WTI spot. The gate passes at θ ≤ 0.10 against a pre-declared minimum of
30 legs, and fails above it. For contrast, the daily series held for Phase 3
yields **322 legs** at θ = 0.05 against the monthly 57 — a factor of six, and the
single number that shows what the monthly constraint costs.

## 4. B6: the sign is right, the sample is not enough

Every threshold and every series is reported, because reporting the best of nine
would be selection over the grid.

| series | θ = 0.05 | θ = 0.08 | θ = 0.10 |
| --- | --- | --- | --- |
| WTI\_Spot | +0.051 (p 0.463) | **+0.369 (p 0.010)** | +0.200 (p 0.140) |
| WTI\_CL | +0.008 (p 0.537) | **+0.284 (p 0.030)** | +0.210 (p 0.139) |
| Brent\_BZ | −0.082 (p 0.721) | −0.041 (p 0.632) | +0.159 (p 0.308) |

Excess of the forecast edge over a return-shuffle null that is passed through the
*entire* pipeline — pivot detection, legs, running median, features, fit and
score — so that only genuine temporal structure can survive it.

**Seven of nine cells are positive, mean excess +0.129, and the sign test gives
p = 0.0898.** Not significant. Two individual cells clear 0.05, but with nine
cells tested the probability of two or more clearing by chance is 0.071, so they
do not survive their own multiple-comparison accounting either. Under rule R5
that is the number that counts, and it is the one reported.

The daily series, shown only for contrast, gives 3 of 3 positive with a mean
excess of +0.093 and no cell significant — three cells cannot produce a
significant sign test whatever they show.

**B6 is not supported.** The test sets hold 10 to 19 decisions each.

## 5. What this is, and what it is not

It is **not** a negative of the kind Phase 1 produced. Gate 1.0 measured
something and found it absent: the increment over persistence was −0.0003 to
+0.0073 with p from 0.32 to 0.64, sitting exactly on its null. Here the effect is
consistently *positive* — ten of twelve cells across both frequencies — with a
mean excess of about +0.13 monthly, and it fails on **power**, not on sign.

It is also **not** a positive. A consistent sign across an underpowered grid is
what a real effect looks like, and it is equally what a mild pipeline bias looks
like. The distinction cannot be made at this sample size, and I am not going to
make it by picking θ = 0.08.

The direction agrees with the deconvolution programme's Level 5 result, where the
same target beat the same null twelve times out of twelve at p = 2.4 × 10⁻⁴ — but
that used twelve instruments over three decades of daily data. Here it is one
market over sixteen years of monthly data. Agreement in sign with prior work is
encouraging and is not evidence; treating it as evidence would be the confirmation
error this protocol exists to prevent.

## 6. A control of mine that was wrong

The first power control was a perfectly periodic reversal, on the reasoning that
a deterministic clock must be detectable. It failed, and the failure was
instructive: with a perfectly periodic clock **every wait equals the running
median**, so the short-wait target is constant, the base rate is 1.0, and the
edge is 0 no matter how well the model does. The forecast scored an accuracy of
1.000 and an excess of 0.054.

The control now uses a clock that is predictable but *not constant* — waits
alternating between 8 and 24 steps — which is near-balanced and perfectly
learnable. It passes at an excess above 0.15. The size control, geometric
Brownian motion, correctly fails to beat its own null.

This is the fifth control-caught error in the package, and like the others it was
caught by the check rather than by intuition.

## 7. Consequence

The monthly dataset is exhausted for this question as it was for the last one.
Phase 3 was pre-declared to run **regardless of the Phase 1 and Phase 2
outcomes**, on the grounds that a frequency extension tests the method rather
than the market, and that reasoning now has a concrete number behind it: 322 legs
against 57.

Phase 3 as declared: daily WTI extended backwards from FRED `DCOILWTICO`
(available from 1986, against the 2010 start of the file held here), the panel
enlarged with EIA inventories and the Kilian index, and rolling-origin
evaluation. The pooled sign test across instruments — the design that gave Level
5 its 12/12 — is what this dataset cannot provide and Phase 3 can.

## 9. Postscript, 2026-08-18 — challenged, and rightly

The assessor put this phase down to **Datasaurus syndrome**: summary statistics
reported with no shape behind them. Phase 2 contained no figures at all. Acting
on the objection changed what should be reported, though not the verdict.

**The headline statistic was the artefact.** The null's mean edge is about −0.115
*even after conditioning on test-set size*. That is not noise: a lookup table
fitted on a random prefix scores about 0.5 on the test suffix while the base rate
is about 0.58, so a correctly specified null model *must* score negative. It is an
overfitting penalty. The reported "mean excess +0.129" therefore adds a modest
real edge of about +0.096 to that penalty and presents the sum as one effect,
which flatters and conceals that everything rests on one cell.

**What survived.** The rank-based *p*-values, which are what the verdict actually
rested on. Conditioning on matched test-set size moves them from 0.0050 to 0.0082,
0.1433 to 0.1319 and 0.4393 to 0.4423 — the mismatch is real but immaterial.

**A suspicion of mine that did not survive.** I expected volatility clustering to
give the real series systematically fewer pivots than its own shuffle, which would
have left the null unmatched on leg count. It does not, at this resolution:
z = −1.07, −0.73, +0.38 across the three thresholds, none significant. Reasonable
concern, wrong.

**What the looking confirmed.** The pivots are the turning points an energy
analyst would name — the 2011 peak, the 2014 peak that begins the shale collapse,
the 2016 bottom, the 2018 trough. The encoding is sound, so the negative is about
the sample and not about the representation.

**The corrected summary of B6.** Not a mean excess but a count: one cell of nine
significant, Bonferroni 0.074, sign consistently positive across ten of twelve
cells, sample insufficient. Notebook 03 carries the figures that should have
existed before any of this was written down.

## 8. Next

Phase 3. Fetch the longer daily history first, since every other decision depends
on how much of it exists.

---

## Addendum 2026-09-02 (AUDIT02/Q1-C) — both Phase 2 producers were unrunnable; declared policy now applied

An arm-1 reproducibility sweep re-ran every producer in this package against its
committed artefact. `scripts/phase2_gate.py` and `scripts/phase2_forecast.py`
did not merely disagree — **they aborted**:

```
NonPositivePriceError: 1 non-positive price(s) at index [2588] (min -37.63)
```

That is the 2020-04-20 negative WTI settlement, and `validate_prices` is right
to refuse it: a *relative* threshold θ is undefined once a price crosses zero,
so every directional-change pivot computed through it would be meaningless
rather than merely noisy. The committed artefacts therefore predate the guard
and could not be regenerated from the code in the tree — the strongest form of
irreproducibility, since no amount of rerunning would have surfaced it.

Both now apply the declared policy — `clean_prices`: drop, never interpolate,
never winsorise — and **report** the exclusion in the output under
`daily_exclusion`, which is what the guard's own message instructs.

**Exactly one observation is excluded**, 4,156 → 4,155, dated 2020-04-20.

### What moved, and what did not

The monthly blocks are **unchanged**. Those carry the Phase 2 claims; the daily
series is present only as a contrast for Phase 3. So the Gate 2.0 verdict and
the monthly forecast comparison stand exactly as recorded above.

What moved is confined to the daily contrast, and it is worth stating plainly:

| quantity | pre-guard | after exclusion |
|---|---|---|
| `daily_signtest.mean_excess` | 0.0931 | **0.0506** |
| `daily_signtest.p_value` | 0.125 | 0.125 (unchanged) |
| `any_significant` | False | False (unchanged) |

A single untradeable print was inflating the apparent daily edge by roughly
84 per cent. The conclusion does not change — it was not significant before and
is not now — but any future Phase 3 work that quoted the daily effect size
would have been quoting an artefact of one settlement.

### Sensitivity, because one dropped point invites the obvious objection

`clean_prices` takes a `pad` that additionally drops neighbours, precisely so
this can be checked rather than asserted. Excess over null on the daily series:

| pad | observations kept | θ=0.05 | θ=0.10 | θ=0.15 |
|---|---|---|---|---|
| 0 | 4,155 | +0.0340 | +0.0572 | +0.1171 |
| 1 | 4,153 | +0.0366 | +0.0546 | +0.1184 |
| 5 | 4,125 | +0.0254 | +0.0272 | +0.1304 |
| 20 | 3,735 | +0.0453 | +0.0716 | +0.0953 |

Positive and in the same band throughout, while discarding up to 421
observations. The daily contrast does not depend on the neighbourhood of the
excluded print, so the exclusion is safe and the remaining signal is not an
edge effect of the April 2020 dislocation.
