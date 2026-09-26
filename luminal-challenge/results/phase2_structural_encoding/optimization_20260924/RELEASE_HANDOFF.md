# RELEASE_HANDOFF — Phase 2 optimization, public score and model evaluation (protocol 1.0)

**Status: READY_FOR_CODEX_REVIEW**

- Implementer: Claude Code, 2026-09-24. Nothing here is self-accepted.
- No paper, production source, tracked plan, `STATUS.md` or historical result was edited. Nothing was committed, pushed or submitted, and no other agents were launched.
- Run of record: `results/phase2_structural_encoding/optimization_20260924/`, about 398 MB, 68,904 measured rows.

## Answers

- **Which method improved, and on what metric and population?** The NEW selected non-model controller (`cap512_wider`: query cap 512, four-operation windows followed by appended eight-operation windows at time slack 4; cached build; 0.1 s allowance).
  - On 200 fresh generated programs (seeds 810000–810199, 40 per family), paired log(J_frozen_phase2/J_selected) at 0.1 s = **+0.0451, 95% [+0.0337, +0.0575]**. That is about 4.4% lower geometric J; 73 wins, 126 ties, 1 loss. **SUPPORTS_IMPROVEMENT.**
  - Descriptively (unadjusted intervals) it also beats original direct at the same budget, +0.0752 [+0.0602, +0.0913] with 0 losses, and classical, +0.0892 [+0.0686, +0.1106] with 22 losses.
  - Exact fixed public-suite score: 2.10275, against frozen Phase 2 2.03276, original 2.00847 and classical 1.90138. The gain is strict in all 15 repetitions. Two programs improve (mixed_broadcast, vector_reduction); the rest are equal.
- **At what compile cost?** Geometric compile time is 11.9× frozen Phase 2 [10.9, 12.9] and 76× classical; process time is 2.1× frozen. Median compile is 0.100 s; the policy runs to its 0.1 s deadline in 54% of rows. This is a quality gain, not a speedup.
- **What failed or did not run?**
  - H4_NEW is **INCONCLUSIVE**: every contrast is exactly 0 on all 30 fixtures. A post-hoc diagnosis shows the frozen fixture design had no test-only headroom: in 45 of 45 fixtures the training split already held the global minimum J.
  - The end-to-end model compiler arm (9,000 + 360 rows) and the model export are **BLOCKED_BY_H4_NEW**.
  - The depth-1 descriptive arm is not applicable, because depth 1 was selected, by a tie at 0.0.
  - 0 failed rows anywhere.
- **What the evidence cannot claim:** private-grader performance; populations beyond this generator; equal-work speed; global optimality; reachability of classical wins; any model-learning benefit. See `CLAIMS_AND_LIMITATIONS.md`.

## Where to look

| What | Path |
|---|---|
| Requirement to artifact map | `READINESS_MATRIX.md` |
| Stage A reproduction and bottlenecks | `DIAGNOSIS.md`, `stage_a/` |
| Development decisions (selection arithmetic, engineering, ablation, depth) | `DEVELOPMENT_SELECTION.json`, `selection/*.json` |
| Freeze | `FROZEN_SELECTION.json`, `frozen_expected/`, `FRESH_COHORT.json`, `SOURCE_MANIFESTS/frozen/` |
| Fixtures and rejection ledgers | `fixtures/{development,evaluation}/` (`FIXTURE_QUALIFICATION.jsonl`, `MANIFEST.json`, `*/record.json`, `oracle.json`, `split.json`) |
| Raw rows, commands, manifests, resume records | `stages/<stage>/{rows.jsonl,commands.jsonl,EXPECTED_KEYS.json,STAGE_MANIFEST.json,resume_log.jsonl}`, `logs/` |
| Results | `COMPARISON.json/.md`, `PUBLIC_SCORE.json/.md`, `MODEL_EVALUATION.json/.md` |
| Export | `export/nonmodel/compiler.py`, `compiler_MANIFEST.json`, `EXPORT_VALIDATION.json`, `pinned/` |
| Checker, independent audit, final checks | `CHECKER_REPORT.json`, `INDEPENDENT_AUDIT.json`, `final_checks/` |
| Source | `SOURCE_MANIFESTS/{starting,frozen,final}/`, `SOURCE_MANIFESTS/final/AUTHORIZED_PARAMETERISATION.diff` |
| Repairs | `REPAIRS.jsonl` |

## Source ownership and changes

- New, owned files:
  - `research/optimization_{common,search,worker,frozen_worker,runner,analysis,report,fixtures,models,model_worker,export,export_validation,checker,audit,stage_a,profile}.py`;
  - `research_tests/test_phase2_optimization.py` and `research_tests/test_phase2_optimization_evidence.py`.
- Authorized backward-compatible parameterisation, with defaults preserved and the 286 inherited tests passing:
  - `run_structural_experiments.matched_window_record(time_slack=dk.TIME_SLACK)`;
  - `structural_encoding.Domain.from_record(record, memo=None)`.
  - Both are in `AUTHORIZED_PARAMETERISATION.diff`.
- `optimization_search.windows_of_size` restates `direct_optimizer.windows_for` at a variable size, because the production owner may not be edited. A test asserts equality with the owner at size 4 on 216 cases.

## Deviations, interpretations and disclosures (for review)

1. **Isolation repair before any measured row** (`REPAIRS.jsonl`). A relative `--run` path made the frozen workspace path relative, and the first isolation probe imported the modified research tree. The probe FAILED. The failure is retained in `isolation/superseded/`, the runner now resolves the path, and the frozen worker refuses relative paths. 0 rows affected.
2. **Added after the freeze.** `optimization_checker.py`, `optimization_audit.py`, `optimization_export_validation.py` and the evidence mutation tests were written after the freeze. None of them is imported by any worker, estimator or report. Every file hashed in the freeze is unchanged (checker `POST_FREEZE_SOURCE_*` = 0).
3. **Checker rerun.** The first checker run reported a single `PACKAGE_VERIFY` finding, because it called the package verifier in full starting-hash mode. That mode necessarily fails after the authorized edits. I changed the checker to the package's `--policy-only` mode, with an explicit authorized-edit allowlist check, and reran. The first report was overwritten; this disclosure replaces it.
4. **Old checker.** Two attempts to run it on accepted source failed for environmental reasons: first a workspace without `reference.json`, then a tree not nested under a repository root. Both are retained (`final_checks/old_policy_checker_on_frozen_source.*`, `final_checks/superseded_repo_root_*`). The third, in a repository-shaped temporary tree, reproduced the lead's result: 0 findings, P4 INCONCLUSIVE, exit 2.
5. **Interpretations fixed before any evaluation outcome.**
   - Fixture candidate tuples are iterated per order as "first two, then first three".
   - Learners validate only decoded objects whose J is below the best training label; only those can change either endpoint.
   - The tie-break "geometric compile time" is the geometric mean over programs of the per-program median `compile_seconds` at 0.1 s.
   - The aggregate node ceiling is enforced on charged nodes, including the node that trips a meter.
   - The frozen control is the accepted `run_measurement` entry point, run from a byte-verified snapshot copy.
   - The cached build memoises program validation, facts and incumbent validation within one compilation only.
6. **Selection tie.** `cap512_wider` and `capnull_wider` had identical development effects, +0.046034. The rule's first tie-break chose `cap512_wider`: geometric compile 0.05689 s against 0.05698 s, a near-equal difference, applied as written.
7. **Concurrent workspace edits by others.** During this run, other work added `plan/CLAUDE_PHASE2_RESEARCH_PROTOCOL.md`, `plan/PHASE2_SCIENTIFIC_RESEARCH.md`, `plan/phase2_research/` and `../self-improving/`, and edited `plan/STATUS.md`. I did not touch them (`SOURCE_MANIFESTS/final/GIT_STATUS.txt` against `starting/`).
8. **Evidence mutation tests depend on the run of record.** They skip only if it is absent; in the final run all 22 executed and passed.
9. **Budget sensitivity.** In each of the export's 624 rows, J was one of the values observed for that program in the research rows, and never above the program's direct bootstrap. Deadline-bound policies can vary with machine load; no identical-J guarantee is claimed.

## Failure rates and denominators

- 0 of 68,904 measured rows failed.
- 0 validator discrepancies.
- 0 timeouts (20 s external limit).
- 0 missing and 0 duplicate keys across 7 stages. Expected ledgers equal the frozen ledgers, and the auditor also re-derived them from the written schedule rule.

## Open blockers

- None for the non-model release.
- The model-benefit question stays open. A new lead-issued protocol would need fixtures with test-only improvement headroom, or a different endpoint, before any model compiler arm can be authorized.

## Resume and re-verification commands (from `luminal-challenge`)

```
PY=../venv/bin/python; export PYTHONPATH=.reference:.
RUN=results/phase2_structural_encoding/optimization_20260924
$PY plan/phase2_optimization/verify_package.py --policy-only
$PY -m research.optimization_checker --run $RUN --output /tmp/checker.json
$PY research/optimization_audit.py --run $RUN --output /tmp/audit.json
$PY -m unittest discover -s research_tests
# Stages resume only missing keys under an identical stage manifest, e.g.:
$PY -m research.optimization_runner --run $RUN --stage D_fresh_compiler
```
