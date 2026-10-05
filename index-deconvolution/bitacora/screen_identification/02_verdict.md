# Entry 02 — S1 complete; table and verdict

Date: 2026-09-29
Status: all four settings measured; verdict computed by script.

## S1 — full table (`s1_full_table.json`)

27 networks at n ≤ 20 (15 synthetic, 12 biological). `deconvolve` is exact on
27/27 (`verify_forward`). BoolNet REVEAL and best-fit are exact on 20/27; the
other 7 are timeouts (> 600 s per run): all five synthetic networks at n = 20,
and two biological models (n = 18, in-degree 4; n = 19, in-degree 8), even
though BoolNet was told the true maximum in-degree.

H3: `deconvolve` at least as fast as the best exact competitor on 26/27. The
exception is `bio/biomodels_MODEL1712240003` (n = 9): 0.118 s for ours against
0.007 s for BoolNet. Not yet examined; recorded as an open item.

## Verdict (`VERDICT.md`, `verdict.json`, `table.md`)

**NARROW**, applied mechanically by `experiments/screen_s6_report.py`.

| Place | Headroom? | Our arm there |
|---|---|---|
| S2 identification by queries | yes (1/15 within 2 × Q_LB at n ≥ 50) | none exists |
| S3a one-step questions | no (CUDD, verified, < 1 s at n = 200) | index-based |
| S3b fixed points | no (PyBoolNet, BoolNet) | none exists |
| S3b all attractors | yes (no tool answered all at n = 200 within 1 s) | exhaustive (`num_attractors`) |
| S3b reachability in 3 steps | no (Z3 bounded model checking) | none exists |

Headroom exists only where we have no arm or an exhaustive one: the niche
exists, we are not yet placed to fill it. Per PROTOCOL §4 the next step is a
written proposal for a query-mode or symbolic deconvolution, with its own
protocol. Nothing is built here.

## Qualifications that travel with the verdict

1. S2 headroom is measured against random sampling. Chosen-query
   identification (Akutsu 2003) has no software and was not run.
2. Z3 was run as a cross-check for reachability and then counted as a
   competitor. That is the conservative reading (it can only remove headroom);
   the verdict is NARROW under either reading.
3. The S3a size comparison measures the explicit-list output of
   `exact_query_representation`, not the method's schema form (entry 01, §6).
4. The corpus is the frozen one: synthetic in-degree ≤ 3, n ≤ 200. The
   author's request for n ≥ 300 and complex networks is a candidate amendment.

Figure (render of both gates' objects, one point per network or question):
`results/screen_identification/figures/s2_s3a.png`.
