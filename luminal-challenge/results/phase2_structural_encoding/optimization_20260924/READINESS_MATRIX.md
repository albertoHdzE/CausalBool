# Readiness matrix — optimization protocol 1.0

Paths are relative to this directory unless they start with `research/` or `plan/` (relative to `luminal-challenge`). Commands run from `luminal-challenge` with `PYTHONPATH=.reference:.` and `../venv/bin/python` (written `PY` below). Verdicts are the implementer's; Codex decides acceptance.

| # | Requirement (plan section) | Artifact(s) | Command | Exit | Verdict |
|---|---|---|---|---|---|
| 0 | Package verified before editing (§2, prompt) | `stage_a/commands/package_verifier.*` | `PY plan/phase2_optimization/verify_package.py` | 0 | PASS |
| 0b | Inherited policy-only verifier | `stage_a/commands/inherited_policy_verifier.*`, `final_checks/inherited_policy_verifier.*` | `PY plan/claude_phase2_release/verify_package.py --policy-only` | 0 / 0 | PASS |
| 0c | Package after authorized edits | `final_checks/package_verifier_policy_only.*` | `... verify_package.py --policy-only` | 0 | PASS. Full starting-hash mode now exits 1 (`final_checks/package_verifier_full_starting_hashes.*`). This is expected: the two authorized parameterisations are listed in `SOURCE_MANIFESTS/final/AUTHORIZED_PARAMETERISATION.diff`. |
| 1 | HEAD/status/diff/environment, source snapshots (§2) | `SOURCE_MANIFESTS/starting/`, `SOURCE_MANIFESTS/frozen/research_source.tar`, `SOURCE_MANIFESTS/final/` | shell `git`/`tar`/`shasum` | 0 | PASS |
| 2 | Frozen control isolated from the modified tree (§2) | `frozen_control_workspace.json`, `isolation/probe_*.json`, per-row `result.imported_sources` | `PY -m research.optimization_runner --run RUN --stage setup` and `--stage probe` | 0 | PASS. The first probe failed on a relative path; that failure is retained in `isolation/superseded/` and `REPAIRS.jsonl`, with 0 rows affected. |
| 3 | A.1 tests, score recount, C/S/J, coexistence note | `stage_a/commands/research_tests_start.*`, `stage_a/PUBLIC_SCORE_REPRODUCTION.json`, `DIAGNOSIS.md` | `PY -m research.optimization_stage_a --out stage_a` | 0 | PASS (all agree to 1e-12) |
| 4 | A.2 stopping reasons, cap 64/100, 45 capped ties | `stage_a/STOPPING_AUDIT.json` | same | 0 | Verified from raw rows |
| 5 | A.3 development-only profile | `stage_a/PROFILE.json`, `DIAGNOSIS.md` | `PY -m research.optimization_profile --out stage_a` | 0 | PASS |
| 6 | A.4 regression/mutation tests | `research_tests/test_phase2_optimization.py` (20), `research_tests/test_phase2_optimization_evidence.py` (22) | `PY -m unittest discover -s research_tests -v` | 0 | 328 tests OK (`final_checks/research_tests_final.*`) |
| 7 | B: 8 configs × 3 budgets × 3 reps + 2,100 controls = 9,300 | `stages/B_search_development/` | `--stage B_search_development` | 0 | 9,300 of 9,300, 0 failed |
| 8 | B selection by the fixed rule | `selection/search.json`, `DEVELOPMENT_SELECTION.json` | `--stage decide --part search` | 0 | cap512_wider (tied with capnull_wider; lower geometric compile time) |
| 9 | Engineering pair 1,800 + adoption rule | `stages/B_engineering_pair/`, `selection/engineering.json` | `--stage B_engineering_pair`; `--stage decide --part engineering` | 0 | 1,800 of 1,800; cached build adopted |
| 10 | Bound ablation 1,800 (descriptive) | `stages/B_bound_ablation/`, `selection/ablation.json` | `--stage B_bound_ablation`; `--stage decide --part ablation` | 0 | 1,800 of 1,800 |
| 11 | C fixture construction, oracle-only qualification, ledgers | `fixtures/{development,evaluation}/FIXTURE_QUALIFICATION.jsonl`, `MANIFEST.json`, per-fixture `record/oracle/split.json` | `--stage qualify --part development` and `--part evaluation` | 0 / 0 | 15 of 15 and 30 of 30 filled, 0 collisions |
| 12 | Depth development: 270 rows, frozen depth | `stages/C_model_development/`, `selection/model.json` | `--stage C_model_development`; `--stage decide --part model` | 0 | depth 1 (tie at 0.0) |
| 13 | Fresh cohort frozen with reference-only legality and collision checks | `FRESH_COHORT.json` | `--stage fresh_cohort` | 0 | PASS: 200 programs, 40 per family, 0 collisions |
| 14 | FROZEN_SELECTION.json before any NEW evaluation outcome; expected ledgers; MDE | `FROZEN_SELECTION.json` (sha256 094198e4…), `frozen_expected/`, `selection/search.json` (`minimum_detectable_effect`) | `--stage freeze` | 0 | PASS. Measured sources unchanged since the freeze (checker). |
| 15 | D fresh matrix: 36,000 rows | `stages/D_fresh_compiler/` | `--stage D_fresh_compiler` | 0 | 36,000 of 36,000, 0 failed |
| 16 | D public 1,440 + serial 120 | `stages/D_public/` | `--stage D_public` | 0 | 1,560 of 1,560, 0 failed |
| 17 | H4_NEW evaluation: 17,550 rows | `stages/C_model_evaluation/`, `MODEL_EVALUATION.json/.md` | `--stage C_model_evaluation`; `PY -m research.optimization_report --part model` | 0 | 17,550 of 17,550; H4_NEW INCONCLUSIVE |
| 18 | Depth-1 descriptive arm (only if depth 2) | — | — | — | NOT APPLICABLE (depth 1 selected) |
| 19 | Conditional model compiler: 9,000 + 360 | — | — | — | BLOCKED_BY_H4_NEW |
| 20 | Primary comparison and descriptive contrasts/runtime | `COMPARISON.json/.md` | `PY -m research.optimization_report --part comparison` | 0 | SUPPORTS_IMPROVEMENT |
| 21 | PUBLIC_SCORE with independent formula, reconciliation, leave-one-out | `PUBLIC_SCORE.json/.md` | `--part public` | 0 | strict gain in all 15 repetitions against every control |
| 22 | Standalone export, pinned tests/score, 624 rows | `export/nonmodel/compiler.py` (sha256 ab669d02…), `compiler_MANIFEST.json`, `EXPORT_VALIDATION.json`, `pinned/` | `PY -m research.optimization_export_validation --run RUN --label nonmodel` | 0 | PASS: 624 of 624; pinned 11 tests OK; score.py 2.103x |
| 23 | Model export | — | — | — | BLOCKED_BY_H4_NEW |
| 24 | Evidence checker | `CHECKER_REPORT.json`, `logs/checker.*` | `PY -m research.optimization_checker --run RUN` | 0 | PASS, 0 findings |
| 25 | Independent numerical auditor | `INDEPENDENT_AUDIT.json`, `logs/audit.*` | `PY research/optimization_audit.py --run RUN` | 0 | PASS: 205,066 checks, 0 findings |
| 26 | Old policy checker on accepted frozen source | `final_checks/OLD_CHECKER_REPORT_r3_accepted_source.json`, `final_checks/old_policy_checker_on_accepted_source_tree.*` | `check_structural_evidence` inside a repo-shaped tree whose `research*/` are the accepted snapshot | 2 | 0 findings, internally consistent, P4 INCONCLUSIVE; same as the lead. On the current tree: 21 provenance-only findings, all from this assignment's new or parameterised files. Two earlier environment-shaped attempts are retained as `superseded_*` / `old_policy_checker_on_frozen_source.*`. |
| 27 | Production-control verification and comparison after timing | `final_checks/production_verification/`, `final_checks/production_comparison/`, `final_checks/production_export/compiler.py` | `PY verify_direct.py --stage all ...`; `PY compare_direct.py --repeats 3 --timeout 20 ...`; `PY export_direct.py ...` | 0 / 0 / 0 | PASS; all 8 gates pass; export sha d14bf39b… equals the retained export |
| 28 | CLAIMS_AND_LIMITATIONS and handoff | `CLAIMS_AND_LIMITATIONS.md`, `RELEASE_HANDOFF.md` | — | — | written |
