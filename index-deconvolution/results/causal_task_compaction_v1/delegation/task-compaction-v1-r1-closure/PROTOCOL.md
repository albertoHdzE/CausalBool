# Task-compaction closure and research positioning

Status: authorized when this packet is forwarded to Claude Code. Run ID `task-compaction-v1-r1-closure`. Complete the authorized work autonomously and stop at a reviewable handoff. This is a correction and integration-preparation phase, not another scientific benchmark.

## Scope and owners

Read the Codex review pinned by this packet, original HANDOFF, THEORY, OWNERSHIP and freeze. Preserve all existing evidence, active source, tests, notebooks including notebook19/build19, governance, sibling repositories and unrelated dirty files. Snapshot protected hashes and git status before development. Check the delegation manifest first; stop on an unexplained mismatch or an occupied output path.

Write only under:

`index-deconvolution/results/causal_task_compaction_v1/review_closure/task-compaction-v1-r1/`

and disposable `/tmp` copies. Use layout-preserving isolated copies; no dependencies installed. Set no-bytecode and disable pytest caches outside the output. Graph tools preferred for discovery, targeted reads if unavailable.

Existing concept owner remains `index-deconvolution/src/deconvolution.py`. The public APIs minimal_task_partition and distinguishing_task_word remain unchanged for valid inputs. This ticket additionally authorizes task_word_path with the R2 contract below. No additional production engine or public API. The extra unchanged repertoire_program.py dependency is authorized read-only in the isolated layout.

Permitted integration targets in copies only: existing core, new `tests/test_task_compaction.py`, new `tests/fixtures/task_compaction_v1.json`. Deliver replacement patches against the current active tree, including the fixture file. Do not apply them to active files. The revised audit is a separately identified run-local revision, not a replacement of frozen src/audit.py.

## R1: complete and robust evidence audit

Repair the actual audit pipeline, not just label_status. Separate schema validation, availability, scientific checks and reporting. Verify the original freeze and saved evidence identities; declare the revised audit's own source identity separately. Preserve independence from producer/minimizer/witness/comparator implementations. Accepted model/candidate declarations may still be used.

Rules:

- Available malformed or contradictory evidence is INVALID. Missing artifacts/records alone are INCOMPLETE. INVALID takes precedence when both occur; both issue lists and intended/available counts survive.
- A missing file named by a seal is missing evidence; an existing file with a wrong hash is invalid evidence. Do not silently reseal original evidence.
- Exact declared cell and record sets apply to summary rows too. Empty or truncated summaries are incomplete; duplicates, undeclared IDs and altered present values are invalid. No unavailable quantity becomes zero, and no result label or aggregate is evaluated from incomplete inputs as if complete.
- Parse JSON/JSONL and validate necessary schema before indexing. For malformed JSONL, identify the line; check independent readable records where possible. A corrupt artifact may prevent its dependent calculations but cannot suppress independent evidence checks. Do not catch everything and label a program bug as success.
- Check vector label types, canonical form, dimensions, index ranges, required fields and finite integer counts. Validate all present scientific fields using the existing independent logic. Never report more comparisons than were actually performed.

Declare and implement this finite test matrix before running it, all on tiny fixtures or copies of saved evidence:

1. Original complete data: VALID_COMPLETE, all 24/3,276/85,504 intended checks, all original scientific values unchanged.
2. Summary `cells=[]` and one omitted summary row: INCOMPLETE with correct counts.
3. Duplicate summary ID and undeclared summary ID: INVALID.
4. One changed summary scientific value: INVALID at that field.
5. Remove M1 table only: INCOMPLETE; preserve intended versus available counts and skipped-dependency reasons.
6. Malformed candidate JSONL and malformed table JSON: structured INVALID, no unhandled traceback; independent files still checked.
7. Missing cell plus wrong decoder in another available cell: INVALID and missing both recorded.
8. Missing required summary/record identifier; malformed alpha/stage vector or invalid state index: structured INVALID.
9. Normal integrity mode: missing sealed artifact alone INCOMPLETE; existing modified artifact INVALID.
10. Retain the four original corruption probes, including validity-pass/minimality-fail identity and failure-over-missing.

Do not expand into unbounded fuzzing. Show the three Codex probes fail against the old audit for the intended reasons. A new audit can be iterated on disposable copies with each failed attempt retained; no scientific production job is authorized.

## R2: public replay contract

Before replay validate transitions with the same complete-domain contract as the minimizer: nonempty list/tuple of nonempty equal-length list/tuple tables, built-in integer indices in range, no bool. Validate x, and validate the entire word as list/tuple of built-in integer action indices; empty word allowed. Invalid inputs raise ValueError, including malformed unused tables. Reject generators without consuming them; no coercion. Reuse private validators where appropriate inside the owner.

Tests must include the three review examples, empty/ragged tables, negative/out-of-range targets, invalid unused table with empty word, bool state/action/target, malformed word containers, invalid action late in the word, valid empty word, and noncommuting actions applied in written order. Tests for existing valid minimizer/witness calls remain unchanged. Replacing only this validation with the old implementation must cause the relevant tests to fail for behavioral reasons.

## Packaging and valid-data preservation

Copy the original declared fixtures unchanged into the proposed tests/fixtures location; link its original SHA-256 in provenance. Update only the test's fixture lookup. Prove the new tests run in a layout-preserving scratch tree without the task-compaction run folder. The 73 historical regression tests may still use their accepted historical study fixtures; disclose that separately.

Run the 73 accepted regressions, all existing 31 compaction fixtures, all 5 audit-label tests and new behavioral/pipeline cases; count collection changes explicitly. Ruff on changed sources. Test the owner check including the authorized third helper. Re-run repository read-only guards and compare known failures; no broad repairs and no make ci-local that writes unrelated results.

Audit the saved 24-cell dataset with the corrected audit, without invoking produce.py or any M1–M4 minimization. Compare all saved scientific results and summaries; zeros, absent values and nulls remain distinct. If any scientific discrepancy appears, stop adoption and report it; do not regenerate the production. The original 62 artifacts are protected byte for byte. Verify replacement patches apply to the active baseline in a disposable copy and reproduce the corrected owner/test/fixture bytes exactly.

## Literature and bounded next decision

Read the primary sections named in LITERATURE_AND_ROADMAP.md, record versions, sections actually read, access limitations and local hashes for files downloaded. No search-summary-only support for technical conclusions. Deliver a contract comparison table: state vs variable grouping, all-start vs restricted domain, single vs multiple transition maps, outputs preserved, word/input quantifiers, exactness, minimality scope, computational assumptions and existing implementations/licenses (verify these if making a reuse recommendation).

Answer whether our component is an implementation of established theory; whether any cited method addresses scalability without changing the all-state/action contract; and what would have to change for approximate or finite-horizon grouping. Any unproved mapping is explicitly a hypothesis. Do not implement literature algorithms or launch experiments.

Deliver a narrowly scoped v1 completion plan. Default recommendation: integrate and document the exact known-model component after closure acceptance. At most one optional next-research proposal, only with a concrete unresolved need, closest prior method, acceptance criterion, cost and stop condition. NO_NEW_STUDY_JUSTIFIED is a valid and preferred outcome when these are absent. Do not promise a final general theory, empirical causal identification, fractal structure or compression savings.

## Outputs and accounting

HANDOFF.md, CHANGELOG.md, corrected audit and tests, corrected isolated owner/tests/fixture, replacement patches, OWNERSHIP_ADDENDUM.md, LITERATURE_MAP.md, V1_COMPLETION_PLAN.md, DECISION.md, audit results and probe evidence, test/mutation/guard logs, regeneration command for closure evidence from saved inputs, source and output manifests, before/after preservation, attempt log and time ledger. Every failed attempt retained; files below 10 MB or losslessly compressed with both identities.

Historical time erratum: carry forward 1,685 recorded seconds plus a conservative 300 for excluded final handoff/manifest = 1,985 executor seconds; append separately, never rewrite original ledger. This closure has a new **3,600-second executor cap**: preflight 300; corrections/fixtures 1,200; tests/audit/preservation 900; literature/roadmap 900; handoff/manifests 300. Separate **600-second Codex review reserve**, total 4,200. Include thinking, failed attempts and final writes. No category transfers; stop at a cap with partial truthful handoff. Record an explicit conservative final-write allowance when exact self-accounting is impossible.

No staging, commits, pushes, publishing, recurring tasks, sibling edits, active patch application, new benchmark, or successor implementation. Finish: **ready for Codex review; not yet accepted**.
