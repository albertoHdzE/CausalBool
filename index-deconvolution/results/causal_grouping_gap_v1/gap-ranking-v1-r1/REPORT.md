# Causal state grouping — gap-ranking-v1-r1 (Track G)

Status: **ready for Codex review; not yet accepted.** Exploratory scheduling evidence on an
already inspected population with known labels. It is not fresh causal confirmation, not a
compression claim and not a test of nesting.

## 1. Question

Does the recurrence-gap ordering declared in corrected `DESIGN.md` §4 place the already
validated FULL causal state groupings earlier than (a) canonical candidate order and (b) the
exact expected first rank under a uniformly random ordering of the same candidates?

## 2. What was computed

- 24 autonomous trajectories (4 models × 6 declared starting states), 65 states each, from the
  adopted model owners; reused at τ ∈ {1, 2, 4, 8, 16} (65, 33, 17, 9, 5 sampled frames).
- 8,368 occurrence sets (trajectory, block, value) over the 9 partitions; occurrence frames from
  the isolated owner `seqdecon.operators.token_occurrence_frames`, gaps from the existing
  `gaps`. Trajectories are never concatenated; the score pools integer counts.
- 180 partition scores R = regular / eligible (exact integers); none is UNAVAILABLE.
- 20 ranked lists, 2,510 positions (N = 124 for M1–M3, 130 for M4; duplicates kept; F2 last).
- Scores and ranks were sealed (`production/seal.json`) in a process that could not read the
  outcome tree, and only then joined to the original `results_d.jsonl` FULL labels.

## 3. Result (all 20 cells; `production/joined_table.md`, `production/joined.json`)

| comparator | EARLIER | TIE | LATER | no FULL reference |
|---|---|---|---|---|
| exact random expectation (N+1)/(m+1) | 5 | 0 | 9 | 6 |
| canonical candidate order | 12 | 0 | 2 | 6 |

The six cells without a FULL candidate in the ranked population are M1 at every τ and M3 at
τ = 1; they carry no rank and no imputed win or loss.

Per cell, against the random expectation for that same cell:

| cell | m | r_G | (N+1)/(m+1) | r_C | first gap hit | dynamics evidence |
|---|---|---|---|---|---|---|
| M2 τ=1 | 9 | 9 | 12.5 | 41 | F3 val [0,4) | not characterised |
| M2 τ=2 | 9 | 17 | 12.5 | 41 | F3 val [0,1) | not characterised |
| M2 τ=4 | 9 | 25 | 12.5 | 41 | F3 val [0,1) | not characterised |
| M2 τ=8 | 9 | 33 | 12.5 | 41 | F3 val [0,1) | not characterised |
| M2 τ=16 | 9 | 37 | 12.5 | 41 | F3 val [0,2) | not characterised |
| M3 τ=2 | 2 | 119 | 41.67 | 40 | F4 and∘and (4,0) o₂=0 | constant dynamics |
| M3 τ=4 | 2 | 53 | 41.67 | 40 | F4 and∘and (4,0) o₂=0 | constant dynamics |
| M3 τ=8 | 2 | 38 | 41.67 | 40 | F4 and∘and (4,0) o₂=0 | constant dynamics |
| M3 τ=16 | 2 | 18 | 41.67 | 40 | F4 and∘and (4,0) o₂=0 | constant dynamics |
| M4 τ=1 | 8 | 5 | 14.56 | 41 | F3 val [0,2) of (4,2) | not characterised |
| M4 τ=2 | 8 | 13 | 14.56 | 41 | F3 val [0,3) of (3,0) | not characterised |
| M4 τ=4 | 9 | 25 | 13.1 | 40 | F3 val [0,2) of (2,0) | not characterised |
| M4 τ=8 | 10 | 37 | 11.91 | 40 | F3 val [0,2) of (2,0) | not characterised |
| M4 τ=16 | 10 | 37 | 11.91 | 40 | F3 val [0,2) of (2,0) | not characterised |

Exact values (fractions, not the decimals above) are in `joined.json`. Two of the five cells
that beat the random expectation (M3 τ = 8 and 16) do so with a first hit whose induced maps
are constant (saved `nonf3_full_maps.json` evidence, row 1918 and 1919). The other three
(M2 τ = 1, M4 τ = 1 and 2) are F3 projections, which that evidence does not cover; nothing
is inferred about their usefulness from the FULL label.

## 4. Mechanism (why the two comparators disagree)

- **The canonical comparator is structurally late.** FULL groupings in M2 and M4 are almost
  all F3 single-block projections, whose canonical IDs start at 49; after removal of the nine
  F1 val recodings, the first F3 sits at canonical position 41 and F2 and (ID 48) at 40.
  Every available cell has r_C = 41 (first F3) or 40 (F2 and is FULL: M3 τ ≥ 2, M4 τ ≥ 4). Beating canonical order therefore mostly measures that canonical
  order places F3 after the 36 lossy F1 candidates; it is a weak baseline.
- **The score saturates as τ grows.** Partitions with R = 1 out of 9: M1 1, 9, 9, 9, 9;
  M2 2, 4, 6, 8, 9; M3 0, 0, 0, 0, 2; M4 1, 3, 6, 9, 9 (τ = 1 … 16). With 9 or 5 frames, an
  eligible set needs three of very few frames and is then usually regular. When all nine
  partitions tie, the declared tie rule (ascending ID) returns canonical order with F2 moved
  last, which is why r_G is 37 in M2 τ = 16 and M4 τ = 8, 16 (36 F1 lossy candidates first).
  This is a property of the declared score on these trajectory lengths, observed after the
  freeze; no tie rule or trajectory length was changed.
- **M3 (rule 30).** The only FULL groupings are F2 and (UNAVAILABLE, ranked last at 124) and
  F4 and∘and (4,0) o₂=0; both have constant induced dynamics. The gap rank of the F4 candidate
  falls from 119 to 18 as τ grows, which tracks saturation of its (4,0) partition, not any
  dynamical property of the grouping.

## 5. Audit

Independent audit (`audit/audit.json`, no producer function imported, seqdecon not on its
path): VALID_COMPLETE — 24 trajectories, 1,536 transitions against the owner table and, for
M2 and M1, against x+1 mod 256 and a hand-written rule 150; declared controls (rule 150:
1 → 131; counter 255 → 0); 8,368 occurrence records; 180 scores; 2,510 rank positions by
cross-multiplied rational comparison; 20 endpoints and both tallies. Three corruptions of
copies were caught (`audit/corruptions.json`): an altered occurrence index (content check,
seal disabled), a swap of two ranked IDs (rank-position check) and a changed FULL label in a
copied `results_d` (trusted-input hash).

## 6. Tests, mutations, reproduction

73 accepted regression tests pass with the adopted source revision; 32 focused tests and 15
dependency tests pass; 6 of 6 mutants are killed by a declared relevant assertion
(`logs/mutations.json`). `run.sh` reproduces production, join and audit in a fresh
destination; all eight production files and `audit.json` were byte-identical.

## 7. Cost

One production run: trajectories 0.0105 s, scoring and ranking 0.0739 s (includes writing
the occurrence records). These are single measurements, not a search-runtime benchmark, and
no speedup is claimed from rank.

## 8. Limits

- Labels were known before the run; process separation blocks mechanical leakage only.
- Exploratory, descriptive, 14 available cells; no significance test, no population claim.
- Nested candidates are ranked by their first-level partition; the value of nesting is not
  tested.
- The random reference fixes N, m and the candidate multiset; it is an ordering baseline, not
  a causal null.
- F3 first hits are NOT_CHARACTERISED for dynamics; no new endpoint was created.
