# HANDOFF — closure of review R1/R2, representation-review-v1-r1

**Status: ready for Codex review; not yet accepted.**

Executor: Claude Code, 2026-10-04. Instructions read:
`supervision/representation-review-v1-r1/CLOSURE_CLAUDE.md` and `REVIEW.md` (both
hashed in the closure manifest). Prose and audit closure only: no encoder, generator,
fixture corpus, notebook execution, archive creation, cap change or new experiment.
Nothing committed, pushed, published or scheduled. Only this new directory was written;
the original synthesis run, its failed attempt, the supervision directory, every older
run, owner source and notebook are untouched (manifest compare below).

## R1 — corrected prose (`SYNTHESIS.md`, closure copy; original preserved)

* §5 keeps **STOP**, now as a research-priority judgment grounded in zero observed
  retained gain (0 of 96 strings shorter than A0 for best R or best O), ties reached
  only by operations k = 1 already has, and the cost of further work. It says "A0
  selected a raw literal" (30 strings), not "incompressible"; it states that stronger
  search under the unchanged HID-v1 format is **untested, not impossible**, and that the
  evidence does not show a representation change is necessary. The claim that H2's
  per-word optimum is the only discriminating experiment, and the remark on fresh
  confirmation, are withdrawn; no fresh confirmation is prescribed for an extension
  with no gain. No next encoder protocol is proposed.
* §4 H1: the saved ledgers support a declared descriptive inequality on component
  tables without a new archive; correlation of reference bytes with total length is
  accounting, not a causal falsifier; the absence of a controlled intervention is named
  as a separate limitation. H2: independent per-word minima need not minimize a shared
  DAG's cost; an oracle would be a joint full-archive optimization over a declared
  finite set, and its conclusion would cover that set only. No oracle implemented.
* §3 separates **source capabilities** (code only) from **saved-archive witnesses**. A
  CONCAT rule does not certify shared grammar reuse or the search path; segmentation
  has no archive witness and is labelled a code-only capability. No inference was run.
* §2 now states the original audit's real coverage and the original manifest's
  omission of the raw archives.

## R2 — revised independent audit (`closure_audit.py`)

Imports neither synthesis script nor the supervisor's `audit_review.py`; shared owners
by intention: `hierarchy.decode.decode_archive`, `hierarchy.ledger.archive_ledger`,
`hierarchy.codes.OP_NAMES`. It restates the synthesis's declared quantile definition
(`v[n//4]`, `statistics.median`, `v[3n//4]`) rather than a new estimator.

Real data (`closure_audit_result.json`, `closure_audit_attempt02.log`) — **pass**:

| check | result |
|---|---|
| exact case set (enforced before any comparison) | 96 rows, 0 duplicates, 0 missing, 0 extra |
| raw archive sha256 vs CASES pin; decoded n and input sha256 vs CASES | 96 / 96 each |
| A0 hash vs k = 1 pin, decodes; D2 trace hash vs row | 96 / 96 each |
| 192 selections re-made from traces by (bits, request ordinal); hash, bits, decode | 192 / 192 each |
| per-case fields: mode, proposal, ordinal, view, sha, bits, margins (bits and per input bit), identity, components and deltas, field by field | 0 mismatches |
| summary: both margin distributions with n/min/q25/median/q75/max, counts, identity, component sums and positive-case counts, modes, proposals, views, best R − best O distribution and counts, A0 codecs and rule kinds, beats-A0 | 0 mismatches |
| `per_case.csv`, `per_case_components.csv` (as multisets) | equal |

Not rechecked: `three_notions.within_view_*`, copied by the synthesis from the accepted
dictionary run's summary (outside R2).

Corruptions on in-memory copies (same result file) — each rejected by the intended check:

| corruption | failed check(s) | reason recorded |
|---|---|---|
| 8 bits moved CONCAT.refs → LITERAL.payload in F01-1024-3000-base best R (and its delta), total unchanged | `per_case_fields` only | `.R.components`, `.R.component_minus_a0`; the component-sum check **still passes**, which is the class the original audit could not catch |
| reported R margin q25 + 8 bits | `summary_all_derivable_fields` only | `R.margin_bits.q25` |
| last case replaced by a duplicate of the first | `exact_case_set`; audit stops before computing anything else | duplicate F01-1024-3000-base, missing F12-4096-3001-ragged |

Retained failed attempt: `closure-audit-01` failed real data on
`per_case_components_csv` only, because the audit assumed archive labels `R`/`O` where
the CSV writes `best_R`/`best_O`. Audit-side label assumption, not a data defect; fixed
by renaming the labels in the audit. Log and result kept (`closure_audit_attempt01.log`,
`closure_audit_result_attempt01.json`).

## Supplemental manifest (`closure_manifest.py`, `closure_manifest_{pre,post,compare}.json`)

Created at closure; it is **not** a pre-synthesis record and backdates nothing. 694
files: CASES.json; the **96 raw input archives** (96 / 96 equal their CASES
`archive_sha256` pins; 96 / 96 absent from the original manifest); all 17 original
synthesis-run files including both original manifests; the 4 supervision files; 192
A0/D2 rows; 96 traces; 259 distinct archives read (A0 plus selected, deduplicated);
27 owner sources `hierarchy/*.py`; the closure audit and manifest scripts. Every one of
the 644 files the audit actually read lies inside it (0 outside).

Original coverage versus now: the original `evidence_manifest_{pre,post}.json` hashed
11,722 files, identical pre and post, but its "all input files" omitted the 96 raw
archives both original scripts read. Those files are not edited; the omission is
recorded here, and the raw archives are verified now against the pins committed in
CASES, not against any pre-synthesis hash (none exists).

Pre versus post: 694 / 694, 0 missing, one change — `closure_audit.py` itself, from the
logged attempt-01 label fix made between the two stages. Every evidence input is
byte-identical.

## Numeric equality (`numeric_equality.py`, `numeric_equality.json`)

Selections and every derivable reported number are unchanged (R2 table above). The
prose figures not in the tables were recomputed from bytes, 8 / 8 equal: 30 raw-A0
strings in F02, F07, F08, F09, F11; their margins 408–1,608 bits with medians 484 (R)
and 456 (O); HID-A0 margins 0–4,384, medians 652 and 528; the six best-R ties at 144,
200, 440, 440, 696 and 688 bits (the F10 erratum stands); family sums XFORM +9,728,
PATCH +10,528, REPEAT +1,992, AP_UNION −2,624, SCHEMA_UNION −416. **No new numeric
defect was found.**

## Time

Allowance 1,800 s. Prior charges retained unchanged: 243 executor + 300 supervisor =
543 s. Closure cap 600 s; 300 s reserved for the next Codex review. Closure executor
time, wall clock from the first read of CLOSURE_CLAUDE.md (`time_ledger.jsonl` here;
original ledger not touched): **see the stop event in `time_ledger.jsonl`**, under
260 s, so the running total stays below 543 + 600 = 1,143 s and below the 1,443 s
ceiling including the reserve.

## Exact commands (from `index-deconvolution/`)

```
O=results/hierarchy_synthesis/review_closure/representation-review-v1-r1
../venv/bin/python -B $O/closure_manifest.py pre
PYTHONPATH=.:../src ../venv/bin/python -B $O/closure_audit.py          # exit 0 required
PYTHONPATH=.:../src:$O ../venv/bin/python -B $O/numeric_equality.py
../venv/bin/python -B $O/closure_manifest.py post
../venv/bin/python -B $O/closure_manifest.py compare
```

**Ready for Codex review; not yet accepted.**
