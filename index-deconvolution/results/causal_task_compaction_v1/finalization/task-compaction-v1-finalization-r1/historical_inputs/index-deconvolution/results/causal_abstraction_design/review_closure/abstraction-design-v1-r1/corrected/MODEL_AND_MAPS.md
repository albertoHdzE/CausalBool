# Models, encoding, candidate maps and interventions — `abstraction-design-v1-r1`

> **Corrected copy** (`review_closure/abstraction-design-v1-r1`, closing REVIEW R1–R3 and nonblocking notes). Original unchanged at `../../../abstraction-design-v1-r1/`. Changes: `../CHANGELOG.md`.

**Design only. NOT AUTHORIZED FOR EXECUTION.** Every count below follows by hand
arithmetic from the declarations in this file; nothing was simulated, enumerated or
run to obtain it. Contract terms (α, F̄, Q, β, Ȳ, (R-a), (R-b), (iv-a), (iv-b)) are those
of the accepted corrected `ABSTRACTION_CONTRACT.md` and `EVALUATION_SPEC.md`
(`../../causal_target_v1/review_closure/causal-target-spec-v1-r1/corrected/`).

## 1. State encoding (common to every model)

- A state is an integer x ∈ [0, 2^n). **Bit i is node i, 0-based, LSB-first**:
  x_i = (x >> i) & 1, the convention of `src/deconvolution.py` (line 34) and `src/causalbool.py`.
- State-to-string: s(x) = x_0 x_1 … x_{n−1}, node 0 leftmost (the project's
  `Reverse[IntegerDigits[…]]` convention). A word at positions [a, a+w) of s(x) is the
  block of nodes a … a+w−1.
- The token value of a block B = (a, …, a+ℓ−1) is val_B(x) = Σ_{k<ℓ} x_{a+k}·2^k. This is
  the **global alignment rule**: a token ID is the block's integer value under the declared
  bit order, the same function of state for every example. Per-string first-occurrence IDs
  (as in the dictionary views of `hierarchy_dictionary_v1`) are **not** used as macro labels.
  Such a label can be a deterministic function of the string (hence of the state); the objection is
  that its meaning is not aligned across examples (the same ID names different block values in
  different strings) and that it discards the value itself.
- Domain D = X = {0,1}^n (the whole space) for every check. Hence F_q(D) ⊆ D for every q,
  Ȳ = α(X) is admissible, and iteration of a consistent macro model is exact by induction.
  No restricted domain is used, so the one-step-only caveat of REVIEW.md does not arise.

## 2. Models (finite, deterministic, exact ground truth)

| id | n | |X| | definition | owner / source | role |
|---|---|---|---|---|---|
| M1 | 8 | 256 | elementary CA **rule 150** on a periodic ring: x'_i = x_{i−1} ⊕ x_i ⊕ x_{i+1} (indices mod 8) | `heterogeneous_eca_network([150]*8)`, `src/ca_deconvolution.py:84` (rule index 4l+2c+r, left = i−1) | linear; hand-derivable truth; positive and negative controls |
| M2 | 8 | 256 | **binary up-counter** x ↦ x+1 mod 256: f_0 = ¬x_0, f_i = x_i ⊕ (x_0 ∧ … ∧ x_{i−1}) | declared family; built as a LUT `Network` by the existing owner of `Network` (no new semantics) | nonlinear (carry chain); hand-derivable truth; temporal-scale controls |
| M3 | 8 | 256 | elementary CA **rule 30** on a periodic ring, same owner and orientation as M1 | `heterogeneous_eca_network([30]*8)` | nonlinear, homogeneous; **no outcome predicted** |
| M4 | 10 | 1024 | `egfr_signaling.bnet`, node order v000…v009 as in the file | `results/screen_identification/corpus/bio/egfr_signaling.bnet`, parsed by `src/bnet.py:parse_bnet` | nonlinear, heterogeneous, owned file; **no outcome predicted** |

Hand facts used below (proved in `DESIGN.md` §A):
- M1 over GF(2)[s]/(s^8−1): F = 1+s+s^{−1}, F² = 1+s²+s^{−2}, **F⁴ = 1** (s⁴ = s^{−4}).
  M1 is a bijection with F⁴ = identity; at 3 of the 5 scales (τ ∈ {4, 8, 16}) every **autonomous**
  check is trivial. Intervention checks at those scales are not trivial (F_q = F^τ∘r_q = r_q for
  boundary resets and flips; knockouts act throughout τ) and remain informative.
- M2: F^τ(x) = x+τ mod 256.
- Rule 30 and M4 carry no hand prediction; their outcomes are the open question.

Model count: 4. Total micro states 3·256 + 1024 = **1,792**.

## 3. Temporal sampling and intervention timing

Macro step = τ micro steps, τ ∈ T = {1, 2, 4, 8, 16} (|T| = 5). For τ and micro intervention q:
- reset r_{j,c} (x_j := c) and flip φ_j (x_j ^= 1) act **at the macro-step boundary**:
  F_q = F^τ ∘ r_q;
- knockout κ_{j,c} (mechanism replacement f_j := c, owner `src/reprogramming.py:knockout`)
  is active during **all τ updates**: F_q = (F_{κ})^τ;
- tick ϑ (one extra micro step): F_q = F^{τ+1}; a temporal intervention, declared so that
  temporal mis-alignment can be tested;
- identity q_id: F_q = F^τ.

Interventions inside a macro step (between micro steps) are **not** declared and not tested.

Declared Q for Track D, in this order (the ordering is the tie and representative rule):
q_id; r_{0,0}, r_{0,1}, r_{1,0}, …, r_{n−1,1}; φ_0 … φ_{n−1}; κ_{0,0}, κ_{0,1}, …, κ_{n−1,1}; ϑ.
|Q| = 1 + 2n + n + 2n + 1 = **5n+2**: 42 for n = 8, 52 for n = 10. All admissible from every x.

## 4. Candidate family A (identical formula for every model)

**Partition P(w, o, n)** of node indices 0…n−1 (non-cyclic, also on rings): if o > 0 a head block
[0, o); then blocks [o+kw, o+(k+1)w) ∩ [0, n) for k = 0, 1, …; the last block may be ragged.
Ragged heads and tails are **kept** as blocks of their own length; nothing is dropped.
Widths W = {2, 3, 4}, origins o ∈ {0, …, w−1}: 2+3+4 = **9 (w, o) pairs**.

Block counts b(w,o,n) = [o>0] + ⌈(n−o)/w⌉:

| n | w=2: o0, o1 | w=3: o0, o1, o2 | w=4: o0, o1, o2, o3 | total |
|---|---|---|---|---|
| 8 | 4, 5 | 3, 4, 3 | 2, 3, 3, 3 | **30** |
| 10 | 5, 6 | 4, 4, 4 | 3, 4, 3, 3 | **36** |

Per-block functions G = {val, par, cnt, or, and}: val = token value (injective on the block),
par = XOR, cnt = popcount, or, and. On a 1-bit block all five coincide with the bit.

| family | formula | levels | count n=8 | count n=10 | reversible? |
|---|---|---|---|---|---|
| F1 blockwise vector | α(x) = (g(B_1), …, g(B_b)) over P(w,o,n), g ∈ G | level 1 | 9·5 = 45 | 45 | g = val: yes (9 recodings); others lossy |
| F2 global | g over the single block [0,n), g ∈ {par, cnt, or, and} | level 1 | 4 | 4 | lossy |
| F3 single-block projection | α(x) = val_B(x) for one block B of one P(w,o,n) | level 1 | 30 | 36 | lossy (drops other blocks) |
| F4 nested (analyst-imposed) | α₂ = g over P(2, o₂, b) applied to the F1 output y of (w,o,g), g ∈ {par, or, and}, o₂ ∈ {0,1} | level 2 | 9·3·2 = 54 | 54 | lossy |
| C controls | identity, constant 0 | — | 2 | 2 | identity yes |
| **total** | | | **135** | **141** | |

Candidate pairs (α, τ): 135·5 = **675** per n=8 model, 141·5 = **705** for M4;
over all models 3·675 + 705 = **2,730**.

Exhaustive reference work (every (α, τ, q, x), no filtering):
n=8: 675·42·256 = 7,257,600 per model, ×3 = 21,772,800; n=10: 705·52·1024 = 37,539,840;
**total 59,312,640 pair checks**. Autonomous-only: 2,025·256 + 705·1,024 = **1,240,320**.

Equivalence of candidates: two α are the same abstraction iff they induce the same partition
of X (equal fibres). Duplicates (e.g. F4 par∘par with (w,o)=(2,0),o₂=0 and F1 par with (4,0) on
n=8; a 1-bit head under several (w,o)) are reported raw **and** grouped; ambiguity counts use
distinct partitions. Reversible maps (val in F1, identity) are recodings: injectivity guarantees
that each **individual** induced map G_q exists (autonomous and per-q), which is a theorem used as
a checker test. It does **not** guarantee agreement of different q under a many-to-one β; that is
why §5 keeps local positions for value-preserving maps. Recodings are never counted as abstractions.

**Nesting.** F4 is nesting *imposed by the analyst*: a candidate construction, not an empirical
discovery. No "repeated structure found" endpoint is declared (withdrawn; it had no precise test).
Scale invariance and grammar (CONCAT/REPEAT) are not tested.

**Canonical order and IDs (R3).** Within a model, candidate id k = 0, 1, … in this order:
F1 by w ascending, o ascending, g in (val, par, cnt, or, and) — ids 0–44; F2 g in (par, cnt, or,
and) — 45–48; F3 by w, o, block index ascending — 49–78 (n=8) / 49–84 (n=10); F4 by w, o, g in
(par, or, and), o₂ in (0, 1) — 79–132 / 85–138; C identity then constant — 133–134 / 139–140.
D row id r = offset(model) + 5·k + τ-index (τ-index 0…4 for τ = 1, 2, 4, 8, 16), offsets
M1 0, M2 675, M3 1,350, M4 2,025: rows 0–2,729, unique.

## 5. Structural β for Track D (declared before checking, independent of outcomes; R1-corrected)

Notation: q acts on bit j with operation op ∈ {reset, flip, knockout} and value c (none for flip);
for a coordinate whose block is B = [a, a+ℓ), the **local position** is p = j − a.

**β_fine (primary scheme, every candidate).** β(q_id) = ∅; β(ϑ) = tick; for every other q,
β(q) = (op, k, p, c) where k is the macro coordinate containing j (F1/F3/F4 level-1 block index;
F2 and constant: the single cell; identity: k = j, p = 0; F3 with j ∉ B: k = out, p = j). Because
j ↦ (k, p) is injective, **every β_fine class is a singleton**: the representative rule has no
hold-out and full intervention consistency under β_fine equals per-q existence (E3) for all of Q.
Value-preserving maps (F1 val, F3 val, identity) are scored **only** under β_fine.

**Declared coarse hypotheses (scored separately, never merged with E3; fixed now, never tuned).**
- **H-COARSE** (lossy maps only: F1 par/cnt/or/and, F2, F4): β(q) = (op, k, c), position dropped;
  F4 uses the level-2 coordinate.
- **H-OUT** (F3 only): every q with j ∉ B joins class ∅ with q_id (claim: out-of-block
  interventions are invisible at the macro level).

**Representative rule.** Within a class, members are ordered as in §3; the **first** member q*
is the representative (for any class containing q_id, q* = q_id). F̄_class := G_{q*} if the fibre
condition holds for F_{q*} on all of X. If it does not, the class is **REP-NOEXIST**: an observed
structural failure (not missing evidence, not a harness defect). No other member is promoted.
Each other member q is reported as: AGREE / DISAGREE (G_q exists and differs from F̄_class on d > 0
macro states; d reported) / MEMBER-NOEXIST (G_q does not exist) / NOT-EVALUABLE (reason
"representative has no induced map") / MISSING (record absent). No numeric mismatch is ever
assigned to a comparison with a nonexistent map.

**Why (R1 counterexample, hand proof, not run).** M2, τ = 1, α = val[0,4) (P2). At x = 0:
φ_0 gives x = 1, step → 2, α = 2; φ_1 gives x = 2, step → 3, α = 3. Both start from macro state
y = 0, so a single map shared by the coarse class (flip, in) cannot output both; the
position-labelled operations agree (macro flip of bit 0 of y = 0 gives 1, +1 = 2; of bit 1 gives
2, +1 = 3). The same occurs for F1 val (w,o) = (4,0) on M2 at τ = 1: φ_0 and φ_1 from x = 0
give macro states (2, 0) and (3, 0).

## 6. Supplied controls (Track V) — formulas fixed here, outcomes hand-derived

| id | model | α | τ | Q (size) | Ȳ, F̄ and β supplied | expected | pairs | expected failing |
|---|---|---|---|---|---|---|---|---|
| P1 | M1 | F1 par, (w,o)=(2,0) | 2 | q_id; φ_0…φ_7; block resets ρ_{b,(c0,c1)} setting bits 2b,2b+1, b<4, 4 values (25) | {0,1}⁴; F̄ = rule 150 on a 4-ring; β(φ_j) = flip ȳ_{⌊j/2⌋}; β(ρ_{b,c0c1}) = reset ȳ_b := c0⊕c1 | CONSISTENT; flip and block-reset classes each share β in pairs | 6,400 | 0 |
| N1 | M1 | as P1 | 2 | q_id; r_{j,c}, j<8 (17) | β(r_{j,c}) = reset ȳ_{⌊j/2⌋} := c (plausible, wrong) | INCONSISTENT; (iv-a) fails for all 16 resets | 4,352 | **2,048** (x_partner = 1: 128 per reset) |
| P2 | M2 | F3 val, block [0,4) | 1 | full Track-D Q (42) | {0,1}⁴ ≅ Z/16; F̄(y) = y+1; reset/flip j<4 → macro reset/flip **of local bit j** then F̄; knockout j<4 → (y+1) with bit j := c; every q on j ≥ 4 → ∅; ϑ → F̄² | CONSISTENT | 10,752 | 0 |
| P3 | M2 | F3 val, block [4,8) | 16 | q_id; r_{j,c}; φ_j (25) | F̄(h) = h+1 mod 16; q on j<4 → ∅; on j ≥ 4 → macro op on bit j−4 then F̄ | CONSISTENT | 6,400 | 0 |
| N2 | M2 | as P3 | 16 | q_id; ϑ (2) | β(ϑ) = ∅ (wrong) | INCONSISTENT; (iv-a) fails for ϑ | 512 | **16** (low nibble = 15) |
| N3 | M2 | as P3 | 1 | q_id (1) | F̄(h) = h | INCONSISTENT; autonomous fibre condition fails (carry at low nibble 15) | 256 | **16** (low nibble = 15: image h+1 ≠ h) |
| P4 | M1 | F4 par∘par, (w,o)=(2,0), o₂=0 | 2 | q_id; φ_0…φ_7 (9) | {0,1}²; F̄ = swap(z_0, z_1); β(φ_j) = flip z̄_{⌊j/4⌋} | CONSISTENT; same partition as F1 par (4,0): nesting is representation | 2,304 | 0 |
| C1 | all | constant | all τ | Track-D Q | trivial | CONSISTENT, 0 bits retained | — | 0 |
| C2 | all | identity | all τ | Track-D Q | induced | (iv-a) passes for every q; recoding, n bits retained | — | 0 |

Track V supplied pairs (P1…P4, N1…N3): 6,400 + 4,352 + 10,752 + 6,400 + 512 + 256 + 2,304
= **30,976**; expected failing pairs 2,048 (N1) + 16 (N2) + 16 (N3) = **2,080**, all others pass.
(An intermediate drafting slip set N3 to 256; it is recorded in `attempts.jsonl` A3 and
withdrawn: for low < 15 the image is h = F̄(h), so only the 16 carry states fail.)
All supplied β in P2/P3 already retain the local bit; P1/P4 group positions only on lossy
parity maps, where the grouping is proved by hand (§A.2). R1 changes no Track-V count.

**Prospective fixtures (R1; expectations by hand proof, NOT run).**
| id | model, α, τ | scheme | expected |
|---|---|---|---|
| FX-R1a | M2, F3 val [0,4), 1 | β_fine | G_{φ_j} exists for j < 4; all classes singletons; no disagreement |
| FX-R1b | same | coarse (flip, in) applied deliberately as a **wrong-β test** | DISAGREE witnessed at x = 0 (φ_0 → 2, φ_1 → 3); per-q existence still passes |
| FX-R1c | M2, F1 val (4,0), 1 | coarse (flip, block) as wrong-β test | DISAGREE witnessed at x = 0 ((2,0) vs (3,0)); must not be masked by the CONTROL label |
| FX-REP | M1, F1 par (2,0), 2, class {r_{0,0}, r_{1,0}} under H-COARSE | H-COARSE | representative r_{0,0} has no induced map (§A.2) → REP-NOEXIST; r_{1,0} NOT-EVALUABLE; its own E3 reported as no-exist |
Only witnesses are stated; no failing-state counts are claimed for FX rows.

**Hand-predicted calibration H-M2-F3** (autonomous only): block [a, a+ℓ) of M2 is consistent at τ
iff 2^a divides τ (proof `DESIGN.md` §A.3). Over the 30 F3 blocks × 5 τ = 150 raw pairs this
predicts **75** consistent: per (w,o) 9, 11, 7, 10, 8, 6, 9, 8, 7.

**Hand-predicted calibration H-M1-τ**: in M1, all 135 candidates are autonomously consistent at
τ ∈ {4, 8, 16} (F^τ = identity): 405 raw pairs. This calibrates E2 only; it predicts nothing about
per-q existence at those scales.

**Support-closure cross-check X**: an F3 (val) projection onto block B is autonomously consistent
at τ iff every node of B has all its essential variables under F^τ inside B (proof `DESIGN.md`
§A.4). Computed independently with `essential_variables` (`src/deconvolution.py:95`) on the
columns of F^τ; it must agree with the **autonomous** (E2) fibre check on all 630 F3 pairs.
Scope: X concerns autonomous closure under F^τ only. It predicts nothing about per-q existence,
about knockouts replacing a mechanism throughout τ steps, or about any β grouping, and it cannot
remove or reinterpret any non-F3 result.
