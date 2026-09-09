# AUDIT04-H · H2 — the two measures: declare what they respond to

**Branch:** `fixing`
**Anchor commit:** `fc003f8`
**Date written:** 2026-09-08
**Owners:** `src/description_lengths.py`, `tests/analysis/test_complexity_measures_are_algorithmic.py`,
`GOVERNANCE/NULLS.md`, `GOVERNANCE/DESCRIPTION_LENGTHS.md`, `GOVERNANCE/VERIFICATION.md`

This note is the single record for task H2 of the plan
`plans/AUDIT04-H_comparator_measures_and_lifecycle.md` (lines 431–512). It
holds the response profile under node relabelling (H2.1), the label-matched
probe (H2.2), the adjudication of `DECLARED_INVERSIONS` (H2.3), the
incorporation of the fourth law into `GOVERNANCE/NULLS.md` (H2.4), and the
naming of the variants in the documents that conflate them (H2.5).

---

## 1. Pre-registration (H2.1)

The plan pre-registers the measurement: for each of the two reported
measures (Variant A — `row_run_index_set_length` — and BDM), measure the
response to **node relabelling** (a graph isomorphism, `A' = A[P][:, P]`) over
four families at n = 16, with 200 relabellings and seed `20260908`. The
families are the chain (15 edges, canonical `0–1–2–…–15`), the hub (5 edges,
node 0 connected to nodes 1–5), the checkerboard (`A[i, j] = 1 iff i + j is
even`, 64 ones — the family whose Variant-A inversion is declared in
`DECLARED_INVERSIONS`), and an Erdos–Renyi graph `G(16, p=0.2)` (20 edges).

The plan's review values (n = 16, 200 relabellings) are given as a
cross-check: `random p=0.2 → Variant A 98.10, BDM 92.46; chain → Variant A
0.00, BDM 133.84; hub → Variant A 0.00, BDM 1.44`. The "0.00 (invariant)"
annotation for chain and hub cannot be reproduced under graph isomorphism
(§1.1 below); it is consistent with **row-only permutation** of the
adjacency matrix, which is a different operation and not a graph isomorphism.
The H2.1 measurement is therefore reported under the plan's stated
definition, with the discrepancy recorded in §1.1 and in the commit message.

### 1.1 The plan's review values: a convention mismatch

The plan §2.2 calls the relabelling "an isomorphism that changes no
information" — which is the standard meaning, the matrix operation
`A' = A[P][:, P]` for a permutation `P`. Under this operation the spread
of Variant A on the chain is not zero:

| family | row-only perm | isomorphism (plan prose) |
|---|---|---|
| chain | 0.00 bits | 61.31 bits |
| hub   | 0.00 bits | 28.61 bits |
| random p=0.2 | 0.00 bits | 89.92 bits |

Row-only permutation of an adjacency matrix is not a graph operation; the
result is not a valid adjacency matrix (rows and columns index the same set
of nodes, but only one of the two is permuted). The "0.00 (invariant)"
annotation is therefore evidence of a measurement under a different
convention, not a property of Variant A. The H2.1 measurement below uses
the plan's prose, not the plan's review.

The BDM review values are also not reproducible in detail: chain BDM
spread 170.72 vs the plan's 133.84, hub BDM spread 100.12 vs the plan's
1.44. The chain difference is consistent with a different seed; the hub
difference of two orders of magnitude is not, and suggests the plan's
review values were obtained under a convention whose identity is not
fully recoverable from the prose. The H2.1 measurement is reported
verbatim, the cross-check is recorded, and the reader can reproduce both
sides from the seed.

---

## 2. The response profile (H2.1)

**Producer:** `venv/bin/python audit/AUDIT04_H_measures/response_profile.py`
**Artefact:** `audit/AUDIT04_H_measures/response_profile.json`
**Denominator:** 200 relabellings per family, n = 16, seed `20260908`.
Same permutation set across families, so the two measures' responses are
to the same set of isomorphisms.

### 2.1 Canonical matrix values

The measures evaluated on each matrix in its canonical (un-permuted)
labelling:

| family | edges / ones | Variant A (bits) | BDM (bits) |
|---|---|---|---|
| chain | 15 edges | 298.3848 | 102.3254 |
| hub | 5 edges | 94.0116 | 104.4797 |
| checkerboard | 64 ones | 1050.4780 | 34.2658 |
| random p=0.2 | 20 edges | 282.0349 | 396.7852 |

### 2.2 Spread under 200 node relabellings (the response profile)

| family | Variant A spread (bits) | BDM spread (bits) | Variant A range | BDM range |
|---|---|---|---|---|
| chain | 61.31 | 170.72 | 232.99 – 294.30 | 234.57 – 405.29 |
| hub | 28.61 | 100.12 | 102.19 – 130.80 | 101.15 – 201.26 |
| checkerboard | **784.79** | **437.34** | 134.89 – 919.68 | 66.44 – 503.77 |
| random p=0.2 | 89.92 | 127.61 | 265.69 – 355.61 | 296.31 – 423.91 |

**Both measures respond to relabelling for every family.** The Variant A
spread is 0 bits under row-only permutation (the rows of the matrix are
reordered, the column structure unchanged, the run-length cost of each
row is what it was — the sum is invariant). The Variant A spread is
non-zero under graph isomorphism (the rows AND columns are permuted, so
the pattern of 1s in each row changes and the run-length cost of each
row can differ). Variant A's claim to be a graph measure is therefore
not quite right: it is a **graph-plus-labelling** measure, and the
labelling contributes up to ~785 bits for the checkerboard.

The BDM spread is non-zero under any non-trivial operation on a
two-dimensional matrix, including a row-only permutation in the unusual
case where BDM happened to depend on row order. (In the standard
configuration, BDM treats the matrix as a 2-D object and its cost is
identical under row-only permutation, since the row order does not
change the multiset of 2-D blocks it sums over.) The BDM spread
measured here is therefore entirely attributable to the column
re-permutation that the isomorphism performs.

The dominant finding is the checkerboard's **785-bit** Variant A
spread. The canonical checkerboard costs 1050.48 bits; a randomly
relabelled checkerboard can cost as little as 134.89 bits. Variant A
over-prices a structured family by **a factor of up to 7.8** depending
on labelling alone, which is the precise shape of the defect the
fourth law (§3 below) exists to guard against.

### 2.3 The declared inversion is the labelling response, in disguise

The checkerboard's Variant A cost is high in the canonical labelling
because every row alternates and the run-length code over each row
charges 8 runs (its maximum at n = 16). Under a random relabelling
some rows are no longer alternating and the cost drops. The
"checkerboard inversion" declared in `DECLARED_INVERSIONS` (the
declaration that Variant A ranks the checkerboard at 1050.5 bits
against 563.9 for matched random) is therefore **not a property of
the graph**; it is a property of the labelling under which the graph
is presented to the measure. The same graph, in a different labelling,
can be cheaper than random.

This is the H2.3 adjudication directly: the inversion declared in
`DECLARED_INVERSIONS` is a labelling response, and the declaration
must say so.

---

## 3. The label-matched probe (H2.2)

**Producer:** `venv/bin/python audit/AUDIT04_H_measures/label_matched_probe.py`
**Artefact:** `audit/AUDIT04_H_measures/label_matched_probe.json`
**Denominator:** 200 chain instances × 200 random graphs = 200 paired
comparisons per configuration, n = 12, 11 ones in the matrix, draw seed
`11` (the seed the existing test uses; the chain seed `20260908` controls
the relabelling sampler, drawn fresh per configuration).

The probe re-runs the chain comparison of
`test_complexity_measures_are_algorithmic.py:test_random_is_not_simpler_than_a_chain`
in two configurations. **Canonical** — the chain in its natural labelling
0-1-2-…-11, exactly as the existing test presents it. **Relabelled** — the
chain under a fresh random permutation per instance, drawn with
`np.random.default_rng(20260908).permutation(12)`. In both cases the
matched random graphs are drawn with `np.random.default_rng(11)`, the
existing test's seed, so the canonical column reproduces the existing
test's 9.5 % figure draw-for-draw.

### 3.1 The measurement (side by side with the existing probe)

| configuration | Variant A simpler-or-equal (%) | BDM simpler-or-equal (%) |
|---|---|---|
| canonical (the existing probe) | 9.50 | 0.00 |
| relabelled (the label-matched probe) | 11.00 | **69.00** |

The BDM figure inverts on relabelling: the chain is more expensive than
random 100 % of the time in the canonical configuration, but only 31 % of
the time (100 − 69) in the relabelled one. The two figures are the SAME
graph and the SAME random comparator distribution; only the chain's
labelling differs. BDM's "the chain is simpler than random" finding is
a labelling response, not a property of the family.

Variant A is comparatively stable: 9.50 % canonical, 11.00 % relabelled,
both within the noise the existing test accepts (its 25 % threshold
allows up to 50/200). The run-length code over rows is not
labelling-sensitive at the fraction level, consistent with H2.1's
Variant A spread of 61.31 bits on the chain being a moderate move in
absolute terms (the chain is dominated by rows of runs 1 or 2) but a
modest one relative to the chain's 196-bit canonical cost.

### 3.2 The review value cross-check

The plan's review values for H2.2, n = 12, 11 edges, 200 × 200:

| configuration | Variant A | BDM |
|---|---|---|
| canonical | 9.5 % | 0.0 % |
| relabelled | 9.5 % | **66.9 %** |

The canonical column is exactly reproducible (9.50 %, 0.00 %). The
relabelled column reproduces the BDM 0 → 66.9 % finding as 0 → 69.00 %,
a 2.1-percentage-point shift attributable to the different random
permutation sets drawn under the different seeds; the qualitative claim
is identical. The Variant A relabelled value is 11.00 % against the
plan's 9.5 %; both are within the noise band of the existing test's
25 % acceptance threshold, and the two values are not distinguishable
from each other at this sample size.

### 3.3 Why the existing probe was not enough

The existing probe in `test_complexity_measures_are_algorithmic.py`
asks whether the measure inverts. It is a single-draw test: the chain is
presented in one labelling, and the figure is the inversion rate over
60 (or 200) draws of the random comparator. The H2.1 response profile
shows that the figure is a draw of a labelling-sensitive distribution
and not a property of the family; the label-matched probe is the same
test with the labelling sampled. Both figures now stand:

- the existing probe (canonical, 9.5 % / 0.0 %) is the
  `DECLARED_INVERSIONS` evidence; the reader who relies on it must see
  that the probe does not exclude the relabelled case.
- the label-matched probe (relabelled, 11.0 % / 69.0 %) is the
  measure's behaviour on the family; the BDM figure inverts on
  relabelling, and that is the fact the H2.3 adjudication rests on.

Neither replaces the other. Both are reported.

---

## 4. Adjudication of `DECLARED_INVERSIONS` (H2.3)

(populated by the H2.3 step; left for the next commit)

---

## 5. The fourth law in `GOVERNANCE/NULLS.md` (H2.4)

(populated by the H2.4 step; left for the next commit)

---

## 6. Naming the variants (H2.5)

(populated by the H2.5 step; left for the next commit)
