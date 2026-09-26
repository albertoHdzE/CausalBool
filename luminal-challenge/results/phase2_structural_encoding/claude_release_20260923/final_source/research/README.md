# Phase 2 structural-encoding research system

An **isolated research path**, not a compiler change. Nothing in this package is
on the production dependency graph: `export_direct.py`, `verify_direct.py`,
`compare_direct.py` and the accepted `direct_*` modules are unchanged and none
of them imports `research`. A test asserts that last statement.

Implements plan `plan/PHASE2_STRUCTURAL_ENCODING_PLAN.md` version 2.1 under
`plan/phase2/IMPLEMENTATION_CONTRACT.md`.

## What is here

| Module | Responsibility |
|---|---|
| `structural_encoding.py` | `Domain`, fixed `layout`, `options`, `encode`/`decode`, all four codecs, canonical JSON |
| `structural_search.py` | Depth-first traversal, admissible bounds, acceptance policy |
| `structural_models.py` | Exact cover merge, the byte format, the four proposal policies |
| `structural_oracle.py` | Independent finite-domain enumeration and the hidden evaluator |
| `run_structural_experiments.py` | CLI, subprocess harness, frozen corpora, P0–P5 orchestration |
| `check_structural_evidence.py` | Independent artifact checks, gate recomputation, ownership guard |

Ownership, and the four questions the repository's single-owner law requires, are
answered in the `OWNERSHIP.md` written into every run directory. The codec's
seven proof obligations and their evidence are in that run's `PROOFS.md`.

## Running it

From `luminal-challenge`:

```bash
# the whole campaign, into a new run directory that is never overwritten
PYTHONPATH=.reference:. python3 -m research.run_structural_experiments \
  --stage all --run-id RUN_ID --contract plan/phase2

# a single stage, importing a prior run's verified dependencies read-only
PYTHONPATH=.reference:. python3 -m research.run_structural_experiments \
  --stage p1 --run-id RUN_ID --contract plan/phase2 --inputs results/phase2_structural_encoding/PRIOR

# independent checks and gate recomputation
PYTHONPATH=.reference:. python3 -m research.check_structural_evidence \
  --run results/phase2_structural_encoding/RUN_ID --contract plan/phase2

# the ownership and import-boundary guard alone
PYTHONPATH=.reference:. python3 -m research.check_structural_evidence --architecture

# the research test package
PYTHONPATH=.reference:. python3 -m unittest \
  research_tests.test_phase2_encoding research_tests.test_phase2_search \
  research_tests.test_phase2_models research_tests.test_phase2_evidence \
  research_tests.test_phase2_repair -v
```

The tests live in `research_tests/`, not in `tests_direct/`. The frozen
historical evidence checker, `check_optimization_evidence.py`, discovers every
top-level Python file of `tests_direct/` by glob and requires it to appear in a
provenance record written before phase 2 existed, so a new module there fails a
production gate that nothing in this package is allowed to edit. The lead's
repair decision of 2026-09-23 relocated them; `plan/phase2/` still names the old
paths and is kept unedited as historical input.

`--stage` accepts `preflight, p0, p1, p2, p3, p4, p5, all`. A run id holds only
letters, digits, underscore and hyphen. There is **no flag** that disables a
gate, shrinks a corpus, changes a seed, ignores a failure or permits overwrite;
a test asserts that too.

Exit codes: `0` every required runnable stage completed with valid evidence,
including a scientific null result and correctly marked conditional omissions;
`1` a correctness, integrity or checker failure; `2` missing inputs, a preflight
problem, or incomplete mandatory evidence.

## Limitations

These are properties of this implementation, stated so that no reader has to
infer them from silence.

* **The codec is partial on binary strings, by design.** A finite feasible set
  need not have power-of-two cardinality, so invalid codes exist, are counted
  and are never padded away. Padding would destroy injectivity and bias
  uniform-bit sampling.
* **Completeness means completeness over the declared `F_d`,** never over all
  schedules. A finite codec cannot represent arbitrary idle cycles.
* **Dead ends are detected and counted, not proved absent.** A locally legal
  prefix may have no legal completion, and on the declared whole-program domain
  it very often does not.
* **The bounds are admissible, not tight.** Peak simultaneous live width is a
  lower bound on the footprint that vector alignment can make unreachable; it is
  used to prune and is never reported as a footprint.
* **`UNSAT` from the search means the declared finite domain was exhausted,**
  pruned only by those bounds. It excludes that domain and nothing wider.
  Budget exhaustion is `UNKNOWN` and is never reported as `UNSAT`.
* **An exact cover of observed elites denotes exactly those elites.** The
  `empirical_cover` arm exists to demonstrate that it cannot discover an unseen
  index, and it records its exhaustion.
* **The architecture guard's static scan detects a duplicate *definition*,**
  not a semantically equivalent reimplementation under another name. It cannot
  prove the semantic absence of duplication and does not claim to. The runtime
  import check, which observes the module graph the interpreter actually built,
  is what closes the oracle's import boundary.
* **`structural_expanded` is the bounded search on an explicitly enlarged
  domain.** It is the same algorithm as `structural_bound`; only the declared
  domain differs. It is reported separately and is never a matched-encoding
  comparison.
* **This is a local enumeration research baseline.** Wrapping individual
  enumerated points in cubes does not establish a new symbolic production
  algorithm, and no integration is proposed here.

## Two readings the contract left to the implementer

Both are recorded because a reviewer should not have to guess which way they
went.

1. **An out-of-range or non-integer index raises**, rather than returning
   `INVALID_CODE`. The contract says to "validate index type and `0 <= index <
   2**B` *before* decoding"; a value outside the code universe is not a code, so
   it is a caller error. `INVALID_CODE` is reserved for a well-formed code whose
   rank is out of range at a decision, which is the case the contract's
   precedence rule is about.
2. **P4's matched budget is the three declared optimisation budgets in
   seconds**, primary 0.1 s, with the paid-query counts recorded alongside.
   The contract fixes "the same budgets" without naming a unit; seconds is the
   only budget mechanism the protocol declares, and model construction is
   charged to it along with every attempted, failed and duplicate proposal.
