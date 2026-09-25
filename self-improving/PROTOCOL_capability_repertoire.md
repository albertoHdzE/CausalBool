# PROTOCOL — the capability repertoire of a small language model

**Draft of 2026-09-25. It becomes frozen at the commit that removes this
sentence, and no experiment may run before that commit.** Amendments after the
freeze are permitted only as dated entries at the foot of this file, each with
its reason; a silent amendment invalidates the pre-registration.

The question is whether a small language model *can* answer a question, as
opposed to whether it *did* on one attempt. Repeated sampling answers it by
brute force (Brown et al. 2024, arXiv:2407.21787): draw k samples and see
whether any is correct. This protocol tests a different route. If a question is
a composition of categorised primitive skills, as the Doppel string was a
composition of categorised substrings, then the set of compositions the model
can solve at budget k is a Boolean function of the skill vector, and index-set
deconvolution can recover that function exactly and name it. The claim under
test is that this function is **short**, **skill-specific** and **predictive of
compositions never sampled**. Each of the three can fail independently, and the
controls below are fixed so that search over knobs cannot manufacture a
positive.

Place in the programme: this is the first technical-correctness stage toward
the goal stated in `README.md`, a local quantised model rediscovering index-set
deconvolution without clues.

Positioning: Zenil, Uthamacumaran and Ozelim (arXiv:2601.05280, local copy
`paper/`) argue that next-token objectives are lossy Shannon compressors and
that progress requires symbolic model synthesis. This is a measurement of the
model's capability boundary by exactly such a synthesis. It is not a claim
about the model's internal mechanism.

---

## 1. Standing rules

**R1 — Algorithmic measures only.** Complexity is reported as the index-set
program length and BDM, never as a Shannon quantity (author directives #96,
#117). Success probabilities appear only as sampling statistics, never as a
complexity measure.

**R2 — Every positive needs its marginal-preserving null.** The difficulty of a
composition obviously grows with the number of steps it contains. A result that
does not survive the null which preserves difficulty by step count (N1 below) is
reported as `NEGATIVE`, however small its description length.

**R3 — A positive control in the same run.** The pipeline, unchanged, is applied
to a simulated sampler with planted capability functions (§5). If it does not
recover them, the language-model result is uninterpretable and is not reported.

**R4 — Tautologies are not hypotheses.** y_k is monotone in k by construction
(§3), and on a fully sampled cube the recovered formula reproduces the table
exactly by construction. Neither is reported as a finding.

**R5 — Render the object.** Every reported y_k is shown as a 16 × 16 grid of
cells in Gray-code order, next to its null band, before any summary statistic
is quoted (datasaurus G1).

**R6 — No new owner.** Deconvolution, gate naming and description length are
loaded from their owners (§7). Code written here holds only what is particular
to this study: the task generator, the sampler and the binariser.

---

## 2. The task family

An instance is a list of six decimal digits drawn uniformly with a pinned seed.
There are m = 8 primitive stages, **always applied in this fixed order** when
present:

| bit | stage |
|---|---|
| x1 | sort ascending |
| x2 | reverse |
| x3 | rotate left by one position |
| x4 | swap the first and last elements |
| x5 | add 1 to every digit, modulo 10 |
| x6 | double every digit, modulo 10 |
| x7 | replace every digit d with 9 − d |
| x8 | drop the last element |

A **cell** is a skill vector x ∈ {0,1}^8, giving 256 cells. The cell x = 0 is
"return the list unchanged". The prompt lists the included stages as a numbered
list in the order applied, followed by the input and the line `Answer:`. The
ground truth is computed in Python and checked by exact match after strict
parsing of the first bracketed list in the output. Unparseable output counts as
a failure. The prompt template is committed verbatim with the freeze.

**Gate G0 — distinct cells.** Before any sampling, compute the answer of every
cell on every instance. Two cells whose answers coincide on all instances
cannot be told apart by any success data. Collisions are listed, and the
affected cells are flagged in every figure. If more than 8 of the 256 cells
collide, the stage set is revised by amendment *before* sampling.

---

## 3. Measurement

- **Instances.** 16 per cell, split into halves A and B of 8 each, with pinned
  seeds. Calibration uses a disjoint third seed.
- **Sampling.** Temperature 0.7, top-p 1.0, at most 64 new tokens. Each
  sample's seed is a pinned function of (cell, instance, sample index).
- **First-success time.** For each instance, sample until the first correct
  answer or k_max = 256, and record T (with T = ∞ if none succeeds). Stopping
  early loses nothing: success@k = [T ≤ k] for every k ≤ k_max.
- **Binarisation.** y_k(x) = 1 iff at least a fraction τ of the cell's instances
  have T ≤ k. **Primary τ = 1/2.** Results for τ = any (one or more) and
  τ = all are reported as sensitivity, never as the primary.
- **Budget grid.** k ∈ {1, 4, 16, 64, 256}.

**Gate G1 — test-retest.** y_256 computed from half A must agree with y_256 from
half B on at least 90 % of the 256 cells. Below that, binarisation at τ = 1/2 is
unstable for this model, and Stage B (§6) does not run.

**Model selection (declared knob).** Candidates are Qwen2.5-0.5B-Instruct,
Qwen2.5-1.5B-Instruct and Qwen2.5-3B-Instruct, with HuggingFace revision hashes
recorded at freeze. On the calibration seed, pick the **smallest** model whose
fraction of cells with y_256 = 1 lies in [0.2, 0.8]. A model outside that band
gives a near-constant function and tests nothing. If none qualifies, report that
and stop. The choice is made once, recorded, and not revisited.

**Runtime.** MLX (`mlx-lm`) on the local M3 Ultra, in a venv owned by this
subproject. Throughput is **not yet measured**. The Stage 0 smoke run measures
it, and the worst case (1,048,576 samples if no instance ever succeeds) is
reported against it before the full run starts.

---

## 4. Hypotheses

**H1 — the capability boundary is short and skill-specific (primary, Stage A).**
- **Statistic.** D(y_256) is the schema-normal-form length of the 256-cell table
  (`schema_normal_form_length`); BDM (`bdm_2d`) is reported alongside and never
  merged with it.
- **Null N1 (primary).** 1000 permutations with a pinned seed, each shuffling y
  **within each Hamming-weight class**. This preserves the success rate at every
  step count and destroys which skills matter.
- **PASS** if D(y_256) is below the 5th percentile of N1 **and** the recovered
  essential-variable set is not symmetric: the function is not determined by
  |x| alone.
- **NEGATIVE** if y_256 is a symmetric function of |x|. In that case "can it
  answer?" reduces to "how many steps?", which is a publishable finding and ends
  the skill claim.

**H2 — the boundary moves by skill, not only by count (descriptive).** Report
the essential variables and canonical gate of y_k at every k in the grid, with
the rendered grids. No PASS or FAIL: this is the Schaeffer et al. heavy tail
(arXiv:2502.17578), broken down by composition.

**H3 — the formula predicts unsampled compositions (primary, Stage B).** Run 20
pinned splits. In each, hold out 25 % of cells, stratified by Hamming weight;
fit on the rest; predict y_256 on the held-out cells. Predictors:
- (a) the deconvolved formula (requires T1, §7);
- (b) the best symmetric function of |x| fitted on the training cells;
- (c) L2 logistic regression on x, with C fixed at 1.0;
- (d) nearest neighbour in Hamming distance, with ties broken towards 0;
- (e) a question-only linear probe on the model's middle-layer residual stream
  at the last prompt token, trained on training-cell instances (after
  arXiv:2509.10625). The layer is fixed as ⌊L/2⌋ and not searched.

**PASS** if (a) beats (b) by at least 5 percentage points in mean held-out
accuracy, with a paired bootstrap 95 % CI over splits (10 000 resamples, pinned
seed) that excludes 0, **and** (a) is not worse than (c) by more than 2
percentage points. The comparison with (e) is secondary and reported whatever
its direction.

**H4 — reinforcement-tuned support is a subset of base support (exploratory).**
- Following Yue et al. (arXiv:2504.13837): the same pipeline on the base and
  Instruct checkpoints of the selected size.
- Both are given the same two fixed worked examples, so the prompts match.
- Report |y_256^inst ∖ y_256^base| and |y_256^base ∖ y_256^inst|, with their
  grids.
- No PASS or FAIL.

---

## 5. Positive control (R3)

The simulated sampler replaces the language model and nothing else.

**Planted functions.** Six are fixed now:
- AND(¬x1, ¬x6);
- CANALISING on x8 (x8 = 1 forces failure), else KOFN k = 2 on the complement of x2…x7;
- MAJORITY(x3, x5, x7);
- XOR(x2, x4) ∧ ¬x6;
- the symmetric threshold |x| ≤ 3, to check that N1 correctly calls it NEGATIVE;
- a random 3-input LUT on (x1, x5, x8), from a pinned seed.

**Per-instance success.** Each instance in a solvable cell has p ~ Beta(0.3, 3),
truncated below at p_min = 0.02; unsolvable cells have p = 0. T is geometric.

**The control passes** if:
- all five non-symmetric planted functions are recovered exactly (essential
  variables and gate) at k = 256, τ = 1/2;
- H1 calls the symmetric one NEGATIVE; and
- H3 predictor (a) reaches at least 95 % held-out accuracy on each planted
  function with at most 3 essential variables.

A failure blocks all reporting on real models.

---

## 6. Stages and stopping

| Stage | Content | Blocks on |
|---|---|---|
| 0 | G0 collisions; prompt and parser smoke; throughput; model selection | — |
| A | Full sampling; G1; H1, H2; positive control | Stage 0 |
| B | H3 held-out prediction; H4 | G1 PASS **and** T1 closed |

Stage A is complete on its own. A NEGATIVE H1 does not stop Stage B, because a
symmetric boundary can still be predicted, but it changes what B means, and the
report must say so.

---

## 7. Owners and tickets (monolithic-code)

| Concept | Owner | Use |
|---|---|---|
| Essential variables, reduced table, gate naming | `index-deconvolution/src/deconvolution.py` (`essential_variables`, `reduce_column`, `identify_gate`, `deconvolve_column`) | Stage A, loaded unchanged |
| Symbolic path, if m grows past table size | `deconvolution.py` symbolic API over `doppel-challenge/src/doppel_challenge/repertoire_program.py` | not needed at m = 8 |
| Program length, BDM | `src/description_lengths.py` (`schema_normal_form_length`, `bdm_2d`) | H1 |

**T1 (ticket against `index-deconvolution`, not solved here).**
`essential_variables` raises unless the column has length 2^n: the owner has no
notion of a **partially specified** function. H3 needs the minimum set of
essential variables consistent with the training cells, then gate identification
on the reduced partial table with don't-cares, choosing the shortest consistent
program. That algorithm belongs in the owner, with a parity guard that it equals
the present path whenever the table is complete. Stage B does not start until T1
is closed there.

**Permutation and bootstrap utilities.** Before any code is written, locate the
existing owner (Q1 of monolithic-code) under `src/stats/` and
`index-deconvolution/src/`. If none exists, the author decides where it lives.

---

## 8. Outcomes and what each would mean

| H1 | H3 | Reading |
|---|---|---|
| PASS | PASS | The capability boundary is a short symbolic object that predicts unsampled questions. This is the paper. |
| PASS | FAIL | The boundary is structured but does not extrapolate; compression without prediction. Report the gap. |
| NEGATIVE | PASS or FAIL | Capability is step count, not skill identity, for this family. Report this as a negative result. |
| control FAIL | — | Nothing is reported; the pipeline is repaired first. |

---

## 9. Artefacts

- `results/<run_id>/`: first-success times per (cell, instance) as the raw
  record; y_k tables; the null distributions; split indices; model and
  tokenizer hashes; the prompt template hash.
- `figures/`: y_k grids for every k, the N1 band, and held-out accuracy by
  predictor.
- Every number quoted in any write-up carries its reference distribution in the
  same sentence.

## References

1. Brown, B., Juravsky, J., Ehrlich, R., Clark, R., Le, Q. V., Ré, C. and Mirhoseini, A. (2024). Large Language Monkeys: Scaling Inference Compute with Repeated Sampling. arXiv:2407.21787.
2. Schaeffer, R., Kazdan, J., Hughes, J., Juravsky, J., Price, S., Lynch, A., Jones, E., Kirk, R., Mirhoseini, A. and Koyejo, S. (2025). How Do Large Language Monkeys Get Their Power (Laws)? *Proceedings of the 42nd International Conference on Machine Learning*, PMLR 267:53132–53176. arXiv:2502.17578.
3. Yue, Y., Chen, Z., Lu, R., Zhao, A., Wang, Z., Yue, Y., Song, S. and Huang, G. (2025). Does Reinforcement Learning Really Incentivize Reasoning Capacity in LLMs Beyond the Base Model? *NeurIPS 2025*. arXiv:2504.13837.
4. Moreno Cencerrado, I. V., Padrés Masdemont, A., Gonzalvez Hawthorne, A., Africa, D. D. and Pacchiardi, L. (2025). No Answer Needed: Predicting LLM Answer Accuracy from Question-Only Linear Probes. arXiv:2509.10625.
5. Lugoloobi, W., Foster, T., Bankes, W. and Russell, C. (2026). LLMs Encode Their Failures: Predicting Success from Pre-Generation Activations. arXiv:2602.09924.
6. Chen, L., de Melo, G., Suchanek, F. M. and Varoquaux, G. (2025). Query-Level Uncertainty in Large Language Models. arXiv:2506.09669.
7. Kadavath, S., Conerly, T., Askell, A. et al. (2022). Language Models (Mostly) Know What They Know. arXiv:2207.05221.
8. Zenil, H., Uthamacumaran, A. and Ozelim, L. (2026). Large Language Models As Shannon Lossy Compressors Not Solomonoff Induction Estimators: The Singularity Is Not Near Without Symbolic Model Synthesis. arXiv:2601.05280v5.
9. Holland, J. H. (1975). *Adaptation in Natural and Artificial Systems*. University of Michigan Press.
10. Almuallim, H. and Dietterich, T. G. (1991). Learning with many irrelevant features. *Proceedings of AAAI-91*, vol. 2, 547–552.
11. Yoran, O., Zheng, K., Gloeckle, F., Gehring, J., Synnaeve, G. and Cohen, T. (2025). The KoLMogorov Test: Compression by Code Generation. *ICLR 2025*. arXiv:2503.13992. (Companion test bed, not used in this protocol.)

## Amendments

(none)
