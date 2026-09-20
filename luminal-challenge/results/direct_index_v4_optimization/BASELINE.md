# Baseline freeze — direct-index optimization phase

Worker record. Plan: [OPTIMIZATION_PHASE_PLAN.md](../../plan/OPTIMIZATION_PHASE_PLAN.md)
version **1.1**, section 3. Nothing here is accepted; only the lead accepts.

This baseline was measured **before any production source was edited**.

## Provenance

| Item | Value |
|---|---|
| Git commit | `8e02cd7f5b97085f71e99ba2e0e81dec6769d674` |
| Branch | `luminal-direct-index` |
| Immutable v3 source snapshot | `35d2608d0d2ed4fde47916b7df79c138b007908d` |
| Reference commit | `573b8a85f4bdb8c3d8ba9f180d5f98dac875c902` |
| Python | 3.13.12 |
| Platform | macOS-26.6.2-arm64-arm-64bit-Mach-O, 28 logical CPUs |
| Frozen export | `c0574395d339dae3b24e819955795c2a6165953c5966e46062c9bf9b18a50ce2`, 2,258 lines |

The working tree at `8e02cd7` differs from the accepted v3 snapshot `35d2608`
only in `AGENTS.md`, `plan/STATUS.md`, `results/direct_index_v3_repair/REVIEW.md`
and a new notebook — that is, in documentation the lead wrote after acceptance.
**No production or test source differs.** `git diff --stat 35d2608 -- luminal-challenge`
reports those four paths and nothing else.

## Source and test hashes, checked against the accepted v3 record

Every hash below was compared against
`results/direct_index_v3_repair/lead_review/verification_final/summary.json`,
the record the lead's final v3 rerun wrote. All **17 matched**; zero differ.

| File | SHA256 |
|---|---|
| `schema_index.py` | `0620b9862c1c25a82aa96885a87edb470e9e6dcf818122ae6f1c5b34ded3d2a3` |
| `direct_contract.py` | `3b37ad0e7f5feb8ac464b074ebd8e8c6ab079c79ada3ab1bacc4b2a9f1a83fa8` |
| `direct_constraints.py` | `7d34dbbddd3a2237b7f089024e1dd68e62ee96ce70d813540ef2e8fd9c860c90` |
| `direct_optimizer.py` | `bdbc0dd71b785d283cc7a64c36518dc13a4a0ba7673010ae274d0c69e787de68` |
| `direct_compiler.py` | `4b0c531d1d060af2a43ca4f5140c291afddedfa0301ec62975f7dadc01b780be` |
| `export_direct.py` | `984ffb653535772bbf7ed18cbb122b9ed1fa78b74960281122808214def2cb72` |
| `verify_direct.py` | `2e84c2a2a92af0bf0e41f1a4a1e69ac66535310bbcc37c1d8f4841bf66fcbcdb` |
| `compare_direct.py` | `a0eb3c66317ccb8fe628c41032d4174c8fac183cbb5144b63125348b9fd33bce` |
| `tests_direct/__init__.py` | `b0c4f731de7a44e83b2668cbc20ed410ec4a5bd76f79bb0f665cd022a6929459` |
| `tests_direct/generate_programs.py` | `e6f56e70dab1d2b3d1e10bf86f22d8eb4af8112bc28bd3a2dd523c1a8ecfa7b8` |
| `tests_direct/test_constraints.py` | `81a033fc9730e6e74d954c072c10a1bc8fa3671f7122077a5f5a44196c154fe3` |
| `tests_direct/test_construction.py` | `7787cfd5f348cb4ec7e8547491fbe72c2d0ac0400391ab1be6a5646180fcb88a` |
| `tests_direct/test_contract.py` | `44ac3321e492c2ddcbab831c8d601f09f6cb5c8fdd1e74378f625ca486dcce46` |
| `tests_direct/test_export.py` | `38c814dd64c0186c6ef789f5fdc6267ff6c3371c57896f9c5645e39600917d39` |
| `tests_direct/test_independence.py` | `3c77ea846ed7b41e815c69e2f03adde73324ac9ff767ec3836dc5808f8bf7b13` |
| `tests_direct/test_optimizer.py` | `468235590a7e4bfb5df8e2353626035b3c09e809a60e6f138ac8d7ebd30879db` |
| `tests_direct/test_schema_index.py` | `4bbf7824b7ad3ba46c4501f74eedb857ca54dc7d518945fdcd9dd331ead972e7` |

Reassembling the export from those sources reproduced the accepted v3 export
byte for byte: `c0574395d339dae3…`, 2,258 lines. Baseline provenance is
therefore **exact**, not approximate, and dependent work is safe.

## Protected controls

All four protected hashes of `INDEX_ONLY_PLAN.md` section 2 match:

| File | Result |
|---|---|
| `common.py` | PASS |
| `reference.json` | PASS |
| `results/comparison.json` | PASS |
| `../GOVERNANCE/GLOSSARY.md` | PASS |

The pinned reference manifest verifies at commit `573b8a85f4bd…`.

## Measured baseline

```sh
PYTHONPATH=.reference:. python3 benchmark_optimization.py --phase baseline \
  --repeats 15 --seed 20260920 --output results/direct_index_v4_optimization/baseline
```

Exit 0, 113.8 s, **600 rows, 0 failures**, exact membership over five arms,
eight programs and fifteen repetitions. Raw rows and the retained randomised
arm order are in [`baseline/runs.json`](baseline/runs.json); the per-program
table is in [`baseline/BASELINE_MEASUREMENTS.md`](baseline/BASELINE_MEASUREMENTS.md).

| Arm | Median compile | Median import | Median whole process |
|---|---:|---:|---:|
| `classical` | 0.2710 ms | 0.251 ms | 46.67 ms |
| `frozen_bootstrap` | 0.6722 ms | 12.086 ms | 29.27 ms |
| `frozen_full` | 424.3664 ms | 12.079 ms | 454.80 ms |
| `candidate_bootstrap` | 0.6736 ms | 12.112 ms | 29.37 ms |
| `candidate_full` | 423.8867 ms | 12.085 ms | 452.96 ms |

The classical median reproduces the accepted v3 figure of 0.2726 ms and the
full-direct median reproduces 424.2704 ms. Timing need not reproduce history
and this run is on the same machine under ordinary load; the agreement is
reported as observed, not required.

### The harness's own noise floor

In this phase the frozen and candidate exports are the **same file**, so the
candidate-versus-frozen ratios measure nothing but measurement noise:

| Comparison | Geomean of per-program median ratios | 95% paired interval |
|---|---:|---|
| `full_candidate_vs_frozen` | 1.0001x | 0.9996 – 1.0005 |
| `bootstrap_candidate_vs_frozen` | 1.0013x | 0.9970 – 1.0073 |

The instrument therefore resolves roughly 0.1% on the full path and 1% on the
bootstrap. Both engineering targets lie far outside that band, so a later
measured difference cannot be an artefact of the harness.

## The hypothesis that bootstrap equals full-direct, tested rather than assumed

Section 4 requires this to be measured per program. It was, for both the frozen
and the candidate arms, over all eight public programs:

**It holds. Zero discrepancies.** Every public program's cycles and scratch are
identical with `optimise=False` and `optimise=True`, and every direct arm's
combined score recomputes to the same value.

That is not a property of the method in general — it is a fact about these
eight programs, and it follows from the optimiser accepting **nothing** here:
over 120 full-direct compilations it attempted 3,270 queries and returned
**SAT zero times**. On the 142-program acceptance corpus the same optimiser
does accept improvements, so the two must not be conflated.

## Where the baseline's time goes

| Quantity | Value |
|---|---:|
| Optimiser share of full-direct compile time | ~99.8% (`frozen_full` / `frozen_bootstrap` ≈ 590x) |
| Queries attempted per compilation | 27.25 |
| Infeasible as posed (free) | 20.6 |
| Completed UNSAT | 3.1 |
| Time-exhausted UNKNOWN | 3.5 |
| Accepted improvements on public programs | 0 |

Each time-exhausted query costs exactly the 100 ms per-query budget, so
**3.5 × 100 ms = 350 ms of the 424 ms median — 82.5% — is spent on queries that
return no information and whose wall cost is pinned by the clock.** This single
measurement governs what the optimization phase could and could not achieve;
its consequence is worked out in [BENCHMARK.md](BENCHMARK.md).

## Frozen evaluation corpus

100 programs, twenty from each of the five existing generator families, selected
by seed `20260921` from a seed range disjoint from the acceptance corpus's own
(`0–29` regression, `1000–1099` additional). Program JSON and per-program
content hashes are in [`baseline/extra_corpus/`](baseline/extra_corpus) and
[`baseline/extra_corpus_manifest.json`](baseline/extra_corpus_manifest.json).
Every one was validated by the frozen reference before being frozen.

It is produced by the **same generator** as the acceptance corpus and is
therefore **not statistically independent** of it. It is a held-out evaluation
set and is described as nothing more.

## Limitations

- Eight public programs only. The private grader is unavailable and nothing is
  inferred about it.
- `compile_seconds` excludes interpreter start and imports; `process_seconds`
  includes them and is what the 20 s external limit governs. The direct arms
  pay about 12 ms of import that the classical arm does not, because they load
  the assembled export.
- Combined scores here use the protected historical serial integers; `serial`
  is not one of this harness's five arms. `compare_direct.py` measures serial
  itself and its `frozen_integer_metrics` gate is what keeps that record honest.
