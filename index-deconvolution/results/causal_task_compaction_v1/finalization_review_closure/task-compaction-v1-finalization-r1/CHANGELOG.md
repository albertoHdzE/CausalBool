# Changelog -- final audit closure (r4)

All paths below are new and live only in this directory; nothing outside it was written
except scratch under /tmp.

- `src/audit_r4.py` -- audit revision r4: authority-based seal check (R2), declared-fixture
  check (R1), r4 identity stamp. Imports r3 by path with SHA-256 checks of audit_r3.py,
  expected_r3.py, the original output manifest and the original seal.
- `src/probe_matrix_r4.py` -- the declared matrix: inherited P/F/H (52) from the pinned
  probe_matrix_r3.py, new N (21), old-defect regression under r3 (6), fault-restoration
  mutants (6 mutants, 7 runs).
- `src/compare_r4.py` -- r4 versus saved r3 scientific comparison (one rule correction during
  this run; see attempts/attempt_03_comparison).
- `src/preflight_r4.py` -- packet, 397/153/248 manifests, snapshot and active-path checks.
- `src/preserve.py` -- byte copy of the finalization preserve.py (same depth; it excludes its
  own run directory, so it now excludes this one).
- `tests/test_audit_r4.py` -- 9 run-local tests.
- `VERIFY_R4.sh` -- the new historical verification command for r4. `VERIFY_HISTORICAL.sh`
  (r3) is unchanged and does not contain these checks.
- `TEST_MATRIX_R4.md` (declared before running), `FIELD_INVENTORY_R4.md`, `DECISION.md`,
  `HANDOFF.md`, `source_manifest.json`, `output_manifest.json`, `audit/`, `matrix/`, `logs/`,
  `attempts/`.

Report-format changes relative to r3: `audit_revision` "r4"; `integrity` now carries
`intended_entries`, `candidate_seal`, `candidate_entries_present/agreeing/missing/rejected`,
`data_absent`, `hashes_compared`, `hash_mismatch` (r3's `sealed`, `absent` removed);
`fixture_FX1` always present with availability and completion counters; new counts
`seal_entries_agreeing`, `fixtures_checked`, `fixture_certificate_checks`; new keys
`seal_authority`, `fixture_declaration`; byte-mismatch wording ends "from the pinned seal
authority".
