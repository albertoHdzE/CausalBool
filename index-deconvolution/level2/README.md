# Level 2 — Whole-Pattern (Multidimensional) Dynamics

A separate, more advanced level that treats the complete binarised pattern as a
single multidimensional unit and models the dynamics as one map from the whole
pattern at time t to the whole pattern at time t+1, in one computation. It is the
"multi-tape / multidimensional node" view: instead of factorising the transition
into one Boolean function per node (Level 1, `../src`), the vector is kept whole.

This level does not touch the foundational Level 1 code. It exists to be compared
against it.

## Result (exp08)

- Deterministic control (rule-110 cellular automaton, 9 cells): the whole-pattern
  lookup is exact out of sample, per-bit 1.000 and exact-pattern 1.000, because a
  deterministic low-entropy system reuses its patterns. This validates the level
  as a correct generalisation.
- Real market (9 tickers, 752 days): per-bit 0.505 versus a base rate of 0.539,
  and exact-pattern 0.027. Treating the whole pattern as one unit does not help
  and slightly hurts, because the pattern space is astronomically sparse (739 of
  8.4 million patterns observed across 23 tickers, 11 ever recurring) and market
  transitions are not deterministic. This is the curse of dimensionality that the
  Level 1 per-node factorisation avoids by using the data far more efficiently.

## Why this matters

Both levels agree out of sample that binarised daily markets carry no exploitable
deterministic structure. The whole-pattern level makes the reason explicit: the
market never revisits a configuration, so no map from configuration to
configuration can generalise. The level is exact precisely where the theory says
it should be (deterministic systems) and honest where it cannot help.

## Files

    pattern_dynamics.py         whole-pattern lookup and nearest-neighbour models
    exp08_level2_patterns.py    control (CA) vs market comparison
    test_level2.py              exactness on the deterministic control

Run: `python level2/exp08_level2_patterns.py` and `python -m pytest level2/ -q`.
