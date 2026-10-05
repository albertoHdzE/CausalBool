# Multilevel abstraction-validation design — `abstraction-design-v1-r1`

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
| **D** exhaustive induced-model discovery | R3 tables + Track-D Q | every (α, τ) of the 2,730: autonomous check, per-q existence (iv-a), structural β (§5 of MODEL_AND_MAPS), F̄ induced from the class representative and **tested on the other class members** | **induced-model discovery**; selection cost = 2,730 candidates and 59,312,640 pair checks, charged in full |
| **X** cross-check | R3 | support-closure prediction for every F3 pair vs the fibre result | agreement certificate; also bounds the novelty of F3 results |
| **G** occurrence-gap ranking | trajectory strings, frame n declared | ranks candidates; compared with exhaustive D | **scheduling heuristic only**; never proposes a map outside A and never a causal claim |

Exhaustive D is the reference. G cannot find an abstraction D does not; any G "gain" is only
an earlier rank and has no practical value at n ≤ 10 where exhaustion is cheap.

## 3. Supplied vs induced, and the anti-circularity rule

- Track V: α, F̄, Ȳ and β are written as formulas in `MODEL_AND_MAPS.md` §6 and derived by hand
  in §A below, before any code exists. Success is agreement of a supplied object with truth.
- Track D: F̄ is **induced**. Its existence on all of X is an exact statement (iv-a), not
  predictive validation. The only predictive element is the hold-out: within a β class, the
  map induced from the representative q* is tested on every other member. Single-member classes
  get no hold-out. Constructing F̄ from all transitions and reporting agreement on them is
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
- Endpoint G1 per (model, τ) cell: m = number of FULL candidates (Track D) among N ranked; rank
  r_G of the first FULL candidate vs the exact uniform-order expectation (N+1)/(m+1) and vs the
  canonical order. Cells with m = 0 are UNAVAILABLE. Report all 20 cells; no significance test
  (cells are few and dependent). Gaps, grammar and fractality make **no causal claim** here.

## 5. Endpoints (per (α, τ) in D; per control in V)

| id | endpoint | definition | denominator (intended) |
|---|---|---|---|
| E1 | information retained | |α(X)| and log2|α(X)| (a count, not an entropy); fibre-size min/max; nontrivial iff 1 < |α(X)| < |X| | 2^n states |
| E2 | autonomous consistency | §2 fibre condition for F^τ, all of X | 2^n |
| E3 | per-q existence (iv-a), preliminary | fibre condition for each F_q | |Q|·2^n |
| E4 | full intervention consistency (iv-b) | (R-a),(R-b) with supplied (V) or representative-induced (D) F̄_β(q); hold-out members reported separately | |Q|·2^n; hold-out pairs = (|Q| − #classes)·2^n |
| E5 | coverage | checked/declared pairs; must be 1 for CONSISTENT | as above |
| E6 | ambiguity | number of distinct partitions with FULL per (model, τ), raw and deduplicated, all listed | per cell |
| E7 | costs | candidates evaluated, pair checks, wall time, peak RSS; α description length under `src/description_lengths.py` **reported, never a criterion** | — |
| E8 | restriction | for AUT-pass candidates failing some q: the passing subset Q′ and |Q′|/|Q|, labelled **post-hoc restriction**, never a valid declared-Q claim | |Q| |

Classification per (α, τ): FULL (nontrivial lossy, E2 and E4 pass on every declared pair),
RESTRICTED, AUT-ONLY, FAIL, CONTROL (identity, constant, reversible). No compression score
substitutes for any endpoint.

**Failure precedence** (first applicable wins): FAILED-RUN (harness error) > CHECKER-INVALID
(any Track-V or calibration outcome differs from its hand prediction: halts, no D or G result
is reported) > INCONSISTENT > INCOMPLETE (unchecked declared pair; never a pass) > CONSISTENT.
Missing values are never zero.

## 6. What success and failure would establish

- **V/X/calibrations pass**: the checker implements the corrected contract on 7 supplied controls,
  405 + 75 hand-predicted autonomous outcomes and every F3 support cross-check. Nothing about the world.
- **D finds a FULL lossy non-F3 candidate in M3 or M4**: within family A, that model admits an
  exact macro variable answering all 5n+2 declared interventions with structural β hold-out.
  An existence statement about A on that model; no claim about other models, other
  interventions, or that the world "has" this level.
- **D finds none there**: within A, the only exact abstractions of M3/M4 are recodings,
  constants and support-closed projections (which X shows add nothing beyond the dependency
  graph of F^τ). It does not show that no abstraction exists outside A.
- **G**: only whether gap order would have scheduled valid candidates earlier on these cells.
- **Generalisation**: none. Exhaustive verification is exact on its declared domain. A broader
  claim needs held-out models declared in advance (candidate: `lac_operon.bnet`, 7 nodes,
  untouched here) and is not part of this draft.
- **Scale invariance / fractal dynamics: NOT TESTED.** The only identifiable statistic in reach
  (rule-closure: the level-k macro map equals the same ECA rule on the n/2^k ring at τ = 2^k)
  is non-degenerate at one level only on n ≤ 10 (M1 has F⁴ = 1), and rule 150 being a fixed
  point of coarse-graining is already known (Israeli & Goldenfeld 2006). P1 reproduces it as a
  control; no scale-invariance claim follows.

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
conversely if all are inside B the image block is a function of the block. Hence X is exact.
