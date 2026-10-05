# HANDOFF — HID multilevel v1 feasibility (`multilevel-feasibility-v1-r1`)

**Status: ready for Codex review; not yet accepted.**

Executor: Claude Code, 2026-10-04. Supervisor: Codex. Protocol:
`PROTOCOL_hierarchy_multilevel_v1.md` with `protocols/hierarchy_multilevel_v1/`.
Nothing was committed, pushed, published or scheduled.

## 1. Result in one paragraph

Engineering verdict **VALID_COMPLETE**; conditional exploratory label
**NO_RETAINED_GAIN**. On the 96 exposed strings, no proposal of any arm (A1 width 8;
A2 eight widths; A3 eight widths × four levels) produced a complete archive shorter than
the saved k = 1 archive (A0). All 288 composites are byte-identical to their A0, so every
composite contrast against A0 is exactly 0 (0 better / 96 ties / 0 worse strings; 0/24/0
cells), and each composite's standing against the references is A0's own: +0.351713
bits per input bit against `pair_grammar` (87/0/9 strings) and −0.045188 against the
nine-method portfolio (21/12/63 strings). Across 4,244 evaluated A3 views, 9,576
serialized proposals and 7,780 independent decodes, the closest any view came was a
byte-identical rediscovery of A0 (F05, period 32: G0 = REPEAT of one 32-bit word, a
duplicate) and one equal-length tie on its ragged twin (A0 kept by the tie rule); the
median, over strings, of the best view's relative excess over A0 is 0.525 (min 0.0,
max 24.27). This is a complete negative result for this vocabulary on exposed data. It
is not evidence that multilevel structure is absent, and it carries no fractal or causal
reading.

## 2. Identity

| item | value |
|---|---|
| implementation lock | `implementation_lock.json`, sha256 `4d1908ab4ec81334bb626bbe025d8dce134e8b4d9df124ce2fba84be8bbcf003` |
| lock written | 2026-10-04T22:45:44Z; git HEAD `53c41d8f` (unchanged; nothing committed) |
| source snapshot | `source_snapshot.tar`, sha256 `641dbe716c99726ce4dabf3f1151ec7e4527c71c5186dc8166b0ae308869a169`, 74 members (63 executable in the checked closure) |
| import probe | every reused module resolved inside `index-deconvolution/` (`-S` child, no site `.pth`) |
| A0 config | `hid_full`, registry `search-v2`, sha256 `8a829b12…3128159` (contract value) |
| arm configs | A1 `22450a0f…`, A2 `66a2d968…`, A3 `df7e462f…` (full hashes in the lock) |
| lock re-checked | by every worker (63 files + import locations) and by `cli verify` (clean) |

## 3. Counts and statuses

| item | intended | available | notes |
|---|---:|---:|---|
| strings | 96 | 96 | decoded from retained raw archives; hash and length checked |
| A0 jobs (new) | 96 | 96 | 96/96 reproduce every contract field (`baseline_gate.json`) |
| augmentation jobs (new) | 288 | 288 | all `ok`, all `search_complete`; 0 watchdog, 0 invalid, 0 unavailable |
| new encoder jobs | 384 | 384 | |
| derived composite records | 288 | 288 | not counted as jobs |
| imported constituent records | 864 | 864 | 0 hash/decode problems |
| derived portfolio references | 96 | 96 | 96/96 equal the saved `baseline_best`, ties by owner rule |
| traces | 288 | 288 | hashes re-checked by `verify` |
| A3 view records | 6,144 | 6,144 | 4,244 evaluated, 1,840 saturated-branch, 60 single-symbol-branch, 0 ineligible, 0 cap |
| A2 / A1 view records | 1,536 / 192 | all evaluated | |
| selected augmentation archives | — | 0 | `explanations.jsonl` is therefore empty |

Proposal outcomes (A3): G0 4,224 new + 20 duplicate; G1 2,516 new + 1,728 duplicate;
G2 868 new, 48 duplicate, 2,216 patch-limit rejections, 1,112 no gap template;
G3 172 new, 2,017 patch-limit rejections, 2,055 no gap template; 0 graph rejections;
13,809 requests; 0 strict improvements. A1 and A2 totals are in `summary.json`. Work
caps (64 views, 256 requests) never bound, as designed (64 × 4 = 256).

Nested ablation check on the study rows: A2 views equal A3's level-1 views and A1 views
equal A2's width-8 views on 96/96 strings (view-intrinsic fields), in addition to the
fixture-level equality of restricted configurations.

## 4. Evidence status and recommendation

* Evidence state: VALID_COMPLETE (no INVALID, no INCOMPLETE item).
* Label: NO_RETAINED_GAIN (A3 < A0 on 0 strings; A3 < A2 on 0; A2 < A0 on 0).
  Exploratory guidance only; not statistical superiority, generalization, causality or
  adoption.
* **Beneficial contrasts:** none against A0, A1 or A2 (all exactly 0).
* **Harmful contrasts:** none against A0 (non-regression is an engineering invariant of
  the construction, not a finding). Against the portfolio, the composites inherit A0's
  deficit of −0.045188 (63 worse strings, 16 worse cells).
* **Reading of the map** (`tables/gap_map_A3.csv`, notebook 21 §4). Short words repeat:
  width 4, level 1 has median k/m 0.016 and median weak support 0.001, yet its best view
  is still a median 0.67 bits per input bit longer than A0. Wider words and higher levels
  saturate (k = m) quickly: at width 64, level 4 only 22 of 192 view instances remain
  evaluable. Deeper cells summarise survivor subsets, so their medians are not
  comparable to level 1 without their denominators. Spacing irregularity is visible in
  the 4,233 patch-limit rejections of G2/G3 (more than 64 flips from a one-symbol-period
  template). In every evaluated view the failure is a description gap (paid dictionary
  and structure exceed A0), never an absence of admissible candidates (0 views).
* **Saturated dictionaries keep structure the support proxy cannot see:**
  internally periodic words occur in saturated views (notebook 21 §5).

**Recommendation for M2.** M2 as written (a gap-guided allocation among these views
under matched ceilings) cannot produce a shorter archive on these strings: A3 already
evaluated every eligible view with every proposal and none won, so any allocation over
the same proposal set can only save computation. I recommend a documented stop for M2
as specified. If the programme continues, the observations point to the separately
listed addition — dictionary-internal relations (periodic or mutually related words
inside saturated dictionaries) — as a new, separately specified representation, to be
designed without tuning on these 96 strings.

## 5. Runtime attribution

* Physical execution (each job once): A0 worker wall 44.32 s (max 0.968 s);
  augmentation A1 7.06 s, A2 8.84 s, A3 14.07 s (max 0.262 s); all 384 new jobs 74.29 s.
  Peak RSS: A0 ≤ 52.2 MB, A3 ≤ 36.9 MB. No child approached 30 s or 1 GiB.
* Attributed deployment (A0 + augmentation, A0 charged in full to every composite):
  median / max — A1 0.403 / 1.046 s, A2 0.415 / 1.096 s, A3 0.467 / 1.171 s. No
  composite is cheaper than A0; there is no speedup claim. Imported baseline timings
  belong to another run and were not compared.

## 6. Time (controller ledger `ledger/resource_events.jsonl`)

| category | used (s) | cap (s) |
|---|---:|---:|
| development | 1,307.4 | 10,800 |
| benchmark | 78.5 | 7,200 |
| report_verification | 367.6 (span closed after this handoff was written; this one-line edit is uncharged) | 3,600 |
| **total** | **1,753.5** | **21,600** |

The development span was back-dated to the first packet read (16:24:09 local). The
600 s reporting reserve (300 s finalisation, 300 s Codex review) is intact; the
3,000 s / 3,300 s reporting stops were not approached. Earlier studies' charges are
untouched. Worker wall is reported separately (`resource_totals.json`).

## 7. Code ownership

New algorithm owner: `experiments/hierarchy_multilevel/search.py`. Thin adapters:
`worker.py`, `runner.py`, `cli.py`; reporting `report.py`; audit `audit.py`; clock
`ledger.py`; preservation and lock `preserve.py`; tests in `tests/`. Reused unmodified
owners and the Q1–Q4 statement are in `IMPLEMENTATION_MAP.md`. The owner guard
(`test_no_copied_owner_or_second_algorithm_definition`) rejects a planted copy. Post-lock
presentation files: `notebooks/build_21.py`, `notebooks/21_hierarchy_multilevel.ipynb`,
`experiments/hierarchy_multilevel/notebook21.py` (not in the lock closure; they read
saved artefacts only).

## 8. Tests, guards and verification

* New suite: 50 passed before the lock and again after (`ledger/pytest_new_suite_*.log`).
  It covers every BENCHMARK §2 item with 16 declared fixture inputs (≤ 4,099 bits,
  `fixtures/declared_inputs.json`), including real-child watchdog fixtures under fixture
  limits (2 s wall stall with checkpoint fallback; 1 MiB RSS with the owner-built A0
  retained), crash, corrupt checkpoint, lock mismatch, hooks refused under a lock,
  partial writes, resume rejection and INVALID-over-INCOMPLETE through the report path.
* Mutations (`fixtures/mutations_a1.json`): 8/8 killed by assertion failures — tail
  loss, missing dictionary cost, wrong original span, free-incumbent runtime, false zero
  (modal gap and saving), tie replacement, INCOMPLETE-over-INVALID.
* Existing hierarchy suite: 282 passed, **1 failed** —
  `test_search_v3a.py::test_reserved_generation_requires_a_validated_freeze`. Pre-existing
  and unrelated: it asserts "no freeze yet" for `search-confirm-v3a-r1`, which now has a
  validated freeze. No hierarchy file was touched (initial = final hashes).
* Description-length tests: 145 passed. ruff on new code: clean (pre- and post-lock).
* Guards (zsh): `check_core_index` pass; `check_test_manifest` pass; `check_single_engine`
  **fails** on the same pre-existing sites as the accepted v3a log (sorted logs identical
  apart from the exit-line format; 0 sites in the new package). `make ci-local` was not
  run (dirty-tree exception); **not all repository checks passed.**
* `cli verify`: exit 0 — lock clean, summary recomputed equal, traces re-hashed, audit
  pass. `audit.py`: pass; 1,248 archives read from bytes, 1,344 decodes, 0 problems; it
  reuses only `hierarchy.decode` (the independent decoder) and imports nothing from
  `report.py`.
* Notebook 21: run2 passes all 8 guard checks from the notebook directory and the
  repository root (`notebook/run2.checks.json`); run1 failure retained (§9).

## 9. Deviations and disclosures

1. **Pre-lock smoke on benchmark inputs.** During development I ran `augment()` on 4 of
   the 96 inputs (CASES indices 0, 1, 50, 95) to confirm execution and runtime. All 12
   composites retained A0. The algorithm was not changed afterwards; no other benchmark
   input was used before the lock (`ledger/attempts.jsonl`, A-dev-02).
2. **Fixture declaration file timing.** The 16 fixture constructions were fixed in
   `tests/fixtures.py` before the first suite run, but `fixtures/declared_inputs.json` was
   written after it. Three first-run failures were wrong hand expectations in tests and
   one was a real coding defect in the watchdog selection label (fixed pre-lock;
   attempts A-dev-03, A-dev-04).
3. **Guards first run with bash.** The zsh guards were first invoked with bash
   ("bad substitution"); those logs are retained as `*_bash_wrong_shell.log`.
4. **First run launch** failed in the shell redirect before Python started (no job, no
   row; attempt B-run-00).
5. **Notebook run1** failed one guard check because the driver's forbidden-token list
   matched `hierarchy_multilevel` inside the results path literal. Presentation-only
   revision R1 (`reporting_revisions.json`, diff retained) restricted the token to import
   statements; no row, computation or endpoint arithmetic changed.
6. **Interpretations** fixed before the lock (root assembly, slot accounting, duplicates
   against A0, branch statuses, weak support, description gap, wall-key stripping) are
   listed in `IMPLEMENTATION_MAP.md`.
7. **A0 rows** are produced by the owner `_job_row` and then relabelled (study, role,
   evidence role, lock sha); every contract reproduction field is compared to the saved
   row with keys ending in `wall_s` removed recursively.
8. **Working files** `tmp/*.ckpt/` (checkpoint and per-view logs of completed jobs) are
   retained. The run tree is 108 MB, 99 MB of it traces; no file exceeds 5 MB.

## 10. Preservation

Initial (`preservation/initial_preservation.json`) vs final
(`preservation/final_preservation.json`, comparison `preservation/initial_vs_final.json`):
50/50 hierarchy sources unchanged; shared owners unchanged; 0 critical and 0 protected
files changed against the packet (notebook 19 and its builder were not touched and did
not drift during the run); the four old result trees (95,471 files) have identical
aggregates; bitacora and notebook README unchanged; the only notebook-directory changes
are the new `build_21.py` and `21_hierarchy_multilevel.ipynb`; every git-status addition
is a new file of this phase; nothing was removed.

## 11. Exact commands (from `index-deconvolution/`)

```
venv=../venv/bin/python; E="PYTHONPATH=experiments:.:../src"
(cd .. && venv/bin/python -B index-deconvolution/protocols/hierarchy_multilevel_v1/check_packet.py)
env $E $venv -B -m hierarchy_multilevel.preserve initial <run>/preservation/initial_preservation.json
env $E $venv -B -m hierarchy_multilevel.cli fixtures
env $E $venv -B -m pytest experiments/hierarchy_multilevel/tests -q -p no:cacheprovider
env $E $venv -B -m hierarchy_multilevel.tests.mutations <run>/fixtures/mutations_a1.json
PYTHONPATH=.:../src $venv -B -m pytest hierarchy/tests -q -p no:cacheprovider
env $E $venv -B -m hierarchy_multilevel.cli lock
env $E $venv -B -m hierarchy_multilevel.cli run --quiet
env $E $venv -B -m hierarchy_multilevel.cli report
env $E $venv -B -m hierarchy_multilevel.cli verify
env $E $venv -B -m hierarchy_multilevel.audit
$venv -B notebooks/build_21.py && $venv -B experiments/hierarchy_multilevel/notebook21.py run2
env $E $venv -B -m hierarchy_multilevel.preserve final <run>/preservation/final_preservation.json
(cd .. && zsh tools/check_core_index.sh; zsh tools/check_test_manifest.sh; zsh tools/check_single_engine.sh)
```

## 12. Proposed bitácora entry (text only; bitácora unchanged this round)

> **46 — HID multilevel v1 (exploratory feasibility).** Reversible word abstraction at
> eight widths, two origins and four pairing levels, with run, pair-grammar and
> occurrence-gap proposals, all paid in the archive and decoded independently, was
> added on top of the accepted k = 1 search. On the 96 exposed search-v2 strings no
> proposal beat k = 1 in any arm (VALID_COMPLETE, NO_RETAINED_GAIN); the nearest case
> rediscovered A0 byte for byte. Short words repeat but their dictionaries do not pay;
> long words and deep levels saturate. M2 as specified cannot help; dictionary-internal
> relations are the open thread.

**Ready for Codex review; not yet accepted.**
