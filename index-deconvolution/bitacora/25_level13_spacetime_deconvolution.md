# Bitacora 25 — Level 13: Deconvolving the Market as a Spacetime Pattern (the b12 Obstruction Fixed, the Rule Still Absent)

Date: 2026-07-13
Status: complete and verified

## The assessor's idea

Rotate the oracle plot: put time on one axis, price on the other, and forget the units
-- it is scale-free, pounds or grams, it does not matter. What remains is a grid of
zeros and ones, an event at each buy or sell. That grid is the same kind of object the
programme deconvolves exactly for cellular automata and gene networks: an output
repertoire. So coarse-grain the value axis, treat the price-level pattern as a network's
behaviour, find its behaviour table and formula, and reconstruct the network -- a
cellular automaton with rules, recovered from a market.

The idea is sharper than it looks, because it targets the precise reason the earlier
attempt failed. In bitacora 12 the whole-pattern deconvolution died on markets because
raw prices never recur: every configuration was unique, so there was nothing to invert.
The scale-free coarse-graining is exactly what manufactures recurrence -- coarse price
levels repeat -- and so it makes the deconvolution well-posed for the first time. This
bitacora builds that, with the programme's control triad.

Level 13 is self-contained; Levels 1 to 12 are untouched.

## The construction

`level13/spacetime.py`. The scale-free symboliser maps each price to a coarse log-level,
symbol = floor(log price / h), with h the bin width in log units (the coarseness). It is
scale-free by construction: rescaling the series by a commensurate factor exp(k h) shifts
every symbol by exactly the integer k and leaves the transition structure identical
(for a non-commensurate factor the invariance is approximate, up to bin-boundary
reassignments -- an honest limitation of a fixed grid). The determinism analyser then
asks, for memory w, whether the next symbol is a deterministic function of the last w:
it reports the recurrence (fraction of windows that repeat -- the b12 obstruction), the
contradiction rate (fraction of recurring windows mapping to more than one next symbol;
0 is a deterministic rule, 1 is noise), and the predictive lift over the base rate.

## Result 0 — coarse-graining fixes the well-posedness (the real methodological gain)

Recurrence of length-2 windows, averaged over the twelve long series, against coarseness:

    h = 0.005   recurrence 0.785
    h = 0.010   recurrence 0.934
    h = 0.020   recurrence 0.982
    h = 0.040   recurrence 0.995
    h = 0.160   recurrence 1.000

Fine bins barely recur (the b12 wall); coarse bins recur almost surely. The assessor's
scale-free move does exactly what it promised: it converts the market from a stream of
unique configurations into one where configurations repeat, so the deconvolution finally
has something to invert. This is a genuine advance over bitacora 12, independent of the
answer it then gives.

## Result 1 — the control triad separates, once persistence is removed

The trap here is trivial persistence: a coarse price level barely changes from day to
day, so the raw predictive lift is large for a null reason (predict the current level),
and indeed the market's raw lift (+0.728) exceeds even the deterministic logistic map's
(+0.476), because the map is chaotic and jumps between levels while the market creeps.
Raw lift is therefore meaningless; the honest quantity is the lift *excess* over a
shuffle that keeps the marginal and destroys temporal order (the return-shuffle for the
market, a symbol-permutation for the logistic control).

    system                 contradiction   lift-excess over shuffle
    logistic map (det.)        0.609            +0.418
    MARKET (real)              0.921            -0.004
    market return-shuffle      0.908               --
    GBM                        0.940               --

The instrument works: it detects the logistic map's determinism as a +0.42 lift-excess
and a contradiction rate well below the noise floor. And it places the market at the
noise end on both axes.

## Result 2 — the market has no deterministic rule, even here

The verdict is decisive and negative. The market's lift-excess over its own shuffle is
-0.004, positive on only six of twelve series -- indistinguishable from zero. Its
contradiction rate, 0.921, equals its shuffle's, 0.908: coarse-graining bought
recurrence but not determinism. The coarse price-level dynamics are as ruleless as the
daily direction was; the scale-free (price x time) representation inherits the
unpredictability the programme proved four ways. The network the deconvolution returns
for a market is degenerate -- no essential dependence, a near-constant "stay put" map
plus noise -- while for the logistic control it is a genuine rule. So the beautiful
picture the idea paints is real as a construction and null as a discovery: the market's
rotated event grid is not the spacetime diagram of a hidden automaton.

This is the same lesson the whole programme keeps returning: the order in a market is
not in a deterministic local rule over its values, at any resolution we can reach; it is
only in the clustering of *when* its turning points fall (the self-exciting clock,
Levels 5 to 12), which is a statistical regularity, not a Boolean law. The assessor's
idea is the most rigorous form yet of the question "is a market a cellular automaton",
and the answer, now that the question is finally well-posed, is no.

## Honest residuals

Two. First, the positive control is a chaotic map coarse-grained off its generating
partition, so its own contradiction rate (0.61) is not near zero -- the instrument
detects determinism through the lift-excess, not through a clean zero contradiction; a
sharper control would strengthen the claim, though the separation is already decisive.
Second, this tests a local rule of small memory (w = 2) over a single coarse level track;
a richer neighbourhood (a genuine two-dimensional cellular grid with many cells updating,
rather than a single moving occupancy) is a heavier construction that the sparse,
single-trajectory nature of a price path does not naturally furnish. The negative is
stated for the natural reading of the idea; an exotic embedding is not ruled out, only
unmotivated.

## Verification

Reproduce: `python level13/exp34_spacetime_deconvolution.py` (writes
`results/exp34_spacetime_deconvolution.json`). Tests:
`python -m pytest level13 level12 level11 level10 level9 level8 level7 level6 level5 level4 level3 level2 tests -q`
is 107 / 107 (6 new in `level13/test_level13.py`: scale-free symbolisation for a
commensurate rescaling, coarser bins recurring more, zero contradiction on a periodic
sequence, high contradiction on noise, the logistic map reading more deterministic than
a random walk, and short-input safety). Levels 1 to 12 untouched.
