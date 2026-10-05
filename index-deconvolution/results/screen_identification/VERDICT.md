# VERDICT — identification screen

**NARROW**, applied as PROTOCOL §4 defines it. Every number below is computed by `experiments/screen_s6_report.py`; the tables are in `table.md`.

## Gates

- **H1 (S2 headroom).** The best competitor needed at most 2 × Q_LB queries on 1/15 networks at n ≥ 50. Headroom exists: identification by queries is not near-optimal. Our arm: none exists.
- **H2 (S3a one-step).** Answered, verified and under 1 s on all 15 questions at n = 200 by bdd: no headroom. Our arm: index-based (exact_query_representation).
- **H2 (S3b fixed).** Answered, verified and under 1 s on all 5 questions at n = 200 by pyboolnet, boolnet: no headroom. Our arm: none exists.
- **H2 (S3b attr).** No competitor answered all 5 questions at n = 200 under 1 s with a verified answer: headroom. Our arm: exhaustive (num_attractors).
- **H2 (S3b reach).** Answered, verified and under 1 s on all 10 questions at n = 200 by z3_bmc: no headroom. Our arm: none exists.
  - S3a, time and size against CUDD at n = 200 (H2 moves the comparison there): T1: ours faster on 5/5, smaller on 5/5; T2: ours faster on 4/5, smaller on 3/5; T3: ours faster on 0/5, smaller on 0/5.
- **H3 (our standing in S1).** `deconvolve` was at least as fast as the best exact competitor on 26/27 networks at n ≤ 20.

## Verdict rule applied

- H1 shows no headroom: **False**. H2 shows no headroom (all classes): **False**.
- Headroom found in: **S2, S3b attr**.
- Our arm in each of those: S2 → none exists; S3b attr → exhaustive (num_attractors).
- STOP needs no headroom under H1 and H2; NARROW needs headroom only where our arms are exhaustive or do not exist; GO needs headroom where an existing arm already leads.
- Result: **NARROW**.
