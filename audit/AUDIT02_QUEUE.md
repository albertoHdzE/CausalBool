# AUDIT02 — remaining work, queued (opened 2026-09-02)

Every item that is open at the close of AUDIT02/P9, in execution order. Ids are
stable; nothing here is invented, each traces to a plan, a protocol, or a
recorded finding.

## Q1 — arm-1 reproducibility sweep (EXECUTING NOW)

The audit so far graded the *our-method* arms. This grades the other sense the
author asked for: **do the committed replication results still regenerate from
current code?**

Provenance precondition, established before running anything: all **85**
committed artefacts across the five packages map to a producer script;
**zero orphans**. So every number is in principle re-derivable, and the only
open question is whether it still re-derives to the same value.

Method, per artefact: re-run the producer into a scratch directory, compare to
the committed file **elementwise** (U8 — which keys/rows differ, never a count
alone). Floats compared at the precision the artefact itself stores.

Outcomes declared in advance:
- **identical** → artefact is live and reproducible.
- **differs** → finding. Either the code drifted from the artefact (artefact
  stale) or the producer is non-deterministic (seed leak). Both are reportable;
  neither is fixed by regenerating silently.
- **will not run** → finding: the artefact cannot be defended.

## Q2 — carried scientific opens (author-gated, not mine to close)

| id | item | why it is open |
|---|---|---|
| Q2.1 | Rule 232 is multiplicity-3 in A3.3 RS-A (`MAJORITY{strict}`, `KOFN{k:1,strict}`, `KOFN{k:2}` all `@[1,2,3]`) while C3 accepts on tuple equality | raised, not adopted |
| Q2.2 | calibration v2 unreconciled — my independent MC runs high, Stouffer z=+3.27, p≈0.001; `E[raw hits\|7000]` 1.17 vs 1.76 | two estimates of one quantity disagree |
| Q2.3 | rule 110 not re-designated as the AC-R4-4 out-of-frame refusal control | AC-R4-4 still lacks a natural case |
| Q2.4 | **P9 adjudication** — CA arm reports 10/10 on a criterion 256/256 can pass | pre-registered artefact; §5.4 forbids my editing it |

## Q3 — plan tasks never started

| id | item | source |
|---|---|---|
| Q3.1 | W0.1 ORDERING §7 migration (BioExperiments → LSB-canonical) | SUCCESSOR_PLAN_R4 Wave 0 |
| Q3.2 | W0.2 F36 exception coverage (Comparison.m / OnPossibleBehaviour.m) | SUCCESSOR_PLAN_R4 Wave 0 |
| Q3.3 | W0.5 artefact wiring — 5 PENDING groups need `.tex` markers, `checks` entries, real ids (`id: null` violates the file's own rule) | adopted AUDIT02/P6 |
| Q3.4 | W1.1–W1.5 R4 instrument | SUCCESSOR_PLAN_R4 Wave 1 |
| Q3.5 | intake queue: n>16 trajectory-route validation; regeneration producers for "re-runnable" FINDINGS rows; R1/R3 application arms; OEIS thread | SUCCESSOR_PLAN_R4 |

## Q4 — known, owned, not defects

- `TopologiesTests` — sole red in the MUnit ledger, owned.
- 512 multi-valued + 407 threshold formulas unevaluable **by construction**;
  they now refuse rather than fabricate (AUDIT02/H).
- `GOVERNANCE/GLOSSARY.md:236` cites a pre-archive path; the fix belongs in the
  sibling `series-deconvolution`, not here (editing it here breaks the sync gate).
