# Claude Code corrective assignment: confirm-v1 supervisor review

Work in `/Users/alberto/Documents/projects/CausalBool`.
Read `index-deconvolution/bitacora/35_hierarchy_v1_supervisor_review.md` completely,
then the original protocol and normative annexes. This assignment is a bounded
correctness/reproducibility revision of HID-v1, supervised by Codex.

## Objective and non-negotiable scope

Resolve R1-R5, preserve all original evidence, and return a new reviewable handoff.
The negative primary result is acceptable. Do not change candidate sources,
SearchConfig values, scoring, wire bytes, corpus distributions, seed schedule,
baselines or statistical estimands to obtain better performance. Do not use the
supervisor's metadata-assisted witness as an inference input or tuning target.
No new statistical leaf, entropy coding, segmentation algorithm or research sweep.

Existing unrelated changes belong to the user: do not revert or stage them. Make
no commit, push, deletion of historical evidence or change to the original protocol.
Use graph discovery tools if available, otherwise explicit file reads. Keep the
single shared description-length owner and existing exact-deconvolution engine.

## A. Preserve provenance before editing

1. Verify the original freeze and supervisor audit. Snapshot all files enumerated
   by `confirm-v1/freeze.json` source/protocol/documentation mappings, plus the
   freeze itself, in a non-importable source archive with relative paths and a
   SHA-256 manifest under `results/hierarchy_v1_supervision/confirm-v1/`. Verify
   its contents against the original hashes. Do not archive credentials or the
   whole working tree. The snapshot is evidence, not another active engine.
2. Leave every existing file under `results/hierarchy_v1/confirm-v1/` unchanged.
   Preserve the original HANDOFF as a historical copy before revising active prose.
3. Record the correctness amendment and old/new run relationship in a new file.
   The original protocol §7 requires a **new run ID and freeze** after a correctness
   fix. Use `confirm-v1-r1` if absent; if occupied, inspect and use the next unused
   `confirm-v1-rN`. Never overwrite a prior freeze or pretend the old run passes
   the revised source hash. Mark the old run superseded/invalidated for approval
   of the corrected implementation in the external amendment record, while
   explicitly retaining the independently reproduced original observations.

## B. Implement the corrections

### R1: explicit study validation and verdict gates

Create one reusable validation path used by report and verify. It must construct
expected keys from the declared split design, never infer the population from
present rows. Preserve independently usable aggregation helpers for small unit
test fixtures, with an explicit fixture design; do not weaken production checks
to retain tests that previously blessed incomplete populations.

Reject duplicate keys, unknown cases/methods, wrong metadata, unexpected lengths,
and inconsistent row/corpus/freeze/config identities. Identify every absent
case/method and pair. Require archives, hashes, measured byte lengths and successful
decodes for all statuses that promise a deployed archive. For `baseline_best`,
check valid constituent statuses and equality to the selected constituent bytes/
hash/codec, with deterministic selection and minimum-size checks.

Scientific decisions must first pass the applicable validity/completeness gate:
invalid or incomplete evidence cannot produce a supported primary or component
claim. Censored primary baselines force `inconclusive` even when available rows
give a negative interval. Keep invalidity, incompleteness and inconclusive science
as separate fields/exit states. Any diagnostic aggregate from available cases must
be explicitly partial and cannot stand in for the prespecified endpoint.
Do not remove a case, substitute a raw baseline as uncensored, or silently overwrite
a duplicate. A complete valid negative study remains engineering-successful.

Regression tests must include: one F04 pair out of the required design; a missing
whole unit, whole cell, whole method and one ragged member; duplicate keys; negative
CI plus censored baseline; positive/negative CI plus invalid engineering; null
archive on an `ok` row; wrong archive hash/length/input; wrong portfolio identity
despite equal size; full valid negative study; correct exit states. Tests should
exercise report/verify integration, not only a helper's return string. Use tiny
explicit fixture designs and temporary directories to keep tests fast.

### R2: semantic failures cannot become successful results

Raise a clear exception on candidate expansion mismatch in `_Search.consider`.
Carry it as an error through the worker/runner; do not turn it into `ok`, timeout,
raw fallback, or a merely rejected candidate. Legitimate candidate-cap, depth,
language-arm, and resource exclusions keep their intended behavior. Add fault
injection at search and worker-result integration levels. The existing diagnostic
shows zero such mismatches in the retained original rows.

### R3-R4: correct claims and disclose development scope

Rewrite C5 to name the actual equal-weight aggregate portfolio endpoint. Keep
per-family statistical-code comparisons descriptive if presented. C4 must say
whether a positive portfolio saving is seen at larger sizes, with descriptive
scope. State that 65,536-bit development_resource probes informed cap selection,
outside the nominal development grid; larger reserved inputs are not uniformly
unseen lengths. Preserve the genuine held-out seed/family distinctions.

Separate wire overhead, proposal coverage, caps and search quality. Remove the
assertion that losses are all language limitations. Clearly label the supervisor
witness post hoc, metadata-assisted and outside the benchmark. Any future change
to the wire language needs a new version/specification. Synchronize active
SEARCH_SPEC, new handoff, new bitacora and notebook16/builder so claims match the
new report. Preserve bitacora34 as historical with any correction supplied in a
new note, not rewritten old numerical evidence. Add the missing all-12-family
aggregate as explicitly descriptive, separately from the primary population;
document its reporting seed and do not change the primary/ablation bootstrap.

### R5: environment enforcement

Before writing benchmark/resume/diagnostic results, validate relevant frozen
Python, numpy/pybdm and compressor-version/fingerprint fields, with explicit
actionable mismatch messages. Compare only actual scientific dependencies;
hardware/plotting/test metadata may be informational. Missing required fingerprints
must not silently match. Offline archive verification must report its environment
and must not rewrite the encoding provenance. Use mocks to test mismatches; do
not change the installed environment just to exercise a guard.

## C. Validate, freeze, and replay

1. Run the original 285 tests plus new regression tests, appropriate root analysis
   checks and lint. Preserve original owner semantics. Record actual commands and
   exit codes; distinguish the documented pre-existing worktree governance issue.
2. Demonstrate that untouched complete-data endpoint arithmetic still reproduces
   the supervisor audit to 1e-12. New validity gates must not change those estimates.
3. Freeze the corrected source under the new ID before starting its benchmark.
   Rerun the full affected confirmation and transfer benchmark under the original
   resource policy, preserving all 1,632 strings and 26,112 rows. This is a
   **correctness replay using the same predefined corpus**, not an independent
   replication or newly pristine holdout. Regenerate diagnostics/reports for that
   freeze. Never copy old rows and just replace their freeze/run ID.
4. Compare old/new archive hashes, sizes, selections, deterministic search fields,
   and endpoint values for every matching case/method. Expected: identical archives
   and endpoints; runtime/RSS may differ. If they differ, investigate and document
   the exact cause. Do not tune, cherry-pick or conceal differences. Unexpected
   changes in scientific behavior require supervisor review before any new claim.
5. Run complete verification and execute notebook16 against the new artifacts.
   Keep the original confirmation/transfer evidence readable via the archived
   original sources. Do not claim current-tree freeze validation for the old run.
6. Retain the six-hour run budget and resumability. If the budget or a genuine
   blocker prevents completion, preserve partial evidence with an incomplete
   status; never relax the grid, guards or resource limits to obtain a passing label.

## D. Required return package

Write `index-deconvolution/hierarchy/HANDOFF_CORRECTIONS.md` containing:

- old/new run IDs and freeze hashes, source snapshot path/hash and exact amendment;
- R1-R5 checklist with changed files, regression tests and evidence links;
- complete case/method/archive audit and old/new equality comparison;
- primary and five ablation estimates/intervals, transfer and controls with accurate
  scope, and corrected claim ledger;
- environment verification, exact commands, check exit codes and remaining issues;
- confirmation that no scientific tuning or new use of generator metadata occurred;
- a clear engineering status and scientific verdict, independently of sign.

Finish by returning only the new handoff path, run ID and concise unresolved issues.
Codex will review the actual results before accepting this revision. Do not call
the study accepted merely because the numerical result is negative or tests pass.
