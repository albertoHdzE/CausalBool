# Bitácora 00 — Kick-off

**Date:** 2026-08-17
**Branch:** `clean`
**Status:** analysis and design only. No experiment has been run.

---

## 1. Why this package exists

The GWP3 mini-capstone replicated Alvi (2018) on an independent 199-month sample
and reached a qualified negative: the procedure reproduces, the magnitudes do
not, and the improved specification's headline accuracy of 75.9 per cent is
statistically indistinguishable from repeating last month's answer.

That is a useful negative, but it is a negative about a *probabilistic* method.
The CausalBool programme owns a different instrument — an exact, deterministic
index-set calculus with a closed-form description length — and it has never been
pointed at a forecasting pipeline of this shape. This package points it there.

The framing is deliberate and it is not machine learning. We are not looking for
a better classifier. We are asking whether causality in a time series can be
expressed as an index-set object at all, and if so, how much of a short
macro-financial sample that object can account for. The comparison against the
belief network is the instrument of that test, not the goal of it.

## 2. The decisive observation that motivates the work

GWP3 and the `index-deconvolution/` programme reached three of the same
conclusions from wholly unrelated starting points. Neither knew about the other.

| GWP3 conclusion | `index-deconvolution` finding |
| --- | --- |
| "Discretisation matters more than model choice" (conclusion 2). Parity emissions give regimes that switch in 189 of 198 months; log-return emissions give 52 switches and lift accuracy from 23.3 to 75.9 per cent. No change of scoring function, in-degree limit or prior came close to that effect. | **Level 4.** Four independent negatives had all used a single binarisation. Re-running the protocol across bit positions dissolved the negative onto a different unit: the sign bit is inert (autocorrelation *z* = +0.21, 3/23), the magnitude bit is the volatility unit (*z* = +1.40, 12/23, Hurst 0.665). |
| Balanced accuracy of the improved model is 41.7 per cent. It captures 21 of 21 stagnant months, 1 of 4 bear, 0 of 4 bull. Direction is what it cannot do. | **Levels 5–9.** Direction carries no memory beyond the fat-tailed marginal (driver excess −0.035, 4/12). Timing does: the clock forecast beats a marginal-preserving null 12/12, *p* = 2.4 × 10⁻⁴. |
| §8.2: "Use it to size risk, not to pick trades." | **Level 8.** No return alpha anywhere. But the 5 per cent CVaR of the next day is −4.64 per cent in high-clock periods against −2.60 per cent in low-clock, 12/12; vol targeting cuts maximum drawdown from −48 to −32 per cent. |

The GWP3 report's own future-work sentence — that trending macroeconomic series
"would probably do better discretised against a moving growth benchmark rather
than on the raw monthly change" — is a plain-language description of the Level 4
and Level 5 protocol. The bridge between the two projects was already built from
both banks. Nobody had walked across it.

## 3. Why the index-set method is structurally the right instrument

Four arguments, in descending order of strength.

**3.1 The parameter count.** The report's binding constraint (conclusion 5) is
sample size. A discrete belief-network node with *k* parents over three states
needs 3^k(3−1) free parameters, estimated from 139 months. That is why validation
selected a four-edge network, and why the eighteen configurations returned
anywhere between two and twenty-five edges. A gate has **no free numeric
parameters**: it is one of twelve named functions, or a REGULATORY\_DNF with a
handful of clauses. The adaptation converts estimation into a search over a
finite hypothesis class ordered by description length. This attacks the report's
own stated bottleneck directly, and it is the reason to expect the method to
behave differently rather than merely differently-labelled.

**3.2 Persistence is an attractor, not a prior.** GWP3 patches
non-persistence with a sticky Dirichlet prior — pseudo-counts of five on the
transition diagonal, following Fox et al. In a Boolean network, persistence is a
structural property: the attractor set, the basin sizes and |Im(F)| are exact
consequences of the fitted network, computed not tuned. The sticky prior is a
probabilistic surrogate for what an attractor supplies for free. Stating that
equivalence precisely is itself a contribution.

**3.3 Markov blanket becomes functional connectivity.** The improved network's
blanket collapsed to WTI\_CL alone, and §7 concedes that no bootstrap edge
stability was ever computed — the report judges claim 7 (policy relevance)
"partially achieved; the framework is appropriate, the evidential standard is
not". Deconvolution reports *functional* connectivity, the edges the dynamics
actually use, explicitly distinguished from structural connectivity; the
distinction was measured on 88 of 159 degenerate CANALISING nodes and it is a
genuine functional fact, not an error. Because the hypothesis class is small,
bootstrap stability over the whole class is cheap. That supplies exactly the
evidence the report says was missing.

**3.4 An interventional operator the belief network does not have.**
`index-deconvolution/src/reprogramming.py` computes exact Δ(image size) and
Δ(number of attractors) under node knockout, and it recovers real drivers in
biological networks (cyclins, caspases, myeloid factors; precision 0.67–1.00).
Applied to a fitted oil network the same operator asks: if the dollar were held
fixed, how much of the market's behavioural repertoire collapses? That is an
exact counterfactual sensitivity ranking of macro drivers. A posterior cannot
answer it.

## 4. The six adaptation designs

Recorded in full so that later work can be checked against the original reasoning.

**A — Drop-in replacement (the replication-grade comparison).**
Keep the GWP3 log-return HMM discretisation, the same splits, the same metrics.
Replace pgmpy hill climbing with an index-set network selected by two-part
description length, D(network) + D(residual). Per node, enumerate parent sets of
size ≤ 3 over the candidate bits and match against the twelve-gate family plus
compressed DNF. Produces a row-for-row extension of the report's Table 11. This
is the move that worked in `imp-causalNet-paper`, where the index-set mirror
recovered both cellular-automaton rules by number at 96.7 per cent on the
authors' own figure.

**B — Feasibility gate, before any modelling.**
Level 1's *contradiction rate* — how often the same input pattern maps to both
outcomes — is a falsifiability test that costs almost nothing. Run it on the
exact GWP3 splits with a cellular-automaton positive control alongside, exactly
as the four daily-equity negatives were run. If contradiction sits at the base
rate, the honest report is a measured negative and Design A is not attempted.
This precedes A in execution order even though A is the headline.

**C — Re-target from direction to the clock.**
Apply Level 5 directional-change pivots at a monthly-appropriate relative
threshold. The forecast target becomes the short-wait bit — whether the next
month contains a θ-reversal — rather than bear/stagnant/bull. Two advantages, the
second of them subtle. First, it targets the quantity that nine levels of work
say is forecastable. Second, it **repairs the base-rate pathology that made 75.9
per cent meaningless**: a median split is near 50/50 by construction, so the
persistence and majority benchmarks fall from 79.3 and 72.4 per cent to
approximately 50, and a modest edge becomes statistically visible on a short
window. The open question then becomes genuinely novel: does the dollar-and-rates
clock drive the oil clock? Level 6 found the equity clock largely shared
(R² ≈ 0.45) but not lead–lag predictive; the macro version is untested.

**D — Algorithmic-probability views for Black–Litterman.**
Claim 1 of the dissertation — replacing EGARCH-M views with model-derived views —
is judged *not achieved* in the report's Table 12, and §7.1 notes it would have
been the most valuable of the eight. A deterministic model appears to emit no
posterior, but algorithmic probability does: weight the top-*m* minimal-D networks
by 2^−D and obtain a distribution over next-state predictions with a principled
confidence. This delivers the one claim Alvi failed, by a route unavailable to
him, and it is cheap.

**E — Description length as the regime detector.**
Replace Baum–Welch entirely. A change point is where the description length of
the concatenated segment exceeds the sum of the separate descriptions. Online,
causal by construction, no Gaussian assumption, no restarts.
`index-deconvolution/level3/behaviour_table.py` and `lz76_complexity` already
exist. Gives a three-way version of the report's Table 8.

**F — Exogenous Hawkes for shock arrival.**
Level 9 fitted a three-parameter Hawkes process to the clock with branching ratio
*n* = 0.69 against a shuffle value of 0.01, beating Poisson out of sample by
0.059 nats per event, 12/12. The extension is a self-exciting kernel plus a
macro-driven baseline intensity, with *n* read as a fragility indicator (*n* → 1
is critical). This needs daily data; 199 months yields far too few pivots.

## 5. Risk register — what is expected to fail

Recorded now so that it cannot be recorded later as a discovery.

- **Four independent negatives already exist** at daily equity scale
  (contradiction rate, whole-pattern coverage, backbone search, behaviour-table
  LZ). The prior that price *direction* is not Boolean-deterministic is strong.
  Design C exists because of that prior, not in spite of it.
- **State-space coverage is hopeless at high node count.** Twenty-one nodes gives
  2²¹ states against 139 samples. Mitigations in order of preference: restrict
  in-degree to ≤ 2 or 3; use the pivot encoding to cut node count; pool across
  related commodities; move to daily.
- **A look-ahead trap specific to this encoding.** GWP3 caught Alvi's
  whole-window Viterbi producing a nominal 100 per cent one-month-ahead accuracy.
  Directional-change pivots carry the same class of error in subtler form: a
  pivot at time *t* is only *confirmed* once the reversal threshold is crossed at
  *t + k*. Any forecast feature must use confirmed-only, lagged pivots. This is
  the same discipline that caught the trend-contamination artefact at Level 4 and
  the fat-tail-driver artefact at Level 5, and it is the single most likely way
  for this package to produce a false positive.
- **Twenty-nine test months cannot demonstrate significance against
  persistence**, whatever the method: McNemar returned *p* = 1.00 for GWP3
  against both benchmarks, and the exact binomial interval on 75.9 per cent runs
  from 56.5 to 89.7. Success must therefore be redefined as one of: rolling-origin
  evaluation over the full sample; a target with a near-balanced base rate
  (Design C); or economic evaluation, as Level 8 did.

## 6. A substantive point about the panel

CPI, the federal funds rate and industrial production are not causal drivers of
the monthly oil price at this horizon. The report's own Figures 5 and 6 show them
collapsing onto a single state — CPI never leaves state 1, industrial production
spends 97 per cent of the sample in one state, the dollar index 88 per cent — and
the structure search then drops them. §4.2 states the consequence plainly: the
macroeconomic block is silenced before the belief network is even estimated.

Kilian's decomposition says the drivers are supply, global demand and
*inventories*. Alvi's expert seed knew this — six edges linking OPEC and
non-OPEC production and OECD and non-OECD demand to the spot price — but the
panel of seven never contained them. If the objective is a network in which the
word *causal* earns its place, the panel should acquire EIA crude inventories,
the rig count and the Kilian real economic activity index. Boolean gates are only
as good as the relevance of their inputs. This is deferred to Phase 3 so that
Phases 1 and 2 remain strictly comparable to GWP3.

## 7. Decisions taken at kick-off

1. **Deliverable shape.** Same format as the three sibling packages: own virtual
   environment, installable package under `src/`, executed notebooks, test suite,
   `FINDINGS.md` ledger, and — new to this package — a `bitacora/` logbook on the
   `index-deconvolution` pattern. The stated purpose is that a formal report or
   paper should be assemblable from the ledger and the logbook without re-deriving
   anything. Assessment of that proposal is in §8 below.
2. **Sequencing.** Replicate first for comparability, then re-target. Phase 1 is
   the drop-in comparison on Alvi's own terms; Phase 2 is the clock re-target;
   Phase 3 extends to daily frequency and an enlarged panel **regardless of the
   Phase 1 and Phase 2 outcomes**, because the frequency extension tests the
   method and not the market.
3. **Frequency.** Monthly first, at the original 199 observations and the
   original 139/30/30 chronological split, so that every number is directly
   comparable to the report's Tables 10 and 11. Daily afterwards.
4. **Framing.** The comparison exists to measure the power of the method. A
   negative that is measured, controlled and falsifiable is a result; an
   unmeasured positive is not.
5. **Reference material imported** from
   `/Users/alberto/Documents/projects/GWP_1/RiskManagement/`: the GWP3 pipeline,
   its `results.json`, its discretised frames, its LaTeX source, its
   twenty-five figures, and the 199×7 sterilised panel with the daily
   pulls held for Phase 3. All read-only.

## 8. Assessment of the deliverable-shape proposal

The proposal is that the six artefacts — virtual environment, package, executed
notebooks, tests, findings ledger, logbook — make the jump to a formal paper
easy, and that the paper is the ultimate goal.

**Agreed, with one qualification and one addition.**

The qualification is that the six artefacts guarantee *reproducibility*, not
*narrative*. The three sibling packages demonstrate both halves of this. Where
`imp-pathinfo-paper` carries a `FINDINGS.md` written as a ledger of claims with
their evidence, the transition to prose is nearly mechanical: the decisive
sentence of that package — every degree-driven measure correlates −0.82 with PUM
while the one non-degree measure drops to −0.29, therefore the paper's axis is
molecule size — is already a paper's abstract. Where a package accumulates
results without a claim-level ledger, the same material has to be re-read and
re-argued at writing time. The artefact that does the work is therefore the
ledger, and specifically the discipline of writing each entry as *claim →
evidence → status*, with negatives entered on the same footing as positives. The
other five artefacts protect the ledger from being wrong; they do not substitute
for it.

The addition is that this package needs one thing the siblings did not: an
explicit **pre-registration**. The siblings replicate a fixed published artefact,
so the target is externally defined and cannot drift. Here the target is our own,
and the space of encodings, thresholds, in-degree limits, gate families and
forecast targets is large enough that a positive result could be manufactured by
search without anyone intending it. The `index-deconvolution` programme already
caught itself twice this way. `PROTOCOL_causal_timeseries.md` therefore fixes,
before any run, the falsification criteria, the null models, the benchmarks and
the multiple-comparison accounting. Without that, the package would be publishable
only as an exploration; with it, the negatives become as citable as the positives,
which is the point.

One further remark on the ultimate goal. Two papers are already in flight — the
formal method paper and the computational paper with Zenil. This work is not a
third track competing with them. Its natural home is either a standalone applied
paper (*causal deconvolution of a macro-financial panel: an exact alternative to
probabilistic graphical models on short samples*) or, more efficiently, the
empirical section that the computational paper currently lacks outside biology
and cellular automata. That decision does not need to be taken now, but the
ledger should be written so that either destination remains open, which means
reporting effect sizes and nulls rather than only verdicts.

## 9. Immediate next actions

1. Stand up the virtual environment and the package skeleton; port the GWP3
   loader and splitter so that the 139/30/30 split is reproduced bit for bit and
   asserted in a test against `reference/gwp3/results.json`.
2. Write `PROTOCOL_causal_timeseries.md` and freeze it.
3. Run the Design B feasibility gate: contradiction rate and state-space coverage
   on the exact GWP3 splits, with the cellular-automaton positive control.
4. Report the gate outcome in `FINDINGS.md` before deciding whether Design A runs.
