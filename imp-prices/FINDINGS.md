# FINDINGS — ledger of established results

Each entry is *claim → evidence → status*. Negatives are entered on the same
footing as positives. Nothing is entered here until it has been produced by code
in this package and can be re-run.

**Status legend:** `INHERITED` (established by GWP3, imported as a comparison
target, not ours) · `PENDING` (pre-registered, not yet run) · `CONFIRMED` ·
`NEGATIVE` (measured and null) · `SUPERSEDED`.

---

## A. Inherited anchors — the numbers this package must reproduce or beat

These come from `reference/gwp3/results.json` and the GWP3 report. Any Phase 1
comparison table must reproduce the left-hand column exactly before its
right-hand column can be believed.

| # | Claim | Evidence | Status |
| --- | --- | --- | --- |
| A1 | The panel is 199 monthly observations, 2010-01-31 to 2026-07-31, seven series, split chronologically 139 / 30 / 30 (69.8 / 15.1 / 15.1 per cent) | `data/monthly/sterilized_monthly_data.csv`; report Table 3 | `INHERITED` |
| A2 | Training 2010-01→2021-07, validation 2021-08→2024-01, testing 2024-02→2026-07 | report Table 3 | `INHERITED` |
| A3 | The three windows are not distinguishable on WTI spot log returns: KS *p* = 0.647 / 0.812 / 0.791, Levene *p* ≥ 0.921, Welch *p* ≥ 0.860 | report Table 4 | `INHERITED` |
| A4 | Parity emissions give a degenerate chain: WTI spot transition diagonal 0.000, 189 regime switches in 198 months, log-likelihood −92.37 | `results.json` → `hmm_parity/WTI_Spot`; report Table 7 | `INHERITED` |
| A5 | Log-return emissions give persistent regimes: average diagonal 0.742, 52 switches, log-likelihood 138.53 | `results.json` → `hmm_gaussian/WTI_Spot`; report Table 7 | `INHERITED` |
| A6 | Training-window regime economics: bear 30 months, mean log return −0.1289, vol 0.1463; stagnant 91 months, +0.0143, 0.0532; bull 17 months, +0.1518, 0.1350 | report Table 9 | `INHERITED` |
| A7 | Window composition, per cent bear / stagnant / bull: training 21.7 / 65.9 / 12.3; validation 23.3 / 63.3 / 13.3; testing 13.3 / 73.3 / 13.3 | report Table 5 | `INHERITED` |
| A8 | Replication model (parity emissions, duplicated forecast node, rolled forward): validation accuracy 13.33 per cent, testing 23.33 per cent — **below the 33.3 per cent of an uninformed guess** | report Tables 10, 11 | `INHERITED` |
| A9 | Alvi's own figures were validation 32.14 per cent and testing 57.14 per cent over 28 months; the magnitude does not replicate | report Table 10 | `INHERITED` |
| A10 | Improved model (target led one month, log-return emissions, BIC-d score, in-degree ≤ 2, unseeded, four edges): testing accuracy 75.86 per cent, balanced accuracy 41.67, macro F1 39.31, *n* = 29 | report Table 11; Figure 8 | `INHERITED` |
| A11 | Benchmarks on the same 29 months: uninformed guess 34.48, majority regime 72.41, **persistence 79.31 per cent** | report Table 11 | `INHERITED` |
| A12 | The improved model is not distinguishable from either benchmark: exact McNemar *p* = 1.00 against both; exact binomial interval on 75.86 per cent is 56.5 to 89.7 per cent | report §6.1 | `INHERITED` |
| A13 | The improved model answers "stagnant" in 26 of 29 months; it captures 21 of 21 stagnant, 1 of 4 bear, 0 of 4 bull | report Figure 10 | `INHERITED` |
| A14 | The expected-return rule (τ = 0.01) lowers raw accuracy to 68.97 per cent but raises balanced accuracy to 45.24 and macro F1 to 45.46; it issues 9 directional calls in 29 months and is right in 66.7 per cent of them | report Table 11, Figure 13 | `INHERITED` |
| A15 | Structure is unstable across the eighteen validated configurations: edge count ranges from 2 to 25 and the parents of the forecast node change with the scoring function. No bootstrap edge stability was computed | report §7, claim 7 | `INHERITED` |

**A11 and A13 together define the bar.** Any claim of predictive skill on this
target must clear persistence at 79.31 per cent on a comparable sample, or must
explain why balanced accuracy is the honest measure and clear it there.

## B. Pre-registered tests of this package

Fixed before any run. See `PROTOCOL_causal_timeseries.md` for the full criteria.

| # | Claim to be tested | Decisive evidence | Status |
| --- | --- | --- | --- |
| B1 | *Feasibility.* The discretised GWP3 panel contains deterministic Boolean structure: the contradiction rate over observed input patterns is materially below the base rate, and survives a time-order shuffle | Contradiction rate on the 139 training months, with a rule-110 positive control run through the identical analyser | `PENDING` |
| B2 | *Coverage.* The fraction of the 2^n input space visited, and the number of recurring patterns, are sufficient to identify gates at in-degree ≤ 3 | Coverage histogram; recurrence counts | `PENDING` |
| B3 | *Drop-in.* An index-set network selected by two-part description length matches or beats the improved belief network on the identical splits and metrics | Extension of report Table 11, with McNemar against persistence and majority | `PENDING` |
| B4 | *Parsimony.* The selected index-set network has a strictly smaller description length than the belief network encoding the same conditional structure | D(network) in bits, both encodings self-delimiting | `PENDING` |
| B5 | *Stability.* Functional connectivity of the forecast node is stable under bootstrap resampling, where the belief network's edge set was not (A15) | Bootstrap edge frequencies over the full hypothesis class | `PENDING` |
| B6 | *Re-target.* On the near-balanced clock target, an index-set network beats the marginal-preserving null out of sample | Design C; return-shuffle null; sign test across thresholds | `PENDING` |
| B7 | *Intervention.* Node knockout on the fitted network ranks the macro drivers, and the ranking is economically interpretable | Exact Δ|Im(F)| and Δ(attractors) | `PENDING` |
| B8 | *Frequency.* Every conclusion above is re-derived at daily frequency, where the sample constraint is relaxed by two orders of magnitude | Phase 3 | `PENDING` |

## C. Results of this package

| # | Claim | Evidence | Status |
| --- | --- | --- | --- |
| C1 | **The GWP3 discretisation pipeline is reproduced bit for bit.** The ported loader, splitter and hidden Markov discretiser agree with `reference/gwp3/results.json` on **3,124 independent numbers**: 161 fitted parameters per emission scheme across all seven series (transition matrix, initial distribution, state means, persistence, log-likelihood, and either emission probabilities or Gaussian means and standard deviations), 30 split-summary fields, and 2,772 decoded regime labels covering all three windows under both schemes. Tolerance 1e-4 absolute; no cell required it | `tests/test_reference_parity.py`, 19 tests, all passing. Environment pinned to the GWP3 versions (numpy 2.2.6, pandas 2.3.3, scipy 1.18.0, hmmlearn 0.3.3, scikit-learn 1.9.0) | `CONFIRMED` |
| C2 | Anchors A1, A2, A4–A7 are reproduced independently of the reference file: 199×7 panel; 139/30/30 split at the stated boundaries; parity persistence exactly 0.000 with 189 switches; Gaussian persistence 0.742 with 52 switches; Table 9 regime economics to four decimals; Table 5 window composition to one decimal | same suite | `CONFIRMED` |
| C3 | **Decoding is filtered, not smoothed**, and the check that establishes this has teeth. Truncating the sample at five points leaves every earlier label unchanged. A deliberately leaky whole-window Viterbi decoder, run through the identical check as a positive control, violates it | `test_decoding_is_filtered_not_smoothed` (swept over 5 truncations), `test_the_causality_test_has_teeth` | `CONFIRMED` |
| C4 | *Method note, not a result.* At a single truncation point the leaky decoder changed only 1 of 833 labels, so a one-point invariance test would have passed a decoder that leaks. The test was strengthened to a sweep before being entered here | run log, 2026-08-18 | `CONFIRMED` |

### Gate 1.0 — the pre-registered feasibility test

Run 2026-08-18, `scripts/gate10_feasibility.py --shuffles 1000`, 6.9 s,
deterministic. Statistic: lookup accuracy of the best majority table over parent
sets of size ≤ 3. Primary null: circular shift of the successor column, 126
surrogates enumerated exhaustively, so the attainable *p*-value floor is 0.0079.
Protocol amendment A1 documents the change of statistic and null.

| # | Claim | Evidence | Status |
| --- | --- | --- | --- |
| C5 | **The analyser recovers deterministic structure exactly and rejects its absence.** Rule 110 at width 7: contradiction 0.0000, lookup accuracy 1.0000, true parent set {c6, c0, c1} recovered, and it is the *only* exact parent set at in-degree 3. Independent uniform symbols: excess +0.0052, *p* = 0.386 | `tests/test_feasibility.py`, `control_rule110`, `control_random` | `CONFIRMED` |
| C6 | **The permutation null is unsound for persistent data, and was replaced.** On independent Markov chains with no cross-variable structure by construction, the permutation null reported cross-variable structure at *p* = 0.0050. The circular-shift null returns *p* = 0.4921 on the same data, while still detecting the genuine persistence in it (*p* = 0.0053, excess +0.1474) | `control_persistent_cross` vs `control_persistent_any`; asserted in both directions in the suite | `CONFIRMED` |
| C7 | **The panel is extremely sparse.** 138 training observations over a 2,187-state input space: 34 distinct states visited (1.55 per cent coverage), 15 recurring, maximum multiplicity 44. The contradiction rate is consequently saturated (best 0.70) and carries no discrimination at this alphabet size | `coverage`, `results/gate10_parent_sets.csv` | `CONFIRMED` |
| C8 | **There is structure, and it is persistence.** Target alone: lookup accuracy 0.7737 against a base rate of 0.6642 and a shift null of 0.6645, excess **+0.1092**, *p* at the floor (0.0079 — it beat all 126 surrogates). This reproduces anchor A11, the 79.31 per cent persistence benchmark, from an independent direction | `panel_self` | `CONFIRMED` |
| C9 | **Nothing in the panel adds to persistence.** Against a covariate-shift null that preserves persistence exactly and destroys only the covariates' alignment: adding all six other series gives increment +0.0365 against a surrogate increment of +0.0292, excess **+0.0073**, *p* = 0.323. The two oil futures: excess +0.0028, *p* = 0.504. The four macroeconomic series: excess **−0.0003**, *p* = 0.638. The test's power control — a genuine leading indicator — returns excess +0.1751, *p* = 0.0053 | `increment_all`, `increment_oil`, `increment_macro`, `control_increment_positive` | `NEGATIVE` |
| C10 | **The apparent cross-variable signal is the target under another name.** Unrestricted search gives excess +0.1035 at the *p*-floor, but WTI\_CL agrees with the target's contemporaneous regime in 87.7 per cent of months and Brent in 79.0 per cent, against 11.6 to 30.4 per cent for the four macroeconomic series. Macro-only search returns excess −0.0010, *p* = 0.512 — exactly null | `contemporaneous_agreement`, `panel_macro` | `CONFIRMED` |

**Verdict.** Gate 1.0 as literally worded **passes** (cross-variable structure
beats its null); on its stated intent it **fails** (nothing beats persistence).
C9 and C10 are the operative results.

**What this explains.** GWP3 anchor A12 records that the improved belief network
was statistically indistinguishable from persistence, McNemar *p* = 1.00, and
A10 records that its Markov blanket collapsed to WTI\_CL alone. That was reported
as a property of the fitted model. C9 and C10 show it is a property of **the data
at this frequency**: the panel contains no predictive content for the one-month
WTI regime beyond the regime's own persistence, for any model restricted to
in-degree ≤ 3 over these seven variables. The belief network was not badly
fitted. There was nothing there to fit.

**Consequence for Phase 1.** Running the index-set drop-in as a forecasting
contest would measure noise, and any accuracy it produced would be a restatement
of persistence. Under protocol §2 the forecasting comparison is therefore not
attempted. The parsimony and stability comparisons (B4, B5) remain meaningful and
cheap — they are statements about the *method* on a fixed target, not about
predictive skill — and are retained. Phase 2 proceeds as pre-registered,
unaffected.

### Phase 1 — the comparison arm, and its stability (B5)

Run 2026-08-18. `tests/test_belief_network_parity.py` (15 tests, 36 belief
networks fitted), `scripts/phase1_stability.py --seeds 20`,
`results/phase1_stability.json`.

| # | Claim | Evidence | Status |
| --- | --- | --- | --- |
| C11 | **The belief network arm is ported faithfully in every quantity that determines an outcome.** All 18 configurations of both specifications reproduce their validation accuracy and error exactly; the selected configuration, the selected skeleton, the Markov blanket of the forecast node, all validation and test scores including confusion matrices, the three benchmarks (uninformed 34.48, majority 72.41, persistence 79.31) and both exact McNemar tests (*p* = 1.00) match `results.json` cell for cell | `tests/test_belief_network_parity.py` | `CONFIRMED` |
| C12 | **Row-for-row parity of the validation grid is not achievable in principle, and the reason is a defect in the method rather than in the port.** pgmpy's greedy search breaks score ties in the iteration order of a hashed collection, so the same configuration on the same data returns a different graph in a different interpreter process. Across 12 hash seeds, exactly 3 of 18 configurations disagree with the reference on edge count, always by one edge, and **always under the BDeu score** — K2 and BIC-d are stable. 9 of 12 seeds (specification A) and 5 of 12 (specification B) reproduce every edge count; GWP3 did not record its hash seed and it cannot be recovered | `test_edge_count_discrepancy_is_confined_to_bdeu`; measured per configuration across seeds | `CONFIRMED` |
| C13 | **The selected causal graph is orientation-unstable; the forecast is not.** Across 20 hash seeds, specification B's selected configuration (BIC-d, in-degree ≤ 2, unseeded, 4 edges, validation accuracy 58.62) is stable, and so is its forecast blanket ({WTI\_CL}), but its **edge set takes two distinct values**. The two graphs share an identical skeleton and identical (empty) v-structure set, so they are **Markov-equivalent**, differing only in the direction of `Brent_BZ — WTI_CL` and `WTI_CL — WTI_Spot`. GWP3 Figure 8 presents the chain as WTI\_Spot → WTI\_CL → Brent\_BZ; the reverse orientation of both arrows occurs in the same code on the same data, decided by the interpreter's hash seed | `results/phase1_stability.json`; Markov equivalence verified by skeleton and v-structure comparison | `CONFIRMED` |
| C14 | Specification A's selected edge set *is* stable (1 distinct set over 20 seeds), as is its blanket. The instability is not universal; it is specific to where the score ties | same | `CONFIRMED` |

**Why C13 matters, and it is the strongest result of this phase.** GWP3 §7 judges
the dissertation's policy-relevance claim "partially achieved: the framework is
appropriate, the evidential standard is not", citing an edge count ranging from 2
to 25 across configurations and the absence of any bootstrap stability analysis.
C13 is a sharper version of the same criticism: the *selected* model's causal
orientation is not identified by the data at all. The predictive content survives
— the blanket is stably {WTI\_CL} and every score reproduces — but the arrow
directions, which are the only thing a policy audience would read off the figure,
are decided by an implementation detail with no scientific content.

This is a defect the index-set method does not share, and the reason is
structural rather than incidental. Functional connectivity in the index-set
calculus is defined by exact functional dependence — input *i* is connected to
output *k* if and only if flipping *i* changes *k* — which is a directed,
individually checkable fact about the dynamics, not an orientation selected by a
tie in an aggregate score. Where the data do not determine a dependence, the
index-set method reports the ambiguity as an explicit equivalence class rather
than resolving it silently. Establishing that this difference is real, and not
merely rhetorical, is the object of B4 and the remainder of Phase 1.

**Status of the Phase 1 objectives.** B5 (stability) is **done** and is C11–C14.
B4 (description length of the two encodings) is **not started**: it requires the
index-set encoder, which does not exist in this package yet.

**What C1 licenses and what it does not.** It licenses every subsequent
comparison against GWP3's discretised frames, which is the shared input to both
the belief network and the index-set network. It does *not* yet cover the belief
network itself: `results.json` also holds `validation_grid_A/B`, `modelA/B/C`,
`benchmarks_test` and `inference`, and those remain unported. They are the
comparison targets of Phase 1, not of this gate.
