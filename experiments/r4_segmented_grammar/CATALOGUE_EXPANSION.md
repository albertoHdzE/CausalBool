# Should the gate catalogue be expanded? — corrected analysis

**AUDIT02/P9-closure addendum, 2026-09-02.** Supersedes the conclusion of
`symmetry_closure_analysis.py` on the question of whether expanding the family
set is worthwhile. The closure *measurements* in that file stand; the
recommendation drawn from them does not.

## What I got wrong

I argued that expanding the catalogue to cover all 256 ECA rules is
self-defeating, because a 3-input truth table costs 2³ = 8 bits and a catalogue
of 256 costs log₂(256) = 8 bits to index. The arithmetic is right and the
conclusion does not follow. Two assumptions were wrong, and both were hidden:

**1. It assumed a uniform code over the catalogue.** Naming a gate costs
log₂(|catalogue|) only if every family is equally likely. Real usage is nowhere
near uniform. Measured on the 4,626-node biological corpus:

```
empirical gate entropy H(p) = 2.070 bits/node
uniform code over the same labels = 3.170 bits/node
```

Under a frequency-weighted prefix code, adding a *rare* family costs almost
nothing, while it saves the whole fallback cost every time that family occurs.
Expansion is close to free on the naming side.

**2. It assumed arity 3.** That is the ECA case, and it is the degenerate one.
Real biological in-degrees run to 7 and beyond:

```
in-degree :   0     1     2    3    4    5    6    7
nodes     : 245  1269  1162  674  444  329  223   98
mean LUT cost for a fallback node = 35.2 bits   (not 8)
```

## The corrected accounting

53.7% of corpus nodes (2,486 of 4,626) carry the label `CUSTOM`, which no
canonical family names, so each falls through to a raw LUT.

| | bits/node |
|---|---|
| current — names plus LUT fallback | **20.43** |
| expanded — every family nameable | **2.07** |
| saving | **18.36 bits/node**, ≈ 84,900 bits over the corpus |

The ECA question I answered is the one case where expansion genuinely buys
nothing. It is also the least relevant: k = 3 is exactly where naming cost and
table cost cross.

## What to expand, concretely

The `CUSTOM` set is not 2,486 unrelated functions. Decomposing the formulas:

```
operators inside CUSTOM formulas
  NOT 3092 · AND 1513 · OR 389 · LEQ 308 · GEQ 234 · EQ 232 · LT 43

built ONLY from AND / OR / NOT : 2079 / 2486 = 83.6%
```

So **one new family covers 83.6% of the gap**: the activator/inhibitor
disjunctive form — a disjunction of clauses, each requiring its activators high
and its inhibitors low. Examples from the corpus:

```
Z1 & Z2 & !W & !HEMGN & !FOXL2 & !SOX9
(SOX9 | DMRT1:2) & !FOXL2
(!DMRT1:2 & !SOX9) | (OESTROGEN & !DMRT1)
```

This is precisely `REGULATORY_DNF`, which **already exists in the Python
engine** (`index-deconvolution/src/causalbool.py`) and is the family the ECA
census found doing most of the work. What it lacks is the thing that would make
it a *family* rather than an escape hatch: a Wolfram closed form, a band
decomposition, a Φ-transport reading, and a derivation document with executed
witnesses at arity 2–6 — the same treatment the other twelve received in
`papers/method/derivations/`.

The residual ~16% (`LEQ`, `GEQ`, `EQ`, `LT`) is threshold logic over
multi-valued levels. That is a different object, not a Boolean gate, and it
matches the 512 multi-valued plus 407 threshold formulas already recorded as
unevaluable by construction (AUDIT02/H). It should stay out of scope, not be
forced into a Boolean family.

## Recommendation

Expand **12 → 13**, targeting `REGULATORY_DNF`, by the established method:
visual exploration → computational expression → formal closed form → derivation
document with elementwise witnesses. Do **not** target the 256 ECA rules; that
is a k = 3 curiosity with a provably zero payoff, and the coverage number it
produces would be uninformative for the reason set out in `P9`.

Three consequences worth stating before anyone starts:

1. It would move the ECA census: much of the 216/256 currently "requiring an
   extension" becomes "covered by family 13", because that extension *is*
   family 13 in all but formal standing.
2. It is an explicit **author gate** under `SUCCESSOR_PLAN_R4` — catalogue
   growth requires a dated amendment with the catalogue cost paid in code — and
   it would move A3.1's pinned expressivity.
3. The 18.36 bits/node figure is an **upper bound** on the saving. It assumes
   the new family names the `CUSTOM` functions exactly. The honest next
   measurement, before any claim, is what fraction of the 2,079 AND/OR/NOT
   formulas the closed form actually reproduces elementwise.

## Reproduce

```bash
venv/bin/python experiments/r4_segmented_grammar/symmetry_closure_analysis.py
```
