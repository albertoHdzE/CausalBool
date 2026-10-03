# Supervisor acceptance: validator closure patch

Date: 2026-10-02. Follows bitacora37 and the developer's
`results/hierarchy_v1_supervision/confirm-v1-r1/validator_closure/HANDOFF.md`.

**Decision: APPROVED for the three requested validator fixes and their regression
tests. The patch remains unapplied.** No further corrective delegation or encoding
benchmark is required to complete this assignment.

Approved patch SHA-256:
`587d7bc0e0b9f598a80be99776655e3cc8d1df355cfa62884e7fbd8ee5809346`.

The frozen numerical findings of `confirm-v1-r1` were accepted in bitacora37.
This decision closes the remaining R1a/R1b/R1c requests **in the reviewed patch**.
The active frozen package still contains its original implementation; this is
approval of a correction artifact, not a claim that it has been installed.

## Independent review evidence

I verified the patch hash, the active frozen-source hashes, the isolated baseline,
and the proposed changed-file hashes. I then created a fresh temporary review copy
from the baseline, applied the submitted patch there, and verified that all four
resulting files exactly match the proposed hashes. The active repository sources
were not patched.

- **331 tests passed**, independently, in 30.01 seconds. The sole warning was the
  existing pybdm dependency deprecation warning. Lint passed.
- The tests exercise missing and malformed archives, both types of duplicate,
  undeclared rows/cases, whole-run scope, stale verification state, and propagation
  of unrelated exceptions through the actual tiny-run production paths.
- I reran the inspected read-only corpus harness using this fresh patched copy:
  **26,112 rows**, **16,402 distinct decoded archives**, and a **360-archive isolated
  decoder sample** all checked out apart from the expected source provenance
  mismatch.
- The production validity result is correctly **exit 2**, with exactly the three
  changed-source entries for `validation.py`, `cli.py`, and `report.py`. There are
  **zero other invalid entries**. The old encoding freeze is not rewritten or
  claimed to identify the patched validator.
- In the explicitly labeled counterfactual reading that sets aside those exact
  three source-change entries, all nine checked summary sections match the stored
  study. Representative ledgers are byte-identical; the claim ledger is equal.
  This reading is regression evidence, not production verification under the old
  freeze.
- All **18,062 files** in the retained run have an identical aggregate directory
  hash before and after the harness. The active source/protocol/documentation
  hashes still match their freeze after review.

The harness was written by the developer, inspected by the supervisor, and rerun
independently. This is not another independent implementation of the codec or
statistics. The earlier supervisor audits remain the independent endpoint evidence.

Evidence is in
`results/hierarchy_v1_supervision/confirm-v1-r1/validator_closure/supervisor_review/`:

- `patch_application.json`: verified source identity and patch application;
- `tests.txt`: independent test and lint results;
- `corpus_validation.json`: full retained-corpus reading, provenance differences,
  equality checks and before/after directory hashes;
- `decision.json`: machine-readable scoped acceptance and integration policy.

## Decisions D1–D3

**D1 accepted.** A row file may contain fewer methods when the study is incomplete.
Its rows must be unique, declared, metadata-consistent and equal to the merged
representation. The whole-design validation still detects absent methods and
prevents complete-study acceptance. Treating absence as incompleteness rather than
malformed data preserves the intended distinction between exit 3 and exit 2.
This is a clarification of the assignment's “exactly expected methods” wording,
not permission to omit methods from the completed benchmark.

**D2 accepted.** Rejecting undeclared case files is appropriate for whole-run
validation. Declared split membership must govern both the merged rows and the
individual row artifacts. The implementation also rejects other undeclared
entries in the rows directory; that directory is consequently reserved for
declared case files, not miscellaneous notes or inspection outputs.

**D3 accepted.** Replacing an older verification result with `not_verified` before
starting prevents an interrupted or failed attempt from leaving an older success
as its apparent result. Unexpected programmer errors continue to propagate; they
are not converted into scientific or engineering success.

## Remaining limits do not reopen this bounded assignment

Malformed JSON and absent row fields can still abort some paths. Verification's
initial marker prevents those exceptions from leaving an older success record,
but the patch does not provide comprehensive malformed-metadata reporting. These
are recorded robustness limits, not evidence of an incorrect retained result.

Computing the three report outputs before writing them prevents mixed outputs
caused by a computation failure. It does **not** make three separate file writes
transactional: interruption or an I/O error during writing can still leave a
mixture. The handoff's stronger wording should be read with this qualification.
No multi-file transaction mechanism was required for these three fixes.

The active test inventory remains 317 because the patch is unapplied. On
integration, update the inventory to the resulting suite, currently 331 tests.
The absence of `make ci-local` or `verify --full` in the partial isolated tree is
not a blocker here: its relevant tests, lint, source provenance, and full retained
corpus were directly checked. No repository-wide CI claim is made.

## Integration decision and scientific status

Keep the current frozen tree unchanged. Retain this approved patch and its hashes
as the correction artifact for the next development revision. Integrate it before
that revision's source/configuration freeze, update its test inventory, and record
its provenance separately. Do not edit either historical freeze or change old row
identities to imply that these patched sources encoded the original archives.

This policy completes the requested patch review without an unnecessary third
encoding study. It does not authorize publication, commit, push, a new benchmark,
or a new scientific claim. Historical runs remain interpretable with their own
source versions.

The accepted scientific conclusion remains unchanged: primary saving
**−0.0446156382 bits per input bit**, 95% interval
**[−0.0536775270, −0.0358242637]**. The five ablations retain their positive 99%
intervals within the configured search. The method has not demonstrated an
overall portfolio advantage on the prespecified population. The correctness
replay is not an independent replication, and the transfer/development caveats
remain in force.

**Closure:** the frozen negative study and the scoped validator correction are
accepted. Further research should address the gap between feasible descriptions
and automatic search, separately from wire-format overhead; that is a new research
stage, not unfinished work in this correction assignment.
