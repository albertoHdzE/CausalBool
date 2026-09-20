# Luminal direct-index task status

Canonical contract: [INDEX_ONLY_PLAN.md](INDEX_ONLY_PLAN.md), version **1.0**.
Last updated: **2026-09-19**.

The current request is to persist the plan, not to implement the new compiler.
The older hybrid prototype and its passing checks do not count as completion of
the direct-index implementation tasks below.

| Task | State | Owner | Evidence / next action |
|---|---|---|---|
| L00 — persistent contract and navigation | READY_FOR_REVIEW | Lead | Plan, agent instructions, status, and README links written; document audit pending |
| L01 — direct schema algebra and solver | READY_FOR_REVIEW | Worker (Claude Opus 5) | `schema_index.py`, 34 tests pass; see record below |
| L02 — machine facts and independent corpus | READY_FOR_REVIEW | Worker (Claude Opus 5) | `direct_contract.py`, corpus of 142; 31 tests pass; see record below |
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

## Task records

### L01 — direct schema algebra and solver

- **Plan version:** 1.0. **Owner:** worker agent, Claude Opus 5, working linearly
  without subagents at the user's instruction of 2026-09-19.
- **Exclusive files:** `schema_index.py`, `tests_direct/test_schema_index.py`.
  The shared `tests_direct/__init__.py` was created by this worker because no
  other agent is active; the lead should confirm that substitution.
- **Dependencies:** L00, which remains READY_FOR_REVIEW rather than ACCEPTED.
  Work proceeded on the user's explicit instruction to implement the plan as
  specified; the lead must still accept L00 retrospectively.
- **Command:** `PYTHONPATH=.reference:. python3 -m unittest tests_direct.test_schema_index`
  → **34 tests, OK, exit 0**, 1.83 s.
- **Source hashes (first 16):** `schema_index.py` `bb368a1c7dceaa07`;
  `tests_direct/test_schema_index.py` `1318004fb1c97559`.
- **Evidence:** intersection, difference and restriction are compared against
  explicit Python sets for **every** cube pair of widths zero through five,
  that is 66,430 pairs; differences are checked for disjointness as well as
  extensional equality; every returned SAT schema has **all** of its free-bit
  fillings confirmed against the whole query; interval covers are compared
  against integer predicates for every inclusive range at widths one to five.
- **Limitations:** the solver is a depth-first cube intersection without
  learning, so its worst case is exponential in the number of disjunctions and
  is bounded only by the declared budgets. That is reported as `UNKNOWN`.
- **Note for review:** one fixture defect was found and fixed during the run.
  The first time-budget fixture exhausted the *record* budget during
  construction, so the clock path was never exercised. It was replaced by an
  expression that is cheap to build and expensive to search.
- **Lead decision:** pending.

### L02 — machine facts and independent corpus

- **Plan version:** 1.0. **Owner:** as above.
- **Exclusive files:** `direct_contract.py`, `tests_direct/test_contract.py`,
  `tests_direct/generate_programs.py`.
- **Command:** `PYTHONPATH=.reference:. python3 -m unittest tests_direct.test_contract`
  → **31 tests, OK, exit 0**, 0.16 s.
- **Source hashes (first 16):** `direct_contract.py` `3b37ad0e7f5feb8a`;
  `tests_direct/test_contract.py` `44ac3321e492c2dd`;
  `tests_direct/generate_programs.py` `e6f56e70dab1d2b3`.
- **Corpus:** 142 programs — 8 public, 30 regression, 100 additional, 4 stress.
  Twenty additional programs per family; every program validated by the
  reference and confirmed to fit the starter allocation. The three scratch
  pressure fixtures each reach a peak live width of exactly 256 words, and the
  memory chain fixture holds at least 64 ordered pairs over at most 8 live words.
- **Ownership note:** `machine` remains the owner of every hardware fact and is
  imported, never restated. `common.py` derives four of the same quantities but
  is pinned by hash and barred from the production path by plan section 5.1, so
  the two owners coexist by declared exception. The drift is *measured*:
  `test_derived_facts_agree_elementwise_with_the_frozen_classical_helpers`
  compares predecessors, widths, lifetimes and bundles on four programs and
  finds zero disagreement.
- **Defects found and fixed during the run:** (i) `consumers` returned a
  multiset, counting an operation twice when it read one value for both
  arguments; (ii) the additional-program generator could stall once vector
  results filled the unique-allocation bound, since both the chosen opcode and
  the `const` fallback were refused. Two of my own boundary fixtures also
  asserted the wrong verdict and were corrected, not the code: one placed two
  stores in a single-slot cycle, and one claimed an address clash between
  intervals that do not overlap.
- **Limitations:** the starter-fit property is enforced by construction, by
  refusing any result that would push the unique vectors-first allocation past
  256 words. Programs needing genuine spilling are therefore outside the corpus,
  as they are outside the exercise.
- **Lead decision:** pending.

## Version and decision log

- **1.0 / 2026-09-19:** persisted the approved plan with explicit arithmetic,
  command, test-corpus, evidence, delegation, and independent-review contracts.
  User-selected boundaries: direct schemata, incremental index construction,
  correctness/runtime/serial improvement required, classical comparison reported.
  No new compiler implementation or benchmark result is claimed.
