# Changelog: task-compaction-v1 finalization r1 (2026-10-05)

## Run-local (new files, this directory only)

- `src/audit_r3.py` (new identity). It adds the typed field inventory and type-exact
  comparison against independent expectations, and `--inputs-root` for historical
  identities. It also adds a source-resolution check for the six scientific modules.
  It imports the frozen `audit.py` and `audit_r2.py`, both hash-pinned, and neither is
  modified.
- `src/expected_r3.py`: the frozen `audit_cell` calculation, refactored to return its
  expected values. It is the only live copy in r3, and parity with the frozen function
  is tested on all 24 cells.
- `src/probe_matrix_r3.py`: the 52-case matrix. `tests/test_audit_r3.py` adds the 8
  tests.
- `src/preflight.py`, `src/compare_audits.py`, `src/owner_check_r3.py` and
  `src/preserve.py`. The last is copied from the closure with its logic unchanged.
- `historical_inputs/` plus `historical_inputs_manifest.json`: the 21 freeze inputs,
  each verified against the original freeze and set read-only before adoption.
- `RUN_ACTIVE_TESTS.sh` and `VERIFY_HISTORICAL.sh`: the two delivered commands.

## Active repository (the five authorised paths, after the gates passed)

| path | change | before → after (sha256, bytes) |
|---|---|---|
| `index-deconvolution/src/deconvolution.py` | reviewed closure patch, applied byte-identically | `bd549796…a3a` 34422 → `4e49c064…fbb` 41728 |
| `index-deconvolution/tests/test_task_compaction.py` | new, reviewed patch (52 tests) | absent → `cdc3fe50…f17` 10444 |
| `index-deconvolution/tests/fixtures/task_compaction_v1.json` | new, reviewed patch (original fixture bytes) | absent → `6f7f7cd5…690` 13407 |
| `index-deconvolution/TASK_COMPACTION_V1.md` | new contract document (18 executable examples) | absent → `e7733a3a…8ae` 12921 |
| `GOVERNANCE/CORE.md` | one owner row added after the `deconvolution.py` row | `97baff11…5e03` 19291 → `9a4bd704…125a` 19596 |

Patches: three from `review_closure/.../patches/` (unaltered) plus
`patches/task_compaction_doc.patch` and `patches/core_owner_row.patch`. Full content is
in `proposed/`.
