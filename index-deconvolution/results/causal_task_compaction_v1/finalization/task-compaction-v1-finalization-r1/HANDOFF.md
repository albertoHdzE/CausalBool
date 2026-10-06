# HANDOFF: task-compaction-v1 finalization r1

**Status: ready for Codex review; not yet accepted.**

Claude Code executed this round on 2026-10-05 from
`../../delegation/task-compaction-v1-finalization/NEXT_CLAUDE.md`.

- Nothing was staged, committed, pushed, published or scheduled.
- There was no production rerun, no M1–M4 minimisation, no new study and no dependency
  install.
- Recommendation: **V1_READY_FOR_SUPERVISOR** (`DECISION.md`). This completes, subject
  to review, only the exact known-model state-compaction v1 component. It is not a
  general causal-deconvolution theory.

## Conditional integration gate: PASSED, then adopted

Gates 1–7 were all true before any active write (`logs/gates_pre_adoption.json`).

1. **Inputs.** Packet 3/3, packet inputs 17/17 and freeze inputs 21/21 matched before
   work began. So did run_files 18/18, isolated 20/20, the original manifest 397/397
   and the closure manifest 153/153. Every must-not-exist path was absent.
2. **Patches.** The three reviewed patches applied in a disposable stage reproduce the
   reviewed bytes exactly. In that stage, 125 tests pass (73 + 52), and so do the 12
   existing run-local tests and the 8 new ones.
3. **Matrix.** **52/52**:
   - all 23 prior cases;
   - 23 field-category cases;
   - 6 historical-root cases.

   On the three Codex probes, `audit_r2` still returns VALID_COMPLETE with 0 issues
   (false acceptance reproduced). `audit_r3` returns INVALID at the intended fields, for
   example `record[0].decodable` (bool required) and `candidate[0].candidate.g`, and at
   `cells[0].baselines.identity.task_sufficient` (int ≠ bool) in both summaries.
4. **Saved evidence.** VALID_COMPLETE with 0 invalid, 0 missing and 0 skipped. The
   intended and performed counts agree throughout:
   - 24 cells;
   - 3,276 records and decisions;
   - 178 tables;
   - 85,504 transition entries;
   - 12 refinement pairs;
   - 60 seals;
   - 59 frozen identities.

   New counts separate comparisons from availability: 52,416 record fields compared
   type-exactly, 3,276 typed `null_reason` rules, 24 cell summaries and 24 summary rows
   compared against independent values. Cells, aggregates and every shared denominator
   equal r2 and the original audit (318 stage steps, 261,888 macro entries,
   294 witnesses; `logs/scientific_comparison_pre_adoption.json`). The aggregates are:
   AUTO 10 reductions and 5 matches, INTERVENTION 3 reductions and 11 matches. A fresh
   rerun is byte-identical.
5. **Independence.** `audit_r3` has its own identity, and the expected values come only
   from `expected_r3.py` and the frozen primitives. A test checks that it imports
   nothing from the producer or minimiser and never calls the frozen `audit_cell`.
6. **Historical identities.** The 21 freeze inputs were copied to `historical_inputs/`,
   verified against the original freeze and set read-only. Under the current root and
   under the snapshot root the audits agree scientifically; only `freeze_roots`
   differs. The snapshot cases behave as required: corrupted INVALID, extra file
   INVALID, missing file INCOMPLETE, substituted owner INVALID. All six scientific
   modules resolve to `task-compaction-v1-r1/isolated/`.
7. **Staging.** Documentation, the owner row and the patches were staged and tested in
   a disposable copy (`proposed/`, `patches/`). There was no target drift.

## Active paths changed (exactly five; before and after hashes in `CHANGELOG.md`)

- `index-deconvolution/src/deconvolution.py`
- `index-deconvolution/tests/test_task_compaction.py` (new)
- `index-deconvolution/tests/fixtures/task_compaction_v1.json` (new)
- `index-deconvolution/TASK_COMPACTION_V1.md` (new)
- `GOVERNANCE/CORE.md` (+1 owner row)

The git-status delta is exactly these five (`logs/git_before.txt`, `logs/git_after.txt`).
Preservation, 110,434 files before and 110,436 after, shows only these changes:

- changed: `deconvolution.py` and `CORE.md`;
- added: the test file and the fixture;
- `TASK_COMPACTION_V1.md` is outside the preservation scope and is covered by git
  status.

## After adoption (gates 8–12)

- **Active tests.** 125 pass, and the 18 documentation examples pass against the active
  owner. The test, fixture and core bytes equal the reviewed content. The run-local
  tests give 20/20. The post-adoption matrix gives 52/52, with P and F verified against
  the historical root.
- **Historical verification passes.** Its `audit.json` is byte-identical to the
  pre-adoption historical-root audit.
- **Current-root disclosure.** The current-root audit is now **INVALID by design**. It
  reports exactly two identity mismatches, `inputs/GOVERNANCE/CORE.md` and
  `inputs/index-deconvolution/src/deconvolution.py`
  (`audit/post_adoption_current_root/`). The post-adoption preflight shows the same two
  paths for the packet inputs.
  - The original r2 regeneration is therefore not compatible with the current tree. Use
    `VERIFY_HISTORICAL.sh`.
  - `freeze.json` was not rewritten and no seal check was weakened.
- **Lint and owner.** `ruff` is clean on every changed and new source. The owner check
  finds one definition of each name over 13 files, including `imp-prices/vendor`, and a
  planted renamed copy and a same-name copy are both caught.
- **Read-only guards.** The output is the baseline except for two expected lines:
  - `check_core_index` goes from 71/71 to 73/73, because the new row names two new
    paths;
  - the vendor-parity `deconvolution.py` failure now compares against the new canonical
    hash.

  Test manifest 122/122, glossary sync and glossary conformance are clean. Root
  collection is unchanged at 593 (`logs/guards_diff.txt`).

## Inherited, unresolved (not caused here, not repaired)

- `check_single_engine`: the same 9 FAIL lines before and after.
- `imp-prices/tests/test_vendor_parity.py`: 2 FAIL (`causalbool.py` and
  `deconvolution.py`), before and after; imp-prices was not modified.
- Full CI was not claimed. `make ci-local` was excluded because it rewrites unrelated
  results.

## Read before accepting

1. **"FX2 two-step".** The packet named an "FX2 two-step fixture", but in the fixture
   file FX2 is `FX2_one_step` and the two-step one is `FX3_two_step`. The documentation
   works through FX3 (`K* = N = 4`, word `[0, 0]`). The declared intervention example
   is `FX4_added_action` (K 2 → 3).
2. **Scoped test command.** It runs from `index-deconvolution/` with `-c /dev/null
   --rootdir=.`. From the repository root, the root `conftest.py` ignores these files
   (attempt 3), and the packet forbids changing global collection.
3. **Duplicated calculation.** `expected_r3.py` is a second copy of the frozen
   `audit_cell` expectation code, which the protocol permits as "a separately versioned
   copy". The revised audit runs only that copy, and parity with the frozen copy is a
   test, not a runtime path.
4. **Graph tools.** The graph-discovery tools (codebase-memory MCP) were unavailable;
   discovery was by direct reading of the named files.
5. **Time.** The ledger charges 1,607 of 3,600 s with every category within its cap, no
   transfers and the 600 s reserve untouched (`logs/time_ledger.json`). The historical
   charges of 1,985 s and 1,440 s are unchanged.

## Commands

- Active, scoped: `zsh RUN_ACTIVE_TESTS.sh`
- Saved historical evidence: `zsh VERIFY_HISTORICAL.sh <fresh dir>`

Deterministic outputs are in `audit/*/audit.json`; timings appear only on stdout and in
the logs.

## Where things are

| item | path |
|---|---|
| decision, changes, inventory, matrix | `DECISION.md`, `CHANGELOG.md`, `FIELD_INVENTORY.md`, `TEST_MATRIX.md` |
| audit and tests | `src/audit_r3.py`, `src/expected_r3.py`, `src/probe_matrix_r3.py`, `tests/test_audit_r3.py` |
| evidence | `audit/{pre,post}_adoption_{current,historical}_root/`, `matrix/`, `matrix_post_adoption/`, `logs/` |
| historical snapshot | `historical_inputs/`, `historical_inputs_manifest.json` |
| active patches and content | `patches/`, `proposed/`, `logs/active_before.txt`, `logs/active_after.txt` |
| protection | `logs/preflight*.json`, `logs/preservation_*`, `logs/git_*`, `logs/guards_*` |
| attempts and time | `attempts/`, `logs/time_ledger.json`, `logs/wallclock.jsonl` |
| manifests | `source_manifest.json`, `output_manifest.json` |

Ready for Codex review; not yet accepted.
