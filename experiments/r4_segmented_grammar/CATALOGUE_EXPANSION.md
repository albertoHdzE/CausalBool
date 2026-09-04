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

**1. It assumed a uniform code over the catalogue.** ⚠️ **This argument is
WITHDRAWN — see the superseding section below.** It read:

> Naming a gate costs log₂(|catalogue|) only if every family is equally likely.
> Real usage is nowhere near uniform. Measured on the 4,626-node biological
> corpus: empirical gate entropy `H(p) = 2.070` bits/node against a uniform code
> at `3.170` bits/node. Under a frequency-weighted prefix code, adding a *rare*
> family costs almost nothing.

`H(p)` is a **Shannon quantity** and this programme is algorithmic. It is also
the wrong quantity for the question: a frequency-weighted code beats a uniform
one only if the decoder **already holds the frequency table**, and that table is
never transmitted — it is estimated from the very corpus being priced. Charging
`H(p)` per node charges for a model fitted to the data and then does not pay for
the model. The honest catalogue cost is the uniform `log₂ K`, because indexing
`K` families costs exactly that.

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

⚠️ **SUPERSEDED (AUDIT03/R1.3, 2026-09-04).** The table below is left visible
because deleting the evidence for a withdrawn claim is worse than marking it:

| | bits/node | |
|---|---|---|
| current — names plus LUT fallback | ~~20.43~~ | |
| expanded — every family nameable | ~~2.07~~ | Shannon `H(p)` |
| saving | ~~**18.36 bits/node**, ≈ 84,900 bits~~ | **do not quote** |

Two faults, not one. The naming term was an entropy. And the saving was charged
on **every** `CUSTOM` node, which assumes both that the new family reproduces
them all (coverage = 1, still unmeasured — that is `R4.1`) and that expansion
helps at every in-degree, which is false.

### The corrected accounting — pure program length

Measured by `audit/AUDIT03_R1_correct_the_record/catalogue_expansion_program_length.py`.
No entropy appears in it. `REGULATORY_DNF` is a disjunction of
activator/inhibitor clauses, which *is* a set of schemata, so its parameter
field is the schema-normal-form field already owned by
`src/description_lengths.py` — the thirteenth family needs no new cost model.

**Cost, exactly known:** `log₂13 − log₂12 = 0.1155` bits/node, charged to
**every** node because the gate field widens for all — `600.9` bits over the
5,204-node corpus.

**Saving:** unknown without the clause counts, so it is reported as a
**threshold** rather than invented. Both forms are priced *full and in a common
coordinate* — each pays `log₂(n+1)` for the in-degree and `log₂C(n,d)` to name
its inputs; the raw form then pays `2^d` and the schema form pays its clauses.
`s_max` is the largest clause count at which the schema field still wins:

| d | nodes | LUT full | 1 clause | s_max |
|---|---|---|---|---|
| 0 | 245 | 6.0 | 8.0 | **0 — never cheaper** |
| 1 | 1099 | 12.8 | 14.8 | **0 — never cheaper** |
| 2 | 502 | 18.1 | 19.1 | **0 — never cheaper** |
| 3 | 345 | 26.6 | 24.6 | 1 |
| 4 | 276 | 36.2 | 27.2 | 1 |
| 5 | 205 | 55.7 | 31.7 | 1 |
| 6 | 134 | 88.8 | 33.8 | 2 |
| 7 | 58 | 162.5 | 44.5 | 3 |
| 8 | 73 | 284.8 | 39.8 | 7 |
| 9 | 23 | 541.8 | 41.8 | 13 |
| 10 | 28 | 1064.9 | 53.9 | 20 |
| 11–13 | 4 | 2094–8223 | 30–60 | 36–186 |

**On `d ≤ 2` expansion can never pay — 1,846 of 2,992 reachable nodes, 61.7%.**
A raw table over one or two inputs is 2 or 4 bits; naming even one clause's
coordinates in an ambient `n ≈ 30–40` costs more than listing the answers
outright. The superseded figure charged a saving on every one of those nodes.

No net figure is quoted here, and none may be, until `R4.1` measures what
fraction of the formulas the closed form actually reproduces.

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
3. ~~The 18.36 bits/node figure is an **upper bound** on the saving.~~
   **Withdrawn with the figure (R1.3).** The replacement position: the *cost* is
   known exactly (600.9 bits), the *saving* is zero on 61.7% of reachable nodes
   and bounded by a per-in-degree clause threshold on the rest, and no net
   figure may be quoted until `R4.1` measures what fraction of the AND/OR/NOT
   formulas the closed form actually reproduces elementwise.

## Reproduce

```bash
venv/bin/python experiments/r4_segmented_grammar/symmetry_closure_analysis.py
```
