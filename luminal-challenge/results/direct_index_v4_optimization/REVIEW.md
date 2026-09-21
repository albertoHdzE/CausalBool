# Lead review of runtime optimization

Date: 2026-09-20. Reviewed HEAD: `91be105`. Plan: optimization v1.1.
Verdict: **CHANGES_REQUIRED**. No production source was edited in this review.
Worker artifacts are preserved. V3 remains the accepted historical baseline.

The performance work is useful and the missed targets are reported honestly.
Neither missing the 2.0x/1.2x targets nor remaining slower than classical is the
reason for withholding acceptance. Three reproducible contract/enforcement
defects below are blockers; reporting corrections are also required.

## Independent verification

- Fresh `verify_direct.py --stage all --timeout 20`: exit 0, 253 direct tests,
  11 public tests, 142 isolated corpus programs / 277 cases, CLI checks PASS.
- Fresh `compare_direct.py --repeats 3 --timeout 20`: exit 0, 72 exact rows,
  all seven gates PASS; direct score 2.008466202284657, classical
  1.9013791212645499 in each repetition.
- Independent raw-data audit: 600 public and 1,500 extra-corpus rows have exact
  expected membership and successful recorded validation. Candidate and frozen
  cycles/scratch agree for both modes on every recorded program/repetition.
  Frozen export SHA256 matches the accepted v3 hash; recorded production hashes
  match the current source.
- Independently recomputed public speedups and paired 10,000-resample intervals:
  full **1.9889475815x [1.9841045946, 1.9913193097]**; bootstrap
  **1.1371215179x [1.1334298336, 1.1405957976]**. These reproduce the worker's
  retained measurements; they are not a fresh 15-repetition timing run.

Evidence: `lead_review/verification/`, `lead_review/comparison/`,
`lead_review/measurement_audit.json`, `lead_review/probes.json` and their scripts.
The full fresh performance/corpus experiment is deferred until repairs: the
current candidate already fails deterministic acceptance probes. A final timing
rerun is required after production repair; retained worker timing is historical.

## R1 — P2: deadline bypass on the final conflicting cover

Location: `schema_index.py:911` and `schema_index.py:934`.
The new batched intersection checks time before scanning a cover. If that cover
has no survivors and exhausts the last stack item, solve returns UNSAT without
another clock check. The rationale that every popped state checks time does not
cover this terminal path.

Reproduction: `python3 results/direct_index_v4_optimization/lead_review/probes.py`.
A deterministic clock advances past a one-second deadline after the final
cover's initial check. Result: **UNSAT, elapsed=2.0**, rather than UNKNOWN.
This is a resource-contract violation; it does not demonstrate an incorrect
logical UNSAT answer or a bad generated program.

Repair: check time after bounded scans and before terminal verdicts. Review all
new batched paths. Add durable deterministic regressions for the final
all-conflicting cover, exhausted terminal branches, and valid in-budget answers.
Keep visit/record caps and search order unchanged. Demonstrate that deadline
check granularity is bounded and never certifies a completed result after
observing exhaustion. Rebuild export and rerun the full matrix.

## R2 — P2: benchmark detects a failed control but exits successfully

Location: `benchmark_optimization.py:1375`, `:1450`, and the baseline return path.
`phase_final` returns success based only on membership, ignoring its historical
integer-control result. It also records a frozen-export linkage mismatch without
rejecting it before measuring.

Reproduction replays real rows through actual `phase_final`, doubles classical
cycles and halves scratch (product preserved), and retains valid identities.
The resulting report detects **90 historical integer discrepancies** but the
phase returns **exit 0**. This is the same category of missing release-path
enforcement repaired previously; helper-level rejection alone is insufficient.

Repair: define and enforce a complete mandatory-gate conjunction for baseline
and final phases. Reject provenance/snapshot mismatch before measurements;
enforce membership, row validity, frozen integer controls, per-program product
nonregression, bootstrap metric equality and score floor. Required extra-corpus
evaluation cannot silently disappear from an acceptance run; diagnostic skips
must be labeled non-acceptance. Missed engineering speed targets remain reported
outcomes, not correctness failures. Test actual phase/CLI exit codes with injected
failures and retain the rejected evidence.

## R3 — P2: evidence checker accepts missing or corrupted evidence

Location: `check_optimization_evidence.py:96`, `:289`, `:365`.
The checker trusts several report assertions and does not audit the extra corpus.
The lead's independent real-data audit found no such corruption in the retained
run, but the claimed rejection safeguards do not exist.

The reproducible probes each leave `Checker.run()['all_passed'] == True`:

- remove the entire final extra-corpus payload;
- erase final source and test hash maps;
- replace every reported confidence interval with [999, 1000];
- change an official classical measurement's cycles/scratch while preserving its
  product and leaving the stored PASS flags intact.

Snapshot linkage is accepted from a stored boolean rather than independently
hashing and comparing the files. Benchmark expected arms/programs/repetitions
are also derived from the report being checked, permitting a reduced contract.

Repair: require exact manifest field/key coverage and fixed expected arms,
programs and repetition counts from the plan and pinned inputs. Hash actual
frozen/candidate exports and all required sources/tests, including the benchmark
and checker scripts; verify assembly correspondence. Recompute official controls
and scores from every raw row, not stored gate flags. Audit all extra-corpus
inputs/hashes/rows/cases and recompute distributions. Recompute confidence
intervals and target decisions from raw timings with the declared seeds. Check
positive finite timings and the per-program gates from R2. Test each listed
mutation through the checker entry point with nonzero exit required.

## R4 — reporting corrections required

- Withdraw “Ruled out: further constant-factor work on the search.” This phase
  itself shows queries migrating from time to count limits and some completing.
  It supports remaining bottlenecks under current limits, not impossibility of
  future speedups or an inherent wall of the method.
- Separate geometric means of per-program ratios from pooled medians. For the
  retained data, inverse full/classical geomean is about 709.18, whereas
  171.1/0.264 pooled milliseconds is about 648; neither calculation is 714.
  Bootstrap inverse geomean is about 2.1396, while pooled is about 2.17. Derive
  displayed ratios from unrounded raw data and label the statistic.
- The 82.5%/1.21x ceiling is a heuristic from aggregated medians and a fixed
  timeout assumption, not an established decomposition/lower bound. Label it
  illustrative or replace it with a per-run measured attribution.
- Correct the claim of 2,100 *direct* final benchmark rows: 2,100 includes the
  classical arm; there are 1,680 direct rows. Keep original measured JSON intact
  and append/supersede interpretation in repair reports.
- “All eleven gates pass” must be superseded by this review. Preserve the worker
  handoff as historical evidence rather than silently rewriting it.

## Bounded repair handoff

Worker owns R1 in schema/tests; R2 in benchmark/tests; R3 in evidence checker/tests;
R4 in a new repair handoff. Keep direct method, query policy and defaults fixed.
Write new results under `results/direct_index_v4_optimization_repair/`; preserve
v4 and lead evidence. Do not pursue more speed experiments or alter targets.

1. Reproduce the lead probes before edits. Add regressions that fail first.
2. Repair R1–R3 and reporting. Normalization or budget-accounting changes must
   preserve all original tests and both v3 expression-cache retry regressions.
3. Run full unit discovery, export, staged verification and official 3-repeat
   comparison. Rerun final paired performance with 15 repetitions and the frozen
   v4 baseline plus its 100-program evaluation corpus, using new output paths.
4. Run the repaired evidence checker on the new tree and mutation cases. It must
   support an explicit baseline path so repairs do not require overwriting v4.
5. Retain commands, exit codes, hashes, raw rows and changed target outcomes.
   Append STATUS and hand off READY_FOR_REVIEW; lead alone accepts.

Lead rerun commands already exercised from `luminal-challenge`:

```sh
PYTHONPATH=.reference python3 verify_direct.py --stage all --timeout 20 --output results/direct_index_v4_optimization/lead_review/verification
PYTHONPATH=.reference python3 compare_direct.py --repeats 3 --timeout 20 --output results/direct_index_v4_optimization/lead_review/comparison
python3 results/direct_index_v4_optimization/lead_review/probes.py
python3 results/direct_index_v4_optimization/lead_review/audit_measurements.py
```

Use new output directories for further runs. Review complete; the paper remains
deferred pending these repairs and final lead acceptance.
