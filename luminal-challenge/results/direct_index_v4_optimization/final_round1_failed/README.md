# Final phase, round 1 — FAILED, retained

All 1,500 extra-corpus measurements completed, then the aggregation step raised
`KeyError: 'additional_211945'`: `analyse` tried to compute an official combined
score for the frozen evaluation corpus against the protected *serial* integers,
which only cover the eight public programs. The corpus has its own serial
integers in its manifest and is scored by `extra_score_distribution`.

The defect was in the harness's reporting, not in any measurement and not in the
compiler. No `runs.json` was written for this attempt, so there is no partial
result that could be mistaken for evidence. The fix makes `analyse` return an
explicit "no protected serial baseline for these programs" note instead of
indexing a dictionary it was never given.

Round 2 is in `../final/`. This directory is kept because the plan requires a
failed attempt to be retained rather than overwritten.
