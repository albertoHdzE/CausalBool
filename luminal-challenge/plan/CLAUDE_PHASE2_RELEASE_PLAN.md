# Phase 2 scientific release candidate — Claude Code execution plan

Version 1.0 · 2026-09-23 · Author/final reviewer: Codex for Alberto.
Implementer: Claude Code, manually invoked by the user.
Status: READY_FOR_EXECUTION; no experimental outcome is pre-approved.

## 1. Mission and authority

Deliver a complete, independently reviewable Phase 2 research release candidate:
reproduce repair validation, fix remaining implementation defects, execute the
frozen experiments, compare with accepted direct v4 and classical, and state
whether further optimization is warranted before a new manuscript. This task
is not satisfied by a plan, unit tests, a partial benchmark, a success banner,
or a rewritten paper. A rigorous negative result is an acceptable scientific
outcome. Favorable hypotheses are not a deliverable that can be guaranteed.

This user-requested transfer replaces Luna as implementer and replaces the
administrative instruction to await a separate pre-campaign launch approval.
Claude is authorized to complete the readiness audit below and then launch when
its objective requirements pass. This is not acceptance of the current code.
Codex retains final independent review. No routine confirmation is required.

The scientific policy remains the immutable recovery amendment and original
contract. This plan changes no algorithm, corpus, seed, gate, budget, estimator,
or protected compiler. Read in order:

1. `AGENTS.md`, `plan/INDEX_ONLY_PLAN.md`, `plan/STATUS.md`.
2. `plan/PHASE2_STRUCTURAL_ENCODING_PLAN.md`, `plan/phase2/IMPLEMENTATION_CONTRACT.md`
   and `plan/phase2/PROTOCOL.json`.
3. `plan/PHASE2_RECOVERY_AND_COMPARISON_PLAN.md` and
   `plan/phase2_recovery/AMENDMENT.json` (these override their specified original
   policy clauses only).
4. `results/phase2_structural_encoding/recovery_lead_review_20260923/REPAIR_REVIEW.md`
   (all seven findings) and the latest pre-campaign checkpoint named below.
5. This release plan and its locked delegation package.

Scientific conflicts are not implementation choices: retain evidence and report
the exact conflicting clauses. Never silently prefer the easier interpretation.

## 2. Verified starting point and limits of existing evidence

Start from the current working tree, not a clean checkout of HEAD. Research and
tests are untracked; resetting to HEAD would discard the implementation.

The stable checkpoint is
`results/phase2_structural_encoding/recovery_pre_campaign_20260923/`:
`REPAIRED_IMPLEMENTATION_MANIFEST.json`, `READY_FOR_PRECAMPAIGN_REVIEW.md`,
`VALIDATION.json`. Codex verified its 17 research/test file hashes and seven
amendment inputs at handoff preparation. Luna reports 269 full-suite tests and
26 recovery tests passing. Reproduce these with raw logs; a summary JSON is
not independent verification. More tests may be added; never delete tests to
retain a particular count.

The initial recovery campaign, `recovery_campaign_20260923`, was aborted for
implementation/evidence repairs. Its 1,800 P2 rows remain available and were
independently checked for membership and classical integer controls. They are
provisional evidence, not an accepted completed campaign. P5 raw rows were lost
before journaling existed. Do not reconstruct them from exit logs, describe that
P5 prefix as a result, or merge old rows into the new campaign. The original
`phase2_repair_20260923c` random-coverage verdict remains INCONCLUSIVE forever.
No accepted Phase 2 superiority result currently exists.

Original direct means accepted v4 repair2, not v3. Its public composite score
advantage over classical is not a Phase 2 result, compilation speedup, or a
causal estimate of representation alone. The production compiler stays frozen.

## 3. Ownership, provenance and process control

You own `research/`, `research_tests/`, and exclusively created new directories
under `results/phase2_structural_encoding/claude_release_*` plus fresh recovery
campaign directories. Do not edit paper, production, reference, `tests_direct/`,
historical results, any plan package, STATUS.md, or lead review artifacts.
Do not revert others' edits. Do not stash/reset/clean, change branches, merge,
commit, push, publish, or launch additional agents/services.

Use `results/phase2_structural_encoding/claude_release_20260923/` for your audit
and handoff. Refuse an existing path; if a prior attempt exists, preserve it and
use the next unused numeric suffix, explicitly linking the preceding attempt.
Capture HEAD, git status, full working diff, source hashes and copies of all
research/test Python sources before changes. Snapshot the final measured source
bytes as well as hashes; record Python executable/version, OS and dependencies.
Keep large evidence locally and intact; storage packaging is a separate task.

An earlier worker mistakenly terminated an unrelated Jupyter kernel. Do not
use kill, pkill, killall or numeric-PID signaling, and do not touch editor,
notebook or unrelated Python services. If cancellation is necessary, use only
the execution session/process handle you created for this exact campaign.
Preserve partial journals, document the reason, and establish that those owned
workers stopped before modifying measured source. If ownership or termination
cannot be established, report the blocker rather than guessing. Never weaken
sandbox permissions or service controls to work around a limit.

## 4. A — pre-campaign release gate

From `luminal-challenge`, use `../venv/bin/python` consistently. First run
`../venv/bin/python plan/claude_phase2_release/verify_package.py`; its initial
mode also verifies the starting implementation hashes. After authorized source
repairs, `--policy-only` skips that initial-state comparison while still
verifying immutable delegation, recovery and original policy inputs. Preserve
both initial and final implementation hashes; this flag does not accept drift
in protected code or experimental policy.

Review all seven lead findings against code and executable tests. Explicitly
verify:

- Fixture-keyed P4 identity through real subprocess workers, harness, commands,
  durable journals and checker, including informative and NOT_APPLICABLE cases.
- Mean of matched log quality ratios, not log of mean products. Pair repetitions,
  then seeds, then fixture variants and semantic programs as specified. Never
  drop failed/missing pairs and present the reduced denominator as complete.
  The fixed primary is held-out P5 structural_bound versus accepted_budgeted
  at 0.1 seconds. Public and secondary comparisons remain descriptive.
- Shared absolute deadlines across construction, cover building, decode,
  machine/case validation and hidden evaluation. Late discoveries/completions
  do not count; partial work is retained. Known defects outrank simultaneous
  expiry. Report oracle preprocessing separately, never give it to the learner.
- Exact original/amended coverage separation, diversity, counters, chronology,
  membership and stopping reasons recomputed from raw evidence.
- Every corruption case in recovery-plan section 8 and the lead review: false
  PASS, missing/duplicate/reordered rows, erased validations, forged identities,
  policy/import mismatches, classical omissions/budget duplication, missing
  journals, worker failure, wrong primary endpoint and forged statistics.
- Fsynced command/result journaling per worker and reconciliation after both
  normal execution and a controlled failed worker.
- P4's original balanced seeded arm order, paired inference and model gates.

Run and retain complete stdout/stderr, argv, cwd, selected environment, timestamps
and terminal exit codes for:

```
../venv/bin/python plan/phase2_recovery/verify_package.py
env PYTHONPATH=.reference:. ../venv/bin/python -m unittest discover -s research_tests -v
env PYTHONPATH=.reference:. ../venv/bin/python -m research.check_structural_evidence --architecture
```

The test suite includes small real worker integration checks. These prevent
another immediate pipeline crash; they are not comparative scientific evidence
and never replace the full campaign. If tests fail, add a regression, repair the
demonstrated defect within scope, and rerun affected checks plus the complete
research suite before measuring. Do not change codec/search policy or expected
answers to obtain a pass. Fill `READINESS_MATRIX.md` with each finding, relevant
code/test, exact log/exit and disposition. All implementation findings must be
closed before launch. Freeze final source only after this gate passes.

## 5. B — execute the real scientific campaign

Use a new `recovery_campaign_20260923_r2` directory; if it exists, never overwrite
or append a second attempt into it. Select the next suffix and document why.
No source edits or competing benchmarks during timing. Maintain a recoverable
progress record with current stage, completed/expected durable measurements,
last successful command, source digest and exact resume procedure.

```
env PYTHONPATH=.reference:. ../venv/bin/python -m research.run_structural_experiments \
  --stage all --run-id recovery_campaign_20260923_r2 --contract plan/phase2 \
  --amendment plan/phase2_recovery/AMENDMENT.json
env PYTHONPATH=.reference:. ../venv/bin/python -m research.check_structural_evidence \
  --run results/phase2_structural_encoding/recovery_campaign_20260923_r2 \
  --contract plan/phase2 --amendment plan/phase2_recovery/AMENDMENT.json
```

Every later occurrence of the run ID must use the actual selected suffix.
Do not override gates, restart for favorable timings, reduce repetitions, extend
budgets, remove hard programs, pick better seeds, or tune on held-out outcomes.
If a runtime defect requires source repair, preserve the failed attempt and
rerun affected evidence in a fresh self-contained campaign. Do not combine
measurements from different implementations into one result.

Required matrix (independent stage gates still apply):

| Component | Required evidence |
|---|---|
| P0/P1 | All 12 fixtures, original 16 random streams and exact supplemental physical-coordinate protocol on all eight public programs; independent replay and separate coverage verdicts |
| P2 | Four-codec representation diagnostics and tiny-domain oracle/bound checks; 1,800 fresh-process public measurement rows |
| P3 | All declared fixtures/codecs and 100 controls; complete structure evidence and original triage gate |
| P4 when authorized | Four model policies; 12 fixtures × 3 budgets × 15 repetitions × (3 deterministic null-seed policies + 10 uniform-bit seeds) = 7,020 worker rows, including explicitly uninformative outcomes |
| P5 non-model | Eight public + 100 held-out programs, three optimization budgets, 15 repetitions: 24,300 worker rows |
| P5 model when H4 authorizes | Additional 4,860 rows; otherwise absent with a recomputed scientific reason |

No model gate miss blocks an otherwise authorized non-model P5 comparison.
Keep scientific null/triage outcomes distinct from correctness or evidence
failures. Record every nonzero exit and its actual cause; do not relabel a gate
or bypass a checker to obtain exit 0. If a genuine scientific prerequisite
remains unmet, finish independent authorized work and return the precise
limitation. Never advertise the blocked experiment as completed.

Also run unchanged production controls, serially and into new output locations:

```
../venv/bin/python export_direct.py
../venv/bin/python verify_direct.py --stage all --output NEW_AUDIT_DIR/production_verification
../venv/bin/python compare_direct.py --repeats 3 --timeout 20 --output NEW_AUDIT_DIR/production_comparison
```

Replace NEW_AUDIT_DIR with your actual exclusively created audit directory.
The official comparator validates production controls; it does not itself
compare Phase 2. Protect all original/reference hashes before and after work.

## 6. C — comparisons and independent numerical cross-check

Keep the candidate fixed at structural_bound. Report all three budgets against
accepted_budgeted, accepted_default, accepted_bootstrap and classical, separately
for public and held-out cohorts: 24 descriptive matrix entries. Designate only
the frozen held-out primary as confirmatory H2. Apply the original H4 multiplicity
rule; do not promote whichever structural arm or budget happens to win.

Report C, S, J=C*S, program-level wins/ties/losses, paired quality effect and
interval, compile/process cost and intervals, peak RSS, failures/timeouts,
budget overshoot, and denominators. Reuse unbudgeted controls analytically by
program/repetition, not as fabricated additional observations. Resample programs
within family with equal family weighting; technical repetitions are not
independent programs. Positive paired log(control J/candidate J) favors the
candidate. Runtime candidate/control above one means slower. Explain signs.

As an additional independent check, run the lead's immutable raw-row auditor
after measurements have stopped:

```
../venv/bin/python results/phase2_structural_encoding/recovery_lead_review_20260923/independent_compare.py \
  results/phase2_structural_encoding/recovery_campaign_20260923_r2 \
  NEW_AUDIT_DIR/INDEPENDENT_COMPARISON.json
```

It imports no research implementation. Compare its estimates, intervals,
membership and program-level classifications with COMPARISON.json. Preserve
differences, investigate them, and never edit the lead auditor to force agreement.
If the scientific gates prevent a full P5, report why this full-P5 audit cannot
run; do not feed it synthetic or incomplete data. This numerical cross-check is
necessary where applicable but does not replace Codex's final review.

## 7. D — optimization and manuscript decision, without moving the target

Write `OPTIMIZATION_DECISION.md` answering separately:

1. Is the implementation correct within the established test/domain scope?
2. Did the fixed Phase 2 candidate improve output quality versus original direct?
3. How did it compare with classical in output quality and compilation cost?
4. What evidence supports H3 and H4, and what remains unmeasured?
5. Are remaining shortcomings correctness defects, measured engineering costs,
   unsupported hypotheses, or insufficient evidence?

Fix correctness/integrity defects before delivery. Do not undertake open-ended
performance tuning in this release. If optimization is warranted, provide a
ranked proposal tied to measured costs, with files/algorithm affected, invariant
to preserve, falsifiable expected effect, ablation, and a fresh evaluation policy.
Any tuning using these held-out outcomes makes them development evidence for
the tuned version; a later confirmatory claim needs a separately specified fresh
hold-out. Do not reuse the same cohort under a false claim of independence.

Write `PAPER_READINESS.md` with a claim-to-evidence table, supported claims,
unsupported claims, limitations and open blockers. A completed null comparison
can support an honest bounded paper; it does not establish superiority. No
manuscript overwrite, new-challenge experiment or production integration belongs
to this assignment. Codex reviews the release first and decides the next phase.

## 8. Release handoff and acceptance

Deliver `RELEASE_HANDOFF.md` in your audit directory, status
`READY_FOR_CODEX_REVIEW` or `INCOMPLETE_WITH_EVIDENCE`. It must identify:

- Starting and final source manifests, all changed files and reasons.
- Readiness matrix, full test logs/exit codes, worker/journal mutation evidence.
- Exact campaign directory, command history, raw artifacts, stage/hypothesis
  verdicts, checker report/exit, interrupted or omitted work and explanations.
- Production verification/comparison logs and protected-file hash verification.
- COMPARISON.json/.md, independent audit and an explicit agreement/difference report.
- Optimization decision, manuscript readiness and all limitations.
- Process/session ownership and exact resume instructions if interrupted.

The final message must answer: what works; better/worse on which metric and
population; what did not run; remaining defects; optimization needed or not;
paper readiness subject to Codex review. No self-acceptance, novelty proof,
global optimality claim, or guaranteed favorable conclusion.

Codex will independently inspect the seven repairs, rerun relevant checks,
recompute statistics from raw rows, check corpus/process membership and baseline
integrity, and adjudicate the release. Preserve everything required for that
review. If no genuine blocker remains, complete the assignment without asking
the user to approve routine implementation or experiment steps.
