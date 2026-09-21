# Final lead review: direct-index optimization and evidence repairs

Date: 2026-09-20. Reviewed commit: `1cf98da` (compiler unchanged from `bb88b31`).
Verdict: **ACCEPTED WITH LIMITATIONS** for the local implementation and empirical
evaluation. All reviewed blocking findings are closed. No production code was
changed in this review. Publication, novelty and private-grader success are not
implied by local acceptance.

## Finding closure

- Original R1 deadline repair and R2 benchmark exit-status repair remain valid;
  neither production compiler nor benchmark runner changed in this round.
- F1 is closed: public interval settings are fixed at 10,000 paired resamples
  and seed 20260920, declarations are checked, and the relaxation option was
  removed. The lead independently replayed a mathematically self-consistent
  one-resample mutation; it now fails protocol and interval checks. Wrong-seed
  input also fails. The complete unmodified worker tree passes.
- F2 is closed: all nine test stages and three acceptance steps are mandatory,
  with log/count checks, corpus evidence and CLI membership. The lead's deletion
  leaving only schema and corpus now fails five checks. Complete fresh evidence
  passes. The new regression fixture supplies the full contract.
- Reporting corrections distinguish composite score, compilation time,
  between-run variation, and unestablished causal explanations. No remaining
  concrete blocker was found in this reviewed scope.

Probes and their results: `lead_review/probes.py`, `lead_review/probes.json`.

## Fresh lead runs

All commands below completed with exit 0, run serially so performance experiments
did not compete with another verification/benchmark process started by the lead.

| Check | Fresh result |
|---|---|
| Complete verifier | 340 direct tests; 11 unchanged public tests; 142 isolated programs / 277 cases; CLI 8/8; PASS |
| Official comparison | 72 exact measurements; all seven gates PASS |
| Paired public timing | Five arms, 15 repetitions, 600 rows; no failures |
| Frozen extra evaluation | 100 programs, five arms, three repetitions, 1,500 rows; no failures |
| Evidence audit | 50 checks PASS, including hashes, interval protocol, full verification and underlying artifacts |
| Independent recomputation | Exact row membership, source hashes, frozen export and timing aggregates/intervals agree |

The final candidate export has 2,652 lines and SHA256
`d14bf39b450aaa5fe73c41a3236980e219089e527ae43007781d78e0059a5864`.
The frozen export SHA256 is
`c0574395d339dae3b24e819955795c2a6165953c5966e46062c9bf9b18a50ce2`.
Full source/test provenance is in the fresh verification and timing JSON files.
Four protected controls and pinned reference commit
`573b8a85f4bdb8c3d8ba9f180d5f98dac875c902` were verified unchanged.

## Results and limits

Public combined score: direct **2.008466202284657**, classical
**1.9013791212645499**, serial 1.0. The direct score is about **5.63% higher than
this classical implementation's score**, not 5.63% faster program execution.
Candidate and frozen cycles/scratch agree on every measured program/repetition,
in both public and extra evaluation data. There are no new score regressions.

Primary performance statistic: geometric mean of per-program median baseline
time / candidate time. Fresh lead results, independently recomputed:

| Mode versus frozen v3 | Speedup | Paired within-run 95% interval | Engineering target |
|---|---:|---|---|
| Full compiler | 2.132005693x | [2.126779601, 2.137538179] | 2.00x met in this run |
| Bootstrap | 1.162943978x | [1.147124692, 1.168961407] | 1.20x not met |

Keep earlier results in the paper's reproducibility discussion: the worker's
latest run was 1.9471x full and 1.1337x bootstrap using the same compiler. The
fresh run crossing 2.00x does not erase prior misses or establish that the target
will be met reliably. Within-run intervals do not cover between-run variability.

Pooled median compile times, a **different statistic**: classical 0.26927 ms,
candidate bootstrap 0.54962 ms, candidate full 155.80323 ms. Their ratios are
about 2.04x and 578.61x slower than classical. Direct remains slower overall;
do not treat its score improvement or v3-relative speedup as runtime superiority
to classical. Classical-relative timings have varied across rounds, including
two previously anomalous public-program medians; their cause is not established.

Extra-corpus composite score geomeans: classical 2.370890261, bootstrap
2.362098438, full 2.376596963. The optimizer accepts 18 improvements over three
repetitions (six distinct improved programs), equally for frozen and candidate.
It is useful on some generated programs despite adding no public-score gain.
The corpus shares a generator with development inputs and is not a sample of
all real compiler workloads.

Implementation acceptance does not prove global optimality, compactness for
arbitrary Boolean networks, polynomial complexity, a general advantage over
compiler optimizers, or performance on the unavailable private grader. Query
UNSAT remains local and deadline exhaustion remains UNKNOWN. Baseline heuristic
differences prevent assigning the score benefit solely to index representation.

## Reproduction

From `luminal-challenge`, the exact commands used were:

```sh
PYTHONPATH=.reference python3 verify_direct.py --stage all --timeout 20 --output results/direct_index_v4_optimization_repair2/lead_review/verification
PYTHONPATH=.reference python3 compare_direct.py --repeats 3 --timeout 20 --output results/direct_index_v4_optimization_repair2/lead_review/comparison
PYTHONPATH=.reference:. python3 benchmark_optimization.py --phase final --baseline results/direct_index_v4_optimization/baseline --repeats 15 --seed 20260920 --output results/direct_index_v4_optimization_repair2/lead_review/final
python3 check_optimization_evidence.py --root results/direct_index_v4_optimization_repair2/lead_review --baseline results/direct_index_v4_optimization/baseline
python3 results/direct_index_v4_optimization_repair2/lead_review/audit_measurements.py
python3 results/direct_index_v4_optimization_repair2/lead_review/probes.py
git diff --check -- luminal-challenge
```

Use new output paths when repeating measurements; preserve this evidence.
Independent audit output is `lead_review/measurement_audit.json`.

## Paper readiness

**Ready to draft a rigorous compiler case-study paper.** No additional speed
campaign is required before writing. The claims/evidence map and proposed
manuscript structure are in `../../paper/CLAIMS_AND_EVIDENCE.md`. Before
publication, verify related work and novelty, write and review mathematical
arguments, derive tables from accepted artifacts, and retain negative results
and limitations. This is a writing readiness decision, not publication approval.

Source changes after these recorded hashes require the plan's affected reruns.
