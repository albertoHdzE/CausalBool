# Evidence-bounded manuscript revision

Lead specification, 2026-09-23. Status: implemented by Luna and accepted by the
lead for internal draft revision; see `paper/PHASE2_REVISION_REVIEW.md`.
This is a manuscript task, not a new
experiment or an amendment to the locked Phase 2 protocol.

## Scientific objective

Revise the existing internal compiler case study to incorporate the accepted
structural-encoding feasibility campaign. Preserve the production contribution
and measurements. Report the incomplete coverage as an inconclusive feasibility
result. Do not recast implementation acceptance as scientific success.

## Ownership and preservation

Luna owns `paper/` revisions only. The lead owns this plan and `plan/STATUS.md`.
Other work is present: do not revert it. Do not modify production, research,
tests, results, reference files or the frozen `plan/phase2/` package. No new
benchmark, protocol change, commit, push, merge or external publication.

Before editing, preserve the existing manuscript as
`paper/baselines/20260921/`: copy main.tex, main.pdf, README.md,
CLAIMS_AND_EVIDENCE.md, BUILD_VALIDATION.json, both Python build scripts and
the generated directory. Write a SHA256 manifest for these copies and record
the current git HEAD. Exclude transient TeX files and build caches. Never
overwrite a pre-existing baseline; verify it and report discrepancies instead.

## Mandatory evidence

Read AGENTS.md, INDEX_ONLY_PLAN.md, STATUS.md and the existing manuscript and
claims contract. Production evidence remains
`results/direct_index_v4_optimization_repair2/lead_review/` and its accepted
review. Phase 2 evidence is exclusively
`results/phase2_structural_encoding/phase2_repair_20260923c/`:
LEAD_ACCEPTANCE.md, manifest.json, gates.json, hypotheses.json, checker.json,
p1/summary.json and the raw files named in that summary. Read the locked
protocol and structural plan to describe sampling accurately. Earlier repair
runs are history, not extra samples. Distinguish fixture enumeration, sampled
public executions, tests and mathematical proofs throughout.

## Required manuscript changes

1. Keep the title and production narrative. Add one bounded abstract sentence
   stating that structural-encoding feasibility sampling failed the declared
   coverage gate, leaving subsequent experiments unmeasured.
2. Add a dedicated section before related work: motivation, fixed sampling
   design and stopping rule, finite-fixture checks, public coverage table,
   stage disposition and interpretation. Define raw-bit versus option-path
   sampling; do not imply uniform sampling of feasible schedules. Explain the
   minimum of 100 distinct completions per program and the union across streams.
3. Generate the eight-row coverage table from retained JSON, not manually typed
   values. Pinned order counts are 0, 234, 194, 55, 135, 16, 168, 17; these are
   distinct completions per program, not case executions. Include raw and path
   completions, distinct union and coverage disposition with clear column labels.
4. Report 160,000 attempts, 16 streams, 819 completed draws, 1,356 case checks,
   zero observed discrepancies. Four programs miss coverage. All raw-bit
   streams have zero completions. P0 PASS; P1 INCONCLUSIVE; P2-P5 blocked and
   unmeasured. Zero checker findings means internally consistent artifacts;
   `artifacts_complete=false` and `scientific_success=false` must remain explicit
   in the evidence documentation. Zero observed defects is not a general proof.
5. Describe finite checks with exact denominators derived from summary.json:
   12 fixtures, four codecs, 24 exhausted code universes, 564 round trips.
   Do not claim all four codecs were exhaustively checked on every fixture.
6. Update discussion/future work: a new sampling policy would need a separately
   specified amendment and fresh evidence. The present result neither proves
   structural encoding impossible nor demonstrates compression, scaling,
   discovery or performance benefits. Do not add an unimplemented protocol.
7. Preserve all production numerical claims, caveats, proofs and citations.
   The 5.6321% result is composite-score improvement, not runtime speedup or
   an isolated causal effect of representation. No new novelty claim or citation
   is needed. Do not mix September 20 production tests with September 23 tests.
8. Extend CLAIMS_AND_EVIDENCE.md, README.md and artifact reproduction text with
   the new evidence map, dates and limits. Explain that the 113 MB raw-attempt
   file remains local and packaging is unresolved; do not claim a portable,
   published or fully archived Phase 2 artifact.

## Reproducible derivation

Extend the existing generator (or add a small paper-local helper called by it)
to read the accepted Phase 2 JSON and generate a TeX table and metrics JSON.
Record source paths and SHA256 hashes. Validate raw artifact hashes against
summary.json using streaming reads, and assert the expected gates, counts and
checker disposition. Fail if the retained inputs contradict the manuscript.
Retain the existing production validation. Build manifest must include any
new generator/helper. Generated table must actually be included by main.tex.
Do not modify evidence files or run the campaign to make a check pass.

## Validation and delivery

Run from repository root:
`venv/bin/python luminal-challenge/paper/build_paper.py`.
Require exit 0 and no unresolved references, LaTeX warnings or overfull boxes.
Inspect the new section in the built PDF (render pages if tools are available).
Confirm original production metrics are unchanged and baseline copy hashes
match the initial manifest. Run `git diff --check` on changed tracked files.
Write `paper/PHASE2_REVISION_HANDOFF.md` with changed files, exact commands and
exit codes, baseline manifest location, evidence hashes, claim limitations and
any remaining issues. Do not mark the manuscript peer reviewed or accepted.

Lead acceptance requires checking the generated numbers against source JSON,
the wording against stage verdicts, the baseline preservation, and a successful
build. The lead records the final disposition in STATUS.md after review.
