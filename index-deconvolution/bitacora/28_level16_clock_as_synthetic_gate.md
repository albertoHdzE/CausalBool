# Bitacora 28 — Level 16: The Clock as a Synthetic Gate-Network, and Its Fractal Behaviour Formula

Date: 2026-07-14
Status: complete and verified

## The assessor's challenge, and the intelligence behind it

The assessor asked to close the loop back to the origin of the programme. The original
method took Boolean networks whose exhaustive output looked random and found, for each
node, an exact behaviour formula: it read the occurrence set (where the ones fall) as a
pivot plus an offset family (AND, the derivation in `02_cb_and.pdf`) or as a band-union
(OR, `02_cb_or.pdf`), and it noticed the spacing was self-similar -- a constant (n+1)/n
ratio column, a nested "repetitions of repetitions" run-length compression, the fractal
phi_K branch of Chapter 4 of the thesis. Knowing the gate, the formula was named.

The market clock is an occurrence set too -- the indices where buy and sell turns fall.
Since we have found it compressible in the classical (entropy) sense, the assessor's
challenge was to find its behaviour formula the same way, and, lacking a pre-built
network, to invent synthetic nodes and gates whose behaviour formula reproduces the
clock's structure. This bitacora does exactly that, and holds the result to the ground.

Level 16 is self-contained; Levels 1 to 15 are untouched.

## The honest boundary, stated first

A gate's behaviour formula is exact and deterministic because a Boolean network over an
exhaustive repertoire is deterministic. The market clock is not deterministic (proven
four ways), so it cannot admit an exact index-set formula, and indeed its behaviour
table's (n+1)/n ratio column scatters rather than locking to a constant -- there is no
exact gate. What we can do, and what the challenge really asks, is find the synthetic
construction whose behaviour formula reproduces the clock's self-similar SIGNATURE. The
match is distributional, not event-by-event; the turns stay stochastic.

## Three synthetic gate-networks, one discriminating test

`level16/synthgate.py` builds three constructions, each a reading of the gate picture,
and scores each by the Fano-factor self-similarity exponent alpha (F(T) ~ T^alpha; 0 is
flat/renewal, ~0.5 is the market). On the 100-stock panel, against the return-shuffle:

    construction                          Fano exponent alpha
    MARKET clock                                +0.494
    return-shuffle (null)                       -0.037
    superpose  (flat OR / band-union)           -0.029
    branching  (self-exciting cascade)          +0.247
    nested     (fractal phi_K, ratio r)         +0.499   (residual 0.017)

The reading is clean and discriminating:

- A flat band-union of independent scales -- the naive OR reading -- cannot produce
  self-similarity at all. Palm-Khinchin makes an independent superposition Poisson, so its
  exponent sits at zero, with the shuffle. The clock is not a flat union of scales.
- A plain self-exciting cascade -- the Hawkes reading of Level 9 -- clusters, but its
  exponent reaches only 0.25, under-shooting the market's 0.49. This is the same shortfall
  Level 9 reported (regenerated Fano 0.4 against a real 0.49); one branching timescale is
  not enough.
- The nested, fractal construction -- coarse bursts each subdivided into finer bursts by a
  geometric ratio r, the "repetitions of repetitions" of the behaviour table -- matches the
  market exponent to a residual of 0.017. It is the closest of the three on 99 of 100
  stocks (branching on 1, the flat union on none).

So the market clock's self-similarity is the nested / fractal branch of the method, not
the simple pivot-offset or band-union branch. The Fano curve confirms it across scales: the
nested construction tracks the market's rising Var/Mean line, while the flat union stays
flat and the cascade rises too slowly.

## The recovered behaviour-formula parameter: a fractal ratio

The nested construction matches when its geometric ratio r is tuned to the market. That r
is the clock's analogue of the behaviour table's constant (n+1)/n column -- the
self-similar spacing ratio. Across the 100 stocks it clusters tightly: median r = 3.20,
mean 3.23. This is a genuine recovered number, a behaviour-formula parameter for the clock,
comparable to the dyadic ratio (2, or 4 for alternate-node gates) that the canonical gates
carry. The clock is a fractal with a spacing ratio near three, shared across the market.

## What Level 16 establishes, and what it does not

- A discriminating, honest result on 100 stocks: the market clock's self-similarity is
  reproduced only by the nested / fractal construction (99/100), not by a flat gate-union
  (structurally impossible) nor a plain cascade (under-shoots). The clock's behaviour
  formula, in the method's own language, is the fractal phi_K structure -- a nested
  run-length with a recovered geometric ratio r near 3.2.
- This validates the assessor's intuition that the compressibility of the clock is
  formalizable, and it names the branch of the formalism it belongs to: the fractal one,
  the same "repetitions of repetitions" the thesis identified for the hardest gates.
- The residual is stated plainly: this reproduces the self-similar SIGNATURE and the
  burstiness, not the exact turns. It is a synthetic, distributional formula, matched on the
  Fano exponent; it does not predict individual events and does not resurrect direction. The
  match is of one exponent, made credible by the structural discrimination (two rival
  constructions cannot reach it) rather than by a single fitted number alone.

The natural continuation, noted for the next mind: test whether the fitted fractal formula
regenerates statistics it was not shown -- the gap distribution, the multifractal width --
and whether the recovered ratio r carries any cross-sectional meaning. That would turn a
signature match into a fuller behaviour formula.

## The notebook

`notebooks/12_clock_as_gate.ipynb` tells the whole story for a naive reader: the clock as a
rotated occurrence set with its behaviour table (the ratio column scattering, so no exact
gate), the Fano curve of the market against the three synthetic constructions, the
100-stock exponent bar chart, the recovered fractal-ratio histogram, and a side-by-side
raster of the real clock against the fitted fractal synthetic. Executed end to end from a
foreign working directory: four embedded plots, zero errors.

## Verification

Reproduce: `python level16/exp38_clock_as_gate.py` (writes
`results/exp38_clock_as_gate.json`); `python notebooks/build_12.py` rebuilds the notebook.
Tests:
`python -m pytest level16 level15 level14 level13 level12 level11 level10 level9 level8 level7 level6 level5 level4 level3 level2 tests -q`
is 128 / 128 (6 new in `level16/test_level16.py`: the flat superposition reading as flat,
the nested construction as self-similar, the cascade clustering less than the nested one,
the nested fit reaching a target exponent, determinism, and positive event counts). Levels
1 to 15 untouched.
