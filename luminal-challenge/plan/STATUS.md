# Luminal direct-index task status

Canonical contract: [INDEX_ONLY_PLAN.md](INDEX_ONLY_PLAN.md), version **1.0**.
Last updated: **2026-09-19**.

The current request is to persist the plan, not to implement the new compiler.
The older hybrid prototype and its passing checks do not count as completion of
the direct-index implementation tasks below.

| Task | State | Owner | Evidence / next action |
|---|---|---|---|
| L00 — persistent contract and navigation | READY_FOR_REVIEW | Lead | Plan, agent instructions, status, and README links written; document audit pending |
| L01 — direct schema algebra and solver | PENDING | Unassigned | Await implementation authorization and L00 acceptance |
| L02 — machine facts and independent corpus | PENDING | Unassigned | Await implementation authorization and L00 acceptance |
| L03 — comparisons and joint constraints | PENDING | Unassigned | Requires L01/L02 acceptance |
| L04 — independent bootstrap compiler | PENDING | Unassigned | Requires L01/L02 acceptance |
| L05 — joint optimization | PENDING | Unassigned | Requires L03/L04 acceptance |
| L06 — packaging and verification runners | PENDING | Unassigned | Requires frozen L04 interfaces; final gate requires L05 |
| L07 — integration and independent review | PENDING | Lead | Requires all implementation gates |

## Required task record when work starts

For each active task append: task ID, plan version, owner/model, exclusive files,
accepted dependencies and evidence paths, actual commands and exit codes,
source hashes, limitations, elapsed work time, and lead review verdict. Workers
may report READY_FOR_REVIEW; only the lead sets ACCEPTED.

## Version and decision log

- **1.0 / 2026-09-19:** persisted the approved plan with explicit arithmetic,
  command, test-corpus, evidence, delegation, and independent-review contracts.
  User-selected boundaries: direct schemata, incremental index construction,
  correctness/runtime/serial improvement required, classical comparison reported.
  No new compiler implementation or benchmark result is claimed.
