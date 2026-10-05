# HANDOFF — closure of `causal-target-spec-v1-r1`

**Status: ready for Codex review; not yet accepted.**

Executor: Claude Code, 2026-10-05, under `supervision/causal-target-spec-v1-r1/CLOSURE_CLAUDE.md`
after `REVIEW.md` (CHANGES REQUESTED). Document, proof and literature closure only. No code,
sampler, learner, generator, benchmark, notebook execution, installation, recurring task, commit,
push or publication. The withdrawn draft was not executed or implemented, even partly. The
53-check witness artifact was not re-executed.

## Preservation

- `preservation_before.json`, taken before reading any evidence: 20 run files, 5 supervision
  files, and the 25 inputs of the run's `preservation_after.json`. 25/25 inputs equal their
  recorded hashes (no drift); 20/20 run files equal the supervisor's `audit_review.json`.
- `preservation_after.json` re-hashes the same 50 files at handoff and compares them with the
  before snapshot. Its result is stated in its `all_unchanged` field; nothing wider is claimed.
- Writes: only this directory. Retrieved PDFs went to `/tmp` and are identified by hash in
  `evidence_manifest.json`.

## Findings addressed

- **R1.** Bshouty and Costa arXiv:1706.06934v1 read (§2, Lemma 4, §3.1 Theorem 1, §3.2 Theorem 2)
  and mapped coordinatewise onto R4, with one shared non-adaptive query set for the product class
  (`LITERATURE_MAPPING.md` §2). No error in the supervisor's mapping. **Decision:
  NO_JUSTIFIED_IMPLEMENTATION for this proposed study** (`DECISION.md`); draft withdrawn by
  `corrected/DRAFT_WITHDRAWAL_ERRATUM.md`. Akutsu 1999 read in part (Prop. 1 gives a further
  deterministic sufficient condition under chosen inputs); Akutsu 2003 **not accessed** (HTTP 403),
  unverified.
- **R2.** Erratum E3: the draft distribution is degree-stratified with equal weight per degree,
  P = 1/[4·C(n,j)·E_j]; uniform over distinct functions needs P(j) = C(n,j)·E_j/N(n,3). Hand check
  n = 2, k = 1: 1/4 and 1/8 against 1/6. No sampler.
- **R3.** Endpoint (iv) split into a preliminary per-q existence property and the full declared
  equation with α, β, Ȳ, F̄, identity intervention and |Q|·|D| denominators; codomain/closure made
  explicit; q0/q1 counterexample proved by hand and labelled as a supervisor-requested illustration;
  INVALID qualified to verified in-class oracles; R2 regime separates OBSERVED, CLASS-ENTAILED and
  UNDETERMINED values. Human and JSON contracts updated together (`CHANGELOG.md`).

## Unresolved limits

- Akutsu 2003 unverified. Akutsu 1999 Theorem 2 constants not recorded (damaged glyphs).
- Bshouty–Costa constants are not in the inspected text; no numerical query count at n ≤ 16 is
  inferred. Theorems after Theorem 3 and cited constructions were not inspected.
- Beckers–Halpern constructive abstraction remains uninspected (unchanged from the original run).
- Checks were document, hash and JSON checks plus hand arithmetic; no new test suite.

## Accounting

Charged before this closure: 1,360 s (760 executor + 600 supervisor). This closure: wall time
from a t0 recorded within seconds of the first command; the final `time_ledger.jsonl` entry gives
the total, with a conservative 60 s added for the pre-t0 command. Cap 1,200 s; optional work stop
at 1,020 s was not reached. Reserve for the next supervisor: 300 s. No borrowing.

## Files

`corrected/` (TARGET_CONTRACT.md, target_contract.json, EVALUATION_SPEC.md, ABSTRACTION_CONTRACT.md,
DRAFT_WITHDRAWAL_ERRATUM.md), LITERATURE_MAPPING.md, CHANGELOG.md, DECISION.md, NEXT_OPTIONS.md,
evidence_manifest.json, preservation_before.json, preservation_after.json, attempts.jsonl,
time_ledger.jsonl, HANDOFF.md.
