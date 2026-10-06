# HANDOFF: task-compaction-v1-r1 review closure

**Status: ready for Codex review; not yet accepted.**

Executed by Claude Code on 2026-10-05 from
`../../delegation/task-compaction-v1-r1-closure/NEXT_CLAUDE.md`.

- Nothing was staged, committed, pushed or published, and nothing was scheduled.
- No active file, frozen evidence, notebook, `build_19.py`, governance file or sibling
  file was modified.
- No production rerun, retuning or new experiment was performed.

## Outcome

- **R1 closed** (`src/audit_r2.py`, a new identity; the frozen `audit.py` is untouched).
  - The declared matrix of PROTOCOL items 1–10 gives **23/23 as required**
    (`probes/final/matrix.json`).
  - The frozen audit, run on the same copies, reproduces the three Codex defects:
    VALID_COMPLETE on `cells=[]`, INVALID for a merely missing M1 table, and an uncaught
    traceback with no record for malformed JSONL.
  - On the saved 24-cell dataset: **VALID_COMPLETE**, with intended = performed for
    24 cells, 24 summary rows, 3,276 records and decisions, 178 tables, 85,504 transition
    entries, 12 refinement pairs and 60 sealed files.
  - Compared with the original audit, 24/24 cell results and 10/10 shared denominators
    are identical (318 stage steps, 261,888 macro entries, 294 witnesses and the rest).
    The refinement list, FX1 and the hand checks are identical too.
  - The summary rows equal their cell artifacts as type-exact JSON (24/24), so nulls, 0
    and absent fields stay distinct.
  - The aggregates equal the review's independent counts: INTERVENTION 3 reductions and
    11 matches, AUTO 10 reductions and 5 matches.
  - **No scientific discrepancy** (`logs/scientific_comparison.json`).
- **R2 closed** in the isolated owner.
  - The 52 owner tests pass (31 unchanged and 21 new), in a layout **without** the run
    folder.
  - Restoring the old `task_word_path` fails 11 of them on behaviour: the three review
    examples, the ragged table, the negative and out-of-range targets, two
    invalid-unused-table cases, the set word, the iterator word and generator
    consumption (`logs/mutation_R2_old_task_word_path.log`).
  - The old function already rejected the other 9 malformed-call cases (the valid-call test passes on both). Those tests pin the
    contract but are not R2 discriminators.
- **Packaging.** The fixture is now `tests/fixtures/task_compaction_v1.json`,
  byte-identical to the run `fixtures.json` (sha256 6f7f7cd5…cbef690).
  - Three replacement patches pass `git apply --check` on the active tree.
  - Applied in a disposable copy, they reproduce the corrected owner, test and fixture
    byte-for-byte, and 73 + 52 = 125 tests pass (`logs/patch_check.log`).
- **Positioning** (`LITERATURE_MAP.md`). The component implements the greatest
  congruence (Knuutila 2001, Prop. 4) for an all-start, multi-action, multi-label
  contract.
  - K\* = N is proved equivalent to Zhang & Zhang Definition-5 (pairwise) observability
    of an encoded BCN, and to nothing stronger.
  - GFB and BBE scale by grouping variables and, in BBE's case, by restricting the
    domain. A GFB valid for every table yields a grouping no smaller than K\* (proved).
  - Same-contract symbolic methods were not read and remain a hypothesis.
- **Decision:** adopt after review; **NO_NEW_STUDY_JUSTIFIED** (`DECISION.md`,
  `V1_COMPLETION_PLAN.md`).

## Test and collection counts

| suite | before (original run) | now |
|---|---|---|
| accepted regressions | 73 | 73, unchanged; they still read the historical study fixtures (disclosed) |
| owner tests `test_task_compaction.py` | 31 | 52 (+21 R2) |
| frozen run-local `test_audit_labels.py` | 5 | 5 (rerun, pass) |
| revised run-local `test_audit_r2.py` | — | 7 |
| **total pytest** | 109 | **137** |
| audit pipeline matrix (subprocess cases) | 4 corruptions | 23 (includes the 4 originals as M10a–d) |

Other results:

- `ruff --output-format=concise` is clean on all changed and new sources
  (`logs/ruff.log`).
- The owner check passes over 18 files, and the planted copies are caught
  (`logs/owner_check.log`).
- Repository guards were rerun read-only (`logs/guards.log`) and git status is unchanged
  by them:
  - `check_test_manifest`, glossary sync, glossary conformance and `check_core_index`
    pass;
  - `check_single_engine` shows the same 9 pre-existing FAIL lines, identical to the
    original run and none naming this closure.
  - `make ci-local` was **not** run.

## Read before accepting

1. **Aggregate rule.** Aggregates are withheld whenever the audit is not VALID_COMPLETE,
   even when all 24 cells verify, for example when only the summary is corrupt. Attempt 2
   recorded the earlier, looser rule; the strict one is the conservative reading of the
   protocol.
2. **Inherited `!=` comparisons.** The frozen per-cell checks compare candidate-record
   fields with Python `!=`, which treats `0 == False` and `1 == 1.0` as equal. The
   revision added type-exact comparison for summary rows and top-level fields only. A
   bool or float substituted in a candidate-record field would still pass the frozen
   check unless schema rejects it, and schema covers only `record_id` and `candidate_id`.
   This is a known residual and was not fixed, to keep the frozen scientific checks as
   the single implementation.
3. **Intended counts.** Intended counts exist only where the declaration fixes them:
   cells, rows, records, decisions, tables, entries, pairs and seals. Stage steps,
   witnesses and macro entries are reported as performed only.
4. **Read-only dependency.** `repertoire_program.py` is mirrored unchanged and recorded
   in `OWNERSHIP_ADDENDUM.md`.
5. **Preservation scope.** Same scope as the original run (`src/preserve.py`, depth
   adjusted).
   - The before-snapshot was taken right after the empty output directory was created
     and before any development write.
   - Both snapshots are gzipped, with compressed and uncompressed SHA-256 in
     `logs/preservation_sha256.txt`.
   - Outside scope: `/tmp` copies and other top-level trees. Those are covered only by
     the git-status comparison.

## Where things are

| item | path |
|---|---|
| decision, plan, literature, ownership, changes | `DECISION.md`, `V1_COMPLETION_PLAN.md`, `LITERATURE_MAP.md`, `OWNERSHIP_ADDENDUM.md`, `CHANGELOG.md` |
| corrected isolated owner, tests and fixture | `isolated/index-deconvolution/{src/deconvolution.py, tests/test_task_compaction.py, tests/fixtures/task_compaction_v1.json}` |
| replacement patches (unapplied) | `patches/deconvolution_owner.patch`, `patches/test_task_compaction.patch`, `patches/fixture_task_compaction_v1.patch` |
| revised audit, matrix, owner guard, run-local tests | `src/audit_r2.py`, `src/probe_matrix.py`, `src/owner_check_r2.py`, `tests/test_audit_r2.py` |
| saved-data audit and comparison | `audit/audit.json`, `logs/audit_saved.log`, `logs/scientific_comparison.json` |
| matrix results and all attempts | `probes/final/`, `probes/attempt_01` (harness crash), `probes/attempt_02` (15/23), `probes/attempt_03`, `probes/attempt_03_saved_audit`, `attempts/attempts.jsonl`, `attempts/attempt_04_owner_check.log` |
| logs | `logs/` (tests, mutation, guards, ruff, owner check, patch check, transitive verification, literature sources, wall clock, git before/after, preservation) |
| regeneration | `zsh REGENERATE.sh <fresh dir>`: saved inputs only; regenerated `audit.json` and `matrix.json` are byte-identical |
| manifests | `source_manifest.json` (inputs read, with identities), `output_manifest.json` (every file here except itself) |
| time | `logs/time_ledger.json`: the closure charge is 1,440 of 3,600 s with every category under its cap and no transfers, against about 1,100 s of wall clock at the ledger write. The 300 s handoff allowance is a fixed conservative estimate. The 600 s Codex reserve is untouched. The historical erratum (1,685 + 300 = 1,985 s; handoff 518/900) is appended there, and the original ledger is unchanged. |

Ready for Codex review; not yet accepted.
