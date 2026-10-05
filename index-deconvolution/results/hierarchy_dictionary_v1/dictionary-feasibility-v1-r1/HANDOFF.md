# HANDOFF — HID dictionary relations v1 feasibility (`dictionary-feasibility-v1-r1`)

**Status: ready for Codex review; not yet accepted.**

Executor: Claude Code, 2026-10-04. Supervisor: Codex. Protocol:
`PROTOCOL_hierarchy_dictionary_v1.md` with `protocols/hierarchy_dictionary_v1/`.
Nothing was committed, pushed, published or scheduled; no follow-on phase was started.

## 1. Result in one paragraph

Engineering verdict **VALID_COMPLETE**; conditional exploratory label **NO_RETAINED_GAIN**
(D2 < D1 on 0 of 96 strings, D1 < D0 on 0, D0 < A0 on 0). All 288 composites are
byte-identical to their A0, so every arm-vs-A0 contrast is exactly 0 (0/96/0 strings,
0/48/0 pairs, 0/24/0 cells), D0 = old A3 on 96/96, and each arm inherits A0's standing:
+0.351713 bits per input bit against `pair_grammar` (87/0/9 strings) and −0.045188 against
the nine-method portfolio (21/12/63 strings). The new dictionary modes are not inert at the
level of a single view: over the 6,096 evaluated D2 views, R(O) gives a shorter archive than
the *same view's* O proposal in 1,243 views (2,628 equal, 2,225 longer) and P in 368
(4,787 equal, 941 longer); per string, the best R(P) view beats the best O view on 14 of 96
strings (R(O) 12, P 2). None of those view-level gains reached A0. The closest any relation
came: on 4 F10 strings R(O)/R(P) produced distinct complete archives of exactly A0's length
(440 or 688 bits; ties keep A0); on the rendered case (F10-1024-3000-base, width 64) the two
selected relations are exact complements, and the tied archive has the same byte composition
as A0 (LITERAL 20, XFORM 8, CONCAT 18 bytes), i.e. the relation mode rediscovered structure the
k = 1 search already describes. The searches all completed (no watchdog), so this is not a
time-out artefact — but it is a statement about this finite candidate heuristic on exposed
strings, not about the absence of dictionary structure, and it carries no fractal or causal
reading.

## 2. Identity

| item | value |
|---|---|
| implementation lock | `implementation_lock.json`, sha256 `19b53d32873a37cfd37e84129d880056ebf6132a6994c2f6e339f25142373780` |
| lock written | 2026-10-04T23:37:50Z; git HEAD `53c41d8f` (unchanged; nothing committed) |
| source snapshot | `source_snapshot.tar`, sha256 `1405a506f7a0f50882eb24c65682aaa56010d582febf96febed14a96f6f4ee1a`, 93 members |
| lock closure | all 93 members (Python **and** non-Python: packet, CASES, contracts, PREVIOUS_A3, declared fixtures, implementation map) re-hashed by every worker and by `verify` |
| import probe | every reused module (`hierarchy*`, `hierarchy_multilevel*`, `hierarchy_dictionary*`) resolved inside `index-deconvolution/` in a `-S` child |
| A0 config | `hid_full`, registry `search-v2`, sha256 `8a829b12…3128159` (contract value) |
| arm configs | D0 `6bf73be8…`, D1 `1921fc1f…`, D2 `d4d81d9c…` (full hashes and configs in the lock) |
| packet | `check_packet.py` exit 0, output identical to `PACKET_CHECKS.json` (14/14 checks); manifest 14/14 hashes match (`preflight/`) |

## 3. Counts and statuses

| item | intended | available | notes |
|---|---:|---:|---|
| strings | 96 | 96 | decoded from retained raw archives; input hash and n checked |
| A0 jobs (new) | 96 | 96 | 96/96 reproduce every contract field incl. bytes (`baseline_gate.json`) |
| augmentation jobs (new) | 288 | 288 | all `ok`, all `search_complete`; 0 watchdog, 0 invalid, 0 unavailable |
| new encoder jobs | 384 | 384 | |
| derived composite records | 288 | 288 | not jobs |
| imported constituent references | 864 | 864 | 0 hash/decode problems |
| derived portfolio minima | 96 | 96 | 96/96 equal saved `baseline_best` (owner tie rule) |
| imported old A3 (rows, archives, traces, masks) | 96 | 96 | 0 problems; no jobs, no runtime comparison |
| traces | 288 | 288 | hashes re-checked by `verify` and the audit |
| D2 view records | 6,144 | 6,144 | 6,096 evaluated, 48 ineligible (width 64, level 4, m < 2), 0 pruned, 0 capped |
| selected augmentation archives | — | 0 | `explanations.jsonl` holds 384 representative best candidates (one per D2 string × mode), each with an exact byte ledger |

Work (whole run; requests include duplicates, patch and graph rejections):

| arm | requests | serialized | decoded | duplicates | patch-limit rej. | no gap template | graph rej. | relation comparisons |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D0 | 17,571 | 13,338 | 9,648 | 3,690 | 4,233 | 6,813 | 0 | 0 |
| D1 | 35,142 | 26,676 | 12,183 | 14,493 | 8,466 | 13,626 | 0 | 0 |
| D2 | 70,284 | 53,352 | 19,652 | 33,700 | 16,932 | 27,252 | 0 | 12,398,416 |

D2 by mode — O: 9,648 new / 3,690 duplicate; P: 2,535 / 10,803; R(O): 6,573 / 6,765; R(P):
896 / 12,442 (each mode 4,233 patch-limit rejections, 6,813 missing templates). Dictionary
construction (D2): 219,053 entries; 4,195 periodic replacements in 1,392 views; 167,147
words with a proper but non-dividing period (kept O, as specified); 130,575 relations
selected per R mode in 3,514 views; 354,960 comparisons per R mode were within 8 flips but
refused by the hop cap of 8 (the cap binds often); flags 0/1/2/3 = 44,455/25,621/40,699/
19,800; hops 1…8 all occur (8: 18,441). Strict improvements: 0 in every arm. Work caps
(64 views, 1,024 requests) never bound; every stop reason is `completed`.

## 4. Evidence status and recommendation

* Evidence state: VALID_COMPLETE (no INVALID, no INCOMPLETE item). State checks ran before
  any aggregate or label logic.
* Label: **NO_RETAINED_GAIN** (fixed order: relation, period, control-only, none).
  Exploratory guidance about these algorithms on these cases only.
* Incremental contrasts: D0 vs old A3 0/96/0 (changed pruning gained nothing; D0 evaluated
  every view old A3 skipped — 1,852 more D2/D0 view instances — and reproduced all 4,244
  old-A3 views byte for byte in mode O); D1 vs D0 0/96/0; D2 vs D1 0/96/0.
* Ties: equal-length distinct archives on F05-1024-3000-ragged (all modes, as in
  multilevel-v1) and on F10-1024-3000/3001-base and F10-4096-3000/3001-base (R modes only,
  new in this phase); byte-identical rediscovery of A0 on F05-1024-3000-base.
* Harmful contrasts: none against A0 (non-regression is an engineering invariant). Against
  the portfolio the composites inherit A0's −0.045188 (63 worse strings, 16 worse cells).
* Nesting invariants on complete searches: D0 ≤ old A3, D1 ≤ D0, D2 ≤ D1 (96 each), old-A3
  views in D0 (4,244), D1/D2 mode O = D0 (96 each): 0 violations. Invariants, not evidence.

**Bounded next recommendation.** Stop this line as specified: neither paid periods nor
predecessor relations, offered as whole-dictionary bundles inside the multilevel-v1 views
and proposals, retained any gain over k = 1 on these exposed strings, and the nearest
cases tie by rediscovering what A0 already encodes. If the programme continues, the only
observation that suggests a different representation (to be specified fresh, without
tuning on these 96 strings, and confirmed prospectively) is that view-level relation gains
are common (1,243 views) but never large enough to cover the cost of the multilevel
envelope against A0's own segmentation; a fresh protocol would have to change *what is
paid*, not enlarge windows, flip caps or hop caps here. No experiment is authorized by this
handoff.

## 5. Runtime attribution

* Physical execution (each job once): A0 worker wall 45.16 s (max 0.980 s); augmentation
  D0 17.83 s, D1 25.27 s, D2 44.89 s (max 0.974 s); all 384 jobs 133.16 s. Peak RSS: A0
  ≤ 52.0 MB, D2 ≤ 50.9 MB. No child approached 30 s or 1 GiB.
* Attributed deployment (A0 + augmentation, A0 charged in full to each composite) median /
  max: D0 0.494 / 1.302 s, D1 0.538 / 1.471 s, D2 0.678 / 1.933 s. More modes cost more
  work (D2 ≈ 4× D0 requests, 12.4 M relation comparisons) and bought nothing here. No
  speedup claim. Imported baseline and old-A3 timings belong to other runs and were not
  compared.

## 6. Time (controller ledger `ledger/resource_events.jsonl`)

| category | used (s) at handoff write | cap (s) |
|---|---:|---:|
| development | 1,319.2 | 10,800 |
| benchmark | 161.6 | 7,200 |
| report_verification | 429.7 (ledger stop event; this one-line correction after the stop is uncharged) | 3,600 |
| **total** | 1,910.6 | **21,600** |

The development span was opened at the controller start (first packet read, 23:16:00Z).
The 600 s reporting reserve (300 s finalisation, 300 s Codex review) is intact; the 3,000 s /
3,300 s reporting stops were not approached. No borrowing or recategorisation. Historical
charges untouched. Worker wall is reported separately (`resource_totals.json`).

## 7. Code ownership

Single new algorithm owner: `experiments/hierarchy_dictionary/search.py` (dictionary modes
O/P/R and `augment`). Thin adapters: `worker.py`, `runner.py` (subclasses multilevel
`AugJob` only to launch this worker), `cli.py`, `report.py`, `audit.py`, `ledger.py`,
`preserve.py`; tests in `tests/`. Imported, unmodified: multilevel-v1 `path_levels`,
`ViewBuilder` (G0–G3), `ranked_gaps`, `view_diagnostics`, `_Inc`, the multilevel runner,
ledger, preserve and report arithmetic helpers, and the `hierarchy` grammar/wire/decoder/
ledger/watchdog owners (`IMPLEMENTATION_MAP.md`, Q1–Q4). The owner guard
(`test_no_copied_owner_or_second_algorithm_definition`) rejects a planted copy. Dictionary
modes only replace `ViewBuilder.sym` per mode inside one factory per view. Post-lock
presentation files (not in the closure; read saved artefacts only): `notebooks/build_22.py`,
`notebooks/22_hierarchy_dictionary.ipynb`, `experiments/hierarchy_dictionary/notebook22.py`.

## 8. Tests, guards and verification

* Fixtures: 17 distinct declared inputs (≤ 4,099 bits, seed 63001; none equal to a benchmark
  input) with hand-derived expectations, written to `fixtures/declared_inputs.json` before
  the first fixture execution (no amendment was needed).
* New suite: 59 passed before the lock and again after (`logs/tests/`). Covers every
  BENCHMARK §2 item: empty/short, odd tails at several levels, both origins, k = 1 and k = m
  with descendants evaluated, forced grouping vs reuse; exact and non-dividing periods with
  a hand case where P lengthens the archive (248 → 272 bits); exact complement/reversal/
  composition, 0/8/9 flips, predecessor-window edge, tie rules, nonzero origin; hop-depth-8
  boundary; original vs rewritten donors; shared donor retained when otherwise unused;
  graph/view/request caps; every mode word equals its original and every archive decodes;
  the hand-derived shared-word witness (O 264 bits vs R(O) 216 bits, A0 192 retained);
  P-off/R-off/mode-restriction reproductions; old-mask D0 reproduces multilevel-v1 A3
  proposals on 6 declared fixtures; real-child watchdog fixtures (2 s stall with checkpoint
  fallback; 1 MiB RSS with the owner-built A0 retained), crash, corrupt checkpoint,
  unusable A0, lock mismatch incl. a non-Python closure member, hooks refused under a lock,
  partial writes, resume rejection (missing/corrupt/foreign rows, other-lock A0), old-A3
  tamper detection, INVALID-over-INCOMPLETE and absent-is-null through the report path.
* Mutations (`fixtures/mutations_prelock_final.json`): 8/8 killed by failing tests — donor
  misreference, omitted exception, dropped tail (these three by in-test verification errors:
  `DecodeMismatch` ×2, owner wire `ValueError`), free dictionary cost, incorrect hop cap,
  free A0 runtime, missing-as-zero, INCOMPLETE-over-INVALID (assertion failures).
* Existing hierarchy suite: 282 passed, **1 failed** —
  `test_search_v3a.py::test_reserved_generation_requires_a_validated_freeze`, the
  pre-existing stale test (unchanged; not repaired, as instructed).
* Description-length tests: 145 passed. ruff: clean pre- and post-lock.
* Guards (zsh): `check_core_index` pass; `check_test_manifest` pass; `check_single_engine`
  **fails** with the same 9 pre-existing sites as the accepted multilevel log (sorted FAIL
  lines identical; 0 sites in the new package). `make ci-local` not run (dirty-tree
  exception). **Not all repository checks passed.**
* `cli verify`: lock clean, `summary.json` recomputed identical, trace and candidate hashes
  clean, nesting 0 violations, verification pass.
* Independent audit (`arithmetic_audit.json`): pass, 0 problems; 26,364 archive reads, 12,332
  distinct decodes, 25,020 retained candidate archives re-decoded; recomputes lengths,
  reference minima, old A3, all 15 contrasts at string/pair/cell level with denominators
  96/48/24, selection (first strict minimum by request ordinal), per-mode best bits,
  request ordinals and the label without importing `report`/`search` or any encoder. It
  shares the owner decoder `hierarchy.decode` on purpose: exactness is defined by it.
* Notebook 22: guarded run3 passes all checks from the notebook directory and the
  repository root (exit 0 both, 0 errors, 0 refusals, only allow-listed `hierarchy.decode`/
  `ledger` imports, identical outputs, saved values displayed incl. failed attempts).

## 9. Deviations and retained failures

1. **Test expectation (pre-lock).** `test_unusable_baseline_is_invalid_not_success` first
   expected `invalid_crash`; the row is `invalid_decode_mismatch` because the parent's
   fallback is that same unusable A0. INVALID either way; the test was corrected, no code
   change (`ledger/attempts.jsonl`, `logs/tests/attempt01_new_suite.log`).
2. **Mutation harness (pre-lock).** First run killed `free_a0_runtime` by a worker
   ImportError (copy lacked the multilevel package); fixed by symlinking the unmodified
   package; rerun killed it by its assertion (`mutations_attempt01/02.json` retained).
3. **Notebook driver/builder (post-lock, presentation-only;** `reporting_revisions.json`).
   run1 failed a false-positive token check; run2 passed but rendered the wrong "closest"
   case; run3 is the deliverable. All three executions are retained under `notebook/`.
4. **Interpretations fixed before the lock** (`IMPLEMENTATION_MAP.md` §Interpretations): the
   per-mode `ViewBuilder.sym` swap; one job-wide duplicate set initialised with A0; R(O) and
   R(P) computed separately (work charged twice) with R(P)'s identical comparison arrays
   stored as `same_as_R(O)`; expansion hashes recorded as one digest per view plus a
   per-mode exact-equality check of every word; `vs_previous_level` gap fields of
   multilevel-v1 not carried (not required here).
5. **Size.** The run tree is ≈ 351 MB (traces 292 MB; largest single file 3.35 MB; nothing
   over 10 MB). Nothing enters history (no commit).

## 10. Preservation

`preservation/initial.json` (captured before the first new file outside preflight/ledger)
vs `final.json` → `initial_vs_final.json`: protected files (all notebooks incl. 19 and its
builder, README, `_nblib.py`) unchanged; 70 scientific dependencies unchanged; hierarchy
sources and the whole multilevel package unchanged; all five prior result trees unchanged;
protocols and bitácora unchanged; git HEAD unchanged; no git-status entry added outside the
owned paths and none removed. No external drift was observed (notebook 19 included).

## 11. Exact commands (from `index-deconvolution/`)

```
E="PYTHONPATH=experiments:.:../src"; venv=../venv/bin/python
$venv protocols/hierarchy_dictionary_v1/check_packet.py
$venv -B <run>/preflight/capture_initial.py initial <run>/preservation/initial.json
env $E $venv -B -m hierarchy_dictionary.cli fixtures
env $E $venv -B -m pytest experiments/hierarchy_dictionary/tests -q -p no:cacheprovider
env $E $venv -B -m hierarchy_dictionary.tests.mutations <run>/fixtures/mutations_attempt02.json
PYTHONPATH=.:../src $venv -B -m pytest hierarchy/tests -q -p no:cacheprovider
(cd .. && venv/bin/python -B -m pytest tests/analysis/test_description_length_is_algorithmic.py tests/analysis/test_description_lengths_values.py -q)
(cd .. && zsh tools/check_core_index.sh; zsh tools/check_test_manifest.sh; zsh tools/check_single_engine.sh)
env $E $venv -B -m hierarchy_dictionary.cli lock
env $E $venv -B -m hierarchy_dictionary.cli run --quiet
env $E $venv -B -m hierarchy_dictionary.cli report
env $E $venv -B -m hierarchy_dictionary.cli verify
env $E $venv -B -m hierarchy_dictionary.audit
$venv -B notebooks/build_22.py && $venv -B experiments/hierarchy_dictionary/notebook22.py run3
env $E $venv -B -m hierarchy_dictionary.preserve final
env $E $venv -B -m hierarchy_dictionary.ledger status
```

## 12. Proposed documentation entries (text only; README and bitácora unchanged)

> **Notebook README, 22.** `22_hierarchy_dictionary.ipynb` — HID dictionary relations v1:
> paid periodic and related-word dictionaries on the multilevel views; artifact-only.

> **47 — HID dictionary relations v1 (exploratory feasibility).** Dictionary words were
> re-described through exact dividing periods and through complement/reversal-plus-patch
> relations to the eight preceding words, all paid inside complete archives and decoded
> independently, on the unpruned multilevel views. On the 96 exposed strings no arm beat
> k = 1 (VALID_COMPLETE, NO_RETAINED_GAIN). Relations often shortened a view's own proposal
> but never reached below A0; on four F10 strings they tied A0 exactly by rediscovering
> its complement structure. The dictionary-relations thread is closed as specified.

**Ready for Codex review; not yet accepted.**
