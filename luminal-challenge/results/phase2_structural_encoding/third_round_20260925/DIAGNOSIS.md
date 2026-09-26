# Stage M: shared propagation state — diagnosis, kernel and decision

2026-09-25 · Claude Code · plan `CLAUDE_PHASE2_THIRD_ROUND.md` §3 · protocol 1.0.

**Decision: NO_JUSTIFIED_MECHANISM** under the formula registered in
`MECHANISM_SPEC.json`. The conservative predicted fixed-work compile ratio is
**0.827** against a gate of **≤ 0.80** (point prediction 0.654). Kernel parity
held on all 30 workloads. The registered formula has a scope defect, which I found
only after seeing the result. It is disclosed in §4 and was not used to reverse
the decision. C1 was not built; D and C were not run.

## 1. What was measured (M0, 210 rows, 0 failed)

- **Programs:** development seeds 800000–800029, six per family. This is
  development evidence, not an inferential cohort.
- **Work:** R0 (`research/efficiency_search.py`, sha `d0fcd441…`), imported and
  unedited, in fixed-work mode: A4 catalog, DFS, 10,000 nodes, 100,000
  validations, 2,048-node slices, constant clock.
- **Modes:** each mode ran in its own fresh process. Rows are in
  `stages/M_diagnosis/rows.jsonl`; keys were frozen in `EXPECTED_KEYS.json`.
  - three unprofiled compile calls (`T0` is their median);
  - exclusive timers;
  - a workload trace;
  - tracemalloc peak memory;
  - an instrumentation-parity probe.
- **Instrumentation parity:** the timer run, the trace run and the plain call
  have identical decision fingerprints on all 30 programs. The fingerprint
  covers the search trace, incumbent, certificate stream, statuses and aggregate.
- **Timer distortion:** timer inflation over `T0` is 1.01–1.52. Exclusive time
  plus the untimed remainder equals the timed wall.
- **Replay fidelity:** replaying R0's own methods over each captured workload
  reproduces every captured output. It also reproduces every per-call
  certificate count and the complete certificate stream, on 30/30 programs
  (`stages/M_diagnosis/REUSE_COUNTS.json`).
- **Memory:** tracemalloc peak is 0.18–3.56 MB per program.
- **Cost ownership:** the component map is in `COST_OWNERSHIP.json`. Certificate
  emission is charged once, to `certificates`. `prune → product_bound →
  compulsory_peak` counts as one component, live/product bounds.

### Work that re-reads unchanged facts, pooled over 30 programs

The comparison is always against the fact's previous evaluation on the same
branch. For a child's first sweep, that previous evaluation is the one at the
end of the parent's propagation.

| Operation | Evaluations | Inputs unchanged | Evaluations that change something |
|---|---:|---:|---:|
| Precedence edge (four bounds read) | 15,792,408 | 87.4% | 3.7% |
| Issue-capacity op scan (domain and full-cycle set) | 3,550,105 | 76.9% | 7.6% |
| Compulsory interval of a value after a child | — | 76.1% of values | 2.2% of children have all intervals unchanged |
| Address pair (bounds of `A_v`) | 7,454,810 | 84.1% | 3.0% |

Whole-call exact repeats, the earlier cache measure, are rare, so a cache keyed
on whole inputs has little to reuse. Re-derivation of facts from a parent is
common, and that is the object this round measured.

## 2. The nominated design (M1)

`BS1_branch_state_with_change_record`, specified in `MECHANISM_SPEC.json` before
the kernel was first run (ordering disclosure in the spec). Each node holds an
immutable branch state, shared read-only by its children. The state carries:

- the node's domains;
- R0's last singles snapshot;
- per-value compulsory intervals and the peak;
- address-pair incidence.

A child records which bounds changed. That record drives four components:

- precedence evaluates only dirtied edges, in R0's sweep order;
- issue capacity handles only new singletons and newly full cycles;
- live bounds recompute only the intervals whose producer or consumer changed;
- address support evaluates only pairs whose `A_v` bounds changed.

The certificate stream is identical to R0's by construction. The kernel
reproduces it on 30/30 workloads, and six planted defects are caught
(`research_tests/test_third_round_kernel.py`).

## 3. Kernel replay and prediction (M2, 180 rows, 0 failed)

Workload hashes and kernel sources were frozen in `WORKLOAD_MANIFEST.json` before
any timing. Each row is one fresh process. It times one cold replay of the captured
events, releasing each output after its last use, then checks parity untimed.

- **Kernel speedup** on the replaced work (baseline replay median / shared
  replay median): median 2.39× over the 30 programs, range 0.92×–4.36×.
- **Integration upper estimate:** at most 1.9 ms per program, measured.
- **`O`**, as registered: min(baseline replay median, timer-exclusive replaced
  seconds / timer inflation).
- **`N`**: shared replay median plus the integration estimate.

| Aggregate (equal-family geometric mean, 30 programs) | Value | Gate |
|---|---:|---:|
| `(T0 − O + N)/T0` | 0.654 | — |
| `(T0 − O + 1.5N)/T0`, registered | **0.827** | ≤ 0.80 → **not met** |

Family conservative geometric means: scalar 0.874, vector 0.771, mixed 0.749,
dependency 0.959, aliasing 0.798.

- **Dependency family:** the ratio is driven by 800023 (13 events, kernel slower
  than baseline, ratio 1.17) and 800028. On 800028 the timer arm of `O` is 19%
  below the replay arm.
- **Small programs** (800000, 800012, 800024) have conservative ratios above 1.
  Fixed overheads dominate there.

| Seed | Family | T0 (s) | Replaced share (timed) | Edge evals unchanged | Scans unchanged | Pair evals unchanged | O/T0 | N/T0 | Kernel x | Ratio | Conservative |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800000 | scalar | 0.005 | 0.46 | 0.55 | 0.69 | — | 0.46 | 0.43 | 1.19 | 0.960 | 1.173 |
| 800001 | vector | 0.196 | 0.82 | 0.84 | 0.80 | 0.90 | 0.82 | 0.43 | 2.19 | 0.607 | 0.820 |
| 800002 | mixed | 0.042 | 0.48 | 0.87 | 0.70 | 0.91 | 0.48 | 0.13 | 4.10 | 0.650 | 0.714 |
| 800003 | dependency | 0.039 | 0.31 | 0.78 | 0.64 | 0.94 | 0.31 | 0.13 | 2.92 | 0.821 | 0.887 |
| 800004 | aliasing | 0.023 | 0.68 | 0.68 | 0.81 | 0.86 | 0.68 | 0.40 | 1.94 | 0.727 | 0.929 |
| 800005 | scalar | 1.072 | 0.84 | 0.86 | 0.76 | 0.93 | 0.84 | 0.40 | 2.39 | 0.557 | 0.756 |
| 800006 | vector | 0.651 | 0.86 | 0.92 | 0.82 | 0.95 | 0.86 | 0.38 | 2.40 | 0.525 | 0.717 |
| 800007 | mixed | 0.050 | 0.51 | 0.85 | 0.79 | 0.92 | 0.51 | 0.13 | 4.36 | 0.623 | 0.689 |
| 800008 | dependency | 0.013 | 0.64 | 0.78 | 0.90 | — | 0.64 | 0.36 | 2.07 | 0.717 | 0.897 |
| 800009 | aliasing | 0.090 | 0.79 | 0.92 | 0.87 | 0.85 | 0.79 | 0.29 | 2.96 | 0.498 | 0.643 |
| 800010 | scalar | 0.034 | 0.46 | 0.76 | 0.66 | 0.90 | 0.46 | 0.21 | 2.46 | 0.751 | 0.858 |
| 800011 | vector | 2.001 | 0.80 | 0.85 | 0.37 | 0.85 | 0.80 | 0.29 | 3.27 | 0.481 | 0.624 |
| 800012 | mixed | 0.008 | 0.51 | 0.80 | 0.80 | 0.91 | 0.51 | 0.35 | 1.49 | 0.844 | 1.021 |
| 800013 | dependency | 0.793 | 0.82 | 0.83 | 0.82 | — | 0.82 | 0.43 | 2.22 | 0.607 | 0.819 |
| 800014 | aliasing | 0.260 | 0.77 | 0.96 | 0.67 | 0.85 | 0.77 | 0.33 | 2.47 | 0.560 | 0.726 |
| 800015 | scalar | 0.793 | 0.77 | 0.89 | 0.55 | 0.73 | 0.77 | 0.35 | 2.34 | 0.586 | 0.762 |
| 800016 | vector | 0.290 | 0.78 | 0.74 | 0.78 | 0.83 | 0.78 | 0.47 | 1.97 | 0.691 | 0.925 |
| 800017 | mixed | 0.202 | 0.80 | 0.91 | 0.90 | 0.89 | 0.80 | 0.36 | 2.41 | 0.562 | 0.742 |
| 800018 | dependency | 0.012 | 0.27 | 0.83 | 0.60 | 0.87 | 0.27 | 0.14 | 2.10 | 0.873 | 0.944 |
| 800019 | aliasing | 0.590 | 0.81 | 0.95 | 0.75 | 0.94 | 0.81 | 0.34 | 2.52 | 0.530 | 0.698 |
| 800020 | scalar | 0.241 | 0.78 | 0.76 | 0.78 | 0.77 | 0.78 | 0.54 | 1.71 | 0.759 | 1.030 |
| 800021 | vector | 1.462 | 0.86 | 0.92 | 0.85 | — | 0.86 | 0.37 | 2.45 | 0.506 | 0.690 |
| 800022 | mixed | 0.924 | 0.82 | 0.93 | 0.83 | 0.95 | 0.82 | 0.36 | 2.53 | 0.542 | 0.720 |
| 800023 | dependency | 0.012 | 0.02 | 0.45 | 0.25 | — | 0.02 | 0.13 | 0.92 | 1.103 | 1.166 |
| 800024 | aliasing | 0.011 | 0.57 | 0.73 | 0.48 | — | 0.57 | 0.45 | 1.47 | 0.879 | 1.105 |
| 800025 | scalar | 0.464 | 0.83 | 0.86 | 0.78 | 0.91 | 0.83 | 0.39 | 2.44 | 0.554 | 0.747 |
| 800026 | vector | 0.573 | 0.70 | 0.93 | 0.81 | 0.74 | 0.70 | 0.40 | 2.19 | 0.696 | 0.895 |
| 800027 | mixed | 0.833 | 0.76 | 0.91 | 0.73 | 0.94 | 0.76 | 0.28 | 2.89 | 0.519 | 0.657 |
| 800028 | dependency | 1.536 | 0.76 | 0.61 | 0.68 | — | 0.76 | 0.56 | 1.66 | 0.806 | 1.087 |
| 800029 | aliasing | 1.401 | 0.84 | 0.92 | 0.87 | — | 0.84 | 0.41 | 2.28 | 0.570 | 0.774 |

"Replaced share" is timer-inflated (share of the timed wall). `O/T0` uses the
registered `O`. "Kernel x" is the baseline replay median divided by the shared
replay median.

## 4. Analysis defect found after the outcome (not applied)

The timer arm of `O` sums only the components BS1 replaces (`REPLACED` in
`third_round_analysis.py`). It leaves out three things that the ownership map
charges elsewhere:

- certificate emission, charged to `certificates`;
- `Propagation.__init__`;
- `address_pairs`.

`N` is the shared-kernel replay, and it **does** include the same emissions,
construction and pair building, which it re-performs identically. So `min()`
picked the timer arm on all 30 programs. It then charged the unchanged emission
work at 1.5× on top of `T0`, although that work is not replaced.

The two arms can be matched in scope. The baseline replay median divided by a
scope-matched timer estimate (replaced components plus certificates, setup and
pairs, deflated) lies in **[0.90, 1.07]** over the 30 programs.

With a consistent scope, the conservative ratio would be:

- **0.742** with `O` = the replay median;
- **0.764** with `O` = min(replay, scope-matched timer).

Both are below 0.80.

I did not act on this. Plan §3 and §6 forbid changing a gate computation after
its outcome is known ("do not … lower the target"), and the defect was found only
after the registered result had been read. The decision therefore stands as
registered. Whether the corrected computation is admissible, and whether D may
be authorized on it, is the lead's decision (`MECHANISM_DECISION.json`,
`analysis_defect_found_after_outcome`).

## 5. What this does and does not show

- **Shown:** exact re-derivation is common in R0's propagation, and one shared
  branch state removes most of it. The captured replaced work runs about 2.4×
  faster, with byte-identical certificates on 30 development programs.
- **Not shown:** a compiler speedup. A kernel replay is not a compile call. The
  prediction is a development model, not a bound; no C1 was integrated or timed.
- **Not shown:** that the 20% target is unreachable. The registered conservative
  prediction misses it, and a scope-consistent one would not.
