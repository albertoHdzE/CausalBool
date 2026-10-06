# audit_r3 test matrix

The matrix runs every case on a copy in a fresh scratch directory, and the saved
evidence is only read. Results are in `matrix/matrix.json`, recorded before adoption,
and in `matrix_post_adoption/matrix.json`, recorded after adoption with
`--post-adoption`. Both give **52/52 as required**.

A case counts as *as required* only when all of the following hold:

- the status and exit code are the expected ones;
- aggregates are withheld unless the status is VALID_COMPLETE;
- every required `where|field|check` fragment is present;
- nothing tracebacks;
- the declared minimum number of cells was still audited, so independent checks
  continued.

| group | cases | what is covered |
|---|---|---|
| P | 23 | The closure's 23 cases (M01–M10d), each mutation imported from the hash-pinned closure `probe_matrix.py` with the same expected status. Four have field-level fragments now: M03a, M04, M08a, M08b and M10d. |
| F | 23 | The field categories. **F01–F03 are the exact three Codex probes**: `audit_r2` returns VALID_COMPLETE with zero issues on all three, and r3 returns INVALID at the intended fields. The rest are:<ul><li>float in nested ratios: F04 (record), F05 (summary);</li><li>null where not allowed: F06;</li><li>a value where null is required: F07;</li><li>wrong candidate declaration metadata: F08;</li><li>a missing required field: F09a (record), F09b (cell), F09c (fixture K);</li><li>malformed index containers: F10a–c;</li><li>a paired value mutation of both summaries: F11;</li><li>INVALID together with missing evidence: F12;</li><li>a top-level float count: F13;</li><li>a cell scalar value: F14;</li><li>a witness bookkeeping name: F15;</li><li>a bool in an action declaration: F16;</li><li>an undeclared record field: F17;</li><li>a bool summary count: F18;</li><li>F01's mutation in normal mode, where the seal and the field both fire: F19.</li></ul> |
| H | 6 | <ul><li>Default current root: H01. VALID_COMPLETE before adoption; after adoption it must be INVALID with exactly the two adopted-input mismatches.</li><li>Explicit historical root: H02.</li><li>Snapshot copies that are corrupted (H03), carry an extra file (H04), lack a file (H05, INCOMPLETE) or substitute the reviewed owner (H06).</li></ul> |

Run-local pytest gives 20 tests. Eight are new in `tests/test_audit_r3.py`:

- type-exact recursion;
- the record schema;
- parity of `expected_r3` with the frozen `audit_cell` on all 24 saved cells, with zero
  frozen issues and type-exact equality of the records and summaries;
- source resolution, plus the rejection of a switched module;
- the import boundary and single-expectation rule, run on both new sources;
- label precedence.

The remaining twelve are the closure's r2 tests (7) and the frozen audit's tests (5).

**Disclosure.** `matrix/` was produced by `probe_matrix_r3.py` *before* the
`--post-adoption` option was added. Without the flag, that option changes no code path,
and the final source is the one in `src/`. `attempts/attempt_01_matrix/` holds the first
run (49/52). The three misses were wording errors in the harness's expected fragments;
`audit_r3` was unchanged between the two runs.
