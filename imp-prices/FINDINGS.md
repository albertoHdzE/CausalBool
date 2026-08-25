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
| B4 | *Parsimony.* The selected index-set network has a strictly smaller description length than the belief network encoding the same conditional structure | D(network) in bits, both encodings self-delimiting | **`NEGATIVE`** — refuted twice: C15–C17 (degenerate encoding), then C19–C22 (real gate family, whole network, BDM) |
| B5 | *Stability.* Functional connectivity of the forecast node is stable under bootstrap resampling, where the belief network's edge set was not (A15) | Bootstrap edge frequencies over the full hypothesis class | **`NEGATIVE`** — refuted, C18. The belief network's separate *hash* instability is confirmed, C11–C14 |
| B6 | *Re-target.* On the near-balanced clock target, an index-set network beats the marginal-preserving null out of sample | Design C; return-shuffle null; sign test across thresholds | **`NEGATIVE`** — underpowered, not null: C26. 7/9 positive, mean excess +0.129, sign test p = 0.0898 |
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

**Evidence.** C1–C10 are carried by
`notebooks/00_reference_parity_and_feasibility.ipynb`, C11–C14 by
`notebooks/01_comparison_arm_and_orientation.ipynb`, and C15–C22 by
`notebooks/02_description_length_and_correction.ipynb` — all executed, 0 errors, 9
figures between them. Notebook 01's closing section carries the correction that
B4 later forced on it; notebook 02 answers B4 twice, keeping the first answer
visible because deleting it would hide how the conclusion was reached. Every figure and number is recomputed in the notebook, not
quoted from a script. `scripts/check_notebooks.py` verifies three things, each of
which has actually gone wrong here: no errors; no unexecuted cells (an aborted
nbconvert run leaves a notebook that passes an error-only check); and no
`application/vnd.jupyter.widget-view+json` outputs, which cannot be rendered
outside the session that produced them and leave a reader looking at "Could not
render content" where an output should be. pgmpy's `predict` raises a `tqdm.auto`
bar unconditionally, which produced 41 such outputs in notebook 01; it is now
suppressed in `predict_regimes`. Every number in the re-executed notebook is
unchanged.

### Phase 1 — B4, description length, and the stability comparison completed

Run 2026-08-18. `scripts/phase1_b4_description_length.py --boot 300`,
`results/b4_description_length.json` (content sha256 `160d8437a2eb20dc`),
`tests/test_index_set.py`.

| # | Claim | Evidence | Status |
| --- | --- | --- | --- |
| C15 | **B4 fails: the conditional probability table describes the panel in fewer bits.** Two-part code length on the 137 training months, both encodings selecting the same parent set {WTI\_CL}: index-set **153.63** bits (9.56 model + 144.07 data) against CPT **138.07** (26.10 model + 111.96 data), a margin of **15.56 bits**. Both beat the marginal baseline of 178.14, so the panel does contain compressible signal — the persistence of C8 — and the probabilistic encoding captures it better. The CPT spends 16.5 more bits on its model and buys 32 fewer bits of data | `test_b4_fails_the_cpt_describes_the_panel_in_fewer_bits` | `NEGATIVE` |
| C16 | **The verdict does not rest on the parameter-precision convention.** The prequential code length, which needs no such convention, agrees: over 125 scored months the CPT costs 116.50 bits against the index-set encoding's 134.90 (0.932 against 1.079 bits per month) | `test_prequential_agrees_so_the_verdict_is_not_a_precision_convention` | `CONFIRMED` |
| C17 | **The encoding is sound; the controls pass decisively.** On rule 110 the index-set code recovers the true parent set {c6, c0, c1}, makes zero errors, and costs **16.13** bits against the CPT's 48.46 and a marginal baseline of 200.85. On independent uniform ternary symbols **neither** encoding beats the marginal baseline (325.82 and 330.61 against 321.03), so the bit accounting is not biased in our favour | `test_rule110_is_compressed_by_the_index_set_encoding`, `test_neither_encoding_beats_the_marginal_on_noise`, Kraft checks on every code | `CONFIRMED` |
| C18 | **The second half of B5 fails, and it contradicts the argument of bitácora 03 §5.** On identical moving-block resamples with an identical candidate space, changing only the encoding that picks the winner: the index-set code length yields **22** distinct winning parent sets over 300 resamples (modal 26.7 per cent) against the CPT's **4** (modal {WTI\_CL}, 51.7 per cent); pgmpy's own hill climbing yields 6 over 120 resamples (modal {WTI\_Spot}, 37.5 per cent, with {WTI\_CL} second at 33.3). The index-set selection is **far less stable**, and its full-sample winner {WTI\_CL} is chosen in only 5.3 per cent of resamples. Diagnosis, visible in the accounting: a map costs log₂3 = 1.585 bits per pattern against the table's 2 × ½log₂137 = 7.098, so the index-set code under-penalises in-degree by a factor of 4.5 and over-selects | `test_index_set_selection_is_less_stable_than_the_cpt_selection` | `NEGATIVE` |

**Correction 2026-08-24 (AUDIT01/T2.1).** The hill-climb clause of C18 originally
read "yields **5** over 120 resamples (modal {WTI\_CL}, 55.0 per cent)". That triple does
not appear in the artifact this row pins (content sha256 `160d8437a2eb20dc`), whose
`bootstrap.hill_climb` block records **6 distinct winning parent sets over 120
resamples, modal {WTI\_Spot} at 37.5 per cent**, {WTI\_CL} second at 33.33. The row above
now quotes the pin. An executed re-check (`scripts/recheck_c18_hillclimb.py`; outputs,
log and environment fingerprint under `results/recheck_c18/`) additionally found the
statistic itself hash-seed-unstable — pgmpy's tie-breaking, the C13 mechanism, reaching
this block: across 45 fixed-rng executions of the committed code the same computation
yields 5–7 distinct winners, modal {WTI\_CL} or {WTI\_Spot}, at modal frequencies
35–55 per cent; exactly one seed of the 45 (19) reproduces the pinned map elementwise
and three (17, 33, 39) reproduce the originally printed triple. The C18 verdict is
unaffected: under every observed draw the index-set selection remains far less stable
(22 distinct sets) than either the CPT (4) or hill climbing (5–7).

**What survives, narrowly.** *Reproducibility is not stability.* The belief
network's C13 instability is *same data, same configuration, different answer*,
decided by string hashing — irreproducibility with no statistical content. The
index-set instability is *different data, different answer* — genuine sampling
uncertainty that the bootstrap surfaces rather than hides; the computation itself
is deterministic to the content hash. And there is no arrow to reverse in an
index-set model, so C13's specific pathology cannot arise. What does **not**
follow, and what bitácora 03 §5 wrongly implied, is that the choice of parents is
therefore more stable. It is less stable.

**Superseded.** The stability argument of `bitacora/03_comparison_arm.md` §5, the
pre-registered B4 claim, and the second half of the pre-registered B5 claim. All
three failed on measurements built to be capable of showing the opposite.

### Phase 1b — B4 redone with the method as it actually is

Run 2026-08-18. `scripts/phase1b_gate_network.py`,
`results/phase1b_gate_network.json` (content sha256 `290893e291e79cc3`),
`tests/test_gate_network.py`. Design pre-declared in `PROTOCOL` §1b **before** the
first run, after the assessor established that Phase 1 had used a counting
instrument and, more seriously, had not been applying the method: an arbitrary
lookup table where the method has seventeen named gates, one conditional where the
method has a network, and no BDM where all three sibling packages use it.

| # | Claim | Evidence | Status |
| --- | --- | --- | --- |
| C19 | **B4 is refuted again, with the real gate family, a whole 14-node network, and BDM.** Algorithmic two-part length, primary (thermometer) binarisation: gate network **933.0** bits against CPT network **904.5**, a margin of **+28.5**. Counting agrees at +51.1. The verdict holds on all three pre-declared binarisations (thermometer +28.5, binary +18.7, one-hot +13.3) and under both instruments, so it is an artefact of neither. BDM does *narrow* the gap relative to counting — it credits the gate network's structure — but does not reverse it | `test_b4b_the_cpt_still_wins_with_the_real_gate_family` | `NEGATIVE` |
| C20 | **Essentially nothing in this panel is gate-like — the deepest result of Phase 1b.** Named gates fitted: **0 of 14** nodes under thermometer, 1 of 14 under binary (REGULATORY), 2 of 21 under one-hot (CANALISING). Every other node falls back to a general lookup table. The family that names AND, XOR, MAJORITY, CANALISING and REGULATORY names almost nothing here, because the conditionals are not gate-shaped. This is the coding-side counterpart of C9: a gate is a deterministic object, and Gate 1.0 established there is nothing deterministic beyond persistence | `test_almost_no_panel_node_is_describable_by_a_named_gate` | `CONFIRMED` |
| C21 | **The controls pass decisively in both directions, so the comparison is sound.** Rule 110 as a 14-node network: the gate network fits it with **zero errors** at 258.94 bits against the CPT's 714.98 — a 456-bit win. On independent binary noise the gate network *loses* (+131.63) at a 46.3 per cent error rate, which is chance. The gate class covers 17 of 256 arity-3 functions (6.6 per cent) and random draws match at 6.5 per cent, so it tracks its own coverage and does not fit anything | `test_a_deterministic_network_is_fitted_exactly_and_wins`, `test_the_gate_network_does_not_compress_noise`, `test_the_gate_class_does_not_fit_anything` | `CONFIRMED` |
| C22 | **BDM's resolution is enforced, not assumed.** Separation between structured and random arrays: **32.6σ** at 14 × 14, 25.1σ at 14 × 8, **3.2σ at 4 × 4 — unusable**. This is why the scored object is the whole network rather than a single node's table, and the 4 × 4 limit is asserted in the suite so it cannot be quietly forgotten. ~~On the structure axis both matrices are 14 × 14 by construction, so size cannot confound, and there the gate network is *more* complex (BDM 156.45 against 123.37) and denser (23 edges against 17).~~ **The struck sentence is WITHDRAWN — see C29.** | `test_bdm_resolution_is_checked_not_assumed`, `test_structure_axis_requires_identical_shapes` | `CONFIRMED` (resolution) / `SUPERSEDED` (structure axis) |

### Datasaurus audit of the whole ledger (bitácora 07)

Run 2026-08-18 after the assessor identified Phase 2 as Datasaurus syndrome, using
the four gates of the `datasaurus` skill promoted from `deconv-lab`. Three infected
sites, three clean.

| # | Claim | Evidence | Status |
| --- | --- | --- | --- |
| C29 | **C22's structure-axis claim is 66 per cent density artefact and is withdrawn.** I matched *shape* (14 × 14) but not *density*, and density is a nuisance dimension BDM responds to. Random 14 × 14 matrices give BDM 189.39 ± 22.75 at 17 edges and 214.83 ± 17.40 at 23, so **+21.82 of the reported +33.08-bit difference is edge count**. What is true instead is more interesting: both networks sit far *below* random at their own density — gate 156.45 vs 214.83 (z = −3.35), CPT 123.37 vs 189.39 (z = −2.90) — so **both connectivity structures are ≈3σ more compressible than random and are not distinguishable from each other on that axis** | `bitacora/07_datasaurus_audit.md` §1 | `CONFIRMED` (replaces the withdrawn claim) |
| C30 | **C19's model terms were never in a common coordinate; the algorithmic number is demoted, the conclusion survives.** The gate's truth tables are 14 × 8 = 112 cells, the CPT's quantised parameters 14 × 32 = 448, and BDM grows with cell count. Against each object's own null at matched shape *and* density the figures are −29.94 and −485.84 bits, but that repair is encoding-dependent — 4-bit quantisation produces repeating low-order patterns that compress for reasons unrelated to the model. **BDM applied to two representations I chose cannot settle this.** The *counting* comparison (+51.1 bits, same sign on all three binarisations) involves no BDM and is untouched, so C19's conclusion stands on it alone. The size error ran against the CPT, so the verdict was conservative | `bitacora/07_datasaurus_audit.md` §2 | `CONFIRMED` |
| C31 | **The Phase 2 failure did not propagate backwards, and for a structural reason.** Gate 1.0's statistics are in-sample with no train/test split, so there is no overfitting penalty for a null to absorb: base rate 0.6642 against a self-block null mean of **0.6645**, a difference of +0.0002. C5–C10 are clean. C1–C4 are immune by construction — parity was asserted as elementwise equality of 3,124 individual numbers, never as agreement of a summary — and C20 ("0 of 14 nodes named") is a count of an elementwise property with no shape to hide | `bitacora/07_datasaurus_audit.md` §§4–6 | `CONFIRMED` |

**No headline conclusion changes.** B4 is still refuted, B6 still unsupported,
Gate 1.0 still explains GWP3's result. What changes is that two numbers used as
*supporting* evidence turn out to have been measuring density and array size.

**Provenance note 2026-08-24 (AUDIT01/T2.2).** C29's null existed only in prose;
the generating procedure (draw count, seed, sampler convention) was not recorded
and is not uniquely recoverable. Committed machinery now exists —
`experiments/c29_density_matched_null.py`, output
`results/c29_density_matched_null.json` (seeds pinned; N = 20,000 per cell) —
implementing the density-matched null in the two conventions matching the
observed objects (directed, zero-diagonal: uniform exact-k over the 182
off-diagonal cells; sensitivity: 196-cell placement). Recomputed moments land
close to but not exactly on the quoted ones (off-diagonal: 188.58 ± 22.54 at 17
edges, 212.26 ± 17.78 at 23; the prose values sit between the two conventions).
What reproduces under every principled sampler is the *conclusion*: the density
share of the +33.08-bit gap is 66–72 per cent, and both networks sit ≈3σ below
their own-density nulls (recomputed z −2.89 to −3.35 for matched conventions).
The quoted null moments should therefore be read as one unrecoverable scratch
draw; the committed script is now the single source for this null.

**The pattern, recorded because it is the actionable part.** Mechanical faults —
a leaky decoder, an unexecuted notebook, widget outputs, a runtime inside a
content hash — my checks catch reliably. **Interpretive faults — a mean that sums
an effect with a penalty, a BDM compared across densities, a BDM compared across
array sizes — my checks caught none of.** Every one came from an outside
challenge or a deliberate audit. The common shape is matching on the dimension I
had thought of while never enumerating the dimensions the statistic responds to.

**Relation to C15–C18.** Phase 1's numbers stand as measurements of a degenerate
encoding; only their *label* was wrong. C15 should be read as "an arbitrary-map
encoding loses", not "the index-set method loses". C19 is the claim that survives
scrutiny. C18's over-selection finding survives into the corrected design: on the
structure axis the gate network still selects a denser, more complex connectivity
and still loses.

**What is not claimed.** That the index-set method is unsuitable for financial
time series in general. The result is narrower: at monthly frequency, on seven
macro series binarised three ways, over 137 observations, at in-degree ≤ 3, the
conditionals are not gate-like and a probabilistic encoding describes them more
compactly. The rule-110 control in the same run shows the representation working
perfectly on a system that *is* deterministic, which localises the failure to the
data rather than to the method.

### Phase 2 — the clock re-target

Run 2026-08-18. `scripts/phase2_gate.py` (sha `b9f4826f1b86b6bc`),
`scripts/phase2_forecast.py` (sha `27c84648ccaf15cc`), `tests/test_pivots.py`,
`tests/test_clock.py`.

| # | Claim | Evidence | Status |
| --- | --- | --- | --- |
| C23 | **The confirmed-only pivot rule is enforced and it bites hard.** A directional-change pivot occurs at one time and becomes knowable at a later one; the lag is always ≥ 1 and is never assumed. On monthly WTI the mean confirmation lag runs from 1.3 months (θ = 0.05) to 5.3 (θ = 0.25), the maximum reaching **19 months**, and **31 to 52 per cent of the series** sits inside a window where a pivot has occurred but is not yet knowable. The leak is *exploitable*: a rule peeking at unconfirmed pivots predicts next-step direction at above 55 per cent against 50 for anything causal. The running median defining "short" is likewise causal, recomputed from the prefix in the tests | `test_the_leak_window_is_large_enough_to_matter`, `test_the_leak_is_exploitable_which_is_why_it_must_be_guarded`, `test_the_running_median_is_causal` | `CONFIRMED` |
| C24 | **The re-target achieves its design goal: the base-rate trap is gone.** Short-wait base rates of 0.396 to 0.467 on the panel, against the 66–73 per cent stagnant share that made raw accuracy uninformative on the regime target (A7, A11, A13). The encoding is also scale-invariant: multiplying every price by 37.5 leaves every pivot index and kind unchanged | `test_short_wait_target_is_near_balanced_by_construction`, `test_threshold_is_relative_so_the_encoding_is_scale_invariant` | `CONFIRMED` |
| C25 | **Gate 2.0 passes, barely.** Monthly WTI spot yields 57 legs at θ = 0.05, 39 at 0.08, 37 at 0.10, against a pre-declared minimum of 30; θ ≥ 0.15 fails. The daily series held for Phase 3 yields **322** legs at θ = 0.05 — a factor of six, and the single number quantifying what the monthly constraint costs | `results/phase2_gate.json` | `CONFIRMED` |
| C26 | **B6 is not supported: the sign is right, the sample is not enough.** Against a return-shuffle null passed through the entire pipeline, 7 of 9 monthly cells are positive with mean excess **+0.129**, sign test **p = 0.0898**. Two cells clear 0.05 individually, but with nine cells the chance of two or more doing so is 0.071, so they do not survive their own multiple-comparison accounting. Daily, shown for contrast, gives 3 of 3 positive, mean excess +0.093, no cell significant **[Caveat 2026-08-24, AUDIT01/T2.2: the daily cells were computed hours *before* the negative-price guard existed, on data containing −37.63; surrogates completed 170/151/130 of the requested 200 per cell (`results/phase2_forecast.json` `daily[*].n_surrogates`), the shortfall evidencing nan-propagation through the shuffle null — pre-guard numbers, superseded by the guarded pipeline]**. Test sets hold 10 to 19 decisions | `test_b6_is_not_supported_on_the_monthly_panel`; `results/phase2_forecast.json` | `NEGATIVE` (underpowered, not null) |

| C27 | **The Phase 2 headline statistic was a Datasaurus artefact, and is demoted.** Phase 2 was reported with no figures. On inspection: (i) the null's mean edge is ≈ **−0.115 even at matched test-set size**, and it is not noise but an **overfitting penalty** — a lookup table fitted on a random prefix scores ≈ 0.5 against a base rate of ≈ 0.58 — so the headline "mean excess +0.129" sums a real edge of ≈ +0.096 with that penalty and reports the total as one effect; (ii) surrogate test-set sizes are *not* matched (observed 12, surrogate median 14, range 7–18, matching in 22.5 per cent of cases), but conditioning on them barely moves the p-values (0.0050→0.0082, 0.1433→0.1319, 0.4393→0.4423), so the **rank-based tests are robust and the mean was the misleading statistic, not the test**; (iii) a suspicion of mine did *not* survive — I expected volatility clustering to give the real series systematically fewer pivots than its shuffle, and it does not at this resolution (z = −1.07, −0.73, +0.38) | `notebooks/03_phase2_clock_and_looking.ipynb` | `CONFIRMED` |
| C28 | **The pivots are economically real, so the negative is about the sample and not the representation.** Visual inspection against the price series recovers the turning points an analyst would name: the April 2011 peak at 113.39, the June 2014 peak at 106.07 that begins the shale collapse, the February 2016 bottom at 32.74, the December 2018 trough at 45.15 | same notebook | `CONFIRMED` |

**The honest summary of B6 is a count, not a mean.** **One cell of nine** reaches
significance (θ = 0.08, matched-null *p* = 0.008); with nine cells a Bonferroni
correction puts it at 0.074. The sign is consistently positive across ten of
twelve cells and the sample cannot establish it.

**C26 is a different kind of negative from Phase 1's.** Gate 1.0 measured
something and found it *absent* — the increment over persistence sat on its null
at −0.0003 to +0.0073, p from 0.32 to 0.64. Here the effect is consistently
positive, ten of twelve cells across both frequencies, and fails on **power**
rather than on sign. That is what a real effect looks like at this sample size,
and it is equally what a mild pipeline bias looks like; the distinction cannot be
drawn from 199 monthly observations and is not drawn by selecting θ = 0.08. The
direction agrees with the deconvolution programme's Level 5 result (same target,
same null, 12/12 at p = 2.4 × 10⁻⁴) — but that used twelve instruments over three
decades of daily data, and agreement in sign with prior work is encouraging, not
evidence.

**Status of the Phase 1 objectives.** B5 is **done** (C11–C14 for the belief
network, C18 for ours). B4 is **done and negative twice** — C15–C17 on the
degenerate encoding, C19–C22 on the method proper. Phase 1 is closed; Phase 2
carries the weight of the project, and now for a stated reason: the monthly regime
target has no deterministic structure, so no representation built on exact
functional dependence can win on it.

**What C1 licenses and what it does not.** It licenses every subsequent
comparison against GWP3's discretised frames, which is the shared input to both
the belief network and the index-set network. It does *not* yet cover the belief
network itself: `results.json` also holds `validation_grid_A/B`, `modelA/B/C`,
`benchmarks_test` and `inference`, and those remain unported. They are the
comparison targets of Phase 1, not of this gate.

### Phase 3 — opening: the data policy, found by rendering first

Run 2026-08-18. `scripts/fetch_daily.py`, `figures/phase3_g1_render.png`,
protocol §P3. The `datasaurus` gates were applied from the first action rather
than after the fact.

| # | Claim | Evidence | Status |
| --- | --- | --- | --- |
| C32 | **A relative-threshold method breaks silently on the 2020 negative oil price, and G1 caught it before any Phase 3 number existed.** WTI futures closed at **−37.63 on 2020-04-20**. Three simultaneous failures, none of which raises: the downturn test `p ≤ ext·(1−θ)` **inverts** when `ext` is negative, so any higher price "confirms" a reversal; `log` of a non-positive price is undefined, so the return-shuffle null propagates nan and retains only **2,627 of 6,524** path values; and the detector returned 550 pivots including a *trough* at −37.63. ~~with seven pivots inside a fifteen-day window — a burst of spurious reversals biasing towards the clustering hypothesis under test.~~ **The struck clause is WITHDRAWN — see C36.** `directional_change` now raises `NonPositivePriceError` | `test_non_positive_prices_raise_rather_than_produce_numbers`, `test_the_inequality_really_does_invert_on_a_negative_extreme` | `CONFIRMED` |
| C33 | **The exclusion pad is a knob and behaves like one (G3).** Dropping the print alone is insufficient: the neighbouring returns still carry a 60 per cent single-day move and the 26-year kurtosis stays at **51.8**. At pad = 5 it falls to 12.4, at pad = 20 to 7.3; pivot counts go 550 / 544 / 506 at θ = 0.05. Primary setting pad = 5, with every Phase 3 result to be reported at pad ∈ {0, 5, 20}. A result that depends on the pad is a result about April 2020 | `clean_prices`, protocol P3.3 | `CONFIRMED` |
| C34 | **The daily panel is fetched and its nuisance dimensions enumerated before any pooling (G2).** Six instruments: WTI, Brent, natural gas, heating oil, gasoline, and **gold as a non-energy control** — a clock result appearing equally in gold is not about oil. They differ in length (4,742–6,524), start (2000 vs 2007), price level (0.41 to 5,318), annualised volatility (0.179–0.611) and kurtosis (7.3–21.2 cleaned). WTI now gives **6,524 daily observations against the monthly 199** | `figures/phase3_g1_render.png` | `CONFIRMED` |
| C35 | **The pre-declared 1986 start is not achieved, and is recorded as a shortfall.** FRED was unreachable from this environment (HTTP/2 error, then timeout), so the panel comes from Yahoo v8 and reaches 2000, not the 1986 that `DCOILWTICO` would have given | protocol P3.5 | `NEGATIVE` (scope shortfall) |

| C36 | **C32's "burst of spurious reversals" is withdrawn: I made a Datasaurus claim while writing up a Datasaurus fix.** I reported seven pivots within fifteen days of the negative print and attributed the burst to it. Checked against a reference distribution I had not computed: 15-day windows hold 1.26 ± 1.12 pivots and **7 occurs in 2 of 6,478 windows (0.031 %)** — so the count is extreme, but it is **not caused by the print**. Six of the seven pivots sit at legitimate positive prices, the genuine 7-pivot window is in **March 2020** (47.18 → 31.13 → 34.36 → 20.37 → 25.22 → 22.43 → 24.49 → 20.09, the COVID crash), and it **survives cleaning at pad = 5 with max still 7**. The negative print contributes **exactly one** spurious pivot. The mechanical failures of C32 — inverted inequality, undefined `log`, a null retaining 2,627 of 6,524 values — were demonstrated by execution and stand; only the magnitude and the causal attribution were fabricated | this correction, computed against the window distribution | `CONFIRMED` (replaces the withdrawn clause) |

**Third instance of the same reporting failure**, after the Phase 2 headline mean
(C27) and C22's density artefact (C29). In all three the *code* was guarded and
the *narrative* was not: a number was computed correctly, looked striking, and was
given a causal reading with no reference distribution in the same sentence. The
guards live in the tests; the infection enters at the moment of writing prose.

**Provenance note 2026-08-24 (AUDIT01/T2.2).** C36's reference distribution also
existed only in prose; committed machinery now exists —
`experiments/c36_window_distribution.py`, output
`results/c36_window_distribution.json` — rebuilding it from `clean_prices`
(pad = 5) and `directional_change` (θ = 0.05) over the committed daily series.
Every quoted statistic reproduces exactly: 1.26 ± 1.12 pivots per 15-day window,
two windows holding 7 (0.031 %), max still 7 under cleaning, the negative print
contributing exactly one pivot (a trough at −37.63; the raw-series run yields
550 pivots, as C32 states). Two disclosures. First, all starts enumerated give
6,479 windows, not the quoted 6,478 — an off-by-one window enumeration in the
original scratch computation; no statistic is affected. Second, the quoted
March 2020 price sequence is the **raw-series** detector's episode: it ends at
the trough 20.09 (2020-03-30), which pad = 5 cleaning removes along with
everything after the guarded neighbourhood; under the current policy the same
episode's in-window extremes are seven, ending at 22.60. The pre-guard numbers
in this entry are retained as history; the guarded pipeline is authoritative.

### The visual pass — the objects drawn, and Phase 1 re-read through them

Run 2026-08-21. `notebooks/04_the_visual_pass.ipynb` (23 cells, 0 errors, 7
figures), `figures/04_*.png`. Built after the assessor required that the method's
own discovery order be restored: look at the distribution of ones and zeros
first, and let the table headers, the formulae and the statistics follow from
what was seen. Before this notebook the project held **one** figure in
`figures/` for all of Phases 1 and 2.

| # | Claim | Evidence | Status |
| --- | --- | --- | --- |
| C37 | **The binary object the method eats had never been rendered, and rendering it explains Phase 1 without any new statistic.** The 198×14 thermometer matrix shows four near-white columns and two solid ones at a glance. Run counts over 198 months: **CPI 1 and 1** (a literally constant column, both bits), Fed_Funds.not_bear **3**, USD_Idx **4 and 4**, Ind_Prod **5 and 5**; against **23–39** for the six crude-oil nodes. Four of seven series barely move at monthly resolution | `figures/04_A3_binary_object.png`, `04_B3_run_counts.png`, notebook §6b | `CONFIRMED` |
| C38 | **The panel is one crude-oil factor observed three ways, and the co-occurrence ordering finds this unprompted.** Hierarchical ordering on Hamming distance places the three `not_bear` oil nodes adjacent and the three `bull` oil nodes adjacent; WTI_CL, Brent_BZ and WTI_Spot are the same underlying object. So the Phase 1 parent search offered crude oil as the predictor of crude oil, plus four columns that do not vary | `figures/04_A4_column_order.png` | `CONFIRMED` |
| C39 | **The three-state HMM collapses to two states on three of seven series, and this is a property of the panel, not of the evaluation window.** Middle state occupancy is **0** for USD_Idx (175/0/23), CPI (198/0/0) and Ind_Prod (6/0/192). CPI's log-return dispersion is **sd = 0.00264** against WTI's **0.11726**, a factor of about forty-four; 29 non-convergence warnings fire during the fit. The collapse holds inside the 139 training rows alone | notebook §6, `discretise.RegimeDiscretiser` | `CONFIRMED` |
| C40 | **The support is thin, so most of the gate catalogue is unidentifiable on this panel.** Across all **364** node triples the median triple visits **5 of 8** corners of its cube, and the modal corner holds a median **0.697** of the rows. A gate is a labelling of all eight corners, so much of what separates one catalogue member from another is decided on corners the data never visits. This is a statement about what the panel can identify, not a defect of the method — and it should have been known before any gate was fitted | `figures/04_B2_support.png`, notebook §5b | `CONFIRMED` |
| C41 | **WITHDRAWN BEFORE PUBLICATION — "eight of fourteen nodes are frozen across the test window" does not survive its own reference.** Observed 8 of 14; a circular-shift null that preserves each column's run structure and randomises only where the test window falls gives median **6**, 5–95 pct **[4, 8]**, rank-based **p = 0.1100**. The figure is a restatement of the run structure of C37, not an additional finding. Recorded because the number was computed, looked striking, and was stopped at the gate rather than after the fact | notebook §6b, executed in place | `NEGATIVE` (withdrawn at the gate) |

**C41 is the first time the reporting failure was caught before the claim was
written**, rather than by the assessor (C27, C29) or by a deliberate audit (C36).
The mechanism was the rule that no number enters prose without its reference
distribution in the same sentence: computing the reference is what demoted it.

**What C37–C40 change.** Phase 1's verdict is unaltered — the panel carries no
predictive content for the one-month WTI regime beyond the regime's own
persistence (A11, 79.31 per cent) — but it now has a mechanism that can be seen
rather than inferred from a score: the candidate parents either do not move, or
they are crude oil under another name. No scoring rule, description length or
gate catalogue could have rescued that panel. This is a statement about the data,
not about the method, and it is the reason Phase 3 moves to daily resolution and
drops the macro covariates rather than carrying them along as decoration.
