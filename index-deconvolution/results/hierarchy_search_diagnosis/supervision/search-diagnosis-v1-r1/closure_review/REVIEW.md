# Codex closure review: report-r2

Date: 2026-10-03. Decision: **CHANGES REQUESTED. Do not apply either patch yet.**

R1 and R2 are closed for the corrected reporting artifacts. The original R3
KeyErrors are addressed, but two related evidence-accounting defects remain.
The retained computations remain usable; neither finding changes the actual
study estimates or the exploratory BOTH_SEPARATELY recommendation.

## R3a — P2: D4 job counts count conversions instead of jobs

In `report-r2/source/search_diagnosis/analysis.py`, `_evidence` computes `st4`
from every D4 row. Each job has two rows, one per translation. The delivered
`outputs/flags.json` therefore says intended D4 jobs = 576 but D4 job status
`ok` = 1,152. The resource summary correctly says 576 jobs.

A read-only in-memory probe removes one D4 job. The pipeline correctly returns
INCOMPLETE, but reports two missing jobs and 1,150 successful jobs. Correct counts
are one missing job and 575 successful jobs; two missing conversions and 1,150
successful conversions are correct and must remain distinct.

Count job status once per intended case, retaining conversion status separately.
Test the complete and missing-job pipelines, and assert that each status count
sums to its own intended denominator. Include invalid job statuses in this
accounting without double counting. This finding affects delivered report-r2
numbers, so the replacement must explicitly list these corrected numbers rather
than asserting that every report-r2 number is unchanged.

## R3b — P2: failed selected-B byte comparison does not invalidate evidence

`d2_rows` computes `B0_bytes_equal_saved_final`, but neither `_evidence` nor
`report.decision` gates on a false result. On an in-memory copy of
`confirmation-F12-1024-3000-base`'s B0 record, changing only
`archives.output.sha256` makes this comparison false, yet the decision remains
`valid: true`, `BOTH_SEPARATELY`. All deterministic telemetry comparisons remain
equal, so the existing mismatch test does not exercise this path.

Protocol §5 requires the retained selected-B bytes comparison and investigation
of deterministic disagreement before interpreting B8. Feed an explicit false
comparison into the invalid-evidence gate, with case identifiers. Do not treat
an absent comparison for an old final archive selected from another stage as a
failure. Test this failure alone and with missing evidence: INVALID must win and
neither recommendation signal may be evaluated. The actual retained B0 byte
comparisons pass; this is a failure-handling defect, not a newly failed study job.

## Checks completed

The adjacent `audit.py` and `audit.json` reproduce both findings without changing
retained records or executing any diagnostic job. The audit also independently:

- verifies report-r2 identity, source/reference hashes, closure tar hash and all
  1,950 consumed-file manifest entries;
- regenerates all nine reporting objects in memory and matches the saved outputs
  exactly;
- verifies the original a1 run's entire 8,152-file manifest is unchanged and the
  closure preservation record's named protected files still match;
- checks all ten retained executed notebooks: zero error outputs, zero unexecuted
  code cells, and identical output objects after joining adjacent stream messages
  with the same stream name. This preserves ordering and all non-stream output.

Both patches independently pass `git apply --check`. The executor's retained log
records 44 passing tests and the documented negative probes; these tests were
inspected, not rerun by Codex. No notebook kernel or full owner suite was rerun.
Protected tree-wide validation from the earlier audit and executor's preservation
record remains supporting evidence; this review does not claim a fresh full audit
of every historical archive.

The notebook discrepancy is accepted as an output-message segmentation difference:
the saved outputs establish semantic equality. The underlying flush mechanism
remains unproven and need not be asserted. Future checks should coalesce adjacent
same-name stream messages rather than select a run solely for message chunking.

## Budget and integration decision

The executor's reported 72.984045-second report_verification overrun is a real
protocol deviation, not erased by unused allowances in other categories. The
claim that only final accounting/handoff remained is recorded as the executor's
account, not independently certified by file timestamps. The overrun alone does
not alter already retained scientific measurements; it precludes claiming full
resource compliance. No allowance has been increased by this review.

This explicitly requested supervisor review adds a separate conservative 60-second
automated-check/tooling charge, using the prior supervisor accounting convention.
See `resource_accounting.json`; it is additional to, not a replacement for, the
earlier 120-second supervisor charge. Cumulative report_verification is now
1,932.984045 seconds against 1,800, and total charged use is 3,240.156246 seconds.
Original ledgers are untouched. The two remaining corrections must not start
without a prospective budget amendment. Proposed: increase this category's cap
by 600 seconds to 2,400, retain the 14,400-second overall ceiling, and retain all
historical overruns explicitly. This would leave 467.015955 seconds in the category,
including 60 seconds reserved for the next supervisor review. No other category
is debited, reset or enlarged.

Implementation remains delegated to Claude in
`index-deconvolution/KICKOFF_hierarchy_search_diagnosis_closure_followup.md`, a
bounded brief pending that amendment. Produce report-r3 separately, keep a1 and
report-r2 intact, and deliver replacement patches against the active files.
Neither active patch is approved for integration yet. No next algorithm study,
new diagnostic run, commit, push, publication or recurring task is authorized.

The search-v2 conclusion remains inconclusive. These diagnostics do not establish
a final causal deconvolution method; next-phase protocol design follows closure.
