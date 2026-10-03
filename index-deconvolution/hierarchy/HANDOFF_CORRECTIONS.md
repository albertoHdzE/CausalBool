# HID-v1 corrections handoff — `confirm-v1` → `confirm-v1-r1`

Developer: Claude Code. Date: 2026-10-02. Responds to
`bitacora/35_hierarchy_v1_supervisor_review.md` under
`KICKOFF_hierarchy_v1_corrections.md`. **The supervising session has not reviewed or
approved this revision.** Passing tests and a reproduced negative result do not
constitute acceptance.

Paths are relative to `index-deconvolution/` unless rooted.

## 1. Outcome

| dimension | status |
|---|---|
| Engineering (`confirm-v1-r1`) | **valid** — `verify --full` exit 0: 26,112 / 26,112 declared rows, 0 invalid, 0 incomplete, 0 censored; 26,112 promised archives opened, hashed, measured and decoded against regenerated inputs (16,402 distinct); 360-archive separate-process sample all correct; `summary.json` and `claim_ledger.json` recomputed from rows and equal |
| Completeness | **complete** — confirmation 1,440 / 1,440 strings, transfer 192 / 192 |
| Old/new replay | **identical deterministic behaviour** — 26,112 / 26,112 rows equal in every deterministic field; archive manifests byte-identical; every endpoint identical; only wall time and RSS differ |
| Scientific verdict, primary endpoint | **not_supported** — gates passed; −0.04462 bits saved per input bit, 95 % CI [−0.05368, −0.03582] |
| Acceptance | **pending Codex review** |

The engineering status and the scientific verdict are independent: the study is a
complete, valid study with a negative primary result.

## 2. Runs, freezes, snapshot, amendment

| item | value |
|---|---|
| old run | `confirm-v1`, freeze sha256 `ba4bec0a19842deacc349c162ebd79a5634fc384fc6dc4c54040dba3ec78a3b4` (2026-10-02T15:06:52Z). Every file under `results/hierarchy_v1/confirm-v1/` unchanged (no file there is newer than the corrective kickoff). **Superseded; invalidated for approval of the corrected implementation**; its independently reproduced observations are retained |
| new run | **`confirm-v1-r1`**, freeze sha256 `f970efff16a2d08bf1dd22eee1386c164af5ba67b22137fefcf06cd182b27f5c` (2026-10-02T17:19:45Z), written before its corpus manifest or any row; `confirm-v1-r1` was unused |
| freeze diff | `source_sha256` (benchmark, cli, infer, report changed; `validation.py` added), `analysis_plan` (`evidence_gates` text and documented descriptive seeds added), SEARCH_SPEC informational hash, run id and time. **Equal**: search configs, restricted oracle config, baseline parameters, generator, seed formula, expected counts, methods, resource policy, environment |
| source snapshot | `results/hierarchy_v1_supervision/confirm-v1/source_snapshot_confirm-v1.tar`, sha256 `f5a3d3d7a35541171521415409562e8a35fd8166a36b354d4396e5ffe0333407`; manifest `source_snapshot_confirm-v1.sha256` (sha256 `3e237dd79fdcb3e5…`). 22 files from the original freeze's source/protocol/documentation maps plus `freeze.json` and `freeze.sha256`, under the non-importable prefix `confirm-v1-source/`; each verified against the original hashes on archiving and on re-read |
| original handoff | `hierarchy/HANDOFF_confirm-v1_original.md`, byte-identical (sha256 `144956d27bc9a54d…`); the active `HANDOFF.md` carries a supersession banner only |
| amendment record | `results/hierarchy_v1/AMENDMENT_confirm-v1-r1.md` |
| deviation log | `results/hierarchy_v1/confirm-v1-r1/DEVIATIONS.md` |
| bitacora | `bitacora/36_hierarchy_v1_corrections.md` (new); bitacora 34 untouched |

Exact amendment: correctness only (R1, R2, R5) and wording (R3, R4). No candidate
source, SearchConfig value, scoring rule, wire byte, corpus distribution, seed,
baseline, estimand or bootstrap seed changed.

The original evidence stays readable under its own code:
`zsh experiments/audit_confirm_v1_from_snapshot.sh` extracts the snapshot to a
temporary tree, verifies its manifest, and reruns the supervisor's audit against the
untouched run through a symlink. Exit 0; its output equals the stored `audit.json`.
No current-tree freeze validation is claimed for `confirm-v1`; `verify --run-id
confirm-v1` was **not** run, because it would rewrite that run's `verification.json`
and would report a freeze mismatch by design.

## 3. R1–R5 checklist

| item | done | changed files | regression tests | evidence |
|---|---|---|---|---|
| **R1** fail-closed validation and gated verdicts | ✓ | new `hierarchy/validation.py` (sole owner; `validate_study`, `validate_run`, `make_design`, `production_design`); `hierarchy/report.py` (design-built population, `population_gate`, `verdict(ci, gate)`, `aggregate` with partial diagnostics, corrected ledger); `hierarchy/cli.py` (`report` and `verify` through `validate_run`; report exit 0/2/3; verify recomputes summary and ledger); `hierarchy/benchmark.py` (`validation.py` frozen; `_Job.worker_argv`); `GOVERNANCE/CORE.md` owner row | `tests/test_validation.py` (26, real `report`/`verify` on a tiny frozen run), `tests/test_report.py` (9, explicit fixture designs) | `results/hierarchy_v1/confirm-v1-r1/verification.json`, `summary.json#validation` |
| **R2** semantic mismatch is an error | ✓ | `hierarchy/infer.py` (`CandidateExpansionMismatch` in `_Search.consider`) | `test_search.py::test_candidate_expansion_mismatch_raises_instead_of_rejecting`; `test_validation.py::test_worker_semantic_mismatch_becomes_an_invalid_error_row` (real worker subprocess with the fault injected; `error` rows, no archive, no fallback; validation invalid) | all 26,112 rows: `rejected_verify = 0`, statuses `ok` |
| **R3** claims match estimands | ✓ | ledger C4/C5 text and logic in `report.py`; `SEARCH_SPEC.md` §8; `notebooks/build_16.py` §9, §9b, closing; bitacora 36 | ledger gates tested in `test_report.py`, `test_validation.py` | `claim_ledger.json`, `report_tables.md` |
| **R4** development scope disclosed | ✓ | `SEARCH_SPEC.md` §7 deviation table; C4 caveat; notebook §9 and closing; amendment record; bitacora 36 | — (wording) | `SEARCH_SPEC.md` §7 |
| **R5** environment enforced | ✓ | `hierarchy/benchmark.py` (`ENVIRONMENT_REQUIRED`, `check_environment`, `environment_comparison`; `load_and_validate_freeze(purpose=…)`; benchmark/resume enforce), `cli.py` (diagnostics and report enforce; verify reports `verification_environment`, `environment_differences`, `environment_problems_by_purpose`, never writes the freeze) | `test_benchmark.py::test_environment_check_…`; `test_validation.py::test_benchmark_resume_refuses_…`, `::test_report_and_diagnostics_refuse_and_verify_reports_…` (mocked environment; nothing installed) | `verification.json#environment_differences` = {} |

R1 regression coverage required by the kickoff, each through real `report` + `verify`
exit states unless noted: one F04 pair out of the declared design (exit 3,
`not_assessed`, missing units listed); a whole unit, a whole cell, one ragged member,
`not_run` rows (exit 3); a whole ablation method (components `not_assessed`, primary
still assessed); a whole baseline method (incomplete, and the `ok` portfolio
unverifiable → exit 2); duplicate key (exit 2, neither copy kept); unknown method;
negative or positive interval with a censored baseline → `inconclusive`, exit 0
(`test_report.py` for both signs; integration for the real data); positive and
negative interval with invalid engineering → `not_assessed` (`test_report.py` both
signs; integration with an `error` row); null archive on an `ok` row; wrong archive
hash, length, codec, `decode_ok`; an archive of another input; wrong input hash;
wrong portfolio label despite equal size; rows file disagreeing with `cases.jsonl`;
stale `summary.json`; complete valid study → exit 0 whatever its verdict; empty
design or population never complete; `report` and `verify` share `validate_run`.

Monolithic-code gate: Q1 — no single owner of study validation existed (it was split
across `cli._engineering`, the body of `cmd_verify` and `report.summarise`). Q2 — the
only other copy is the supervisor's deliberately independent audit script, left as
such. Q3 — the scattered fragments were replaced, not duplicated: `_engineering` and
the verify loop are gone. Q4 — `GOVERNANCE/CORE.md` owner row; test
`test_report_and_verify_share_one_validation_path`.

## 4. Case / method / archive audit and old/new equality

`confirm-v1-r1` (`verification.json`, 2026-10-02T18:19:36Z–18:22:03Z):

| check | result |
|---|---|
| declared rows / present / duplicates / unknown | 26,112 / 26,112 / 0 / 0 |
| exact case × method membership; metadata (split, family, length, replicate, ragged, n_bits); run id; freeze hash; config hash per method | all equal to the design and freeze |
| regenerated corpus vs stored manifests (both splits) | equal |
| rows/*.json vs cases.jsonl | equal for all 1,632 cases |
| archives promised by status / opened, hash, size, codec, decode = regenerated input | 26,112 / 26,112 (16,402 distinct) |
| portfolio: all constituents ok, deterministic minimum (length, codec, bytes), identity of path/hash/bits/codec with the selected constituent | 1,632 / 1,632 |
| HID archive ≤ literal archive | all HID rows |
| separate-process decoder, one archive per split × family × method × status | 360 / 360 |
| censored / not_run / error rows | 0 / 0 / 0 |

Old/new (`results/hierarchy_v1_corrections/compare_confirm-v1_vs_confirm-v1-r1.json`,
script `experiments/compare_hierarchy_runs.py`): 26,112 case × method pairs compared,
0 absent, **0 differences** over status, archive sha256/bits/path, raw bits, decode,
codec, selected method, rule count, depth, candidate count, work units, stop reason,
search counters, best source, trace, input hash, n_bits, config hash and exception
type; no unclassified field; `archives_manifest.sha256` byte-identical between the runs;
every endpoint block of `summary.json` identical. Diagnostics: observed and null score
matrices, adaptive p-values and Holm corrections identical; only `wall_s` and
`freeze_sha256` differ. Allowed to differ, and did: total encode time 5,486 s → 5,380 s,
max encode 9.96 s → 9.34 s, max worker RSS 315.5 → 314.8 MiB; budget 3,325 s → 3,266 s.

Corrected report on the retained `confirm-v1` rows
(`experiments/replay_corrected_report_on_confirm_v1.py` →
`results/hierarchy_v1_corrections/original_rows_under_corrected_report.json`): the
corrected validation passes those rows (valid, complete, 26,112 archives), and the
primary, five ablation, transfer and all-12 estimates and intervals differ from the
supervisor's `audit.json` by at most 5.6×10⁻¹⁷ (tolerance 10⁻¹²); controls and all 60
family/size cells equal the original summary exactly.

## 5. Estimates, intervals and the corrected claim ledger

All from `results/hierarchy_v1/confirm-v1-r1/summary.json` via `hierarchy.present`
(`report_tables.md`). Unit: bits saved per input bit, (portfolio − HID) / n.

| quantity | estimate | interval | population, seed |
|---|---:|---|---|
| **primary**, portfolio − full | −0.04462 | 95 % [−0.05368, −0.03582] | structured confirmation, 21 cells / 420 units / 840 strings, 33001 |
| no_schema − full | +0.00896 | 99 % [+0.00595, +0.01211] | same, joint, 33002 |
| no_arithmetic − full | +0.03923 | 99 % [+0.03353, +0.04514] | same |
| no_transform − full | +0.00188 | 99 % [+0.00148, +0.00227] | same |
| flat − full | +0.26360 | 99 % [+0.24348, +0.28251] | same |
| fixed8 − full | +0.01152 | 99 % [+0.00670, +0.01668] | same |
| transfer, structured (descriptive) | −0.06280 | 95 % [−0.07690, −0.04853] | 16,384 and 65,536 bits, 4 units per cell, 33005 |
| controls F07–F09 vs portfolio (descriptive) | −0.26335 | 95 % [−0.28105, −0.24511] | confirmation, 33006 |
| all twelve families (descriptive, **not** the primary population) | −0.10226 | 95 % [−0.10922, −0.09531] | confirmation, 43001 (the supervisor's seed) |

Per-string, primary population: HID better on 208, tied 91, worse 541; mean −77.6, median
−48.0 bits. Transfer, descriptive per cell: F04 positive at 16,384 (+0.04602) and 65,536
(+0.01155); F05 positive at both (+0.00305, +0.00218); every other structured cell
negative. Controls against min(Bernoulli, context) alone (descriptive, unweighted string
means): F07 +0.01798, HID shorter on 117 / 120 (3 tied); F08 −0.44668, longer on 120 / 120;
F09 −0.34338, longer on 118 / 120 (2 tied). BDM diagnostic: unchanged, C6 inconclusive
(F04 not separated after Holm).

Claim ledger (`claim_ledger.json`; every decision recorded with its evidence gate, all
gates passed):

| id | status | claim (as now worded) | estimate | uncertainty |
|---|---|---|---|---|
| C1 | not_supported | HID-v1 (full) yields an average code-length gain over the strong decodable baseline portfolio on the prespecified structured confirmation benchmark | −0.04462 | [−0.05368, −0.03582] |
| C2 | supported | Every stored archive decodes exactly to its input with the independent decoder | 26,112 archives | — |
| C3.1–C3.5 | supported | The component removed in each arm contributes a code-length advantage to the full search (caveat: configured algorithm under the frozen budget, not a language-intrinsic contribution) | see above | 99 % |
| C4 | not_supported | At 16,384 and 65,536 bits HID-v1 (full) has a positive equal-weight mean saving over the nine-code portfolio on the structured families (descriptive; reserved seeds and held-out families unused before the freeze, 65,536-bit length exercised in development) | −0.06280 | [−0.07690, −0.04853] |
| C5 | not_supported | On the statistical controls F07–F09 HID-v1 (full) has a positive equal-weight aggregate saving over the nine-code portfolio (descriptive; not a per-family statement, not equivalence) | −0.26335 | [−0.28105, −0.24511] |
| C6 | inconclusive | BDM separates the structured diagnostic objects from bit shuffles | see file | 199 nulls |
| C7–C10 | out_of_scope | K, unique mechanism, prediction, causal identification | — | — |

Changes against the `confirm-v1` ledger: C4 reworded (status unchanged); **C5 reworded,
status supported → not_supported**, because the old text asserted "no advantage over
the statistical baselines" while the metric was the portfolio aggregate, and its
`supported` meant "the interval is not above zero"; the new claim is a superiority
claim tested on its actual estimand. C1, C2, C3, C6 unchanged in status.

Scope of the losses: the result is the best archive found under the frozen budget.
Wire overhead, proposal coverage, caps (confirmation: 44 / 1,440 full searches at the
candidate cap; transfer: 50 / 192 at the work cap and 21 at the candidate cap) and
search quality are not separated by this design. The supervisor's F12 witness (22,480
bits in the unchanged language vs 28,528 found, portfolio 23,240) is post hoc,
metadata-assisted and outside every result; notebook 16 §9b prints it with that label.

## 6. Environment verification

Frozen and current environments are equal on every field (`verification.json`:
`environment_differences` = {}): CPython 3.13.12 (Clang 17.0.0), zlib 1.2.12 (compile
and runtime), liblzma probe `sha256:0040f94d…`, numpy 2.4.3, pybdm 0.1.0; informational
Apple M3 Ultra, 28 cores, macOS 27.0.1 arm64. Required fields per purpose: benchmark
and resume — python, implementation, zlib ×2, liblzma; diagnostics — python,
implementation, numpy, pybdm; report — python, implementation, numpy. Hardware,
platform, matplotlib and pytest are informational. A field the freeze lacks or records
as null is a mismatch.

## 7. Commands and exit codes

Repository root, `export PYTHONPATH=index-deconvolution:src`, `venv/bin/python`.

| command | exit | note |
|---|---:|---|
| supervisor audit, original tree, output redirected to a temp dir (before any edit) | 0 | equal to stored `audit.json` |
| snapshot creation + verification (inline script) | 0 | 24 files |
| `python -m pytest index-deconvolution/hierarchy/tests tests/analysis/test_description_lengths_values.py -q` | 0 | **317 passed** (285 original + 32 new) |
| `ruff check --output-format=concise index-deconvolution/hierarchy …` | 0 | all checks passed |
| `python -m pytest tests/analysis -q` (`PYTHONPATH=src`) | 0 | 265 passed |
| `python -m hierarchy.cli selfcheck` | 0 | |
| `python experiments/replay_corrected_report_on_confirm_v1.py` | 0 | ≤ 5.6×10⁻¹⁷ |
| `python -m hierarchy.cli freeze --run-id confirm-v1-r1` | 0 | |
| `benchmark --split confirmation --resume --quiet` | 0 | first chain launch failed in argparse before touching the run (`DEVIATIONS.md`) |
| `benchmark --split transfer --resume --quiet` | 0 | |
| `diagnostics --run-id confirm-v1-r1` | 0 | |
| `report --run-id confirm-v1-r1` | 0 | valid, complete, not_supported |
| `python -m hierarchy.present --run-id confirm-v1-r1` | 0 | |
| `python experiments/compare_hierarchy_runs.py confirm-v1 confirm-v1-r1` | 0 | identical |
| `python notebooks/build_16.py` + `jupyter nbconvert --execute --inplace` | 0 | 17 code cells, 0 errors |
| `zsh experiments/audit_confirm_v1_from_snapshot.sh` | 0 | original evidence under original sources |
| `verify --run-id confirm-v1-r1 --full` | **0** | includes pytest 317, ruff, check_core_index 71/71, check_test_manifest (28/28), notebooks 15 and 16 |
| `zsh tools/check_core_index.sh` | 0 | 71/71 |
| `zsh tools/check_test_manifest.sh` | 0 | root manifest unchanged; package tests are outside the root tree |
| `zsh tools/check_single_engine.sh` | 1 | **pre-existing**: all nine failing checks name files under `.kilo/worktrees/held-saguaro/`; none names a file of this stage |

Not run: `make ci-local` (no push is planned) and `verify --run-id confirm-v1` (see §2).

## 8. No tuning, no new metadata use

No scientific parameter was changed, and no result was used to choose one: the freeze
diff in §2 shows search configs, baselines, generator, seeds, counts, methods and
resource policy equal; the replay's archives are byte-identical. The supervisor's
witness and its construction boundaries were not used as an inference input, a tuning
target or a benchmark number; they appear only, labelled, in notebook §9b, the SEARCH_SPEC
§8 discussion and bitacora 36. No statistical leaf, entropy coding, segmentation method
or sweep was added. Nothing was committed, pushed, deleted or reverted; the original
protocol and annexes are unchanged; unrelated worktree changes were left alone.

## 9. Remaining issues

1. **Not an independent test.** `confirm-v1-r1` reuses the strings, seeds and families
   whose results were seen in `confirm-v1`. Its identity with `confirm-v1` checks the
   correctness amendment; it adds no new evidence about the hypothesis.
2. **Search versus language is unresolved.** The design cannot apportion losses between
   representation, proposal coverage, caps and search; one post-hoc witness shows the
   search gap is real on at least one input. The two-gap study proposed in bitacora 35 §7
   would be exploratory on inspected families and then need newly reserved seeds.
3. **Transfer length.** 65,536 bits was exercised in development; this cannot be undone
   by a rerun. Transfer stays descriptive.
4. **Untested paths in production data.** No timeout, RSS breach, censored baseline,
   `not_run` or error row occurred in either run, so those paths are exercised by tests
   only.
5. **Guard noise.** `check_single_engine.sh` stays red until the `.kilo` worktree is
   removed or excluded; that worktree is not part of this stage and was not touched.
6. **CLI docstring.** `hierarchy/cli.py`'s module docstring still lists `confirm-v1`
   in its example commands; it is a frozen source, so it was left as frozen rather than
   edited after the freeze. `README.md` gives the current commands.
7. **Supervisor scripts.** `experiments/review_hierarchy_confirm_v1.py` validates the
   current tree against the original hashes and now fails by design on the current
   tree; run it through `experiments/audit_confirm_v1_from_snapshot.sh`.
   `review_hierarchy_failure_modes.py` reproduces bugs of the original code; on the
   corrected tree its `report.verdict` and `summarise` calls no longer match the new
   signatures, which is expected and not a desired behaviour to restore.

---
Ready for supervisor review. Not accepted.
