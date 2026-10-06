# HANDOFF — task-compaction-v1-r1

**Status: ready for Codex review; not yet accepted.**

Executed by Claude Code from `../delegation/task-compaction-v1-r1/NEXT_CLAUDE.md`
(forwarded by the user on 2026-10-05). Nothing was committed, staged, pushed or
published. No active source, frozen evidence, notebook, `build_19.py`, earlier result
tree or sibling-repository file was modified. No successor phase was started.

## Outcome in one paragraph

The isolated owner extension computes the exact coarsest task-preserving state grouping
by classical partition refinement. The proof is in THEORY.md; the source is Knuutila
(2001) §§2.2–3.1, and SOURCES.md records the retrieved-file hash. The single production
run covered 24 of 24 cells and 3,276 of 3,276 candidate records. The independent audit
returned **VALID_COMPLETE** (0 invalid, 0 missing).

On the 12 primary INTERVENTION cells there are 3 EXACT_REDUCTION and 9 NO_REDUCTION:

- M2/T0: K* = 2 of 256.
- M4/T0: K* = 2 of 1024.
- M4/T1: K* = 16 of 1024.

The earlier width and nesting family matches the optimum in 11 of these 12 cells, and
in 9 of those 11 the optimum is the full state set. The one CANDIDATE_GAP is M4/T1: the
optimum is the non-contiguous coordinate set {0, 1, 8, 9}, and no old non-control
candidate is sufficient. The 12 AUTO controls give 10 EXACT_REDUCTION and
7 CANDIDATE_GAP, and INTERVENTION refines AUTO in 12 of 12 pairs. These are
state-cardinality results only: they are not archive or description-length savings.

## Where everything is

| item | path |
|---|---|
| report, decision, claims | `REPORT.md`, `REPORT_TABLES.md` (generated), `DECISION.md`, `CLAIMS.md` |
| theory and sources read | `THEORY.md`, `SOURCES.md` |
| protocol / cases / packet snapshot | `protocol/` (byte copies of the delegation packet) |
| declared fixtures (before first execution; SUP1, SUP2 supplemental) | `fixtures.json` |
| isolated core revision (layout-preserving snapshot, NOT an active alternative) | `isolated/index-deconvolution/src/deconvolution.py`; origins `isolated/ORIGINS_at_copy.json` |
| owner tests (new) | `isolated/index-deconvolution/tests/test_task_compaction.py` |
| original owner snapshot | `dependency/original/deconvolution.py` (sha256 bd549796…, equals manifest) |
| **unapplied integration patches** | `patches/deconvolution_owner.patch`, `patches/test_task_compaction.patch` |
| orchestration, audit, probes, guards | `src/produce.py`, `src/audit.py`, `src/corruptions.py`, `src/mutations.py`, `src/owner_check.py`, `src/freeze.py`, `src/preserve.py`, `src/report.py` (post-freeze, presentation only) |
| run-local tests | `tests/test_audit_labels.py` |
| freeze | `freeze.json`; `logs/freeze_verify_preproduction.json`, `logs/freeze_verify_postproduction.json` |
| scientific artifacts | `production/` (tables, candidate alphas, 24 cell certificates with stages, coarsening maps, decoders, macro tables, witnesses; 24 candidate shards; `summary.json`; `seal.json`; `imports.json`; `cost.json`); every file is under 10 MB, 4.5 MB in total |
| independent audit | `audit/audit.json`; corruption copies and manifests `audit/corruptions/` (`corruptions.json`) |
| tests, mutations, lint, guards | `logs/regression_73.log`, `logs/fixture_tests.log`, `logs/run_local_tests.log`, `logs/mutations.json`, `logs/owner_check.log`, `logs/ruff.log`, `logs/guards_prefreeze.log`, `logs/guards_handoff.log`, `logs/single_engine_full.log` |
| dry run (SUP2) | `logs/dryrun_SUP2_{summary,audit,corruptions}.json` |
| attempts and time | `attempts/attempts.jsonl`, `logs/wallclock.jsonl`, `logs/time_ledger.json` |
| preservation | `logs/preservation_{before,after}.json.gz` (gzip -9n of files over 10 MB; uncompressed hashes in `logs/preservation_uncompressed_sha256.txt`), `logs/preservation_diff.json`, `logs/git_before.txt`, `logs/git_after.txt` |
| reproduction | `run.sh`; `logs/reproduction.log`; `logs/reproduction_compare.json` |
| output manifest | `output_manifest.json` |

## Reproduce

From anywhere, with the repository's venv, run `zsh index-deconvolution/results/causal_task_compaction_v1/task-compaction-v1-r1/run.sh <fresh dir>`.
The command refuses to run if the destination exists. It verifies the freeze, runs the
production, then runs the audit. The deterministic artifact list is
`freeze.json → schema.deterministic_production_artifacts` plus `audit.json`. In a fresh
`/tmp` directory, 62 of 62 artifacts came out byte-identical. `cost.json` is excluded
because it holds timings.

## Verified

- 26 of 26 packet and input hashes matched before work, and again at freeze and after
  production.
- Tests: 73 regression and 31 new, all passing on the isolated revision; 5 run-local
  audit-label tests passing.
- Mutants: 6 of 6 killed.
  - MUT2, MUT5 and MUT6 are caught by test-file assertions.
  - MUT1, MUT3 and MUT4 are caught by the owner's internal decode, closure and domain
    checks, which surface as failing fixture tests.
- Owner AST check passes, and a planted copy is rejected.
- ruff is clean.
- Audit denominators: 85,504 transition entries; 318 stage-induction steps; 261,888 macro
  entries; 294 witnesses; 3,276 candidate decisions.
- Corruptions: 4 of 4 behaved as required. COR3 passes validity and fails minimality.
  COR4 is INVALID and also records the missing cell.
- Patches: `git apply --check` succeeds, and in a disposable copy the patched tree passes
  104 tests.
- Preservation: 109,851 protected files unchanged; git status identical before and after.

## Read before accepting

1. The patches include a third public helper, `task_word_path`, beyond the ticket's two
   names. It is declared and guarded.
2. The new test reads `fixtures.json` from this run directory, so that path must persist
   if the patches are adopted.
3. The isolated layout needed one more read-only dependency than the ticket listed:
   `doppel-challenge/src/doppel_challenge/repertoire_program.py`. It is mirrored
   byte-identically (attempt 1).
4. `check_single_engine` has 9 pre-existing FAIL lines. They come from a
   `.kilo/worktrees/held-saguaro` worktree and from python description-length sites, and
   none names this run. They were not repaired. `make ci-local` was not run, so full CI
   has not passed; the scoped substitute is listed above.
5. Preservation scope (`src/preserve.py`, copied from gap-ranking-v1-r1):
   - Covered: index-deconvolution src, tests, notebooks, bitacora, protocols and results
     (this run excluded); GOVERNANCE; and the sibling's src, tests and top-level files.
   - Timing: the before-snapshot was taken after this empty run directory was created and
     before any development file was written. The after-snapshot was taken at handoff.
   - Not covered: `/tmp` workspaces (since deleted) and other top-level repository trees.
     Those are covered only by the git status comparison.
6. The time ledger in `logs/time_ledger.json` shows about 1,700 s of the 6,600 s used.
   Every category is under its cap, with no transfers; the charging method is stated in
   the file.

Ready for Codex review; not yet accepted.
