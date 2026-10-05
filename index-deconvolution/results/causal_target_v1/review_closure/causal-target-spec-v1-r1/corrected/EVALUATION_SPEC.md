# Evaluation specification — corrected

> **Corrected copy** (`review_closure/causal-target-spec-v1-r1`, 2026-10-05). Original preserved unchanged at
> `causal-target-spec-v1-r1/EVALUATION_SPEC.md`. Changes are marked **[C-R1]**, **[C-R2]** or **[C-R3]** and listed in `../CHANGELOG.md`.


Applies to any future execution under TARGET_CONTRACT T\* or ABSTRACTION_CONTRACT. Nothing here
was run.

## 1. Endpoints, scored separately and never merged

| id | endpoint | unit | ground truth | success means |
|---|---|---|---|---|
| (i) | functional recovery | node and network | f_i on all 2^n states (full table, n ≤ 16; symbolic decision-diagram identity above, labelled as such) | IDENTIFIED and equal on every state |
| (ii) | support recovery | node | S_i = essential set of the true f_i (never the declared C) | reported S_i equals true S_i; precision and recall of edges reported **only** for IDENTIFIED and AMBIGUOUS-with-unique-support nodes, with denominators |
| (iii) | predicted intervention answers | (q, x) pair | true F_q(x) for declared q ∈ Q (reset subsets; mechanism replacement f_i := c) | equality on all declared pairs; exhaustive over x when n ≤ 16 |
| (iv-a) | **preliminary**: per-q induced-map existence **[C-R3]** | (α, q, fibre) | §2 fibre condition applied to each F_q separately | the fibre condition holds for that q on every declared pair; necessary for (iv-b), never sufficient, never reported as abstraction consistency |
| (iv-b) | declared abstraction contract **[C-R3]** | (q, x) for q ∈ Q (identity intervention included), x ∈ D | ABSTRACTION_CONTRACT §3 with the **supplied** α, β, macro codomain Ȳ and maps F̄_q̄ | α(F_q(x)) ∈ Ȳ and α(F_q(x)) = F̄_β(q)(α(x)) on **every** declared (q, x); this enforces agreement among all q sharing one β-image. Outcome CONSISTENT (all declared pairs checked and equal), INCONSISTENT (any checked pair fails), INCOMPLETE (no failure, some declared pair unchecked); denominators |Q|·|D| declared versus checked |

Exact equivalence (i) is assessable only on a finite class with known ground truth. When only
held-out query accuracy is available, the result is labelled **predictive only** and does not
count for (i), (ii) or (iii).

## 2. Outcome taxonomy and denominators

Per node and per network, exactly one of:

| outcome | meaning | scoring |
|---|---|---|
| IDENTIFIED-CORRECT | singleton consistent set, equal to truth | success |
| IDENTIFIED-WRONG | singleton consistent set (within the class), not equal to truth (truth outside class, or a bug) | **error**; confident misidentification is never a compression success |
| AMBIGUOUS | ≥ 2 consistent members at budget end | justified when the truth is ambiguous at that budget; counted separately, not as an error and not as success |
| ABSTAIN | stopped by budget or cap before the consistent set could be enumerated | separate count |
| INVALID | answers inconsistent with every class member, or a repeated query with two answers | separate count. **[C-R3]** For an oracle verified to lie in the class, INVALID is a harness defect and halts the run; for a deterministic oracle not verified in-class it is a correct outcome (class membership falsified). A repeated query with two answers refutes determinism itself |
| FAILED-RUN | crash, timeout of the harness, missing output | separate count |
| UNAVAILABLE | the endpoint could not be computed (e.g. no ground truth) | reported with reason |

Report **intended** and **available** denominators for every table. A missing value is never
replaced by zero, by the budget, or by the competitor's value. Medians are reported with the full
per-instance list (render, not summary).

## 3. Costs reported for every arm

Queries submitted (distinct and total), bits returned (n per query), wall time, peak RSS, and the
description length of every supplied object (hypothesis class declaration, features, α,
dictionaries, intervention set) under DESCRIPTION_LENGTHS. No entropy, BDM sum or unexplained
score enters any criterion.

## 4. Fair competitors under the same access

| arm | access | role |
|---|---|---|
| full-table `deconvolve` (owner) | R3, 2^n queries charged | reference ceiling for (i)–(iii); never given to a query arm |
| random-state consistency learner with the **same** certifier | R4 restricted to i.i.d. uniform states, pinned seed | isolates the value of adaptivity |
| BoolNet `bestfit`/`reveal` on random samples (historical S2 competitor) | R4 random states | continuity with the screen; lenient and unique criteria both reported |
| **[C-R1]** Bshouty and Costa 2017, arXiv:1706.06934v1, §3.2 Theorem 2 | R4: one shared non-adaptive query set A, |A| = O(k·2^k·log n), each answer used for all n coordinates (`../LITERATURE_MAPPING.md`) | existing deterministic exact learner for C(n,k); any future query study must be compared with it, not only with RAND or the full table |
| Akutsu, Miyano and Kuhara 1999 [8] | R4 random states (i.i.d. uniform INPUT patterns); Proposition 1 gives a deterministic sufficient condition (all assignments to every 2K-subset appear) **[C-R1]** | read in the primary PDF; mapping in `../LITERATURE_MAPPING.md` |
| Akutsu et al. 2003 [9] chosen perturbations | **unverified; primary source not accessed in the closure (publisher returned HTTP 403)**: its perturbations are described as gene disruptions and over-expressions (mechanism replacement), possibly with a different observation model | included **only** if its primary source is read and its access regime is mapped onto R4 or explicitly re-priced; otherwise UNAVAILABLE with the reason |

Prohibited: an equivalence oracle counted as a free state query; exhaustive tables given to one arm
and withheld from another without charging 2^n; competitor guarantees transferred without reading
the primary source; installations in this phase.

## 5. Information bound

The only bound used is Q ≥ ⌈log2 N(n,k)⌉ for worst-case adaptive exact identification in C(n,k)
(EXISTING_EVIDENCE §2). It constrains worst-case guarantees of an algorithm over the whole
class; it is not a per-instance target, and a sample maximum is not a worst case. It is a lower
bound only. No ratio to it is called "headroom" unless a matching upper bound for the
same class and access is also stated.
