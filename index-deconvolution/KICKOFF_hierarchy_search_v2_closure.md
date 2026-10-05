# Claude Code: close the HID-search-v2 review findings

Date: 2026-10-03. Supervisor: Codex. Developer/executor: Claude Code.
Paste this prompt into a Claude Code session in
`/Users/alberto/Documents/projects/CausalBool`.

Implement this bounded correction assignment and return the evidence for Codex
review. Do not stop at a plan. The user has authorized delegation of these
corrections. Do not commit, push, publish, or mark your own work accepted.

## Read first

1. `index-deconvolution/results/hierarchy_search_v2/supervision/REVIEW.md`
2. `index-deconvolution/results/hierarchy_search_v2/supervision/diagnostic_audit.json`
3. `index-deconvolution/results/hierarchy_search_v2/supervision/verification_full.json`
4. `index-deconvolution/hierarchy/HANDOFF_SEARCH_V2.md`
5. `index-deconvolution/protocols/hierarchy_search_v2/ACCEPTANCE.md`
6. `index-deconvolution/PROTOCOL_hierarchy_search_v2.md`, especially the
   post-freeze policy, and its SEARCH.md and BENCHMARK.md annexes.

Respect applicable AGENTS.md instructions. Prefer graph tools for discovery if
available; document their absence otherwise. You are not alone in this working
tree. Do not reset, stash, revert, or overwrite other work. Save the current
status and baseline hashes before starting.

## Identity and scope

Run: `search-confirm-v2-r1`, under
`index-deconvolution/results/hierarchy_search_v2/`.
Freeze SHA-256:
`0f0a72ef2f9d9faac406b6d18594a45ba9dc71ff1d0331f38c6a3fead68e1d49`.

The study is complete and its primary conclusion remains **inconclusive**.
The supervisor reproduced the primary estimate exactly and reran full
verification successfully: 385 tests, lint and relevant guards pass except for
the disclosed pre-existing single-engine failure. The six handoff section 7
interpretations are accepted. Do not reopen them or attempt to obtain a positive
primary result.

This assignment closes R1 (five incorrect diagnostic medians) and R2 (live
inference in notebook 17). It is a diagnostic erratum and presentation correction,
with an isolated source patch for later integration. It is not a new scientific
run, independent replication, or authorization for another search revision.

## Ownership and preservation

Own only the correction package at:

`index-deconvolution/results/hierarchy_search_v2/review_closure/`

Build source changes in an isolated temporary copy outside the repository,
using the recorded working-tree/snapshot bytes, not an incomplete checkout of
HEAD. Deliver repository-relative patches, not another unpacked engine tree
inside this repository. Record the copy location and baseline/patched hashes.

Preserve byte-for-byte:

- Active frozen `hierarchy/` sources, including `diagnostics_v2.py` and tests.
- Both historical run directories and the full `search-confirm-v2-r1` directory,
  including freeze, snapshots, rows, archives, summaries, diagnostic records,
  verification, and manifests.
- The existing builder and notebook 17, notebook 16, old handoffs, and supervisor
  review evidence. Deliver the revised builder/notebook in the correction package
  for review and later presentation integration.
- All protected scientific owners and unrelated working-tree edits.

Do not change the freeze to fit repaired sources or override mismatch checks.
Do not run `report`, `diagnostics`, or `verify` against the original run if they
write into it; reuse the supervisor's retained verification or use an explicitly
labeled read-only review harness with output in the correction package.

## R1: median erratum and isolated owner repair

1. Read the retained
   `search-confirm-v2-r1/diagnostics/boundary_reference/references.json`.
   Check its input hash and the referenced archives' identity before deriving
   corrections. Do not rebuild reference partitions or generate any strings.
2. Recompute each available cell's median using the conventional sample median:
   the middle value for odd counts, the mean of both middle values for even
   counts, and the existing unavailable representation for an empty cell.
   Preserve bits-per-input-bit units, membership and gap sign. Compare all cells,
   not only the five already identified in `supervision/diagnostic_audit.json`.
3. Write `diagnostic_median_erratum.json` plus a short human-readable erratum in
   the correction package. Include source/run/freeze identity, source-file hashes,
   cell membership/counts, old and corrected values, unchanged quantities checked,
   derivation-script hash, and the explicit diagnostic-only scope. Original
   `diagnostics.json` and reference records remain untouched.
4. Fix the existing `boundary_references` aggregation owner in the isolated copy.
   Do not create a second production diagnostics implementation. Retain meaningful
   tests through that owner for even and odd samples, including a negative/mixed
   example; use available helper structure if suitable. The tests must detect the
   actual upper-middle defect, not merely test `statistics.median` itself.
5. Supply the small patch and test evidence. The patched source is a separately
   identified repair for later integration, never a claim that it matches the
   original freeze. No new encoding run is needed to derive the erratum.

## R2: notebook reads saved artifacts only

1. In the isolated notebook builder, replace the two live-inference demonstration
   cells with a deterministic, explicitly identified retained case and its six
   arm archives/telemetry. Explain that it is an illustrative example, not a new
   endpoint. Select by an explicit retained case ID, not by searching for a
   favorable result. Decode and parse the saved archives with the existing owners
   to show exact reconstruction, stages and field costs.
2. Remove notebook encoder and corpus-generation imports/calls. Do not generate
   the previous synthetic period-63 example or rerun it to manufacture a saved
   artifact. Preserve the required historical result, exposure status, counts,
   primary gates/interval, five contrasts, descriptive summaries, resource events
   and supplied-boundary limitations.
3. Read the original diagnostics together with the identified median erratum;
   display corrected medians and visibly label the correction. Leave the primary
   and targeted results unchanged. Make artifact paths explicit and robust to
   execution from the repository root or notebook directory.
4. Deliver `build_17.py` changes as a patch and the executed
   `17_hierarchy_search_v2.corrected.ipynb` in the correction package. Preserve
   existing original notebook outputs for comparison. Document the intended paths
   for later integration of the revised presentation.
5. Execute the corrected notebook, retain the execution log and checks for zero
   errors/unexecuted cells, and verify artifact-only operation. Use a test harness
   that fails if inference or reserved generation is invoked; do not add fault
   switches or monkeypatches to production code. Confirm that displayed medians
   come from the erratum and saved scientific results retain their values.

## Validation and handoff

- Retain input/source hashes, patch hash, output hashes, exact commands and exit
  statuses. Verify all protected files/run-tree hashes before and after.
- Run focused regression tests and lint on changed Python files in isolation.
  Run the retained hierarchy/shared-owner suite with the isolated repair; compare
  collection against the 385-test baseline and explain additions. Do not weaken
  tests or assert that the final count must equal 385.
- Keep original-source production verification distinct from patched-source
  correctness checks. An isolated patch failing the old freeze is expected, not
  something to suppress. Preserve the valid inconclusive scientific conclusion.
- Record correction automation elapsed time without resetting prior study time.
  The supervisor verification record reports roughly 2,175/7,200 seconds used
  for diagnostics/verification and 14,679/43,200 overall; read the current ledger
  before work and account for this assignment separately and cumulatively in the
  closure report. Do not launch concurrent benchmark workers or another study.
- Do not run destructive repository-wide checks against others' modified outputs.
  The disclosed guard failure and `make ci-local` omission remain documented;
  cleaning stray protocol copies or `.kilo` is outside your ownership.

Write `review_closure/HANDOFF.md` containing R1/R2 closure evidence, artifact
paths, baseline and patched identities, changed-file inventory, test/lint/notebook
results, original-versus-corrected diagnostic values, preservation proof, resource
accounting, and any unresolved issue. State exactly what remains isolated and what
Codex would integrate. Leave acceptance to the supervisor.

Finish with the handoff path, run ID, unchanged freeze hash, and:
**ready for Codex review; not yet accepted**.
Stop there. Do not initiate the next research phase.
