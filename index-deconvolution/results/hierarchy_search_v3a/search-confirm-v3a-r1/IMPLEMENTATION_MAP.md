# HID-search-v3a implementation map (search-confirm-v3a-r1)

One owner per concept. Every change is relative to the pre-edit executable snapshot
`preservation/preedit_executable_snapshot.tar`; the exact delta is `code_delta.diff`.

## Owners changed (allowed by PROTOCOL section 2)

| File | Change |
|---|---|
| `hierarchy/segmentation.py` | The one boundary search. Adds `BoundaryPolicy` (k, schedule, seed selection, seed pool; `K1` default), `TraceObserver` (append-only, 8,192-event bound, `TraceOverflow`), `_request` (one trace event per trial request: pre/post charges, cache hit, outcome, archive length/hash) and the k-seed schedule inside `run`. `BoundaryConfig` and its serialization are unchanged. k = 1 keeps the old round fields, unresolved-state dict and counters exactly; k > 1 adds `seeds`, `seed_count`, `seed_rank`, `current_level`, `current_bracket`. |
| `hierarchy/search_v2.py` | `infer_v2` now delegates to `run_arm(bits, config, policy=K1, observer=None, identity=None)`, the single L-P-C-D-G-B orchestrator; with defaults it is the old function. |
| `hierarchy/search_v3a.py` (new) | Thin adapter: `SearchV3aConfig` (base arm + policy + trace schema, own hash), `REFINE4`, `ARMS_V3A` (`hid_full` is the search-v2 object itself), `infer_v3a` returning the trace sidecar. |
| `hierarchy/study.py` | `HID_KINDS` adds `hid_v3a`; registries `search-v3a`, `search-v3a-dev-control`, `search-v3a-dev-treatment`; `StudySpec.trace_sidecars`, `StudySpec.job_methods`; `V3aStudy` (replicate-parity HID order; reserved roles generated only after `freeze_v2.load_and_validate` passes); `SEARCH_V3A` and the two development studies. Legacy and search-v2 behaviour unchanged. |
| `hierarchy/benchmark.py` | Worker dispatch for `hid_v3a` (always traces; sidecar next to the archive); `_store_trace` moves the sidecar into `traces/` and links it from the row (`complete`, `unavailable_watchdog`, `missing`); `run_cases` uses `study.job_methods` and derives the portfolio only when declared. Legacy rows unchanged. |
| `hierarchy/validation.py` | `hid_v3a` is a HID kind; a trace-sidecar study runs `report_v3a.trace_checks` inside `validate_run` (failures are engineering invalidity). |
| `hierarchy/freeze_v2.py` | Explicit freeze profiles keyed by registry (`search-v2`, `search-v3a`): protocol files, extra closure (the `experiments/search_v3a` adapters and the `search_diagnosis.common` input reader), informational globs, reserved markers, analysis plan owner. Search-v2 profile identical to the old constants. |
| `hierarchy/report_v3a.py` (new) | Trace re-checks recomputed from events; primary decision over `report.design_units/unit_value/weighted_mean/stratified_bootstrap/percentile_interval/verdict` (no new bootstrap); descriptive tables; development summary. |
| `hierarchy/diagnostics_v2.py`, `hierarchy/tests/test_study_v2.py` | The approved median repair patch only (sha256 `e8da5c6b…`), applied with `git apply`. |
| `hierarchy/tests/test_search_v3a.py` (new) | Focused fixtures (ACCEPTANCE section 1). |

Byte-identical (checked in `preservation/`): `infer.py`, `candidates.py`, `model.py`,
`wire.py`, `decode.py`, `codes.py`, `ledger.py`, `consensus.py`, `baselines.py`,
`corpus.py`, `study_corpus.py`, `report.py`, `report_v2.py`, `diagnostics.py`, the shared
owners and all `experiments/search_diagnosis` files.

## Adapters (`experiments/search_v3a/`)

`preserve.py` (initial/final preservation, executable snapshot, integration equalities),
`ledger.py` (controller wall spans, `SpanBudget` for the runner), `development.py`
(retained-input development and the compatibility gate), `prospective.py` (preflight,
freeze, run, report, verify), `audit.py` (independent arithmetic audit).

## Commands (from `index-deconvolution/`)

```bash
export PYTHONPATH=experiments:.:../src
PY="../venv/bin/python -B"
$PY -m search_v3a.preserve initial results/hierarchy_search_v3a/search-confirm-v3a-r1/preservation
$PY -m search_v3a.preserve integration results/hierarchy_search_v3a/search-confirm-v3a-r1/preservation
git -C .. apply results/hierarchy_search_v2/review_closure/R1_diagnostics_median_repair.patch   # (from repo root)
PYTHONPATH=.:../src $PY -m pytest hierarchy/tests experiments/search_diagnosis/tests -q -p no:cacheprovider
$PY -m search_v3a.development run control dev-v3a-control-a1
$PY -m search_v3a.development run treatment dev-v3a-treatment-a1
$PY -m search_v3a.development compare dev-v3a-control-a1 dev-v3a-treatment-a1
$PY -m search_v3a.prospective preflight
$PY -m search_v3a.prospective freeze
$PY -m search_v3a.prospective run            # --resume after an interruption, same identity
$PY -m search_v3a.prospective report
$PY -m search_v3a.prospective verify
$PY -m search_v3a.audit
$PY -m search_v3a.ledger status
```

The controller ledger (`ledger/resource_events.jsonl`) is opened/closed with
`$PY -m search_v3a.ledger start|stop CATEGORY NOTE`.
