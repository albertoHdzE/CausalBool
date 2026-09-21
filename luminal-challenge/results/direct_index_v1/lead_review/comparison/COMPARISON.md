# Public comparison: serial, classical, direct index

Reference commit `573b8a85f4bdb8c3d8ba9f180d5f98dac875c902`, 3 repetitions per program, 72 measured runs, 0 failures.

| Arm | Cycle speedup | Scratch reduction | Combined (mean) | Combined range | Median compile ms | Max process s |
|---|---:|---:|---:|---:|---:|---:|
| serial | 1.0000x | 1.0000x | 1.000000x | 1.000000–1.000000 | 0.080 | 0.04 |
| classical | 1.4936x | 2.4204x | 1.901379x | 1.901379–1.901379 | 0.286 | 0.04 |
| direct_index | 1.5099x | 2.6717x | 2.008466x | 2.008466–2.008466 | 433.925 | 0.70 |

## Reading these numbers

The direct-index compiler scores 2.008466x against the classical arm's 1.901379x, so it is better on score.

It is slower to run: median compile 433.925 ms against 0.286 ms. The direct method answers exact queries, so a larger constant is expected.

Every recorded repetition of the direct arm scored above 1.0: the lowest was 2.008466x.

## Limitations

- Eight public programs only; the private grader is unavailable.
- compile_seconds excludes interpreter start, imports and validation; process_seconds includes them and is what the 20 s limit governs.
- Peak resident memory includes the interpreter and its imports.
- No claim of global optimality follows from any of these numbers.

All raw runs, per-repetition aggregates, source hashes and failures are in
`runs.json`. Scores are relative to the frozen serial baseline on the eight
public programs. Nothing here speaks to the private grader.
