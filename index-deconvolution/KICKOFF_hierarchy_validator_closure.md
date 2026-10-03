# Claude Code: close the remaining validator cases

Read `bitacora/37_hierarchy_v1_r1_supervisor_review.md`, especially §4.
The frozen numerical result of confirm-v1-r1 has been accepted with its stated
scientific scope. The reusable validator is not unconditionally accepted yet.

## Deliverable and boundaries

Prepare a **reviewable patch plus tests in an isolated copy**. Do not edit the
active frozen `hierarchy/` sources, either frozen run directory, old handoffs,
source snapshots, or numerical outputs. Do not freeze another benchmark, run
another full encoding study, tune the search, change the corpus, or alter any
inference/codec/statistical behavior. Do not commit, push or revert unrelated work.

Deliver the patch under
`results/hierarchy_v1_supervision/confirm-v1-r1/validator_closure/`, with repository-
relative paths, baseline source hashes, test logs and `HANDOFF.md`. The review will
decide how to integrate/version it; never claim patched sources match the old freeze.

## Required fixes

1. Missing/malformed archives must not cause report/verify presentation or the
   separate-process sample to abort before writing a structured invalid record.
   Preserve detailed validation failures and exit 2. Do not silently reuse a stale
   verification file, label a skipped sample successful, or suppress unrelated
   programmer errors. Cover missing and malformed selected representative/sample
   archives. Summary and claim outputs must not imply successful validation.
2. Validate `rows/<case_id>.json` as a list of exactly the expected unique methods
   with matching case metadata before converting to a dictionary. Identical as
   well as conflicting duplicates must fail. Keep the existing JSONL duplicate
   checks and exact comparison between the two representations.
3. Do not silently discard unknown/undeclared split rows during whole-run
   validation. Feed the complete row set to the design validator. If an explicit
   subset-inspection API is retained, distinguish it from whole-run acceptance
   and reject/label extra rows consistently. Do not relax expected membership.

## Tests and evidence

Use the existing tiny actual-run fixtures. Add regression tests through both
report and verify where applicable; explicitly assert return codes, newly written
validation records, evidence gates and absence of stale success. Include the
three cases preserved in
`results/hierarchy_v1_supervision/confirm-v1-r1/test_retained_validator_edges.py`,
but invert their assertions to the corrected desired behavior. Add a malformed-
archive case and a conflicting duplicate case. Avoid new encoders or test-only
validation paths.

Run the original 317 tests plus the additions and lint in the isolated copy. Show
that valid complete input remains valid, that negative science still exits 0,
and that primary/ablation arithmetic remains unchanged. Run the corrected validator
read-only against the complete retained corpus, using an explicit test harness
that distinguishes original encoding provenance from patched validation code;
write its evidence only to `validator_closure/`. Do not override a freeze mismatch
and present it as normal production verification.

In the handoff, list changed files, the patch hash, the isolated source hashes,
exact tests and results, old/new validation outcomes, remaining issues and a
statement that active frozen files were untouched. Return its path to the user
for Codex review. This is a small correctness patch, not a new research iteration.
