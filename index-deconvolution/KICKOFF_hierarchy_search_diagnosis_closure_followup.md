# Claude: finish the diagnosis reporting closure

Status: **prepared for delegation; execution pending user approval of the budget
amendment below**. Do not start another correction on an exhausted allowance.

Read `results/hierarchy_search_diagnosis/supervision/search-diagnosis-v1-r1/closure_review/REVIEW.md`,
its `audit.json`, `resource_accounting.json` and `delegation_manifest.json` first.
Paths are relative to `index-deconvolution/` unless explicitly repository-relative.
Codex reviews; Claude implements. You are not alone in the tree: preserve others'
edits, and do not reset, stash or restore them.

## Scope and ownership

Own only a new
`results/hierarchy_search_diagnosis/review_closure/search-diagnosis-v1-r1-followup/`
directory and temporary working copies. Preserve a1 and the whole first closure,
including report-r2, its outputs, source identity, executable tar and ledgers.
Verify delegation hashes and preservation before work. Leave active adapters,
tests, builders, notebooks, bitacora and scientific owners untouched. The approved
historical median repair stays unapplied. Deliver replacement patches against
the current active tree, not patches assuming report-r2 was applied.

Fix only R3a and R3b from the new review:

1. D4 evidence job counts must count each case once; conversion counts remain
   per method. Complete: 576 successful jobs / 1,152 successful conversions.
   One missing job: 575 successful + one missing job, 1,150 successful + two
   missing conversions. Keep intended denominators, including invalid cases.
2. A false selected-B archive-byte comparison must produce INVALID with case IDs,
   ahead of INCOMPLETE, without evaluating recommendation signals. Missing/not
   applicable comparisons for a final archive selected from another stage must
   not be confused with an explicit false comparison.

Exercise the actual record-to-decision pipeline in memory with retained-record
copies. Add regression tests for both defects and invalid-plus-missing precedence;
show they fail on report-r2. No retained job may be edited for a fixture. Existing
44 tests must continue to pass. Do not refactor job runners, encoders or searches.

## Revision and verification

Create immutable report-r3 with sources/tests/builder/runner and consumed-file
hashes, plus a reproducible command reading a1 and writing only this new closure.
Keep job kernels byte-identical. Compare r3 with r2: explicitly enumerate intended
job-count corrections and new gate fields; all actual D1-D4 measurement values,
261/21 byte split, returned-cut proximity and BOTH_SEPARATELY must remain unchanged.
Keep the accepted R1/R2 language; no fresh scientific interpretation is needed.

Run focused tests and lint once, patch apply checks in copies, and the corrected
artifact-only notebook once from each working directory under the reviewed guard.
Compare outputs by coalescing adjacent stream messages of the same name while
retaining order and non-stream outputs; keep raw notebooks. Do not repeat notebook
runs merely to obtain matching message boundaries. Preserve existing guard/CI
exceptions; no full owner suite or unchanged repository guard rerun is required.
Capture preservation and patch/revision hashes. Deliver corrected copies and a
handoff stating ready for Codex review; not yet accepted. Stop at that handoff.

## Budget amendment proposed, not yet approved

Only after explicit user approval: increase report_verification from 1,800 to
2,400 seconds (+600), retain overall 14,400 seconds and all other category caps.
Do not erase the original 72.984045-second overrun or the new supervisor charge.
Starting cumulative report use: 1,932.984045 seconds; remaining under the proposed
cap: 467.015955. Reserve 60 seconds for the next supervisor review, leaving at most
407.015955 for this closure's reporting/verification. Fixture/development remaining
is 575.092429 seconds. Ledger all actual work under the appropriate category;
include documentation and final handoff time in the plan. Do not move charges
between categories to avoid a limit. Stop early enough to finish the handoff
within the allowance; if unfinished, report what remains.

No D2-D4 job launch/resume, new seeds, telemetry campaign, search-v3, TILE, commit,
push, publication, active integration or recurring check-in is authorized.
