# Codex acceptance: search-diagnosis-v1-r1 / report-r3

Decision: **ACCEPTED. R1, R2, R3, R3a and R3b are closed.**

The accepted computation record remains attempt a1,
`518ebc137118643bf564c76f8e597c15565a95411fe9a946a539cc05e7044a9e`.
The accepted reporting revision is report-r3,
`7b1590bb4a63dd0f4c6eec5fb46f7f335d1b75b8450e5bfb3769086067f21066`.
Its reporting source identity does not replace the computation identity.

This acceptance comprises the report-r3 sources, outputs, tests and guarded
notebook in `review_closure/search-diagnosis-v1-r1-followup/`, together with the
R1/R2 interpretation corrections in the first closure's `corrected/` directory.
Those prose copies retain their historical report-r2 label; read them with this
supersession record and report-r3's corrected evidence counts. Original a1 and
report-r2 records remain preserved, not retroactively rewritten.

## Independent verification

The adjacent `audit.py` and `audit.json` establish:

- report-r3 source/reference identity, closure tar and all 1,950 consumed-file
  manifest entries match;
- all nine reporting objects regenerated in memory match the saved report-r3
  outputs exactly;
- D4 has 576 successful jobs and 1,152 successful conversions; removing one
  job in memory yields one missing job, two missing conversions and INCOMPLETE;
- an explicitly false selected-B archive-byte comparison yields INVALID,
  `valid: false`, and the affected case in the new gate;
- relative to report-r2, the only changed existing value is D4's successful job
  count, 1,152 to 576; the only additions are the two empty mismatch lists;
- the original run's 8,152-file manifest, the entire first closure and all 20
  delegation hashes remain unchanged;
- the named protected files match, and the five job package modules remain
  byte-identical to report-r2 and the active tree;
- both saved notebook executions have zero errors and unexecuted code cells,
  and equal output objects after adjacent same-name stream coalescing.

Codex independently ran the focused suite: **51 passed in 8.56 seconds**. These
include invalid-plus-missing precedence, unevaluated recommendation signals,
invalid-job counting, and absent versus explicitly false byte comparisons.
Both replacement patches independently pass `git apply --check` against the
active tree. The source diff is limited to the reviewed reporting corrections,
tests and notebook presentation/path changes. No retained diagnostic job was
launched or resumed. Notebook execution/guard evidence was inspected, not
rerun; no full owner suite was repeated. Prior scoped guard/CI exceptions stand.

The executor's two removed bytecode files were transient artifacts. The supervisor's
focused suite likewise recreated those two files despite bytecode suppression;
Codex removed only those generated files and their empty cache directory, then
reverified the reporting identity. See `verification.json`. No residual bytecode
change is being accepted as scientific source.

## Resources and deviations

The user-approved reporting cap is 2,400 seconds; the overall ceiling remains
14,400 seconds. Charge this supervisor review the reserved 60 seconds exactly
once, in addition to all earlier charges. Cumulative use is now:

| Category | Used (seconds) | Cap | Remaining |
|---|---:|---:|---:|
| Fixtures/development | 1,557.907571 | 1,800 | 242.092429 |
| Diagnostic jobs | 82.264630 | 10,800 | 10,717.735370 |
| Report/verification | 2,153.984045 | 2,400 | 246.015955 |
| Overall | 3,794.156246 | 14,400 | 10,605.843754 |

See `resource_accounting.json`. The original 72.984045-second executor overrun
and subsequent 60-second supervisor charge beyond the former 1,800-second cap
remain historical deviations. This acceptance does not claim compliance with
the old cap or reassign those charges. The post-launch reporting revision remains
the explicitly reviewed exception to the original source-freeze protocol.

## Integration and scientific scope

Both report-r3 replacement patches are **approved for integration by Claude**;
they are still unapplied at this acceptance. They replace the report-r2 patches,
not supplement them. The separate historical search-v2 median source patch
remains approved but unapplied until the next production source revision.

`index-deconvolution/KICKOFF_hierarchy_search_diagnosis_integration.md` specifies
the bounded integration: approved active reporting files and notebook only,
with immutable study records preserved. No commit or push is authorized.

The accepted search-v2 conclusion is still **inconclusive**. BOTH_SEPARATELY is
an exploratory recommendation on inspected data, not a confirmed decomposition,
superiority result or final causal deconvolution method. The diagnostic phase is
closed. A future algorithm phase needs its own reviewed protocol, finite budgets,
fully specified scheduling/ties, source identity and fresh confirmation data.
Neither draft A nor draft B is approved to execute by this acceptance.
