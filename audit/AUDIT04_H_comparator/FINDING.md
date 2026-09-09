# AUDIT04-H · H1 — the comparator, the two measures, and the reference distribution

**Branch:** `fixing`
**Anchor commit:** `fc003f8`
**Date written:** 2026-09-08
**Owner:** `src/experiments/Null_Generator_HPC.py`
**Status:** open — H1.1 prediction registered, H1.2/H1.3/H1.4/H1.5 pending

This note is the single record for task H1 of the plan
`plans/AUDIT04-H_comparator_measures_and_lifecycle.md` (lines 342–427). It is
the only place where the pre-registered prediction, the knob table, the full
six-cell comparator table, the binomial reference, and the open H-D1 question
are kept together. Per the standing law *measure, do not assert*, every number
in this note names the command that produced it and the denominator it ran
over.

---

## 1. Pre-registered prediction (H1.1)

The artefact `results/bio/null_stats.json` carries `gap_bits`, `exceed`,
`best_null`, and `median_null` per record, but the published summary block at
`Null_Generator_HPC.py` lines 363–411 reports only the best-null comparator.
The headline gap therefore is the gap to the null ensemble's **minimum**, which
is a quantity that can only become more negative as the null ensemble grows.

**Prediction, registered before any run for this task:**

> the median gap against the **best** null becomes monotonically more negative
> as the null count rises, while the median permutation tail `exceed` and the
> median gap against the **median** null do not.

The "monotonically more negative" direction is what would be expected if the
best-null comparator charges the run parameters it is not about. The
median-null comparator and the permutation tail are distribution-free or
order-statistic, so they are predicted to be approximately flat across null
counts. If the measurement goes the other way, the reasoning that justifies
publishing the best-null comparator is weakened and the task halts for the
author.

### Subsample rule and seed

- **Subsample:** the first 30 networks from `data/bio/processed/`, sorted
  alphabetically, ignoring `gate_histogram.json` and `truth_tables.json`.
  This is a deterministic, documented rule — no seed is required for the
  selection.
- **Null generation seed:** 42 (the existing default in
  `Null_Generator_HPC.process_networks`).
- **Null counts:** `{10, 100, 1000}`. The full 231-network re-run is not
  required and is not done; the point is the direction and magnitude of the
  knob effect.
- **Other parameters:** `allow_self_loops=False`, `time_limit_sec=None`,
  `nswap_factor=10` (the existing defaults).

### What the run will produce

For each of the three null counts, over the same 30 networks, the run will
publish, per measure × null type (er / deg / gate):

- median `gap_bits` against the best null (the existing comparator)
- median `gap_bits` against the median null (the comparator that does not
  move with the knob, per the prediction)
- the count of networks where the bio object is shorter than its **median**
  null (the median-null analogue of `separating_at_exceed_0`)
- the median `exceed` (the permutation tail)
- the count of networks at `exceed == 0` (the worst-case indicator)

These five quantities × two measures × three null types × three null counts
yield a 90-cell table, which is the empirical content of H1.

### What the run will not change

The six best-null figures already in `null_summary.json` and quoted in
`VERIFICATION.md` §5b are produced from the existing 231-network re-run at
`nulls_per_type=1000`. They are not recomputed and not modified by this
task; the H1.2 acceptance criterion requires that the diff before and after
the enrichment is empty on those six figures.

---

## 2. Reference distribution for `exceed == 0` (H1.3)

Under the exchangeability of a network with its own nulls, the probability
that no null is shorter than the network is `1/(n+1)`, where `n` is the null
count. At `n=1000`, that is `1/1001 ≈ 0.000999`.

Over 231 networks, the expected count of networks at `exceed == 0` is
`231 × 1/1001 ≈ 0.231`. The exact binomial upper-tail probability is
`P(X ≥ k) = Σ_{j≥k} C(231, j) (1/1001)^j (1000/1001)^(231-j)`.

Values computed during review, for cross-check (the run must reproduce
these or explain the difference):

| cell | k  | expected | exact upper-tail p |
|------|----|----------|--------------------|
| index-set / er   | 53 | 0.23 | 5.4 × 10⁻¹⁰⁷ |
| index-set / deg  | 34 | 0.23 | 4.8 × 10⁻⁶²  |
| index-set / gate | 39 | 0.23 | 2.0 × 10⁻⁷³  |
| BDM / er         | 14 | 0.23 | 7.6 × 10⁻²¹  |
| BDM / deg        |  7 | 0.23 | 5.2 × 10⁻⁹   |
| BDM / gate       | 10 | 0.23 | 7.9 × 10⁻¹⁴  |

These probabilities are one-sided upper-tail; the hypothesis they would
allow one to reject, if it were named, is the exchangeability of a network
with its own nulls. The interpretation is **not** drawn here; it is author
decision **H-D1** whether to call biological objects simpler than their null
ensembles, with the binomial probability as evidence and the comparator as
the question to be answered.

---

## 3. Open question for the author (H1.5, H-D1)

`src/pipeline/Contingency_Monitor.py` `evaluate_checkpoint()` falsifies on
`exceed >= 0.05 or gap_bits <= 0.0`, where `gap_bits` is currently the
gap against the best null. Whether the `gap_bits` arm should move to the
gap against the median null is the comparator question. Until the author
decides, **no behaviour is changed**; the rule remains the best-null rule
and the measured consequence of moving it (how many of the 231 networks
change verdict under each rule) is recorded in this note.

---

## 4. Sections to be filled by the run

- §5: the knob table (H1.1)
- §6: the full six-cell table under three comparators (H1.2)
- §7: the verdict-change count (H1.5)

These sections are committed **after** the run that produces them. The
prediction in §1 is the only thing committed before.
