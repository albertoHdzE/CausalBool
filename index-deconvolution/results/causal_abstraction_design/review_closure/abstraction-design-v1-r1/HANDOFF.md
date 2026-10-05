# HANDOFF — closure of REVIEW R1–R3, `abstraction-design-v1-r1`

**Status: ready for Codex review; not yet accepted.**
The corrected draft remains **NOT AUTHORIZED FOR EXECUTION**. Document-only: no experiment,
checker, simulator, enumeration, notebook or gap ranking was implemented or run. No source, core
or governance file edited. No commit, push or recurring task.

## Deliverables (this directory)
| file | content |
|---|---|
| `corrected/DESIGN.md` | tracks re-scoped; endpoints E1–E8 with intended/inspected/evaluable pairs; decision table §5.1; coarse labels §5.2; §6 scoped to A/Q/β; G population and pooling |
| `corrected/MODEL_AND_MAPS.md` | β_fine (local positions), H-COARSE, H-OUT, representative rule, R1 counterexample, fixtures FX-R1a/b/c, FX-REP; canonical ids and row ids; X restricted |
| `corrected/EVIDENCE_AND_LIMITS.md`, `corrected/DECISION.md` | owner paths, literature per REVIEW, limits 3, 8–10 |
| `corrected/DRAFT_EXECUTION_PROTOCOL.md` | **NOT AUTHORIZED FOR EXECUTION**; imports, tests, freeze, audit 273/2,730, proposed budget |
| `CHANGELOG.md`, `OWNERSHIP_TICKET.md` | changes per finding; proposed owner `index-deconvolution/src/deconvolution.py` |
| manifests, preservation, `attempts.jsonl`, `time_ledger.jsonl` | records |

## Counts (hand, from declarations)
Unchanged: 4 models, 1,792 states, 135/141 candidates, 2,730 rows, |Q| 42/52, 59,312,640 pair
checks, Track V 30,976 pairs / 2,080 expected failures, H-M1-τ 405, H-M2-F3 75/150, X 630.
New: audit 273 of 2,730; G population N = 124 / 130.

## Remaining blockers (none blocks review; all block execution)
1. Ownership ticket must be accepted before code.
2. **U2**: no block-value occurrence extractor in `../series-deconvolution/src/seqdecon/operators.py`
   (upstream ticket needed). **U3**: no declared import route to that sibling package. Both block
   Track G only.
3. Execution budget is a proposal (2,160 s + 300 s reserve); requires separate authorization.

## Points for the reviewer
- Hand proofs (R1 counterexample, FX expectations) were not run; only witnesses are stated.
- Import route corrected mid-pass (attempt B3); preservation-before taken late (B4), honestly disclosed.
- Preservation: 73 files, changed after vs before: 0.

## Time
Executor 294 s of the 462 s maximum at handoff; 300 s reserved for Codex. Prior charges
1,038 / 1,800 s unchanged; this pass adds 294 s.
