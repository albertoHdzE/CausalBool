# MUnit TRUE BASELINE v1 — AUDIT01/T0.2

**Date:** 2026-08-23 · **Runner:** `tests/MUnit/run-tests.sh` @ commit `ad97eb8`
(T0.1a parser wiring) · **Scope:** seven known sections + root, as hardcoded pre-T0.1b.

## Delta policy

Future suite runs diff against this ledger. **New failures block merges.** Pre-existing
failures retire only via explicit `[AUDIT01/<task-id>]` commits referencing this plan.
Baseline v2 (all discovered sections, post-T0.1b) appends a dated block below.

## Volatility exclusion (per AC-0.2a)

Comparison ignores: trailing timestamp/date lines inside any `Status*.txt` (e.g.
`mixed001FormulaVsExhaustive/Status.txt` embeds `Sat 22 Nov 2025 19:42:17`), wall-clock
fields, and this file's own Date header. Everything else must reproduce byte-identically.

## Rollup (verbatim)

```
OK=77 FAIL=10 TOTAL=87
TRUE DETAIL: FAILED=TopologiesTests.m, KOFNNetworkTests.m, IMPLIESNetworkTests.m, TSK-MIXED-002-Dispatch-Tests.m, TSK-TEST-002-PropertyTests.m, TSK-ARCH-004-Tests.m, KOFNNetworkTests.m, IMPLIESNetworkTests.m, TSK-MIXED-002-Dispatch-Tests.m, TSK-TEST-002-PropertyTests.m
```

(The historical kernel-exit rollup `OK=87 FAIL=0 TOTAL=87` is **superseded**: it measured
kernel survival, not verdicts.)

## Failure classification (6 unique; duplicates from root+section double-discovery, deduped in T0.1b)

| Test | Verdict read | Root cause (evidence) | Owner |
|---|---|---|---|
| `Analysis/KOFNNetworkTests.m` | `analysis_kofn/Status_network.txt` = FAIL | Genuine long-standing red, **silent since Feb 5 2026** under exit-code runner | UNOWNED → candidate task |
| `Analysis/IMPLIESNetworkTests.m` | `analysis_implies/Status_network_pair.txt` = FAIL | Same class: network-level index test red since Feb 5 | UNOWNED |
| `Theory/TSK-TEST-002-PropertyTests.m` | `test002/Status.txt` = FAIL | Property-test red (Φ-transport coverage gap per audit §D-gaps) | UNOWNED |
| `Mixed/TSK-MIXED-002-Dispatch-Tests.m` | UNPARSEABLE (`mixed002/Status_dispatch.txt`) | Script exports an **unevaluated** `If[Missing["KeyAbsent","error"]==0., …]`; `DispatchMetrics.json` is 0 bytes — missing-key bug in script | UNOWNED |
| `Arch/TSK-ARCH-004-Tests.m` | UNPARSEABLE (`arch4/Status.txt`) | Script exports literal code `If[StringContainsQ[$VersionString,…]]` instead of a verdict — writes its expression, never evaluates it | UNOWNED |
| `Exper/TopologiesTests.m` | NO STATUS EXPORTED | Writes to `results/exper/topologies/`, where only `RunLog.txt` exists — historic run died before the `:55` export; resolver generalized to catch this path shape (commit `ad97eb8`) | UNOWNED |

## Structural findings recorded during baselining

1. **F35 (new):** `TSK-MIXED-001-FormulaVsExhaustive.m` — the flagship verification
   script carrying the known FAIL — does not match the runner's `*Tests.m` glob and is
   therefore **never executed** by `--all`. Its recorded FAIL predates this baseline and
   lives only in its artifacts directory. T1.1 must rename it into the glob (or extend
   discovery) so the suite actually runs it.
2. Root-dir search recursively re-finds every section test, then section dirs add them
   again → partial double-count inside TOTAL=87. Cosmetic for v1; fixed by T0.1b's
   deduped discovery.
3. `results/tests/mixed001Comparison/` shows TSK-MIXED-001-Tests.m green while its
   sibling FormulaVsExhaustive variant is unrun-orphaned — the suite's green number
   includes neither the known-red nor the composed-semantics question (T1.1/D-2).

## Reproduction

```
zsh tests/MUnit/run-tests.sh          # ≈4 min wall-clock on this machine
```

Second-run determinism: verdict tokens reproduce; timestamps excluded per rule above.
