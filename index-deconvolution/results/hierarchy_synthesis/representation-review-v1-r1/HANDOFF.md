# HANDOFF — representation review v1 (`representation-review-v1-r1`)

**Status: ready for Codex review; not yet accepted.**

Executor: Claude Code, 2026-10-04. Instruction:
`results/hierarchy_dictionary_v1/supervision/dictionary-feasibility-v1-r1/NEXT_CLAUDE.md`.
Artifact-only: no encoder run, no archive built, no cap or fixture changed, no source
package created, no notebook. Nothing committed, pushed, published or scheduled.

## Outcome

* **Recommendation: STOP** further compression-extension development of the
  multilevel/dictionary line; no `DRAFT_NEXT_PROTOCOL.md` written (SYNTHESIS §5).
* Over all 96 strings the best relation-mode candidate is longer than A0 on 90 and equal
  on 6 (one byte-identical), the best O candidate longer on 94 and equal on 2; median
  margins 628 and 516 bits. Best R beats best O on 14 strings, ties on 28, loses on 54;
  within single views R(O) beats O in 1,243 of 6,096. A0 is a raw literal on 30 strings,
  where every candidate stays ≥ 408 bits longer.
* Byte accounting (authoritative disjoint ledger partition) places the candidates'
  excess mainly in CONCAT child references and LITERAL dictionary bits; this is
  accounting, not a cause. Two hypotheses (fixed-grid envelope cost; search scope) are
  stated with observations, falsifiers, unmeasured items and minimal controls; neither is
  established.
* Capability map: the dictionary phase changed search, not representation (same HID-v1
  opcodes); k = 1 already contains REPEAT, PATCH, exact XFORM (with rotations), pair
  grammar sharing, AP/schema unions and segmentation, with saved witnesses by family.
  New in the phase: XFORM+PATCH relations to preceding words, word-period REPEAT, rigid
  multi-width/multi-level views.
* Erratum noted (frozen file not edited): the dictionary HANDOFF's "440 or 688 bits" for
  the F10 ties omits F10-4096-3000-base at 696 bits.

## Deliverables (all in this directory)

| file | content |
|---|---|
| `SYNTHESIS.md` | analysis, capability map, hypotheses, recommendation |
| `per_case.json`, `per_case.csv`, `per_case_components.csv` | all 96 cases: ids, hashes, full lengths, margins, ledger components (A0, best R, best O) |
| `summary.json` | distributions, sign counts, component sums, the three notions of improvement |
| `analysis.py` | producer (owner decoder + ledger; no encoder) |
| `audit.py`, `audit_result.json` | independent re-selection and arithmetic check: **pass, 0 problems**, 192 selections |
| `manifest.py`, `evidence_manifest_{pre,post,compare}.json` | 11,722 input files hashed before and after: 0 changed, 0 missing |
| `time_ledger.jsonl`, `analysis_attempt0{1,2}.log`, `audit_attempt01.log` | attempts and times |

Retained failed attempt: `analysis-01` classified CONCAT child ids as payload (ledger
labels are indexed, `child_id[j]`); fixed before any result was used (`analysis_attempt01.log`).

## Evidence and preservation

Inputs: the accepted dictionary and multilevel protocols, handoffs and supervisor reviews,
the accepted v3a review, CONCEPT_REVIEW, the dictionary run's summary, lock, A0/D2 rows,
D2 traces and every archive read, and the owner sources inspected (`hierarchy/{decode,
ledger,model,wire,codes,infer,search_v2,consensus,segmentation,candidates}.py`, both
experiment `search.py` files). All hashes are pinned pre and post and identical.
Notebook 19 / build_19 are hashed for the record only; no claim is made that they equal
any older snapshot. No file outside this new directory was written.

## Time

Separate allowance 1,800 s (controller wall, from the first read 23:56:15Z); executor work stopped at 243 s (`time_ledger.jsonl` stop event; this figure was filled in
after the stop and is uncharged), well inside the 1,500 s executor stop; the 300 s Codex reserve is untouched. No earlier
ledger was read for borrowing or edited.

## Exact commands (from `index-deconvolution/`)

```
O=results/hierarchy_synthesis/representation-review-v1-r1
../venv/bin/python -B $O/manifest.py pre
PYTHONPATH=.:../src ../venv/bin/python -B $O/analysis.py
PYTHONPATH=.:../src ../venv/bin/python -B $O/audit.py
../venv/bin/python -B $O/manifest.py post
```

**Ready for Codex review; not yet accepted.**
