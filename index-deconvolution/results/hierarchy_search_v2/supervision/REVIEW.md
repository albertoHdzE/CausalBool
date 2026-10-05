# HID-search-v2 supervisor review

Date: 2026-10-03. Reviewer: Codex.
Run: `search-confirm-v2-r1`.
Freeze: `0f0a72ef2f9d9faac406b6d18594a45ba9dc71ff1d0331f38c6a3fead68e1d49`.
Decision: **changes_requested — packet not yet accepted**.

The primary scientific conclusion is correctly reported as **inconclusive**.
The independent archive-length audit exactly reproduces
`+0.005605234982532739` bits per input bit. The reported 95% interval crosses
zero. Neither finding below changes that primary estimate or its population;
neither calls for more reserved instances or another algorithm revision.

## Findings

### R1 — P2: diagnostic medians use the upper middle observation

`index-deconvolution/hierarchy/diagnostics_v2.py:167` assigns
`g[len(g) // 2]` to `gap_median`. With an even number of observations this is
the upper middle order statistic, rather than the usual sample median (the
average of both middle observations). Five saved cell summaries differ from
that median, and notebook 17 prints them as medians.

| Cell | Strings | Saved median | Correct median |
|---|---:|---:|---:|
| transfer F12, 16,384 | 8 | 0.1196070055531824 | 0.1181531121515912 |
| transfer F12, 65,536 | 8 | 0.09033203125 | 0.09032996380852432 |
| transfer F12, 131,072 | 8 | 0.0834941827198169 | 0.08346462065678345 |
| stress S02, 4,096 | 16 | -0.021484375 | -0.022452360712978778 |
| stress S02, 65,536 | 16 | 0.008422466012603182 | 0.004455362455942263 |

Units are bits per input bit. These values were recalculated with
`statistics.median` from the saved per-string reference records. All 176
reference archives passed hash, length, independent decoding and signed-gap
checks; the diagnostic cell means agree. Evidence: `diagnostic_audit.json`.
The defect is limited to these descriptive medians, not primary/contrast
bootstrap statistics or the stated mean boundary gaps.

Required closure: supply a clearly labeled diagnostic erratum derived from
the saved reference records, and make the presentation use the corrected
medians. Retain the original frozen sources and artifacts. A production source
change must follow the protocol's post-freeze amendment/new-identity policy;
do not silently patch `diagnostics_v2.py` under the existing freeze. Test even
and odd sample medians in any separately versioned source repair.

### R2 — P2: notebook 17 executes inference despite the artifact-only requirement

`index-deconvolution/notebooks/build_17.py:118` calls `infer_v2` for all six
arms, and line 124 calls it again for `hid_global`. These calls are also in
the retained notebook's fifth and sixth code cells. ACCEPTANCE.md lines 92–93
require the notebook to read saved artifacts and not rerun inference.

The constructed example does not expose new reserved data and does not
invalidate the prospective study. It nevertheless violates the notebook
contract and the notebook introduction's statement that everything is read
from saved artifacts. Existing successful cell outputs do not establish
compliance with that requirement.

Required closure: replace those cells with reads of retained case/arm archives
and telemetry (which already contain exact stage, archive and ledger examples),
then execute the revised notebook and retain its output/error checks. Record
this as a presentation revision; preserve the original builder identity in
the snapshot and leave the scientific freeze unchanged.

## Decisions on handoff section 7

All six listed routine interpretations are acceptable:

| Item | Decision and basis |
|---|---|
| (a) Decode identical candidate bytes once | Accept. The cache is local to one input/invocation, keyed by complete bytes, and populated only on a path that decodes or raises fatally. Duplicate proposals remain counted and serialization remains charged. |
| (b) Charge leaves before the root trial | Accept. Both charges occur before their respective work, exhaustion stops B, and the best completed archive survives. The specification does not require reserving the root charge before leaf work. |
| (c) Always add the deletion join | Accept. This follows BENCHMARK.md's explicit mapping; insertion-adjacent cuts require survival, the deletion join does not. |
| (d) Parse final rule/depth counts inside the worker | Accept. The parse is included in encoding time and the whole worker watchdog interval. |
| (e) Charge development diagnostics/report to diagnostics/verification | Accept. Those are diagnostics/report jobs and the category and total allowances remain comfortably below their limits. |
| (f) Notebook displays the earlier plain verification record | Accept as a historical execution record. Do not present that embedded record as the later full verification; the full record is separate. This acceptance does not waive R2. |

The disclosed fixture-limit watchdog tests exercise the real runner path and
are acceptable evidence for timeout/memory propagation. They do not establish
that the scientific study experienced a 30-second timeout or a 1-GiB breach.

The pre-existing single-engine guard failure remains a failure, not a clean
pass. The exact paths are retained in `../prefreeze/guards/check_single_engine.txt`;
the two stray protocol copies are recorded in the pre-edit status. The pinned
mirror is an allowed owner, not a newly introduced duplicate. Cleanup belongs
to a separate owner task; this review does not remove those files or the `.kilo`
worktree. Skipping `make ci-local` is allowed by ACCEPTANCE section 3 under the
documented dirty-tree conditions. No repository-wide CI claim is accepted.

## Evidence checked

- Supervisor rerun of `PYTHONPATH=index-deconvolution:src venv/bin/python -m
  hierarchy.cli verify --study search-v2 --run-id search-confirm-v2-r1 --full`:
  exit 0, valid, complete, inconclusive; started 16:18:38 UTC and finished
  16:27:29 UTC. All 28,672 rows/archives validate, 17,573 distinct archives
  decode, 8,960 nesting pairs pass, the 390-archive separate-process sample
  passes, and summary/claim-ledger recomputation agrees. Pytest: 385 passed;
  ruff, core-index and test-manifest checks pass. Single-engine remains exit 1
  for the disclosed external sites. Full output record: `verification_full.json`.
  This command refreshed the run's verification record and charged about
  531 additional seconds to its existing execution ledger; diagnostics/verification
  usage is now about 2,175 of 7,200 seconds, total about 14,679 of 43,200 seconds.
- Source review against SEARCH.md, BENCHMARK.md and ACCEPTANCE.md: cumulative
  search, consensus/local/global builders, boundary trial/refinement order,
  deterministic caps, worker dispatch and timing, paired cell weighting,
  bootstrap draw order, claim gates and freeze validation.
- Canonical freeze identity, all 76 snapshot members, all current frozen source,
  protocol, informational and prefreeze evidence hashes: match.
- Ten protected owner hashes and all 13 delegation/reference file hashes: match.
- Historical snapshot: 25 members match. Both historical run trees reproduce
  their pre-edit hashes (18,058 and 18,062 files).
- Historical read-only audit under the extracted old sources: exit 0 and equal
  to the stored historical audit; estimate `-0.044615638178146094`.
- Approved validator patch hash and retained patched validation-test file: match.
- Development legacy input/archive identities: all 1,632 match the historical
  full arm. Pilot resume record: 12-case replay, no differences.
- All 10,752 HID rows satisfy the inspected template and B counter limits.
- Independent primary archive arithmetic: exit 0, exact point-estimate agreement,
  correct 840 strings / 420 units / 21 cells, portfolio minima and contrast points.
- All 176 diagnostic reference archives decode to the corresponding input hash;
  their signed gaps and mean summaries agree. Median discrepancies are R1.
- Notebook's retained outputs: 15 executed code cells, no error outputs. Source
  inspection identifies the live inference calls in R2; no new notebook execution
  was performed during this review.

Supporting machine-readable checks are beside this file:
`provenance_audit.json`, `diagnostic_audit.json`, `telemetry_audit.json`, and
`development_and_notebook_audit.json`. The successful production verifier does
not recompute the diagnostic median summaries or check that notebook cells
avoid inference, so its success does not resolve R1 or R2.

The developer handoff and frozen package are preserved. Review output is kept
outside the frozen executable closure. No encoding campaign, tuning, commit,
push or publication was performed. Close R1 and R2 with a documented artifact
correction, then return the packet for final acceptance.
