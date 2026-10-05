# Plan — Notebook 19: BDM and index-set complexity, two codes for one question

## Context

Bitacora 43 (`index-deconvolution/bitacora/43_bdm_anatomy_initial_study.md`) recorded an
exploratory anatomy of BDM. The author challenged two of its statements:
(1) that BDM "can do things we cannot", since our generators ((L, Ω) plus a decision tree, or
a network) are programs whose length is a Kolmogorov-style upper bound; and (2) that simple
methods "emulate" BDM, which rested on one probe (Spearman 0.93, 600 strings of 96 bits).
The author asked for a notebook that explains every experiment in plain English, with strong
visuals, and that can serve as evidence for the papers. Decisions taken: **our side is two
measures, kept separate** (HID-v1 archive bits, and the certified two-part code where the
generator is known), and **every claim is pre-registered in a frozen protocol** before any
number is produced.

## Objective assessment of the author's claims (goes into the notebook's §0, verbatim in substance)

| claim | verdict | why |
|---|---|---|
| "BDM is the sum of the algorithmic probability" | **Partly.** | It is a sum of CTM values, and CTM = −log2(algorithmic probability). So it is a sum of *complexities* (−log of probabilities) of the distinct blocks, plus log2 of their counts. It is −log2 of a product of block probabilities with the order left out — not a sum of probabilities. |
| "Our generator is a program whose length approximates K from above" | **True, under two conditions.** | (a) The code must be complete and decodable in a fixed language; then its length bounds K up to the decoder's constant. HID-v1 archives meet this (independent decoder). (b) The *data* must be encoded, not only the mechanism: D_schema bounds the mechanism; for an observed diagram the bound is D(mechanism) + seed + steps. **Found during planning:** `imp_causalnet_paper.measure.two_part_code` prices the seed with `bdm_1d(seed)`, which is not a code length, so its "certificate" is not yet a certificate. Fixed in this work (step 1). |
| "We can do what BDM does — they are equivalent" | **Equivalent in kind; not shown equivalent in values; formally different.** | In kind: both return bits that estimate K, and with a literal fallback ours is defined on every string, and an exceptions list makes it graded under noise. So bitacora 43 was wrong to list "any object" and "noisy data" as BDM-only; the notebook corrects it. Formally different: ours is a complete code, hence an upper bound; BDM omits the arrangement term, so it is neither an upper nor a lower bound (C1: it sits ~10,000 bits under a counting bound). In values: unverified, and the only held-out test so far (HID-v1 confirm-v1) was *not_supported* (mean saving −0.045 bits/input bit against the baseline portfolio). Whether ours is the better estimator is an empirical question this notebook answers on known-generator objects. |
| "Simple methods emulate BDM" (my claim) | **Overstated; withdrawn pending test.** | One probe, one length, one block size. It must fail by construction on single-block strings (≤ 12 bits), where the distinct-block count is always 1 and all information is in CTM. The notebook tests it rigorously across regimes (§7 below). |

## Approach

### Step 1 — Enrich the owner (monolithic-code gate)
- Q1 owner: `src/description_lengths.py` (already owns `ctm_1d`, `bdm_1d`, `bdm_1d_partition`,
  `bdm_1d_trace`, `bdm_2d`, `schema_normal_form_length`, `encoded_bit_length`).
- Q2 existing copies: `imp-causalNet-paper/src/imp_causalnet_paper/measure.py`
  (`model_description_length`, `two_part_code`); ECA evolution owned by
  `index-deconvolution/src/ca_deconvolution.py::evolve_eca` (imp-causalNet has a second copy in `ca.py`).
- Q3 enrich, do not re-create. Add to the owner:
  - `block_code_parts(bits, block, shift=None, remainder=...)` → `{dictionary_bits, count_bits, arrangement_bits, header_bits}`; dictionary + counts reproduce `bdm_1d` to 1e-9 (asserted inside, like `bdm_1d_trace`); arrangement = log2(m!/∏n!) via `lgamma`.
  - `certified_eca_code(rule, initial_row, steps)` = `schema_normal_form_length` of the rule + self-delimiting literal seed (Elias-γ length + raw bits) + γ(steps). Decodability checked by a reference decoder in the test, not by assertion of a formula.
  - The subproject's `two_part_code` becomes a forwarder with the seed fix recorded as an erratum (pairwise diff of old vs new values over 256 rules printed before switching).
- Q4 guard: extend `tools/check_single_engine.sh` with the two new names; new test file
  `tests/analysis/test_bdm_anatomy_owner.py` (BDM identity, permutation invariance, log bound,
  certificate decodes for all 256 rules, planted-copy check); declare it in `tests/MUnit/MANIFEST.tsv`.

### Step 2 — Frozen protocol
`index-deconvolution/protocols/bdm_anatomy_v1/PROTOCOL.md` + `freeze.json` (sha256 of protocol,
owner sources, producer script). Contents: hypotheses, factors, seeds, sample sizes, statistics,
pass/fail rules, and what each outcome would mean. Frozen before step 3 runs.

**Hypotheses and pre-registered decision rules**

| id | hypothesis | test | supported if |
|---|---|---|---|
| T1 | Aligned BDM is invariant under any permutation of whole blocks | proof + 1,000 random permutations × all families | exact equality, 0 failures, denominator printed |
| T2 | Fixed-block BDM ≤ C_b + 2^b·log2 m | proof + length sweep | 0 violations |
| H1 | Dictionary+counts+arrangement ("complete block code") per bit on fair coins is stable over length; BDM per bit is not | N = 10^3…10^6, 20 seeds/length | complete-code slope CI excludes BDM's; BDM/N ratio max/min > 5 |
| H2 | The fill ratio m/2^b predicts where BDM can separate a structured from a random region | seam AUC over block 2–12 × length 64–4,096, 50 null strings per cell | logistic fit of "outside null band" on log(fill ratio) has AUC ≥ 0.9 on held-out cells |
| H3 | Single-cell perturbation sign/rank under BDM depends on 2-D grid position (exact-symmetry rolls) | all 256 ECA rules, 4×4 phases (roll both axes on a torus-safe crop), 100 cells, 5 seeds | per-rule sign-instability CI; reported per Wolfram class |
| H4 | Group-level conclusions survive grid phase; single-cell magnitudes do not | same data, aggregate over cell groups | group-sign agreement ≥ 95% while single-cell rank ρ < 0.5 |
| H5 | Simple emulators reproduce BDM rankings | see emulation test below | per regime, as below |
| H6 | On known-generator objects, the certified code is ≤ BDM wherever a mechanism is found, and BDM's excess grows with steps | 256 ECA rules × steps {16, 32, 64, 128} × 5 seeds | reported as a headroom map; no pass/fail, descriptive |
| H7 | Index-set recovery and BDM agree on seam location / rule separation exactly when the four agreement conditions hold (local, noiseless, equal size/alignment, group-level reading) | factorial: each condition broken one at a time | agreement drops only in the broken-condition arms |

**Emulation test (H5), the one the author challenged.**
- Emulators: E0 block-entropy foil; E1 distinct-block count at a flat price b bits; E2 E1 with a
  mean-CTM price; E3 zlib / lzma (`index-deconvolution/hierarchy/baselines.py` ledgers); E4 HID-v1
  archive bits (`hierarchy.infer`). Target: BDM at the same block.
- Regimes: length {8, 12, 24, 48, 96, 384, 1,536, 6,144} × block {4, 8, 12} × families
  {ECA rows, ECA space-time flattened, periodic, biased coin, counters/de Bruijn and shuffles,
  Boolean-network repertoires from the corpus, two-word orders}; ≥ 300 strings per cell, seeds pinned.
- Statistics: Spearman and Kendall with 1,000-bootstrap 95% CIs; **decision agreement** on the
  three published uses (which of two strings is more complex; seam located; perturbation sign).
- Pre-registered rule: E "emulates BDM in a regime" iff the lower CI bound of Spearman ≥ 0.95
  **and** decision agreement ≥ 95%. Reported as a regime map; no single global verdict.
  Prediction written in advance: fails at length ≤ b (single block); the question is where it starts to hold.

### Step 3 — Producer
`index-deconvolution/experiments/bdm_anatomy_run.py --quiet` reads `freeze.json`, refuses on a
sha mismatch, writes `index-deconvolution/results/bdm_anatomy_v1/<run-id>/` (JSON per hypothesis,
`MANIFEST.sha256`, run log). Background run; resumable by hypothesis.

### Step 4 — Notebook 19 (`notebooks/build_19.py` → `19_bdm_and_index_complexity.ipynb`)
Built with `_nblib` (`md`, `code`, `write_notebook`, `BOOTSTRAP`) like `build_15.py`; imports only
from the owner, `hierarchy`, and `ca_deconvolution`. Reads saved results; re-computes a pinned
sample of each table live and asserts equality. Plain English, British, no contractions.

| § | title | main visual |
|---|---|---|
| 0 | Claims register and the objective assessment above | table: claim → section → status |
| 1 | The objects, before any measure | gallery: every family rendered as bit images / CA diagrams |
| 2 | How BDM reads a string | the window walk drawn in place (`bdm_1d_trace`); `1111100000` corrected; bit 10 never read |
| 3 | Two thirds of a description (T1, T2, H1) | stacked bars dictionary / counts / arrangement per family; BDM/N vs complete-code/N over 3 decades with seed bands |
| 4 | Fooling BDM, and why | C1/C2 side-by-side renders with equal BDM and the order-cost bar; period × block heatmap with lcm contours |
| 5 | When a disruption point is visible (H2) | AUC heatmap (block × length) with the fill-ratio = 1 contour and null bands |
| 6 | Perturbation and the grid (H3, H4) | the same diagram under 4 grid phases, cells coloured by ΔBDM sign; instability per Wolfram class |
| 7 | Can something simpler emulate BDM? (H5) | regime map per emulator, CI-annotated; scatter panels at the failing and passing corners |
| 8 | Our two measures against BDM (H6) | headroom map: BDM − certified code per rule × steps; HID archive vs BDM vs literal |
| 9 | When the two methods agree (H7) | factorial panel: each agreement condition broken in turn |
| 10 | Formal statements | T1, T2, complete-code decodability, certificate bound — each with proof sketch and asserting cell |
| 11 | What is supported, what is not, what to claim in the papers | two lists, each item linked to a cell |

### Step 5 — Records
README row for notebook 19; bitacora 44 (results, errata to bitacora 43: the "any object/noise"
rows and the emulation statement); `record_decision` for the run id and verdicts.

## Critical files
- modify: `src/description_lengths.py`, `imp-causalNet-paper/src/imp_causalnet_paper/measure.py` (forwarder), `tools/check_single_engine.sh`, `tests/MUnit/MANIFEST.tsv`, `index-deconvolution/notebooks/README.md`
- create: `tests/analysis/test_bdm_anatomy_owner.py`, `index-deconvolution/protocols/bdm_anatomy_v1/{PROTOCOL.md,freeze.json}`, `index-deconvolution/experiments/bdm_anatomy_run.py`, `index-deconvolution/notebooks/build_19.py`, bitacora 44
- reuse: `ctm_1d`, `bdm_1d`, `bdm_1d_trace`, `bdm_2d`, `schema_normal_form_length` (owner); `evolve_eca` (`index-deconvolution/src/ca_deconvolution.py`); `baseline_ledger`, `infer`, `decode_archive` (`index-deconvolution/hierarchy`); probes in `bitacora/43_probes/` as seeds for the producer, not imported.

## Verification
1. `venv/bin/python -m pytest -q --tb=no` (new owner tests green; manifest guard `tools/check_test_manifest.sh` green; `tools/check_single_engine.sh` green, and red on a planted copy).
2. Freeze check: producer refuses when any frozen file is edited (planted edit test).
3. Producer run completes; `MANIFEST.sha256` verifies.
4. `jupyter nbconvert --execute` of notebook 19 with zero errors; every number in prose asserted by a cell; live re-computation samples equal saved results.
5. `make ci-local` before any push. Nothing is committed without the author's request.
