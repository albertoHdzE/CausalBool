# Public comparison: serial, classical, direct index

Reference commit `573b8a85f4bdb8c3d8ba9f180d5f98dac875c902`, 3 repetitions per program, 72 measured runs, 0 failures.

| Arm | Cycle speedup | Scratch reduction | Combined (mean) | Combined range | Median compile ms | Max process s |
|---|---:|---:|---:|---:|---:|---:|
| serial | 1.0000x | 1.0000x | 1.000000x | 1.000000–1.000000 | 0.082 | 0.04 |
| classical | 1.4936x | 2.4204x | 1.901379x | 1.901379–1.901379 | 0.267 | 0.04 |
| direct_index | 1.5099x | 2.6717x | 2.008466x | 2.008466–2.008466 | 154.086 | 0.47 |

## Reading these numbers

The direct-index compiler scores 2.008466x against the classical arm's 1.901379x, so it is better on score.

It is slower to run: median compile 154.086 ms against 0.267 ms. The direct method answers exact queries, so a larger constant is expected.

Every recorded repetition of the direct arm scored above 1.0; the lowest was 2.008466x.

## Acceptance gates

| Gate | Result | Detail |
|---|---|---|
| all runs present | PASS | expected 72 unique (arm, program, repetition) keys over 8 programs, observed 72 rows and 72 unique; 0 duplicated, 0 missing, 0 unexpected, 0 execution failures; rows per arm {'serial': 24, 'classical': 24, 'direct_index': 24} |
| frozen integer metrics | PASS | 48 serial and classical measurements checked against the protected historical per-program integers; 0 disagree |
| metrics valid | PASS | 0 runs with non-positive or unvalidated metrics |
| direct beats baseline | PASS | direct combined scores per repetition: [2.008466202284657, 2.008466202284657, 2.008466202284657]; each must exceed 1.0 and all 3 must be present |
| frozen classical control | PASS | classical aggregates for repetitions [0, 1, 2] (all of [0, 1, 2] required): [1.9013791212645499, 1.9013791212645499, 1.9013791212645499], each within 1e-9 of the historical 1.9013791212645499 |
| no candidate discrepancies | PASS | 0 measured compilations reported a query/validator discrepancy |
| direct arm isolated | PASS | 0 direct runs loaded a prohibited module |
| all passed | PASS | every gate above |

## Limitations

- Eight public programs only; the private grader is unavailable.
- compile_seconds excludes interpreter start, imports and validation; process_seconds includes them and is what the 20 s limit governs.
- Peak resident memory includes the interpreter and its imports.
- No claim of global optimality follows from any of these numbers.

All raw runs, per-repetition aggregates, source hashes and failures are in
`runs.json`. Scores are relative to the frozen serial baseline on the eight
public programs. Nothing here speaks to the private grader.
