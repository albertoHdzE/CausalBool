# Bitacora 13 — Searching for a Deterministic Backbone (Pivots) in Markets

Date: 2026-07-09
Status: complete and verified

## The idea

The assessor proposed: although the whole series is not deterministic, a filtered
subset of days might obey a deterministic rule (the pivots that match perfectly),
which the index method should reproduce exactly; the remaining days (the sumandos)
might then hide a further pattern, recursively, in a soft-fractal decomposition
like the pattern propagation found in the thesis work (doc/newIntPaper).

## The trap and the safeguard

Selecting the days where a rule already matches and then reporting a perfect match
is tautological: it is post-hoc selection. The legitimate test commits the rules
on training data (high-purity schemata over the lag-1 pattern, the pivots) and
applies them unchanged to unseen test days. A time-shuffle control (temporal order
destroyed) measures how much apparent determinism appears by chance and multiple
testing, and a deterministic cellular-automaton control shows the search recovers
a real backbone when one exists.

Implemented in `level2/schema_pockets.py` and `level2/exp09_deterministic_backbone.py`.

## Result

Out of sample, schemata with training purity at least 0.85 and at least eight
firings, support up to three inputs:

- Deterministic control (rule-110 cellular automaton): coverage 1.000, accuracy
  1.000. The search recovers the complete deterministic backbone perfectly.
- Real market (9 tickers, 752 days; base rate 0.539): coverage 0.009, accuracy on
  the covered days 0.458, an edge of minus 0.081 over the base rate.
- Time-shuffle control: edge minus 0.000, statistically indistinguishable from the
  real market.

The covered subset of the real market is not distinguishable from a
multiple-testing artefact; if anything its out-of-sample accuracy is slightly
below the base rate (weak anti-persistence on a handful of days, not robust). The
pivots that look perfectly pure in training do not survive out of sample.

## Conclusion

The recursive pivots-and-sumandos decomposition is a correct and powerful idea,
and the machinery proves it by recovering the full backbone of a deterministic
system. But binarised daily market data has no deterministic backbone to
decompose: the residual is irreducible at this resolution, so there is nothing for
the fractal recursion to act on. The soft-fractal hierarchy the thesis found for
single cellular-automaton and network patterns is a property of systems with real
internal determinism, which daily up-down market series lack.

This closes the deterministic-structure question for daily binarisation from a
third independent angle (after the contradiction rate of bitacora 06 and the
whole-pattern coverage of bitacora 12), all agreeing. The open frontier remains a
richer encoding or a coarser time-scale, where a backbone might exist and the same
search would find it.

## Verification

`python level2/exp09_deterministic_backbone.py` reports the CA control fully
covered at perfect accuracy and the market indistinguishable from its shuffle. The
CA backbone is locked into the suite; `python -m pytest level2/ tests/ -q` is
26 / 26. Level 1 is untouched.
