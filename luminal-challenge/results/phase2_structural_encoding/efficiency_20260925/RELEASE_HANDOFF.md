# RELEASE_HANDOFF: Phase 2 assurance and propagation efficiency (protocol 1.0)

**Status: READY_FOR_CODEX_REVIEW.** This is not self-accepted; only Codex accepts.

- **Path:** `luminal-challenge/results/phase2_structural_encoding/efficiency_20260925/RELEASE_HANDOFF.md`
- **Implementer and authority:** Claude Code, 2026-09-25, working to
  `plan/CLAUDE_PHASE2_EFFICIENCY_PHASE.md` v1.0 and
  `plan/phase2_efficiency/PROTOCOL.json`, which is locked.
- **Package verifier:** PASS at the start (`SOURCE_MANIFESTS/starting/`) and at
  the end (`final_checks/verify_package.*`). Both runs cover 4 package files and
  120 protected inputs.
- **Outcome in one line:** Gate R is closed and R0 is frozen. Gate P stops as
  **NO_JUSTIFIED_OPTIMIZATION**, a valid outcome under plan §4. No E1 was
  implemented. The E and C measurements were not run, as the plan requires.
- **Measurement process time:** **0.026 h** against the 24 h cap
  (`MEASUREMENT_WALL_LEDGER.jsonl`, 654 charged processes). This covers the
  replay, the guard controls, the R0 acceptance and the Gate P profile.
- **What I did not do:** no commits, pushes, publication, agents, process
  termination, production integration or manuscript edits.
  - No pre-existing source or historical result changed: 109 sources and 877
    result files match the starting manifests (`final_checks/FINAL_STATE.json`).
  - Git status outside my own files is identical at start and end
    (`final_checks/git_status_end.txt`).
  - Every file I created falls under `research/efficiency_*.py`,
    `research_tests/test_efficiency_*.py` or this directory.

## Answers

1. **Is construction interruption accounting complete? Yes, in R0.**
   - The lead probe now reports 1 interruption and 1 overrun (0.9 s past the
     deadline). The query status is `UNKNOWN_DEADLINE`, the cap proof is kept as
     a late diagnostic, and nothing is accepted. The parent reports 0.
   - Every initialization exit is covered, crossed with exact-equality,
     query-only and overall expiry.
   - Model-phase late validations are counted.
   - Search decisions and clock-reading counts equal the parent's.
   - See `ASSURANCE_CLOSURE.md` §R1.
2. **Does the auditor enforce what it states? Yes.**
   - On the unchanged release the successor auditor passes: 162,982 checks,
     0 findings, 0 unmapped fields.
   - It fails the lead's mutation (`LEARNING_CONTRASTS` ×6) and all 21 other
     planted mutations.
   - Its field-to-check map covers 8,591 leaves: 6,421 checked, 2,170 declared
     with reasons, 0 unmapped. It never claims complete coverage.
   - See §R2 and `AUDIT_COVERAGE.json`.
3. **Are source and ranker provenance resolved? Yes, narrowly.**
   - The historical checker still FAILs, and that result stands.
   - Its 1 + 420 findings match dispositions D1 and D2 exactly, with every
     precondition verified. The result is
     `PASS_WITH_APPROVED_HISTORICAL_DEVIATIONS` with 0 unapproved.
   - All 420 orderings replay under an import- and open-denying guard in a
     minimal workspace, with identical indices, digests and models.
   - See §R3.
4. **Can this learner collect 20 observations before model preparation? No.**
   - At most 1 is possible, by construction, whatever the propagation speed.
   - The architecture is retired. See `LEARNER_CLOSURE.md`.
5. **Is there one justified optimization? No.**
   - The most wasteful work is the issue-capacity scan: 99.48% of 4.6 M value
     checks find nothing.
   - Even at zero cost, removing it gives an equal-family fixed-work ratio of
     only **0.819**. Every other single component is above 0.80 as well.
   - Only the whole fixpoint (ceiling 0.582) could reach 20%, and that is the
     worklist mechanism already measured at 4.8%.
   - The measured cost model predicts 0.939 for the best mechanism (M1).
   - Caches are unjustified: exact repeated inputs are 0.3–2.6% of calls.
   - See `PROFILE.md`, `MECHANISM_PROPOSAL.json` and `DEVELOPMENT.json`.

## Deliverables

| Plan item | Path |
|---|---|
| ASSURANCE_CLOSURE.md, LEARNER_CLOSURE.md, AUDIT_COVERAGE.json | this directory |
| Lead probes before and after | `assurance/lead_probes/LEAD_PROBES_BEFORE_AFTER.json` (`research/efficiency_probes.py`) |
| Successor audit and field map | `assurance/successor_audit/`, `assurance/successor_audit.{stdout,exit}` |
| Successor checker, full historical findings | `assurance/checker/EFFICIENCY_CHECKER.json`, `HISTORICAL_CHECKER_FULL.json` |
| Mutation outputs | `research_tests/test_efficiency_audit.py` (22) and `test_efficiency_checker.py` (9), in `r0_checks/efficiency_suite_live.log` and `r0_checks/full_suite_live_tree.log` |
| Guarded ordering replay | `ranker_replay/` (`WORKSPACE_MANIFEST`, `GUARD_CONTROLS`, `rows.jsonl`, `REPLAY_REPORT`, `REPLAY_EVALUATION`, `PROVENANCE_HASHES`) |
| Snapshots and diffs | `repair/source/` (parent and R0 bytes, diff, `SHA256SUMS`); `SOURCE_MANIFESTS/starting/`; `r0_checks/SNAPSHOT_VERIFICATION.json` |
| R0 freeze, export, acceptance | `R0_FREEZE.json`, `r0_export/compiler.py` (`74c87b69…`), `r0_export/acceptance/ACCEPTANCE.json` |
| PROFILE.md, MECHANISM_PROPOSAL.json, DEVELOPMENT.json | this directory; raw rows in `profile/rows.jsonl`, aggregate in `profile/PROFILE.json` |
| Freeze, comparison, public and export artifacts of E and C | **not applicable**: E and C not run (0 of 600 + 600 + 2,000 + 6,000 + 280 + 624 rows, by rule). Seeds 980000–980199 were never generated, and no candidate outcome exists. |

## Tests (exact counts)

| Suite | Source view | Result |
|---|---|---|
| New `test_efficiency_*` suite: R1 14, inherited-on-R0 38 + 1 coverage, closure 4, ranker 5, audit 22, checker 9 | live tree | **93 OK** |
| Everything in `research_tests/`: 443 inherited + 93 new | live tree | **536 OK** |
| Inherited suite | verified original-source snapshot, 74/74 files hash-equal | **442 OK, 1 FAIL**: snapshot-only, passes live (disclosure 2) |
| Public tests (`.reference/tests`) | live tree | 11 OK |
| Pinned public tests and score | isolated export workspace | exit 0 / exit 0 |

## Deviations and disclosures

1. **Replay pass predicate, attempt 1.** The first and only execution of the 420
   replays used a substring marker test. It flagged the standard library's
   `importlib.machinery` as `machine`, so `REPLAY_REPORT.json` says `passed: 0`.
   Every row nonetheless records identical indices, digests and models, and no
   refused open or import. I did **not** re-execute the replays.
   `--evaluate` re-scored the retained rows with a component-exact predicate
   (`REPLAY_EVALUATION.json`: 420/420). Both files are retained. The checker's
   D2 disposition depends on the evaluation and on the rows hash it records.
2. **One inherited test fails only in the snapshot.**
   `test_phase2_repair.R3DependencyGate.test_a_real_resumed_run_retains_checker_resolvable_transitive_links`
   compares a freshly computed checker-report hash in a repository-shaped
   snapshot, whose `.git` is empty and whose entries are symlinks. It passes on
   its own in the live tree and inside the 536-test live run. Logs are in
   `r0_checks/snapshot_failure_rerun_{live,snapshot}.log`. It is recorded, not
   waived.
3. **Profiler tooling changed during Gate P, before any proposal.**
   `efficiency_profile.py` gained three things after the first pass:
   - a `timers_split` mode, which splits rule 2 into its EO part and its scan;
   - a `parity` mode;
   - the ceiling aggregation.

   The first-pass rows (`timers`, `profile`) are retained unchanged. The final
   split is decision-identical on all 10 programs. The profiler is diagnostic;
   it is not a frozen or measured source.
4. **The fixed-work definition is taken literally.** R0 runs with every default
   limit, including the 0.1 s query allowance, 2 ms slices, the 2,048-node slice,
   8 resident queries, the 4,096 frontier and a 10,000-node aggregate. It runs
   under a constant clock, so no wall expiry fires. The real time of the
   complete compile call is measured separately. All 10 profiled searches
   exhausted their catalogs inside the ceiling (8,827 nodes).
5. **Ceilings use equal-family geometric means of per-program shares.** Shares
   come from lightweight timers (1.02–1.29× inflation) divided by the
   unprofiled median of 3 fresh processes. cProfile's 3.64× distortion is
   reported but not used for decisions. The machine load average was about 2.5
   on 28 cores throughout, from other users' processes. I ran no test or
   measurement of my own beside the profile.
6. **Historical checker, complete findings.** A driver calls the unchanged
   `next_round_checker.Checker` and records its full `findings` list. The
   checker's own JSON keeps only the first 200.
7. **Auditor classes declared unchecked.** These are listed with reasons in
   `AUDIT_COVERAGE.json`: `CONFIRMATION_COHORT.json` legality metadata (1,693
   leaves), source-hash tables owned by the checker, pinned-workspace identity
   strings, free text, timestamps, and `decode_mismatches` (which needs the
   codec).
8. **Historical construction counts.** The next round's construction-interruption
   totals, for example 75 and 76 in `COMPARISON.json`, follow the incomplete
   nonterminal-only definition (F1). They are historical and not restated. R0's
   definitions apply only to rows produced by R0.

## Rerun commands (from `luminal-challenge`)

```sh
../venv/bin/python plan/phase2_efficiency/verify_package.py
RUN=results/phase2_structural_encoding/efficiency_20260925
python3 research/efficiency_audit.py --run results/phase2_structural_encoding/next_round_20260925 --output NEW_DIR
PYTHONPATH=.reference:. ../venv/bin/python -m research.efficiency_checker --run $RUN --audit $RUN/assurance/successor_audit/SUCCESSOR_AUDIT.json --output NEW_DIR
PYTHONPATH=.reference:. ../venv/bin/python -m research.efficiency_replay --run $RUN --evaluate   # re-scores, never re-executes (evaluation file is immutable: use a copy)
PYTHONPATH=.reference:. ../venv/bin/python -m research.efficiency_probes --out NEW_DIR
PYTHONPATH=.reference:. ../venv/bin/python -m research.efficiency_export --variant R0 --out NEW_DIR --run $RUN
PYTHONPATH=.reference:. ../venv/bin/python -m research.efficiency_profile --run $RUN --aggregate-only
PYTHONPATH=.reference:. ../venv/bin/python -m unittest discover -s research_tests -p "test_efficiency_*.py"
```
