# RELEASE_HANDOFF: Phase 2 next round (protocol 1.0)

**Status: READY_FOR_CODEX_REVIEW.** This is not self-accepted. Two classes of
checker finding are open for the lead to review; both are explained in
"Deviations and disclosures" below.

- Implementer: Claude Code, 2026-09-25. Authority: `plan/CLAUDE_PHASE2_NEXT_ROUND.md`
  v1.0 and `plan/phase2_next_round/PROTOCOL.json`. The package verifier passed at
  the start and at the end (`SOURCE_MANIFESTS/starting/`, `final_checks/verify_package.*`).
- Run of record: `results/phase2_structural_encoding/next_round_20260925/`.
  It holds 18,294 measured rows, 0 failed and 0 timed out. Measurement wall time
  was **0.598 h** against the 24 h cap.
- I made no commits, pushes or submissions, launched no agents and terminated no
  processes. No production, frozen research, historical result, reference, plan,
  STATUS or manuscript file was edited. Git status is identical at start and end,
  and every pre-existing research and production file hashes as it did at the start.

## Answers to the four questions

1. **Can interruption accounting be repaired without changing search decisions? Yes.**
   The successor `research/next_round_search.py` (sha `b982d4cf…`) returns 1 for the
   lead's probe; the frozen owner returns 0. In both, 0 candidates are accepted and
   all 9 queries end UNKNOWN_DEADLINE. At equal work under a deterministic clock the
   successor makes the same decisions as the frozen owner: identical traces,
   incumbents, statuses and certificate streams. The regression class fails 9/9 on
   the frozen owner and passes 9/9 on the successor. See `REPAIR.md`.
   On the confirmation cohort the repaired accounting now reports real counts:
   repaired A4 had 9 interrupted validations (9 queries) and 75 construction
   interruptions over 3,000 rows. Historical counts stay unknown.
2. **Which delivered optimizer gives better quality for a given cost? Repaired A4.**
   The primary result, prespecified and on 200 fresh programs × 5 repetitions at
   0.1 s, is mean paired log(J_cap512_wider / J_A4) = **+0.0312**, 95%
   [+0.0182, +0.0460]: **FAVOURS_A4**, about 3.1% lower geometric J. A4
   wins/ties/losses are 55/123/22, and its geometric compile-time ratio to the
   earlier optimizer is 0.978, so the costs are about equal.
   On the fixed public suite the earlier optimizer still scores higher
   (2.102747 against 2.088945), which reproduces both earlier recorded scores
   exactly. The generated-population result and the eight-program public result
   point in opposite directions. Both are reported; neither overrides the other.
3. **Catalog or traversal? The catalog.** In the development 2×2 at 0.1 s, the
   catalog main effect is −0.0624 log J (95% [−0.084, −0.043]). The traversal
   effect is +0.0020 (95% [−0.003, +0.007]) and the interaction +0.0075
   ([−0.003, +0.017]); both intervals span zero. Propagation is 75–83% of A4's
   profiled time. See `FACTORIAL.md` and `BOTTLENECKS.md`.
   The development rule selected `cell_a4cat_dfs`, the A4 catalog with
   depth-first traversal. On confirmation it is descriptively best: J ratio 0.959
   against the earlier optimizer and 0.989 against A4, with compile ratios 0.916
   and 0.937. Against A4 the J ratio's 98.75% upper bound is 0.9997, above the
   0.98 target, so **neither practical route passes: TARGET_NOT_REACHED**.
4. **Can the ranker prioritise useful unseen objects, and can a real query afford
   it? No on both gates.**
   - **Mechanism: FAIL_OR_INCONCLUSIVE.** Both sensitivity gates passed (15/15
     development and 30/30 fresh fixtures informative). The tree **loses to
     Hamming order on all 30 fixtures**: yield difference −0.107, 98.33%
     [−0.132, −0.084]. It beats random (+0.061, [+0.033, +0.098]). Against
     shuffled labels its lower bound is positive but its point estimate, 0.045,
     is below the 0.05 minimum gain.
   - **Economics: ECONOMICALLY_UNAVAILABLE.** 0/100 development programs had a
     query reaching 20 case-validated observations. Of 1,639 learner queries only
     33 reached the search-half boundary, with at most 1 distinct observation
     there. Per the plan, the non-model compiler is retained and effort is
     redirected to the measured solver bottleneck, propagation. No learned-compiler
     test is proposed.

## The five categories the plan asks to keep apart

| Category | Claim | Where |
|---|---|---|
| Reporting repair | R1 fixed in a versioned successor, with no decision change | `REPAIR.md`, `repair/` |
| Correctness evidence | 443 research tests OK (392 inherited + 51 new); acceptance on 142 programs / 277 cases for 4 cells + variant; production verification PASS; export PASS; auditor PASS | `final_checks/`, `repair/acceptance/`, `repair/production/`, `export/candidate/` |
| Measured enhancement | Repaired A4 > earlier `cap512_wider` on this generator population at 0.1 s (primary). The candidate reaches neither pre-registered route. The worklist variant was not frozen (4.8% < 10%) | `COMPARISON.*`, `ENGINEERING_DECISION.json` |
| Mechanism-only learning | Tree < Hamming on novel elite yield; secondary endpoint saturated in 27/30 fixtures | `LEARNING_FEASIBILITY.*` |
| Economic availability | Unavailable: observations do not accumulate within a query | `LEARNING_FEASIBILITY.*`, `stages/L_acquisition/` |

Unresolved: the public suite ranks the earlier optimizer above repaired A4 while
the generated cohort ranks A4 above it. The frozen candidate also scores highest
on the public suite (2.187957, strict in all 5 repetitions). That is descriptive
only: public programs were development-visible, and nothing about the private
grader or other generators is claimed. Whether propagation can be made
substantially cheaper remains open. The worklist change removed only about 5%.

## Denominators

| Stage | Expected | Observed | Failed | Timed out |
|---|---:|---:|---:|---:|
| D_factorial | 4,500 | 4,500 | 0 | 0 |
| D_fixed_work | 120 | 120 | 0 | 0 |
| D_profile (separate, not timing) | 150 | 150 | 0 | 0 |
| E_engineering | 900 | 900 | 0 | 0 |
| C_confirmation (9,000 arms + 2,000 controls) | 11,000 | 11,000 | 0 | 0 |
| C_public (K = 3: 480) | 480 | 480 | 0 | 0 |
| export/candidate | 624 | 624 | 0 | 0 |
| L_acquisition | 100 | 100 | 0 | 0 |
| L_orderings | 420 | 420 | 0 | 0 |

Every stage reports `sources_unchanged_during_stage: true`.

- **Independent auditor** (`INDEPENDENT_AUDIT.json`): PASS, **52,013 checks**,
  0 findings, nothing left unaudited. It imports no experiment code.
- **Checker** (`CHECKER_REPORT.json`): 113,996 checks. Its findings are exactly
  1 × `FROZEN_SOURCE_CHANGED` and 420 × `ORACLE_LEAK`, explained under items 1–2 below.

## Deviations and disclosures (for review)

1. **Post-freeze reporting fix.** After C_confirmation completed, `report --part
   comparison` crashed. Control rows record `None` for timings they do not have
   (for example, classical `bootstrap_seconds`), and `next_round_analysis.
   per_program_median` did not skip `None`. I changed four lines in that owner to
   skip `None`; I did not monkey-patch it. The crash log, the at-freeze copy, both
   hashes and the affected outputs are in `POST_FREEZE_CHANGES.json` and
   `post_freeze/`. Only the descriptive cost entries of the unbudgeted controls
   are affected. The primary result, the candidate endpoints and the public
   scores do not use those fields, and the auditor recomputes them independently.
   The frozen checker correctly flags this file (`FROZEN_SOURCE_CHANGED` × 1).
   No measured source changed.
2. **Checker `ORACLE_LEAK` × 420.** The checker flags any ranker process that
   *loads* a module with oracle capability. `research.structural_oracle` is loaded
   through the existing owner's import chain (`schema_ranker → optimization_models
   → run_structural_experiments`). To check whether any oracle *data* was read, I
   re-ran all 420 ranker processes under a file-open audit hook
   (`final_checks/ranker_file_audit/RANKER_FILE_AUDIT.json`). The only data files
   opened were the 30 `RANKER_INPUT.json` files, and every ordering digest was
   identical to its row. The checker also verified that these inputs carry no
   identity, label or oracle field. I did not weaken the checker.
3. **Historical checker.** It rejects the added modules on the live tree (11
   `POST_FREEZE_SOURCE_ADDED`). In the verified snapshot its only findings are the
   41,040 location checks that a relocated tree cannot pass. The two views are
   reconciled exactly in `REPAIR.md`. The historical evidence tests (116) pass in
   the snapshot.
4. **Engineering prediction missed.** I predicted a 15–25% compile-time reduction
   (`ENGINEERING_PLAN.json`) and measured 4.8% [3.3%, 6.5%]. The variant also
   lowered development J slightly (0.0077 log J, 7/93/0), because more work fits
   in the budget. Under the rule, the parent was frozen.
5. **Interpretations fixed before use.**
   - `fixture_sha256` is the manifest `record_sha256`.
   - "Reached 20" is the learner's own gate: ≥20 distinct case-validated objects.
     The observed count at the boundary is also reported.
   - Fixed-work cells use budget key `work:N` in the arm-order hash.
   - A construction interruption means the allowance was spent before the first
     node, or no time was left at initialisation.
   - Geometric median compile time is exp(equal-family mean of log per-program
     median `compile_seconds`).
   - Controls and arms share one confirmation matrix, so their order is randomised
     together.
   - The earlier optimizer records no incumbent trajectory. Its target results are
     attainment only, not hitting times.
   - The worklist change is one mechanism applied to both fixpoints.
6. **Timing hygiene.**
   - L_acquisition ran while the fixture qualification (oracle enumeration) used
     another core on the 28-core machine. Its outputs are counts, and the
     diagnostic is not efficacy evidence.
   - Export rows were charged to the ledger after they ran. The cap was checked
     before the export started.
   - The first full-suite run in `repair/tests/` overlapped my addition of the
     optional `timers` hook. The authoritative runs are `prefreeze_checks/` and
     `final_checks/`, both 443 OK.
7. **Starting manifest.** `research/next_round_common.py` existed when the
   starting manifest was captured. It is listed separately, and every other
   research file matched.
8. **Acquisition worker imports.** The acquisition worker imports the frozen
   `objective_index_learned`, which loads the frozen solver module into that
   process. The controller actually called is the successor's
   `multiscale_optimise`; its rows carry `interrupted_validation_total`.

## Where to look

| What | Path |
|---|---|
| Repair and correctness review | `REPAIR.md`, `repair/` |
| Development diagnosis | `FACTORIAL.json/.md`, `BOTTLENECKS.json/.md`, `SELECTION.json` |
| Engineering | `ENGINEERING_PLAN.json`, `ENGINEERING_DECISION.json`, `repair/source/next_round_engineered.diff` |
| Freeze | `FROZEN_SELECTION.json` (sha `81c84844…`), `frozen_expected/`, `CONFIRMATION_COHORT.json`, `SOURCE_MANIFESTS/frozen/` |
| Confirmation and public | `COMPARISON.json/.md`, `PUBLIC_SCORE.json/.md`, `export/candidate/` |
| Learning | `learning/`, `LEARNING_FREEZE.json`, `LEARNING_FEASIBILITY.json/.md` |
| Rows, commands, manifests, resume logs, ledger | `stages/*/`, `logs/`, `MEASUREMENT_WALL_LEDGER.jsonl`, `PREFLIGHT_ESTIMATE.json` |
| Checks | `CHECKER_REPORT.json`, `INDEPENDENT_AUDIT.json`, `final_checks/`, `prefreeze_checks/` |
| Requirement map | `READINESS_MATRIX.md` |

Owned source: `research/next_round_{common,search,engineered,worker,profile,runner,analysis,report,checker,audit,export,acceptance,learning,ranker,acquisition}.py`
and `research_tests/test_next_round_{search,engineered,learning,evidence}.py`.

## Rerun commands (from `luminal-challenge`)

```sh
../venv/bin/python plan/phase2_next_round/verify_package.py
PYTHONPATH=.reference:. ../venv/bin/python -m research.next_round_runner --run "$PWD/results/phase2_structural_encoding/next_round_20260925" --stage <STAGE>   # only missing keys, identical manifest
PYTHONPATH=.reference:. ../venv/bin/python -m research.next_round_report --run <RUN> --part development|comparison|public|learning
PYTHONPATH=.reference:. ../venv/bin/python -m research.next_round_checker --run <RUN>
python3 research/next_round_audit.py --run <RUN>
PYTHONPATH=.reference:. ../venv/bin/python -m research.next_round_export --run <RUN>
PYTHONPATH=.reference:. ../venv/bin/python -m unittest discover -s research_tests -p "test_*.py"
```
