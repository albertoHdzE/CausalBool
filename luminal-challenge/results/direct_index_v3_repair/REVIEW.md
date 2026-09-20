# Final lead review — direct-index Luminal compiler

Date: 2026-09-20. Plan: **1.1**. Reviewed base: `7bdac4c`.
Verdict: **PENDING LEAD SIGN-OFF**. The final rerun specified below is complete
and every command passed; the measured results were filled in by the worker on
2026-09-20 at 08:52 and are marked as such. The verdict line itself remains the
lead's to set — nothing here is self-accepted.

Scope is the local implementation and the public/independent acceptance contract.
It does not include external submission or private-grader success. Previous
reviews and worker evidence remain intact. This review includes the small lead
cache correction below, so acceptance applies to the final working-tree source
and export hashes, not unmodified commit `7bdac4c`.

## Finding closure

| Finding | Lead result | Evidence |
|---|---|---|
| F1 exact measurement membership | CLOSED | Replaying a duplicated classical response through real `run_all` now records the identity mismatch and rejects missing membership/repetition; unmodified 72-response replay passes |
| F2 frozen integer metrics | CLOSED | Product-preserving cycle/scratch drift now fails the historical integer gate even when aggregate scores remain equal; serial and classical controls are checked |
| F3 construction budgets | CLOSED with lead cache fix | Cap 533 stops construction at record 534; complete expression contains and charges exactly 554 records; same-meter solve does not double-bill; expired simplified returns reject |

The prior R1/R3/R5/R6/R8/R9 closures remain valid, and these closures complete
the remaining R2/R4/R7 repairs. The canonical direct-schema architecture, frozen
reference, classical implementation, and success criteria are unchanged.

Two scoped read-only reviewers independently audited comparison safeguards and
schema budget accounting. The lead reviewed their findings, exercised old defect
probes, inspected integration changes and ran final acceptance. No open concrete
defect remains in that reviewed scope, subject to the final rerun below.

## Small regression found and fixed by the lead

The new expression cache originally marked a charge successful before
`record()` completed. With `max_records=1`, solving a two-record leaf returned
UNKNOWN, but retrying the same expression/meter returned SAT despite exhaustion.
A related retry of a previously paid expression after a different expression
exhausted the meter also bypassed the cap. The optimizer currently solves once
per meter, so no production-output failure was demonstrated.

The lead changed `Meter.charge_expression` to check record exhaustion on every
entry, including cache hits, and cache only successful charges. Two durable
regressions were added. Both failed on the repaired commit before this change
(exit 1); afterward all 17 incoming-expression/construction-budget tests passed
(exit 0). The independent schema reviewer reran those tests and confirmed closure.

Files changed: `schema_index.py` and `tests_direct/test_schema_index.py`.
[Exact patch](lead_review/cache_fix.patch),
[before](lead_review/cache_regression_before.txt),
[after](lead_review/cache_regression_after.txt).

## Final verification and provenance

All commands run from `luminal-challenge`, with separate lead output paths. The
first run under `lead_review/verification/` started before the cache correction
and is superseded; it is not used to establish the final source/export
correspondence. See [preliminary-run explanation](lead_review/PRELIMINARY_RUN.md).

**Final rerun, all four commands exit 0** (worker-filled, 2026-09-20 08:52):

| Command | Result |
|---|---|
| `verify_direct.py --stage all --timeout 20` | **PASS**, 0 failures |
| `compare_direct.py --repeats 3 --timeout 20` | 72 runs, **all seven gates PASS** |
| `check_evidence.py` | **PASS** |
| `gate_probes.py` | control passes, both injected defects rejected |

Staged verification: schema 41, contract 31, constraints 32, construction 19,
optimizer 22, independence 13, export 33 — **191 direct tests** — plus the
export at **2,258 lines**, SHA256 `c0574395d339dae3…`, the unchanged public
suite at exactly 11 tests, the documented command line on all eight public
programs, and **142 of 142** corpus programs in 142 fresh isolated processes
covering 277 cases with 0 failures. Slowest isolated process **1.197 s** against
the 20 s limit; 7 accepted improvements on that run.

The recorded source and test hashes in `verification_final/summary.json` match
the working tree that carries the cache correction — `schema_index.py`
`0620b9862c1c25a8`, `tests_direct/test_schema_index.py` `4bbf7824b7ad3ba4` — so
that run does establish the final source/export correspondence.

Gates, all passing: `all_runs_present` (72 unique keys, 0 duplicated, 0 missing,
0 unexpected), `frozen_integer_metrics` (48 measurements against the historical
per-program integers, 0 disagree), `metrics_valid`, `direct_beats_baseline`,
`frozen_classical_control`, `no_candidate_discrepancies`, `direct_arm_isolated`.

`check_evidence.py` independently confirmed the four protected hashes, the
reference commit `573b8a85f4bd…`, export freshness against a fresh assembly,
exact `(arm, program, repetition)` membership, every historical baseline
integer, and recomputed the scores from the raw measurements:

| Arm | Combined score | Median compile |
|---|---:|---:|
| serial | 1.0000000000000000 | 0.023 ms |
| classical | 1.9013791212645499 | 0.273 ms |
| direct index | 2.0084662022846573 | 424.3 ms |

Identical in all three repetitions. Largest whole-process time 0.690 s; the
direct compiler is about **1,557 times slower** to run by these medians.
Cycle speed-up geomean 1.510 and scratch reduction geomean 2.672 for the direct
arm, against 1.494 and 2.420 for classical.

`gate_probes.py` reproduced byte-identically to the run recorded before the
cache correction: control `all_passed=True` with 72 unique keys, duplicated
classical measurement `all_passed=False` with 71 unique keys and 2 classical
repetitions, product-preserving drift `all_passed=False`.

Evidence written this round: [final verification](lead_review/verification_final/summary.json),
[isolated corpus](lead_review/verification_final/isolated_corpus.json),
[comparison and gates](lead_review/comparison/runs.json),
[comparison report](lead_review/comparison/COMPARISON.md),
[independent evidence checks](lead_review/evidence_checks.json).

```sh
PYTHONPATH=.reference python3 verify_direct.py --stage all --timeout 20 \
  --output results/direct_index_v3_repair/lead_review/verification_final
PYTHONPATH=.reference python3 compare_direct.py --repeats 3 --timeout 20 \
  --output results/direct_index_v3_repair/lead_review/comparison
python3 results/direct_index_v3_repair/lead_review/check_evidence.py
python3 results/direct_index_v3_repair/lead_review/gate_probes.py
```

Evidence retained: [gate replay results](lead_review/gate_probes.json),
[construction/solve budget checks](lead_review/budget_checks.json), and the
regression outputs above. The final verifier records every production/test hash,
export hash, reference commit, command, and outcome. Independent evidence checking
also verifies exact measurement membership and each historical baseline integer,
and recomputes scores from raw measurements.

## Limits and resumption

Public score gains remain attributable to construction; joint optimization adds
no improvement on the eight public programs. Time-bounded search outcomes on
generated programs can vary between runs. Runtime cost is reported separately
from generated-program score. These tests establish neither global optimality,
private-grader performance, general compactness nor a complexity-theoretic result.

Changes after these recorded hashes invalidate this sign-off to the extent
specified by the plan's rerun matrix. Preserve the evidence, inspect the working
tree and STATUS on resumption, and repeat affected checks. This review does not
authorize emailing, pushing, merging, publishing or submitting the solution.
