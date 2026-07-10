# Bitacora 14 — Level 3: Gate-Agnostic Behaviour Tables and the Path to General Rules

Date: 2026-07-09
Status: foundation complete and verified

## The shift the assessor asked for

The primary discovery of the method was never which gate a node uses; it was how
the information of an output pattern is distributed: the pivots, the patterns
between pivots, and the patterns of patterns (the soft-fractal), which the UNAM
thesis expressed as decimals and sumandos in its behaviour tables (chapter 4).
Naming a gate was a post-hoc label. The generalisation is therefore to run the
behaviour-table analysis on any pattern, gate-agnostic, and let the
information-distribution structure speak. This is the foundation for expressing
patterns that have no gate name, and eventually for synthesising rules more
general than Boolean gates (shifts, reverses, and ultimately Turing machines).

## Level 3 foundation, implemented

`level3/behaviour_table.py` decomposes any binary pattern without assuming a gate:
the DecimalRepertoire (where it fires), the sumandos (the invariant bits, the free
offset dimension), the pivots (the essential place-value structure), the schemata
that tile the one-set, and a compression figure (how many ones each schema
accounts for). It also provides a one-dimensional reading for a time series: the
run-length signature and the Lempel-Ziv (1976) complexity. It reuses only the
Level 1 primitives and modifies nothing.

## Result (exp10)

- Structured control (AND of three of eight inputs): one-set 32, five sumando
  bits, a single schema accounting for all 32 ones. The behaviour table compresses
  the pattern exactly, gate-agnostically.
- Random control (256-bit column): fifty-two schemata, about two ones each. No
  compression, as it must be.
- Real market (nine up/down series): mean LZ(real)/LZ(shuffle) = 1.002. The series
  is as complex as its own shuffle, so at daily resolution it carries no fractal
  structure to compress.

This is the fourth independent line of evidence, after the contradiction rate
(06), the whole-pattern coverage (12) and the backbone search (13), now through
the information-distribution lens the assessor asked for. All agree: the daily
up/down binarisation has no exploitable structure, and the same instrument
compresses genuinely structured patterns perfectly.

## The wider vision (the target, now reframed)

The goal is not a coarser regime such as weekly; the cadence of the data is
irrelevant. The goal is a general procedure that, given any time series, extracts
its behaviour table, the way a machine-learning method is applied afresh to each
dataset, but grounded in algorithmic information theory rather than statistics.

Three commitments distinguish it from the short-string algorithmic-information
work of Zenil and colleagues, who summarise a short string by a single complexity
number.

1. The long-term whole picture. We do not seek one Turing machine that reproduces
   a pattern; we seek the set of local programs whose composition reproduces the
   full series: a library of local rules plus a schedule of where each applies.
   This is a decomposition of a long string into locally generated segments, an
   extension of the theory to the long-term regime that a single global complexity
   misses.

2. Noise is expected, so a perfect global fit is the wrong objective. The pivots,
   the points and segments where local determinism holds exactly, are the gold.
   The object of study becomes the distribution of the pivots along time: are they
   clustered, fractal-spaced, regime-like? That distribution is itself the
   behaviour table of the series and can carry information even where the direction
   is unpredictable.

3. Cadence and gate agnosticism. The same procedure applies whatever the sampling
   frequency and whatever the underlying operations (not only Boolean gates, but
   shifts, reverses, mutations, and ultimately arbitrary Turing-machine
   configurations, guided by the discovered behaviour tables, with complex
   networks as the controlled generator as in the founding work).

## First evidence: the pivots cluster in time (exp11)

The whole-picture view already yields a positive, honest signal where the global
view gave only negatives. Cutting each market series into non-overlapping windows
and scoring the local Lempel-Ziv complexity of each, the dispersion of the local-
complexity profile is larger for the real series than for its time-shuffle (ratio
1.076, with seven of nine instruments more clustered than their shuffle). Local
structure is not spread uniformly; it clusters in time, a structured distribution
of the islands of determinism, even though the daily direction is not predictable.
The effect is modest at this window and series length, and must be confirmed on
longer data, but it is real and it is in the right direction: the information is
in where the pivots fall, not in a global rule.

## Next steps

1. Characterise the pivot distribution properly: inter-pivot gap laws, clustering
   and self-similarity across scales, on longer series (a genuine multi-decade
   daily dataset; the Yahoo max range returns only monthly bars, so another source
   is needed).
2. Turn the local programs into an explicit set: segment the series, fit a short
   local program per segment, and study the library and its schedule.
3. Move beyond Boolean gates toward Turing-machine synthesis guided by the
   behaviour tables, keeping complex networks as the controlled validator.

## Verification

`python level3/exp10_behaviour_tables.py` reports the structured pattern
compressing, the random one not, and the market at the shuffle baseline. Tests:
`python -m pytest level3/ level2/ tests/ -q` is 30 / 30. Levels 1 and 2 are
untouched.
