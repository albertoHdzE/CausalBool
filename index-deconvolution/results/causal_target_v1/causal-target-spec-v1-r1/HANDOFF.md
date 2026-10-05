# HANDOFF — `causal-target-spec-v1-r1`

**Status: ready for Codex review; not yet accepted.**

Executor: Claude Code, 2026-10-04. Supervisor: Codex. Phase: specification and identifiability
only. No encoder, learner, generator, benchmark, notebook execution, installation, commit, push,
publication or recurring task. The draft protocol was not executed or implemented. The only
scientific computation was `check_witnesses.py` over the four declared maps.

## Preflight and preservation

- `check_packet.py`: all 13 checks pass, with no packet or required-input mismatch and no
  notebook 19 / build_19 drift (`preservation_before.json`; HEAD `53c41d8f`, 202 status lines).
- `preservation_after.json` re-hashes the same 25 files, compares git status, and records the
  final machine checks: document presence, JSON validity, output hashes against
  `evidence_manifest.json`, the witness rerun and a packet recheck. Coverage is limited to those
  files plus git status; no wider historical preservation is claimed.
- Writes: only this directory.

## Result

**Decision: DRAFT_QUERY_RECOVERY**, gated on preconditions P1–P4 (`DECISION.md`). There is one
draft, `DRAFT_EXECUTION_PROTOCOL.md`, marked **NOT AUTHORIZED FOR EXECUTION**. If P1 (the
primary-source literature) finds prior art for the same class and access, the decision reverts to
NO_JUSTIFIED_IMPLEMENTATION.

## Findings, in order of consequence

1. **Q_LB audit** (`EXISTING_EVIDENCE.md` §2). The screen's formula counts padded
   (support, table) pairs with exactly k declared inputs, not distinct functions. The corpus has
   at most k declared inputs and a 12-family pool. A valid worst-case adaptive bound for C(n,k)
   is ⌈log2 Σ_{j≤k} C(n,j)·E_j⌉, with E = 2, 2, 10, 218. The padded count exceeds the distinct
   count by about 17% (0.23 bits) at n = 50, 100 and 200, and the ceiling gives the same integers
   (23, 26, 29). The numbers survive by rounding, not by the screen's argument. **"S2 headroom" is
   not established**: H1 compared a worst-case bound with per-instance stopping points of a
   random-sample, lenient, non-certifying learner, and no upper bound exists. The old 2·Q_LB
   threshold is marked unvalidated. The NARROW verdict itself is not changed.
2. **Access regimes and target** (`TARGET_CONTRACT.md`, `target_contract.json`). The four regimes
   are kept distinct. Three intervention semantics are kept distinct: reset-then-step, mechanism
   replacement (`reprogramming.knockout`) and clamp. Target T\* is exact functional recovery in
   C(n ≤ 16, 3) under chosen queries. Proved: for n > 2k, no set of fewer than 2^n queries
   certifies class membership, so identification is always relative to the class.
3. **Witnesses** (`IDENTIFIABILITY.md`). Declaration v2; v1 was corrected before any check and is
   retained. Checker run 1 failed 49/51, because the checker's first-pair convention in W4 did not
   match the declared pair; the declaration was right. Runs 2 and 3 pass 53/53. Two
   all-violating-pairs checks were added after run 1 and are labelled post hoc.
4. **Abstraction contract** (`ABSTRACTION_CONTRACT.md`). The fibre condition for a macro map is
   proved in both directions (W3). Intervention consistency is shown to require the fibre
   condition for every F_q, which W4 fails. Each of the user's five ideas has a stated evidential
   role. A codec dictionary is separated from a lossy α.
5. **Certifier** (`DECISION.md`, draft §3). An exact, cheap criterion: a node is IDENTIFIED iff
   every consistent support has all its projections observed and they give one canonical
   function.

## Not done or unavailable (first-class)

- Akutsu 1999 and 2003, and the exact k-junta membership-query literature: **not accessed**. Their
  guarantees and access regimes were neither transferred nor guessed.
- Beckers and Halpern: constructive abstraction **not inspected**. Rubenstein et al.: Sections 5–6
  not inspected. Moving their static-SEM definitions onto one-step maps is our construction.
- Abstraction validation is not drafted. It is missing a labelled state space, an α family and an
  intervention set Q (`DECISION.md`).
- Codebase-graph tools were not used; source was read with grep and sed (`evidence_manifest.json`).
- The class-uniform sampler that the draft needs does not exist (P3).

## Accounting

Wall time is measured from the first preflight command (`time_ledger.jsonl`). The executor
finished well inside the 3,000 s cap, and the final entry records the total. The 600 s Codex
reserve is untouched. No budget was borrowed. Failed attempts and superseded versions are retained
(`attempts.jsonl`, `witness_results_attempt1_failed.json`, `check_witnesses_run1_superseded.py`,
`witnesses_v1_superseded_precheck.json`).

## Files

EXISTING_EVIDENCE.md, TARGET_CONTRACT.md, target_contract.json, IDENTIFIABILITY.md,
witnesses.json, check_witnesses.py, witness_results.json, ABSTRACTION_CONTRACT.md,
EVALUATION_SPEC.md, DECISION.md, DRAFT_EXECUTION_PROTOCOL.md, evidence_manifest.json,
preservation_before.json, preservation_after.json, attempts.jsonl, time_ledger.jsonl, HANDOFF.md;
retained superseded artifacts are as listed above.
