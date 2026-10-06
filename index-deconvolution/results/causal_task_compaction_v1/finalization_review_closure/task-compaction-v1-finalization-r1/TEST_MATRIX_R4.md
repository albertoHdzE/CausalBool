# Test matrix for audit revision r4 (declared before any r4 run)

Declared at executor second ~200, before `audit_r4.py` was executed. Every case runs on a
copy of `task-compaction-v1-r1/production` in a fresh scratch directory, with freeze inputs
read from the explicit root `finalization/task-compaction-v1-finalization-r1/historical_inputs`
(H cases use copies of that snapshot). Saved evidence is only read.

A case is *as required* iff status, exit code, aggregate withholding and every required
`where|field|check` (invalid) and `where|missing` (missing) fragment match, nothing
tracebacks, and the declared independent checks still ran (cells performed).

## Inherited: 52 cases (P 23, F 23, H 6)

Reused unchanged from the hash-pinned `probe_matrix_r3.py` in its post-adoption form
(`--post-adoption`: explicit historical root for P and F; H01 must disclose exactly the two
adopted-input mismatches). Only the audited program changes (r3 -> r4).

Intended diagnostic wording changes, none of which alters a required fragment:

- byte mismatch: `sealed artifact K: present bytes differ from the pinned seal authority`
  (r3: `... from the seal`); the r3 prefix `present bytes differ` is kept, so F19 and M09b
  match unchanged;
- absent data file: unchanged (`sealed artifact K`), so M09a matches unchanged;
- `report.integrity` gains intended / candidate-entry / compared / mismatch counters and loses
  r3's `sealed` (which was the size of the candidate's own map);
- `report.fixture_FX1` is always written, with `intended`, `file_available`, `schema_valid`,
  `certificate_checks_completed`, `validity`, `minimality`, `issues`; M10c still requires
  validity True and minimality False.

## New: N cases (R1 fixture, R2 seal)

| id | change (on a copy) | mode | expected | required evidence |
|---|---|---|---|---|
| N01a | FX1 `fixture_id` = 123 | bypass | INVALID | `FX1|fixture.fixture_id|type int != expected str`; fixture certificate not completed |
| N01b | FX1 `fixture_id` = "NOT_FX1" | bypass | INVALID | `FX1|fixture.fixture_id|value 'NOT_FX1'` |
| N01c | FX1 `fixture_id` removed | bypass | INVALID | `FX1|fixture.fixture_id|missing required field` |
| N01d | FX1 `coarsening` = null | bypass | INVALID | `FX1|fixture.coarsening|null where a value is required` |
| N01e | FX1 `K` = true | bypass | INVALID | `FX1|fixture.K|non-boolean int` |
| N01f | FX1 `outputs` = [0,1,1,1] | bypass | INVALID | `FX1|fixture.outputs[1]|value 1 != expected 0` |
| N02a | FX1 file removed | normal | INCOMPLETE | missing `FX1|FX1_identity.json` and `seal|sealed artifact fixtures/FX1_identity.json`; fixture intended 1, available false, completed 0 |
| N02b | COR3: identity partition, valid but not minimal | bypass | INVALID | `FX1|stage-induction check`; validity True, minimality False, completed 2 |
| N03a | seal `sha256` = {} | normal | INCOMPLETE | 60 missing `seal|seal entry`; intended 60, entries agreeing 0, hashes compared 60 |
| N03b | seal `sha256` = {} | bypass | INCOMPLETE | as N03a |
| N03c | seal entry `fixtures/FX1_identity.json` deleted | normal | INCOMPLETE | missing `seal|seal entry fixtures/FX1_identity.json`; entries agreeing 59 |
| N03d | as N03c | bypass | INCOMPLETE | as N03c |
| N03e | seal.json removed | normal | INCOMPLETE | missing `seal|seal.json`; intended 60 |
| N04a | undeclared seal entry `extra.json` | normal | INVALID | `seal|sha256[extra.json]|undeclared path` |
| N04b | `sha256[summary.json]` = "XYZ" | normal | INVALID | `seal|sha256[summary.json]|malformed hash` |
| N04c | seal `files` = 59 | normal | INVALID | `seal|files|` |
| N04d | `sha256[imports.json]` = 64 zeros, data unchanged | bypass | INVALID | `seal|sha256[imports.json]|contradicts the pinned authority` |
| N05a | imports.json + "\n" AND its candidate seal hash updated to match | normal | INVALID | `seal|sha256[imports.json]|contradicts` and `seal||sealed artifact imports.json: present bytes differ` |
| N05b | as N05a | bypass | INVALID | `seal|sha256[imports.json]|contradicts` |
| N06 | seal entry FX1 deleted AND FX1 `fixture_id` = 123 | bypass | INVALID | invalid `FX1|fixture.fixture_id|` and missing `seal|seal entry fixtures/FX1_identity.json`; 24 cells performed |
| N07 | none (pristine) | normal | VALID_COMPLETE | seal intended 60, entries 60, compared 60, mismatches 0; fixture intended 1, completed 2 checks, validity and minimality True |

Every N case except N02b and N07 must also produce a fixture/seal issue whose `where` is
`FX1` or `seal`; N cases must perform all 24 cells except N03e/N02a where the frozen chain
is unchanged (24 also required).

## Old-defect regression (r3 on the same copies)

N01a, N01b, N01d, N03a, N03c, N05a are also run under the pinned `audit_r3.py`. Required: r3
returns VALID_COMPLETE (exit 0) on each, which is the defect the review reproduced; r4 does not.

## Fault restoration (mutants of audit_r4, in /tmp, executed under the original file name)

| mutant | restored r3 behaviour | must be caught by |
|---|---|---|
| X1 | fixture_id type failure without an issue | N01a |
| X2 | fixture_id value not bound to the declaration | N01b |
| X3 | null coarsening accepted | N01d |
| X4 | intended seal set taken from the candidate seal | N03a, N03c |
| X5 | data hashes compared with the candidate seal, not the authority | N05a |
| X6 | bypass also suppresses missing-entry evidence | N03d |

Caught means the case is no longer as required, with the case's own fragment absent.

## Other runs

20 inherited run-local tests (r3 8, r2 7, frozen 5) plus new `tests/test_audit_r4.py`;
125 active tests and TASK_COMPACTION_V1.md examples once; ruff on new code; r4 on saved data
twice (byte-identical audit.json); scientific comparison against the saved r3 audit.
