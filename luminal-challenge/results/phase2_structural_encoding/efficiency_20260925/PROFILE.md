# Gate P: where the fixed-work time of R0 goes

2026-09-25 · Claude Code · plan §4. Data: `profile/rows.jsonl` (80 rows, 0 failed).
Aggregate: `profile/PROFILE.json`. Producer: `research/efficiency_profile.py`.

**Decision: NO_JUSTIFIED_OPTIMIZATION.** No mechanism confined to one propagation
component can plausibly cut total fixed-work compile time by 20%, even if its own
cost fell to zero. The proposal is in `MECHANISM_PROPOSAL.json`. E1 is not
implemented, and Gates E and C are not run.

## What was measured

- **Programs.** The first two development seeds of each family, 800000–800009
  (seed mod 5 is the family).
- **Work.** R0 in the E-gate fixed-work mode: A4 catalog, DFS, every existing
  limit, aggregate 10,000 nodes and 100,000 validations. The clock is constant, so
  no allowance, slice or deadline expires. All ten searches ran to catalog
  exhaustion inside that ceiling: 8,827 charged nodes in total, the same as the
  next round's `work:10000` diagnostic.
- **Modes.** One fresh process per mode, with nothing else measured running
  alongside.
  - `time`: unprofiled, 3 fresh processes per program; the median is the
    matched-work reference.
  - `timers_split`: exclusive seconds of named helpers, from a `perf_counter`
    stack.
  - `profile`: cProfile.
  - `count`: calls, domain changes, sweeps, exact repeated inputs.
  - `memory`: tracemalloc peak.
  - `parity`: checks that the split instrumentation changes no decision.
- **Split instrumentation.** `SplitPropagation` and `SplitExpander` contain the R0
  bodies with rule 1, the two halves of rule 2 and the state copies moved into
  named helpers. On all 10 programs the decision fingerprint is identical:
  trace, incumbent, certificate stream, statuses and aggregate
  (`final_split_changes_no_decision_all: true`).
- **Distortion.** cProfile inflates the whole call 3.64× (2.61–3.83× by program).
  Its exclusive time reconciles to 0.998–1.000 of the profiled wall. The
  lightweight timers inflate it only 1.02–1.29×, so **shares below are timer
  seconds divided by the unprofiled median**, not cProfile shares.

## Shares of unprofiled fixed-work compile time (timers_split)

| Seed | Family | T (s) | Precedence | Rule 2: EO/singles | Rule 2: scan | Address support | Bounds | Certificates | Options | Validation |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800000 | scalar | 0.0047 | 0.147 | 0.065 | 0.112 | 0.000 | 0.156 | 0.102 | 0.034 | 0.018 |
| 800001 | vector | 0.1952 | 0.199 | 0.107 | 0.252 | 0.003 | 0.305 | 0.091 | 0.033 | 0.003 |
| 800002 | mixed | 0.0424 | 0.013 | 0.006 | 0.004 | 0.373 | 0.074 | 0.025 | 0.083 | 0.121 |
| 800003 | dependency | 0.0384 | 0.015 | 0.006 | 0.004 | 0.251 | 0.042 | 0.015 | 0.043 | 0.091 |
| 800004 | aliasing | 0.0232 | 0.142 | 0.090 | 0.326 | 0.007 | 0.169 | 0.115 | 0.030 | 0.028 |
| 800005 | scalar | 1.0708 | 0.238 | 0.108 | 0.307 | 0.009 | 0.239 | 0.102 | 0.022 | 0.002 |
| 800006 | vector | 0.6496 | 0.189 | 0.122 | 0.141 | 0.014 | 0.433 | 0.040 | 0.042 | 0.005 |
| 800007 | mixed | 0.0487 | 0.022 | 0.007 | 0.012 | 0.432 | 0.042 | 0.018 | 0.049 | 0.040 |
| 800008 | dependency | 0.0130 | 0.147 | 0.090 | 0.252 | 0.000 | 0.196 | 0.090 | 0.042 | 0.006 |
| 800009 | aliasing | 0.0893 | 0.205 | 0.110 | 0.308 | 0.014 | 0.206 | 0.061 | 0.038 | 0.020 |

The **state copying** share is 0.002–0.021 and the **encoding** share is at most
0.047. In the cProfile view (inflated, pooled), propagation is 91.1% of exclusive
time: issue capacity 39.7%, bounds 24.3%, precedence 19.9%, certificates 4.2%,
address support 3.0%.

The profile is not uniform. For scalar, vector and aliasing programs, and for one
of the two dependency programs, the cost is rule 2, bounds and precedence. The
two mixed programs, and dependency program 800003, spend most of their time in
**address support** (0.25–0.43).

## Avoidable work, counted

| Quantity | Pooled over 10 programs |
|---|---:|
| Rule-2 value checks (every value of every non-singleton op, every sweep) | 4,608,044 |
| of which found a full cycle | 23,998 (**99.48% futile**) |
| Rule-2 op-scans / scans whose engine had no dynamic full cycle | 730,224 / 362,769 |
| `times_fixpoint` calls / sweeps / edge visits | 55,728 / 98,191 / 2,651,092 |
| Confirmation sweeps, i.e. final sweeps that change nothing (at least) | 55,611 |
| Exact repeated inputs within one domain: `times_fixpoint` | 185 (0.33%) |
| … `compulsory_peak` / `prune` / `addresses_fixpoint` | 1,471 (2.6%) / 381 (0.67%) / 24 (2.1%) |
| Certificates emitted | 176,500 |
| tracemalloc peak | 0.2–2.5 MB per program |

Least-squares cost model of the rule-2 scan over the 10 programs: **324 ns per
op-scan + 59 ns per value check**.

## Zero-cost ceilings

The ceiling is the fixed-work compile ratio if a component cost **nothing**,
taken as the equal-family geometric mean of `1 − share`. It bounds any mechanism
confined to that component. Timer overhead makes it slightly optimistic.

| Component | Ceiling | Mean share | Max share |
|---|---:|---:|---:|
| whole `times_fixpoint` (precedence + both parts of rule 2) | **0.582** | 0.375 | 0.652 |
| bounds (product bound, compulsory peak, prune) | 0.805 | 0.186 | 0.433 |
| rule-2 scan | 0.819 | 0.172 | 0.326 |
| address support | 0.846 | 0.138 | 0.432 |
| precedence | 0.865 | 0.132 | 0.238 |
| rule-2 EO/singles | 0.928 | 0.071 | 0.122 |
| certificate bookkeeping | 0.933 | 0.066 | 0.115 |
| option lists | 0.958 | 0.041 | 0.083 |
| state copying | 0.986 | 0.014 | 0.021 |

## Reading

1. The most wasteful measured work is the rule-2 scan: 99.5% of its checks find
   nothing. An exact candidate-cycle filter (M1 in `MECHANISM_PROPOSAL.json`)
   could skip most of it without changing any certificate. But even if the scan
   cost nothing, the ratio would be 0.819: an 18% saving, below the 20% bar. The
   cost model predicts **0.939** (a 6% saving) once the filter's own cost is paid.
2. Every other single component has a ceiling above 0.80. Only the whole
   fixpoint is below it, at 0.582. That would need a change-driven fixpoint, and
   the next round measured exactly that worklist mechanism at a 4.8% saving. The
   plan forbids assuming another worklist wins.
3. Caching cannot help: exact repeated inputs are 0.3–2.6% of calls.
4. The mixed and dependency programs, whose cost is address support, cap any
   rule-2 or bounds mechanism under equal family weighting. This is also why the
   confirmation target (upper bound ≤ 0.80) would be out of reach.
