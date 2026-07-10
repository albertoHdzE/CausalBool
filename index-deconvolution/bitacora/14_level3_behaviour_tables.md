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

## Roadmap toward general rules (documented, not yet built)

1. Richer encodings and coarser time-scales, where a fractal backbone might exist;
   the Level 2 backbone search and this Level 3 decomposition are the instruments
   that would detect it.
2. A larger, longer dataset (the Yahoo max range returns monthly bars; a genuine
   twenty-year daily series needs a different source) to strengthen the fractal
   test.
3. Beyond Boolean gates: catalogue the mathematical formulae for a richer set of
   operations (shifts, reverses, mutations), then let the behaviour tables guide
   the synthesis of Turing-machine configurations, using complex networks as the
   controlled generator exactly as in the founding work.

## Verification

`python level3/exp10_behaviour_tables.py` reports the structured pattern
compressing, the random one not, and the market at the shuffle baseline. Tests:
`python -m pytest level3/ level2/ tests/ -q` is 30 / 30. Levels 1 and 2 are
untouched.
