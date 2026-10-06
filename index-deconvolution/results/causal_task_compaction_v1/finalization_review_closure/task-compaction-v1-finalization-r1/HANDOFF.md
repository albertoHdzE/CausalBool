# HANDOFF -- task-compaction-v1 final audit closure (audit revision r4)

**Status: ready for Codex review; not yet accepted.**

Packet: `delegation/task-compaction-v1-final-audit-closure` (NEXT_CLAUDE, PROTOCOL, ACCEPTANCE,
manifest), against `supervision/task-compaction-v1-finalization-r1/REVIEW.md` (R1, R2).
Executor recommendation: **V1_READY_FOR_SUPERVISOR** (DECISION.md).

## What changed
One new run-local revision, `src/audit_r4.py`, wrapping the hash-pinned r3. It rebinds
`check_fixture` (R1), r2's `check_seal` as r3 sees it (R2) and the finisher (r4 identity);
everything scientific stays r3/r2/frozen. See CHANGELOG.md and FIELD_INVENTORY_R4.md.

## Acceptance gates
| # | gate | evidence | result |
|---|---|---|---|
| 1 | only this directory and /tmp written; active, old trees, snapshot, manifests unchanged | `logs/preflight_before.json`, `logs/preflight_after.json` (packet 3, inputs 17, run_files 18, isolated 20, 397/153/248 manifests, snapshot 21, five active paths); `logs/preservation_diff.json` 110,713 -> 110,713, 0 changed/added/removed; `logs/git_before.txt` == `logs/git_after.txt` | pass |
| 2 | R1 | N01a-f INVALID with field paths (fixture_id int, wrong string, missing, coarsening null, K bool, outputs rebound); N02a absent file INCOMPLETE, available false, 0/2 completed; N02b (COR3) validity True, minimality False, 2/2 completed; N07 1 intended, 2/2 completed | pass |
| 3 | R2 | authority = original seal (SHA-256 c97e8031...) confirmed by the original output manifest (d6aff053..., all 60 values); N03a-e INCOMPLETE in both modes (empty map, deleted entry, absent seal; intended stays 60); N04a-d INVALID (undeclared path, malformed hash, files 59, contradicting hash in bypass); N05a/b file + matching candidate hash INVALID in both modes | pass |
| 4 | 52 inherited + new matrix, precedence, withheld aggregates, real defects | `matrix/matrix.json`: 73/73 as required (P 23/23, F 23/23, H 6/6, N 21/21); N06 INVALID with the missing entry also recorded and 24 cells performed; old-defect: r3 returns VALID_COMPLETE, exit 0 on 6/6 of the same copies (explicit historical root, so no incidental input mismatch); mutants X1-X6 caught 7/7 runs with the case's own fragment absent | pass |
| 5 | tests and lint | `logs/run_local_tests.log` 29 passed (r4 9, r3 8, r2 7, frozen 5); `logs/RUN_ACTIVE_TESTS.log` 125 passed + TASK_COMPACTION_V1.md examples pass; `logs/ruff.log` clean on src/ and tests/ | pass |
| 6 | determinism and scientific equality | runs A (`audit/historical_root/audit.json`) and B (/tmp) byte-identical; `logs/scientific_comparison_r4_vs_r3.json`: status, cells (24), aggregates, refinement pairs, candidate records, tables, hand fixtures equal to the saved r3 audit; every shared count equal; anchors 24 cells / 3,276 decisions / 85,504 transition entries; differing keys only provenance, the two revised reports and three new counters | pass |
| 7 | new command | `VERIFY_R4.sh <fresh dest>` run from `/`: snapshot 21/21, r4 VALID_COMPLETE, seal 60/60/60/0, FX1 2/2, byte-identical audit, 29 tests (`logs/VERIFY_R4.log`); refuses an existing destination | pass |
| 8 | deliverables, failed attempts, time | this file, DECISION, CHANGELOG, TEST_MATRIX_R4 (declared before running), FIELD_INVENTORY_R4, source/output manifests, `attempts/attempts.jsonl` (2 failed attempts preserved), `logs/time_ledger.json`, `logs/wallclock.jsonl` | pass |

## Wording changes in inherited cases
None altered a required fragment. Byte mismatch now reads "...present bytes differ from the
pinned seal authority"; r3's integrity keys `sealed`/`absent` are replaced by the counters in
CHANGELOG.md; `fixture_FX1` is always written.

## Failed attempts (preserved)
1. Run commands used `$PWD` inside `(cd /tmp && ...)`, so the path resolved to /tmp; nothing
   was written; rerun with an absolute path.
2. `compare_r4.py` reported NOT OK because its own rule did not admit the `counts` key even
   though every shared count was equal and the only extras were the three declared new
   counters. Science was equal. Rule corrected; first output kept in `attempts/attempt_03_comparison/`.

## Limitations
Not run: `make ci-local`, repository guards, vendor parity (known failures untouched, no waiver
added). In-process rebinding of r3's module attributes is the wrapper mechanism; r3's files are
unchanged and its own command `VERIFY_HISTORICAL.sh` still runs r3 without these checks.
Mutants are executed under audit_r4.py's file name, so their reported `audit_r4.py` identity
is the unmutated hash; they are labelled by mutant id in `matrix/matrix.json`.
Scratch (not evidence): /tmp/r4_try1, /tmp/r4_matrix_a1_*, /tmp/r4_run_B, /tmp/r4_verify_dest,
/tmp/r4_preservation_*.json.

## Time
Cap 1,800 s; Codex reserve 300 s separate; historical charges 1,985 + 1,440 + 1,607 s unchanged.
Executor charge to the final manifest write: 711 s (start epoch 1791245613, stamp 1791246309 plus 15 s allowance for the manifest write), within the 1,800 s cap.
