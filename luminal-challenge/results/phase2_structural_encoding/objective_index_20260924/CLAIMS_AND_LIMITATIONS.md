# Claims and limitations — objective-index research protocol 1.0

The kinds of statement are kept apart: **proved**, **tested** (finite checks with
denominators), **measured** (frozen design, fresh data), **null/blocked**, **not claimed**.

## 1. Proved (THEORY.md)

- Expanding ANY exact cover of an elite set by one free coordinate yields exactly the novel
  one-bit neighbourhood; depths 1+2 yield exactly the radius-2 Hamming ball; the old
  implementation's proposal sequences are identical to one-bit mutation. The old
  `model_expand` is a neighbourhood operator, not a demonstrated learned predictor.
- Integer-cap lemma: within a declared window neighbourhood, capping selected times below
  ⌊(J0−1)/LS⌋ and block ends at ⌊(J0−1)/LC⌋ keeps every strict improvement; caps below the
  lower bounds prove there is none IN THAT NEIGHBOURHOOD.
- Soundness of the four propagation rules; rank preservation under value filtering;
  partition of the universe by the schema tree's leaves (a statement about representation,
  not about label correctness).
- From the frozen oracle/split alone: H_LEARN's endpoint could not differ between arms on
  any of the 30 evaluation fixtures (0/30 had a test object below the training minimum).

## 2. Tested correctness (finite, with denominators)

`PRUNING_VALIDATION.json`, `final_checks/research_tests_final.*`: cap-lemma set equality on
87 exhaustible domains at 328 thresholds (21,853 improving objects) across oracle and three
complete searches; 32,621 propagation events checked against 214,545 feasible completions,
0 violations; 6,431 certificates replayed; two planted unsound rules detected; 12,964 leaf
round trips; node-for-node parity with `structural_search.search`; A1 identical to
`optimization_search.optimise(capnull_matched)` under fixed work; resumed = uninterrupted
pop sequences; late validations never accepted; planted validator rejections retained. This
is tested implementation plus proofs, not a formal verification of arbitrary programs.

## 3. Measured (fresh cohort 910000–910199, 200 programs × 15 repetitions; frozen)

**Primary, 0.1 s, Bonferroni 98.33% (1/120, 119/120), paired log(J_control/J_A4):**

| control | point | interval | wins/ties/losses |
|---|---|---|---|
| A0 (accepted Phase 2) | +0.0623 | [+0.0460, +0.0806] | 102/98/0 |
| accepted budgeted direct | +0.0917 | [+0.0710, +0.1134] | 127/73/0 |
| classical | +0.1118 | [+0.0876, +0.1375] | 138/42/20 |

All three lower bounds exceed zero. The protocol's wording therefore applies: A4 at 0.1 s
has the **best average output quality among these three controls at this budget on this
population** (programs from the same generator families). About 6.0%, 8.8% and 10.6% lower
geometric J respectively. It is not best on every program: it loses to classical on 20.

**Cost (same Bonferroni level, selected / control):** compile time 11.65× A0
[10.04, 13.53] and 76.2× classical [62.4, 92.7]; process time 2.21× A0 and 3.33× classical;
0.82× the accepted budgeted compiler's compile time [0.68, 0.98] (a speed-up only relative
to that control's longer 0.1 s search). A4's median compile time is 0.101 s (p95 0.107,
max 0.110; overshoot ≤ 4.4 ms): it runs to its deadline in 1,591 of 3,000 rows. Relative to
A0 and classical this is a quality/cost trade-off, not Pareto dominance.

**Descriptive (unadjusted 95%):** A4 vs A0 at 1.0 s +0.0786 [+0.0637, +0.0946] (115/85/0),
at 0.01 s +0.0114 [+0.0023, +0.0217] (24/166/10, losses appear at the smallest budget).
Ladder at 0.1 s: cap removal A0→A1 +0.0055 [+0.0025, +0.0091]; product domains A1→A2
−0.0011 [−0.0028, 0.0000] (2 losses, 198 ties); propagation A2→A3 exactly 0 but 17% cheaper;
A3→A4 +0.0579 [+0.0442, +0.0726] at 14.6× A3's compile time. The A4 step bundles the larger
neighbourhood catalog and the discrepancy traversal; this design cannot attribute it to
either. Of A4's 175,868 queries at 0.1 s, 6,933 (3.9%) ended UNKNOWN at the deadline,
25,551 were SUPERSEDED by an improvement elsewhere, 103,922 were proved empty by the caps.

**Exact public suite (8 programs, 15 repetitions, serial denominator):** A4@0.1 =
2.0889454903 in every repetition, vs A0 2.0327602339, original direct 2.0084662023,
classical 1.9013791213; strictly greater in all 15 paired repetitions against each. The
export reproduces 2.0889454903 in 3/3 repetitions. This is exact arithmetic on a fixed
suite: it is not a population estimate and says nothing about the private grader.

## 4. Nulls and blocked stages

- **H_LEARN: FAIL.** Every contrast is exactly 0 on 30/30 fixtures ([0, 0]; 0 defects), as
  §1 proved in advance from the frozen design. This is a failed gate of this design, not
  evidence that learning cannot help. Descriptively (fixed work, nested prefixes), the tree
  placed more elite-level test objects in its first 32 proposals than shuffled labels
  (1.73 vs 0.80) or random order (0.51), but fewer than plain Hamming order (3.33).
- **End-to-end learned compiler pair: BLOCKED_BY_H_LEARN.** Implemented, frozen and tested
  before evaluation; not run. In real compilation, bounded queries rarely accumulate the
  required 20 case-validated observations, so even an enabled pair would mostly fall back
  to search.
- **Original H4:** INCONCLUSIVE, unchanged.

## 5. Not claimed

Private-grader performance; populations beyond these five generator families; equal-work
or wall-clock superiority over A0 or classical; global optimality; that A4's gain comes
from any single one of its components; any learning benefit.

## 6. What would require another experiment

A fixture design with test headroom (e.g. a split or qualification rule that leaves some
better objects unseen) before any learning hypothesis can be estimable; a factorial
ablation to separate A4's catalog from its traversal; evaluation on a different program
distribution; a matched-work (node-count) comparison if speed at equal effort matters.
