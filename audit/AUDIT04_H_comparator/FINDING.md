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

---

## 5. Knob table — best-null gap moves with the knob, the others do not (H1.1)

**Run command (each line a separate invocation, each writing its own
artefact):**

```bash
venv/bin/python src/experiments/Null_Generator_HPC.py \
    --max-networks 30 --nulls-per-type 10   --subsample h1_30_n10
venv/bin/python src/experiments/Null_Generator_HPC.py \
    --max-networks 30 --nulls-per-type 100  --subsample h1_30_n100
venv/bin/python src/experiments/Null_Generator_HPC.py \
    --max-networks 30 --nulls-per-type 1000 --subsample h1_30_n1000
```

The 30-network subsample is the first 30 networks of
`data/bio/processed/`, sorted alphabetically by stem, with `gate_histogram.json`
and `truth_tables.json` excluded. The seed is the existing default (42). The
artefact `null_stats_h1_30_n1000.json` is byte-identical to the first 30
records of the main 231-network `null_stats.json`, verified in H1.2.

**Index-set length, 30 networks, seed 42:**

| kind | null count | median gap to best null | median gap to median null | median `exceed` | `exceed == 0` count |
|------|------------|-------------------------|---------------------------|-----------------|----------------------|
| er   | 10         | **+21.05**              | 50.28                     | 0.000           | 19 / 30              |
| er   | 100        | **−7.62**               | 44.61                     | 0.015           | 12 / 30              |
| er   | 1000       | **−25.81**              | 41.73                     | 0.012           | 8 / 30               |
| deg  | 10         | **−4.91**               | 3.39                      | 0.450           | 10 / 30              |
| deg  | 100        | **−17.65**              | 1.73                      | 0.435           | 5 / 30               |
| deg  | 1000       | **−22.07**              | 3.32                      | 0.402           | 4 / 30               |
| gate | 10         | **−14.30**              | 2.93                      | 0.500           | 10 / 30              |
| gate | 100        | **−26.25**              | 9.69                      | 0.380           | 7 / 30               |
| gate | 1000       | **−37.30**              | 9.69                      | 0.362           | 6 / 30               |

**The prediction in §1 is confirmed.** Across all three null kinds, the
median gap to the best null becomes monotonically more negative as the
null count rises (er: +21.05 → −7.62 → −25.81; deg: −4.91 → −17.65 → −22.07;
gate: −14.30 → −26.25 → −37.30). The median gap to the median null
(er: 50.28 → 44.61 → 41.73; deg: 3.39 → 1.73 → 3.32; gate: 2.93 → 9.69 → 9.69)
and the median `exceed` (er: 0.000 → 0.015 → 0.012; deg: 0.450 → 0.435 → 0.402;
gate: 0.500 → 0.380 → 0.362) do not.

**What the knob charges.** A null count of 1000 nulls of each kind is 100x
more than the 10-null run; the median gap to the best null moves by ~50
bits on the er cell (from +21 to −26) while the median gap to the median
null moves by ~9 bits in the opposite direction (from 50.28 to 41.73). The
best-null comparator is therefore reading a quantity that depends on the
ensemble size, not on the network. The `exceed` distribution and the
median-null gap are not, on this subsample, charging the run parameters
they are not about.

The `exceed == 0` count also drops monotonically with the null count
(er: 19 → 12 → 8; deg: 10 → 5 → 4; gate: 10 → 7 → 6) — the worst-case
indicator becomes rarer as more nulls are drawn, which is the expected
behaviour of an order statistic over a fixed ground truth and is
**not** an artefact of the comparator choice.

---

## 6. Full six-cell table under three comparators (H1.2)

**Artefact:** `results/bio/null_summary.json` (regenerated 2026-09-08 at
`nulls_per_type = 1000` over 231 networks). The enrichment adds
`median_gap_to_median_null` and `n_bio_lt_median_null` to each cell
without modifying the six `median_gap_bits` figures already in §5b of
`VERIFICATION.md` — the diff is empty on those six values, verified.

**Index-set length (231 networks, 1000 nulls per kind):**

| cell | median `gap_bits` (best) | median `gap_to_median_null` | median `exceed` | `exceed == 0` | `n_bio < median_null` |
|------|--------------------------|------------------------------|-----------------|---------------|------------------------|
| er   | −27.68 bits              | 25.22 bits                   | 0.130           | 53 / 231      | 171 / 231              |
| deg  | −31.26 bits              | 10.72 bits                   | 0.257           | 34 / 231      | 149 / 231              |
| gate | −38.05 bits              | 9.29 bits                    | 0.296           | 39 / 231      | 147 / 231              |

**BDM (231 networks, 1000 nulls per kind):**

| cell | median `gap_bits` (best) | median `gap_to_median_null` | median `exceed` | `exceed == 0` | `n_bio < median_null` |
|------|--------------------------|------------------------------|-----------------|---------------|------------------------|
| er   | −59.20 bits              | 3.35 bits                    | 0.340           | 14 / 231      | 150 / 231              |
| deg  | −53.12 bits              | 1.09 bits                    | 0.395           | 7 / 231       | 130 / 231              |
| gate | −68.45 bits              | 1.39 bits                    | 0.423           | 10 / 231      | 131 / 231              |

**Sign-relationship statement.** A negative `gap_bits` (bio shorter than
the best null) and an `exceed` of zero (no null is shorter than bio) are
the same event. The counts agree exactly: index-set has 53 / 34 / 39
networks at `exceed == 0` against 53 / 34 / 39 with negative `gap_bits`
(separating by the best null), and BDM has 14 / 7 / 10 against
14 / 7 / 10. The two comparators are not independent statements of
separation, they are two readings of the same per-network minimum
relative to a 1000-draw ensemble.

**What the table does not say.** It does not say the median-null gap
is "the right" comparator. The median-null gap is positive in all six
cells (bio is shorter than the median null in the median network),
which is a statement about the central tendency of the corpus, not
about the falsification of a single network. Which comparator the
`Contingency_Monitor` should use on the `gap_bits` arm is **H-D1**;
this note does not draw the conclusion.

---

## 7. Verdict-change count — the consequence of moving the gap arm (H1.5)

The `Contingency_Monitor.evaluate_checkpoint` rule (line 138 of
`src/pipeline/Contingency_Monitor.py`) is:

```python
def _falsified(g, e):
    return e >= 0.05 or g <= 0.0
```

with `g = gap_bits` (the gap to the **best** null). A network is
falsified — and the action `SWITCH_TO_HYBRID_ENCODING` is taken — if
`gap_bits <= 0.0` (bio not shorter than the best null) or
`exceed >= 0.05` (5 % or more of nulls as short as bio).

If the gap arm is moved to the median-null comparator, a network is
separating on the gap arm when `D(median_null) > D_bio`, i.e.
`gap_to_median_null > 0.0`. The two comparators disagree on a network
when exactly one of the two inequalities holds.

**Verdict change, 231 networks, 1000 nulls per kind:**

| measure  | er     | deg    | gate   | total (3 null kinds) |
|----------|--------|--------|--------|------------------------|
| index-set | **118 / 231** | **115 / 231** | **108 / 231** | **341 / 693** (49.2 %) |
| BDM       | **136 / 231** | **123 / 231** | **121 / 231** | **380 / 693** (54.8 %) |

**Interpretation, stated rather than implied.** Moving the gap arm
from the best-null comparator to the median-null comparator changes
the falsification verdict on roughly half the corpus, under both
measures and all three null kinds. The decision rule therefore
**does** depend on the comparator choice, and the choice is a
substantive scientific decision rather than a technical one. The
verdict-change count is a measured quantity, not an estimate: it
comes from the same 231 networks and the same 1000 nulls already
on disk in `null_stats.json`.

**No behaviour is changed.** `Contingency_Monitor._falsified` still
takes the best-null gap. The count above is the measured consequence
of the change; the change itself is author decision **H-D1** and
remains pending.
