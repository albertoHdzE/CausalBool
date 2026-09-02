# Bitácora 04 — B4: the index-set encoding loses, and so does my argument

**Date:** 2026-08-18
**Status:** complete. 57 tests passing; `results/b4_description_length.json`
(content sha256 `160d8437a2eb20dc`), `results/b4_code_lengths.csv`.
**Ledger entries produced:** C15–C18.
**Supersedes:** the stability argument of bitácora 03 §5, and the pre-registered
expectation of B4 and the second half of B5.

---

## 1. The question and the hazard

B4 asks whether the index-set representation describes the same conditional
relationship in fewer bits than a conditional probability table. The hazard is
that a description-length comparison is **trivially riggable** by choice of
encoding, so three guards were fixed before the first run.

**Two-part, not model-only.** The quantity compared is
L(model) + L(data | model), the total cost of transmitting the successor column
to a receiver who already holds the evidence columns. Comparing model sizes alone
is meaningless: a model of zero bits that predicts nothing would win. A smaller
model that fits worse pays for it in the second term.

**The other side gets the favourable convention.** The conditional probability
table's parameters are transmitted at Rissanen's optimal precision, ½log₂N bits
per free parameter — the precision the Bayesian information criterion assumes.
Any coarser convention would have made our side win by construction.

**Controls decide whether the verdict counts at all.** A deterministic system,
where the index-set encoding must win by a wide margin, and independent uniform
symbols, where neither encoding may beat the marginal baseline. If the index-set
side won on noise, the accounting would be biased and every panel number void.

Every code is self-delimiting, and each is checked against Kraft's inequality in
the test suite rather than asserted to be a code.

## 2. The controls pass, decisively

| | marginal | index-set | CPT |
| --- | --- | --- | --- |
| **rule 110** (deterministic, binary) | 200.85 | **16.13** = 15.13 model + 1.00 data | 48.46 |
| **random** (uniform ternary) | 321.03 | 325.82 | 330.61 |

On rule 110 the encoding recovers the true parent set {c6, c0, c1}, makes **zero
errors**, and pays essentially nothing for data — 16 bits against the CPT's 48
and a baseline of 201. That is the behaviour the representation was designed for
and it is unambiguous.

On noise, neither encoding beats the marginal baseline. The accounting is not
biased in our favour, so the panel result is interpretable.

## 3. B4 fails

| the panel, 137 months | total | model | data |
| --- | --- | --- | --- |
| marginal baseline (no parents) | 178.14 | — | — |
| index-set, parents {WTI\_CL} | 153.63 | 9.56 | 144.07 |
| **CPT, parents {WTI\_CL}** | **138.07** | 26.10 | 111.96 |

**The conditional probability table describes the panel in 15.56 fewer bits.**
Both encodings select the same parent set, and both beat the marginal baseline —
so there *is* compressible signal here, and it is the persistence that Gate 1.0
identified. The probabilistic encoding simply captures it better.

The mechanism is visible in the decomposition and it is not subtle. The CPT
spends 16.5 more bits on its model and buys 32 fewer bits of data. A deterministic
map must pay a residual code for every month it gets wrong, and on a target that
is 66 per cent stagnant but not deterministic there are many such months. A
distribution over three symbols absorbs the same uncertainty far more cheaply
than a hard prediction plus a correction list.

**The verdict does not depend on the precision convention.** That was the obvious
objection, so the prequential code length was computed as well: encode the column
one symbol at a time, refitting on the prefix, with no parameter-precision
convention anywhere. Over the same 125 scored months the CPT costs 116.50 bits
against the index-set encoding's 134.90 — 0.932 bits per month against 1.079. The
two methods agree, which is the point of running both.

## 4. The stability comparison, and my error

Bitácora 03 §5 argued that the index-set method could not suffer the belief
network's orientation instability, because functional connectivity is exact
functional dependence rather than an orientation chosen by a tie in an aggregate
score. I labelled it explicitly as an argument from the method's definition
rather than a measurement, which was right, and said B4 would settle it.

It has settled it, against the argument. On **identical** moving-block resamples
of the same data, with the identical candidate space, changing only the encoding
that decides the winner:

| selector | distinct winning parent sets | modal set | modal frequency |
| --- | --- | --- | --- |
| index-set code length | **22** of 300 | Brent\_BZ+Fed\_Funds+WTI\_Spot | 26.7% |
| CPT code length | **4** of 300 | WTI\_CL | 51.7% |
| hill climbing (BIC-d, in-degree ≤ 2) | 5 of 120 | WTI\_CL | 55.0% |

The index-set selection is **far less stable**, not more. Its full-sample winner,
{WTI\_CL}, is chosen in only 5.3 per cent of resamples, and the modal bootstrap
winner is a three-parent set that the full sample does not select at all.

Resampling is by moving blocks of twelve months, not by individual observations,
because an independent bootstrap of a serially dependent series destroys the
persistence that dominates this target and would have made every selection look
far more stable than it is. That choice was made before the numbers were seen and
it works against the flattering answer.

**The diagnosis is in the accounting.** Per realised pattern, the index-set map
costs log₂3 = 1.585 bits; the CPT costs (a−1)·½log₂N = 2 × 3.549 = 7.098 bits, a
factor of 4.5. The index-set code therefore **under-penalises in-degree**: adding a
third parent creates 27 cells holding five observations each, the map fits each
cell's majority almost perfectly, and the residual code rewards it. The
representation's parsimony — the very property that motivated this whole package —
is what makes it over-select on stochastic data.

That is a real finding and it should be stated as one rather than explained away.

## 5. What survives, stated narrowly

Two things, and I want to keep them separate from each other and from what has
just been refuted.

**Reproducibility is not stability, and on reproducibility the index-set side
still wins outright.** The belief network's instability (C13) is of the form
*same data, same configuration, different answer*, decided by the interpreter's
string hashing. That has no statistical content whatever; it is irreproducibility.
The index-set instability measured here is of the form *different data, different
answer* — genuine sampling uncertainty, which the bootstrap makes visible rather
than conceals. The index-set computation is deterministic: two runs give an
identical content hash, asserted as a test.

**The orientation claim narrowly stands, and is narrower than I implied.** There
is no arrow to reverse in an index-set model — the map is from parents to
successor by construction — so the specific pathology of C13, two Markov-equivalent
graphs making opposite causal statements, cannot arise. That remains true. What
does not follow, and what I wrongly implied, is that the *choice of parents* is
therefore more stable. It is less stable.

**What is refuted.** The pre-registered B4 claim, that the index-set network would
have a strictly smaller description length. And the second half of the
pre-registered B5 claim, that its functional connectivity would be stable under
bootstrap resampling where the belief network's edge set was not. Both fail, both
by a clear margin, on measurements designed to be able to show the opposite.

## 6. Why this is consistent with everything before it, without being excused by it

Gate 1.0 established that the panel contains no deterministic structure beyond
persistence (C9, C10). B4 is what that looks like from the coding side: an
encoding built to express exact functional dependence has nothing exact to
express, so it pays a large residual and loses to a model that was designed for
uncertainty.

The temptation is to stop there and call B4 a confirmation of Gate 1.0 rather than
a defeat. That would be too comfortable. The CPT wins **on the same data**, and
both beat the marginal baseline, so the panel is not empty — it contains
compressible signal that a probabilistic encoding extracts and a deterministic one
does not. The correct conclusion is narrower and less flattering: on stochastic
data at this sample size, the index-set encoding is the wrong instrument, and its
advantage is confined to the regime the rule-110 control exhibits.

Whether that regime is reachable in a financial series at all is precisely what
Phase 2 asks, and it now carries the weight of the project. Phase 2 re-targets to
the clock, where nine levels of prior work found the structure that direction
lacks, and where the base rate does not defeat measurement.

## 7. Honest residuals

- The comparison is at in-degree ≤ 3 over seven ternary variables on 137 months.
  A different alphabet or a binarisation into the Boolean gate family proper —
  where the twelve named gates apply and a gate costs far less than a general map
  — is not tested here and could change the accounting. That is a real open
  question, not a defence of the present result.
- The residual code charges log₂(a−1) per error for which wrong symbol occurred.
  A cleverer residual model could exploit structure in the errors. Any such
  refinement must be pre-declared and must be run through the same noise control,
  since a smarter residual code is exactly how one would accidentally rig this.
- The two-part code is computed in sample. That is legitimate for MDL, which is a
  model-selection criterion, and the prequential figure is out of sample by
  construction and agrees.

## 8. Next

Phase 2, as pre-registered: directional-change pivots, the near-balanced
short-wait target, and the return-shuffle null. The confirmed-only pivot rule
(protocol R1) is the principal false-positive risk and is the first thing to
build.

---

## Addendum 2026-08-24 (AUDIT01/T2.1) — correction to §4's hill-climbing row

The §4 table row "hill climbing (BIC-d, in-degree ≤ 2) | 5 of 120 | WTI\_CL | 55.0%"
does not match the artifact this bitácora pins in its header
(`results/b4_description_length.json`, content sha256 `160d8437a2eb20dc`), whose
`bootstrap.hill_climb` block records **6 distinct winning parent sets over 120
resamples, modal {WTI\_Spot} at 37.5 per cent**, with {WTI\_CL} second at 33.33.
The corrected triple is therefore **(6, {WTI_Spot}, 37.5%)**, traced to the pinned
artifact and to the executed re-check below.

Executed re-check (`scripts/recheck_c18_hillclimb.py`; outputs, transcript and
environment fingerprint under `results/recheck_c18/`): re-running the committed
hill-climb block under a 45-value `PYTHONHASHSEED` sweep (rng seed fixed at 42,
120 resamples of block 12, BIC-d, in-degree ≤ 2) shows the statistic itself is
hash-seed-unstable — the C13 tie-breaking mechanism reaches this block. Outcomes:
5–7 distinct winners; modal set {WTI\_CL} or {WTI\_Spot}; modal frequency
35–55 per cent. Exactly one seed (19) reproduces the pinned map elementwise;
three seeds (17, 33, 39) reproduce the triple originally printed in §4, which
explains — without excusing — how the misquotation arose: numbers from an ad-hoc
re-run were written next to a pin pointing at a different draw.

§4's text above stands unmodified (no-retro-edit rule). FINDINGS.md's C18 row now
quotes the pin, with a dated correction note. The stability verdict is unaffected:
under every observed draw, 22 distinct index-set winners remain far less stable than
either the CPT's 4 or hill climbing's 5–7. The instability finding extends ledger
C13/C12: any future structural claim from this search must fix and record
`PYTHONHASHSEED` (see `results/recheck_c18/environment.txt` for the stack this
sweep ran on).

---

## Addendum 2026-09-02 (AUDIT02/Q1) — the mandate above is now implemented in the producer

The 2026-08-24 addendum diagnosed the hash-seed instability correctly and closed
with a rule: *"any future structural claim from this search must fix and record
`PYTHONHASHSEED`."* That rule was written but never wired into the producer.
`scripts/phase1_b4_description_length.py` still ran unpinned, so every
regeneration kept drawing a fresh sample and `results/b4_description_length.json`
remained one unlabelled draw rather than a result.

Found independently, by a different route: an arm-1 reproducibility sweep re-ran
every producer in the five replication packages and compared each committed
artefact elementwise. This one did not reproduce. Two invocations with identical
arguments gave `WTI_Spot @ 0.375` and `WTI_CL @ 0.4583` — both inside the 5–7
winners / 35–55 per cent band the August sweep had already mapped, which is a
cross-validation of that sweep rather than a new phenomenon.

Isolation, so the cause is named rather than assumed:

| candidate | verdict |
|---|---|
| resampling rng | not it — `np.random.default_rng(42)`, seeded |
| pgmpy `HillClimbSearch` | not it — deterministic *within* a process (six `learn_structure` calls on one frame agree elementwise) |
| `PYTHONHASHSEED` | **it** — pinning it makes repeated runs byte-identical, `content_sha256` included |

Two changes, both in the producer:

1. Re-exec with `PYTHONHASHSEED=0` when it is unset. The variable is read by the
   interpreter at start-up, so it cannot be set from inside a running process;
   re-exec is the only correct remedy. The value is now recorded in the output
   under `bootstrap.hill_climb.pythonhashseed`.
2. Tie-break `ranked` on the parent tuple, not on dict insertion order. With
   counts tied, `key=-count` alone left `ranked[0]` at the mercy of the order
   winners were first seen — a second, independent source of variation.

Verified: three fresh runs with no environment set by the caller agree
elementwise, `content_sha256` included.

`results/b4_description_length.json` has been regenerated at its own recorded
config (`--boot 300`). The pinned triple is now **(5, {WTI_CL}, 48.33%)**. The
CPT arm is unchanged at modal frequency 0.5167 over 300 resamples, confirming it
was always deterministic and that only the hill-climb comparator moved.

§4 and the 2026-08-24 addendum stand unmodified (no-retro-edit rule). The
stability verdict is unaffected: 22 distinct index-set winners remain far less
stable than the CPT's 4 or hill climbing's 5.

The `_curation_note` recorded in the previous artefact (AUDIT01/T2.0, duplicate
prequential rows, "regeneration queued as backlog") is discharged by this
regeneration. It is not carried into the new file, because the producer does not
emit it and hand-adding a field no producer writes is the practice this sweep
exists to catch.
