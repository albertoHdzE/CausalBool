# Recovery implementation: interim lead review

2026-09-23. **CHANGES_REQUIRED before a replacement campaign.** This review
does not accept any comparative result. Reviewed the source identified by
`recovery_diagnosis_20260923/FINAL_IMPLEMENTATION_MANIFEST.json` and the first
campaign's available artifacts. Findings below are source-inspection findings
unless explicitly identified as observed at runtime. No competing timing run
was started by the lead.

The diagnosis is supported by retained prefix traces and bootstrap round trips:
the original random sampler has severe rank rejection and horizon dead ends.
Supplemental physical-object coverage is a separate adequacy diagnostic, not a
repair to random sampling or evidence of faster optimization. P2's 1,800-row
artifact is provisional pending complete independent checking.

## Required repairs

1. **P4 worker identity (observed crash).** The first model worker completed,
   but Harness.run indexed missing `program_sha256` in a fixture-keyed spec.
   Handle fixture/program identities consistently in measurement records,
   journal, commands, worker acceptance and checker. Add a regression through
   the actual harness with a model result; do not just test a dictionary helper.

2. **Wrong primary corpus and estimand.** build_recovery_comparison designates
   public/P2 as primary H2. The frozen primary is held-out P5 structural_bound
   versus accepted_budgeted at 0.1 seconds. Public results are descriptive.
   `_quality_table` then log ratios computes log of arithmetic mean products;
   the required endpoint averages paired log ratios over matching technical
   repetitions, then seeds, then programs. Repair the shared analysis owner,
   maintain full pairing identities, and test a varying-product example where
   the two estimands differ. Null-crossing intervals are not equivalence.

3. **Supplemental deadline enforcement/accounting.** physical_probes.run checks
   time only before each physical proposal. It never produces INTERRUPTED and
   can count a candidate whose validation/round trips cross the deadline.
   Check the shared absolute deadline between expensive operations and after
   validation, retain partial work/counters, count no partially validated object
   toward coverage, and report overshoot independently of exhaustion/cap status.
   Record pinned validation/case work for each codec as specified, with regressions
   forcing expiry during case checking and during a codec round trip.

4. **Missing diversity and integrity evidence.** The required unique issue-time
   vectors, address maps, changed-field counts and C/S/J ranges are absent.
   Report them for individual streams and union, and recompute independently.
   Validate exact physical-summary program membership, roundtrip totals, elapsed
   chronology, budgets and stopping reason; do not accept duplicate/omitted
   summary members or erased counters. Keep original and amended coverage
   dispositions separate and derived from their respective identity sets.

5. **Incomplete mutation test matrix.** Four recovery plumbing tests do not
   fulfill section 8. Cover removed/duplicated/forged physical rows, invalid
   physical candidates relabeled complete, erased case/codec counts, false
   original/amended PASS, absent/mismatched policy and imported policy, missing
   or budget-duplicated classical rows, worker crashes, and forged comparison
   statistics/primary budget. Use bounded fixtures; these should not rerun a
   full public campaign per mutation.

6. **Durable partial evidence.** Harness/run buffers measurement rows and
   commands until corpus/run completion. Add append-and-flush durable row and
   command journals as each worker exits; retain them across errors and orderly
   interruption. Final membership must reconcile journal and stage artifacts,
   including failed model workers. A list of worker exit lines is not a
   reconstructible replacement for raw measurements. Test interruption after
   one worker and missing journal records. Do not retrospectively fabricate
   missing measurements from the first campaign's logs.

7. **Previously unexecuted P4 inference and budgeting.** `p4_contrasts` also
   logs ratios after averaging raw products, rather than aggregating paired
   logs across repetition, seed, fixture variant and semantic program. Its
   deterministic arms must be paired analytically against stochastic seeds
   without inventing extra measurements. `run_model_measurement` gives cover
   construction the independent ten-second cover allowance instead of the
   remaining optimization allowance, does unmetered decoding, and can credit
   discoveries after expiry. Enforce the existing shared-budget contract,
   retain interrupted work, report oracle preprocessing separately, and test
   expiry during cover/decode/evaluation. P4's grouped arm execution must also
   obey the frozen balanced order rather than measuring an entire arm first.
   These are corrections to the already specified experiment, not new model
   policies or expanded budgets.

## Execution disposition

Lead authorized orderly termination of the first campaign to repair these known
defects before spending another full measurement matrix. Preserve every existing
artifact, source manifest and log and mark ABORTED_FOR_REPAIR with actual progress
and any missing partial rows. This is a correctness/evidence interruption, not
selection based on favorable performance. Confirm the runner and its worker
descendants have stopped before changing measured source.

Implement all repairs, run required tests and obtain lead pre-campaign review.
Then freeze a new source manifest and use a fresh `_r2` run. Do not edit the
frozen policy, weaken scientific gates, reduce repetitions, or change candidate
heuristics. The unchanged independent H3/H4 gates may legitimately produce a
negative or inconclusive outcome.
