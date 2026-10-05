# search-diagnosis-v1-r1 — handoff for Codex review (corrected copy, `report-r2`)

> **Corrected copy.** The original `search-diagnosis-v1-r1/HANDOFF.md` is kept unchanged as
> a historical artifact. Only the interpretive statements answering Codex review R1–R2
> and the scope statement are corrected here; operational content (identity, resources,
> tests, commands) is the a1 record as delivered. The closure of the review is
> `review_closure/search-diagnosis-v1-r1/HANDOFF.md`.

Date: 2026-10-03. Executor: Claude Code. Git HEAD `53c41d8f3b97106fd176f24d575e0934848dddd6`
(branch `main`), dirty tree with unrelated pre-existing edits preserved.
**Status: ready for Codex review; not yet accepted.** Nothing committed, pushed or published.

## 1. Outcome

* **Completion:** complete. D1 1,792/1,792 cases, 28,672 rows; D2 416/416 jobs; D3 176/176
  jobs (5,632 subsets); D4 576/576 jobs, 1,152/1,152 admissible conversion records.
  No timeout, RSS breach, error, decode failure, graph-limit rejection or `not_run` record.
* **Validity:** all gates pass — B0 deterministic mismatches 0/208; supplied references
  reproduced 176/176; H − C identity failures 0/1,152; D1 problems 0; accepted primary
  estimate reproduced exactly (`0.005605234982532739`, 21 cells), labelled as a
  preservation check.
* **Flags** (`analysis/flags.json`):

  | flag | value | prevalence / effect |
  |---|---|---|
  | `budget_opportunity_observed` | true | 1/176 targets (`stress-S02-4096-4001-ragged`: B8 2,352 vs H 2,392 bits, n = 4,099); 0/32 controls change; equal-cell mean opportunity 7.62e-5 bits/input bit |
  | `restricted_path_barrier_observed` | true | 22/176 strings, all positive-cost steps, 0 equality barriers; 0 eligibility obstructions |
  | `missed_baseline_structure_observed` | false | 0/576 period, 0/576 pair-grammar translations shorter than H |
  | `proposal_representation_penalty_observed` | true | 576/576 and 576/576 translations longer than their own baseline; T − C median 96 bits (period), 472 bits (pair grammar) |

* **Recommendation:** `BOTH_SEPARATELY`, exploratory (corrected `DECISION.md`,
  `report-r2/outputs/DECISION.json`), with **no superiority claim**. Boundary families: in
  all 72 strings where the full arm loses to the portfolio, a supplied-cut partition in
  the unchanged leaf language is shorter than both; the B0→B8 cap increase changed one
  target output; these data do not rank proposal, accepted path, refinement and leaf
  construction as causes. Period-type families: of 367 losses to a translated winner, 282
  have H = T in length (261 byte-identical, 21 different bytes), so there H − C = T − C,
  the translation's measured penalty; this is not an optimality or impossibility result.
  Two separate single-change drafts are in the corrected `NEXT_PROTOCOL_DRAFT.md`; neither
  is approved; no seeds generated, no source version implemented.

## 2. Implementation identity

* Identity SHA-256 `518ebc137118643bf564c76f8e597c15565a95411fe9a946a539cc05e7044a9e`
  (`identity/identity.json`): adapters, all 25 `hierarchy/*.py` owners, the four packet
  files, B0/B8 configurations, limits, and design SHA-256 `cdc07bf5…70ce`.
* Input manifest `identity/input_manifest.jsonl` (1,792 rows: input hash, length, raw /
  hid_full / period / pair_grammar / baseline_best archive hashes), SHA-256 `e434253e…babdc`.
  Bits always come from decoding the retained raw archive, checked against the row hash.
* Executable closure `identity/executable_closure.tar` (41 members, deterministic),
  SHA-256 `afe79179…090a`; environment `identity/environment.json`.
* Delegation manifest verified before any work: 39/39 hashes match (packet, references,
  28 scientific owners).
* Job-executing adapter hashes, unchanged since launch: `common.py c0356e6f…`,
  `kernels.py aad3099d…`, `runner.py 07fa5e3f…`, `worker.py 16405c3a…`, `__init__.py 08b1243c…`.
  Reporting-only adapters revised after the jobs (see deviation D1): `analysis.py`
  `e173e899… → 20c15557…`, `cli.py 0614c4a1… → ad0669b2…`, new `report.py c52affcc…`.
* Imported owners unchanged: the active `hierarchy/` package, the scientific freeze and
  the R1 patch (still unapplied) are untouched (§6).

## 3. Expected versus actual

| section | expected | actual | unavailable / invalid |
|---|--:|--:|---|
| D1 cases / rows | 1,792 / 28,672 | 1,792 / 28,672 | none |
| D2 jobs (176 + 32 strings × B0, B8) | 416 | 416 ok | none |
| D3 jobs / subsets | 176 / ≤ 5,632 | 176 ok / 5,632 (every list had exactly 5 cuts) | none |
| D4 jobs / conversion records | 576 / 1,152 | 576 ok / 1,152 admissible | none |

Attempt `a1` only (`attempts.jsonl`): D2 22:12:14–22:13:11Z, D3 22:13:11–22:13:18Z,
D4 22:13:18–22:13:32Z (UTC), case-ID order, two workers, 30 s / 1 GiB each. Maximum
worker wall 2.28 s, maximum peak RSS 65.7 MiB (`analysis/resources.json`).

## 4. Time charges (`../execution_ledger.jsonl`, new ledger; the accepted study's untouched)

| category | allowance | charged |
|---|--:|--:|
| fixtures_development | 1,800 s | 599.9 s |
| diagnostic_jobs | 10,800 s | 82.3 s (D1 map plus D2–D4 runner wall) |
| report_verification | 1,800 s | 965.2 s |
| total | 14,400 s | 1,647.4 s |

Development and report time are wall-clock spans charged explicitly; the report charge
spans identity → handoff minus job charges, so it conservatively overlaps analysis
coding. A final short charge for writing this file follows it in the ledger.

## 5. Tests, lint, guards

* Focused tests `experiments/search_diagnosis/tests`: **27 passed** (pre-launch and final;
  `verification/pytest_prelaunch.log`, `pytest_final.log`). Hand-derived byte fixtures for
  period (ragged tail, exact, literal, p = 300 off-grid) and pair grammar (sharing, start
  order, unused terminal, depth-66 graph-limit rejection); exact ledger sums and the
  H − C identity; subset order and reference reproduction; D3 reachability on hand
  spaces including a tie barrier, a positive step and an eligibility obstruction;
  weighting; real-process timeout, RSS watchdog (exit 86), worker error, parameter
  refusal, resume skip/identity refusal, and `not_run` on an exhausted budget.
* Mutation probe (isolated `/tmp` copy): strict edge `< 0 → <= 0` and swapped pair
  children → 3 failures (`verification/mutation_probe.txt`).
* Owner suite unchanged owners: `hierarchy/tests` + shared owner file **385 passed**
  (`verification/pytest_owner_suite.log`).
* Ruff: all new Python files clean (`verification/ruff_final.log`).
* Guards (`verification/guards/`): `check_test_manifest`, `check_core_index`,
  `check_glossary_sync`, `check_glossary_conformance` pass. `check_single_engine` fails
  with the **pre-existing** 9 FAIL lines (`.kilo/worktrees/*` copies and existing Wolfram
  sites); 0 lines involve any file of this phase.
* `make ci-local` not run: the documented dirty-tree exception still holds (it rewrites
  tracked `results/tests/*` already modified by other work and does not exercise this
  Python code); the owner suite, focused tests, guards and preservation are the relevant
  alternatives.
* Notebook 18: built by `notebooks/build_18.py`, executed under the accepted
  artifact-only guard (reused `run` from `review_closure/scripts/execute_notebook_artifact_only.py`)
  from the notebook directory and the repository root: 12 code cells, exit 0, no errors,
  no unexecuted cells, no guard refusals, only allowlisted `hierarchy` modules, no
  inference/generation/job tokens, saved values displayed, identical text outputs across
  directories (`verification/notebook_execution_checks.json`, all checks pass). It
  re-decodes the 32 archives of the drawn D3 string and re-hashes/re-buckets all 1,152
  translated archives.

## 6. Preservation (`preservation/`)

Before-record taken after creating only new files under the owned paths; after-record
at the end. Four trees (`hierarchy_v1/confirm-v1`, `confirm-v1-r1`, the entire accepted
`hierarchy_search_v2` results tree, all old `protocols/`) and 60 files (all non-bytecode
`hierarchy/` files incl. tests and protocols, the 28 delegation owners, notebooks 16/17,
their builders, `_nblib.py`, notebook README, packet files): **0 unexpected differences**;
one allowed change, the appended README row for notebook 18. Git status before/after in
`git_status_before.txt` / `git_status_after.txt`.

## 7. Exact commands (from `index-deconvolution/`)

```sh
P="PYTHONPATH=experiments:.:../src"
env $P ../venv/bin/python -m pytest experiments/search_diagnosis/tests -q --tb=short -p no:cacheprovider
env $P ../venv/bin/python -m search_diagnosis.cli identity
env $P ../venv/bin/python -m search_diagnosis.cli d1
env $P ../venv/bin/python -m search_diagnosis.cli run --section D2 --quiet   # then D3, D4
env $P ../venv/bin/python -m search_diagnosis.cli analyse
(cd notebooks && ../../venv/bin/python build_18.py)
../venv/bin/python results/hierarchy_search_diagnosis/search-diagnosis-v1-r1/verification/execute_notebook_18.py
env $P ../venv/bin/python -m search_diagnosis.cli preserve-after
PYTHONPATH=.:../src ../venv/bin/python -m pytest hierarchy/tests ../tests/analysis/test_description_lengths_values.py -q --tb=no
```

`search_diagnosis` is imported with `experiments/` on the path because the name
`experiments` resolves to the root `src/experiments` package.

## 8. File inventory

New code: `experiments/search_diagnosis/{__init__,common,kernels,worker,runner,analysis,report,cli}.py`,
`experiments/search_diagnosis/tests/{test_kernels,test_d3_graph,test_runner}.py`;
`notebooks/build_18.py`, `notebooks/18_hierarchy_search_diagnosis.ipynb`;
`bitacora/42_hierarchy_search_diagnosis.md`; one row appended to `notebooks/README.md`.

Run directory (`results/hierarchy_search_diagnosis/search-diagnosis-v1-r1/`, 52 MB):
`identity/` (6), `d1/` (3), `jobs/` (1,168 records), `archives/` (6,943 content-addressed
archives), `analysis/` (8: d2/d3/d4 rows and summaries, flags, resources, key numbers),
`preservation/` (5), `verification/` (13 incl. guard logs and the notebook driver),
`attempts.jsonl`, `DECISION.json`, `REPORT.md`, `DECISION.md`, `NEXT_PROTOCOL_DRAFT.md`,
this file; phase ledger `../execution_ledger.jsonl`.

## 9. What was learned and what was not

Learned (post hoc, these populations): the B0→B8 cap increase changed one target output;
the supplied-cut space contains same-language partitions shorter than the full archive
and the portfolio in every losing boundary-family string, mostly strictly reachable over
supplied cuts; in period-type cells the saved full archive usually has exactly the
translated length (mostly the same bytes, 21 exceptions among the losses), so the loss
equals that translation's measured penalty, whose per-bit size shrinks with n. Not
learned: why B stops (returned cuts cannot separate proposal from rejection, path,
refinement or leaves); whether shorter HID descriptions of the period strings exist; the
85 losses with H < T; the cause of the F06–F11 losses (where the largest per-bit losses
are); anything about new draws or unfamiliar families.

## 10. Deviations and items needing review

* **D1 Reporting adapters revised after launch.** `analysis.py` and `cli.py` were
  extended (flags, decision record, preservation allowance) and `report.py` added after
  the D2–D4 jobs ran. No job was re-run and no job-executing adapter or owner changed;
  `cli analyse` verifies this before reading records and writes
  `identity/reporting_revisions.json`. The launched bytes are in the closure tar. The
  attempt id stays `a1`; please confirm this is acceptable rather than a new attempt.
* **D2 Decision rule is post hoc.** The rule in `DECISION.json` was written after the
  measurements, as the protocol's evidence role implies; it is stated so its counts can
  be checked.
* **D3 "Ten protected owners"** are not enumerated in the packet; the preservation record
  covers a superset (60 files plus four trees).
* **D4 Preservation incident, repaired.** Loading the accepted notebook-guard harness
  wrote `review_closure/scripts/__pycache__/execute_notebook_artifact_only.cpython-313.pyc`
  into the accepted tree. The after-check caught it; I removed that directory (created by
  this phase, absent before), made the driver set `sys.dont_write_bytecode`, and re-ran
  the checks: clean.
* **D5 Intermittent notebook difference.** One of five guarded executions reported a text
  difference in code cell 9 (the D4 re-hash cell) between the two working directories
  before detail capture existed; four later executions with capture were identical and
  the delivered notebook comes from a passing run. Cause unidentified (possibly a kernel
  stream message).
* **D6 Reuse of private owner names.** The runner subclasses `hierarchy.benchmark._Job`
  (overriding only `worker_argv`) and the worker uses `_rss_watch`; the budget uses
  `CategoryBudget` through a two-attribute shim. No production global is monkeypatched.
  The closure tar reuses `build_tar` from a private module instance with its own prefix.
* **D7 D3 graph-limited subsets** would be treated as non-states; none occurred.
* **D8 Bucket mapping.** `field_buckets` files the period codec's first-period bits under
  `other_payload`, so bucket-level T − C differences move bits between
  `literal_payload_bits` and `other_payload`; totals are exact.
* **D9 F06–F11 scope (corrected).** F06, F07 and F11 were sampled as D2 controls at
  4,096 and 65,536 bits; none was a D3 or D4 target; F08–F10 appear only in D1. No
  diagnostic targeted their losses.

**Ready for Codex review; not yet accepted.**
