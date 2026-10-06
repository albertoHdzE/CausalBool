# CHANGELOG: task-compaction-v1-r1 review closure (2026-10-05)

All changes are in this directory or in disposable `/tmp` copies. The active tree, the
frozen run and the sibling repositories are untouched.

## Owner (isolated copy `isolated/index-deconvolution/src/deconvolution.py`)

- `_transition_contract(transitions, N=None)` is factored out of `_task_contract`; the
  minimizer's validation behaviour and messages are unchanged.
- `task_word_path` now:
  - applies the full table contract (all tables, including unused ones);
  - requires a built-in int state in range;
  - requires `word` to be a list or tuple, which rejects generators unconsumed and
    `None`, strings and sets;
  - validates every action before the first step, with the position in the message.

  Valid-call results are unchanged.

## Tests (isolated `tests/test_task_compaction.py`)

- The fixture lookup is now `tests/fixtures/task_compaction_v1.json`, a byte copy of
  the run file `fixtures.json`; the docstring records the provenance.
- 21 tests are appended: 19 parametrised malformed calls, one generator-consumption test
  and one valid-call test that includes noncommuting actions. The existing 31 tests are
  unchanged.

## Audit (new run-local revision `src/audit_r2.py`; the frozen `audit.py` is untouched)

- The pipeline is separated into schema, availability and integrity, the frozen
  scientific checks (imported by path, sha256-verified), and reporting.
- Missing evidence is INCOMPLETE, malformed or contradictory evidence is INVALID, and
  INVALID takes precedence; both issue lists survive.
- JSON and JSONL are parsed per line, with line numbers. NaN and Infinity are rejected,
  and types are exact (bool is never an int).
- In integrity mode, a sealed file that is absent is missing; a sealed file whose bytes
  are wrong is invalid.
- Summary rows must match the declared cell set exactly, and every field is compared
  type-exactly with the audited cell. The top-level counts and the refinement list are
  checked too.
- Intended and performed counts are reported per denominator, together with skipped
  dependencies and their reasons.
- Aggregates are withheld unless the whole audit is VALID_COMPLETE.

## New run-local files

| file | purpose |
|---|---|
| `src/probe_matrix.py` | the declared matrix (PROTOCOL R1 items 1–10, 23 cases) |
| `src/owner_check_r2.py` | owner guard with a plant |
| `src/preserve.py` | copied from the original run, REPO depth 4→5 |
| `tests/test_audit_r2.py` | 7 tests |
| `REGENERATE.sh` | regenerates the closure evidence from saved inputs |

## Patches (`patches/`)

The replacement patches are against the active tree:

- `deconvolution_owner.patch`
- `test_task_compaction.patch` (new file)
- `fixture_task_compaction_v1.patch` (new file)

They supersede the original run's two patches, which are kept unchanged in the frozen
run.

## Layout

The closure's isolated tree is a byte copy of the original run's `isolated/`, with two
differences:

- the corrected owner, test and fixture;
- the `results/causal_task_compaction_v1/` mirror removed, so portability is proven by
  construction.
