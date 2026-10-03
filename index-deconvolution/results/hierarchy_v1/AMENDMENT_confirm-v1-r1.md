# Correctness amendment: `confirm-v1` → `confirm-v1-r1`

Date: 2026-10-02. Author: Claude Code (implementing developer). Not yet reviewed.
Authority: supervisor review `bitacora/35_hierarchy_v1_supervisor_review.md`
(sha256 `4a000fa5e4d3b0f6…`) and assignment `KICKOFF_hierarchy_v1_corrections.md`
(sha256 `88c85c2e7533e98e…`). Protocol §7: *"A post-freeze correctness fix requires a
new run ID and freeze, with the old run retained as invalidated and the full affected
benchmark rerun."* The original protocol and annexes are unchanged.

## The two runs

| | `confirm-v1` | `confirm-v1-r1` |
|---|---|---|
| freeze sha256 | `ba4bec0a19842deacc349c162ebd79a5634fc384fc6dc4c54040dba3ec78a3b4` | `f970efff16a2d08bf1dd22eee1386c164af5ba67b22137fefcf06cd182b27f5c` |
| frozen at (UTC) | 2026-10-02T15:06:52Z | 2026-10-02T17:19:45Z |
| sources | 17 files | 18 files (adds `hierarchy/validation.py`) |
| status | **superseded; invalidated for approval of the corrected implementation** | correctness replay; awaiting supervisor review |
| files | unchanged, every byte (`results/hierarchy_v1/confirm-v1/`) | `results/hierarchy_v1/confirm-v1-r1/` |

`confirm-v1` is invalidated **only** as evidence for the corrected source: its freeze
names source hashes that the corrected tree no longer has, so `verify --run-id
confirm-v1` on the current tree reports engineering invalidity by design, and no claim
of current-tree freeze validation is made for it. Its observations are **retained**:
the supervisor independently reproduced all 26,112 rows, all 16,402 distinct archives
and every endpoint (`results/hierarchy_v1_supervision/confirm-v1/audit.json`), and that
reproduction stands as evidence about the frozen original implementation.

## Source snapshot of the original

`results/hierarchy_v1_supervision/confirm-v1/source_snapshot_confirm-v1.tar` (sha256
`f5a3d3d7a35541171521415409562e8a35fd8166a36b354d4396e5ffe0333407`) holds, under the
non-importable prefix `confirm-v1-source/`, every file named in the original freeze's
`source_sha256`, `protocol_sha256` and `documentation_sha256_informational` maps (22
files) plus `freeze.json` and `freeze.sha256`, with repository-relative paths. The
manifest `source_snapshot_confirm-v1.sha256` lists each file's sha256; each was verified
equal to the original freeze hash when archived and again after re-reading the archive.
Nothing else was archived (no credentials, no working tree). It is evidence, not an
engine: nothing imports it. The original handoff is preserved verbatim as
`hierarchy/HANDOFF_confirm-v1_original.md` (sha256 `144956d27bc9a54d…`, equal to the
pre-revision `HANDOFF.md`).

Before any edit, the supervisor audit script was rerun against the untouched tree with
its output redirected to a temporary directory; its result was identical to the stored
`audit.json` (apart from the script hash field).

## The amendment (correctness only)

| item | change | effect on stored numbers |
|---|---|---|
| R1 | new owner `hierarchy/validation.py`: the declared design, exact row/method membership, duplicates, unknown keys, metadata and identity checks, archive existence/hash/size/codec/decoding for every status that promises an archive, deterministic portfolio identity; `report` and `verify` both call `validate_run`. `report.py`: the population is the declared design; gates (validity → completeness → censoring → interval) precede every verdict; incomplete or censored data yield only a labelled partial diagnostic. C4/C5 reworded; all-12-family aggregate (seed 43001) and controls-vs-statistical-codes table added as descriptive | none: on the retained `confirm-v1` rows the corrected report reproduces the supervisor's estimates and intervals to ≤ 6×10⁻¹⁷ (`results/hierarchy_v1_corrections/original_rows_under_corrected_report.json`) |
| R2 | `infer._Search.consider` raises `CandidateExpansionMismatch` on a right-length, wrong-expansion proposal; the worker exits non-zero and the row is `error` | none: every retained row has `rejected_verify = 0` |
| R3/R4 | claim and scope wording (`SEARCH_SPEC.md` §7–§8, ledger C4/C5, notebook 16, new handoff and bitacora 36) | none |
| R5 | `benchmark.check_environment`: frozen interpreter/zlib/liblzma (benchmark, resume), numpy/pybdm (diagnostics), numpy (report) are enforced; missing fingerprints never match; `verify` reports its environment without enforcing it or rewriting provenance | none |

Unchanged, by construction and by the freeze diff (`search_configs`, `restricted_oracle_config`,
`baseline_parameters`, `generator`, `expected_counts`, `resource_policy`, `environment`,
`methods` are equal between the two freezes): candidate sources, SearchConfig values,
scoring, wire bytes, corpus distributions, seed schedule, baselines, estimands,
bootstrap seeds. The `analysis_plan` differs only by the added `evidence_gates` text
and the documented descriptive seeds.

## What `confirm-v1-r1` is and is not

A **correctness replay on the same predefined corpus**: the same 1,632 strings and
26,112 method rows, regenerated and rescored from scratch under the corrected source
and the original resource policy. It is not an independent replication, and the
confirmation and transfer strings are not a newly pristine holdout: their results were
seen in `confirm-v1`. Old rows were never copied into the new run. The old/new
comparison is `results/hierarchy_v1_corrections/compare_confirm-v1_vs_confirm-v1-r1.json`.
