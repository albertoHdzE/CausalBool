# Erratum R1 — supplied-boundary gap medians, `search-confirm-v2-r1`

Date: 2026-10-03. Scope: **diagnostic only**. Machine-readable record:
`diagnostic_median_erratum.json` (sha256 `1669a3e5…`), derived by
`scripts/derive_median_erratum.py` (sha256 `903ffa55…`).

Run `search-confirm-v2-r1`, freeze
`0f0a72ef2f9d9faac406b6d18594a45ba9dc71ff1d0331f38c6a3fead68e1d49`.

## What was wrong

`diagnostics.json#supplied_boundary_references.by_cell[*].gap_median` was written by
the frozen `hierarchy/diagnostics_v2.py` (sha256 `a73d0650…`, line 167) as
`g[len(g) // 2]`. For an even number of gaps that is the upper of the two middle
order statistics, not the sample median. All eight cells hold an even number of
gaps (8, 16 or 40), so all eight were exposed. In three of them the two middle
values coincide and the stored figure happens to be correct.

## Corrected values

Gap = (bits(hid_full) − min(bits(reference), bits(raw))) / n, in bits per input bit;
negative means the automatic archive is shorter. Corrected median = mean of the two
middle values.

| Cell | n | Two middle gaps | Stored median | Corrected median | Status |
|---|---:|---|---:|---:|---|
| confirmation F12 256 | 40 | 0.0, 0.0 | 0.0 | 0.0 | unchanged |
| confirmation F12 1,024 | 40 | −0.062317429406037 (both) | −0.062317429406037 | −0.062317429406037 | unchanged |
| confirmation F12 4,096 | 40 | 0.076171875 (both) | 0.076171875 | 0.076171875 | unchanged |
| transfer F12 16,384 | 8 | 0.11669921875, 0.1196070055531824 | 0.1196070055531824 | **0.1181531121515912** | corrected |
| transfer F12 65,536 | 8 | 0.09032789636704863, 0.09033203125 | 0.09033203125 | **0.09032996380852432** | corrected |
| transfer F12 131,072 | 8 | 0.08343505859375, 0.0834941827198169 | 0.0834941827198169 | **0.08346462065678345** | corrected |
| stress S02 4,096 | 16 | −0.023420346425957552, −0.021484375 | −0.021484375 | **−0.022452360712978778** | corrected |
| stress S02 65,536 | 16 | 0.00048825889928134393, 0.008422466012603182 | 0.008422466012603182 | **0.004455362455942263** | corrected |

These are the same five cells and values as the supervisor's
`supervision/diagnostic_audit.json`; the derivation fails if they disagree. The sign of
every median is unchanged. The largest change is S02 at 65,536 bits, where the corrected
median is about half the stored one (0.0045 against 0.0084). In that cell the two middle
gaps are far apart (0.0005 and 0.0084), and it is the cell whose automatic archive is
shorter than the reference on 7 of 16 strings.

## What was checked and is unchanged

- `references.json` (sha256 `937940b6…`) is the file `diagnostics.json` names. For all
  176 of its 176 records: the archive sha256 matches, 8 × bytes equals `reference_bits`,
  the frozen decoder recovers a string of `n_bits` whose sha256 equals the case's
  recorded `input_sha256`, the `hid_full`/`hid_global`/`hid_legacy` bits equal
  `cases.jsonl`, `raw_bits` equals the row's `raw_archive_bits`, and the stored gap
  recomputes exactly. No partition was rebuilt and no string was generated.
- For every cell: membership (case IDs), `strings`, `available`, `gap_mean`, and the
  shorter/longer/tie counts are exactly equal to the original `diagnostics.json`.
- The corrected medians are produced by the repaired owner
  (`diagnostics_v2.boundary_gap_summary`, isolated patch, sha256 `a89e9585…`). An
  independent `statistics.median` in the derivation script must match it exactly.

## What this does not touch

The primary estimate, its interval and gates, the five contrasts, the descriptive
transfer/stress summaries, the mean boundary gaps, and every row, archive, summary and
claim are untouched. The original `diagnostics.json` and `references.json` remain
byte-identical (`baseline/preservation_after.json`). This erratum is not a new run and
not a replication. The scientific verdict is still **inconclusive**.
