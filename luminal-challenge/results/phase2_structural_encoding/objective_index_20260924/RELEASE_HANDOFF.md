# RELEASE_HANDOFF — objective-index research protocol 1.0

**Status: READY_FOR_CODEX_REVIEW** (not self-accepted).

- Implementer: Claude Code, 2026-09-24/25. Protocol `plan/CLAUDE_PHASE2_RESEARCH_PROTOCOL.md`
  v1.0 (package verified at start and end). Supersedes the pending optimization campaign;
  its completed directory `optimization_20260924/` was found finished (no running process)
  and is untouched.
- Nothing committed, pushed or submitted; no agents launched; no production file, test
  harness, reference, plan, `STATUS.md`, paper or historical result edited. The paper/plan
  working-tree diffs predate this run (identical to `SOURCE_MANIFESTS/starting/git_diff.patch`).

## Answers

- **Selected solver (development rule, frozen before evaluation):** A4_multiscale_search.
  On 100 development programs at 0.1 s: +0.0663 vs A0 (46/54/0); A1 = A2 = A3 = +0.0063.
- **Fresh evaluation (200 programs × 15 reps, 0.1 s, Bonferroni 98.33%):** A4 vs A0
  +0.0623 [+0.0460, +0.0806]; vs accepted_budgeted +0.0917 [+0.0710, +0.1134]; vs classical
  +0.1118 [+0.0876, +0.1375]. All lower bounds > 0 → "best average output quality among
  these three controls at 0.1 s on this population". 20 per-program losses to classical.
- **Cost:** 11.65× A0 and 76.2× classical compile time (quality/cost trade-off, not speed).
- **Public (exact, fixed suite):** 2.0889454903, strictly above A0 2.0327602339, original
  2.0084662023 and classical 1.9013791213 in all 15 repetitions. Export reproduces it (3/3).
- **H_LEARN: FAIL** (all contrasts exactly 0 on 30/30 fixtures), predicted before evaluation
  from the frozen oracle/split: 0/30 fixtures had test headroom. **Learned compiler pair:
  BLOCKED_BY_H_LEARN** (implemented, frozen, tested; not run). Original H4: INCONCLUSIVE.
- **Theory:** expansion ≡ Hamming neighbourhood (general covers, proved + tested); integer-cap
  lemma; propagation soundness; tree partition — see THEORY.md.

## Denominators

| stage | expected | observed | failed |
|---|---|---|---|
| DEV_compiler | 5,700 | 5,700 | 0 |
| DEV_model | 2,025 | 2,025 | 0 |
| EVAL_model_wall | 20,250 | 20,250 | 0 |
| EVAL_model_work | 450 | 450 | 0 |
| EVAL_compiler | 63,000 | 63,000 | 0 |
| EVAL_public | 2,520 | 2,520 | 0 |
| EVAL_public_serial | 120 | 120 | 0 |
| export/nonmodel | 624 | 624 | 0 |
| EVAL_learned_tree / _shuffled_tree | 9,360 each | not run | BLOCKED_BY_H_LEARN |

Every stage reports `sources_unchanged_during_stage: true`. Checker: PASS, 116,859 checks,
0 findings. Independent auditor (imports nothing from `research`): PASS, 163,281 checks.
Final: 392/392 research tests; package verifier, production export/verify/compare exit 0.

## Where to look

| What | Path |
|---|---|
| Proofs, tested obligations | `THEORY.md`, `PRUNING_VALIDATION.json`, `pruning_replay/`, `theory/` |
| Diagnosis, recount reproduction | `DIAGNOSIS.md`, `stage_a/` |
| Research basis | `RESEARCH_BASIS.md` |
| Development and selection | `DEVELOPMENT.json` (table, ablations, sensitivity/MDE) |
| Freeze | `FROZEN_SELECTION.json` (sha256 96420d64…), `frozen_expected/`, `SOURCE_MANIFESTS/frozen/` |
| Fixtures | `fixtures/{development,evaluation}/` (ledgers, manifests, oracle, split), `theory/FIXTURE_RECIPE_PARITY.json` |
| Fresh cohort | `FRESH_COHORT.json`, `FRESH_COHORT_EXPOSURE_SCAN.json` |
| Raw rows, commands, manifests, resume logs | `stages/<stage>/`, `logs/` |
| Results | `COMPARISON.json/.md`, `LEARNING.json/.md`, `PUBLIC_SCORE.json/.md` |
| Export | `export/nonmodel/` (`compiler.py`, `compiler_MANIFEST.json`, `EXPORT_VALIDATION.json`, rows) |
| Checks | `CHECKER_REPORT.json`, `INDEPENDENT_AUDIT.json`, `final_checks/`, `prefreeze_checks/` |
| Claims | `CLAIMS_AND_LIMITATIONS.md` |

## Deviations and disclosures (for review)

1. **Post-freeze report wrapper.** The frozen `objective_index_report.comparison` crashed in a
   descriptive absolute-times table (the reused owner `optimization_analysis.absolute_times`
   assumes `attempted_queries` wherever `aggregate` exists; A4 records lack it). No frozen
   source was edited. `post_freeze/run_comparison_report.py` ran the frozen function
   unchanged, substituting only that helper with one guard (empty list omitted). Primary
   estimates were independently recomputed by the auditor. The crash log is retained
   (`logs/report_comparison.*`).
2. **Pre-freeze fixes found by dry runs:** an auditor path bug (`PUBLIC_SCORE.json` nesting)
   and two engineering changes after profiling (per-query digest reuse; incremental
   engine-capacity rule). All before any measured row or before the freeze respectively; the
   full test suite passed after each.
3. **Pre-freeze public observation:** the export trial (`theory/export_trial/`) printed a
   public score after selection was fixed; public programs are development-visible.
4. **Interpretations fixed before evaluation:** A2/A3 window list = A1's target-major window
   order, first occurrences (fallback memory-first if no target); A1–A4 use the tested
   per-compilation domain memo; "canonical rank tuple" = ranks in the codec's own decision
   order (times by operation, addresses in allocation order); tie-break "paired geometric
   compile time" = family-weighted mean log of per-program median compile time vs A0;
   learned sequential query: model half only after a time-limited search half, fresh
   re-search if data are insufficient; fixed-work prefixes count pool entries in order.
5. `run_structural_experiments` is embedded in the export as an exact two-function slice
   (per-function hashes recorded); all other modules are embedded byte-for-byte.

## Resume / rerun

From `luminal-challenge`: `PYTHONPATH=.reference:. ../venv/bin/python -m
research.objective_index_runner --run <abs run dir> --stage <STAGE>` (only missing keys
re-run, identical manifest required); reports `-m research.objective_index_report --run DIR
--part learning|public` and `post_freeze/run_comparison_report.py DIR`; checker `-m
research.objective_index_checker --run DIR`; auditor `python3 research/objective_index_audit.py
--run DIR`; export `-m research.objective_index_export --run DIR --label nonmodel`.
