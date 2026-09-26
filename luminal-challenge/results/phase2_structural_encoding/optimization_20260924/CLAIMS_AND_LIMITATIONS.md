# Claims and limitations — optimization protocol 1.0

Implementer: Claude Code. Final acceptance: Codex (not self-accepted). All numbers below come from raw rows via `research/optimization_analysis.py` and `research/optimization_report.py`. They were independently recomputed by `research/optimization_audit.py` (standard library only, imports no research module): 205,066 checks, 0 findings (`INDEPENDENT_AUDIT.json`).

Here J = cycles × scratch, lower is better. An "effect" is the mean paired log(J_control / J_candidate): repetitions averaged within each program, then families weighted equally; positive favours the candidate. Intervals are family-stratified program bootstraps with 10,000 resamples and seed 2026092403.

## 1. Correctness scope

- 68,904 measured rows, every one expected by a frozen ledger, with 0 failed rows, 0 missing, 0 duplicates, 0 timeouts and 0 validator discrepancies (`CHECKER_REPORT.json`, `INDEPENDENT_AUDIT.json`):

  | stage | rows |
  |---|---|
  | development search | 9,300 |
  | engineering pair | 1,800 |
  | bound ablation | 1,800 |
  | model depth | 270 |
  | fresh compiler | 36,000 |
  | public | 1,560 |
  | model evaluation | 17,550 |
  | export | 624 |

- Every returned compilation was checked by the pinned machine: `check_compilation` plus every declared case. Correctness is established for these programs and their cases only, not for arbitrary programs.
- The frozen control ran from a byte-verified copy of the accepted `final_source_v2` snapshot. Isolation probes (`isolation/`) and every control row's recorded import paths show that `research` resolved to the snapshot workspace, and production modules matched their protected hashes.

## 2. Original versus current versus optimized index method

Population: 200 fresh programs from the unchanged generator, seeds 810000–810199, 40 per family, 15 technical repetitions each. They are new instances of the same generator, not new distributions and not the private grader.

- **Primary (single optimization primary).** `selected_nonmodel` (NEW controller, `cap512_wider`, cached build) against `frozen_phase2` (accepted `structural_bound`), both at 0.1 s:
  - effect **+0.04513**, 95% interval [+0.03365, +0.05754], verdict **SUPPORTS_IMPROVEMENT**;
  - about **4.41% lower geometric J** (interval 3.31% to 5.59%);
  - 73 wins, 126 ties, 1 loss;
  - per-family means: aliasing 0.0326, dependency 0.0309, mixed 0.0480 (the 1 loss), scalar 0.0582, vector 0.0560.
- **Descriptive at 0.1 s** (unadjusted 95% intervals):

  | control | effect of selected_nonmodel | 95% interval | W/T/L |
  |---|---|---|---|
  | accepted_budgeted (original, 0.1 s) | +0.0752 | [+0.0602, +0.0913] | 105/95/0 |
  | accepted_default (original, unbudgeted) | +0.0713 | [+0.0568, +0.0866] | 102/98/0 |
  | accepted_bootstrap | +0.0861 | [+0.0682, +0.1052] | 108/92/0 |

  The current Phase 2 control reproduces its accepted gain on this fresh cohort: `frozen_phase2` vs `accepted_budgeted` is +0.0301 [+0.0197, +0.0415], 47/153/0.
- **Other budgets.**
  - At 0.01 s the gain over `frozen_phase2` shrinks to +0.0132 [+0.0043, +0.0232], with **13 program losses** (26/161/13).
  - At 1.0 s it is +0.0523 [+0.0405, +0.0648], 83/117/0.
  - The gain is budget-sensitive; it is not uniform.
- **Development.** The selection used only the old 100 programs (seeds 800000–800099). Development effect of the selected configuration: +0.0460, 36/64/0. Configurations were selected before any fresh row existed (`FROZEN_SELECTION.json`, sha256 `094198e448f8…`).

## 3. Classical quality and cost

- Against unbudgeted classical at 0.1 s: +0.0892 [+0.0686, +0.1106], with **118 wins, 60 ties and 22 losses**. At 1.0 s: +0.0963, 122/58/20.
- Classical still wins on 20–33 programs depending on budget. The data do not say whether those outcomes are reachable within our frozen domains; no reachability claim is made.
- Compile cost against classical at 0.1 s:
  - geometric compile-time ratio **76.2×** [66.0, 88.1];
  - process-time ratio 3.21×;
  - median compile 0.100 s vs 0.0008 s.

## 4. Runtime cost of the optimization

- Against `frozen_phase2` at 0.1 s:
  - geometric compile ratio **11.86×** [10.87, 12.89];
  - process ratio 2.14× [2.04, 2.23];
  - median compile 0.1004 s vs 0.0053 s.
- The selected policy runs to the 0.1 s deadline in 1,605 of 3,000 rows; it completes its pass in the rest. Maximum overshoot 0.41 ms. Peak RSS at most 29.1 MB.
- It is a quality gain bought with deadline-bounded search. **It is not a compile speedup and not an equal-work comparison.**
- At 1.0 s the compile ratio against frozen is 20.4×.
- The cached engineering build is semantics-preserving: equal outputs under deterministic work limits. On development at 0.1 s it lowered geometric compile time to 0.962× [0.950, 0.973] of the reference build, with quality not lower (+0.00013, 1/99/0).

## 5. Finite public score versus private generalization

- Exact fixed eight-program public suite, 15 repetitions, pinned formula, re-measured serial denominator equal to the frozen records (120 rows):

  | arm | score |
  |---|---|
  | `selected_nonmodel` @0.1 s | **2.1027466543513094** |
  | `selected_nonmodel` @1.0 s | 2.1027466543513094 |
  | `selected_nonmodel` @0.01 s | 2.0736243061428388 |
  | frozen Phase 2 | 2.0327602339438613 |
  | original direct | 2.008466202284657 |
  | classical | 1.9013791212645499 |

- Every paired score ratio is above 1+1e-12 in all 15 repetitions:

  | selected_nonmodel against | score ratio |
  |---|---|
  | original direct | 1.04694 |
  | frozen Phase 2 | 1.03443 |
  | classical | 1.10591 |

- Program by program against original direct and against frozen Phase 2, two programs improve and six are equal:
  - mixed_broadcast: J 240 → 144;
  - vector_reduction: J 480 or 396 → 384.
- Against classical, five programs are better, three equal and none worse, by J.
- One-program-removed sensitivity keeps every ratio above 1 (`PUBLIC_SCORE.md`).
- The standalone export reproduces 2.1027466543513094 in its own isolated workspace. The unchanged `score.py` prints 2.103x.
- **This is exact arithmetic on a fixed suite. It is not a significance test, not a private-grader result and not evidence about the 16-program grader's hidden half.**

## 6. Fixture-model benefit versus end-to-end model benefit

- **Original H4** (historical `_r3`): INCONCLUSIVE, unchanged.
- **H4_NEW: INCONCLUSIVE.**
  - All 30 qualified evaluation fixtures (6 per family) are accounted for, 5 families are informative by the frozen design, and there are 0 defects.
  - But every contrast at every budget is exactly 0: selected model (depth 1) against one_bit, against uniform_bits (10 seeds) and against empirical_cover, each with interval [0, 0] and 0/30/0.
  - No arm validated a single object below the best training label (0 validated discoveries in 17,550 rows).
- **Post-hoc design diagnosis.** This is a diagnostic, not used for any decision. In all 30 evaluation fixtures and all 15 development fixtures, the training split already contains the minimum J of the whole feasible set. The frozen endpoint min(min_training_J, test discoveries) therefore could not differ from min_training_J for any arm. H4_NEW was untestable as specified on these fixtures. That is a limitation of the qualification rule, which did not require test-only headroom, not evidence that models cannot help.
- Depth 1 was chosen by the tie rule: both depths gave exactly 0.0 on development.
- Depth-1 expansion and one_bit produced identical novel, invalid, dead-end and complete counts (33,645 novel proposals each at 0.1 s). This is consistent with the analytic equivalence recorded concurrently in `plan/PHASE2_SCIENTIFIC_RESEARCH.md`, which was written by another agent, not this assignment.
- **End-to-end model compiler: BLOCKED_BY_H4_NEW.** 9,000 fresh and 360 public rows and the model export did not run. No end-to-end model benefit is claimed.

## 7. Remaining losses and costs

- 1 fresh-program loss against frozen Phase 2 at 0.1 s, and 13 at 0.01 s.
- 22 losses against classical at 0.1 s.
- About 12× compile time against frozen Phase 2 and 76× against classical.
- About 54% of rows at 0.1 s end on the deadline, so quality is budget-sensitive.
- The per-query construction-expiry correction never triggered in measurement.

## 8. What would require another experiment

- A private-grader or other-distribution claim, which needs different programs.
- Any population claim beyond this generator.
- A model-benefit claim, which needs fixtures qualified with explicit test-only headroom (for example min_test_J < min_training_J) or a different endpoint.
- An equal-work or speed claim.
- A statement that classical wins are unreachable, which needs domain exclusion or exhaustive evidence.
- Global optimality.
- Using `cap512_wider` at a different budget as a separately "selected" policy; only 0.1 s was selected.
