# Claude correction packet — causal state grouping

This packet is activated when the user sends it to Claude Code. Read adjacent REVIEW.md and robustness_probes.json, then the accepted design addendum and the frozen validation handoff. The V/D/X evidence is accepted; two implementation robustness findings remain. Execute this correction only. Do not launch a new scientific phase.

## Scope and preservation

Use new output directory:
`index-deconvolution/results/causal_abstraction_validation/review_closure/abstraction-validation-v1-r1/`
Stop on collision. You are not alone in the repository: preserve other edits and record the current status before work. Read and verify the original freeze/output manifests and this supervision manifest. Preserve all original run files, active core/test files, notebooks (especially 19/build_19), other studies, governance and sibling repository. No commits, pushes, publication or schedules.

Work only in isolated copies and the new closure directory. Produce patches against current active files; **do not apply patches to active or frozen files**. Hash the original source and proposed corrected source separately. Allowed patch targets are the existing deconvolution.py, tests/test_abstraction.py, and the old run's study.py/test_study.py as source references. A patch referring to historical study.py is for a separately adopted corrected copy; never apply it in place to the frozen run. Do not introduce a competing production checker or rename APIs/paths.

## R1 — evidence availability and failure precedence

Repair evaluate_classes in the copied orchestration:
- An absent representative counts as missing evidence even for a singleton class; it must not yield NO-HOLDOUT or HOLDS.
- Evaluate a present member's own existence status even when its representative is missing or has no map. A known no-map member is a structural failure and outranks missing evidence in the row decision. Existing observed disagreements also retain priority over missingness.
- Keep the distinction between individual existence and comparison evaluability: no representative substitution, null mismatch values for missing/non-evaluable comparisons, explicit reasons.
- Count missing records and missing comparisons separately if necessary; name units. Do not count a missing singleton as a micro-state comparison, since it has no held-out member. Avoid duplicate counts of the same logical event.
- Preserve complete-input scientific outputs. Document any new availability fields separately from unchanged old fields.

Add declared focused tests for missing singleton, missing representative with a failed member, missing representative with a passing member, and representative-no-map with member missing/failed. Include a failure-plus-missing regression. Restore each old branch in a copy to show the relevant new test detects it.

## R2 — reject incomplete supplied-map domains

In copied deconvolution.py::commutation_failures, require nonempty alpha and image of identical lengths, as induced_map does. Raise ValueError before iterating on malformed inputs. Test empty sequences, both mismatch directions, and complete valid cases retaining the same failure indices. Run new negative tests against the old implementation and demonstrate failure. No broad API redesign.

## Terminology and clarification

In new prose call this **causal state grouping**; use **state compaction** only for reduced state distinctions, not bit savings. Preserve historical identifiers and exact mathematical/literature quotations. Add a short terminology note linking old and new names; do not mass-rename code or frozen documents.

Keep FULL on the 11 constant-dynamics rows. Explain that validity and usefulness are separate. Label the constant/nonconstant analysis as post-hoc descriptive and its map renderer as supplemental recomputation. Do not add a new usefulness criterion or compute new scientific endpoints. Clarify the historical timing-note inconsistency in the closure only. No median patch is required for this closure: all actual medians agree; record the future-use caution.

## Validation, budget, handoff

Declare fixtures before first execution. Use the same interpreter/import owners with bytecode disabled and pytest cache disabled. Run the 63 existing scoped tests plus new regression tests on isolated patched copies. Check import origins. Verify patches apply cleanly to the exact current source bytes without changing them. Compare old versus repaired class evaluation on saved complete evidence using the frozen audit oracle's tables if needed; this is validation in copies, not a production rerun. At minimum, exercise every complete coarse-state branch and confirm unchanged existing scientific fields; disclose coverage exactly. Do not overwrite or regenerate results_v/d/x, report tables, or any original artifact.

Executor cap: **600 wall-clock seconds**: fixtures/development 300, tests/patch verification 180, preservation/handoff 120. Separate **180 seconds reserved for Codex review**, not for executor use. Include failed attempts. No category transfers. Stop optional work at 80%; at a cap, hand off honest incomplete work. No V/D/X jobs, no G, no installs or sibling edits.

Deliver HANDOFF.md, corrected source copies, patches, before/after source identities, tests and negative-test logs, comparison evidence, terminology note, attempts/time ledger and manifest. Preserve all failures. End at “ready for Codex review; not yet accepted” for the correction; the original V/D/X evidence remains accepted by the supervisor. Stop.
