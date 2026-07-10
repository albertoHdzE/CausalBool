# Bitacora 12 — Level 2: Whole-Pattern (Multidimensional) Dynamics

Date: 2026-07-09
Status: complete and verified

## The two ideas, joined

The assessor asked whether the identifiability insights enhance the financial
test, and proposed a more advanced framework: treat the complete binarised
pattern as a single input whose one-step computation gives the next pattern, a
multi-tape or multidimensional view rather than independent per-node bits.

These are one question. The identifiability audit (bitacora 11) showed that
per-node recovery is defeated by confounding when inputs are correlated. The
whole-pattern view sidesteps per-node causal attribution by modelling the joint
transition directly. So the natural test of the insight is exactly the new level.

## Does confounding bite in finance? Yes

Across 23 tickers over 752 days the mean pairwise same-direction agreement is
0.563 and the maximum is 0.830: tickers co-move strongly, which is precisely the
correlation that confounds per-node causal attribution. And the pattern space is
almost empty: 739 distinct daily patterns of 8.4 million possible, with only 11
ever recurring. Both facts predict that neither the per-node view nor the
whole-pattern view can generalise.

## Level 2, implemented separately

`level2/` is a self-contained level that does not touch the Level 1 foundation.
It models the dynamics as a single map from the whole pattern to the next whole
pattern (`whole_pattern_lookup`), with a nearest-neighbour variant for unseen
patterns. Evaluation is out of sample.

## Result

Deterministic control (rule-110 cellular automaton, 9 cells): the whole-pattern
lookup is exact, per-bit 1.000 and exact-pattern 1.000, coverage 1.000. A
deterministic low-entropy system revisits its patterns, so the map generalises
perfectly. This confirms the level is a correct generalisation of the framework
to the multidimensional unit.

Real market (9 tickers, 752 days): per-bit accuracy 0.505 against a base rate of
0.539, exact-pattern 0.027, nearest-neighbour 0.508. The whole-pattern view does
not enhance the market prediction; it slightly worsens it. The market never
revisits a configuration, so no configuration-to-configuration map can
generalise. This is the curse of dimensionality, and it is why the Level 1
per-node factorisation, which estimates each function from all transitions, uses
the scarce data far more efficiently.

## Conclusion

The idea is sound and now implemented as a genuine, separate level. It is exact
where the theory demands it, on deterministic systems, and it makes explicit why
the market cannot be predicted this way: the whole-pattern map has essentially
zero coverage. Both levels agree, out of sample, that binarised daily markets
carry no exploitable deterministic structure, and the multidimensional level
supplies the sharpest reason for it. The framework now spans two levels: Level 1,
the exact per-node index deconvolution (the foundation), and Level 2, the
whole-pattern dynamics, which generalises to a multidimensional unit and is
validated on deterministic systems.

## Verification

`python level2/exp08_level2_patterns.py` reports the control exact and the market
at or below the base rate. Tests: `python -m pytest level2/ tests/ -q` is 25 / 25
(two new Level 2 tests plus the existing 23). Level 1 is untouched.
