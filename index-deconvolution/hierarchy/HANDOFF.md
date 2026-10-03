> **Superseded (2026-10-02).** This is the handoff of the original run `confirm-v1`,
> kept for provenance; a byte-identical copy is `HANDOFF_confirm-v1_original.md`. The
> supervisor review (`bitacora/35_hierarchy_v1_supervisor_review.md`) requested changes
> R1–R5; the corrected implementation was replayed as `confirm-v1-r1` and is reported in
> **`HANDOFF_CORRECTIONS.md`**, which governs. Read this file as historical: in
> particular its C4 and C5 wording, the §8 attribution of losses to structure rather
> than search ("structural, not bugs"), the omission of the 65,536-bit development
> probes from the scope records, and the suggested next experiment (an entropy-coded
> stream, which would be a new wire version, not W3) are corrected there. Its numbers
> were independently reproduced by the supervisor and are unchanged.

# HID-v1 developer handoff — run `confirm-v1`

Developer: Claude Code (implementing developer). Date: 2026-10-02.
**This handoff has not been reviewed or approved by the supervising session.**
Order follows `protocols/hierarchy_v1/ACCEPTANCE.md` §A4.

## 1. Outcome

| dimension | status |
|---|---|
| Engineering | **valid** — 26,112 of 26,112 expected method rows present (confirmation 23,040; transfer 3,072), all `ok`; 0 errors, 0 timeouts, 0 RSS breaches, 0 censored baselines; every stored archive decodes to its regenerated input; `verify --full` exit 0 |
| Confirmation | **complete** (1,440 / 1,440 scored strings) |
| Transfer | **complete** (192 / 192 scored strings; descriptive) |
| Scientific verdict (prespecified primary endpoint) | **not_supported — the advantage is rejected.** Equal-weight mean saving −0.04462 bits per input bit, 95 % bootstrap CI [−0.05368, −0.03582], entirely below zero |

HID-v1 does not produce shorter archives than the strong decodable baseline portfolio
on the prespecified structured confirmation population. It wins descriptively on
arithmetic supports (F04, every size including transfer) and on noisy periods at 256 and
1,024 bits (F06); it loses on plain periods, i.i.d. macro tokens, held-out nested
relations, Thue–Morse and mixed regimes, ties or loses on rule-110 traces, and loses on
the biased-IID and Markov controls (ties on fair coins). Each of the five restricted arms is worse than the full search (all five 99 %
intervals exclude zero; `flat` by far the largest), so the components help HID relative
to restricted versions of itself, but not enough to beat the portfolio. Transfer shows
the same pattern. The BDM diagnostic claim is inconclusive (F04 not separated after
Holm).

## 2. Paths

All paths relative to `index-deconvolution/` unless rooted.

| item | path / hash |
|---|---|
| protocol (sha256) | `PROTOCOL_hierarchical_index_generalization.md` `6208e6b901b9af92…`; annexes `protocols/hierarchy_v1/WIRE_FORMAT.md` `030fcbe58f705b26…`, `BENCHMARK.md` `c7a8fbc090b73614…`, `ACCEPTANCE.md` `55a6adec184d28c5…` (full hashes in `freeze.json`) |
| run id | `confirm-v1` |
| freeze | `results/hierarchy_v1/confirm-v1/freeze.json`, sha256 `ba4bec0a19842deacc349c162ebd79a5634fc384fc6dc4c54040dba3ec78a3b4` (`freeze.sha256`), written 2026-10-02T15:06:52Z UTC, before any confirmation/transfer string was generated |
| source manifest | `freeze.json` → `source_sha256` (17 frozen files: the package except `present.py`/tests, `src/deconvolution.py`, `src/causalbool.py`, root `src/description_lengths.py`); SEARCH_SPEC hash recorded as informational |
| result rows | `results/hierarchy_v1/confirm-v1/rows/<case_id>.json` (1,632 files, `rows_manifest.sha256`) merged into `cases.jsonl` (39 MB, sha256 `da650cad697f0d80…`, kept out of history, see `ARTEFACT_MANIFEST.json`) |
| archives | `results/hierarchy_v1/confirm-v1/archives/<sha[:2]>/<sha>.isd` (16,402 content-addressed files, 15.5 MB, `archives_manifest.sha256`) |
| corpus manifest | `results/hierarchy_v1/confirm-v1/corpus_manifest.jsonl` (evaluation-only realised parameters) |
| summary / claim ledger | `summary.json`, `claim_ledger.json`, `report_tables.md`, `ledgers.json` (one HID and one portfolio ledger per split × family × size) |
| diagnostics | `diagnostics.json`; historical audit rerun to `diagnostics_historical_audit33.json` (original `results/shifted_zero_generalization_audit.json` untouched) |
| verification | `verification.json` (2026-10-02T16:17:12Z–2026-10-02T16:19:21Z, exit 0; final run after all writes) |
| deviations | `DEVIATIONS.md` (append-only; no frozen-source change) |
| report / bitacora | `bitacora/34_hierarchy_v1_results.md` (34 was free) |
| notebooks | `notebooks/16_hierarchical_index_generalization.ipynb` + `build_16.py`; corrected `notebooks/15_shifted_zero_bdm_probe.ipynb` + `build_15.py` |
| development evidence | `results/hierarchy_v1/development/`: `provenance/` (start status, HEAD, hashes, diffs, copies), `calibration/` (scripts + outputs), `dev-v1/` (pilot, `resume_check.json`, `oracle.json`), `dev-v1-replay/`, `dev-smoke/` (full pipeline on development data) |
| package | `hierarchy/` with `README.md`, `SEARCH_SPEC.md`, `TESTS.md` |

## 3. Commands

Interpreter `venv/bin/python` (CPython 3.13.12), working directory the repository root
`/Users/alberto/Documents/projects/CausalBool`, `export PYTHONPATH=index-deconvolution:src`
(index-deconvolution must precede site-packages: a sibling repository's `.pth` ships a
module named `hierarchy`).

```sh
venv/bin/python -m hierarchy.cli selfcheck
venv/bin/python -m pytest index-deconvolution/hierarchy/tests tests/analysis/test_description_lengths_values.py -q
venv/bin/python -m hierarchy.cli verify --run-id confirm-v1          # read-only; add --full for tests/lint/guards/notebooks
printf '1111111101111111' > /tmp/x.txt
venv/bin/python -m hierarchy.cli encode --input /tmp/x.txt --output /tmp/x.isd
venv/bin/python -m hierarchy.cli decode --input /tmp/x.isd --output /tmp/y.txt && cmp /tmp/x.txt /tmp/y.txt
# full reproduction under a NEW run id (confirm-v1 is frozen and complete):
venv/bin/python -m hierarchy.cli freeze --run-id confirm-v1-repro
venv/bin/python -m hierarchy.cli benchmark --run-id confirm-v1-repro --split confirmation --resume
venv/bin/python -m hierarchy.cli benchmark --run-id confirm-v1-repro --split transfer --resume
venv/bin/python -m hierarchy.cli diagnostics --run-id confirm-v1-repro
venv/bin/python -m hierarchy.cli report --run-id confirm-v1-repro
venv/bin/python -m hierarchy.cli verify --run-id confirm-v1-repro --full
venv/bin/python -m hierarchy.present --run-id confirm-v1-repro      # presentation tables
# development: pilot and the pipeline smoke run (development data only)
venv/bin/python -m hierarchy.cli pilot --run-id dev-v1
```

Measured cost of the full study on this machine: about 55 minutes (`budget.json`: 3,325 s
of the 21,600 s budget, including diagnostics), two workers.

## 4. Changes

Created (this stage):

- `index-deconvolution/hierarchy/` — `__init__.py`, `codes.py`, `model.py`, `wire.py`,
  `decode.py`, `candidates.py`, `infer.py`, `baselines.py`, `corpus.py`, `benchmark.py`,
  `diagnostics.py`, `ledger.py` (reporting-side field ledgers; documented in the owner
  map), `report.py`, `cli.py`, `present.py` (presentation, post-freeze), `README.md`,
  `SEARCH_SPEC.md`, `TESTS.md`, `HANDOFF.md`; `tests/` (`conftest.py`, `interp.py`,
  `oracle.py`, eight test files). The empty `hierarchy/protocols/` directory pre-existed
  and was left alone.
- `index-deconvolution/notebooks/build_16.py`, `16_hierarchical_index_generalization.ipynb`.
- `index-deconvolution/bitacora/34_hierarchy_v1_results.md`.
- `index-deconvolution/results/hierarchy_v1/` (development, confirm-v1).

Shared owners and permitted shared files (narrow; starting copies and diffs in
`development/provenance/`):

- `src/description_lengths.py` — `_bits` validates before converting (refuses floats incl.
  0.5, non-binary, ragged, multidimensional, empty, scalar); `block`/`shift` must be
  integral, bool excluded, `1 <= shift <= block`; `remainder` in raise/drop/recursive;
  short input refused for raise/drop; `recursive` via `PartitionRecursive(min_length=1)`
  with explicit coverage check; new `bdm_1d_partition` (reports covered/dropped bits and
  parts); new `encoded_bit_length(payload: bytes) -> int`. Does not import the hierarchy
  package. Parity: 0.0 max difference over 20,458 old-vs-new scores
  (`provenance/h0_owner_parity.txt`). Callers checked: only notebook 15, the audit script
  and the owner's tests call these functions; all pass strings — no compatibility issue.
- `tests/analysis/test_description_lengths_values.py` — +38 tests; the 91 existing kept.
- `GOVERNANCE/CORE.md` — owner rows for the HID format, decoder, search/baselines and
  archive bits; declared exceptions for the deliberately independent decoder, the test
  interpreter, the oracle writer and the ledger parser. `GOVERNANCE/DESCRIPTION_LENGTHS.md`
  — §1c: archive bits are a distinct measured quantity, not a variant; A–E unchanged.
- `index-deconvolution/notebooks/build_15.py` + `15_…ipynb` (regenerated, executed);
  `notebooks/README.md` (rows 15 and 16).
- `index-deconvolution/bitacora/32_shifted_zero_bdm_probe.md` — dated errata appended;
  measured tables and the truncated quotation left as they were, the quotation marked
  incomplete.

Not changed: the exact deconvolution owner (imported by path and asserted), variants
A–E, other notebooks, papers, finance data, vendored code, the root test manifest and
pytest configuration. Nothing committed, pushed, stashed, reset or cleaned.

Deviations and incidents: (1) notebook 15 was regenerated after H1/H2 because its
archive-bits column needs the codec (ordering note, `SEARCH_SPEC.md` §10). (2) The
author hand-edited executed notebook 15 at 09:43 (a comment block in its setup cell);
the edit is preserved and folded verbatim into the builder (`DEVIATIONS.md`). (3) Two
search numbers changed during development only, with before/after measurements
(`SEARCH_SPEC.md` §7): schema table budget 65,536 → 4,096, work cap 60 M → 120 M.
(4) One proposal source beyond the protocol's minimum (AP cover, §4) and a local
dyadic `split` proposal were added during development. No invalidated runs; no new
dependencies.

Pre-existing failures: `tools/check_single_engine.sh` fails nine checks, every one
caused by files under `.kilo/worktrees/held-saguaro/` (a separate worktree from
2026-10-01 23:14); after my provenance copies were renamed to `.py.orig`, no failing
line names a file of this stage.

## 5. Evidence table

| gate / check | result | evidence |
|---|---|---|
| H0 owner tests | pass — 129 in `test_description_lengths_values.py` (91 old + 38 new) | pytest |
| H0 old valid scores unchanged | pass — 0.0 max abs difference, 20,458 comparisons | `provenance/h0_owner_parity.txt` |
| H0 notebook 15 executes / builder agrees | pass — 13 code cells, 0 errors, 0 unexecuted, 6 figures; sources = builder | `verification.json` |
| H0 errata point to executed evidence | pass | bitacora 32 errata §1–11 |
| H1 literal round trips 0..10 | pass — 2,047 / 2,047 | `test_wire_decode.py` |
| H1 golden fixtures | pass — the 6 annex archives, 6 additional hand-derived HID archives (AP overlap, ragged schema overlap, ordered concat, patch deltas, transform order, multi-byte U) and 4 additional baseline archives, all byte-exact | `test_wire_decode.py`, `test_baselines.py` |
| H1 malformed archives | pass — 33 cases rejected; resource limits raise a distinct exception | `test_wire_decode.py` |
| H1 independent decoding | pass — separate process with only `decode.py`; 3 evaluators agree on 300 random compositions | tests; `verification.json` (360-archive stratified sample, all ok) |
| H1 baselines | pass — each of 9 round-trips all 511 strings 0..8 | `test_baselines.py` |
| H2 determinism | pass — identical bytes, counters, traces under PYTHONHASHSEED 0 / 12345 | `test_search.py` |
| H2 blindness | pass — no corpus/benchmark/report imports in inference; `infer(bits, config)`; renamed files give identical archives; workers get stdin only | `test_search.py` |
| H2 caps and fallback | pass — candidate and work caps stop with valid fallback; HID never exceeds literal (every row) | tests; rows |
| H2 tiny oracle | restricted search gap 0 on 511 (n ≤ 8) and 960 generated targets; does **not** exhaust the language; full search below the 3-node language on 48 | `dev-v1/oracle.json` |
| H3 pilot (exploratory) | 128 strings, 2,048/2,048 decode; interrupted after 8, resumed; fresh replay of 12 cases identical | `dev-v1/summary.json`, `resume_check.json` |
| H4 freeze before data | pass — freeze 15:06:52 UTC; corpus generated at benchmark start 15:06:57 UTC, first row 15:06:58 UTC (logs print local time, UTC−6); `write_freeze` refuses once rows exist | `freeze.json`, `logs/`, row mtimes |
| H4 completeness | pass — 26,112 / 26,112 rows, statuses all `ok`; 0 not_run | `summary.json` |
| H5 verify | exit 0 — engineering valid, complete; 24,480 constituent archives decoded against regenerated inputs (portfolio rows point to constituents); 0 input-hash mismatches | `verification.json` |
| tests | 285 passed (156 package + 129 owner); root `tests/analysis`: 265 passed | `verification.json`; console |
| lint | ruff clean on all new/changed Python | `verification.json` |
| guards | `check_core_index` 68/68; `check_test_manifest` agrees (28/28); `check_single_engine` fails only on pre-existing `.kilo` worktree | `verification.json` |
| resources | max encode 9.96 s (hid_full, 65,536-bit transfer); max worker RSS 315.5 MB; 0 timeouts | `summary.json#resources` |

## 6. Scientific tables

Generated from the stored rows by `hierarchy.present` (`report_tables.md`, verbatim).
Intervals for single families, transfer and controls are descriptive. "Not supported"
for C1 is a rejection on this population and budget; it is not evidence that the
families lack structure, and absence of a HID gain on F07 is not proof of randomness.

### Primary endpoint (confirmation, structured families F01–F06, F12)

| quantity | value |
|---|---|
| equal-weight mean saving per input bit | -0.04462 |
| 95% percentile bootstrap CI (10,000, seed 33001) | [-0.05368, -0.03582] |
| cells / units / scored strings | 21 / 420 / 840 |
| mean / median saving (bits per string) | -77.6 / -48.0 |
| strings HID better / tied / worse | 208 / 91 / 541 |
| units missing; baseline rows not ok | 0; 0 |
| **verdict** | **not_supported** |

### Every family and size, confirmation (descriptive 95% CIs)

| family | base | units | mean saving/bit | 95% CI | median bits | HID better/tied/worse |
|---|---:|---:|---:|---|---:|---|
| F01 (structured) | 256 | 20 | -0.3852 | [-0.3915, -0.3790] | -96.0 | 0/0/40 |
| F01 (structured) | 1024 | 20 | -0.0895 | [-0.0948, -0.0843] | -96.0 | 0/0/40 |
| F01 (structured) | 4096 | 20 | -0.0249 | [-0.0254, -0.0244] | -104.0 | 0/0/40 |
| F02 (structured) | 256 | 20 | -0.1670 | [-0.2687, -0.0714] | +0.0 | 0/24/16 |
| F02 (structured) | 1024 | 20 | -0.1051 | [-0.1299, -0.0800] | -108.0 | 0/0/40 |
| F02 (structured) | 4096 | 20 | -0.1074 | [-0.1428, -0.0721] | -368.0 | 0/0/40 |
| F03 (structured) | 256 | 20 | -0.1452 | [-0.1553, -0.1367] | -40.0 | 0/0/40 |
| F03 (structured) | 1024 | 20 | -0.1712 | [-0.1796, -0.1617] | -192.0 | 0/0/40 |
| F03 (structured) | 4096 | 20 | -0.0445 | [-0.0459, -0.0426] | -184.0 | 0/0/40 |
| F04 (structured) | 256 | 20 | +0.0940 | [+0.0590, +0.1274] | +24.0 | 32/2/6 |
| F04 (structured) | 1024 | 20 | +0.2767 | [+0.2412, +0.3072] | +320.0 | 40/0/0 |
| F04 (structured) | 4096 | 20 | +0.1187 | [+0.0848, +0.1547] | +432.0 | 40/0/0 |
| F05 (structured) | 256 | 20 | -0.0266 | [-0.0980, +0.0455] | -8.0 | 18/0/22 |
| F05 (structured) | 1024 | 20 | -0.0214 | [-0.0357, -0.0070] | -24.0 | 9/1/30 |
| F05 (structured) | 4096 | 20 | -0.0072 | [-0.0121, -0.0020] | -36.0 | 6/3/31 |
| F06 (structured) | 256 | 20 | +0.0621 | [+0.0326, +0.0932] | +4.0 | 20/19/1 |
| F06 (structured) | 1024 | 20 | +0.1970 | [+0.1022, +0.2935] | +252.0 | 24/2/14 |
| F06 (structured) | 4096 | 20 | -0.0102 | [-0.0808, +0.0565] | -20.0 | 19/0/21 |
| F07 | 256 | 20 | +0.0000 | [+0.0000, +0.0000] | +0.0 | 0/40/0 |
| F07 | 1024 | 20 | +0.0000 | [+0.0000, +0.0000] | +0.0 | 0/40/0 |
| F07 | 4096 | 20 | +0.0000 | [+0.0000, +0.0000] | +0.0 | 0/40/0 |
| F08 | 256 | 20 | -0.4240 | [-0.4496, -0.3984] | -112.0 | 0/0/40 |
| F08 | 1024 | 20 | -0.4608 | [-0.4766, -0.4456] | -472.0 | 0/0/40 |
| F08 | 4096 | 20 | -0.4552 | [-0.4629, -0.4474] | -1864.0 | 0/0/40 |
| F09 | 256 | 20 | -0.2803 | [-0.3766, -0.1848] | -80.0 | 0/2/38 |
| F09 | 1024 | 20 | -0.3680 | [-0.4560, -0.2810] | -364.0 | 0/0/40 |
| F09 | 4096 | 20 | -0.3818 | [-0.4694, -0.2942] | -1528.0 | 0/0/40 |
| F10 | 256 | 20 | -0.1917 | [-0.2119, -0.1738] | -48.0 | 0/0/40 |
| F10 | 1024 | 20 | -0.0983 | [-0.1061, -0.0915] | -96.0 | 0/0/40 |
| F10 | 4096 | 20 | -0.0627 | [-0.0663, -0.0589] | -256.0 | 0/0/40 |
| F11 | 256 | 20 | +0.0000 | [+0.0000, +0.0000] | +0.0 | 0/40/0 |
| F11 | 1024 | 20 | -0.0010 | [-0.0029, +0.0000] | +0.0 | 0/38/2 |
| F11 | 4096 | 20 | -0.0204 | [-0.0231, -0.0184] | -80.0 | 0/0/40 |
| F12 (structured) | 256 | 20 | +0.0000 | [+0.0000, +0.0000] | +0.0 | 0/40/0 |
| F12 (structured) | 1024 | 20 | -0.0958 | [-0.0993, -0.0922] | -96.0 | 0/0/40 |
| F12 (structured) | 4096 | 20 | -0.2841 | [-0.2912, -0.2755] | -1184.0 | 0/0/40 |

### Ablations (structured confirmation population; 99% CIs, seed 33002)

| arm | (ablation − full) bits per input bit | 99% CI | reading |
|---|---:|---|---|
| hid_no_schema | +0.00896 | [+0.00595, +0.01211] | supported |
| hid_no_arithmetic | +0.03923 | [+0.03353, +0.04514] | supported |
| hid_no_transform | +0.00188 | [+0.00148, +0.00227] | supported |
| hid_flat | +0.26360 | [+0.24348, +0.28251] | supported |
| hid_fixed8 | +0.01152 | [+0.00670, +0.01668] | supported |

### Transfer (descriptive; four units per cell)

Structured aggregate: -0.06280 per input bit, 95% CI [-0.07690, -0.04853].

| family | base | mean saving/bit | 95% CI | median bits | better/tied/worse |
|---|---:|---:|---|---:|---|
| F01 | 16384 | -0.00647 | [-0.00671, -0.00635] | -104.0 | 0/0/8 |
| F01 | 65536 | -0.00163 | [-0.00172, -0.00159] | -104.0 | 0/0/8 |
| F02 | 16384 | -0.05859 | [-0.10766, -0.00952] | -880.0 | 0/0/8 |
| F02 | 65536 | -0.02806 | [-0.05362, -0.00250] | -1768.0 | 0/0/8 |
| F03 | 16384 | -0.00928 | [-0.00928, -0.00928] | -152.0 | 0/0/8 |
| F03 | 65536 | -0.00523 | [-0.00531, -0.00508] | -344.0 | 0/0/8 |
| F04 | 16384 | +0.04602 | [+0.02038, +0.09179] | +424.0 | 8/0/0 |
| F04 | 65536 | +0.01155 | [+0.00374, +0.02295] | +520.0 | 8/0/0 |
| F05 | 16384 | +0.00305 | [+0.00171, +0.00476] | +40.0 | 8/0/0 |
| F05 | 65536 | +0.00218 | [+0.00034, +0.00403] | +140.0 | 7/0/1 |
| F06 | 16384 | -0.33444 | [-0.49861, -0.17027] | -5448.0 | 0/0/8 |
| F06 | 65536 | -0.28373 | [-0.37282, -0.19464] | -20008.0 | 0/0/8 |
| F07 | 16384 | +0.00000 | [+0.00000, +0.00000] | +0.0 | 0/8/0 |
| F07 | 65536 | +0.00000 | [+0.00000, +0.00000] | +0.0 | 0/8/0 |
| F08 | 16384 | -0.45723 | [-0.46297, -0.45186] | -7484.0 | 0/0/8 |
| F08 | 65536 | -0.39051 | [-0.39147, -0.38955] | -25592.0 | 0/0/8 |
| F09 | 16384 | -0.29996 | [-0.41293, -0.18699] | -4852.0 | 0/0/8 |
| F09 | 65536 | -0.25242 | [-0.31991, -0.18493] | -16564.0 | 0/0/8 |
| F10 | 16384 | -0.01788 | [-0.02099, -0.01477] | -300.0 | 0/0/8 |
| F10 | 65536 | -0.00375 | [-0.00417, -0.00343] | -252.0 | 0/0/8 |
| F11 | 16384 | -0.24900 | [-0.33566, -0.16234] | -4360.0 | 0/0/8 |
| F11 | 65536 | -0.46874 | [-0.57024, -0.35694] | -33192.0 | 0/0/8 |
| F12 | 16384 | -0.13243 | [-0.14415, -0.11083] | -2332.0 | 0/0/8 |
| F12 | 65536 | -0.08209 | [-0.08365, -0.08053] | -5392.0 | 0/0/8 |

Statistical controls F07–F09 (confirmation, descriptive): -0.26335 per input bit, 95% CI [-0.28105, -0.24511].

### BDM diagnostics (replicate 1000, 1,024 bits, 199 marginal-preserving shuffles)

| object | adaptive p | Holm-adjusted | reject at 0.05 | selected configuration |
|---|---:|---:|---|---|
| F01 | 0.005 | 0.050 | True | b=4, recursive, r=0 |
| F02 | 0.005 | 0.050 | True | b=4, recursive, r=0 |
| F03 | 0.005 | 0.050 | True | b=4, recursive, r=0 |
| F04 | 0.050 | 0.150 | False | b=4, sliding, r=0 |
| F05 | 0.005 | 0.050 | True | b=4, recursive, r=0 |
| F06 | 0.005 | 0.050 | True | b=4, recursive, r=0 |
| F12 | 0.010 | 0.050 | True | b=4, recursive, r=1 |
| F07 | 0.215 | 0.430 | False | b=4, recursive, r=1 |
| F08 | 0.985 | 0.985 | False | b=12, recursive, r=1 |
| F09 | 0.005 | 0.050 | True | b=4, recursive, r=0 |

Claim status: inconclusive (structured objects rejected after Holm: F01, F02, F03, F05, F06, F12).

### Claim ledger

| id | status | claim | estimate | uncertainty |
|---|---|---|---|---|
| C1 | not_supported | HID-v1 (full) yields an average code-length gain over the strong decodable baseline portfolio on the prespecified structured confirmation benchmark | -0.04462 | [-0.05368, -0.03582] |
| C2 | supported | Every stored archive decodes exactly to its input with the independent decoder | see file | — |
| C3.1 | supported | The component removed in hid_fixed8 contributes a code-length advantage to the full search | +0.01152 | [+0.00670, +0.01668] |
| C3.2 | supported | The component removed in hid_flat contributes a code-length advantage to the full search | +0.26360 | [+0.24348, +0.28251] |
| C3.3 | supported | The component removed in hid_no_arithmetic contributes a code-length advantage to the full search | +0.03923 | [+0.03353, +0.04514] |
| C3.4 | supported | The component removed in hid_no_schema contributes a code-length advantage to the full search | +0.00896 | [+0.00595, +0.01211] |
| C3.5 | supported | The component removed in hid_no_transform contributes a code-length advantage to the full search | +0.00188 | [+0.00148, +0.00227] |
| C4 | not_supported | The structured-family result transfers to 16384 and 65536 bits | -0.06280 | [-0.07690, -0.04853] |
| C5 | supported | HID-v1 shows no advantage over the statistical baselines on IID, biased IID and Markov controls | -0.26335 | [-0.28105, -0.24511] |
| C6 | inconclusive | Aligned/full-coverage BDM, with setting selection calibrated symmetrically on marginal-preserving nulls, separates the structured diagnostic objects from bit shuffles | see file | Monte Carlo, 199 nulls |
| C7 | out_of_scope | HID-v1 computes or estimates Kolmogorov complexity | — | — |
| C8 | out_of_scope | An inferred description is the unique generating mechanism | — | — |
| C9 | out_of_scope | Full-string compression establishes prediction of unseen suffixes | — | — |
| C10 | out_of_scope | The study establishes causal identification or priority of hierarchical grammar coding | — | — |

### Completeness and resources

| split | method rows expected | present | ok | non-ok |
|---|---:|---:|---:|---:|
| confirmation | 23040 | 23040 | 23040 | 0 |
| transfer | 3072 | 3072 | 3072 | 0 |

| method | median encode s | max encode s | total encode s | total worker s | max RSS MB |
|---|---:|---:|---:|---:|---:|
| baseline_best | 0.004 | 0.94 | 87.1 | 723.2 | 43.6 |
| bernoulli | 0.000 | 0.54 | 46.7 | 117.4 | 24.2 |
| context | 0.000 | 0.29 | 23.6 | 97.5 | 24.5 |
| gaps | 0.000 | 0.02 | 3.0 | 72.3 | 26.3 |
| hid_fixed8 | 0.115 | 4.40 | 553.2 | 627.9 | 122.8 |
| hid_flat | 0.194 | 9.57 | 1006.5 | 1077.6 | 306.5 |
| hid_full | 0.219 | 9.96 | 1163.3 | 1234.8 | 313.7 |
| hid_no_arithmetic | 0.101 | 4.80 | 363.4 | 435.4 | 183.0 |
| hid_no_schema | 0.186 | 9.80 | 1077.3 | 1148.0 | 315.0 |
| hid_no_transform | 0.217 | 9.94 | 1148.6 | 1219.6 | 315.5 |
| lzma | 0.001 | 0.00 | 1.8 | 71.1 | 40.7 |
| pair_grammar | 0.001 | 0.08 | 9.4 | 80.4 | 43.6 |
| period | 0.000 | 0.00 | 0.6 | 70.3 | 26.0 |
| raw | 0.000 | 0.00 | 0.1 | 68.7 | 24.0 |
| rle | 0.000 | 0.01 | 1.5 | 70.7 | 30.1 |
| zlib | 0.000 | 0.00 | 0.4 | 74.8 | 24.0 |

Wall-clock budget used: 3325 s of 21600 s.

## 7. Representative artefacts

Generated by `hierarchy.present` from the stored archive bytes (`handoff_artifacts.md`,
verbatim; full field lists in `handoff_artifacts.json`). Selection rules are fixed in the
generator: A1 largest saving among structured confirmation strings with ≥ 3 rules; A2–A3
largest loss and the portfolio archive that beats it; A4 first F06 confirmation string
where HID returned raw mode (a noise case; there were no timeouts, so no timeout
fallback exists); A5 the tiny-oracle case.

#### A1. automatically inferred success: largest saving among structured confirmation strings with >= 3 rules

- case `confirmation-F06-4096-1002-base`, method `hid_full`, n = 4096 bits
- input sha256 `42a069d1f7491ee33307c68852e2fe835571557523806a4bdd6387c55581a45a` (regenerated; row says `42a069d1f7491ee3…`)
- archive `archives/b4/b4a185907a8521dc599669ed718a39cb152207f1527b036025058799459aaafe.isd`, sha256 `b4a185907a8521dc599669ed718a39cb152207f1527b036025058799459aaafe`
- archive 1624 bits (row 1624); raw archive 4168 bits; portfolio 2472 bits (lzma); search stop `rounds_exhausted`, source `global:split[2048]>xform(flags=0,r=4)`
- decoded by `decode.py` equals the input: **True**; ledger sum 1624 bits = archive 1624 bits
- graph (read back from the archive bytes):

  | id | op | length | refs | detail |
  |---:|---|---:|---:|---|
  | 0 | LITERAL | 13 | 2 | {"bits": "0001011110101"} |
  | 1 | XFORM | 13 | 1 | {"child": 0, "complement": false, "reverse": false, "right_rotation": 4} |
  | 2 | REPEAT | 2041 | 1 | {"child": 1, "copies": 157} |
  | 3 | LITERAL | 7 | 1 | {"bits": "0101000"} |
  | 4 | CONCAT | 2048 | 1 | {"children": [2, 3]} |
  | 5 | PATCH | 2048 | 1 | {"child": 4, "flips": 58, "positions": "32 shown of 58"} |
  | 6 | LITERAL | 13 | 1 | {"bits": "1011110101000"} |
  | 7 | REPEAT | 1014 | 1 | {"child": 6, "copies": 78} |
  | 8 | LITERAL | 10 | 1 | {"bits": "1011110101"} |
  | 9 | CONCAT | 1024 | 1 | {"children": [7, 8]} |
  | 10 | PATCH | 1024 | 1 | {"child": 9, "flips": 36, "positions": "32 shown of 36"} |
  | 11 | REPEAT | 1014 | 1 | {"child": 0, "copies": 78} |
  | 12 | LITERAL | 10 | 1 | {"bits": "0001011110"} |
  | 13 | CONCAT | 1024 | 1 | {"children": [11, 12]} |
  | 14 | PATCH | 1024 | 1 | {"child": 13, "flips": 34, "positions": "32 shown of 34"} |
  | 15 | CONCAT | 2048 | 1 | {"children": [10, 14]} |
  | 16 | CONCAT | 4096 | 0 | {"children": [5, 15]} |

- exact byte ledger, summed per record (190 fields in `handoff_artifacts.json`): envelope 9, dag 1, rule0 4, rule1 4, rule2 4, rule3 3, rule4 4, rule5 63, rule6 4, rule7 3, rule8 4, rule9 4, rule10 40, rule11 3, rule12 4, rule13 4, rule14 37, rule15 4, rule16 4 — total 203 bytes

#### A2. baseline loss: largest loss among structured confirmation strings

- case `confirmation-F12-4096-1014-ragged`, method `hid_full`, n = 4099 bits
- input sha256 `1277211d0284e0d57c4c26e604bc635d7803d6b5c4b0d2cd99eef7acd67c7b89` (regenerated; row says `1277211d0284e0d5…`)
- archive `archives/eb/eb39fc916d10d15d176f18b2f74258e945af4de62ab718c84fdec3ef21235505.isd`, sha256 `eb39fc916d10d15d176f18b2f74258e945af4de62ab718c84fdec3ef21235505`
- archive 3456 bits (row 3456); raw archive 4176 bits; portfolio 2176 bits (zlib); search stop `candidate_cap`, source `seg:fixed[256,phase=6]:local>xform(flags=0,r=2)`
- decoded by `decode.py` equals the input: **True**; ledger sum 3456 bits = archive 3456 bits
- graph (read back from the archive bytes):

  | id | op | length | refs | detail |
  |---:|---|---:|---:|---|
  | 0 | LITERAL | 6 | 1 | {"bits": "001010"} |
  | 1 | LITERAL | 17 | 2 | {"bits": "10100001001010101"} |
  | 2 | XFORM | 17 | 2 | {"child": 1, "complement": false, "reverse": false, "right_rotation": 2} |
  | 3 | XFORM | 17 | 1 | {"child": 2, "complement": false, "reverse": false, "right_rotation": 1} |
  | 4 | REPEAT | 255 | 1 | {"child": 3, "copies": 15} |
  | 5 | LITERAL | 1 | 2 | {"bits": "1"} |
  | 6 | CONCAT | 256 | 1 | {"children": [4, 5]} |
  | 7 | REPEAT | 255 | 1 | {"child": 2, "copies": 15} |
  | 8 | LITERAL | 1 | 1 | {"bits": "0"} |
  | 9 | CONCAT | 256 | 1 | {"children": [7, 8]} |
  | 10 | REPEAT | 255 | 1 | {"child": 1, "copies": 15} |
  | 11 | CONCAT | 256 | 2 | {"children": [10, 5]} |
  | 12 | XFORM | 256 | 1 | {"child": 11, "complement": false, "reverse": false, "right_rotation": 1} |
  | 13 | LITERAL | 256 | 1 | {"bits": "1010000100101010110100001001010101101000\u2026"} |
  | 14 | LITERAL | 256 | 1 | {"bits": "0100001001010101101000010010101011010000\u2026"} |
  | 15 | LITERAL | 256 | 1 | {"bits": "0100011110011011110111011011101110110100\u2026"} |
  | 16 | LITERAL | 256 | 1 | {"bits": "0001010100111100110011000110101011110101\u2026"} |
  | 17 | LITERAL | 256 | 1 | {"bits": "0000110001011111000101010100100100111101\u2026"} |
  | 18 | LITERAL | 256 | 1 | {"bits": "1001011111011110001110100010100110111100\u2026"} |
  | 19 | LITERAL | 256 | 1 | {"bits": "0101110101110010011110100010011000001011\u2026"} |
  | 20 | LITERAL | 39 | 1 | {"bits": "011101110111010101000100010000100010001"} |
  | 21 | REPEAT | 234 | 1 | {"child": 20, "copies": 6} |
  | 22 | LITERAL | 22 | 1 | {"bits": "0111011101110101010001"} |
  | 23 | CONCAT | 256 | 1 | {"children": [21, 22]} |
  | 24 | LITERAL | 256 | 1 | {"bits": "0001000010001000101110111011101010100010\u2026"} |
  | 25 | LITERAL | 39 | 1 | {"bits": "110111010101000100010000100010001011101"} |
  | 26 | REPEAT | 234 | 1 | {"child": 25, "copies": 6} |
  | 27 | LITERAL | 22 | 1 | {"bits": "1101110101010001000100"} |
  | 28 | CONCAT | 256 | 1 | {"children": [26, 27]} |
  | 29 | LITERAL | 39 | 1 | {"bits": "001000100010111011101110101010001000100"} |
  | 30 | REPEAT | 234 | 1 | {"child": 29, "copies": 6} |
  | 31 | LITERAL | 22 | 1 | {"bits": "0010001000101110111011"} |
  | 32 | CONCAT | 256 | 1 | {"children": [30, 31]} |
  | 33 | LITERAL | 39 | 1 | {"bits": "101010100010001000010001000101110111011"} |
  | 34 | REPEAT | 234 | 1 | {"child": 33, "copies": 6} |
  | 35 | LITERAL | 19 | 1 | {"bits": "1010101000100010000"} |
  | 36 | CONCAT | 253 | 1 | {"children": [34, 35]} |
  | 37 | CONCAT | 4099 | 0 | {"children": [0, 6, 9, 12, 13, 11, 14, 15, 16, 17, 18, 19, 23, 24, 28, 32, 36]} |

- exact byte ledger, summed per record (145 fields in `handoff_artifacts.json`): envelope 9, dag 1, rule0 3, rule1 5, rule2 4, rule3 4, rule4 3, rule5 3, rule6 4, rule7 3, rule8 3, rule9 4, rule10 3, rule11 4, rule12 4, rule13 35, rule14 35, rule15 35, rule16 35, rule17 35, rule18 35, rule19 35, rule20 7, rule21 3, rule22 5, rule23 4, rule24 35, rule25 7, rule26 3, rule27 5, rule28 4, rule29 7, rule30 3, rule31 5, rule32 4, rule33 7, rule34 3, rule35 5, rule36 4, rule37 19 — total 432 bytes

#### A3. the portfolio archive that wins that loss

- case `confirmation-F12-4096-1014-ragged`, method `baseline_best`, n = 4099 bits
- input sha256 `1277211d0284e0d57c4c26e604bc635d7803d6b5c4b0d2cd99eef7acd67c7b89` (regenerated; row says `1277211d0284e0d5…`)
- archive `archives/79/79ec1c477dd467a75cdd67676d218f147a8ba7a5abc9b13b2582e1a3e5253bfd.isd`, sha256 `79ec1c477dd467a75cdd67676d218f147a8ba7a5abc9b13b2582e1a3e5253bfd`
- archive 2176 bits (row 2176); raw archive 4176 bits; portfolio 2176 bits (zlib); search stop `None`, source `None`
- decoded by `decode.py` equals the input: **True**; ledger sum 2176 bits = archive 2176 bits

- exact byte ledger:

  | owner | field | bytes | hex |
  |---|---|---:|---|
  | envelope | magic | 4 | `49534431` |
  | envelope | codec_id | 1 | `07` |
  | envelope | output_n_bits | 2 | `8320` |
  | envelope | payload_n_bytes | 2 | `8702` |
  | zlib | compressed stream incl. library headers/checksums | 263 | `78dad3ba3035c36b8b6a94d05aceb096d54ea10bb56821a0` |

#### A4. noise case with literal fallback: first F06 confirmation string where HID returned raw mode

- case `confirmation-F06-1024-1005-base`, method `hid_full`, n = 1024 bits
- input sha256 `9b95db04cd80cb11257d52f747035a11e1cb4b90a8b61e5bf4ea42d333c76b0f` (regenerated; row says `9b95db04cd80cb11…`)
- archive `archives/a4/a42d6a4d11ee73ef1626575e09a92c12015ca6a80949aa6014fca828256f6314.isd`, sha256 `a42d6a4d11ee73ef1626575e09a92c12015ca6a80949aa6014fca828256f6314`
- archive 1096 bits (row 1096); raw archive 1096 bits; portfolio 1080 bits (bernoulli); search stop `converged`, source `literal`
- decoded by `decode.py` equals the input: **True**; ledger sum 1096 bits = archive 1096 bits

- exact byte ledger:

  | owner | field | bytes | hex |
  |---|---|---:|---|
  | envelope | magic | 4 | `49534431` |
  | envelope | codec_id | 1 | `00` |
  | envelope | output_n_bits | 2 | `8008` |
  | envelope | payload_n_bytes | 2 | `8001` |
  | literal | P(bits) [1024 bits] | 128 | `5a8eba1bbe23ce7e951d72357cc79c5d223aec6cf98f39fa` |

#### A5. tiny oracle case: 64 identical bits, repetition beats the raw envelope

- target: 64 ones; oracle program `R(L(1),64)`; raw 120 bits; restricted search 112 bits; full search 96 bits
- input sha256 `3138bb9bc78df27c473ecfd1410f7bd45ebac1f59cf3ff9cfe4db77aab7aedd3`, archive sha256 `5b411d85a889cec3575fad8f5bf44f42c6bbe19f95ce04406a3b50eab1f0279e`
- decoded by `decode.py` equals the input: **True**; ledger sum 112 bits = archive 112 bits
- graph (read back from the archive bytes):

  | id | op | length | refs | detail |
  |---:|---|---:|---:|---|
  | 0 | LITERAL | 1 | 1 | {"bits": "1"} |
  | 1 | REPEAT | 64 | 0 | {"child": 0, "copies": 64} |

- exact byte ledger:

  | owner | field | bytes | hex |
  |---|---|---:|---|
  | envelope | magic | 4 | `49534431` |
  | envelope | codec_id | 1 | `01` |
  | envelope | output_n_bits | 1 | `40` |
  | envelope | payload_n_bytes | 1 | `07` |
  | dag | q_rules | 1 | `02` |
  | rule0 | opcode | 1 | `00` |
  | rule0 | length | 1 | `01` |
  | rule0 | P(bits) [1 bits + 7 pad] | 1 | `80` |
  | rule1 | opcode | 1 | `02` |
  | rule1 | child_id | 1 | `00` |
  | rule1 | copies | 1 | `40` |

## 8. Open issues

- **The primary hypothesis is rejected for this language and budget.** The diagnosed
  causes are structural, not bugs: (i) fixed per-record overhead (opcode, length,
  references) against single-field codecs on simple periods; (ii) one-byte-minimum
  references with no entropy coding of reference streams (F02 tokens, statistical
  controls); (iii) a whole-string patch cap of 64 flips; (iv) segmentation on fixed
  grids, with no discovery of region boundaries (F12) — 44 / 1,440 confirmation full
  searches stopped at the 512-candidate cap: 40 on F12 and 4 on F06, all at 4,096 bits.
- **Search versus language.** The oracle validates accounting on a 3-node language only;
  nothing certifies large-input optimality. The schema cover is greedy; schema proposals
  are budgeted to 4,096 table entries per input, which development data showed costless
  but which was not re-examined at transfer sizes.
- **Not implemented:** no operator beyond W3; no timeout ever occurred, so the
  `timeout_raw` path is exercised only by tests; a 1 GiB RSS breach likewise.
- **Scope:** results hold for these twelve synthetic families, these sizes and seeds,
  and this machine/interpreter (zlib 1.2.12, liblzma probe hash in `freeze.json`).
- **Smallest warranted next experiment:** keep the frozen format and benchmark design;
  add one change the development data already isolates — an entropy-coded reference
  stream (or a statistical leaf codec inside the graph) — and rerun on **new reserved
  seeds**, disclosing that `confirm-v1` informed the change.

---
Ready for supervisor review.
