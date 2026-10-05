# Evaluation specification

Applies to any future execution under TARGET_CONTRACT T\* or ABSTRACTION_CONTRACT. Nothing here
was run.

## 1. Endpoints, scored separately and never merged

| id | endpoint | unit | ground truth | success means |
|---|---|---|---|---|
| (i) | functional recovery | node and network | f_i on all 2^n states (full table, n ≤ 16; symbolic decision-diagram identity above, labelled as such) | IDENTIFIED and equal on every state |
| (ii) | support recovery | node | S_i = essential set of the true f_i (never the declared C) | reported S_i equals true S_i; precision and recall of edges reported **only** for IDENTIFIED and AMBIGUOUS-with-unique-support nodes, with denominators |
| (iii) | predicted intervention answers | (q, x) pair | true F_q(x) for declared q ∈ Q (reset subsets; mechanism replacement f_i := c) | equality on all declared pairs; exhaustive over x when n ≤ 16 |
| (iv) | abstraction consistency | (α, q, fibre) | §2–§3 of ABSTRACTION_CONTRACT on the declared domain | the fibre condition holds on every declared, checked pair |

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
| INVALID | answers inconsistent with every class member, or a repeated query with two answers | separate count; an INVALID on a deterministic oracle is a harness defect and halts the run |
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
| Akutsu et al. 2003 [9] chosen perturbations | **unverified**: its perturbations are described as gene disruptions and over-expressions (mechanism replacement), possibly with a different observation model | included **only** if its primary source is read and its access regime is mapped onto R4 or explicitly re-priced; otherwise UNAVAILABLE with the reason |

Prohibited: an equivalence oracle counted as a free state query; exhaustive tables given to one arm
and withheld from another without charging 2^n; competitor guarantees transferred without reading
the primary source; installations in this phase.

## 5. Information bound

The only bound used is Q ≥ ⌈log2 N(n,k)⌉ for worst-case adaptive exact identification in C(n,k)
(EXISTING_EVIDENCE §2). It constrains worst-case guarantees of an algorithm over the whole
class; it is not a per-instance target, and a sample maximum is not a worst case. It is a lower
bound only. No ratio to it is called "headroom" unless a matching upper bound for the
same class and access is also stated.
