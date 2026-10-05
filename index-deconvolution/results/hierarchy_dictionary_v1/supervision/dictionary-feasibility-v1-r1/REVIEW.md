# Codex review — dictionary-feasibility-v1-r1

2026-10-04. **ACCEPTED as a completed negative exposed-data feasibility study.**
VALID_COMPLETE / NO_RETAINED_GAIN is supported. No blocking implementation fix,
benchmark rerun or production adoption is required. Preserve the original handoff;
this separate supervisory record resolves its pending acceptance status.

## Verification

The supervisor read the algorithm, independent audit, reporting gates,
preservation implementation, mutation evidence and notebook guard records.
`audit_review.py` performs read-only checks and writes only in this supervision
directory. Final `audit_review.json`: **23 checks pass, no problems**.

- Lock `19b53d32873a37cfd37e84129d880056ebf6132a6994c2f6e339f25142373780`
  matches. All 93 closure members match current files and snapshot contents;
  the snapshot hash matches. Scientific owners and old packages are unchanged.
- Independently compared all 96 A0 records against their hashed original rows
  and every specified deterministic field, removing only `wall_s` timing keys.
  All 288 composites retain A0's bytes and completed status.
- Reran the separately implemented archive audit after reading its source:
  26,364 archive reads, 12,332 decoder calls with a hash cache, 25,020 candidate
  archive checks, zero problems. These are reads/checks, not all distinct files.
  It reuses the independent owner decoder and launches no encoder. This is a
  rerun of the executor's independent audit, supplemented by supervisor code,
  not a newly implemented decoder.
- Supervisor code additionally checks retained mode-best byte lengths, absence
  of any shorter-than-A0 mode winner, all 6,096 evaluated/48 ineligible D2 views,
  the per-view P and R(O) win/tie/loss counts, four F10 distinct equal-length
  cases, and hop refusals recomputed from comparison arrays and donor hop depths.
- Hop refusals are **354,960 per relation mode**, or 709,920 comparison events
  across R(O) and R(P). The modes repeat the same relation comparisons; these
  are not that many independent cases or proven lost compression opportunities.
- All five prior result trees (96,587 files) match initial and final manifests.
  Protocols and bitacora match. The full current run tree is unchanged by review.
- Reviewed saved 59-test success and all eight mutation failures. Three mutations
  are caught by in-test semantic validation exceptions rather than assertion
  statements; they exercise the intended defects, not import/setup failures.
  Accept this as substantive fault detection, while retaining that distinction
  from the protocol's literal assertion wording.
- Reviewed both saved run3 notebook guard executions. Builder/driver hashes
  match; delivered notebook bytes equal the saved notebook-directory execution.
  The test suite and notebook were not re-executed by the supervisor.

## Preservation qualification and presentation revisions

The first supervisor audit flagged current notebook19 and build_19 bytes. Its
output is preserved as `audit_review_attempt1.json`. The study's recorded initial
and final hashes match each other and the packet. Current bytes differ in exactly
the two files explicitly allowlisted for external drift by INITIAL_STATE.json.
The final supervisor audit distinguishes historical preservation from current
allowlisted drift and records both hashes. No file was reverted. File hashes alone
do not identify the external editor or independently timestamp that edit.

The two post-lock notebook corrections affect presentation, with earlier
executions retained. They do not change locked measurements or calculations.
The aggregate dictionary-expansion hash plus per-entry expansion validation is
an acceptable representation of the required integrity evidence; individual
word hash fields were not emitted as originally phrased.

The known stale v3a test, nine pre-existing single-engine failures and scoped
ci-local exception remain disclosed. Acceptance does not mean repository-wide
CI passed. Do not edit frozen owner files to make those historical checks green.

## Accepted interpretation and limits

The new dictionary modes can shorten a particular view's original proposal,
but no mode beats k=1 on any study string. The positive pair_grammar and negative
portfolio comparisons are inherited A0 performance. Non-regression against A0
is a selection invariant, not evidence of scientific benefit.

Close this finite candidate search as specified and keep k=1. Do not increase
the donor window, flip limit or hop cap on these results without a new protocol.
However, HANDOFF section4's assertion that a future method *has to* change what
is paid is too strong. This study does not isolate the cause of the residual
cost gap or rule out gains from other selection policies, mixtures, caps or
representations. Whole-dictionary bundling, the local donor window, greedy
flip-count ranking and hop restrictions all limit its scope. Their effects were
not independently manipulated here. Nor does frequent hop rejection prove that
relaxing it would improve full archive length.

Read the overhead explanation as a hypothesis, not a causal finding. Same byte
composition in the illustrated F10 case supports the reported descriptive
comparison; matching rule-type totals alone is not a general equivalence proof.
These qualifications supersede stronger wording in the handoff, without changing
any numeric result or requiring edits to frozen evidence.

Before another encoder phase, prepare a bounded artifact-only synthesis: compare
the complete saved candidates to A0, identify what each proposed capability adds
beyond the incumbent, and draft at most one discriminating next experiment. A
finite negative feasibility result neither completes the causal method nor
refutes multilevel structure. Causal recovery and self-similarity need explicit
targets and separate evidence.

## Accounting

Charge a conservative 300 seconds of supervisor report/verification, including
both audit attempts, their investigation, review and next-step handoff, and the
executor's disclosed uncharged final one-line edit. Audit execution took about
14.68 + 13.79 seconds, included in that charge.

Executor recorded development 1,319.189150 s, benchmark 161.622834 s and reporting
429.742626 s. Reporting including supervisor: 729.742626 / 3,600 s; total
2,210.554610 / 21,600 s. Keep the original ledger unchanged. A subsequent phase
must record its own allowance and may not borrow these unused seconds.

Only this supervision directory was added by Codex. No study or implementation
files changed; no encoder jobs, commits, pushes, publication or schedules.
