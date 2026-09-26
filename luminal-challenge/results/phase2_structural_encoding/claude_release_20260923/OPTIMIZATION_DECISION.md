# Optimisation decision — Phase 2 release candidate

2026-09-24 · Claude Code · plan §7. Every number below comes from the run of record, the
self-contained run `recovery_campaign_20260923_r3`: checker 0 findings
(`CHECKER_REPORT_r3.json`), the lead's raw-row auditor PASS
(`INDEPENDENT_COMPARISON.json`), and 24/24 contrasts agreeing to 1e-9
(`CROSSCHECK.json`). `_r2`, whose measurement source is identical, reproduces the
primary to the last digit. Quality is paired log(J_control / J_candidate) with
J = C × S; positive favours the candidate. Runtime ratios are candidate / control,
where above 1 means slower. Intervals are 95 %, family-stratified, 10,000 resamples,
seed 20261021. Only the held-out primary is confirmatory.

## 1. Is the implementation correct within the established scope?

Yes, within the tested and measured scope, subject to Codex review.
- 286 research tests pass: 269 inherited plus 17 new. Twelve of the 17 fail on
  the unrepaired source (`logs/b02`: 8, `logs/f02`: 3, `logs/h02`: 1). The other
  five are guards or coverage tests, and they pass on both sources by design.
- 33,120 measurement workers ran: 1,800 in P2, 7,020 in P4 and 24,300 in P5. There
  were 0 failed rows, 0 timeouts, 0 non-zero worker exits and 0 validator
  discrepancies.
- P1: 24 exhausted codec/oracle comparisons show exact set equality, with 0
  round-trip failures and 0 physical-probe discrepancies over 11,564 proposals
  (7,727 validated, 3,835 physically invalid, 2 interrupted at the deadline).
- P2: every tiny fixture reaches the oracle minimum, and the bounds are admissible
  on every fixture.
- Seven implementation defects were found and repaired in this release, R1–R7 in
  `READINESS_MATRIX.md`. Two of them (R6, R7) were checker defects exposed only by
  a real completed campaign.

The scope limits are as follows. Correctness is established on the 8 public and
100 held-out programs, the 12 tiny fixtures and the pinned machine; it is not
established for arbitrary programs. P1 coverage passes only under the amendment:
the original random-stream coverage still fails (0–234 distinct per program
against the required 100). The amended pass is local codec coverage around one
schedule. For example, `01_scalar_pipeline` has 1,267 objects but only 19 distinct
issue-time vectors, so it is not evidence of diverse schedule sampling.

## 2. Did the fixed candidate improve output quality versus original direct?

**Yes, on the frozen held-out primary, and the effect is small.** `structural_bound`
versus accepted v4 `accepted_budgeted` at 0.1 s over 100/100 held-out programs:
+0.0439 [0.0251, 0.0660]. Candidate J is lower on 26 programs, equal on 74 and
higher on none. The geometric-mean J reduction is 4.3 % across all 100 programs,
so the whole effect is carried by the 26 changed programs; 74 % of programs are
untouched. Of the 26 improvements:
- 21 reduce scratch at unchanged cycles;
- 3 trade one extra cycle for a larger scratch reduction;
- 2 reduce cycles only.
The gain is therefore mainly a scratch-allocation gain (`RELEASE_ANALYSIS.json`,
`primary_render`).

The descriptive held-out contrasts against the other direct controls point the
same way, with no losses at any budget:

| Control | 0.01 s | 0.1 s | 1.0 s |
|---|---|---|---|
| accepted_bootstrap | +0.0566 [0.0329, 0.0846], 31 W / 69 T / 0 L | same | same |
| accepted_default | +0.0403 [0.0223, 0.0614], 25 W / 75 T / 0 L | same | same |

On public programs (8, descriptive only) the effect is +0.0240 [0, 0.0721] with
1 W / 7 T / 0 L at every budget. The interval touches zero, so this is
inconclusive, not equivalence.

Attribution: `structural_dfs` equals `structural_bound` at 0.1 s and 1.0 s (26
and 25 wins, identical intervals); they differ only at 0.01 s (30 against 31 wins).
The measured gain therefore comes from the matched-window structural search, not
from the admissible bound. The larger-domain `structural_expanded` is weaker
(+0.0049 [−0.0138, 0.0198], 7 W / 91 T / 2 L at 0.1 s) because it is deadline-bound.

## 3. How did it compare with classical?

These contrasts are descriptive and unadjusted.
- **Quality, held-out:** better by +0.0882 [0.0592, 0.1194]: 53 W / 35 T / 12 L,
  8.4 % lower geometric-mean J. Classical keeps 12 programs: 7 through fewer
  cycles and 5 through less scratch. Across all 100 programs, classical has fewer
  cycles on 22 and the candidate has less scratch on 56. The cycle wins are
  schedule wins that the matched window around the direct bootstrap schedule
  cannot reach.
- **Quality, public:** +0.1336 [−0.0865, 0.3352], 4 W / 3 T / 1 L. Inconclusive.
- **Cost, held-out:** compile time 7.3× classical [6.0, 8.7], a median of 5.65 ms
  against 0.64 ms. Process time is 1.50× [1.48, 1.51], 0.054 s against 0.036 s.
  Peak RSS is 1.18×.
- **Cost, public:** compile 12.6× [9.3, 16.4] and process 1.50×.

The candidate is **better in output quality and worse in compile cost** than
classical. That is a trade-off, not an overall "better". Absolute cost stays far
inside the 20 s process limit: the maximum held-out process time for
`structural_bound` is 0.066 s.

Against accepted direct, the candidate is also cheaper. At 0.1 s its compile time
is 0.073× `accepted_budgeted` [0.063, 0.085] and process time 0.43×. Its compile
time is 0.042× `accepted_default`. The saving comes from a different stopping
rule, not from faster equal work: `accepted_budgeted` consumes its deadline,
whereas `structural_bound` stops after a median of 3 ms (section 5). Against
`accepted_bootstrap`, which runs no optimisation, compile time is 4.0× [3.4, 4.6].

## 4. H3 and H4

- **H3 is supported as a research triage.** 7/11 informative fixtures meet the
  20 % margin across families memory, mixed and scalar. This is a triage
  threshold, not a statistical test.
- **H4 is inconclusive and structurally untestable with the frozen fixtures.**
  P4 ran all 7,020 rows, but only `many_ready_1` (40 feasible objects) meets the
  ≥10 train / ≥5 test rule. The other 11 fixtures have 2–18 feasible objects,
  matching P3's independent oracle counts. The fixture set can therefore never
  supply the ≥3 families that H4 requires. On that single fixture, `model_expand`
  ties every control at every budget; the Bonferroni lower bounds are 0.0 and
  0.0, and empirical-cover test discoveries are 0.
- **Consequence:** the P5 model arm is correctly absent (`NOT_RUN`, 0 rows) and
  its 4,860 rows were not measured. Neither a model advantage nor a model
  disadvantage has been measured.

## 5. Nature of the remaining shortcomings

| Shortcoming | Class | Evidence |
|---|---|---|
| 74 % of held-out programs unchanged | Measured engineering limit, not a defect | See the next row |
| 64/100 held-out programs stop at the query cap (`max_queries` = 32) after about 3 ms; this includes 45 of the 74 ties, so the search is truncated | Measured engineering cost; possible headroom, **not measured** | `stopping_reasons` in `RELEASE_ANALYSIS.json`: 960/1,500 rows at 0.1 s and 1.0 s, and 939 (+21 at the deadline) at 0.01 s |
| 29 ties complete the matched-window pass without improvement | Measured limit of the domain | same |
| Classical wins 12 held-out programs (7 on cycles, 5 on scratch) | Measured limit of the domain, which is anchored on the direct schedule | per-program C/S in `RELEASE_ANALYSIS.json` |
| Compile cost 7.3× classical | Measured engineering cost | COMPARISON.json |
| H4 untestable | Insufficient evidence caused by the design (fixture sizes) | P4 split sizes |
| Original random P1 coverage fails | Measured limitation, reported separately from the amended gate | P1 summary |

After repairs R1–R7, no known correctness defect remains open.

## Decision

**Further optimisation is warranted, as a new, separately registered phase.** It
does not belong in this release, and it must not be carried out by tuning on
these held-out outcomes. The measured result is a small, reproducible, one-sided
quality gain over accepted direct and a cost trade-off against classical. The
binding constraint is a query cap, not time: that is the one clear, measurable
lever this campaign exposes.

The proposals are ranked by measured cost. Each will need a **fresh held-out
cohort**, for example a new seed range disjoint from 800000–800099. Once any of
them is tuned, the present 100 programs become development evidence for the
tuned version.

1. **Make the matched-window query cap budget-aware**
   (`research/run_structural_experiments.py::structural_optimise`, where
   `dcomp.DEFAULT_LIMITS.max_queries` is passed). The invariant to preserve is the
   shared absolute deadline, strict-improvement acceptance and pinned validation of
   every accepted incumbent. The prediction is falsifiable: at 0.1 s and 1.0 s,
   some of the 45 query-capped ties become wins, the effect grows with budget
   (unlike the flat 0.01 = 0.1 = 1.0 profile measured now), and compile time rises
   towards the budget. The ablation compares the cap at 32 with the uncapped
   version at each budget. If the capped ties do not move, the domain is the limit
   and proposal 2 becomes first.
2. **Add schedule (time-field) moves that can reach classical's cycle counts**
   (`research/structural_encoding.py` domain construction; matched-window bounds).
   The invariant is the same codec semantics and pinned validator. The prediction
   is falsifiable: the 7 held-out programs that classical wins on cycles fall
   below 7, without new losses against accepted direct. The ablation is the
   current window against the widened one, with `structural_expanded`'s
   deadline-bound behaviour as the warning case.
3. **Reduce fixed process cost** (worker import path). The measured process cost
   is 0.054 s against classical's 0.036 s. The prediction is that the process
   ratio against classical falls below 1.5 with J unchanged. This is engineering
   only; no quality claim follows.
4. **H4 requires new fixtures before any model work:** at least three families
   with ≥20 feasible objects, specified before measurement. No model tuning is
   meaningful until H4 is testable.
