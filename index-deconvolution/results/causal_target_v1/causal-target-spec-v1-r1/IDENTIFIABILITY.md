# Identifiability and ambiguity — four declared witnesses

Declaration: `witnesses.json` version 2 (sha256 in `witness_results.json`). Version 1 was
corrected **before any checker existed** (one hand-arithmetic slip in W2 prose; expected integers
unchanged) and is retained as `witnesses_v1_superseded_precheck.json`. Checker:
`check_witnesses.py`, standard library only, imports no project module. Run 1 failed 49/51
(`witness_results_attempt1_failed.json`; the checker reported only the first violating pair, see
W4). Run 2: **53/53 pass** (`witness_results.json`): W1 10/10, W2 24/24, W3 10/10, W4 9/9.
Two checks in run 2 (the complete lists of violating pairs in W3 and W4) were written into the
checker after run 1, not into the declaration; they are **post hoc** and hand-verifiable below.
These are mathematical sanity checks of hand-written maps on at most 3 bits. They are not
performance data and not learned recovery.

States are written x1x2(x3).

## W1 — passive ambiguity, one chosen query resolves it (R2 versus R4)

| x | 00 | 01 | 10 | 11 |
|---|---|---|---|---|
| identity I(x) | 00 | 01 | 10 | 11 |
| swap S(x) | 00 | 10 | 01 | 11 |

From 00 both trajectories are 00, 00, 00, … Every observed transition is 00→00, so the
declared pair {I, S} is **AMBIGUOUS** under R2. Without a declared pair the version space is
larger: 4^3 = 64 two-bit maps fix 00, and 9 networks in the class "each node depends on at most
one input" do (node functions with f(00) = 0 are 0, x1, x2). Under R4, a single query at 01
(or 10) returns 01 under I and 10 under S; the diagonal queries 00 and 11 return the same answer
for both and distinguish nothing. Consequence for the contract: observed agreement is never
identification, and a query is informative only if the candidate maps differ there.

## W2 — functional support is identifiable; syntax and declared edges are not (R3)

A: y = AND(x1, x2), declared {x1, x2}. B: y = (x1 ∧ x2) ∨ (x1 ∧ x2 ∧ x3), declared
{x1, x2, x3}. By absorption both equal x1 ∧ x2: the tables are 1 exactly at 110 and 111.
Flipping x3 never changes the value; flipping x1 or x2 at 110 does. The complete table therefore
fixes the function, its essential set {x1, x2} and its reduced table (0, 0, 0, 1 over 00, 01,
10, 11). It cannot say whether x3 was declared, nor which of the infinitely many equal formulae was
written: two different (syntax, declared set) pairs map to the one table. The full-table
deconvolution recovers exactly what the table determines (E1); a canonical name such as AND is a
representation choice within the equivalence class.

**Counting attachment (audit of PROTOCOL_screen_identification §3).** On two inputs there are
2 constants, 4 functions with exactly one essential input and 10 with both; so 6 distinct
functions have at most one essential input, against 8 padded (support, table) pairs, because each
constant is counted under both supports. A 2-node network in this class is one of 36; each query
returns one of 4 successors; any adaptive learner needs ⌈log4 36⌉ = 3 queries in the worst case.
The non-adaptive set {00, 01, 10} separates all six node functions, and no pair of states does,
so 3 is exact for this tiny class. E_3 = 256 − 3·10 − 3·2 − 2 = 218, which gives the distinct
counts in EXISTING_EVIDENCE §2. Tightness at n = 2 says nothing about tightness at n ≥ 50.

## W3 — a lossy projection admits a macro map for one dynamics and not another

α(x1, x2) = x1, fibres {00, 01} → 0 and {10, 11} → 1.

| x | 00 | 01 | 10 | 11 |
|---|---|---|---|---|
| identity | 00 | 01 | 10 | 11 |
| xor_first: (x1 ⊕ x2, x2) | 00 | 11 | 10 | 01 |
| α of xor_first successor | 0 | 1 | 1 | 0 |

Identity maps each fibre into itself: F̄ = identity on {0, 1}. Under xor_first, 00 and 01 share
α = 0 but their successors have α = 0 and 1; likewise 10 and 11 (α = 1 → 1 and 0). Both fibres
violate the condition, so no F̄ with α∘F = F̄∘α exists. Control: the bijective relabelling
(x1, x2) ↦ (x2, x1) admits a macro map for **both** dynamics, because singleton fibres make the
condition vacuous. An invertible codec dictionary is a change of name; only a lossy α can carry a
macro-level regularity, and only a lossy α can fail.

## W4 — autonomous consistency without intervention consistency

α(x1, x2) = x1 ⊕ x2, F = identity. α∘F = α, so F̄ = identity: autonomous consistency holds.
Intervention q: reset x1 := 0, then apply F once. F_q = (00, 01, 00, 01) on (00, 01, 10, 11),
and α(F_q(x)) = x2. The states 00 and 11 share α = 0 and give next α = 0 and 1; the states 01 and
10 share α = 1 and give 1 and 0. Any macro operation g on {0, 1} would need g(0) = 0 and
g(0) = 1, so none of the four maps {0,1} → {0,1} represents q. The macro description is exact
for the autonomous dynamics and **cannot express** this micro intervention. Run 1 of the checker
reported the α = 1 pair (01, 10) where the declaration named the α = 0 pair (00, 11); both
violate. The conclusion (no representing macro operation) passed in run 1. The defect was the
checker's first-pair convention, and the declaration was not changed.

## Guarantees stated with their scope

| statement | model class | access | equivalence | status |
|---|---|---|---|---|
| F and every S_i are determined by the table | deterministic full-state maps on {0,1}^n | R3 | functional equality on all states | proved (`bitacora/01` items 1–4; W2) |
| syntax and declared edges are not determined | same | R3 | — | proved by W2 (two implementations, one table) |
| Q ≥ ⌈log2 N(n,k)⌉ worst case | C(n,k) | R4 adaptive | functional | proved (EXISTING_EVIDENCE §2) |
| class membership not certifiable with < 2^n queries | C(n,k), n > 2k | R4 | — | proved (TARGET_CONTRACT §3) |
| macro map exists iff fibres map into fibres | deterministic F, any α | — | exact on the declared domain | proved (ABSTRACTION_CONTRACT §2); W3 |
| autonomous consistency does not imply intervention consistency | as above, reset intervention | — | — | W4 counterexample |
