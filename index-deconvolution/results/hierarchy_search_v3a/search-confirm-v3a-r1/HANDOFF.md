# Handoff: HID-search-v3a (search-confirm-v3a-r1)

**Ready for Codex review; not yet accepted.** Date: 2026-10-04. Executor: Claude Code.
Nothing was committed or pushed, and no remote service or recurring process was used.

## Identity

* Freeze: `05dd799d154e5e53a36bac7dca49f0438ca27b58b2df94c045eeca2fa6dd69e5` (`freeze.json`,
  `freeze.sha256`). The executable closure is in `source_snapshot.tar` (94 members:
  38 closure sources, 16 protocol files, 17 prefreeze evidence files, plus
  informational tests and docs). The freeze still validates with zero problems after
  the run, for purposes benchmark and report.
* Method configurations: `hid_full` `8a829b12…` (the search-v2 hash, unchanged);
  `hid_refine4` `177ac1f8…`.
* Baseline: accepted search-v2 `hid_full`, freeze `0f0a72ef…`; diagnosis report-r3
  `7b1590bb…`.

## Scope and primary verdict

The study tests one change only: boundary refinement over k = 4 ranked distinct coarse
seeds instead of k = 1, with stages L–G, grammar and caps unchanged. Both arms ran
independently on 256 fresh strings, alongside the nine baselines and the derived
portfolio.

**HARMFUL.** The estimate is −0.0063290600504822 bits per input bit, with 99%
percentile interval [−0.00833260223670385, −0.004177554260442437] (10,000 draws, seed
55001, NumPy linear quantiles, shared `report` bootstrap) [`DECISION.json`].

## Counts

* Target set: 6 cells, 120 of 120 paired units, 240 strings, 2,640 encoder jobs and
  2,880 rows. Controls: 4 cells, 8 units, 16 strings, 176 jobs and 192 rows.
* Total: 2,816 of 2,816 encoder jobs plus 256 derived portfolio rows, 3,072 rows.
  Every row is `ok`.
* Unavailable, censored or invalid records: none. HID raw fallbacks: 0. Baseline
  censoring: 0. Missing or `not_run`: 0. Failed or unavailable traces: 0; all 512 HID
  traces are complete and consistent with telemetry.
* Baseline constituents, in owner order: `raw, rle, gaps, period, bernoulli, context,
  zlib, lzma, pair_grammar`. All costs are full archive bytes × 8.
* Distinction kept: a HID raw fallback is a valid deployed cost under watchdog status;
  baseline censoring blocks only a portfolio conclusion. Neither occurred.

## Beneficial and harmful cases

Detail is in `REPORT.md` and `tables/`.

* **Harmful.** F12 at 4,096 and 16,384 bits: 26 and 25 of 40 strings worse, none
  better. S02 at 65,536 bits: 15 worse, none better. The largest single loss is
  `boundary_large-F12-16384-7018-base` (−0.0537 bits per input bit).
* **Beneficial.** S02 at 4,096 bits only: 18 strings better, 5 worse. The largest gain
  is `boundary_stress-S02-4096-8011-ragged` (0.1269).
* **Ties.** Both large F12 cells tie on every string.
* **Controls.** All 16 control strings are unchanged.
* **Portfolio (descriptive).** Both arms are longer than the best baseline:
  equal-cell −0.0398 (k = 1) and −0.0461 (k = 4).

## Development exposure and k = 1 reproduction

* Development used only inspected, retained search-v2 inputs. Reserved strings were
  generated once, after a validated freeze, by `V3aStudy.role_cases`, which re-validates
  the freeze before generation.
* Exposure inventory (`prefreeze/exposure_inventory.json`): reserved namespaces were
  mentioned only in protocol and source files, the old `NEXT_PROTOCOL_DRAFT.md` and its
  prose diff. No generated artifact mentioned them.
* **Compatibility.** 1,792 of 1,792 `hid_full` archives are byte-identical to the
  accepted run. There are 0 differences across the deterministic fields and the
  timing-stripped telemetry. The configuration dictionary and hash are equal
  (`development/compatibility.json`).
* **Treatment.** 208 of 208 terminal records; 176 of 176 paired target traces
  complete. Descriptive results: 28 better, 104 tied, 44 worse; no gate, no tuning
  (`development/development_summary.json`).
* **Supplied-cut coverage**, within 8 bits, pooled over the 176 development targets:
  * proposed: 720 of 880 for both arms;
  * returned: 287 of 880 (k = 1) and 259 of 880 (k = 4).

## Controlled code delta

The delta is `code_delta.diff` against `preservation/preedit_executable_snapshot.tar`;
the files are mapped in `IMPLEMENTATION_MAP.md`.

* **Changed owners**, all allowed: `segmentation.py`, `search_v2.py`, `study.py`,
  `benchmark.py`, `validation.py`, `freeze_v2.py`, plus the approved median patch to
  `diagnostics_v2.py` and `tests/test_study_v2.py`.
* **New files:** `search_v3a.py`, `report_v3a.py`, `tests/test_search_v3a.py`,
  `experiments/search_v3a/*`, `notebooks/build_20.py` and notebook 20.
* **Protected files and trees:** byte-identical.

## Telemetry meaning and cap distribution

* **Cap exits** are normal deterministic outcomes that return the best serialized
  complete archive.
* **B stop reasons**, of 256 strings per arm:

  | Arm | `no_strict_improvement` | `leaf_length_charge_cap` | `root_trial_cap` |
  |---|---:|---:|---:|
  | k = 1 | 248 | 0 | 8 |
  | k = 4 | 36 | 219 | 1 |

* **Commits:** 576 (k = 1) and 323 (k = 4).
* **Trace definitions:**
  * proposed: any request, including a request blocked by a cap;
  * evaluated: completed, including cache hits;
  * returned: cuts in B's final archive. These are never called coverage.

  Wall and RSS are instrumented.
* **Interpretation:** exhausting the length charge co-occurs with the loss; the design
  does not identify it as the cause.

## Discrepancies and deviations (all disclosed, none hidden)

1. **External concurrent change.** `notebooks/build_19.py` and notebook 19 (BDM
   workstream) changed at 07:22 local, during implementation. An untracked
   `notebooks/.ipynb_checkpoints/` also appeared. This phase did not write them and did
   not revert them. They lie outside the closure. The record is in
   `prefreeze/preflight.json` under `protected_changed_external_disclosed`, and in
   `preservation/final_preservation.json`.
2. **Post-development closure edit.** `experiments/search_v3a/prospective.py` changed
   after development, in its preflight function only: the allowed-failure set and the
   exposure classification. `prefreeze/dev_fingerprint_link.json` reconstructs the
   development fingerprint and shows it is the only closure difference. No worker,
   search, runner, validation or analysis code changed.
3. **Expected packet-check failures after the edit.** The pre-edit packet check passed
   22 of 22 (`ledger/preedit_packet_check.json`). After the edit,
   `source_hashes_unchanged`, `new_run_not_started` and `notebook20_unoccupied` are
   expected failures, and `protected_file_hashes_unchanged` fails because of item 1.
4. **Guard failure.** `check_single_engine` fails on pre-existing sites:
   `.kilo/worktrees`, the `imp-pathinfo` mirror, `protocols/description_lengths.py`
   and the Wolfram duplicates. None is in a file touched here; no new duplicate owner
   was added. `check_core_index` and `check_test_manifest` pass. `make ci-local` was
   not run. The alternative checks were the hierarchy and diagnosis suites, the
   description-length tests, ruff and the three guards. **Not all guards passed.**
5. **Notebook run1 failure.** The first guarded execution of notebook 20 (run1) failed
   on a formatting bug in the builder; it is retained under `notebook/`. Run2 passes
   every check, and its notebook-directory execution is the deliverable.
6. **Freeze closure probe.** `closure_not_loaded` in the freeze probe lists the
   `experiments` adapters and `src/description_lengths.py`, which are not imported by
   the package probe. They are hashed and archived in the snapshot.
7. **Execution mode.** The development and prospective queues each ran as one
   background invocation with checkpointed rows. There were no interruptions or
   resumes. The queue crossed role boundaries without a barrier, in frozen order.

## Tests and checks

* Hierarchy plus diagnosis suites: 334 passed (`ledger/pytest_full_prefreeze_a1.log`).
  This includes 30 new v3a tests, and 4 median-patch tests also passed separately.
  `tests/analysis/test_description_lengths_values.py`: 136 passed.
* ruff: clean before and after the freeze.
* `prospective verify`: exit 0, valid and complete, with the summary and decision
  recomputed equal.
* `search_v3a.audit`: pass, with 2,816 archives and 0 problems.
* Notebook guard: `notebook/run2.checks.json`, all checks true.

## Time

Controller spans, conservative, from `ledger/resource_events.jsonl`:

| Category | Used (s) | Cap (s) |
|---|---:|---:|
| development | 2,939.7 | 14,400 |
| prospective | 1,694.5 | 10,800 |
| report_verification | 698.0 when the totals were recorded (span still open for this handoff) | 3,600 |

* Total: 5,332.3 s of 28,800 s at the time of recording. The 600 s reserve is intact.
* Summed worker wall, reported separately: development 2,263.9 s + 505.4 s;
  prospective 2,981.9 s (`resource_totals.json`).

## Preservation

* Initial state (`preservation/initial_preservation.json`): 62 of 62 sources, 39 of 39
  protected files and 5 of 5 trees matched the packet.
* Final state:
  * the four result trees are unchanged;
  * the bitacora differs only by the new entry 45 (`preservation/bitacora_check.json`);
  * the protected-file differences are the external notebook-19 pair only;
  * the source differences are exactly the eight allowed owner edits.
* Integration equalities: 10 of 10. The `git status` difference is in
  `ledger/git_status_initial_to_final.diff`.

## Reproduce

Run from `index-deconvolution/`; the full command list is in `IMPLEMENTATION_MAP.md`:

```bash
export PYTHONPATH=experiments:.:../src
../venv/bin/python -B -m search_v3a.prospective verify
../venv/bin/python -B -m search_v3a.audit
../venv/bin/python -B experiments/search_v3a/notebook20.py run3   # optional re-execution
```

Artifacts: `REPORT.md`, `DECISION.json`, `DECISION.md`, `summary.json`,
`tables/{per_string.csv,per_unit.csv,per_cell.json}`, `rows/`, `archives/`,
`traces/`, `intended_jobs.json`, `corpus_manifest.*.jsonl`, `input_checks.json`,
`verification.json`, `arithmetic_audit.json`, `prefreeze/`, `preservation/`,
`ledger/`, `notebook/`, `resource_totals.json`, and `../development/`. Also
`notebooks/20_hierarchy_search_v3a.ipynb`, `bitacora/45_hierarchy_search_v3a.md` and
the README entry.

## What remains unidentified

The study does not show why k = 4 loses. The leading descriptive candidate is the
interaction with the shared length-charge cap, but it is not established. The study
makes no claim about other k, caps, families or the portfolio, and no claim of a final
causal method. The accepted search-v2 conclusion is unchanged. As specified, this
change does not merit adoption. Whether a cap-aware variant merits a separate protocol
is the supervisor's decision; nothing further was implemented.
