# PROTOCOL — causality in time series by index-set deconvolution

**Frozen at kick-off, 2026-08-17, before any experiment.** Amendments are
permitted but must be recorded as dated entries at the foot of this file with the
reason; silent amendment invalidates the pre-registration.

The purpose of this document is narrow. The space of encodings, thresholds,
in-degree limits, gate families and forecast targets available to this package is
large enough that a positive result could be produced by search without anyone
intending it. The `index-deconvolution` programme caught itself twice — the
trend-contamination artefact at Level 4 and the fat-tail-driver artefact at Level
5 — and in both cases the control, not the intuition, did the catching. What
follows fixes the controls in advance.

---

## 1. Standing rules

**R1 — Strict causality.** No quantity used to predict month *t + 1* may depend
on any observation after month *t*. This applies to hidden-state decoding
(expanding-window Viterbi only, never whole-window), to any threshold, to any
normalisation, and to any pivot label. A directional-change pivot at time *t* is
confirmed only when the reversal threshold is crossed at *t + k*; forecast
features must use confirmed-only, lagged pivots. GWP3 caught a nominal 100 per
cent accuracy from exactly this class of error, and it remains the single most
likely route to a false positive here.

**R2 — Every positive needs a null.** The null is not a random baseline. It is
the *marginal-preserving* null appropriate to the claim: a return shuffle that
preserves the fat-tailed marginal and destroys time order for temporal claims; a
degree-preserving or label-permuting null for structural claims. A result that
does not survive its null is reported as `NEGATIVE`.

**R3 — Every method needs a positive control.** Any analyser applied to market
data is applied unchanged to a deterministic system — a cellular-automaton
trajectory, ordinarily rule 110 — in the same run. If the analyser fails to
recover the deterministic structure, the market result is uninterpretable and is
not reported.

**R4 — Falsifiability of the representation.** The gate family must not be able
to fit anything. The standing test, inherited from the legitimacy audit, is that
a random Boolean function of the same arity requires materially more DNF clauses
than a real gate (measured: ≈ 14.5 clauses for a random six-variable function
against 1 for AND and 3 for rule 30). Any new gate added to the family must pass
the same test before it is used.

**R5 — Multiple comparisons are counted.** Every threshold, encoding and
in-degree limit tried is recorded, including those that failed. Sign tests across
instruments or thresholds are reported with the number of trials that produced
them. The Level 2 backbone experiment reported coverage 0.009 at accuracy 0.458
and correctly called it a multiple-testing artefact; that standard holds here.

**R6 — Determinism.** Seeds pinned and recorded; two runs of any experiment must
agree to the digit.

**R7 — Negatives are results.** A measured, controlled negative is entered in
`FINDINGS.md` with the same weight as a positive and is not re-run in search of a
better number.

## 2. Phase 1 — the drop-in comparison (monthly, Alvi's own terms)

*Purpose: measure the method against a probabilistic graphical model on identical
ground. Comparability is the objective; forecasting performance is the
measurement.*

**Data.** `data/monthly/sterilized_monthly_data.csv`, 199 × 7, unmodified.
**Split.** 139 / 30 / 30 chronological, exactly as A1–A2.
**Discretisation.** The GWP3 log-return HMM, reproduced bit for bit and asserted
against `reference/gwp3/results.json` in a test before anything else runs.

**Gate 1.0 — feasibility, before any modelling.** Compute on the training window:

- the *contradiction rate*: over input patterns observed more than once, the
  fraction that map to more than one successor value;
- state-space coverage: distinct patterns visited against 2ⁿ, and the recurrence
  histogram.

Positive control: the identical analyser on a rule-110 trajectory, which must
return contradiction 0 and full recovery.

*Falsification criterion.* If the contradiction rate is not below the base rate
by a margin that survives a time-order shuffle, Phase 1 terminates and the
outcome is reported as a measured negative. Design A is not attempted, and Phase
2 proceeds regardless. This criterion is fixed now and will not be relaxed.

**Model.** Per node, enumerate parent sets of size ≤ 3 and match the reduced
truth table against the twelve-gate family plus compressed DNF. Select by
two-part description length, D(network) + D(residual), both self-delimiting.
Model selection uses the validation window only; the testing window is opened
once.

**Reported metrics.** Accuracy, balanced accuracy, macro F1, confusion matrix,
exact binomial interval, exact McNemar against persistence and against majority —
the same set as report Table 11, so that the two tables concatenate. Plus
D(network) in bits for both encodings, and bootstrap functional-connectivity
frequencies for the forecast node.

**What would count as a win.** Not a higher accuracy. Accuracy on this target is
capped by a 73.3 per cent stagnant base rate and a persistence benchmark of 79.3
per cent, on 29 months. A win is: equal or better balanced accuracy at a strictly
smaller description length, with a stable functional-connectivity set where the
belief network's edge set was unstable (A15). That is a statement about the
method, which is what this phase is for.

## 3. Phase 2 — the clock re-target

*Purpose: point the method at the quantity that nine levels of prior work say is
forecastable, on a target whose base rate does not defeat measurement.*

**Encoding.** Level 5 directional-change pivots at relative threshold θ, applied
to WTI spot and, separately, to the growth rate of each trending macro series —
the principled version of the report's own §4.2 recommendation. θ is swept over a
pre-declared grid and every value is reported (R5).

**Target.** The short-wait bit: whether the interval to the next confirmed pivot
falls below its running median. Near-balanced by construction, which is the
point.

**Null.** Return shuffle, which preserves the fat-tailed marginal and destroys
time order. Reported as edge over base *and* edge over null; only the second is
evidence.

**Open question, and the novel one.** Level 6 found the equity clock largely
shared across instruments (R² ≈ 0.45 from a leave-one-out common signal) but not
lead–lag predictive. The macro analogue is untested: does the dollar-and-rates
clock lead the oil clock? A positive here would be the first lead–lag clock result
in the programme and would not be a restatement of anything already known.

## 4. Phase 3 — frequency and panel extension

Runs **regardless of the Phase 1 and Phase 2 outcomes**, because it tests the
method rather than the market.

- **Frequency.** Daily WTI, held in `data/daily/`, extended backwards from FRED
  `DCOILWTICO` (available from 1986) using explicit `period1`/`period2` Unix
  timestamps on the Yahoo v8 endpoint — the `range=max` parameter silently
  downsamples to monthly, a trap already recorded in the programme.
- **Panel.** Add EIA crude inventories, the rig count and the Kilian real
  economic activity index. CPI, the federal funds rate and industrial production
  collapse onto a single state at monthly frequency (report Figures 5, 6) and are
  silenced before the network is estimated; Kilian's decomposition names supply,
  global demand and inventories as the actual drivers, and Alvi's own expert seed
  used production and demand variables that his panel never contained.
- **Evaluation.** Rolling-origin rather than a single hold-out, which is the
  report's own conclusion 5.

## 5. Deferred designs

Recorded so that they are not re-invented, and not run until Phases 1 and 2 close.

- **D — algorithmic-probability views for Black–Litterman.** Weight the top-*m*
  minimal-D networks by 2^−D to obtain a distribution over next-state predictions
  with a principled confidence. Delivers the one dissertation claim judged *not
  achieved*.
- **E — description length as the regime detector.** A change point is where the
  description length of the concatenation exceeds the sum of the separate
  descriptions. Online, causal, distribution-free.
- **F — exogenous Hawkes.** Self-exciting kernel plus macro-driven baseline
  intensity; branching ratio as a fragility indicator. Requires Phase 3 data.
- **G — attractors as regimes, knockout as intervention.** The fitted network's
  attractor set and basin sizes supply regimes without an HMM, and node knockout
  supplies an exact counterfactual ranking of drivers.

---

## Phase 1b — the corrected comparison (pre-declared 2026-08-18, before any run)

Phase 1's B4 compared a parent set plus an *arbitrary lookup table* against a
conditional probability table. That is not the index-set method; it is what the
index-set method was invented to replace. The gate family was not used, the
pivot/sumando factorisation was not used, the network was not built — one node
was modelled — and the deconvolution machinery was never invoked. The instrument
was a Shannon counting code, which is blind to structure by construction and
discontinuous with the three sibling packages, all of which use BDM.

Phase 1b repeats B4 and B5 with the method as it actually is. Everything below is
fixed before the first run.

### 1b.1 Binarisation (pre-declared, all variants reported)

The Boolean gate family requires bits. The three regimes are **ordered** by mean
monthly log return — that is how they are labelled — so the primary encoding is
**thermometer (ordinal)**, which preserves that order and gives each bit an
economic reading:

| regime | bit 0 = "not bear" | bit 1 = "bull" |
| --- | --- | --- |
| bear | 0 | 0 |
| stagnant | 1 | 0 |
| bull | 1 | 1 |

Two alternatives are declared now and **must both be reported** whatever they
show (rule R5): plain 2-bit binary (which admits an unrealisable code, 11), and
one-hot over three bits (which is redundant by construction). Reporting only the
best of three would be selection over encodings, which is the error Level 4
records and GWP3 conclusion 2 warns about.

Seven series × 2 bits gives **14 binary nodes**. Every node is a target, so the
object built is a network, not a conditional.

### 1b.2 Model class

For each target bit: a parent set of size ≤ 3 drawn from the 14 candidates, and a
**named gate** from the family implemented in
`index-deconvolution/src/causalbool.py` (AND, OR, XOR, NAND, NOR, XNOR, NOT,
IMPLIES, NIMPLIES, MAJORITY, KOFN, CANALISING, REGULATORY, REGULATORY\_DNF,
TRUE, FALSE), falling back to a general LUT only when no named gate fits better.

Real data will not match any gate exactly, so gates are fitted as **nearest
gates**: the gate minimising mismatches against the observed successor bit. This
is the approximate-gate idea already on the programme's roadmap, and it carries
the guard agreed there: an approximate gate must beat **both** the LUT
description length **and** the shuffle null, or it is overfitting and is reported
as such.

### 1b.3 Instrument — algorithmic two-part, not counting

    L(model) = BDM(model encoded as a discrete array)
    L(data | model) = residual code (index-set) or negative log likelihood (CPT)

This is the Kolmogorov structure function in the form the sibling packages use:
algorithmic on the model side, while still paying for misfit, so that neither an
empty model nor an unconstrained one can win by construction.

**Both models are encoded symmetrically as discrete arrays** so that BDM is
applied to like objects: the connectivity matrix, concatenated with the truth
tables (index-set) or with the probability tables quantised to the same
½log₂N-bit precision (CPT). Quantising the CPT is what makes the comparison
symmetric; without it BDM would be applied to a discrete object on one side and a
continuous one on the other.

**The object is the whole network**, a 14 × 14 connectivity matrix, not a
single node. This is both faithful to the method and necessary for the
instrument: BDM separates structure from noise by 17.9σ at 8 × 8 and 34.1σ at
12 × 12, but only 3.5σ at 4 × 4, so single-node objects are below its resolution.

The counting two-part code of Phase 1 is retained and reported alongside, as the
prequential code was, so that any disagreement between instruments is visible
rather than hidden.

### 1b.4 Controls — the verdict is void without them

- **Resolution.** BDM must separate structured from random objects *at matched
  size*. imp-pathinfo established that BDM can track size rather than structure,
  so the resolution control compares objects of identical dimensions and the
  size-matching is asserted.

  *Refinement, made before the first run.* Requiring identical dimensions of
  every BDM comparison would forbid the comparison itself, since a smaller model
  object is exactly what the parsimony claim asserts. The two questions are
  therefore separated and reported separately:

  - **Structure axis.** BDM of the two connectivity matrices, both 14 × 14 by
    construction. Identical shape, so any difference is structure and not size.
  - **Total axis.** The algorithmic two-part length, in which the table term is
    BDM of the truth tables for the index-set model and quantised parameter bits
    for the table model. Here the objects differ in kind — a discrete program
    against continuous parameters — and that asymmetry is intrinsic to the
    comparison rather than a modelling choice. It is stated wherever the number
    is reported, and the pure-counting variant is reported alongside so that a
    reader can see how much of any gap the instrument is responsible for.
- **Positive.** A deterministic system (rule 110 as a network) must be recovered
  with named gates and must win decisively.
- **Negative.** On independent noise, neither encoding may beat the marginal
  baseline, and the named-gate class must not fit noise better than chance.
- **Falsifiability of the gate class.** A random Boolean function of the same
  arity must require materially more description than a real gate — the standing
  test of rule R4.

### 1b.5 What Phase 1b can and cannot settle

It can settle whether the *method as actually defined* describes this panel more
compactly than a probabilistic graphical model, and whether its selection is
stable. It cannot produce price prediction: the target is a regime, and Gate 1.0
(C9, C10) already established that the regime is not predictable beyond
persistence at monthly frequency. That negative is instrument-independent and
Phase 1b does not revisit it.

### 1b.6 Declared in advance: what would count as each outcome

- **B4 upheld** if the index-set network's algorithmic two-part length is
  strictly smaller, with controls passing and the counting code agreeing in sign.
- **B4 refuted again** if the CPT wins under both instruments.
- **Instruments disagree** — reported as the primary finding, not resolved by
  preferring the flattering one.
- **C18 reversal is possible and is declared now**: the named-gate class has ~17
  members against 3^m arbitrary maps, so selection may prove more stable than
  Phase 1 found. If it does, C18 was an artefact of the degenerate encoding, and
  that is to be stated plainly rather than presented as a new discovery.

## Phase 3 data policy (pre-declared 2026-08-18, before any Phase 3 analysis)

Found by applying G1 — render the object at full length before quoting any
number — to the newly fetched daily panel, and demonstrated rather than assumed.

**P3.1 — non-positive prices are refused, not handled silently.** WTI futures
closed at **−37.63 on 2020-04-20**. A relative-threshold method is undefined
there and fails in three ways at once, none of which raises: the downturn test
`p ≤ ext·(1−θ)` *inverts* when `ext` is negative, so any higher price "confirms"
a reversal; `log` of a non-positive price is undefined, so the return-shuffle
null propagates nan and loses most of its path; and the detector returned 550
pivots including a *trough* at −37.63, with **seven pivots inside a fifteen-day
window** — a burst of spurious reversals biasing towards the clustering
hypothesis under test. `directional_change` now raises `NonPositivePriceError`.

**P3.2 — the declared handling is exclusion, never interpolation.** Inventing a
price where the market printed a negative one puts a number into the series that
nobody could have traded. `clean_prices` drops non-positive observations and
reports what it dropped.

**P3.3 — the exclusion pad is a knob, so it is swept and reported (G3).**
Dropping the print alone is *not* sufficient: the neighbouring returns still
carry a 60 per cent single-day move, and the 26-year kurtosis stays at 51.8. At
pad = 5 it is 12.4, at pad = 20 it is 7.3. The primary setting is **pad = 5**
(one trading week) and every Phase 3 result is reported at **pad ∈ {0, 5, 20}**.
A result that depends on the pad is a result about April 2020.

**P3.4 — the pooled panel's nuisance dimensions, enumerated before pooling (G2).**
The six instruments differ in length (4,742–6,524), start date (2000 vs 2007),
price level (0.41 to 5,318), annualised volatility (0.179–0.611) and kurtosis
(7.3–21.2 after cleaning). Any pooled statistic must be matched or conditioned on
these; a pooled sign test must state how many instruments and how many
independent decisions it rests on. `Gold_control` is included as a **non-energy
control**: a clock result that appears equally in gold is not about oil.

**P3.5 — data provenance.** FRED was unreachable from this environment
(HTTP/2 error, then timeout), so the daily panel comes from the Yahoo v8 endpoint
with explicit `period1`/`period2`, which reaches 2000 rather than the 1986 that
FRED `DCOILWTICO` would have given. The pre-declared 1986 start is therefore
**not achieved**, and this is recorded as a shortfall rather than quietly
substituted.

## Amendments

### A1 — 2026-08-18. Gate 1.0 statistic and null, following the controls.

Three changes, all forced by controls run before the market measurement, all
recorded here because §2 as frozen would otherwise have been silently replaced.
Full argument in `bitacora/02_gate10.md`.

**A1.1 — the operative statistic is lookup accuracy, not the contradiction rate.**
With three successor values, ten to fifteen recurring patterns and multiplicities
up to 44, the contradiction rate saturates: almost every recurring pattern
carries more than one successor whatever the data, so the observed value (0.70 at
best) sits *above* its own null and cannot discriminate. The contradiction rate
remains reported, and remains the operative statistic wherever recurrence is high
and the alphabet small — the rule-110 control returns exactly 0.0000 — but it is
not the criterion here. Lookup accuracy, the in-sample accuracy of the majority
lookup table, replaces it.

**A1.2 — the primary null is a circular shift, not a permutation.**
The permutation null of §2 destroys the successor column's autocorrelation as
well as its alignment. Two persistent but wholly independent processes align
spuriously over a finite sample, and a permutation null cannot reproduce that, so
it certifies the alignment as structure. Measured: on
`controls.persistent_random_frame`, which contains no cross-variable structure by
construction, the permutation null returned *p* = 0.0050. The circular shift
preserves the successor's marginal, autocorrelation, run lengths and clustering
exactly and destroys only the alignment; on the same control it returns
*p* = 0.4921. Both nulls are retained and reported, and both behaviours are
asserted in `tests/test_feasibility.py` so that a regression to the weaker null
cannot pass silently.

**A1.3 — the gate is decomposed, and the decisive test is the increment over
persistence.** §2 asked whether the panel contains deterministic structure. It
does — but the target's own lagged regime is part of the panel, and persistence
is already the benchmark of anchor A11, so an undecomposed test would have
certified the benchmark as a finding. The gate now reports four blocks (self,
cross, macro-only, unrestricted) and, decisively, a **covariate-shift null** that
asks whether adding any other variable improves on the target alone by more than
an unrelated variable would. A raw increment is positive by construction — any
extra parent raises in-sample lookup accuracy — so it is compared against the
surrogate increment, not against zero. This test has its own power control (a
true leading indicator: excess +0.1751, *p* = 0.0053) and its own size control
(an unrelated covariate: raw increment positive, *p* > 0.05).

**Effect on the verdict.** Gate 1.0 as literally worded passes; on its stated
intent it fails. Both readings are recorded in `FINDINGS.md` (C5–C9) and the
consequence for Phase 1 is set out there. No criterion was relaxed: the
replacement is strictly harder to pass than the original, as its own controls
demonstrate.
