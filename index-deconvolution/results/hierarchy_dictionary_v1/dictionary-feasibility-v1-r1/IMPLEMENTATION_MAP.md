# Implementation map — HID dictionary relations v1 (`dictionary-feasibility-v1-r1`)

Written before any new code ran and before the implementation lock. Exploratory
development on exposed data; the lock is a reproducibility record, not a blinded
preregistration.

## Ownership (monolithic-code Q1–Q4)

* **Q1 — owners.** The new algorithm has one owner,
  `experiments/hierarchy_dictionary/search.py` (PROTOCOL §2). Everything else in the
  package is a thin adapter.
* **Reused unmodified (imported, never copied):**
  * multilevel-v1 primitives `hierarchy_multilevel.search`: `path_levels` (with
    `canonical` first-appearance ids and `Level`), `ViewBuilder` (prefix/core/suffix
    coverage, `wrap`, `run_core`, `g0`, `g1`, `gap`), `ranked_gaps`,
    `view_diagnostics`, `_Inc` (strict-improvement incumbent, ties keep earlier),
    `strip_timing`, `BaselineUnusable`, `WIDTHS`, `PROPOSALS`, the view/proposal status
    constants, and `ARMS["A3"]` (old-mask fixture comparison only);
  * multilevel-v1 adapters `hierarchy_multilevel.runner`: `case_specs`, `load_input`,
    `validate_references`, `a0_verified`, `a0_row_path`, `aug_row_path`,
    `read_checkpoints`, `aug_row_valid_for_resume`, `run_queue`, `strip_wall`,
    `REPRO_FIELDS`, `AugJob` (subclassed only to point at this package's worker),
    `write_json`, `sha`;
  * `hierarchy_multilevel.ledger` (`state`, `start`, `stop`, `checkpoint`, `remaining`
    with this run's event-file path; identical caps) and `hierarchy_multilevel.preserve`
    (`sha`, `sha_file`, `snapshot_tar`, `environment`, `git_head`, `git_status`);
  * `hierarchy.model` (`NodeFactory.literal/repeat/xform/patch/concat/expand`,
    `apply_xform` — complement then reversal then rotation, rotation 0 here —
    `to_model`, `count_reachable`, `check_bits`), `hierarchy.wire.serialize_model`,
    `hierarchy.decode.decode_archive` (independent decoder), `hierarchy.candidates`
    (`shortest_period`; `pair_grammar` through `ViewBuilder.g1`),
    `hierarchy.ledger` (`archive_ledger`, `explain_model`),
    `hierarchy.segmentation.DecodeMismatch`, `hierarchy.benchmark` (`_Job` watchdog
    via `AugJob`, `_job_row`, `_rss_watch`, `atomic_write`, `store_archive`,
    `RSS_EXIT`, `method_config_sha`), `hierarchy.baselines.select_best` (through
    `validate_references`), `hierarchy.study.get_study`, `hierarchy.corpus.Case`,
    `search_v3a.preserve.tree_hash`, and the reviewed notebook guard
    `results/hierarchy_search_v2/review_closure/scripts/execute_notebook_artifact_only.py`.
* **Q2 — existing copies.** Searched `hierarchy/` and `experiments/` by body fragment
  (`apply_xform(`, `shortest_period(`, `xform(`, `patch(`, predecessor windows): the
  only relation search is `hierarchy.infer.Inferrer.relations`, a different object
  (exact matches only, rotations 0/1/2/4/8, beam-scoped, no patch, no predecessor
  window, no hop accounting) bound to the v1 inferrer. It is not the protocol's relation
  and is not reused; its semantic owner `apply_xform` is. No periodic-dictionary
  construction exists anywhere (multilevel only *records* `shortest_period`).
* **Q3 — why not enrich the owner.** PROTOCOL §2 freezes `hierarchy/` and the whole
  `experiments/hierarchy_multilevel/` package and requires a separate package with
  `search.py` as the single new algorithm owner.
* **Q4 — guard.** `tests/test_search.py::test_no_copied_owner_or_second_algorithm_definition`
  rejects any definition of an owner name (multilevel primitives, wire/decoder/model
  owners) anywhere in the package and any algorithm definition outside `search.py`;
  it is verified by planting a copy.

## New responsibilities (all in `experiments/hierarchy_dictionary/`)

| file | role |
|---|---|
| `search.py` | `DictionaryConfig`, `ARMS` (D0/D1/D2), mode builders O/P/R(base), `augment` (views, modes × G0–G3, selection, per-mode diagnostics) |
| `worker.py` | child: lock check, checkpoints, `views.jsonl`, candidate archive side file |
| `runner.py` | parent: A0 row (owner `_job_row`), augmentation `AugJob` subclass, `finish_aug`, old-A3 import |
| `cli.py` | `fixtures`, `lock`, `run [--resume]`, `report`, `verify` |
| `report.py` | evidence state, bits, contrasts, labels, workload, mode contributions, ledgers, REPORT/DECISION |
| `audit.py` | independent read-only arithmetic audit (archive bytes + traces; no report import, no encoder) |
| `ledger.py` | this run's controller ledger path over the multilevel ledger functions |
| `preserve.py` | preservation records, lock members, import probe |
| `notebook22.py` | guarded artifact-only execution driver for notebook 22 (post-lock presentation) |
| `tests/` | `fixtures.py` (declared inputs), `test_search.py`, `test_runner.py`, `mutations.py` |

## Interpretations fixed before the lock

1. **Dictionary swap.** One `ViewBuilder` (one `NodeFactory`) per view. Mode nodes are
   built in that factory; for each mode `vb.sym` is set to the mode's node list, G0–G3
   are requested through the unchanged `ViewBuilder` methods, and `vb.sym` is restored
   to O. Top ids, streams, gaps and prefix/suffix are the original ones.
2. **P.** Per top word w: p = `shortest_period(w)`; if p < |w| and |w| mod p = 0 the
   node is `REPEAT(LITERAL(w[:p]), |w|/p)`, otherwise O[i]. Recorded: p,
   complete-repeat, replaced.
3. **R(base).** i ascending; j = max(0, i−8)..i−1; flags 0,1,2,3; comparison of
   `apply_xform(w[j], flags, 0)` with w[i]; flip positions word-relative. Eligible iff
   flips ≤ 8 and 1 + hops[j] ≤ 8; the first of (flips, j, flags) is taken. Node =
   resolved node j of this mode, then `xform(·, flags, 0)` when flags ≠ 0, then
   `patch(·, flips)` (owner drops empty patches). R(O) and R(P) are computed separately
   (work charged twice) even though their comparisons coincide.
4. **Expansion check.** Every mode node is expanded by the encoder evaluator and must
   equal the original word; a mismatch raises `DecodeMismatch` (INVALID).
5. **Pruning.** New arms never block descendants. k = m, k = 1 and an ancestor with
   either flag are recorded as diagnostics. `old_branch_mask=True` (fixtures only)
   reinstates multilevel-v1 blocking to compare with old A3.
6. **Requests.** Order: views (level, width, origin), then modes in arm order, then
   G0–G3. A missing gap template consumes no request; duplicate, patch-limit and graph
   rejections consume one. One job-wide `seen` set initialised with A0; an archive equal
   to A0 or to any earlier request (any mode) is a duplicate and is not re-decoded.
   Limits per contract: 64 views, 1,024 requests, 4,096 reachable rules, depth 64,
   64 pair rules per view and mode, 64 gap-template flips.
7. **Saved candidates.** Per view and mode the shortest serialized archive (duplicates
   included, first on ties) is retained by hash in the worker's candidate side file and
   stored content-addressed by the parent, with every checkpoint and selected archive.
8. **Per-mode gaps.** `minus_a0_bits` = best mode bits − A0 bits; `minus_O_bits` = best
   mode bits − best O bits of the same view; null whenever either side is missing.
9. **Old A3 comparison.** Imported rows/archives/traces (PREVIOUS_A3.json), hashes
   re-checked; D0 vs old A3 is computed from bytes; for complete searches every
   old-A3-evaluated view's proposal hashes must reappear in D0 mode O of the same view
   (nesting check) and D0 bits ≤ old A3 bits.
10. **Statuses, A0 reproduction, deployment cost** as in multilevel-v1 (fields of the
    pinned contract; keys ending `wall_s` removed recursively; composite cost = A0
    worker wall + augmentation worker wall).

## Exact invocations (from `index-deconvolution/`)

```
P="PYTHONPATH=experiments:.:../src ../venv/bin/python -B"
$P -m hierarchy_dictionary.cli fixtures
$P -m pytest experiments/hierarchy_dictionary/tests -q -p no:cacheprovider
$P -m hierarchy_dictionary.tests.mutations <OUT_JSON>
$P -m hierarchy_dictionary.cli lock
$P -m hierarchy_dictionary.cli run [--resume] [--quiet]
$P -m hierarchy_dictionary.cli report
$P -m hierarchy_dictionary.cli verify
$P -m hierarchy_dictionary.audit
$P -m hierarchy_dictionary.ledger start|stop|status CATEGORY NOTE
../venv/bin/python -B experiments/hierarchy_dictionary/notebook22.py TAG
```
