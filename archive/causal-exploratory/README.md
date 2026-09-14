# `src/causal/` — exploratory island, retired 2026-09-02 (AUDIT02/P4e)

Archived per the project's archive policy: superseded code is preserved for
provenance, never deleted.

## What this was

`CausalBool.m` (6,296 lines) plus its companion notebooks `CausalBool.nb` and
`CausalBool.vsnb`. It shared ancestry with the live engine
`src/integration/Alpha.m` through commit `cba2eec` (2026-08-22) and then diverged:

- `Alpha.m` received `7c56dc6` (T4.1) — ORDERING fixes and the F24 stale-`resOp`
  guards.
- `CausalBool.m` received `316ce22` (T1.4) — terminology only.

Neither was a superset of the other. Nothing in the repository ever loaded
`src/causal/`: no `Get`, `<<`, or `Needs` referenced it, and the seven functions
unique to it were called only by the file itself and its own notebook.

## Why it was safe to retire

`src/integration/Alpha.m` is the engine. It is the only copy loaded
(`src/Packages/Integration/Alpha.m:5`, `Experiments.m:6`), it carries the T4.1
safety hardening, it defines `createRepertoires` and the whole `runDynamic*`
family — fourteen functions the island lacked — and it contains no technical
sense of the word "pivot".

A note on a claim that did **not** survive checking: an earlier pass of this
audit reported that T1.4's `pivot` → `decimalAnchor` / `sequenceStarts` rename had
been applied only to this dead copy, leaving the live engine stale. That was
wrong. The renamed identifiers sit inside `findPatternIndices` and
`findANDIndicesFormula`, two of the island-only functions; `Alpha.m` has zero
occurrences of `pivot = Total`, `"Pivot"` or `pivots` because it never contained
them. T1.4 was complete.

## Capability map — every equivalence demonstrated, not asserted

| island function | live counterpart | evidence |
|---|---|---|
| `combineInsIdxProducingOuts` | `combiningRepersWithSharedInputs` (`src/integration/Alpha.m:2117`) | same body, character-identical usage example `{1,3,5,6},"OR",1,{1,5,7,3},"AND",1` → `DecRep {85,117}`; live and called at `Alpha.m:2491,2499` |
| `findInputsProducingOutput` | `createRepertoireByResult` (`src/integration/Alpha.m`) | renamed; repaired in AUDIT02/P4a from 4 of 12 gate families to 12, MAJORITY now honours the requested result; 96/96 elementwise, order-sensitive |
| `v2` | — | an in-file refactor of `combineInsIdxProducingOuts`, superseded by the same counterpart. It drops the `Reverse[Reverse[#]&/@…]` the original applies, so it was not order-equivalent to its own sibling |
| `findANDIndicesFormula` | `IndexSetAnalytic` / `IndexSetNetwork` (`src/Packages/Integration/Gates.m:171,178`) | AND-only precursor; the general form covers all twelve families and matches the exhaustive baseline on 43 gate×arity pairs with zero mismatches (`AnalyticVsExhaustiveQueryTests.m`) |
| `findPatternIndices` | `PatternIndices` (`src/Packages/Integration/IndexAlgebra.m`) | equal to the brute-force scan, and equal to this original under Φ transport, over 98 (n, node-set, pattern) cases at n = 2,3,4 with zero mismatches (`PatternQueryTests.m`, claims A and B) |
| `filterByCondition` | `FilterRepertoireByOutput` (`src/Packages/Integration/IndexAlgebra.m`) | ported; its selected rows, mapped through Φ, equal `IndexSetNetwork` exactly, symmetric difference empty (`PatternQueryTests.m`, claim C) |
| `inIdxProducingOutsToDecimal` | `poweringArray` ∘ `createRepertoireByResult` (both live in `src/integration/Alpha.m`) | reproduces the documented example exactly: `{1,8},"OR",1` → `Decimal {1,128,129}`, `Binary {{1,0},{0,1},{1,1}}`. Now spans twelve gate families rather than four |

`findPatternIndices` and `filterByCondition` had **no** live counterpart before
this pass; they were ported rather than merely declared superseded, because they
are the analytic partial-pattern query and its exhaustive baseline — the pair the
manuscripts use to show that specific inputs for a specific output are obtained
in closed form rather than by enumerating 2^n.

## One open pointer, deliberately not fixed here

`GOVERNANCE/GLOSSARY.md:236` cites `src/causal/CausalBool.m findANDIndicesFormula`
and now points at this archive path instead.

It was **not** edited in place. That file is synchronised from the sibling
repository `series-deconvolution` (CLAUDE.md; `tools/check_glossary_sync.sh`
compares the two bodies and reports drift). Repointing our copy unilaterally
turned the gate red — verified: the sync check reported `GLOSSARY DRIFT` and
returned to `clean` on revert. The correct fix is to change the citation **in the
sibling** and re-synchronise, which is a cross-repository action outside this
pass.

This is a live instance of a defect this audit already recorded: the glossary
gate verifies that two *documents* mirror each other, never that either matches
the code. A companion code-conformance check is item P5.2.

## Provenance

Retirement and the evidence above are recorded in the AUDIT02 commit series on
branch `fixing`, starting at `f17e839`.
