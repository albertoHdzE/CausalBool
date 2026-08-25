# Bitacora 29 — Level 17: One Universal Clock Law, Not a Model per Stock

Date: 2026-07-14
Status: complete and verified

## The assessor's two prompts, joined

The assessor first asked to expand the pattern-discovery method beyond the single (n+1)/n
ratio -- the canonical gates each add a lens (band unions, parity, thresholds,
place-values, complements, the phi bit-reversal), and the spirit is to hunt, by counting
and measuring, for whatever stable relationships the data actually carry, the way physical
constants and laws were found by observation. Then, mid-build, a sharper question: does it
make sense to fit a model per stock, rather than a universal one?

The second question reframes the first correctly. A per-stock fit is a description; a law
must be the same object for every stock, as the AND formula is identical for every AND
gate. So Level 17 does not fit 100 models -- it treats the 100 stocks as 100 independent
measurements of the same candidate constants and tests universality by data collapse, in
the manner of statistical physics: remove each stock's scale, and see whether one law
remains. Level 17 is self-contained; Levels 1 to 16 are untouched.

## The construction

`level17/scaling.py`. For each stock the clock's inter-turn gaps are rescaled by their own
mean (the per-stock scale removed, leaving a dimensionless distribution). The collapse test
pools all normalised gaps into a reference and measures each stock's Kolmogorov-Smirnov
distance to it. A universal law fit (exponential / lognormal / power-law, chosen by AIC)
is applied to the pooled normalised gaps; the self-similarity exponent alpha is measured
across stocks and reversal scales. Every claim is set against the return-shuffle.

## Result 1 — the gap distribution is universal, and it collapses

The per-stock mean gap ranges only 4 to 9 days at theta = 0.02: at a fixed relative reversal
scale, stocks already tick at similar rates, so there is little scale to remove. The
normalised gap distributions collapse onto one curve with a mean KS of 0.095 (max 0.154)
across the 100 stocks. One shape describes the whole panel, with a single per-stock scale
number. So the answer to "a model per stock" is no: there is one universal law, and the
only free number per stock is its mean rate.

## Result 2 — but the universal shape is marginal, not structural (the honest catch)

The pooled normalised gaps are best fit, on every reading, by a lognormal law (mu = -0.365,
sigma = 0.851). The catch, which the discipline of the programme requires stating loudly:
the return-shuffle -- same gap sizes, temporal order destroyed -- collapses onto the SAME
lognormal, and the real and shuffle pooled distributions differ by a KS of only 0.049. The
shape of the gap distribution is therefore a property of the sizes alone, present just as
strongly when time is scrambled; it is universal but it is a marginal artefact, not the
temporal structure. This is the fat-tail-marginal trap of bitacora 16 reappearing at the
level of the whole panel: a clean, universal, and structurally empty regularity. It must
not be sold as the mechanism.

## Result 3 — the universal structural constant is the exponent alpha

Where the market and its shuffle truly part is the self-similarity exponent alpha (the Fano
growth of burstiness across time-scales). Across the 100 stocks:

    theta = 0.01   alpha = 0.430 +/- 0.099
    theta = 0.02   alpha = 0.494 +/- 0.090
    theta = 0.04   alpha = 0.465 +/- 0.104
    theta = 0.08   alpha = 0.363 +/- 0.124

At fine scales alpha sits near one half, tight across the panel (a spread of about 0.09),
and it softens toward coarse scales. The shuffle has no self-similarity (alpha near zero).
This is the one market-wide constant that survives the null: a universal self-similarity
exponent of about a half, not a per-stock parameter, and structural rather than marginal.

## The universal model, as a scorecard

The market clock is one universal object, not a hundred, and it factorises:

- per-stock scale (mean gap, 4 to 9 days): the only free number per stock; a tick rate,
  not physics;
- gap-distribution shape (lognormal): universal, collapses on all 100 -- but marginal, the
  shuffle shares it (KS 0.049), so not the structure;
- self-similarity exponent alpha ~ 1/2: universal, tight at fine scales, structural -- the
  shuffle has none.

The honest reading of the assessor's constant-hunt: the search yielded exactly one
structural universal constant, alpha ~ 1/2, and it caught a universal-looking regularity
(the lognormal gap shape) that is in fact a marginal artefact. That is the method working
as intended -- a stable law and a rejected impostor, both reported. The earlier
model-dependent nested ratio r ~ 3.2 (Level 16) is, by the same standard, not a
representation-free constant: it is a parameter of one synthetic construction on a coarse
grid, and is not claimed as fundamental.

## Residuals and honesty

The collapse is moderate, not razor-sharp (KS ~ 0.1), and normalisation barely improves on
the raw gaps because the per-stock scale range is narrow at a fixed theta -- a genuine but
limited demonstration. Alpha is tight only at fine scales and softens at coarse ones, so
"a half" is a fine-scale universal, not a scale-free one (consistent with bitacora 17). And
the one clean universal shape is the marginal one. The structural universal is real but
modest: a single self-similarity exponent near a half, shared across a hundred diverse
stocks, and absent from their shuffles.

## The notebook

`notebooks/13_universal_law.ipynb` shows the collapse (100 raw gap curves scattering, then
falling on one curve after normalisation), the universal lognormal shape with the shuffle's
identical curve drawn on top (the marginal catch made visible), and the universal exponent
alpha with its error bars against the alpha = 1/2 line and the shuffle's zero. Executed end
to end from a foreign working directory: three embedded plots, zero errors.

## Verification

Reproduce: `python level17/exp39_universal_collapse.py` (writes
`results/exp39_universal_collapse.json`); `python notebooks/build_13.py` rebuilds the
notebook. Tests:
`python -m pytest level17 level16 level15 level14 level13 level12 level11 level10 level9 level8 level7 level6 level5 level4 level3 level2 tests -q`
is 137 / 137 (9 in `level17/test_level17.py`: gaps, the three law fits and their MLE
recovery, the proliferation exponent, unit-mean normalisation, the KS bounds, and the
collapse of a common shape across scales). Levels 1 to 16 untouched.
