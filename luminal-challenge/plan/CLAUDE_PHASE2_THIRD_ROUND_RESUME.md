# Complete the third round: accounting and audit repair, then conditional D/C

Version 1.0 · 2026-09-25 · Lead: Codex · Implementer: Claude Code.
**READY_FOR_EXECUTION — NOT DISPATCHED.** This continues the third round.

## 1. Authority and decision

Read AGENTS.md, INDEX_ONLY_PLAN.md, STATUS, the glossary, pinned semantics,
CLAUDE_PHASE2_THIRD_ROUND.md v1.0 and its locked protocol, the worker's third-round
handoff, and the new lead review:
`results/phase2_structural_encoding/lead_third_round_review_20260925/REVIEW.md`.

The lead reproduces 26 passing tests, exact baseline/shared replay on 30 programs
and 829,993 captured events, and the disclosed cost-scope error. The registered
0.8268222321783514 prediction is retained but cannot substantiate rejection of
the mechanism. Scope-matched arithmetic yields 0.7638230784259178 using the old
adapter estimate. That estimate does not implement the slot write it claims,
and four evidence mutations still pass the auditor. **CHANGES_REQUIRED.**

The lead explicitly permits a **post-hoc development accounting correction**.
It is not a change to the <=0.80 target, 1.5× sensitivity, development selection,
fresh-cohort confirmation or statistical family. No C1 or fresh outcome has been
observed. Keep that distinction and disclose the correction in the final paper
handoff. No fourth round, alternative kernel or new learning experiment is allowed.

Run `../venv/bin/python plan/phase2_third_round_resume/verify_package.py` first.
The parent plan applies in full except the precise repair/continuation rules here.
No routine lead permission is needed after the locally verified repair gate.
Only independent lead review can accept the completed research release.

## 2. Ownership and preservation

Own only new `research/third_round_resume_*.py`,
`research/third_round_candidate.py`, `research_tests/test_third_round_resume_*.py`,
`research_tests/test_third_round_candidate*.py`, and a fresh
`results/phase2_structural_encoding/third_round_20260925_resume[_N]/` directory.
Shared workspace: do not revert others' edits. Preserve the complete original
third-round run, its sources/tests, both old verdicts and the lead review.
No edits to existing modules, protocols, production, references or manuscript.
No subagents, commits, pushes, process termination or publication.

Import accepted R0 unchanged. Reuse the nominated BS1 class bodies unchanged from
`research/third_round_kernel.py`, measured hash
`77c373e1d4e6a328c70c590d46ffdf5b5a82ec8ccd38f82de246821f2da5ff85`.
If necessary, an explicitly versioned integration wrapper can import them.
The candidate may derive from R0 with a retained parent snapshot and minimal diff.
A kernel correctness defect requires a new version under the owned resume prefix,
an explicit minimal correction within BS1, repeated parity and a stopped affected
gate; it is not permission for performance retuning or a new mechanism.

Use the original 210 M0 rows and 180 M2 rows as linked historical development
evidence, with full identity/membership checks. Do not rerun those matrices to
replace unfavorable timing. New measurements below append evidence in the new run.
All process time from both runs counts toward the original 24-hour measurement
cap; all active development counts toward the original 16-hour cap. Preserve the
old ledger and build an aggregate ledger without double-counting linked rows.

## 3. Repair A: matching costs and measuring the adapter

The one approved corrected O is:

    min(baseline replay median,
        exclusive timer seconds for the matched scope / timer inflation)

The exact matched scope is the old eight components (`tfix_shell`, `tfix_copy`,
`precedence`, `issue_capacity`, `bounds_live`, `bounds_product`, `address_support`,
`child_domain_copy`) plus `certificates`, `propagation_setup`, `address_pairs`.
Keep all 30 programs and equal family weights. Replay-only O remains a sensitivity
diagnostic, never an alternative selected by its favorable outcome.

Retain corrected arithmetic on the old N as a diagnostic, then measure the missing
integration cost before granting M eligibility. Write `ADAPTER_SPEC.json` first:
show the minimal real node/query adapter operations and counts needed by C1,
which are already included in the timed shared replay, and which are additional.
At minimum exercise the actual extra state-reference reads/writes and dispatch,
and their release. Include branch/sibling/resume and epoch disposal where those
add work. The old read-only `_adapter(holder)` is not a slot-write benchmark.
Do not count replay-only dictionary bookkeeping as compiler work without explaining
the correspondence. Do not use future last-use knowledge to make the real compiler
adapter cheaper. Keep the kernel and search decisions unchanged.

A minimal adapter skeleton is allowed before compiler integration; it may not run
a new search or tune BS1. Freeze its exact source, invocation sequence and expected
keys before measuring one implementation on each original diagnostic workload:
30 programs × three fresh processes = **90 adapter rows**, stage `R_adapter`.
Use the parent's deterministic key/seed function with this new stage ID,
`arm_id=adapter`, `mode_key=adapter`, and repetitions 0–2. Keep all programs;
measure complete adapter work and cold construction/disposal on a real clock.
Timeout remains 20 s. Retain raw stdout/stderr/command/exit and failures. No timing
worker runs alongside tests, replay checks, profilers or other measurement work.

For each program define:

    N = original shared-kernel replay median
        + max(original adapter-estimate median, repaired adapter median)
        + explicit upper estimate of additional unmeasured integration work

The last term is nonnegative, with itemized evidence. Zero requires a documented
complete accounting of the actual proposed adapter. Do not subtract overhead
merely because a new estimate is smaller. Retain `O <= T0`, positivity and the
cost-ownership checks; avoid double subtraction of old work. Use the unchanged
`T0 - O + N` and conservative `T0 - O + 1.5*N` formulas and equal-family log means.

Eligibility requires corrected conservative ratio <=0.80, complete adapter rows,
kernel parity and a defensible overhead model. Otherwise stop with a supported
`NO_JUSTIFIED_MECHANISM` or `INCOMPLETE_WITH_EVIDENCE`, as appropriate. No alternative
formula, mechanism, overhead constant or second adapter selection after outcomes.
Any adapter failure/defect invalidates the calibration and stops for review; do
not rerun until favorable. A passing prediction remains a development forecast.

## 4. Repair B: enforce evidence prerequisites

Implement new checker/auditor modules under the resume prefix. Run the lead's
exact probes against the old auditor and demonstrate rejection by the successor:
extra torn final row, zeroed measured kernel hash, false M0 instrumentation parity,
and missing NOT_RUN file. Never patch the old auditor or hide its PASS outputs.

Required coverage for the reused and new evidence:

- Strict JSONL parsing of every line, including final fragments and blank/malformed
  lines; require complete dict rows and finite numerical values. A complete stage
  cannot silently ignore extra torn material. Preserve partial attempts on failure.
- Expected program/family/arm/mode/repetition membership derived independently from
  protocol and generator, not solely from a provided expected-key file. Reconcile
  keys, attempts, exits/timeouts, raw payload hashes and charge ledgers. No dropping
  failed rows, duplicate/replaced keys, hidden retries or success-only denominators.
- Compare all declared measured source bytes against their frozen hashes and
  verify transitive dependencies. Check the mechanism spec, workload manifest,
  serialized workload bytes and captured result fingerprints.
- Enforce M0 plain/timer/trace decision fingerprints, instrumentation parity,
  replay fidelity, and M2 output/certificate parity. Check both output and emission
  sequence lengths against the captured event count, stream length and digest.
  Recompute joint prerequisite flags rather than trusting booleans in a report.
- Reconcile explicit stage state in NOT_RUN, mechanism/development decisions and
  actual stage directories. Missing stage-state files, contradictory labels or
  launched dependent rows under a failing gate must fail. Required stage lists
  come from protocol, never just from report-supplied dictionary keys.
- Independently recompute original/corrected M arithmetic, per-program values,
  both aggregates, family values, overhead terms, speedup median/range and the
  revised gate. Use a field-to-check map for all claims in successor reports;
  explicitly declare unchecked metadata. Do not reuse reporter estimators.

After C1 qualifies, extend these checks to the parent D/C requirements, both
confidence endpoints, joint verdict, public denominators, exact work parity and
standalone exports. Complete the parent's synthetic positive/negative/incomplete
dry runs and mutations before each timing freeze. New timing freezes must include
all measured sources and the report/checker/auditor, with zero silent re-hashing.

### Narrow provenance dispositions

The old common-module edit is admissible only for this exact hash pair:

- measured `bd3a7b48d7d9535dea20fe5a8a70a17b993c292a476f67838981acb868d72f6d`;
- current `3a0e4163eb450adc08d2860d68a28ca9c7fdb0d67bf77a82c0f27f0b77542632`.

Restoring `Callable, Iterable, List` to the one typing import reproduces the old
bytes exactly. Preserve both versions and diff; no other source drift is waived.
Use a clean frozen successor source set for new measurement, not a blanket allowlist.

The spec-era kernel hash is the measured file's first 17,377 bytes; the added
suffix is the replay driver. Retain both versions and the spec-before-code
deviation. Do not claim the chronology met the original rule. This remains
exploratory development. No favorable fresh confirmation was observed.

The lead reconstructed 390 worker stdout payloads matching all recorded stdout
hashes. Preserve this recovery as such; it is not an original raw-log archive.
Missing historical full stderr cannot be reconstructed from a tail. Record that
limitation, and retain complete raw streams for all new processes.

## 5. Repair C, continuation and exit

Create new corrected reports; do not rewrite the old handoff. The median kernel
speedup defined by baseline replay median / shared replay median is
**2.3649168298633314**, not 2.3947613512067907. Preserve the original range and
explain the reporting correction. Do not call this a compiler speedup.

Write `REPAIR_CLOSURE.json` covering every lead finding, exact mutations, source
dispositions and the original/corrected/recalibrated predictions. Only if the
successor audit passes and the repaired M gate qualifies may you proceed to
**the original Stage D**, integrating BS1 as the sole C1 candidate. All original
semantic tests, exact decisions/certificates, development freeze and 600/600/60
matrices apply. No restart of M to choose another representation.

Only D qualification permits the original Stage C. Recheck the untouched
980000–980199 reservation, including compilation-input duplicates excluding names
and cases, before use. Keep the original 284 acceptance, 2,000 fixed-work,
6,000 wall, 280 public and 1,248 export rows; all original budgets, seeds,
97.5% intervals and <=0.80 / <=1.01 joint target are unchanged. A later source
defect/failure triggers the original stop rules, not performance retuning.

Always deliver a new PAPER_HANDOFF.md distinguishing original registered failure,
post-hoc accounting repair, kernel-only evidence and conditional real compiler
results. Preserve earlier practical failures and learner limitations. After lead
review, paper revision remains the next planned activity regardless of success.
Do not edit the manuscript in this assignment.

Return RELEASE_HANDOFF.md with its exact path, all stage statuses/counts, full
validation commands/exits and deviations, marked READY_FOR_CODEX_REVIEW or
INCOMPLETE_WITH_EVIDENCE. A properly evidenced stop is a valid completion.
