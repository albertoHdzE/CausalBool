# HID-search-v2 implementation map

Requirement → owner → focused verification → retained output. Paths are relative to
`index-deconvolution/` unless they start with `src/` or `tools/`. Tests are in
`hierarchy/tests/`. One legacy inference engine (`hierarchy/infer.py`), one serializer
(`hierarchy/wire.py`), one decoder (`hierarchy/decode.py`) and one shared
description-length owner (`src/description_lengths.py`) exist; none was edited.

## Monolithic-code gate (answered before writing code)

* **Q1 owners.** `model.NodeFactory`/`to_model`/`count_reachable`, `wire.serialize_model`/
  `encode_literal`, `decode.decode_archive`, `candidates.shortest_period`/`positions_of`,
  `infer.infer(bits, FULL)`, `corpus.generate_unit`/`stream_rng`/word helpers,
  `report` (gates, aggregate, bootstrap, interval), `validation.validate_study`/`validate_run`,
  `benchmark` (runner, workers, rows, freeze), `ledger.archive_ledger`.
* **Q2 existing copies.** The slice-phase periodic builder existed only in the post-hoc
  probe `experiments/probe_hierarchy_search_walls.py` (an experiment, hash-pinned by the
  packet, left untouched); `infer._Search.periodic` has different tail semantics and is
  in a hash-preserved file. Consensus/mismatch helpers likewise existed only in the probe.
* **Q3 enrich vs new.** The scientific owners are hash-preserved by protocol, so the new
  proposers are new modules (`consensus.py`, `segmentation.py`) as the protocol directs;
  orchestration owners (`benchmark`, `validation`, `report`, `cli`, `ledger`) were
  ENRICHED (explicit `study` argument, `cell_index_draws`, `field_buckets`), not forked.
* **Q4 guards.** `test_search_v2.py::test_search_v2_reuses_the_existing_owners` asserts
  object identity of the reused owners; `test_inference_modules_import_no_corpus_or_evaluation_layer`;
  `tools/check_single_engine.sh` (pre-existing external failures documented in the handoff).

## Provenance (PROTOCOL section 3)

| Requirement | Owner | Verification | Output |
|---|---|---|---|
| Working-tree status before edits; patch hash; r1 source check with one disclosed exception | `experiments/preserve_confirm_v1_r1_sources.py snapshot` | exits non-zero on any unexplained drift | `results/hierarchy_search_v2/preservation/preservation_before.json`, `working_tree_status_*_before.txt` |
| r1 source/protocol snapshot (tar, historical bytes only) | same | every member re-hashed against freeze `f970efff…` | `results/hierarchy_v1_supervision/confirm-v1-r1/source_snapshot_confirm-v1-r1.tar` + `.sha256` |
| Read-only historical audit wrapper | `experiments/audit_confirm_v1_r1_from_snapshot.sh` | exit 0 iff audit under snapshot sources equals stored `audit.json` | `preservation/historical_audit_wrapper.log` |
| Approved validator patch integrated once | `git apply` of `validator_closure.patch` | before = reviewed baseline, after = reviewed patched hashes; its 14 tests retained in `test_validation.py` | `preservation/patch_application.json` |
| Old run trees byte-identical before/after | `preserve_confirm_v1_r1_sources.py trees` | aggregate directory hashes | `preservation/preservation_after.json` |

## Search (SEARCH.md)

| Requirement | Owner | Verification | Output |
|---|---|---|---|
| Six cumulative arms, stage prefixes, legacy FULL unchanged | `search_v2.ARMS`, `SearchV2Config.__post_init__` | `test_config_refuses_non_prefix_stages_and_changed_legacy`; selfcheck contract check | `freeze.json#method_configs` |
| Start from complete literal; smallest complete archive; ties keep earlier (raw, L, P, C, D, G, B; periods ascending) | `search_v2._Incumbent`, `infer_v2` | `test_equal_length_keeps_the_earlier_incumbent`, `test_an_added_proposal_strictly_wins_and_raw_is_kept_on_random_input` | row `best_source`, `search_counters.selected_stage` |
| Fresh legacy run in every arm; L byte-identical to legacy FULL | `infer_v2` stage L calls `infer(bits, FULL)` | `test_arms_are_nested_and_every_arm_reruns_the_unchanged_legacy_search`; run-wide `validation.search_v2_checks` (stage-L hash equals `hid_legacy` archive in every row) | `search_counters.stages.L.archive_sha256` |
| Nesting of completed arms; timeout breaks counted, never repaired | `validation.search_v2_checks` | `test_nesting_violation_between_completed_arms_is_invalid_and_fallback_breaks_counted` | `summary.json#nesting`, `resource_nesting_breaks` |
| Grids: original 1..32,64,128,256 ∩ [1, min(256, n/2)]; D = dense minus grid; G = dense | `consensus.original_grid`, `dense_grid` | selfcheck contract; `test_period_63_…` | telemetry `eligible_periods` |
| First-block and consensus words (tie → 0), y = tile, all mismatches, gate floor(n/16) | `consensus.first_block_word`, `consensus_word`, `Residual` | `test_consensus_majority_tie_and_ragged_phases`, `test_consensus_corrects_a_noisy_first_block…`, `test_residual_gate_boundary_is_floor_n_over_16` | telemetry `gate_rejections` |
| Periodic builder carrying phase (slice of y) | `consensus.periodic` | `test_local_blocks_carry_phase…` | — |
| Local proposal: aligned 1,024-bit blocks, per-block cap min(64, floor(L/16)), literal fallback, zero-error collapse | `consensus.local_proposal` | `test_local_blocks_carry_phase_short_final_block_and_eligibility_boundaries`, `test_local_block_with_zero_local_errors_is_a_shared_periodic_node` | — |
| Global proposal: one Patch, only floor(n/16) | `consensus.global_proposal` | `test_zero_error_template_collapses_patch_and_global_holds_more_than_64_corrections`, `test_period_63_…` (200 corrections) | — |
| NodeFactory sharing, to_model order, rule ≤ 4,096 and depth ≤ 64 rejection with telemetry, never truncation | `search_v2._Templates.run_stage` | `test_graph_limits_reject_candidates_with_telemetry_and_never_truncate` | telemetry `graph_rejections` |
| Independent decode of every admissible new full-input candidate; disagreement fatal | `_Templates.run_stage`, `BoundarySearch.evaluate`, final check in `infer_v2` | `test_inference_error_becomes_an_error_row_and_invalidates` (test-only worker forces a disagreement → `error` row) | telemetry `decoded`, `duplicate_archives` |
| Candidate caps 35 / 256 / 256 (547) | `SearchV2Config` caps; D receives 256 − C serialized | selfcheck contract | telemetry `serialized`, `candidate_cap_hit` |
| Cache words/residuals per invocation only; no cross-arm sharing | `_Templates` (per call); each arm is a separate worker | `test_worker_resolves_the_registry_and_matches_in_process_inference` | — |
| B leaf builder: literal vs shortest exact period ≤ 256 (owner `shortest_period`), standalone pricing, literal on tie, cache by (a,b) | `segmentation.BoundarySearch.leaf` | `test_leaf_builder_is_shortest_period_only_with_literal_on_ties` | telemetry `B.counts` |
| Flat concatenation with factory sharing, full-root pricing | `BoundarySearch.evaluate` | `test_partition_shares_identical_leaves` | — |
| Coarse cuts {a+1, b−1} ∪ {a+floor(j(b−a)/32)}; parents ≥ 64; children ≥ 1; trial rank | `BoundarySearch.coarse_cuts`, `run` | `test_coarse_cut_set_parent_eligibility_and_one_bit_children` | telemetry `B.rounds` |
| Refinement ≤ 5 levels, bracket, tie (len, cut, bytes), strict-improvement commit, offer to incumbent, eight segments | `BoundarySearch.run` | `test_two_regime_input_is_split_and_strict_improvement_terminates`, `test_refinement_tie_rule…`, `test_boundary_stage_offers_to_the_full_incumbent` | telemetry `B.rounds[*].last_bracket/last_step/levels` |
| Caps 512 root trials (incl. initial), 2,048 leaves, length charge ≤ 256 n; atomic charge before uncached leaf, trial charge before serialization; best serialized trial offered on exhaustion; unresolved state recorded | `BoundarySearch.leaf/evaluate/run` | `test_budget_exhaustion_stops_and_offers_the_best_serialized_trial` (three caps) | telemetry `B.stop_reason`, `cap_hit`, `unresolved_refinement` |
| Telemetry without truth; stage absence ≠ zero proposals | `infer_v2` | `test_repeated_runs_give_identical_archives_and_deterministic_telemetry`; `test_inference_modules_import_no_corpus_or_evaluation_layer` | row `search_counters` |
| Exhaustive cost buckets (sum = 8 × bytes), defined before freeze | `ledger.BUCKETS`, `BUCKET_RULES`, `field_buckets` | `test_field_buckets_sum_exactly_for_every_codec_and_arm` | `summary.json#cost_components`, `diagnostics.json#cost_buckets` |
| Supplied-boundary references (evaluation only), signed gap vs min(reference, raw) | `study_corpus.edit_mapped_cuts`, `boundary_reference_cuts`, `segmentation.supplied_partition`, `diagnostics_v2.boundary_references` | `test_edit_mapping_of_construction_cuts`; fixture end-to-end | `diagnostics/boundary_reference/references.json` + archives |
| Handcrafted F12 witness kept separately with its post-hoc label | `diagnostics_v2.witness` | — | `diagnostics.json#handcrafted_witness` (development regression) |

Field-to-bucket rule (`ledger.BUCKET_RULES`): envelope = magic, codec, n, payload length;
dag_count_opcodes = `q_rules` and each opcode; references = every `child_id`;
parameters = length/arity/copies/foreground/q_ap/q_schema/q_flip/flags/rotation and AP
and schema numeric fields; literal_payload_bits / literal_padding_bits = meaningful and
padding bits of HID LITERAL payloads and of the raw codec; correction_deltas = PATCH
deltas; other_payload = everything after the envelope of the other baseline codecs.

## Study, corpus, runner (PROTOCOL section 4, BENCHMARK.md)

| Requirement | Owner | Verification | Output |
|---|---|---|---|
| Explicit immutable study specification; legacy default; no production monkeypatch | `study.StudySpec`, `LEGACY`, `SEARCH_V2`; every orchestration function takes `study` | legacy suite unchanged (202 + validator tests); `test_registry_declares_sixteen_methods…` | `freeze.json#design` |
| Method registry with declared kinds; dispatch by kind (worker too) | `study.method_registry`, `benchmark.worker_main`, `validation.method_kind(m, design)` | `test_registry_…`, `test_worker_resolves_the_registry…` | row `method_kind` |
| Role vs RNG namespace separation; namespace never `development…` | `study.RoleSpec`, `study_corpus.generate_unit` | `test_namespaces_roles_and_development_prefix_separation` | manifests `rng_namespace`, rows `role` |
| Base/ragged paired units from one N string | `study_corpus.generated_cases` | `test_base_is_the_prefix_of_ragged…` | `corpus_manifest.<role>.jsonl` |
| Stress S01/S02 exact draw order; edit coordinates recorded | `study_corpus.s01`, `s02` | `test_stress_draw_order_and_parameters_are_exact` | manifests `params_evaluation_only` |
| Development inputs decoded from retained r1 raw archives, hash-checked; original case ids | `study_corpus.retained_cases` | pilot/regression runs | `development/*/corpus_manifest.*.jsonl` |
| No reserved generation before freeze | `study_corpus._require_freeze` | `test_reserved_namespaces_cannot_be_generated_before_a_freeze` | `freeze.json#exposure_check` |
| Freeze of complete closure + packet + configs + env; snapshot tar; refusal on mismatch | `freeze_v2.write/load_and_validate` (import probe) | `test_source_mismatch_is_refused…`; end-to-end | `freeze.json`, `source_snapshot.tar` |
| Resume only with identical freeze, input and config hashes | `benchmark.case_is_complete` | `test_source_mismatch_is_refused_and_resume_requires_identical_hashes`, `test_interrupted_run_resumes_to_identical_rows` | `logs/benchmark_*.log` |
| 30 s / 1 GiB / two workers; deployed HID fallbacks; censored baselines | `benchmark.run_cases`, `_Job`, `_job_row` with `study.resources` | `test_timeout_and_rss_limit_are_deployed_fallbacks_and_baselines_censored` | row `status`, `worker_wall_ns`, `peak_rss_bytes` |
| Durable cumulative 4 h / 6 h / 2 h allowances | `benchmark.CategoryBudget` | `test_category_budget_is_durable_and_never_resets` | `execution_ledger.jsonl` |
| Whole-run validation, exit codes 0/2/3, approved D1–D3 behaviour | `validation.validate_run(study=…)` + `search_v2_checks` | `test_missing_method_is_incomplete…`, `test_missing_or_malformed_archive…`, `test_verify_writes_not_verified…` | `verification.json` |

Worker cost attribution: `worker_wall_ns` is the parent-measured wall time of the whole
isolated `python -S` worker (start-up, reading the input, every included stage including
legacy inference, serialization, candidate decoding, telemetry, the final archive parse
for rule counts and the archive write); `encode_wall_ns` is the worker-measured inference
call plus that parse. The watchdog applies to `worker_wall_ns`. Sidecar telemetry is in
the row (`search_counters`); archives are written by the worker and content-addressed by
the parent.

## Analysis (BENCHMARK.md sections 5–7)

| Requirement | Owner | Verification | Output |
|---|---|---|---|
| Primary: population, per-string saving, unit → cell → equal cells, seed 44001, percentile 95%, gate order | `report_v2.primary` over `report.population_gate/aggregate/verdict` | `test_primary_weights_pairs_then_cells_equally_never_pools_bits`, `test_gates_invalid_incomplete_censored_and_zero_touching` | `summary.json#primary` |
| Five contrasts, one joint draw over all 21 declared cells (seed 44002), fixed draw order regardless of availability, 99% | `report_v2.contrasts`, `report.cell_index_draws` (shared with `stratified_bootstrap`) | `test_contrasts_read_only_their_cells_with_a_fixed_draw_sequence`; legacy bootstrap test unchanged | `summary.json#contrasts` |
| Descriptive summaries (44003–44005) with full-vs-legacy from the same draws; per-cell estimates; transfer by size | `report_v2.describe_summary/describe_cells/by_transfer_size` | fixture end-to-end | `summary.json` |
| Claim ledger | `report_v2.claim_ledger` | verify recomputes and compares | `claim_ledger.json` |
| Independent primary arithmetic from bytes | `experiments/audit_search_v2_primary.py` (imports no report code) | tolerance 1e-12, counts 840/420/21, portfolio minima, contrast points | `arithmetic_audit.json` |
| Notebook from saved artefacts | `notebooks/build_17.py` | executed; error/unexecuted cell check in `verify --full` | `notebooks/17_hierarchy_search_v2.ipynb` |
