# HID-search-v2 prefreeze gate (PROTOCOL section 5, step 4), 2026-10-02

Status at this gate: implementation complete, tests green, development complete, no
reserved string generated. Everything below is retained in this directory or named path.

## Implementation map and sources

* Requirement-to-code map: `implementation_map.md` (copy of
  `results/hierarchy_search_v2/implementation_map.md`).
* Source identity: frozen by `freeze_v2` into `search-confirm-v2-r1/freeze.json`
  (complete closure: every non-test module of `hierarchy/`, the schema-cover owner
  `src/deconvolution.py` and its import `src/causalbool.py`, and the shared owner
  `src/description_lengths.py` at its ACTIVE hash `b6fb6eaf…`, the pre-existing
  `bdm_1d_trace` addition disclosed in PROTOCOL section 3; the trace function is not
  used by inference) and archived in `search-confirm-v2-r1/source_snapshot.tar`.
* Unchanged scientific owners (hashes equal to INITIAL_SOURCE_STATE /
  DELEGATION_MANIFEST): `infer.py`, `candidates.py`, `model.py`, `wire.py`, `decode.py`,
  `baselines.py`, `corpus.py`, `src/deconvolution.py`, `src/causalbool.py`,
  `src/description_lengths.py`.
* Resolved configuration: `selfcheck_search_v2.json` (registry and every constant equal
  to `study_contract.json`); per-method configs and hashes recorded in the freeze.

## Tests, lint, guards

* `tests.txt`: 385 passed (249 package + 136 shared-owner file), ruff clean on every
  changed Python file, both selfchecks exit 0.
* `guards/`: `check_test_manifest` 0, `check_core_index` 0, `check_single_engine` 1.
  The single-engine failure lists only sites that predate this work: the external
  `.kilo/worktrees/held-saguaro/*` tree, the pinned imp-pathinfo mirror, and two stray
  untracked copies `index-deconvolution/protocols/description_lengths.py` (r1-era bytes
  `052786ca…`) and `index-deconvolution/protocols/causalbool.py`, both already listed in
  `../preservation/working_tree_status_before.txt` (lines 57-58) before any edit of this
  assignment. None was introduced or modified here; none was touched.

## Development results (previously inspected inputs; exploratory, not confirmatory)

* `development/dev-search-v2-pilot`: 96 strings, 1,536 rows, valid and complete;
  deliberate interruption plus resume, and a fresh replay of 12 cases, identical.
* `development/dev-search-v2-regression`: 1,632 strings, 26,112 rows, valid and
  complete; 8,160 nesting pairs checked, 0 violations, 0 resource fallbacks.
* `legacy_identity_vs_r1.json`: `hid_legacy` equals r1 `hid_full` byte-for-byte on
  1,632/1,632 strings; all 16,320 baseline and portfolio archives identical to r1.
* Development diagnostics (`development/dev-search-v2-regression/diagnostics.json`):
  136/136 F12 supplied-boundary references built and decoded.
* Attempts and the one external interruption: `attempts_notes.md`, logs
  `pilot_attempt1.log`, `regression_attempt1.log`, `regression_attempt2.log`.
* No defect correction was needed after the first development run; no parameter was
  changed; no amendment is requested.

## Resource accounting

Durable ledger `../execution_ledger.jsonl` at this gate: development 5,313.8 s of
14,400 s (includes a conservative 60 s entry for the externally interrupted invocation);
diagnostics/verification 75.6 s of 7,200 s (development-run diagnostics were charged to
this category, conservatively); reserved 0 s of 21,600 s.

## No-reserved-access declaration

No string from `search_v2_confirmation`, `search_v2_transfer` or `search_v2_stress` has
been generated, scored, previewed or used. No 131,072- or 131,075-bit input has been
generated. Fixture tests used only `search_v2_fixture` (maximum length 65,539) and the
historical development keys authorised by BENCHMARK.md section 1. The freeze records an
automated exposure scan of every generated-data artefact under the study root, and
`study_corpus` refuses to generate a reserved role without a freeze declaring it.
