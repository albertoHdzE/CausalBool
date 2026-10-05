# REPORT — `abstraction-validation-v1-r1` (Tracks V, D, X; G deferred)

Run status **COMPLETE for V/D/X**. Track G is **DEFERRED_DEPENDENCY** (U2, U3) with no G work executed.
The four-track study is therefore not complete. Every statement below is scoped to the
declared family A, the declared Q (42 or 52 interventions) and the named β scheme. It concerns
four finite models with n ≤ 10.

## 1. Checker validation (stage 1, after freeze, before D)

| item | hand prediction | measured |
|---|---|---|
| Track V supplied pairs / failing pairs | 30,976 / 2,080 | 30,976 / 2,080 |
| P1, P2, P3, P4 failing | 0 each | 0 each; (iv-a) holds for every q |
| N1 failing; (iv-a) failures | 2,048 (128 per reset); 16 resets | 2,048 (128 per reset); 16 |
| N2 failing; (iv-a) failure | 16; tick | 16; tick |
| N3 failing; autonomous failure | 16; q_id | 16; q_id |
| P4 partition equals F1 par (4,0); P1 β pairs share labels | yes; yes | yes; yes |
| C1/C2: G_q exists for constant and identity, 4 models × 5 τ | 40 of 40 cells | 40 of 40 |
| H-M1-τ: E2 passes, M1, 135 candidates × τ ∈ {4,8,16} | 405 of 405 | 405 of 405 |
| H-M2-F3: E2 passes iff 2^a divides τ | 75 of 150; per (w,o) 9,11,7,10,8,6,9,8,7 | 75 of 150, same per (w,o); all 150 pairs individually agree |
| theorem: injective/constant maps, every G_q exists | 9,790 of 9,790 | 9,790 of 9,790 |
| X: support closure vs E2, F3 pairs | 630 agree of 630 | 630 of 630 |

No prediction deviated, so the run was not stopped as CHECKER-INVALID. Source: `results_v.json`, `results_x.json`.

## 2. Track D: fine existence (β_fine, primary)

Coverage: 2,730 of 2,730 rows and 59,312,640 of 59,312,640 declared (α, τ, q, x) pairs were
evaluated, with no early exit. Every β_fine class is a singleton in all 2,730 rows. In-run
witness re-verification checked a separate 94,363 stored witnesses (fibre and macro). That
is extra work and is not part of the declared pair count. No record is missing, and no row
has a lower-bound Q′.

Display labels across all 2,730 rows: CONTROL 220 (the 11 injective/constant candidates × 5 τ × 4 models;
each is complete and FULL), AUT-FAIL 1,936, RESTRICTED 458, AUT-ONLY 18 (M1 only, τ ∈ {4,8,16}),
FULL 98. The per-(model, τ) table, every FULL row and the E8 restriction spread are in
`report_tables.md`. Every row is in `results_d.jsonl`.

**FULL lossy rows (98 of the 2,510 non-control rows):**
- **M1 (rule 150): 0.** P1's parity map at τ = 2 is RESTRICTED, because single-bit resets fail, as N1 predicts.
- **M2 (counter): 45, all F3.** They are the four distinct low-bit blocks [0,ℓ), ℓ = 1…4, at every τ. Each
  (model, τ) cell has 9 raw rows and 4 distinct partitions. Mechanism: low bits never receive a carry from
  higher bits, and every out-of-block operation leaves them unchanged.
- **M3 (rule 30): 8, all non-F3** (τ ∈ {2,4,8,16}): `F2 and` and `F4 and∘and (4,0) o2=0`. These are one
  partition, so each cell has 2 raw rows but 1 distinct partition. **Mechanism (rendered in `nonf3_full_maps.json`).** The macro
  variable is the indicator of the all-ones state, with fibres 255 and 1. All 42 induced maps G_q are
  the same constant map, so no F_q reaches the all-ones state at these τ. FULL holds because the induced
  dynamics are trivial. It is not evidence of an informative macro dynamics.
- **M4 (EGFR file): 45 total, 40 F3 and 5 non-F3.** The 40 F3 rows are 8 raw F3 candidates per τ.
  They cover three distinct upstream blocks, [0,1), [0,2) and [0,3); [0,4) fails because v003 reads v007. Counting
  the non-F3 rows, each cell has 3–5 distinct FULL partitions (`report_tables.md`). The non-F3 rows are:
  - `F2 and` at τ ∈ {4,8,16} (rows 2267–2269). This is the all-ones indicator again, with every G_q equal to the same constant map.
  - `F4 or∘or (4,1) o2=1` at τ ∈ {8,16} (rows 2648, 2649). This map is z = (v000, OR(v001…v008), v009), with 8 macro
    states. The induced autonomous map is G(z) = (z₀, z₀, z₀). Across the 52 interventions there are 9 distinct G_q.
    In the file encoding, every node descends from the self-looped v000. After ≥ 8 steps the macro image
    depends only on v000, which the map keeps as its own coordinate. This is the only non-constant non-F3 FULL
    result. It is a statement about this file's node order and wiring, not about biology.

Descriptive count required by the design: FULL lossy rows in M3/M4 are **40 F3 and 13 non-F3**. Of the 13
non-F3 rows, 11 have constant induced maps and 2 are the `F4 or∘or` rows above. No stop rule follows.

## 3. Coarse hypotheses (separate column, never merged with §2)

| model | scheme | DISAGREE | STRUCT-FAIL | INCOMPLETE | NO-HOLDOUT | HOLDS |
|---|---|---|---|---|---|---|
| M1 | H-COARSE | 0 | 470 | 0 | 0 | 0 |
| M1 | H-OUT | 0 | 150 | 0 | 0 | 0 |
| M2 | H-COARSE | 0 | 470 | 0 | 0 | 0 |
| M2 | H-OUT | 0 | 105 | 0 | 0 | 45 |
| M3 | H-COARSE | 0 | 462 | 0 | 0 | 8 |
| M3 | H-OUT | 0 | 150 | 0 | 0 | 0 |
| M4 | H-COARSE | 49 | 418 | 0 | 0 | 3 |
| M4 | H-OUT | 4 | 136 | 0 | 0 | 40 |

These are counts of rows. H-COARSE covers 94 lossy candidates × 5 τ per model, and H-OUT covers the F3 rows. H-OUT holds exactly on the
FULL F3 rows of M2 and M4 (45 and 40), where out-of-block interventions are invisible at the macro level.
H-COARSE holds only on the 11 rows whose induced maps are constant (8 in M3, 3 in M4). In every other row the
position-free grouping is falsified, mostly by a representative or member without an induced map.
Four M4 H-OUT rows (2288, 2289, 2388, 2389) show an evaluable disagreement. A failure falsifies the
declared grouping only; it does not falsify per-q existence. Comparison units: macro-state disagreements and micro-state pair mismatches
(fibre-weighted) are both stored per member and per row.

## 4. Independent audit

`audit_oracle.py` was hashed at freeze before production. It does not import the production checker, `study.py` or `run.py`.
It builds M1–M3 and every intervention from their definitions. For M4 it uses the owners `bnet.parse_bnet` and
`causalbool.repertoire` (disclosed). It also reads `fixtures.json`. It passed **18 of 18 checks**:
- the audit list equals the frozen list;
- candidate counts;
- the seven V controls and their totals;
- both calibrations, including all 150 H-M2-F3 pairs;
- exact whole-run row coverage of 0…2,729, each row once;
- checked = declared = 59,312,640 pairs;
- cross-field arithmetic on all 2,730 rows: row id, E2 = E3(q_id), Q′, status re-derived, witness presence and coarse pair counts;
- all scientific fields of the **273 selected rows** (r_j = 10j + j mod 5; 55,55,55,54,54 rows over τ),
  compared as canonical JSON with runtime excluded.

A planted single-field change in three selected rows was detected (`logs/audit_nonvacuity.log`). The selected
rows are deterministic coverage, not a random sample. They give no statistical certificate for the 2,457
unaudited rows. Those rows rest on the in-run witness verification, the cross-field arithmetic and the stage-1 checks. One audit
field, `beta_fine_all_singletons`, is compared against a constant True. The oracle relies on j ↦ (k, p) being injective and does not recompute the field.

## 5. What this does and does not establish

- Within A, the declared Q and β_fine, rule 30 admits **no** FULL lossy map with non-constant induced dynamics.
  EGFR (file encoding) admits one such non-F3 map, `F4 or∘or (4,1) o2=1` at τ ∈ {8,16}. Its dynamics are
  carried by a retained input coordinate. Neither statement extends to other Q, β, families or models.
- AUT-ONLY and RESTRICTED results are reported separately (E8). Q′ is a post-hoc restriction and never a declared-Q claim.
- Not tested: occurrence-gap ranking (G), description length, fractal or scale-invariant structure,
  grammar, held-out prediction under β_fine, biological causation. No novelty claim, no compression claim and no claim of a
  completed general causal-deconvolution method.
