# Codex review — gap-ranking-v1-r1

Decision: **ACCEPTED — exploratory evidence, VALID_COMPLETE.**

The delivered study satisfies the finite Track G computation and endpoint contract. No blocking correction is requested. This review supersedes the pending-review status for this run without modifying its frozen handoff, reports, sources or evidence. Acceptance does not promote the heuristic, integrate the sibling dependency, or authorize another experiment.

## Evidence checked

- Read the delegation protocol and ownership/import contract, handoff, report, decision, producer, score/rank code, import guard, joiner, independent audit and dependency patch.
- Independently verified all 50 frozen-file hashes, all 30 expected-input hashes and all 83 output-manifest entries. The untracked historical results_d.jsonl matches its trusted SHA-256, 7119aa72f6483e955aa1033cbde7d0ef144f34ea8a614a03ba66830354ad0e12.
- Re-ran the independent audit against the delivered bytes: VALID_COMPLETE, zero failures and missing records; 24 trajectories, 1,536 transitions, 8,368 occurrence records, 180 scores, 2,510 rank positions and 20 endpoints. All three deliberate corruptions were caught by the intended checks.
- Re-ran the combined scoped suites: **120 passed in 1.82 s** (73 accepted regression tests, 32 focused tests, 15 dependency tests), with bytecode and pytest cache disabled. Reviewed the six mutation results: relevant assertions failed, without collection errors.
- Ran run.sh into a fresh /tmp directory. All eight deterministic production artifacts and audit.json match byte for byte. cost.json contains fresh timings and is explicitly excluded from byte equality. “Every output byte for byte” must be read with that timing exception; the report's eight-file formulation is accurate.
- Added independent supplemental checks for exact cell sets, duplicate-free orders, all six unavailable cells' null fields, all FULL memberships, first-hit identities, reduced exact expectations, both descriptive summaries, all constant-evidence flags, and score metadata. These pass; see review_check.py/json.
- Inspected the reported preservation comparison (109,754 unchanged files). This review independently re-hashed the manifests above, not the full 109,754-file tree. The late before-snapshot cannot retrospectively certify pre-development preservation; that limitation is retained.

## Accepted interpretation

Of 14 cells containing a FULL candidate, gap ordering is earlier than the exact random-order expectation in 5 and later in 9. Against canonical order it is earlier in 12 and later in 2. The other 6 cells have no FULL reference. These are descriptive comparisons with an expected rank, not win probabilities against every random ordering or a population significance result.

There are four known constant-dynamics first hits overall, all in M3; two of these are among the five cells earlier than the random expectation. The remaining first hits are not characterised by the supplied supplemental dynamics evidence. FULL continues to mean validity under the declared model, interventions and grouping, not usefulness.

Canonical ordering mechanically puts F3 after the lossy F1 candidates. That explains the weak baseline and the exact all-score-tied cases; the study does not isolate how much of every other advantage is caused by that arrangement. Likewise short trajectories and score saturation are observed together here, not established as a general causal law. These qualifications govern the report's explanatory wording.

Recommendation: **do not adopt this gap ordering as an improvement, and do not automatically tune it.** This is a research-priority decision based on the delivered population, not a proof that recurrence features can never help. The validated grouping checker remains useful for testing explicit grouping hypotheses. The study provides no new compression, nesting, fractal or biological result.

## Disclosures and integration decisions

1. The synthetic pre-freeze join read saved non-F3 dynamics evidence. This is disclosed, and researchers already knew outcomes. The protocol is explicitly exploratory. Inspection of the producer and the successful guarded reproduction support the narrower claim that the scoring process did not use outcome labels; there is no claim of human blinding.
2. The guard covers opens/listings/process creation, not metadata, and is a process guard rather than an adversarial sandbox. No scientific computation in the inspected scoring path depends on outcome metadata. This does not invalidate this run.
3. The late preservation snapshot limits the preservation claim as described above. It does not invalidate the source identities actually frozen and rechecked.
4. The isolated token extractor is accepted for this run. **Do not apply upstream.patch to the active sibling as part of this acceptance.** The old pinned operator-group hash is a versioned scientific contract; changing the active registry needs an explicit migration, tests for the new identity, and preservation of the old identity. This negative ordering result creates no immediate need for that migration.
5. Commit 3e78e6f0 exists and has no co-author trailer. This review does not review or endorse every unrelated change in that broad commit. The large historical input remains available and hash-verified locally, but a clean checkout alone cannot reproduce this study until that input is supplied through the repository's approved artifact mechanism. Do not equate local reproducibility with a self-contained Git release. No commit, upload or publication is authorized by this review.

## Next decision

Track G is complete. No correction delegation or successor execution protocol is warranted by these results alone. A new scientific phase should first name a concrete task that a compacted state must preserve (a specified output, intervention response or prediction), and define usefulness separately from validity. It needs a named model/data source, an observation/intervention contract and a falsifiable comparison before implementation. Simply changing trajectory length, tie rules or recurrence scores after seeing this result would be a new exploratory design, not confirmation of this one.

For now retain the accepted checker, the negative scheduling evidence and the isolated dependency snapshot. No follow-up phase was launched and no active or frozen scientific file was changed during review.

## Review provenance

Review began 2026-10-05 17:59:15 UTC. The time record is in review_ledger.json; a conservative charge is used within the 300-second supervisor reserve. One supplemental-check attempt failed before reading study evidence because ROOT used parents[6] instead of parents[5]; the path was corrected and the successful check is retained. This was a supervisor harness setup error, not a study failure. The audit, tests and fresh reproduction passed on their first supervisor runs.
