# HID-search-v2 — developer handoff for supervisor review

Date: 2026-10-02. Developer/executor: Claude Code. Supervisor: Codex.
**Status: `ready_for_review` — not accepted.** Acceptance is the supervisor's decision.
Nothing was committed, pushed or published.

## 1. Identity

| Item | Value |
|---|---|
| Study / algorithm | `search-v2` / HID-search-v2 (ISD1/HID-v1 wire format unchanged) |
| Run ID | `search-confirm-v2-r1` |
| Result root | `index-deconvolution/results/hierarchy_search_v2/` |
| Freeze SHA-256 | `0f0a72ef2f9d9faac406b6d18594a45ba9dc71ff1d0331f38c6a3fead68e1d49` (`search-confirm-v2-r1/freeze.sha256`) |
| Source snapshot | `search-confirm-v2-r1/source_snapshot.tar`, 76 members, SHA-256 `6766f967012b97f3b2bbcd373115831d4d4761a8213dfc8997a76da31c9dc215` (manifest `source_snapshot.sha256`) |
| Code revision | `git HEAD dcc1d59e`; the whole `index-deconvolution/hierarchy/` package is **untracked** in git and the tree is dirty with other people's work, so content hashes (the freeze) identify the sources, not a commit |
| Dirty-state disclosure | pre-existing modifications preserved untouched (repository status before edits: `results/hierarchy_search_v2/preservation/working_tree_status_repository_before.txt`, 155 lines); among them the disclosed `src/description_lengths.py` `bdm_1d_trace` addition |

## 2. What was implemented; what stayed identical

* Six cumulative arms (`hid_legacy`, `hid_first_local`, `hid_consensus_local`,
  `hid_dense_local`, `hid_global`, `hid_full`) exactly as SEARCH.md, in new modules
  `hierarchy/search_v2.py` (orchestrator), `consensus.py` (P/C/D/G) and
  `segmentation.py` (B). Every arm reruns `infer(bits, FULL)` and pays for all its work.
* Explicit immutable study specification and method registry (`study.py`) with the
  legacy study (`hid-v1`) as the default of every command; evaluation layer
  (`study_corpus.py`: namespaced generation, stress S01/S02, retained development
  inputs, boundary metadata, reserved-access guard); prospective freeze of the complete
  executable closure (`freeze_v2.py`); analysis adapter over the shared report owner
  (`report_v2.py`); diagnostics (`diagnostics_v2.py`); command implementations
  (`cli_v2.py`). Shared orchestration owners were enriched, not forked: `benchmark.py`
  (explicit `study`, registry-dispatched workers, `job_class` for test workers,
  durable `CategoryBudget`), `validation.py` (study designs with declared kinds and case
  prefixes, `search_v2_checks`), `report.py` (`cell_index_draws`, now also used by
  `stratified_bootstrap` with identical RNG consumption), `ledger.py` (exhaustive cost
  buckets), `cli.py` (`--study`, `regression`).
* **Identical to the recorded initial state** (verified after the run): `infer.py`,
  `candidates.py`, `model.py`, `wire.py`, `decode.py`, `baselines.py`, `corpus.py`,
  `src/deconvolution.py`, `src/causalbool.py`, `src/description_lengths.py` (active
  hash `b6fb6eaf…`, the disclosed trace addition, frozen as is; the trace function is
  not used by inference). All seven packet files and six reference files still match
  `DELEGATION_MANIFEST.json`.
* **Approved validator patch** (`587d7bc0…5809346`): applied once with `git apply`
  after confirming the reviewed baseline; the four resulting files equalled the
  reviewed patched hashes (`preservation/patch_application.json`); its 14 regression
  tests are retained in `tests/test_validation.py`. `cli.py`, `report.py` and
  `validation.py` were subsequently extended by this assignment; the freeze records
  their final hashes.
* **r1 source snapshot**: `results/hierarchy_v1_supervision/confirm-v1-r1/source_snapshot_confirm-v1-r1.tar`
  (25 members, SHA-256 `35217d1134aa2fde0a86b05b81e7034c2bfa1c22c53ed77e862a73955608c74f`),
  every member verified against freeze `f970efff…`; the historical
  `description_lengths.py` (`052786ca…`) was taken from the verified retained copy in
  `CausalBool_validator_closure/baseline/` and the active file was never overwritten.
* Requirement-by-requirement map: `results/hierarchy_search_v2/implementation_map.md`.

## 3. Commands, exit statuses and checks

All from the repository root with `PYTHONPATH=index-deconvolution:src` and `venv/bin/python`.

| Command | Exit |
|---|---|
| `experiments/preserve_confirm_v1_r1_sources.py snapshot` | 0 |
| `zsh experiments/audit_confirm_v1_r1_from_snapshot.sh` (historical audit, twice) | 0, 0 |
| `git apply` of the approved patch (after `--check`) | 0 |
| `-m hierarchy.cli selfcheck --study search-v2` / `selfcheck` (legacy) | 0 / 0 |
| `-m hierarchy.cli pilot --study search-v2 --run-id dev-search-v2-pilot` | 0 |
| `-m hierarchy.cli regression --study search-v2 --run-id dev-search-v2-regression` | killed externally (see §4), then `--resume` → 0 |
| `-m hierarchy.cli diagnostics --study search-v2 --run-id dev-search-v2-regression` | 0 |
| `-m hierarchy.cli freeze --study search-v2 --run-id search-confirm-v2-r1` | 0 |
| `-m hierarchy.cli benchmark --study search-v2 --run-id search-confirm-v2-r1 --split confirmation|transfer|stress --resume --quiet` | 0, 0, 0 |
| `-m hierarchy.cli diagnostics --study search-v2 --run-id search-confirm-v2-r1` | 0 |
| `-m hierarchy.cli report --study search-v2 --run-id search-confirm-v2-r1` | 0 |
| `experiments/audit_search_v2_primary.py results/hierarchy_search_v2/search-confirm-v2-r1` | 0 |
| `-m hierarchy.cli verify --study search-v2 --run-id search-confirm-v2-r1` (plain, then notebook execution, then `--full`) | 0, 0 |
| `experiments/preserve_confirm_v1_r1_sources.py trees` | 0 |

`verify --full` (`search-confirm-v2-r1/verification.json`): pytest **385 passed**
(249 package + 136 shared-owner file; the approved integrated suite was 331, plus 7
tests of the pre-existing `bdm_1d_trace` work, plus 47 new); ruff clean on every
changed Python file; `check_core_index` 0; `check_test_manifest` 0; notebook 17: 15
code cells, 0 errors, 0 unexecuted; separate-process stdlib decoder on a 390-archive
stratified sample: all correct; `summary.json` and `claim_ledger.json` recompute
identically from the rows.

**Known external failure, not a clean guard pass:** `tools/check_single_engine.sh`
exits 1. Every flagged site predates this assignment: `.kilo/worktrees/held-saguaro/*`
(Wolfram and Python duplicates), the pinned imp-pathinfo mirror, and two stray untracked
copies `index-deconvolution/protocols/description_lengths.py` (r1-era bytes `052786ca…`)
and `index-deconvolution/protocols/causalbool.py` (plus an empty directory
`protocols/deconvolution.py/`). Both files are listed in
`preservation/working_tree_status_before.txt` lines 57–58, recorded before my first
edit. None was created, modified or removed by me. Full guard output:
`prefreeze/guards/`.

**Not run:** `make ci-local` (Wolfram closure + 69-test MUnit suite, ~40 min). It
rewrites tracked `results/tests/*` files that are already modified by other work in
this tree, and it does not exercise this Python package. Equivalent relevant checks
performed: the full hierarchy + shared-owner pytest suite, ruff, the three guards, both
selfchecks, and `verify --full`. No repository-wide CI claim is made.

## 4. Counts, decoding, resources, resume history, time

* Expected = actual: **1,792 cases** (1,440 confirmation, 288 transfer, 64 stress) and
  **28,672 unique case-method rows**, all `ok`; 28,672 archives present, hash-checked,
  length-checked and decoded against regenerated inputs (17,573 distinct archives);
  `decode_failed` 0. Every newly introduced full-input candidate was decoded inside its
  worker (duplicates of already-decoded bytes are counted, not re-decoded).
* Resource events: **none**. 0 timeouts, 0 RSS breaches, 0 censored baselines, 0 error
  rows, 0 resource nesting breaks; 8,960 nesting pairs checked; stage-L of every arm
  equals the `hid_legacy` archive on every string. Max HID worker wall 10.4 s
  (`hid_full`), peak RSS 316 MB. B stopped on a deterministic cap in 22/1,440
  confirmation, 6/288 transfer and 2/64 stress `hid_full` rows (root-trial or
  leaf-length cap), each offering its best serialized trial.
* Reserved run resume history: each split completed in one invocation; no interruption.
* Development: pilot one invocation (deliberate interruption after 8 cases + resume,
  12-case fresh replay identical). Regression invocation 1 was **killed externally by
  the agent tool's 1,800 s background limit** at 1,406/1,440 confirmation cases (no
  code defect, no orphaned workers, atomic rows preserved; 60 s charged conservatively
  for the unrecorded in-flight interval); invocation 2 resumed the same run id under
  the same development fingerprint. Details: `prefreeze/attempts_notes.md`.
* Cumulative automated time (`execution_ledger.jsonl`): development 5,314 s / 14,400;
  reserved 7,191 s / 21,600; diagnostics/verification 1,644 s / 7,200 (development-run
  diagnostics and report were charged here, conservatively); total 14,148 s / 43,200.

## 5. Results

**Primary (confirmation F01–F06, F12; 21 cells, 420 paired units, 840 strings):**
engineering valid, population complete, 0 censored baselines; estimate
**+0.005605 bits saved per input bit**, 95% percentile interval
**[−0.002081, +0.013047]** (10,000 draws, seed 44001). The interval crosses zero:
**verdict `inconclusive`.** HID-search-v2 has not demonstrated superiority over the
nine-baseline portfolio on this population; nor is it shown inferior. At string level
297 strings favour HID, 72 tie and 471 favour the portfolio (median saving −0.0234
bits/input bit). The independent audit reproduces the point estimate from archive
bytes with |difference| = 0.0 and re-derives every portfolio minimum
(`arithmetic_audit.json`).

**Five targeted cumulative contrasts (99% intervals, one joint draw, seed 44002; 60
paired units each):**

| Contrast | Target | Estimate (bits/input bit) | 99% interval | Reading |
|---|---|---:|---|---|
| P vs L (first-block local) | F06 | +0.01425 | [+0.00117, +0.03443] | supported |
| C vs P (consensus) | F06 | +0.12214 | [+0.07057, +0.17494] | supported |
| D vs C (dense periods) | F06 | +0.09959 | [+0.03706, +0.17023] | supported |
| G vs D (global patch) | F06 | +0.04563 | [+0.03892, +0.05219] | supported |
| full vs G (boundaries) | F12 | +0.12026 | [+0.11287, +0.12763] | supported |

These are cumulative algorithm changes including their cost, on their target families
only; they are not additive, not pure mechanism effects, and they do not rescue the
inconclusive primary result.

**Descriptive (no verdicts; 95% intervals as prespecified):**

| Summary | full vs portfolio | full vs legacy | units |
|---|---|---|---:|
| All twelve confirmation families (44003) | −0.07295 [−0.07923, −0.06667] | +0.03435 [+0.03021, +0.03853] | 720 |
| Structured transfer, 21 cells (44004) | +0.00037 [−0.00345, +0.00426] | +0.05501 [+0.04387, +0.06683] | 84 |
| All stress, 4 cells (44005) | +0.17408 [+0.15138, +0.19358] | +0.29326 [+0.25592, +0.33021] | 32 |

Structured transfer by size, estimates only (full vs portfolio): 16,384 bits +0.00174,
65,536 bits −0.00157, 131,072 bits +0.00095. Stress cells (full vs portfolio):
S01 4,096 +0.425, S01 65,536 +0.110, S02 4,096 +0.170, S02 65,536 −0.009.
Per-cell tables for every role: `summary.json#cells`.

## 6. What the measurements say, and what they do not

* **Templates and coverage.** On noisy periodic strings (F06) consensus templates and
  dense period coverage carry the largest measured gains (C vs P, D vs C), consistent
  with the bitacora-39 diagnosis (first-block errors repeated; period 63 absent from
  the old grid; 63 is one of the four confirmation periods). Full vs portfolio on F06:
  +0.111, +0.442, +0.315 bits/input bit at 256, 1,024, 4,096.
* **Patch placement.** One global correction list beats capped local patches on F06
  (G vs D) by a smaller but tight margin.
* **Boundaries.** B adds +0.120 on F12, yet F12 still loses to the portfolio at 4,096
  bits (−0.063) and on every transfer F12 string. Against the evaluation-only
  supplied-boundary references, automatic `hid_full` is shorter on all 40 F12-1,024
  strings (mean gap −0.073 bits/input bit) but longer on all 40 F12-4,096 strings
  (+0.105) and all 24 transfer F12 strings (+0.083 to +0.135); S02 is mixed (4,096:
  12 shorter / 4 longer; 65,536: 7 / 9). These references are restricted feasible
  partitions under a shortest-period leaf heuristic, not optima or bounds; the gap
  suggests, without proving, that B's coarse/refined cut search under its caps misses
  construction-like cuts at larger sizes.
* **Where the primary is lost.** Unchanged from HID-v1, the periodic and macro
  families F01, F02, F03 lose in all nine cells (e.g. F01-256 −0.381; F01 is always won
  by the `period` baseline), F05 loses slightly in all three, F12-4,096 loses; F04 and
  F06 win in all six cells. New proposals moved the population mean from clearly
  negative in HID-v1 (−0.0446 [−0.0537, −0.0358], **different reserved instances**, so
  not a paired comparison) to an interval around zero, but not above it.
* **Overhead.** Exact cost buckets (`summary.json#cost_components`): in transfer,
  `hid_full` spends on average 8,235 of 24,806 bits on child references (33%) and
  1,504 on correction deltas; in confirmation 81 of 983 bits on references (8%). This
  measures where bits go; it does not test whether a different format would win, and
  removing overhead on paper is not a deployable code.
* **Not identified.** The contrasts estimate costed algorithm changes on F06/F12 only;
  no causal decomposition of the primary result into obstacles is available, and
  nothing here identifies generators, computes K, or establishes generalisation to
  unfamiliar families.

## 7. Exposure, amendments, untested paths, genuineness

* Reserved namespaces `search_v2_confirmation/transfer/stress` were generated only by
  the benchmark after the freeze; the freeze's automated exposure scan was clean and
  `study_corpus` refuses reserved generation without a freeze declaring the role
  (tested). No 131,072-bit input existed before the freeze. Fixture tests used only
  `search_v2_fixture` (≤ 65,539 bits). Development used only the historical keys
  authorised by BENCHMARK.md section 1. **No amendment was needed or made**; no
  parameter was tuned; no freeze-changing fix was made after reserved access.
* The result is genuinely prospective for the reserved instances. It is a test on
  fresh instances of familiar generators; S01/S02 are parameter-shifted versions of
  familiar ideas. Transfer and stress are descriptive. The `dev-*` runs are on
  previously inspected data and are not evidence of generalisation.
* Untested or partly tested paths: a real 1 GiB RSS breach and a real 30 s timeout
  never occurred in the study; their runner paths were tested with a fixture policy of
  a 1-byte RSS limit and a 0 s wall limit through the real watchdog (deterministic on
  this platform). Malformed-JSON robustness limits inherited from the approved patch
  remain (bitacora 38).
* Interpretations to review (routine choices, each documented in code): (a) a
  duplicate candidate archive is counted but not re-decoded, because identical bytes
  were already decoded; (b) in B a new partition's leaves are charged before its
  root-trial charge, which is taken immediately before serialization; (c) in the
  boundary mapping the deletion join min(d, N) is always added, while insertion-adjacent
  cuts require the inserted element to survive, as written; (d) `rule_count`/`dag_depth`
  are parsed from the final archive inside the worker, so that parse is inside
  `encode_wall_ns` and `worker_wall_ns`; (e) development-run diagnostics/report time was
  charged to the diagnostics/verification allowance; (f) notebook 17 shows the plain
  `verify` record that existed when it was executed (before `--full`).

## 8. Old-run integrity and review commands (no re-encoding)

* `confirm-v1`: 18,058 files, aggregate `8aa2326e…`; `confirm-v1-r1`: 18,062 files,
  aggregate `46c84ce8…`; identical before and after (`preservation/preservation_before.json`,
  `preservation_after.json`). No old row, archive, freeze, notebook or verification
  record was written; notebook 16 untouched.
* Historical audit (read-only, temp tree from the r1 snapshot; equals stored
  `audit.json`, estimate −0.0446156382):
  `zsh index-deconvolution/experiments/audit_confirm_v1_r1_from_snapshot.sh`
* Review the new run without re-encoding:

```sh
cd /Users/alberto/Documents/projects/CausalBool
export PYTHONPATH=index-deconvolution:src
venv/bin/python -m hierarchy.cli verify --study search-v2 --run-id search-confirm-v2-r1        # ~6 min
venv/bin/python -m hierarchy.cli verify --study search-v2 --run-id search-confirm-v2-r1 --full # + tests, lint, guards, notebook
venv/bin/python index-deconvolution/experiments/audit_search_v2_primary.py index-deconvolution/results/hierarchy_search_v2/search-confirm-v2-r1
venv/bin/python index-deconvolution/experiments/preserve_confirm_v1_r1_sources.py trees
venv/bin/python -m hierarchy.cli selfcheck --study search-v2
```

(`verify` and `report` append to the study's execution ledger; `report` rewrites
`summary.json`, `ledgers.json` and `claim_ledger.json` deterministically.)

## 9. Files

**New:** `hierarchy/study.py`, `study_corpus.py`, `consensus.py`, `segmentation.py`,
`search_v2.py`, `freeze_v2.py`, `report_v2.py`, `diagnostics_v2.py`, `cli_v2.py`,
`tests/test_search_v2.py`, `tests/test_study_v2.py`, `HANDOFF_SEARCH_V2.md`;
`experiments/preserve_confirm_v1_r1_sources.py`, `audit_confirm_v1_r1_from_snapshot.sh`,
`audit_search_v2_primary.py`; `notebooks/build_17.py`, `17_hierarchy_search_v2.ipynb`;
`bitacora/40_hierarchy_search_v2_results.md`; the r1 snapshot tar and its `.sha256`
under `results/hierarchy_v1_supervision/confirm-v1-r1/`; everything under
`results/hierarchy_search_v2/` (preservation, prefreeze, development runs, the run,
implementation map, execution ledger, development attempts).

**Modified:** `hierarchy/benchmark.py`, `cli.py`, `report.py`, `validation.py`,
`ledger.py`, `tests/test_validation.py` (approved patch only), `README.md`, `TESTS.md`;
`notebooks/README.md` (one line for notebook 17, beside pre-existing edits).

**Decisions needed from the supervisor:** acceptance of the engineering packet and of
the interpretations in §7; whether the pre-existing stray `protocols/` copies should be
removed by their owner. No deviation from the protocol constants was made.

Nothing was committed, pushed or published.
