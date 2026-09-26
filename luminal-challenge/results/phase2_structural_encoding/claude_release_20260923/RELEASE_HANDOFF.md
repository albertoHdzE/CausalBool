# Phase 2 release handoff

**Status: READY_FOR_CODEX_REVIEW.** This release is not self-accepted.

2026-09-24 · Implementer: Claude Code (Opus 5.5), manually invoked by the user
under `plan/CLAUDE_PHASE2_RELEASE_PLAN.md` v1.0 · Final reviewer: Codex.
Audit directory: `results/phase2_structural_encoding/claude_release_20260923/`
(the first attempt; no earlier `claude_release_*` directory existed). All paths
below are relative to it unless they begin with `results/`.

## 1. Outcome in one paragraph

The implementation is correct within its tested and measured scope after seven
repairs (R1–R7), each pinned by a regression. The run of record is
`results/phase2_structural_encoding/recovery_campaign_20260923_r3`. It completed
P0–P5 with all 33,120 measurement workers and 0 failed rows. Its checker reports
**0 findings**, and every derived stage verdict equals the recorded one; the
checker exits 2 only because P4 is INCONCLUSIVE. The lead's raw-row auditor
passes, and the 24 contrasts agree with COMPARISON.json to 1e-9.

**Primary H2 (held-out, 0.1 s, `structural_bound` against accepted
`accepted_budgeted`):** +0.0439 [0.0251, 0.0660] on the paired log J ratio.
There are 26 wins, 74 ties and 0 losses over 100 of 100 programs. That is a small
confirmed gain, mainly in scratch.

**Against classical (held-out, descriptive):** J is better by +0.0882 [0.0592,
0.1194] (53 W / 35 T / 12 L), while compile time is 7.3× and process time 1.5×
classical.

**Public:** the effect is inconclusive. **H3:** supported as a triage. **H4:**
inconclusive and untestable with the frozen fixtures, so the P5 model arm is
absent. Further optimisation is warranted as a new phase with a fresh hold-out.

## 2. Source manifests and changed files

| Item | Path |
|---|---|
| HEAD at start and end | `START_HEAD.txt` = `END_HEAD.txt` = `1aef90681e3dead3ab1f560da8b7823ab66dabf4` |
| Git status and working diff at start / end | `START_GIT_STATUS.txt`, `START_WORKING_DIFF.patch` / `END_GIT_STATUS.txt`, `END_WORKING_DIFF.patch`. The tracked diff is byte-identical at start and end |
| Starting source (Luna checkpoint) | `starting_source/` and `START_SOURCE_SHA256.txt`, matching `plan/claude_phase2_release/STARTING_STATE.json` (logged as `a01`) |
| Source v1, frozen before `_r2` | `final_source/` and `FINAL_SOURCE_SHA256.txt` |
| **Source v2, final measured source, frozen before `_r3`** | `final_source_v2/` and `FINAL_SOURCE_V2_SHA256.txt`. There was no drift after freezing: the tree was re-hashed at the end |
| Diffs | `SOURCE_CHANGES.patch` (start→v1), `SOURCE_CHANGES_V1_TO_V2.patch`, `SOURCE_CHANGES_START_TO_V2.patch` |
| Environment | `ENVIRONMENT.txt`: Python 3.13.12, macOS 26.6.2 arm64, pip freeze |

Changed files:
- `research/run_structural_experiments.py`: R1, R2, R3 and R5.
- `research/check_structural_evidence.py`: R1/R2 recomputation flags, R6 and R7.
- `research_tests/test_phase2_release.py`: new file, 17 tests.

Nothing else in the repository was edited. No paper, production, reference,
plan, STATUS, lead-review or historical file was changed.

The one other effect on disk is the gitignored build artifact
`.build/direct_index/compiler.py`, which the prescribed `verify_direct.py` rewrites.
It was proven byte-identical beforehand (`production/export_hash_comparison.txt`),
backed up verbatim (`production/build_compiler_backup_before_controls.py`), and
has the same sha256 `d14bf39b…5864` afterwards.

## 3. Readiness matrix, tests and journals

- `READINESS_MATRIX.md` lists all seven lead findings, R1–R7, the logs and exits,
  and the post-launch addendum.
- Checkpoint reproduced: `logs/a04_research_tests_full.*` passes 269 tests (exit 0).
- Final: `logs/h03_research_tests_full_v3.*` passes 286 tests (exit 0). No test
  was deleted.
- The regressions fail on unrepaired source: `logs/b02_*` (8), `logs/f02_*` (3)
  and `logs/h02_*` (1).
- Every command I ran is in `COMMANDS.jsonl`: 33 records with argv, cwd,
  environment, UTC times and exit codes. Full stdout and stderr are in
  `logs/<label>.*`.
- Worker journals are fsynced per worker in `results/.../recovery_campaign_20260923_r3/journals/`.
  The checker reconciles journals, commands and stage rows (`journals.*` checks in
  `CHECKER_REPORT_r3.json`).
- The crash and missing-journal mutations are covered by
  `test_crashed_worker_is_fsynced_and_missing_journal_row_is_detected`.

## 4. Campaigns, command history and verdicts

| Run | Source | Runner exit | Checker exit | Disposition |
|---|---|---:|---:|---|
| `recovery_campaign_20260923_r2` | v1 | 2 (P4 INCONCLUSIVE) | 1: 22 findings from checker defects R6/R7 (`logs/e01_*`) | **Preserved unchanged, and not the run of record.** Its measurement source is identical to v2. A dry run with the v2 checker (`logs/h04_*`) reconciles every stage; only source-provenance findings remain. The lead auditor passes (`r2_audit/`). This run is replication evidence, never merged with `_r3` |
| **`recovery_campaign_20260923_r3`** | v2 | 2 (P4 INCONCLUSIVE) | **2: 0 findings, 1 inconclusive (`p4.h4_gate`)**. `artifacts_internally_consistent` is true; `artifacts_complete` is false only because the required P4 stage is INCONCLUSIVE | **Run of record** |

Command, identical for both runs apart from the ID:
`env PYTHONPATH=.reference:. ../venv/bin/python -m research.run_structural_experiments --stage all --run-id <ID> --contract plan/phase2 --amendment plan/phase2_recovery/AMENDMENT.json`
(`logs/d01_*` and `logs/i01_*`, 81 min each).

Checker: `logs/j01_checker_r3.*`, copied to `CHECKER_REPORT_r3.json`.

Stage verdicts for `_r3`, recorded and derived:

| Stage | Verdict |
|---|---|
| preflight | PASS |
| P0 | PASS |
| P1 | PASS (amended union coverage). The original random coverage FAILs separately: 0–234 distinct against 100 |
| P2 | PASS: 1,800/1,800 rows |
| P3 | PASS: triage 7/11 |
| P4 | INCONCLUSIVE: 7,020/7,020 rows; H4 does not advance (1 family, bounds 0.0/0.0) |
| P5 | PASS: 24,300/24,300 rows |

Hypotheses: H1 supported, H2 supported (held-out primary), H3 supported, H4
inconclusive.

Interrupted or omitted work:
- The P5 model arm (4,860 rows) was not run. H4 did not authorise it, and the
  reason was recomputed from raw rows by the checker.
- No run was interrupted. The only nonzero exits are the protocol codes explained
  above.
- The initial combined `export_direct.py` command, which writes the default path,
  was refused by the session's permission classifier and never executed. See §5.

Key hashes:

| Artifact | sha256 prefix |
|---|---|
| `_r3/COMPARISON.json` | `f9ffaade` |
| `_r3/manifest.json` | `8c99774a` |
| `_r3/p5/heldout_rows.jsonl` | `1017dbd9` |
| `_r3/p5/public_rows.jsonl` | `2cf4b3dc` |

## 5. Production controls and protected files

The controls ran serially after all measurements had stopped, each into a new
location under `production/`:

| Label | Command | Result |
|---|---|---|
| `k01` | `export_direct.py --output production/export/compiler.py` | Exit 0; byte-identical to the existing build |
| `k02` | `verify_direct.py --stage all --output production/production_verification` | Exit 0; overall PASS, 0 failing |
| `k03` | `compare_direct.py --repeats 3 --timeout 20 --output production/production_comparison` | Exit 0; all 8 gates PASS |

In `k03`, classical is frozen at 1.901379 (within 1e-9 of the historical value)
and direct scores 2.008466. That validates the controls only; it is not a Phase 2
comparison.

Deviation, stated plainly: the plan's first command is the bare
`export_direct.py`, which writes the default gitignored `.build/…/compiler.py`.
That exact invocation was refused by the permission classifier, and I did not work
around the refusal. I ran the same unchanged script with `--output` to a new
location instead. `verify_direct.py --stage all` then rewrote the default path
internally with identical bytes, after a verbatim backup (§2).

Protected, baseline and policy hashes:
- Before the work: `logs/a01` (initial mode, including starting source) and `a02`.
- After the work: `logs/k04` and `logs/k05`. All exit 0: 12 package locks, 46
  baseline locks, 7 recovery inputs and 11 delegation inputs.

## 6. Comparisons and independent audit

| Artifact | Path |
|---|---|
| Machine-readable comparison | `results/.../recovery_campaign_20260923_r3/COMPARISON.json` |
| Human-readable table | `results/.../recovery_campaign_20260923_r3/COMPARISON.md`: primary section plus the 24-entry descriptive matrix |
| Lead auditor, unedited | `INDEPENDENT_COMPARISON.json` (`logs/j02_*`): "PASS: exact P5 membership and 24 independently recomputed contrasts" |

**Agreement report** (`CROSSCHECK.json`, `logs/j03_*`, produced by my
`crosscheck.py`, which reads the two JSON files only): all 24 keys match, with
**0 differences** at a tolerance of 1e-9. The comparison covers the quality point
estimate and 95 % bounds, program and family denominators, W/T/L, the compile and
process point estimates and intervals, and all 100 per-program primary log ratios
with their signs.

A difference that is expected but not an estimate: the lead auditor asserts
`search_seed is None`, and applies no row-exclusion paths because none are
exercised (0 failures).

Additional renders are in `RELEASE_ANALYSIS.json` (`logs/l02_*`). They read raw
rows only and cover:
- the per-program primary J, C and S for all 100 held-out programs;
- the effect histogram;
- stopping reasons, optimisation seconds and overshoot;
- the r2→r3 reproducibility join. J sets are identical in 120/120 public cells
  and 1,498/1,500 held-out cells; the 2 differing cells are the deadline-bound
  `structural_expanded`@0.1 and `structural_dfs`@0.01. The median compile-time
  ratio between the runs is 1.000.

`RELEASE_ANALYSIS_superseded_pattern_bug.json` is an earlier output of my own
script. I retained it, and it is superseded because one summary field lost its
counts; that is an analysis bug, not a measurement.

## 7. Decisions and limitations

- `OPTIMIZATION_DECISION.md` answers the five questions. Optimisation is warranted
  as a new phase. The ranked proposals are: (1) a budget-aware query cap, since
  `max_queries` = 32 binds in 64/100 held-out programs after about 3 ms; (2)
  schedule moves aimed at classical's 7 cycle wins; (3) process overhead; (4) new
  fixtures before any H4 work. Each needs a fresh hold-out.
- `PAPER_READINESS.md` holds the claim-to-evidence table. It supports a bounded
  manuscript section only.

Main limitations:
- The effect is small and concentrated in 26 of 100 programs.
- Public results are inconclusive.
- P1 passes only under the post-hoc amendment.
- H4 is untestable.
- Timing comes from a single machine.
- The repetitions carry timing information only, because J is deterministic.

## 8. Unresolved issues for Codex

1. The R1–R7 source repairs need independent inspection, especially R6. It
   changes what the checker accepts for deadline-interrupted rows; the
   acceptance conditions are in `READINESS_MATRIX.md`.
2. `p4_contrasts` filters `test_proposals >= 0`, a condition that is always true.
   It was left unchanged so as not to move the H4 gate (see the observations in
   `READINESS_MATRIX.md`).
3. The checker's exit 2 on a complete run with one scientifically inconclusive
   required stage (P4) follows the frozen exit-code contract. Codex may want to
   confirm this reading.
4. The 1,800 rows of the original aborted P2 campaign
   (`recovery_campaign_20260923`) were not used or merged.

## 9. Process ownership and resume

I started exactly two long-running processes, both through this session's own
background-task handles: `_r2` and `_r3`. Both exited on their own, with no
cancellation. No kill, pkill or PID signal was used, and no notebook, editor or
other service was touched. No agents were launched. Nothing was committed, pushed
or published.

`PROGRESS.json` is the final progress record. The runner has no resume inside a
run. To repeat this work:
1. Verify the tree against `FINAL_SOURCE_V2_SHA256.txt`.
2. Run the §4 command with the next unused suffix (`_r4`).
3. Run the checker with `--run` on that directory.
4. Run `independent_compare.py` and `crosscheck.py` as in `logs/j02` and `logs/j03`.
5. Run the three production controls as in `logs/k01`–`logs/k03`.
