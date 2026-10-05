# Claude Code: close the diagnosis review, without rerunning the study

The user delegates implementation to Claude; Codex supervises acceptance.
Read `results/hierarchy_search_diagnosis/supervision/search-diagnosis-v1-r1/REVIEW.md`
and its `closure_delegation_manifest.json` first. Paths here are relative to
`index-deconvolution/` unless specified otherwise.

The 416 D2, 176 D3 and 576 D4 jobs are complete and independently audited. Do not
resume or launch them. Close R1, R2 and R3, then stop with a handoff for Codex.
The accepted search-v2 verdict stays inconclusive. No search-v3, new wire codec,
new seeds, new confirmation, inference sweep or recurring check-in is authorized.

## Ownership and preservation

You are not alone in the working tree. Preserve other people's edits; never
reset, stash or restore them from HEAD. Own only a new closure directory
`results/hierarchy_search_diagnosis/review_closure/search-diagnosis-v1-r1/` and
temporary isolated copies. Do not edit active scientific owners, active diagnostic
adapters/tests, active notebook 18/builder/bitacora, or the original diagnosis run.
Deliver patches and corrected copies for review, with `git apply --check` results.
Leave the previously approved historical R1 median source patch unapplied.

Verify the delegation hashes before work. Keep the full diagnosis run, its original
reporting artifacts, both historical runs and the whole accepted search-v2 tree
byte-identical. Do not invoke an old reporting/verification command that writes
there. New closure records and ledgers stay in the new directory. Report any
unexpected collision instead of overwriting it.

## Required correction

1. **R1:** Correct impossibility/optimality claims and distinguish H = T from
   identical proposals. The supervisor found 21 unequal-byte cases among the
   282 losing H = T cases. Keep the exact arithmetic and measured proposal costs.
   Remove the claimed universal exact-repeat floor. Revise Draft B so any exact
   prediction applies only to a fully specified rewritten proposal, with full
   serialization accounting; it cannot predict the automatic full-method change
   merely from H = T. Do not implement TILE. Correct report, decision, handoff,
   draft and bitacora copies wherever affected. A cautious BOTH_SEPARATELY
   recommendation is permissible, but not mandated by this review.
2. **R2:** Label 129/252 as proximity to returned B0 cuts in the 68 selected
   strictly reachable witnesses. It is not coverage of all proposed cuts.
   Remove "never proposes", unsupported mechanism rankings and exclusive causal
   falsification claims. Qualify the one-output B0→B8 cap result. Revise Draft A's
   rationale/development criterion accordingly; no new telemetry jobs. Correct
   the scope statement about F06/F07/F11 D2 controls versus D3/D4 targets.
3. **R3:** Patch the reporting pipeline in a copy so missing D2 outputs, D3
   timeouts/errors and D4 unavailable translations yield explicit partial results
   with intended denominators rather than KeyErrors or zero gains. Exercise actual
   row-building → summaries → flags → decision with fixture/copied records; test
   invalid evidence separately from missing evidence. Include a negative/mutation
   check showing the new tests catch the old defect. Real retained jobs must never
   be deleted or altered for tests. Keep the successful complete-run values exact.

Do not broaden this into runner, codec or search refactoring. Do not assume a
graph-limited proposal proves inexpressibility. Keep output validation and the
resource/identity gates explicit. Make only reporting/test/presentation patches.

## Reporting identity and verification

Codex permits a1 to remain the identity of the completed computations. The current
post-launch report edits are a disclosed exception, not an unchanged-source claim.
Create a distinct immutable reporting revision (e.g. `report-r2`), recording all
reporting sources, tests, builder, protocol/review references and the exact hashes
of consumed a1 records. Retain an executable closure and reproducible command that
reads a1 and writes only the closure directory. Test in copies; no overwrite of
a1's `identity/reporting_revisions.json` or original tables/reports is authorized.

Run focused tests and lint, regenerate corrected reporting outputs from saved
records, compare all original successful-case numbers, and build/execute the
corrected notebook under the reviewed artifact-only guard from both working
directories. Save execution outputs separately. If a text mismatch recurs, retain
both exact outputs and investigate before selecting a passing run. No encoder,
generator or subprocess may run inside the notebook. No full owner-suite rerun
is needed when owners are unchanged. Keep existing guard failures disclosed.

Use remaining category budgets from the phase ledger plus the supervisor's
separate resource record; do not reset allowances. The original four-hour total
and 1,800/10,800/1,800-second category caps still apply. Charge closure work in
its own durable ledger and include it in cumulative totals. If a category runs
out, deliver the completed correction evidence and identify what remains; do
not silently move charges or run more experiments.

## Handoff

Write a closure HANDOFF with R1–R3 disposition, patch/source hashes, reporting
revision identity, numerical comparisons, tests and meaningful negative probes,
notebook checks, preservation before/after and cumulative resources. Keep the
original run and old claims available as historical artifacts, linked to the
corrected copies. State **ready for Codex review; not yet accepted**.

No commit, push, publication, scheduled loop or next-study launch. Stop after the
closure handoff. Implementation of a future algorithm needs its own reviewed
protocol after this acceptance decision.
