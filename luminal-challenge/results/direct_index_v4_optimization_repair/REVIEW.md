# Lead re-review of optimization repairs

Date: 2026-09-20. Reviewed commit: `bb88b31e5ec2166bc9c34d5fd540edac7320b7db`.
Verdict: **CHANGES_REQUIRED**. R1 and R2 are closed. R3 is partially repaired:
two deterministic evidence-enforcement gaps remain. No production source was
changed by this review. Missed speed targets do not cause this verdict.

## Verified closures and results

- R1: the original deterministic deadline probe now returns UNKNOWN with
  `time budget exhausted` at elapsed 2.0, rather than UNSAT. The added post-cover
  and terminal checks address the reviewed path. In-budget tests pass.
- R2: the lead replayed a complete acceptance dataset, including the extra corpus,
  through actual `phase_final`. Clean control exits 0; product-preserving
  classical drift exits 1 with precisely the integer-control gate and aggregate
  gate failing. This isolates the repair from a diagnostic/corpus-skip failure.
- R3 original mutations now reject: missing extra corpus, missing hash maps,
  fabricated [999,1000] intervals, and product-preserving official integer drift.
  The unmodified retained evidence passes the checker.
- Fresh complete verification: exit 0, **300 direct tests**, 11 public tests,
  **142 isolated programs / 277 cases**, and CLI checks PASS.
- Fresh official comparison: exit 0, 72 measurements, all seven gates PASS.
  Direct score 2.008466202284657 and classical 1.9013791212645499 in all three
  repetitions. Retained in `lead_review/comparison/`.
- R4 retracts the impossibility claim, labels statistics, corrects row counts,
  and preserves prior evidence. Minor remaining interpretation corrections are
  below.

The worker reports full speedup 1.9536x and bootstrap 1.1380x relative to the
frozen v3 implementation. These are the worker's new retained measurements,
not fresh lead performance measurements. The lead deferred the complete
15-repetition timing experiment because deterministic evidence gates still fail.
No generated-code error was found in this review.

## F1 — P2: the report still controls its own confidence-interval protocol

Location: `check_optimization_evidence.py:543–544`.
The checker takes resample count and interval seed from the reported interval,
rather than enforcing the plan's 10,000 resamples and seed 20260920. It therefore
recomputes a weakened experiment consistently instead of rejecting it.

Reproduction: replace each public interval with a correctly recomputed interval
using **one resample**, leave its reported `resamples=1`, and run the full checker.
It returns **all_passed=True**. The checker even describes the check as 10,000
resamples in its output, although it executed the report's count.

Repair acceptance criteria:

1. Require the fixed public resample count, seed and paired protocol before
   computing intervals. Verify top-level and per-interval declarations agree.
   A CLI option must not relax an acceptance check; if retained for diagnostics,
   such runs cannot return acceptance success.
2. Recompute intervals and target decisions from raw rows using the fixed
   contract. Require complete target fields; do not let an omitted target
   declaration quietly bypass comparison.
3. Regression: the one-resample mutation must exit nonzero even when its bounds
   are mathematically correct for that reduced count. Include wrong-seed and
   missing protocol-field cases. The complete unmodified dataset must pass.
4. Report the actual enforced settings, not a nominal argument ignored in favor
   of report-controlled values.

## F2 — P2: required verification stages can be removed without rejection

Location: `check_optimization_evidence.py:804`; test fixture at
`tests_direct/test_evidence_checker.py:72`.
The checker requires some positive test count plus the corpus totals, but no
complete stage membership. Removing contract, constraints, construction,
optimizer, independence, export, benchmark, evidence, public suite and CLI from
the recorded verification leaves **all_passed=True** if schema and corpus remain.

The evidence tests construct this very two-record summary as their supposedly
correct fixture. That fixture masks the omission rather than exercising a full
verification contract. This does not mean the worker skipped those actual tests:
both the retained full run and the lead's fresh full run contain them and pass.

Repair acceptance criteria:

1. Require exactly one record for every declared test stage, plus corpus,
   public_suite and CLI acceptance records. Reject missing, duplicated and
   unexpected stage/step identities, any failures, and incomplete status.
2. Require nonzero tests in every test stage and exactly 11 public tests. Check
   the full isolated corpus and CLI expected program/case membership from the
   retained artifacts, rather than accepting only summary totals. Check command
   outcomes and referenced logs consistently with the summary.
3. Replace the two-record positive fixture with a complete fixture. It need not
   read the still-running verifier's summary: create all required records and
   supporting fixture artifacts explicitly, with realistic success/failure cases.
4. Add entry-point regressions for removal of each required stage, a duplicate
   hiding a missing stage, zero-test stages, missing public/CLI checks, and absent
   or failing underlying acceptance evidence. Require nonzero exit.

## Reporting refinements

- The handoff says both speedups fell; bootstrap changed from 1.1371x to 1.1380x
  and did not fall. The ~1.8% full change is a cross-run observation. Added clock
  reads plausibly contribute, but these runs do not isolate their causal cost.
- The two anomalous classical medians are disclosed, which is appropriate.
  Their cause has not been established. Describe observed timing variation,
  rather than asserting a diagnosed machine-load explanation. Keep comparisons
  specific to their run and statistic.

## Reproduction and remaining handoff

From `luminal-challenge`:

```sh
python3 results/direct_index_v4_optimization_repair/lead_review/probes.py
python3 results/direct_index_v4_optimization_repair/lead_review/phase_exit_probes.py
```

Outputs: `lead_review/probes.json`, `lead_review/phase_exit_probes.json`.
These mutate data in memory and use temporary replay output; worker evidence
and production files remain untouched. `probes.py` records checker verdicts:
control True, original four corruptions False, one_resample True,
missing_verification_stages True, expired_final_cover UNKNOWN.

Make a bounded evidence-only repair to F1/F2 and reporting. No further speed
experiments, policy changes or production optimizer edits are requested. Preserve
all earlier evidence; use a new repair result directory. Retain failing-before
regressions and passing-after entry-point tests. Run the full verification,
official comparison and declared final performance protocol against the same
frozen baseline after finalizing script hashes; checker/harness edits are part of
the provenance contract. Update STATUS and hand off READY_FOR_REVIEW with actual
commands, exits, hashes and results. Only the lead accepts.

The paper remains deferred pending completion of these narrow repairs.
