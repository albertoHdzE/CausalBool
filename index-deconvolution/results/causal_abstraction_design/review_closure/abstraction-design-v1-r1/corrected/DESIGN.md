# Multilevel abstraction-validation design — `abstraction-design-v1-r1`

> **Corrected copy** (`review_closure/abstraction-design-v1-r1`, closing REVIEW R1–R3 and nonblocking notes). Original unchanged at `../../../abstraction-design-v1-r1/`. Changes: `../CHANGELOG.md`.

**Design only. NOT AUTHORIZED FOR EXECUTION.** Models, encoding, family, interventions and
counts: `MODEL_AND_MAPS.md`. Executable draft: `DRAFT_EXECUTION_PROTOCOL.md`.

## 1. The question, and what it is not

**Substantive question (beyond W3/W4).** In a declared finite family of block-word maps —
three widths, every origin, ragged blocks kept, five per-block functions, five time scales and
one analyst-imposed nesting level — which maps are *exact intervention-consistent abstractions*
of four declared models, and does that set contain lossy, non-projection maps in the two models
(rule 30, EGFR) where no answer is built in, beyond what the dependency structure of F^τ predicts?

It is **not** a compression contest, not a discovery of a universal criterion (the criterion is
the known commuting-square / τ-abstraction condition, `EVIDENCE_AND_LIMITS.md` §2), and not a
test of R1 unknown-string discovery: every track has **simulator access** (labelled R3 tables of
F^τ and F_q). Unlabelled strings appear only in Track G, and there the frame length n is given.

## 2. Four tracks, kept separate

| track | access | what it does | label of its result |
|---|---|---|---|
| **V** supplied validation | R3 tables + declared Q | checks P1–P4, N1–N3, C1–C2 against **supplied** α, Ȳ, F̄, β (fixed in `MODEL_AND_MAPS.md` §6 before any check) | validates the **checker**; no discovery claim |
| **D** exhaustive induced-model discovery | R3 tables + Track-D Q | every (α, τ) of the 2,730: autonomous check, per-q existence (iv-a) under β_fine (singleton classes), and separately scored coarse hypotheses H-COARSE / H-OUT with representative and held-out members (§5 of MODEL_AND_MAPS) | **induced-model discovery**; selection cost = 2,730 candidates and 59,312,640 pair checks, charged in full |
| **X** cross-check | R3 | autonomous support-closure prediction for every F3 pair vs the E2 fibre result | agreement certificate for E2 on F3 only; says nothing about interventions or β |
| **G** occurrence-gap ranking | trajectory strings, frame n declared | ranks candidates; compared with exhaustive D | **scheduling heuristic only**; never proposes a map outside A and never a causal claim |

Exhaustive D is the reference. G cannot find an abstraction D does not; any G "gain" is only
an earlier rank and has no practical value at n ≤ 10 where exhaustion is cheap.

## 3. Supplied vs induced, and the anti-circularity rule

- Track V: α, F̄, Ȳ and β are written as formulas in `MODEL_AND_MAPS.md` §6 and derived by hand
  in §A below, before any code exists. Success is agreement of a supplied object with truth.
- Track D: F̄ is **induced**. Its existence on all of X is an exact statement (iv-a), not
  predictive validation. Under β_fine every class is a singleton, so there is no hold-out. The
  only predictive elements are the declared coarse hypotheses H-COARSE (lossy maps) and H-OUT
  (F3): within a class, the map induced from the representative q* is tested on every other member. Constructing F̄ from all transitions and reporting agreement on them is
  forbidden as a validation claim.
- Both: identity, constant and reversible (val) maps are controls, never findings.

## 4. Occurrence gaps (Track G) — what they propose and what they cannot

Trajectories per model: initial states 0, 1, 2^{n−1}, 2^n−1, Σ_{i even}2^i, Σ_{i odd}2^i
(6), 64 micro steps, sampled every τ steps (frames t = 0, τ, 2τ, … ≤ 64). For (w, o, τ), each
block b and token value v defines an occurrence set O_{b,v} ⊆ frame indices per trajectory; its
**gaps** are first differences (GLOSSARY §5). Score R(w,o,τ) = fraction of occurrence sets with
≥ 3 occurrences whose gaps are all equal; denominator = number of such sets; empty → UNAVAILABLE,
ranked last. Rationale: a block that evolves autonomously and periodically recurs at constant
gaps. Candidates inherit R of their level-1 (w, o); F2 and controls are UNAVAILABLE.
Order: R descending, ties by the declared candidate order.

- R is a **history** statistic: it needs a trajectory and is used **only to rank**. Every α is a
  function of one state. A history-based α (e.g. time since a token last occurred) would need
  an extended state X × {0…T}; it is out of scope and not in A.
- **Population (R3).** Per (model, τ) cell the ranked population is every raw candidate except
  the 11 recoding/constant controls (9 F1 val, identity, constant): N = 124 (n = 8) or 130
  (n = 10). Duplicate partitions **stay** in the population (ranking acts on raw candidates).
  F2 candidates are in the population with R UNAVAILABLE. Candidates with R UNAVAILABLE are ranked
  after every available one, among themselves in canonical order; ties likewise.
- **Pooling.** Occurrence sets are formed per trajectory (never by concatenating trajectories);
  R pools them by counting: denominator = number of (trajectory, block, value) sets with ≥ 3
  occurrences over the 6 trajectories; numerator = those with all gaps equal.
- Endpoint G1 per cell: m = number of FULL candidates among the same N; rank r_G of the first FULL
  candidate vs the exact uniform-random-order expectation (N+1)/(m+1) for **this fixed population**,
  and vs the canonical order. Cells with m = 0 are UNAVAILABLE. Report all 20 cells; deterministic
  ranking, no significance test, **no causal claim**.

## 5. Endpoints (per (α, τ) in D; per control in V)

Every result is scoped to **(family A, declared Q of size 5n+2, β scheme)**; no conclusion leaves
that scope.

| id | endpoint | definition | denominator |
|---|---|---|---|
| E1 | information retained | |α(X)| and log2|α(X)| (a count, not an entropy); fibre-size min/max | 2^n states |
| E2 | autonomous existence | fibre condition for F^τ (identical to the q_id check) | 2^n |
| E3 | per-q existence (iv-a) | fibre condition for each F_q; Q′ = {q : exists} | |Q|·2^n |
| E4 | shared-β agreement | per class of a **coarse** scheme (H-COARSE, H-OUT): representative status and member outcome (MODEL_AND_MAPS §5); under β_fine E4 ≡ E3 | intended pairs = (members − 1)·2^n per class; **inspected** = intended with records present; **evaluable** = inspected where both maps exist; mismatch counts only over evaluable |
| E5 | coverage | checked / declared pairs per endpoint | as above |
| E6 | ambiguity | distinct partitions with FULL per (model, τ), raw and deduplicated | per cell |
| E7 | costs | candidates evaluated, pair checks, wall time, peak RSS (runtime metadata). Description length **deferred**: no owned encoding exists for mixed-alphabet nested maps and none is designed here | — |
| E8 | restriction | |Q′|/|Q| and Q′ listed; **post-hoc restriction**, never a declared-Q claim | |Q| |

### 5.1 Decision table (primary label, β_fine; first matching row wins)

Run-level first: FAILED-RUN (harness error) > CHECKER-INVALID (any Track-V, calibration, X,
or theorem test differs from its hand prediction — including a recoding or identity whose G_q
fails to exist; halts, no D or G result).

| # | condition on records of one (α, τ) | label |
|---|---|---|
| 1 | |α(X)| ∈ {1, 2^n} (constant or injective partition, by E1, not by name) | CONTROL (all sub-results still reported) |
| 2 | E2 fails on some observed state | AUT-FAIL |
| 3 | E2 passes; ≥ 1 non-identity q exists and ≥ 1 q fails (missing records allowed) | RESTRICTED (Q′ a lower bound if records missing) |
| 4 | E2 passes; every non-identity q fails; no missing record | AUT-ONLY (Q′ = {q_id}) |
| 5 | E2 passes; no non-identity q observed to exist; ≥ 1 fails; ≥ 1 missing | NOT-FULL-INCOMPLETE |
| 6 | no failure observed anywhere; ≥ 1 declared pair missing (E2 or any q) | INCOMPLETE (never a pass) |
| 7 | E2 and every q exist on all of X, complete | FULL |

Failure is never overridden by missingness; missing values are never zero. Since q_id ∈ Q and
F_{q_id} = F^τ, an E2 pass always places q_id in Q′.

### 5.2 Coarse-hypothesis label (separate column per scheme, never merged with 5.1)

Per candidate and scheme (H-COARSE or H-OUT), first match: COARSE-DISAGREE (≥ 1 evaluable DISAGREE)
> COARSE-STRUCT-FAIL (≥ 1 REP-NOEXIST or MEMBER-NOEXIST, no disagreement) > COARSE-INCOMPLETE (no
failure, ≥ 1 MISSING) > COARSE-NO-HOLDOUT (every class a singleton) > COARSE-HOLDS. A CONTROL or
FULL primary label never hides a coarse disagreement; both columns are always printed.

## 6. What success and failure would establish (scoped to A / Q / β)

- **V/X/calibrations pass**: the checker reproduces 7 supplied controls, 405 + 75 hand-predicted
  autonomous outcomes, the theorem tests and the 630 F3 autonomous support cross-checks. Nothing
  about the world.
- **FULL for a lossy non-F3 candidate in M3 or M4**: under A, the declared Q and β_fine, that model
  admits an exact macro variable whose induced map exists for every declared intervention.
  An existence statement about that candidate; no claim about other Q, models, or that the
  world "has" this level.
- **No FULL non-F3 candidate in M3/M4**: no member of A attains FULL under this Q and β_fine.
  It does not show that no abstraction exists outside A, under another Q or β, nor that the
  candidates lack autonomous dynamics (AUT-ONLY / RESTRICTED are reported separately).
- **H-COARSE / H-OUT**: whether the declared grouping holds, per candidate; a failure falsifies the
  grouping, not the existence of per-q maps.
- **X**: only autonomous support closure for F3 val projections; descriptive count reported of
  FULL lossy candidates in M3/M4 that are F3 versus non-F3. No stop rule follows from it.
- **G**: only whether gap order would have scheduled FULL candidates earlier on these cells.
- **Generalisation**: none. No held-out model is part of this draft.
- **Scale invariance / fractal dynamics: NOT TESTED.** M1 has F⁴ = 1, so its autonomous checks are
  trivial at 3 of 5 scales; rule 150 as a fixed point of coarse-graining is known (Israeli &
  Goldenfeld 2006, §III.B.1). P1 reproduces it as a control; no scale-invariance claim follows.

## A. Hand derivations

**A.1 M1 algebra.** Over GF(2)[s]/(s^8−1), rule 150 is F = 1+s+s^{−1}. In characteristic 2,
F² = 1+s²+s^{−2} and F⁴ = 1+s⁴+s^{−4}; s⁴ = s^{−4} so F⁴ = 1.

**A.2 P1, N1, P4.** y_i = x_{2i} ⊕ x_{2i+1}. F²x_k = x_{k−2}+x_k+x_{k+2}, so
y′_i = y_{i−1}+y_i+y_{i+1}: α∘F² = F̄∘α with F̄ = rule 150 on a 4-ring, for **all** x. Hence
α(F²(z)) = F̄(α(z)) for every z, and every intervention claim reduces to α(r(x)).
Flip φ_j: α(x⊕e_j) = y ⊕ e_{⌊j/2⌋}. Block reset ρ_{b,c0c1}: α = y with y_b := c0⊕c1, so (0,1),(1,0)
and (0,0),(1,1) share β. Single reset r_{j,c} with partner p: α(r x) = y with y_b := c ⊕ x_p;
the supplied y_b := c is wrong exactly when x_p = 1 and F̄(e_b) = e_{b−1}+e_b+e_{b+1} ≠ 0, so
128 of 256 states fail per reset, 16·128 = 2,048. The fibre pair x, x ⊕ e_j ⊕ e_p separates after
reset, so (iv-a) fails too. P4: z_0 = y_0+y_1, z_1 = y_2+y_3;
z′_0 = (y_3+y_0+y_1)+(y_0+y_1+y_2) = z_1 and z′_1 = z_0: F̄ = swap.

**A.3 M2.** F^τ(x) = x+τ mod 256. For block [a, a+ℓ), if 2^a | τ, adding τ never touches bits
below a, so the block value maps to v + τ/2^a mod 2^ℓ. If 2^a ∤ τ, low part L = 0 gives no carry
into bit a and L = 2^a−1 does; same block value, different images: inconsistent. For P2 every
q on bits ≥ 4 leaves bits 0–3 of the next state unchanged; a knockout of j < 4 replaces only
bit j of the next state. For P3 (τ=16), x+16 leaves the low nibble and adds 1 to h; operations on
bits < 4 are invisible. N2: ⌊(x+17)/16⌋ mod 16 = h+1+[low = 15]. N3: ⌊(x+1)/16⌋ = h+[low = 15].
Counts of H-M2-F3 per (w,o) follow from the block starts listed in `MODEL_AND_MAPS.md` §4 and
the number of τ ∈ {1,2,4,8,16} divisible by 2^a: 5, 4, 3, 2, 1, 0 for a = 0…5+.

**A.4 Support closure.** For an injective-on-block projection val_B, if some i ∈ B has an
essential variable j ∉ B under F^τ, a pair x, x ⊕ e_j has equal α and images differing at i;
conversely if all are inside B the image block is a function of the block. Hence X is exact
for E2 (autonomous) only.
