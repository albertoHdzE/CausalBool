# Withdrawal and erratum — `DRAFT_EXECUTION_PROTOCOL.md`

Closure `review_closure/causal-target-spec-v1-r1`, 2026-10-05. This document **replaces** a corrected
executable draft; no corrected draft is issued. The original is preserved unchanged at
`causal-target-spec-v1-r1/DRAFT_EXECUTION_PROTOCOL.md` (sha256 `0457d29a…49ca8`).

## Status

**WITHDRAWN — SUPERSEDED.** The draft "query-mode functional recovery in C(n,k)" is withdrawn as a
study. It was never executed or implemented, partly or wholly, and remains not executable. Its
own falsifier F4 (§8) and precondition P1 (`DECISION.md`) are met: Bshouty and Costa,
arXiv:1706.06934v1, §3.2 Theorem 2, give a deterministic non-adaptive exact learner for the
per-coordinate class with d = k, and one shared query set identifies the whole product class C(n,k)
under R4 (proof in `../LITERATURE_MAPPING.md` §2). The disposition is
**NO_JUSTIFIED_IMPLEMENTATION for this proposed study** (`../DECISION.md`).

## Errata to statements in the draft (they remain wrong in the preserved text)

- **E1 [C-R1], §1 "New relative to existing deconvolution".** Exact recovery of C(n,k) from chosen
  state queries is a known problem with a known deterministic algorithm. The draft's novelty is at
  most an engineering re-implementation; it is not a scientific contribution.
- **E2 [C-R1], §4 arm AKUTSU2003.** The competitor list omitted the directly applicable exact
  learner. Akutsu 2003 remains unverified (primary source not accessed).
- **E3 [C-R2], §5 "Confirmation set B, class-uniform".** The specified procedure draws the support
  size j uniformly from {0, 1, 2, 3}, then a support uniformly from C(n, j), then a function with
  exactly j essential variables uniformly from E_j (E = 2, 2, 10, 218). One node function of degree j
  therefore has probability
  P_draft(f) = 1 / [4 · C(n, j) · E_j],
  which depends on j. Its correct name is **degree-stratified, equal-weight-per-degree distribution
  with whole-class support**. It is not uniform over distinct functions or networks.
  A distribution uniform over distinct node functions instead draws j with probability
  C(n, j) · E_j / N(n, 3), N(n, 3) = Σ_{j≤3} C(n, j) · E_j, then the support and the function
  uniformly; node functions are drawn independently, which makes the product network uniform over
  C(n, 3). Hand check, n = 2, k = 1 (E_0 = E_1 = 2, N(2, 1) = 2 + 2·2 = 6): equal degree weights give
  each constant 1/(2·1·2) = 1/4 and each of the four literals 1/(2·2·2) = 1/8 (sum 2/4 + 4/8 = 1);
  the uniform draw gives each of the six functions 1/6. Arithmetic for n = 16, k = 3:
  N(16, 3) = 2 + 16·2 + 120·10 + 560·218 = 123,314, so the uniform degree weights are 2, 32, 1,200 and
  122,080 over 123,314 (degree 3 ≈ 0.990), against 0.25 each in the draft. No sampler for either
  distribution exists or is authorised; none was written or run.
- **E4 [C-R3], §7 halt rule "INVALID for an in-class instance".** Correct as worded (it is restricted
  to in-class instances); see corrected `EVALUATION_SPEC.md` §2 for the out-of-class case.
- **E5, P3/P4.** Generator scope and ownership preconditions lapse with the withdrawal; they are not
  approvals for any future work.

The withdrawal does not make any draft claim correct. It does not state that no future query
algorithm could improve query count or runtime; that would need a separately justified comparison
against existing exact learners.
