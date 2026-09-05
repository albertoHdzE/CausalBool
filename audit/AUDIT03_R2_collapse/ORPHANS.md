# Orphan adjudication — AUDIT03-B

**Date:** 2026-09-04 · **Producer:** `orphan_census.py` → `orphan_census.json`

A function nobody calls drifts exactly as a duplicate does. This audit had
already tripped over two by accident — a `TSK-MIXED-001` copy of the description
length that was never invoked, and a `pair` unpack in `complexity_analysis.py`
that could only ever have raised — so the question is asked deliberately here.

> **The census UNDER-reports.** It counts a name as referenced if it appears
> anywhere outside its own definition, including inside strings, so it
> over-counts references by design. **Every name below is genuinely
> unreferenced; the true orphan set is larger.** A floor, not a ceiling.

| arm | defined | never referenced |
|---|---|---|
| Python, 370 files | 2,053 functions / 1,673 distinct names | **29 (1.7%)** |
| Wolfram packaged core | 38 public definitions | **4** |
| **inside a declared `CORE.md` owner** | — | **0** |

That last row is the one that matters: the files `GOVERNANCE/CORE.md` names as
owners are fully live.

## Nothing is deleted on the strength of a grep

Deleting a public symbol because a text search missed it is precisely the
reasoning this audit exists to discourage. Each entry is labelled, and only
**load-bearing** ones were acted on.

### Acted on — the orphan that was not merely dead

| symbol | site | what it was |
|---|---|---|
| `lsb_inputs` | `papers/method/code/corroboration_6node/ordering_invariance_6node.py` | the machinery for the **LSB half of the ordering-invariance claim**. The LSB one-sets were hard-coded literals, so only the MSB side was ever recomputed. Both sides are now derived from the update rule and the published literals verified against them. They match, so no artefact moved; a planted wrong anchor exits 1. |
| `myAnd`, `myOr`, `myXor`, `runNetwork`, `allPosibleInputsReverse` | `src/Packages/Integration/SelfTest.m` | **a fourth engine.** See `DUPLICATION.md`. Collapsed onto the owners after a 378/378 + 992/992 parity run; the nine unimplemented families had been evaluating to a silent `0`. |

### Capability awaiting use — recorded, kept

| symbol | site | why it stays |
|---|---|---|
| `generate_bio_repertoires` | `src/integration/bio_D_experiment.py` | builds the corpus repertoires. **Blocked behind R4**: 3,977 of 5,204 corpus nodes have no derivable Boolean truth table, so the consumer does not exist yet. Deleting it would delete the unblocking step. |
| `posterior_probabilities` | `imp-prices/src/imp_prices/belief_network.py` | the module scores **hard argmax labels** (`predict_regimes`), so calibrated posteriors are unused. Not a defect — it means **no calibration claim has been made**, and the protocol has not yet called for one. |
| `build_pum_table` | `imp-pathinfo-paper/.../analysis.py` | PUM tables are reproduced by the notebook path; the helper is the packaged equivalent. |
| `delong_test`, `compute_all_node_metrics`, `generate_depmap_lineage_meta` | `workspaces/claude-nature/paper/code/` | **frozen Level 8 reproducibility artefact.** Editing it to remove an unused function damages the thing it exists to preserve. |

### Superseded — recorded, kept for provenance

| symbol | site | superseded by |
|---|---|---|
| `compute_d_bdm_correlation` | `src/integration/bio_D_experiment.py` | `audit/AUDIT03_R3_description_length/bdm_vs_dschema.py`, which reports the correlation **with its permutation null in the same sentence** (`r = +0.388`, null `[-0.136, +0.144]`, `p = 1e-4`) and holds `n` fixed at 10 so size is removed by construction. The older helper returns a bare coefficient. Kept so the provenance of earlier results survives; **not to be quoted**. |

### Public API — kept by role

`KnockoutNetworkByIndex` (`BioExperiments.m`), `LogicParseStatus` and
`LogicVariables` (`LogicEval.m`). Exported surface of packaged modules.

`SelfTestRun` (`SelfTest.m`) is **no longer an orphan**: `tests/SelfTest.m` now
calls it, exports its verdict, and is declared in the manifest.

### Genuinely dead, low value, left in place

The remainder — `_sha256_file`, `_row_stochastic`, `_dep_score_for_node`,
`run_directory_analysis` (`DepMap_Validation.py`); `scrape_cell_collective`,
`scrape_ginsim`, `download_cell_collective_model`,
`build_cellcollective_sbml_cohort` (scrapers); `simple_randomization`,
`signal_handler`, `normalized_lz`, `load_results_from_json`,
`generate_tcga_expression_cohort`, `compare_complexity`; and the
`index-deconvolution` level helpers.

Left in place deliberately. They are ingestion and scaffolding for data paths
that are gitignored or externally fetched, so "unreferenced today" and "dead" are
not the same claim, and the census cannot tell them apart. Recorded here so the
next reader inherits the list rather than rediscovering it.

## Open item

**`SETUP-002` reports `SUCCESS. D_v2 = 0`.** The Nature Level-3 setup test now
runs and passes, and its passing value is a description length of **zero**. That
is either a real defect in `UniversalDv2` or a degenerate fixture. Not chased
here: `D_v2` already carries the standing note that it has **no decodability
proof at all**. Recorded for the author.
