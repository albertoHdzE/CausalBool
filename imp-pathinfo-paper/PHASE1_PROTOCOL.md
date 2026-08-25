# Phase 1 — the within-dataset size test: pre-registered protocol

**Written 2026-08-04, before any run of this experiment completed.** Nothing in
this file may be edited after the first result lands in
`results/runs_sizebins.jsonl`; findings go in a separate results section at the
bottom, appended only.

---

## The question

The paper reports that the Path Usefulness Measure (PUM) falls as BDM
algorithmic complexity rises, across six dataset families. We reproduced that
exactly. We then found (`FINDINGS.md` §3) that BDM AOAC correlates with mean
molecule size at **r = +0.998**, and that plain atom-counting predicts PUM just
as well as BDM does (−0.821 vs −0.821). With six families and only cross-family
variation, "complexity predicts PUM" and "size predicts PUM" are not
distinguishable.

This experiment breaks the confound **by design**: it varies size *inside one
dataset*, holding chemistry, task, label distribution, splitting policy, model
and hyperparameters fixed.

## Hypotheses

* **H₁ (confound).** PUM decreases as mean bin size rises. The cross-family
  correlation is then explained by size, and the complexity reading is not
  needed.
* **H₀ (complexity survives).** PUM is flat across bins. Size alone is then not
  sufficient and something structural is doing work.

## Design

| element | choice | why |
| --- | --- | --- |
| dataset | ESOL (1128 molecules, 1–55 atoms) | wide size range, fast to train |
| model | T-Hop only | fastest, and the model whose published PUMs we reproduced exactly (Φ = 33/36) |
| bins | 4, by atom-count quartile, ties kept in one bin | equal-count bins, all ≥ 250 |
| modes | both (path / no path) | PUM needs the pair |
| noise | all six levels 0.0 … 0.5 | PUM is defined over the six variants |
| repetitions | 3 per cell | matches the campaign |
| total | 4 × 2 × 6 × 3 = **144 runs** | |

Bin edges fixed in advance from the atom-count distribution:

| bin | atoms | molecules |
| --- | --- | --- |
| 0 | ≤ 8 | 337 |
| 1 | 9–12 | 257 |
| 2 | 13–18 | 280 |
| 3 | ≥ 19 | 254 |

Mean atom counts span roughly 6.5 → 23.7, a factor of 3.6 — comparable to the
8.9 → 34.1 spread across the six published families.

## Controls held fixed across bins

1. **`max_nodes` is fixed at the full-ESOL value (55)**, not the bin's own
   maximum, so every bin trains a T-Hop with an identical parameter count. Only
   the molecules differ.
2. **The noise vector is the full-ESOL feature standard deviation**, not the
   bin's own, so the intervention at a given noise level is numerically the same
   perturbation in every bin.
3. **Hyperparameters are `hyperparams.get('t_hop', 'ESOL', mode)`**, the
   authors' whole-dataset Optuna settings, unchanged.
4. **Scaffold splitting is applied within each bin**, 80/10/10.
5. Seeds follow the campaign convention (`torch_seed = run`).

## Decision criterion — fixed in advance

Primary readout: **PUM per bin**, reported as `k/6`, against mean bin atoms.

* **H₁ is supported** if PUM spans **≥ 3/6** across the four bins *in the
  predicted direction* (higher PUM in the smaller bins), i.e. the smallest bin's
  PUM exceeds the largest bin's PUM by at least 0.5.
* **H₀ is supported** if the PUM range across bins is **≤ 1/6** (0.167).
* Anything between 2/6 and 3/6, or a non-monotone pattern, is reported as
  **inconclusive** and neither hypothesis is claimed.

Secondary readouts, reported but not decisive:

* Spearman correlation of mean bin atoms against PUM. **With four points this is
  a descriptive statistic, not a test** — it can only take five values and no
  p-value from it will be quoted as evidence.
* Mean bin BDM against PUM. Within a dataset, BDM and size may decouple slightly;
  if they do, the direction of disagreement is a bonus discriminator and will be
  reported as such.
* Raw test scores per bin, so that a bin whose task is simply harder is visible.

## Stated limitations, fixed in advance

1. **Hyperparameters were tuned on the whole dataset, not per bin.** A large-bin
   PUM could in principle be depressed by settings that suit the whole-dataset
   size distribution. This cannot be removed without a per-bin Optuna sweep,
   which is out of scope; it is a limitation of the result, stated in the
   write-up.
2. **Bins differ in more than size.** Small and large molecules differ in
   functional-group diversity, ring content and label variance. A bin-level
   difference is therefore not a pure size effect. Mean BDM per bin is reported
   alongside for this reason.
3. **Training-set size varies with the bin** (337 vs 254 molecules), and every
   bin is about a quarter of ESOL, so absolute scores will be worse than Table 3.
   That is expected and irrelevant: PUM is a *within-bin* comparison of path
   against no-path, so the shared handicap cancels.
4. **One dataset, one model.** A result here does not generalise to Graphormer or
   to the other five families without further runs.

## Standing rule inherited from `NEXT_PHASES.md` §2

No new structural measure enters the analysis until it has been run against the
250 same-degree pairs. This phase introduces no new measure; it uses BDM and
atom count only.

---

## Results

*(appended after the runs; nothing above this line is edited)*

### ESOL — 144 runs, 918 s, `results/runs_sizebins.jsonl`

| bin | atoms | n | mean atoms | mean BDM | PUM | RMSE no path | RMSE path |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1–8 | 337 | 6.24 | 49.0 | **3/6** | 1.856 | 1.786 |
| 1 | 9–12 | 257 | 10.36 | 119.7 | **1/6** | 1.017 | 1.157 |
| 2 | 13–18 | 280 | 15.44 | 259.2 | **0/6** | 0.922 | 1.101 |
| 3 | 19–55 | 254 | 23.24 | 474.9 | **0/6** | 1.639 | 2.163 |

PUM spread 3/6; smallest bin minus largest +3/6; Spearman against mean atoms
−0.949 and against mean BDM −0.949 (both descriptive, four points).

**Verdict by the pre-registered criterion: H₁ supported.** The criterion asked
for a spread of at least 3/6 in the predicted direction; the observed spread is
exactly 3/6. It is met **at the boundary**, so the binary PUM alone is a thin
result and is not the evidence we rest on.

### Robustness — the continuous effect is far cleaner than the binary PUM

PUM discards magnitude. The underlying quantity, the RMSE penalty for adding
path information (positive = path hurts), is monotone in bin size and much
better resolved:

| bin | mean atoms | path − no-path RMSE | rep-wise PUM | share of 3×3 rep pairings path wins |
| --- | --- | --- | --- | --- |
| 0 | 6.24 | **−0.070** (path *helps*) | 3.7/6 | 0.537 |
| 1 | 10.36 | +0.140 | 1.7/6 | 0.185 |
| 2 | 15.44 | +0.179 | 1.0/6 | 0.185 |
| 3 | 23.24 | **+0.524** | 0.3/6 | 0.111 |

Three independent aggregations — PUM on three-run means, PUM computed
rep-by-rep, and the fraction of all 54 rep-vs-rep pairings — give the same
monotone ordering.

**Permutation test.** Over the 24 (bin, noise) cells, the Spearman correlation
between bin index and the path-minus-no-path RMSE is **+0.721**; shuffling bin
labels 20 000 times gives **p = 0.0002** (two-sided). The trend is not run noise.

### What this does and does not establish

**Does.** Within a single dataset — one chemistry, one task, one label
distribution, one splitting policy, one set of hyperparameters — path
information goes from mildly helpful on the smallest molecules to clearly
harmful on the largest. The paper's cross-family correlation therefore does not
require any family-level explanation: the same gradient exists inside ESOL
alone. Note that whole-dataset ESOL gives T-Hop a PUM of 0/6 in our campaign;
restricting to molecules of eight atoms or fewer raises it to 3/6.

**Does not.** This design **cannot separate BDM from size**, and the anticipated
decoupling did not occur. Mean BDM per bin runs 49 → 120 → 259 → 475 while mean
atoms runs 6.2 → 10.4 → 15.4 → 23.2; the two are monotone together, so their
Spearman correlations with PUM are identical to three decimals. BDM is
superlinear in atom count here (7.9 → 20.4 bits per atom), but not
non-monotone, which is what a discriminator would need.

So Phase 1 rules out the *family-level* confounds and confirms the axis acts
within a family. Which of size or algorithmic complexity is the driver still
rests on the size-free evidence in `FINDINGS.md` §3 — where the one measure that
is not a function of the degree sequence collapses from −0.82 to −0.29/−0.50.
Taken together the two results point the same way, but neither on its own is a
clean separation of BDM from size.

### Caveat on the smallest bin

Bin 0's within-cell standard deviation across the three repetitions is 0.505
RMSE, against 0.11–0.21 for the other bins: molecules of eight atoms or fewer
train unstably, and its test set is about 34 molecules. Its 3/6 is also exactly
chance. The honest reading of bin 0 is "path information stops hurting", not
"path information reliably helps".

### Addendum, not pre-registered: Lipophilicity replication

Run after the ESOL verdict, so it is a replication and is labelled as such.
4200 molecules, bins at 7–22 / 23–27 / 28–32 / 33–115 atoms (means 18.0, 25.2,
30.0, 36.2). The within-dataset size range is a factor of 2.0 against ESOL's
3.7, so it is a weaker test by construction. Prediction stated before the runs
finished: the same direction, smaller spread.

**The prediction failed. 144 runs, 3368 s.**

| bin | atoms | n | mean atoms | mean BDM | PUM | RMSE penalty | as % of no-path RMSE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 7–22 | 1173 | 17.98 | 349.0 | 0/6 | +0.200 | +23.8% |
| 1 | 23–27 | 948 | 25.16 | 537.4 | 0/6 | +0.107 | +11.6% |
| 2 | 28–32 | 1066 | 29.96 | 675.8 | 0/6 | +0.263 | +31.2% |
| 3 | 33–115 | 1013 | 36.22 | 774.5 | 0/6 | +0.227 | +28.9% |

PUM is **0/6 in every bin**. `analyse_sizebins.py` mechanically prints "H₀
supported" because the spread is 0; **that verdict is not valid here** and is not
claimed. The binary measure has no dynamic range: path information never helps
anywhere in Lipophilicity, so a flat PUM is a floor effect, not evidence of
flatness. The criterion in this protocol was written for a dataset that spans the
crossover, and Lipophilicity does not.

The continuous effect, which does have range, shows **no monotone trend**:
Spearman +0.366 over the 24 cells, permutation p = 0.074. Bin 1 is the *lowest*
penalty, not the second lowest.

### What the two datasets say together

Relative RMSE penalty against mean bin size (`figures/phase1_sizebins_both.png`):

| mean atoms | 6.2 | 10.4 | 15.4 | 23.2 | 18.0 | 25.2 | 30.0 | 36.2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| penalty | **−3.8%** | +13.8% | +19.4% | +32.0% | +23.8% | +11.6% | +31.2% | +28.9% |
| dataset | ESOL | ESOL | ESOL | ESOL | Lipo | Lipo | Lipo | Lipo |

Lipophilicity's *smallest* bin already averages 18 atoms — larger than ESOL's
second-largest bin. Its whole range lies **above** the crossover ESOL locates
near eight atoms. So the relationship is **not a smooth monotone function of
size across the full range**: it looks like a crossover at small sizes, below
which path information helps, followed by a plateau at a 10–30% penalty that
does not keep growing.

That is consistent with the ESOL result but is **not independent confirmation of
it**. Lipophilicity neither replicates the gradient nor contradicts it; it
samples only the saturated part of the curve. Reported here because a null in a
range with no dynamic range is still worth recording, and because the plateau
itself was not predicted.
