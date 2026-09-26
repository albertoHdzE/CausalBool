# Claude Code assignment: close the remaining evidence/gate defects

Codex is specification owner and final reviewer. Read AGENTS.md, the original
locked delegation package, the previous repair amendment, and this directory's
LEAD_REVIEW.md, probes.py/probes.json and raw_probe.py/raw_probe.json.

Implement F1–F4 completely. This is a bounded continuation of R2/R3, not a new
scientific campaign. Keep all original scientific thresholds, domains, seeds,
budgets and P1 blocking rules unchanged. Preserve production, historical tests,
reference files, locked plan inputs, prior runs and unrelated work. You are not
alone in the repository; do not revert others' edits. Allowed edits remain
research/*.py, research/README.md, research_tests/* and new result directories.
Do not commit, push, merge, submit or spawn agents.

1. Establish one evidence-derived stage validation interface used by checker and
   imported-stage authorisation. It must distinguish validation failure,
   INCONCLUSIVE, scientific null outcomes, PASS and missing/unrequested work.
   Keep independent scientific recomputation independent of runner status labels.
   F1's mutation must produce a finding/nonzero failure, not merely an inconclusive
   note alongside artifacts_complete=true. Derive required stages from an explicit
   recorded CLI request, and validate that request against the declared stage
   machine. Reject missing required stage/gate entries.
2. Resolve and validate all transitive imported dependencies before entering a
   dependent body. Match full source/input/amendment identity, required digests,
   raw membership and recomputed gates. Preserve links and validated dependency
   metadata in the new manifest; the new run's checker must resolve imported
   artifacts without pretending they were locally generated. Reuse this logic
   without introducing a force/skip mode or circular import boundary.
3. Parse and reconcile finite-domain raw rows, derive their exact expected keys,
   and independently re-execute the required finite-universe decodes/round trips.
   Do not trust exhausted, set_equality or reported codec counts. Validate raw
   sampling row stream-specific seed, fixed codec/domain, contiguous attempt
   numbers and expected stream membership; reproduce deterministic draw sequences
   to ensure retained indices are the declared seeded draws. Reconcile cases and
   identity multiplicities per stream. Fail on extra or missing raw rows.
4. Define and enforce exact command/log requirements for both internal stages
   and subprocess measurements. A stage that legitimately runs no subprocesses
   need not fabricate commands; a launched worker requires a completed record,
   exit code and retained log. Missing/null exit codes, absent referenced logs,
   missing required worker records and failed commands must fail acceptance.

Regression acceptance: use a newly valid repaired control and run each mutation
separately with freshly matching hashes where relevant. Include F1, F2 and F3
verbatim failure modes and an end-to-end F4 test. Include a genuinely passing
controlled prerequisite as positive resume control, a real inconclusive input,
a hash-consistent false PASS, missing raw dependency evidence, and a successful
resumed run whose checker can resolve its transitive provenance. Controlled
fixtures never count as scientific P2–P5 evidence. Every corruption must fail
for its intended reason, not unrelated source drift or an obsolete control.

Record hashes of both review/amendment pairs in new provenance and require their
membership/integrity. Do not change or rehash the original plan package. Preserve
previous source/evidence snapshots. After source is final, run package validation,
all research tests (including repair tests), a fresh --stage all campaign and its
checker, export, full production verification and the three-repeat comparator.
Use unique output paths, retain actual logs and exit codes. P1 INCONCLUSIVE and
blocked P2–P5 remain valid campaign outcomes, not reasons to change the protocol.

Before calling the task complete, check remaining conditional-model budget paths
against the previous R4 requirement: model construction must not begin after its
absolute deadline; proposal work and candidate validation must enforce declared
caps as well as time. In particular inspect _model_optimise's elite encoding,
exact_cover call and proposal validation loop. Add targeted controlled regressions
for any necessary corrections; never manufacture positive scientific evidence.

Preserve oversized old raw files locally and do not stage them. No raw evidence
truncation or historical rewrite is authorised. Commit packaging is deferred
until acceptance; it is not a blocker to this local repair.

Produce a new HANDOFF.md with F1–F4 separately marked fixed/unresolved, exact
locations, mutation controls and outcomes, command results, denominators and
source hashes. Correct any earlier claim that all gate/evidence obligations were
already closed. End READY_FOR_REVIEW with the exact handoff path. Only Codex may
accept the implementation.
