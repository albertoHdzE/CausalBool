# Implementation map — HID multilevel v1 (`multilevel-feasibility-v1-r1`)

Written before the implementation lock. Exploratory development on exposed data.

## Ownership (monolithic-code Q1–Q4)

* **Q1 — owners.** The new algorithm has one owner,
  `experiments/hierarchy_multilevel/search.py` (protocol §2). Reused, unmodified:
  `hierarchy.model` (`NodeFactory`, `to_model`, `count_reachable`, `check_bits`),
  `hierarchy.wire` (`serialize_model`, `encode_literal`), `hierarchy.decode`
  (`decode_archive`, the independent decoder), `hierarchy.candidates` (`pair_grammar`,
  `shortest_period`), `hierarchy.ledger` (`archive_ledger`, `explain_model`),
  `hierarchy.segmentation.DecodeMismatch`, `hierarchy.search_v2` (A0 through the owner
  worker `hierarchy.benchmark.worker_main`, registry `search-v2`, method `hid_full`),
  `hierarchy.benchmark` (`_Job` watchdog, `_job_row`, `_rss_watch`, `atomic_write`,
  `store_archive`), `hierarchy.baselines.select_best`, `hierarchy.study.get_study`,
  `hierarchy.corpus.Case`; `search_v3a.preserve.tree_hash` (tree aggregates);
  the reviewed notebook guard `results/hierarchy_search_v2/review_closure/scripts/execute_notebook_artifact_only.py`.
* **Q2 — existing copies.** Searched `hierarchy/` and `experiments/` for multi-width word
  abstraction, first-appearance relabelling and occurrence-gap templates (body fragments
  and names): none exists. `pair_grammar` exists and is imported, not reimplemented.
* **Q3 — why not enrich the owner.** Protocol §2 forbids edits to `hierarchy/` (frozen
  wildcard closure of older studies) and to shared owners.
* **Q4 — guard.** `tests/test_search.py::test_no_copied_owner_or_second_algorithm_definition`
  rejects any definition of an owner name (pair_grammar, serialize_model, decode_archive,
  shortest_period, to_model, NodeFactory, infer_v2, run_arm, archive_ledger,
  encode_literal) in the package, and any algorithm definition outside `search.py`; it is
  verified by planting a copy.

## Files (all new, under `experiments/hierarchy_multilevel/`)

| file | role |
|---|---|
| `search.py` | the algorithm: views, G0–G3, selection, diagnostics, configs `ARMS` |
| `worker.py` | child script (lock check, checkpoints, views.jsonl, exit codes) |
| `runner.py` | parent: inputs, references, A0 via owner `_Job`, augmentation `_Job` subclass, statuses |
| `cli.py` | `fixtures`, `lock`, `run [--resume]`, `report`, `verify` |
| `report.py` | tables, gap map, explanations, summary, REPORT.md, DECISION.json |
| `audit.py` | independent read-only arithmetic audit |
| `ledger.py` | controller wall-span ledger (development / benchmark / report_verification) |
| `preserve.py` | preservation records, lock members, snapshot, environment, import probe |
| `tests/` | `fixtures.py` (16 declared inputs), `test_search.py`, `test_runner.py`, `mutations.py` |

## Interpretations fixed before the lock

1. **Root assembly.** Every proposal root is `CONCAT(prefix?, core, suffix?)` with the
   core as one node (a single child needs no CONCAT); G0/G1 cores are `CONCAT` of the run
   children; the G2/G3 core is `PATCH(predicted)` (“wrap the prefix/suffix outside the
   patch”). The predicted core is `CONCAT(REPEAT(T, m // p), first m % p symbols of T)`
   with the remainder symbols as direct children and `T = CONCAT(dictionary nodes of
   top[:p])`.
2. **Slots.** Only evaluated views consume a view slot; a skipped view (ineligible,
   saturated or single-symbol branch) consumes none. A G2/G3 with no qualifying gap
   (`NO_GAP_TEMPLATE`) requests no root and consumes no proposal slot; duplicates, patch
   rejections and graph rejections each consume one. With 8 widths × 2 origins × 4 levels
   = 64 views and 4 proposals per view, the 64/256 ceilings cannot bind in the study; they
   are exercised by tiny fixture configurations.
3. **Duplicates.** One `seen` set per job, initialised with the A0 bytes; a proposal equal
   to A0 or to an earlier proposal is `DUPLICATE_ARCHIVE` and is not re-decoded.
4. **Descendants of skipped views.** Descendants of a saturated (k = m) or single-symbol
   (k = 1) view carry that branch status; descendants of an ineligible view are
   `INELIGIBLE_SHORT`. Each record still states m, prefix and suffix lengths.
5. **Weak support** = merged union of bit spans of singleton top symbols plus the prefix
   and suffix, divided by n; locations are merged bit intervals.
6. **Description gap** = shortest archive among the view's serialized proposals
   (duplicates included) minus A0 bits; `vs_previous_level_bits` = same against the
   path's preceding evaluated level when both have an admissible candidate, else null
   with a reason.
7. **Dictionary content.** Every top-level dictionary entry of every evaluated view gets
   the owner `shortest_period` of its exact expansion, `complete_repeat` (length divisible
   by period) and `proper_repeat` (also period < length).
8. **Baseline reproduction.** Fields per contract; `search_counters` compared with every
   key ending in `wall_s` removed recursively (`wall_s`, `total_wall_s`).
9. **Augmentation status** semantics are in `runner.py`'s docstring. Watchdog fallbacks
   are valid deployed output; crashes, decode mismatches, corrupt checkpoints, lock
   mismatches and output/checkpoint inconsistencies are INVALID; unavailable A0 or a
   missing row is INCOMPLETE. INVALID precedes INCOMPLETE.
10. **Deployment cost** of a composite = A0 worker wall + augmentation worker wall
    (and the maximum of their RSS); physical totals count each job once.

## Exact invocations (from `index-deconvolution/`)

```
P="PYTHONPATH=experiments:.:../src ../venv/bin/python -B"
$P -m hierarchy_multilevel.cli fixtures
$P -m pytest experiments/hierarchy_multilevel/tests -q -p no:cacheprovider
$P -m hierarchy_multilevel.tests.mutations <OUT_JSON>
PYTHONPATH=.:../src ../venv/bin/python -B -m pytest hierarchy/tests -q -p no:cacheprovider
$P -m hierarchy_multilevel.cli lock
$P -m hierarchy_multilevel.cli run [--resume] [--quiet]
$P -m hierarchy_multilevel.cli report
$P -m hierarchy_multilevel.cli verify
$P -m hierarchy_multilevel.audit
$P -m hierarchy_multilevel.ledger start|stop|status CATEGORY NOTE
../venv/bin/python -B experiments/hierarchy_multilevel/notebook21.py TAG
```

Environment: `venv/bin/python` (CPython 3.13), children launched with `-S` and
`PYTHONPATH=index-deconvolution:src` only (no site `.pth`, so the sibling repository's
`hierarchy` module cannot shadow the owner); the lock's import probe records where every
reused module resolved.
