# Validator closure for confirm-v1-r1: handoff for Codex review

Date: 2026-10-02. Assignment: `index-deconvolution/KICKOFF_hierarchy_validator_closure.md`,
which closes the three cases in bitacora 37 §4 (R1a, R1b, R1c).

**Status: a patch for review. It has not been applied, committed or frozen.** The
patched sources do **not** match the confirm-v1-r1 freeze
`f970efff16a2d08bf1dd22eee1386c164af5ba67b22137fefcf06cd182b27f5c`: three frozen
sources differ by design. How to integrate and version the patch is the reviewer's
decision.

## 1. What is in this directory

| path | content |
|---|---|
| `validator_closure.patch` | unified diff, repository-relative (`patch -p1` from the repo root) |
| `SOURCE_HASHES.json` | frozen, active, isolated-baseline and isolated-patched SHA-256 for all 22 frozen sources/protocols plus the changed test file |
| `test_retained_validator_edges_inverted.py` | the three retained reproductions with the same damage and inverted assertions |
| `corpus_harness.py` | read-only validation of the full retained run by a chosen source tree (not production verification) |
| `corpus_validation.{baseline,patched}.json` | harness output for each tree |
| `logs/` | pytest, ruff, crossover and harness logs |

**Patch SHA-256:** `587d7bc0e0b9f598a80be99776655e3cc8d1df355cfa62884e7fbd8ee5809346`
(264 insertions, 28 deletions, four files). `patch -p1 --dry-run` applies cleanly to
the active tree. It was a dry run, so nothing was written.

**Isolated copy:** `/Users/alberto/Documents/projects/CausalBool_validator_closure/`, outside
the repository. This keeps a second `src/description_lengths.py` away from the
single-engine guard. It holds `baseline/` and `patched/` mirrors of the repository-relative
paths that the freeze names: `index-deconvolution/hierarchy/`, the two `index-deconvolution/src`
owners, `src/description_lengths.py`, its value test, the protocol files and the root
`ruff.toml`. `imp-causalNet-paper/src` is a symlink to the active one because the
description-length owner delegates Variant A/C to it. `baseline_tree.sha256` lists all
44 files that were copied.

## 2. Changed files

| file | frozen SHA-256 | patched SHA-256 |
|---|---|---|
| `index-deconvolution/hierarchy/validation.py` | `e264dc7232afd211d2b87a5fe92e3203d8cf48a94e31d8e7cc9e196650945cb7` | `e0732fcba694183ce8a7d2262273b180cd60a36d58bffff9b44b0c80078716a9` |
| `index-deconvolution/hierarchy/cli.py` | `601607fcb386585d5f7d0acaecd80d628291fb284303cf59414937f3c167f064` | `4bc0006c0e6ebbc239866f79090bb85ab510541e4c0c6c41bd7e416bf4ed469f` |
| `index-deconvolution/hierarchy/report.py` | `6d32be18cbfc6364e1d0ac9f26fb7d7743cb0ffde0e7303cefe1182f52d6ea54` | `8721bc2cede0ae06f3eac1e96a5ccb764c3e1335a6347b4918c9026a5d7bb02b` |
| `index-deconvolution/hierarchy/tests/test_validation.py` | not a frozen source | `6d52edea34a43d5bbe3b3cb28819e0395a41d94f55de8ec24fe5a77e5d2c05f7` |

The isolated baseline and the active tree both equal the freeze on **22 of 22** frozen
sources and protocols. The patched tree equals the freeze on 19 of 22. No inference,
codec, decoder, wire, corpus, benchmark or statistical function is touched. Only
validation and presentation error handling changes.

### R1a: missing or malformed archives reach the structured invalid record

- `cli._separate_process_sample` now checks each sampled archive with `is_file()`
  before it copies it. An absent file is listed under `unavailable` and makes the sample
  not `all_ok`. It is never replaced by another member of the stratum. Decoder failures
  and wrong decodes are listed under `failed` with the decoder's own error class and message.
  `cmd_verify` adds one invalid reason for unavailable strata, in addition to the
  validator's per-archive reasons.
- `cmd_verify` first replaces any existing `verification.json` with a `not_verified`
  record (`exit_code: null`). If verification does not finish, the file therefore shows
  that it did not finish. It never shows an older success. Unrelated exceptions still
  propagate. A planted `ZeroDivisionError` reaches the caller.
- `report.representative_ledgers` presents a chosen archive as `unavailable` when its
  file is missing, its bytes do not hash to the row, or it raises the decoder's declared
  `ArchiveError`. Decoding now runs before `archive_ledger`, so a malformed archive cannot
  reach the ledger's internal assertion. The `AssertionError` for an encoder/decoder
  disagreement on a decodable archive is unchanged.
- `cmd_report` computes the summary, the ledgers and the claim ledger **before** it writes
  any of them. A failure therefore cannot leave a mix of fresh and stale files.

### R1b: rows files are checked before they are keyed by method

A new function, `validation.rows_file_problems`, is called by `validate_run` for every
declared case file. It requires all of the following:

- the file is a list of objects;
- every method is declared;
- no method appears twice, whether the copies are identical or conflicting;
- every row carries the case's `case_id`, `split`, `family`, `base_length`, `replicate`,
  `ragged` and `n_bits`.

Any of these problems is engineering invalidity with a specific reason. The existing
exact comparison with `cases.jsonl` and the JSONL duplicate checks are unchanged and
still run on well-formed files.

### R1c: undeclared rows are validated, not filtered

`validate_run` passes **every** row in `cases.jsonl` to `validate_study`. Rows from any
other split, case or method are reported as `unknown`, and each one is invalid. Every
`rows/*.json` file that is not a declared case is also invalid. The docstring now states
that `splits` is the run's complete split set and that there is no subset mode, and
`ctx["scope"]` is recorded as `"whole_run"`. If `validate_run` is called with a subset,
such as `["confirmation"]` on a full run, the result is invalid with the other split's
rows listed. It is never a partial acceptance. Expected membership is unchanged.

## 3. Decisions for the reviewer

- **D1. A rows file's method set.** It must be unique and declared, and it must equal
  `cases.jsonl` for that case. It does **not** have to equal the full declared method
  list. Production always writes all 16 methods, including `not_run` rows. A strict
  "all 16" rule would turn the existing `test_missing_ablation_method…` test (exit 3, an
  incompleteness test) into exit 2. I kept the current incompleteness semantics. If you
  want the strict reading, it is one line in `rows_file_problems`, plus re-expressing the
  two missing-method tests.
- **D2. Undeclared `rows/*.json` files are invalid.** This goes slightly beyond the
  JSONL-only wording of R1c. All five retained rows directories contain only declared
  `.json` files (1,632, 1,632, 128, 128 and 12).
- **D3. The `not_verified` marker.** `verify` now writes `verification.json` twice. That
  is still the only file it writes.

## 4. Tests

Command (repository-relative paths, run inside each isolated tree):

```sh
PYTHONPATH=index-deconvolution:src <repo>/venv/bin/python -m pytest \
    index-deconvolution/hierarchy/tests tests/analysis/test_description_lengths_values.py \
    -q --tb=short -p no:cacheprovider
ruff check --output-format=concise index-deconvolution/hierarchy src/description_lengths.py \
    tests/analysis/test_description_lengths_values.py        # with the root ruff.toml
```

| run | result | log |
|---|---|---|
| baseline tree, original suite | **317 passed** | `logs/pytest.baseline.log` |
| patched tree, original + new | **331 passed** (317 + 14) | `logs/pytest.patched.log` |
| ruff, both trees and the closure files | all checks passed | `logs/ruff.*.log` |
| new `test_validation.py` against the **baseline code** | 13 failed, 27 passed | `logs/new_tests_against_baseline_code.log` |
| retained reproductions + inverted, baseline code | original 3 pass, inverted 3 fail | `logs/retained_edges_original_and_inverted.baseline.log` |
| retained reproductions + inverted, patched code | original 3 fail, inverted 3 pass | `logs/retained_edges_original_and_inverted.patched.log` |

The 14 new tests all use the existing tiny frozen run, which is benchmarked by the
production paths. Each one goes through the real `report` and `verify` commands where they
apply. They assert return codes, the newly written `verification.json` / `summary.json` /
`ledgers.json` / `claim_ledger.json`, the evidence gates (C1 `not_assessed`, C2
`not_supported`) and the absence of stale success. No new encoder or test-only
validation path was added.

| test | what it covers | on the baseline code |
|---|---|---|
| `test_valid_run_presents_every_archive_and_samples_without_gaps` | a valid, complete run still exits 0; no `unavailable` or `failed` entries | passes (regression guard) |
| `test_missing_archive_writes_invalid_records_and_replaces_a_stale_success` | **retained R1a, inverted**: exit 2 from report and verify; ledger entry `unavailable`; sample lists the missing archive; the older valid record is replaced | `FileNotFoundError` |
| `test_malformed_archive_claimed_by_its_row_is_invalid_everywhere` | **malformed-archive case**: truncated archive with a consistent row hash; `decoder raised ArchiveError`; ledger and sample report it | `AssertionError` in `ledger.py` from `report` |
| `test_corrupted_archive_bytes_are_invalid_and_never_presented` | garbage bytes at the row's path | `AssertionError` in `ledger.py` from `report` |
| `test_programmer_error_in_verify_propagates_and_leaves_no_stale_success` | a planted exception propagates; the record reads `not_verified` | old valid record left in place |
| `test_malformed_rows_file_is_invalid_before_it_is_keyed` ×6 | **identical duplicate (retained R1b, inverted)**, **conflicting duplicate**, not a list, non-object entry, undeclared method, foreign metadata | identical duplicate is **accepted as valid**; the other five were already exit 2, but only as generic "unreadable"/"differs" reasons |
| `test_undeclared_split_row_is_validated_not_filtered` | **retained R1c, inverted** | row filtered out (`KeyError: 'scope'` is reached first) |
| `test_undeclared_rows_file_is_invalid` | D2 | exit 0 |
| `test_a_split_subset_is_not_a_partial_acceptance` | a subset call is invalid, and the 32 transfer rows and 2 transfer files are listed | silently valid |

Old `report` also failed on malformed archives, through the `AssertionError` above,
before `verify` ran at all. Bitacora 37 did not list this second R1a failure mode. It is
closed by the same change.

## 5. The complete retained corpus, validated read-only

`corpus_harness.py` was run once per tree. The working directory and `PYTHONPATH` were
the tree, and `benchmark.RESULTS` pointed at the active
`index-deconvolution/results/hierarchy_v1`. **Encoding provenance** is the stored freeze,
`f970efff…`, which is recomputed and matched. **Validation code** is each tree's
`validation.py`/`cli.py`/`report.py`, and their hashes are recorded in each output. The
freeze source check runs as it is, and its result is reported. It is **not** overridden.

| | baseline code (= freeze) | patched code |
|---|---|---|
| production exit code | **0** (valid, complete, verdict `not_supported`) | **2**: exactly 3 invalid entries, `freeze: source changed since freeze:` cli.py, report.py, validation.py |
| other invalid entries | 0 | **0** |
| exit code if the sources matched (labelled reading) | 0 | 0 |
| rows expected / present / archives checked / distinct decoded | 26,112 / 26,112 / 26,112 / 16,402 | the same |
| rows files; duplicates; unknown; incomplete; censored | 1,632; 0; 0; 0; 0 | the same |
| separate-process sample | 360 / 360 decoded, all ok | the same |
| `ledgers.json` regenerated, byte-identical to stored | yes | yes |
| claim ledger regenerated from stored summary, equal | yes | yes |
| `SUMMARY_KEYS_CHECKED` equal to stored summary | 9 / 9 | 4 / 9 as gated (the freeze mismatch correctly makes primary, ablations and the three aggregates `not_assessed`); **9 / 9** with only the three named source entries removed |
| run directory before = after (18,062 files hashed) | `e566fa38…` = `e566fa38…` | the same |
| `validate_run` wall time | 77.6 s | 77.6 s |

Arithmetic is unchanged. With only the declared source entries removed, the patched code
recomputes the primary as **−0.0446156382 bits per input bit**, 95% interval
**[−0.0536775270, −0.0358242637]**, verdict `not_supported`. These are the same values as
the stored summary and bitacora 37 §2. The five ablation increments are also identical to
the stored values, and all are `supported` at 99%: `hid_flat` +0.2636,
`hid_no_arithmetic` +0.0392, `hid_fixed8` +0.0115, `hid_no_schema` +0.0090,
`hid_no_transform` +0.0019 bits per input bit.

Negative science still exits 0. The unchanged validator exits 0 on this negative
(`not_supported`) study. In the tiny fixture, the patched code exits 0 on a valid,
complete run whatever its verdict (`test_complete_valid_study_passes_whatever_its_verdict`
and the new regression guard). Under the patched code, the only route from the retained
corpus to exit 0 is the labelled reading. Production exit 0 would need a new freeze or
another provenance decision, and I do not claim it.

## 6. Remaining issues (not in scope, not fixed)

1. A malformed JSON **line** in `cases.jsonl`, or a malformed `summary.json`, still raises
   `JSONDecodeError` in `load_rows` / `cmd_verify`. Only the `not_verified` marker
   protects against a stale success in that case.
2. A row object that has **no `archive_path` key** still raises `KeyError` in the sample and
   ledger selection. The validator would report such a row, but the presentation layers
   index the key directly.
3. If an unrelated exception happens in `report` before the writes, the files from the
   previous `report` stay on disk. They are not mixed with new ones, but they are stale.
   `verify` detects a stale `summary.json` / `claim_ledger.json`, but it does not check
   `ledgers.json`.
4. The harness was run on confirm-v1-r1 only. confirm-v1 has its own, older freeze, which
   differs from both trees, and the supervisor's audit has already matched it byte for byte
   with r1.
5. `hierarchy/TESTS.md` and the test counts in the frozen docs (317) are not updated
   because they sit in the active frozen tree. After integration the inventory would be
   331 tests: `test_validation.py` goes from 26 to 40.
6. `verify --full` and `make ci-local` were not run. The isolated tree has no `tools/`
   guards.

## 7. Statement on frozen material

No active frozen file was edited. After all work, the 44 files copied at the start
(the `hierarchy/` package, the frozen `src` owners, the value test and the protocols)
were re-hashed in the active tree, and all are identical. All 22 frozen sources and
protocols still match `f970efff…`. The confirm-v1-r1 run directory hashes identically
before and after both harness runs: 18,062 files. confirm-v1, the old handoffs, the
source snapshots, bitacora entries and numerical outputs were not opened for writing.

One incidental write was found and reverted. Running the retained reproduction file
created a pytest bytecode cache, `confirm-v1-r1/__pycache__/` (born 13:20:04, after the
supervisor's files of 13:09–13:15). It was removed, and the directory again holds only
its six original entries plus `validator_closure/`. Nothing was committed, pushed or
reverted in git.
