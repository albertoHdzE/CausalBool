# HID-v1 — hierarchical index descriptions

A lossless binary archive format for finite bit strings, an independent decoder, a
bounded deterministic search for hierarchical descriptions, nine comparison codecs,
and the frozen benchmark that tests whether the search finds shorter archives than a
strong decodable baseline portfolio on unseen strings.

Contract: `../PROTOCOL_hierarchical_index_generalization.md` and its annexes in
`../protocols/hierarchy_v1/`. Search details and every development decision:
`SEARCH_SPEC.md`. Test inventory: `TESTS.md`. Results: `../results/hierarchy_v1/`.

**What the numbers are.** `archive_bits` is `8 × len(archive)` of a complete archive
in this fixed format — envelope, headers and padding included. It is a code length
under one fixed language and budget: not K, not CTM/BDM, not `D_schema`, not an
entropy. The search result is the best archive found under the budget, never a
certified minimum.

## Environment

Run from the repository root with the repository venv:

```sh
cd /Users/alberto/Documents/projects/CausalBool
export PYTHONPATH=index-deconvolution:src      # index-deconvolution FIRST: a sibling
                                                # repo's .pth ships a module "hierarchy"
PY=venv/bin/python                              # Python 3.13.12
```

Codec, decoder, search and corpus use the standard library only (benchmark workers
run under `python -S`). numpy/matplotlib/pybdm are used by reporting, diagnostics and
notebooks.

## Commands

The current run is `confirm-v1-r1`, the correctness replay of `confirm-v1` (supervisor
review: `bitacora/35`; amendment: `results/hierarchy_v1/AMENDMENT_confirm-v1-r1.md`).
`confirm-v1` is retained unchanged; it was frozen with the original sources, which are
archived in `results/hierarchy_v1_supervision/confirm-v1/source_snapshot_confirm-v1.tar`,
so verifying it on the current tree reports a freeze mismatch by design. To re-audit it
under its own sources: `zsh index-deconvolution/experiments/audit_confirm_v1_from_snapshot.sh`.
`benchmark`, `diagnostics` and `report` refuse to run when the frozen interpreter,
compression libraries, numpy or pybdm differ from the current ones; `verify` reports
the difference instead.

```sh
$PY -m hierarchy.cli selfcheck                       # golden bytes, round trips, isolated decoder
$PY -m hierarchy.cli encode --input x.txt --output x.isd
$PY -m hierarchy.cli decode --input x.isd --output y.txt
$PY -m hierarchy.cli pilot --run-id dev-v1           # development split only (exploratory)
$PY -m hierarchy.cli freeze --run-id confirm-v1-r1   # once, before any confirmation data
$PY -m hierarchy.cli benchmark --run-id confirm-v1-r1 --split confirmation --resume
$PY -m hierarchy.cli benchmark --run-id confirm-v1-r1 --split transfer --resume
$PY -m hierarchy.cli diagnostics --run-id confirm-v1-r1
$PY -m hierarchy.cli report --run-id confirm-v1-r1    # exit 0 valid+complete, 2 invalid, 3 incomplete
$PY -m hierarchy.cli verify --run-id confirm-v1-r1 [--full]
$PY -m pytest index-deconvolution/hierarchy/tests tests/analysis/test_description_lengths_values.py -q
```

`encode` reads ASCII `0`/`1` with at most one terminal newline (anything else is
refused); `decode` writes exact ASCII `0`/`1` with no newline. The Python API takes
exact `str` bit strings (TypeError for other types, ValueError for other characters).

`verify` is read-only on the stored study (it writes only `verification.json`): it
validates the freeze hashes, regenerates every input from the seed schedule and checks
its hash, decodes every stored archive against it, recomputes lengths from bytes,
checks every portfolio selection, and decodes a stratified sample in a separate
process that holds only `decode.py`. Exit codes: **0** complete and valid (whatever
the scientific verdict), **2** engineering invalidity or corrupted/missing artefacts,
**3** an incomplete declared split. `--full` also runs the tests, ruff, guards and the
notebook execution checks.

A small runnable smoke study on development data, exercising every stage of the
frozen pipeline: `freeze/benchmark/diagnostics/report/verify --run-id dev-smoke`
with `--split development` (about four minutes; development run ids may not touch
confirmation or transfer data).

## HID-search-v2 (study `search-v2`)

Contract: `../PROTOCOL_hierarchy_search_v2.md` and `../protocols/hierarchy_search_v2/`.
Six cumulative HID arms over the UNCHANGED language, decoder and legacy search:
`hid_legacy` (L = `infer(bits, FULL)`), `hid_first_local` (+P), `hid_consensus_local`
(+C), `hid_dense_local` (+D), `hid_global` (+G), `hid_full` (+B). Each arm reruns L and
pays for all of its own work. Results: `../results/hierarchy_search_v2/`; handoff:
`HANDOFF_SEARCH_V2.md`; implementation map: `../results/hierarchy_search_v2/implementation_map.md`.

```sh
$PY -m hierarchy.cli selfcheck  --study search-v2     # also checks the registry against study_contract.json
$PY -m hierarchy.cli pilot      --study search-v2 --run-id dev-search-v2-pilot
$PY -m hierarchy.cli regression --study search-v2 --run-id dev-search-v2-regression
$PY -m hierarchy.cli freeze     --study search-v2 --run-id search-confirm-v2-r1
$PY -m hierarchy.cli benchmark  --study search-v2 --run-id search-confirm-v2-r1 --split confirmation|transfer|stress --resume
$PY -m hierarchy.cli diagnostics|report|verify --study search-v2 --run-id search-confirm-v2-r1 [--full]
```

Study objects (`study.py`) are explicit and immutable: roles, RNG namespaces, case
design, method registry with declared kinds, resource policy and run plans. The legacy
study (`hid-v1`) is the default of every command and is unchanged in behaviour.
Development runs are unfrozen and carry a development fingerprint (hash of the source
closure and method configurations) in place of a freeze hash. Every experimental job is
charged to `results/hierarchy_search_v2/execution_ledger.jsonl` (4 h development,
6 h reserved, 2 h diagnostics/verification; durable across resumes).

## Owner map

| module | responsibility |
|---|---|
| `codes.py` | constants: magic, codec ids, opcodes, compressor parameters |
| `model.py` | immutable validated rule records, `Model`; hash-consed search `Node`s; encoder-side evaluator |
| `wire.py` | canonical serialization, LEB128, MSB-first packing, combinatorial ranks, field ledgers |
| `decode.py` | independent decoder for all ten codecs; standard library only; imports nothing from the package |
| `candidates.py` | proposal generators: period, AP runs/cover, schema bridge to `src/deconvolution.py`, noisy periods, W7 pair grammar |
| `infer.py` | `SearchConfig`, ablation arms, bounded search, literal fallback, trace |
| `baselines.py` | the nine comparison codecs and the decodable best-baseline selection |
| `corpus.py` | the twelve synthetic families, seeds, splits, evaluation-only manifests (never imported by inference) |
| `benchmark.py` | freeze, isolated workers, watchdog, RSS accounting, resumable atomic rows, tiny-oracle run |
| `diagnostics.py` | BDM experiments through `src/description_lengths.py`, symmetric adaptive calibration |
| `ledger.py` | reporting-side field ledgers and graph explanations read from archive bytes |
| `report.py` | analysis from saved rows: endpoint, bootstrap, ablations, tables, claim ledger |
| `cli.py` | orchestration (``--study`` selects the study; legacy default) |
| `study.py` | immutable study specifications, roles, method registries (``hid-v1``, ``search-v2``) |
| `consensus.py` | HID-search-v2 template proposals P/C/D/G (first-block and consensus words, local and global patches) |
| `segmentation.py` | HID-search-v2 stage B: bounded input-only boundary search; evaluation-only supplied partitions |
| `search_v2.py` | HID-search-v2 arms: ``SearchV2Config``, ``infer_v2``, stage telemetry |
| `study_corpus.py` | search-v2 evaluation layer: namespaced generation, stress S01/S02, retained development inputs, boundary metadata, reserved-access guard |
| `freeze_v2.py` | prospective freeze of the executable closure, snapshot tar, exposure check |
| `report_v2.py` | search-v2 analysis adapter over ``report`` (primary, five contrasts, descriptive) |
| `diagnostics_v2.py` | cost buckets, stage yield, supplied-boundary references |
| `cli_v2.py` | search-v2 command implementations |
| `tests/` | package tests, the independent tiny interpreter (`interp.py`), the tiny bounded oracle (`oracle.py`) |

Shared owners touched (narrowly): `src/description_lengths.py` (input validation,
`remainder="recursive"`, `bdm_1d_partition`, `encoded_bit_length`) and its test file.

## Resource limits

Benchmark: 30 s wall per encoding (worker wall, including interpreter start-up), 1 GiB
peak RSS per worker (self-terminating watchdog thread; macOS does not enforce
RLIMIT_AS), at most two concurrent workers, six-hour total budget. HID timeouts keep
a labelled raw fallback (`timeout_raw`); baseline timeouts are `censored_timeout` and
block a positive primary verdict. Decoder limits are documented in `decode.py`.
