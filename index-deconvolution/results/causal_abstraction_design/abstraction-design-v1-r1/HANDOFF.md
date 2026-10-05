# HANDOFF — `abstraction-design-v1-r1`

**Status: ready for Codex review; not yet accepted.**

Design-only phase executing `causal_target_v1/supervision/causal-target-spec-v1-r1-closure/NEXT_CLAUDE.md`.
No experiment was implemented, run, partially implemented or scheduled. No commit, push or
recurring task. Only hashing and JSON parse checks ran.

## Deliverables

| file | content |
|---|---|
| `DESIGN.md` | question, four separated tracks (V supplied, D induced discovery, X cross-check, G gap ranking), endpoints E1–E8, failure precedence, success/failure meaning, hand derivations §A |
| `MODEL_AND_MAPS.md` | encoding, models M1–M4, timing, family A with counts, structural β, controls P1–P4/N1–N3/C1–C2, calibrations |
| `EVIDENCE_AND_LIMITS.md` | sources and sections inspected, literature status, novelty (none claimed), limits |
| `DECISION.md` | choices, rejected alternative, open questions |
| `DRAFT_EXECUTION_PROTOCOL.md` | **NOT AUTHORIZED FOR EXECUTION** |
| `input_manifest.json`, `output_manifest.json`, `preservation_before.json`, `preservation_after.json`, `attempts.jsonl`, `time_ledger.jsonl` | records |

## Key numbers (all by hand from declarations)

Models 4, states 1,792; candidates 135 (n=8) / 141 (n=10); (α, τ) pairs 2,730; |Q| = 42 / 52;
exhaustive pair checks 59,312,640; Track V 30,976 pairs with 2,080 expected failures;
H-M1-τ 405, H-M2-F3 75 of 150; X 630 F3 pairs.

## Points for the reviewer

1. Hand derivations in `DESIGN.md` §A (P1, N1, P4, counter controls) are mathematical
   inspection, not tests. A3 records a slip caught and withdrawn in N3.
2. The literature on ECA coarse-graining (Israeli–Goldenfeld; Song–Grochow) was checked only
   through search summaries; Kemeny–Snell, Lind–Marcus, Naldi et al. are unverified.
3. M1 degenerates at τ ≥ 4 (F⁴ = 1); this is used as a calibration, not hidden.
4. The abstraction-checker has no owner in the core; the draft requires a ticket and owner
   decision before code.
5. Notebook19 and build_19 hashes equal the closure's recorded hashes (no drift); both remain
   untracked in git, so there is no git baseline for them.

## Time

Wall from start to handoff in `time_ledger.jsonl` (allowance 1,500 s for this executor; 300 s
reserved for Codex). Nothing transferred from earlier phases.
