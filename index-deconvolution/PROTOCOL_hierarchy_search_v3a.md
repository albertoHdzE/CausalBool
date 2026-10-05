# HID-search-v3a: fixed wider boundary refinement

Date: 2026-10-04. Supervisor: Codex. Implementation and execution: Claude Code.
Status: **authorized bounded implementation and prospective study, delegated in full**.
Study: `search-v3a`. Confirmation run: `search-confirm-v3a-r1`.
Result root: `index-deconvolution/results/hierarchy_search_v3a/`.

## 1. Question and authority

Does refining four ranked coarse boundary trials per round, instead of one,
reduce the full method's complete archive length on the six declared boundary
cells, with the same deterministic search caps and external worker limits?

This implements Draft A after acceptance of search-diagnosis-v1 / report-r3.
The accepted search-v2 primary result remains inconclusive. The diagnosis found
shorter descriptions in a restricted supplied-cut space; it did not establish
that automatic proposal coverage was the cause of the loss. This experiment
tests one specified algorithm change. It does not establish causal identification,
optimal compression, a final causal method, or superiority over all nine baselines.

Claude is authorized to implement, test, perform fixed development, freeze,
generate the reserved population, execute, verify and deliver the handoff without
routine approval pauses. The gates in this packet are executable conditions,
not additional approval requests. Do not stop merely because a phase completed;
continue through the handoff when its gates pass. Stop on an unresolved validity
failure, exhausted allowance or required scientific redesign, with explicit
partial artifacts. No commit, push, publication, remote compute or scheduled loop.

Normative companions: `protocols/hierarchy_search_v3a/SEARCH.md`, `BENCHMARK.md`,
`ACCEPTANCE.md`, `contract.json`, `INITIAL_SOURCE_STATE.json` and
`DELEGATION_MANIFEST.json`. Markdown defines semantics; JSON supplies exact
membership and constants. An inconsistency is a preflight design failure, not
permission to choose whichever version gives a favorable result.

## 2. Baseline, integration and ownership

The baseline is `hid_full` from accepted search-v2, freeze
`0f0a72ef2f9d9faac406b6d18594a45ba9dc71ff1d0331f38c6a3fead68e1d49`.
Diagnosis report-r3 identity:
`7b1590bb4a63dd0f4c6eec5fb46f7f335d1b75b8450e5bfb3769086067f21066`.
Read its acceptance and integration handoff. The active reporting integration
already exists; verify the ten source/notebook equalities, do not reapply it.
The initial-state record discloses current dirty-tree and historical-directory
state. A changed aggregate is not silently attributed to this work or reverted.

Before edits, save status, all file-level protected hashes, and an executable
snapshot of the current hierarchy package plus shared scientific dependencies
under the new result root. Preserve this snapshot so old freezes remain auditable.
Never relax old-source validation or run an old writer into a frozen result tree.

Apply the approved historical median repair **before** new development/freeze:
`results/hierarchy_search_v2/review_closure/R1_diagnostics_median_repair.patch`,
SHA-256 `e8da5c6ba731d4635295e867e04d3fe4d303adad42ffebeed18d744be1de96c5`.
Verify the patch hash and exact application, run its four tests, and record the
new source hashes. This is a reporting repair shared by both new arms; it is not
an algorithmic treatment. Do not recompute or replace old diagnostic summaries.

Allowed active changes, narrowly scoped:

- `hierarchy/segmentation.py`: one shared search owner, k=1 compatibility, k=4
  scheduling, observational trace support and focused tests.
- `hierarchy/search_v2.py`: a shared internal hook for the new boundary policy;
  preserve the existing public k=1 behavior and configuration serialization.
- a thin `hierarchy/search_v3a.py` policy/config adapter, and study-specific
  reporting/presentation adapters under `hierarchy/` as needed.
- `hierarchy/study.py`, `benchmark.py`, `validation.py`, `freeze_v2.py`, `cli.py`,
  `cli_v2.py`, `present.py`: explicit study dispatch and thin extensions needed
  for this study. Preserve defaults and old fixture behavior. No globals patched
  at runtime, second runner/validator/bootstrap engine, or name-prefix dispatch.
- `hierarchy/diagnostics_v2.py` and `hierarchy/tests/test_study_v2.py` only for
  the reviewed median patch; other new tests belong in new focused test files.
- new orchestration/audit adapters under `experiments/search_v3a/`; new results
  below the declared root; `notebooks/build_20.py` and
  `notebooks/20_hierarchy_search_v3a.ipynb`; append one README entry and create
  one unused numbered bitacora entry. Do not overwrite a colliding filename.

Keep byte-identical: `infer.py`, `candidates.py`, `model.py`, `wire.py`,
`decode.py`, `codes.py`, `ledger.py`, `consensus.py`, `baselines.py`, `corpus.py`,
`study_corpus.py`, `report.py`, `report_v2.py`, `diagnostics.py`, the shared
schema/deconvolution/description-length owners listed in the manifest, and the
entire accepted diagnosis adapters. Do not modify the generators, grammar,
leaf heuristic, legacy search, arithmetic coding or statistical engine.

Keep all old protocols, result trees, snapshots, ledgers, handoffs, notebooks
16–19/builders (19 belongs to the BDM workstream), and existing bitacora entries unchanged. You are not alone in
the tree: no reset, stash, restore-from-HEAD or incidental cleanup of others' work.

## 3. Fixed scope and sequence

1. Verify packet/initial-state hashes and current integration; take preservation
   records and the pre-edit executable snapshot; apply the approved median patch.
2. Implement exactly SEARCH.md, fixture tests and study orchestration. Expose a
   reproducible CLI for preflight, development, freeze, run, report and verify;
   record exact commands in the implementation map. Reuse existing owners.
3. Run the fixed retained-input compatibility/development design in BENCHMARK.md.
   Repair coding defects before the freeze, retaining all attempts and charges.
   No sweep over k, caps, seed schedules, populations or commit rules is allowed.
4. Complete the engineering gate, development report, exposure declaration,
   resolved configurations, environment and full source/analysis/test freeze.
   Proceed automatically if these pass. Development improvement or coverage
   increase is **not** a gate; do not tune or replace this algorithm to pass it.
5. Generate all reserved units only after validating the freeze. Run the exact
   prospective design once, with immutable same-identity resume after interruption.
6. Analyze retained rows, verify every promised archive and all denominators,
   execute artifact-only notebook 20, write the decision and acceptance checklist,
   preserve before/after state, and stop at the final handoff.

Use one run ID, `search-confirm-v3a-r1`, and the namespaces in the contract.
No automatic new attempt/namespace following a bad or inconclusive outcome.
Any scientific source/config change after reserved access invalidates the
unchanged-freeze claim: preserve the attempt, record exposure, stop for a new
supervisor decision. Do not fix it under the same run ID, combine attempts, or
generate replacement seeds. A reporting-only defect likewise needs a separate
reviewed revision; never overwrite the frozen report source to conceal it.

## 4. Resource authorization and interruption

New phase allowance: **8 cumulative hours (28,800 seconds)**, independent of all
earlier studies and their preserved deviations:

| Category | Cap | Includes |
|---|---:|---|
| development | 14,400 s | preservation, implementation/fixtures, median repair, all retained-input regression/development attempts, preflight/freeze preparation |
| prospective | 10,800 s | reserved generation, input checks, all prospective worker/controller attempts and resumes |
| report_verification | 3,600 s | saved-data analysis, verification, notebook, prose, handoff and supervisor acceptance |

Reserve the final **600 reporting seconds**: 300 for final documentation,
preservation and handoff, 300 for Codex review. Stop optional work before using
that reserve. Do not repeat successful tests/graphs/kernel runs without a new
change or discrepancy. No borrowing between categories, resetting on resume,
or unapproved increases; finalizing a handoff is work and must fit the budget.

Charge conservative elapsed wall spans for active work under each category,
including failed attempts, setup and documentation. Count overlapping work in
the same controller span once; also report summed worker CPU/wall separately.
Do not omit time spent by simultaneous workers or label it zero; distinguish it
from the category's controller elapsed time. Persist start/stop/checkpoint events.
Never overlap different charged category controllers. Parent interruption leaves
an open span charged conservatively through the last observed process termination
or next recovery check, with the uncertainty disclosed; do not invent a zero gap.

Per worker: **30 seconds, 1 GiB RSS, at most two workers**. Deterministic boundary
caps remain 512 roots, 2,048 leaves and 256*n length charge. Use the real existing
watchdog. No change in limits when a case is slow. Before starting more jobs,
leave enough category time to terminate/record the current workers. Preserve
explicit not_run rows for intended jobs that cannot start. Missing data are not
zero costs, and a killed parent is not automatically an algorithm failure.

Prefer foreground/checkpointed bounded invocations rather than unattended
background processes. Resume only after checking no previous workers survive
and validating source/config/input/environment hashes. No recurring check-in.

## 5. Outcome and delegation boundary

The primary result is the prospective full-method k=1 versus k=4 contrast on
the six cells. Positive, harmful, inconclusive, incomplete and invalid are all
legitimate terminal outcomes; no requirement to achieve a positive result.
Portfolio/control/development findings cannot replace or rescue that endpoint.

Report whether this exact change merits a separate follow-up; do not implement
TILE, a second search candidate, a combined method, or another experiment here.
Stop with **ready for Codex review; not yet accepted**. Full delegation includes
execution and documentation, not self-acceptance of the scientific study.
