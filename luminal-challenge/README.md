# Luminal challenge

The current objective is an independent compiler using direct index schemata.
Start with the [canonical implementation and review plan](plan/INDEX_ONLY_PLAN.md),
[agent instructions](AGENTS.md), and [task status](plan/STATUS.md).
The plan includes copy-ready prompts for implementation, delegation, and later
independent review. Writing the plan does not complete the new implementation.

## Historical hybrid pilot

The material below describes the earlier hybrid prototype. Its BDD backend and
classical starting solution do not satisfy the new direct-index method boundary.

This is a local research pilot. Both compilers solve the public challenge's
instruction-scheduling and scratch-allocation contract. The index arm reuses
the existing Doppel shared decision-program implementation, whose paths encode
decimal anchors and free-coordinate sumandos. Its computational backend is an
ordered binary decision diagram (BDD); this pilot does not claim a new BDD or
general-purpose complexity breakthrough.

The first experiment gives equal public scores for the classical and index
arms. See [results/COMPARISON.md](results/COMPARISON.md) and the complete measured
[results/comparison.json](results/comparison.json). The index arm starts from
the classical solution, so its score alone is not evidence of an index advantage.

## Reproduce

Use Python 3.10 or later, with no third-party packages. From this directory:

```sh
git clone https://github.com/luminal-ai/interview.git .reference
git -C .reference checkout 573b8a85f4bdb8c3d8ba9f180d5f98dac875c902
python3 -m unittest discover -s . -p 'test_*.py' -v
python3 benchmark.py
```

The local `.reference` already exists in the current workspace; cloning is for
a fresh checkout. `reference.json` pins every original file by SHA256.
Benchmarking verifies those hashes and runs the unchanged public test suite
against each compiler. The source exercise remains in ignored `.reference`.

Standalone, standard-library-only compiler files can be assembled locally:

```sh
python3 export.py --method classical
python3 export.py --method index
PYTHONPATH=.reference python3 .build/index/compiler.py .reference/programs/03_vector_axpy.json
```

Each exports `compile_program(program)` and emits only JSON on stdout through
the CLI. The output files carry the constituent source hashes. They are local
artifacts; nothing is submitted or published by these commands. The exercise's
README requests that the exercise and solution not be shared publicly; any
paper benchmark should use independently specified examples or obtain permission.

## Experimental arms

- **Serial:** unchanged Luminal baseline.
- **Classical:** critical-path list scheduling and aligned first-fit allocation,
  choosing the best of three fixed interval orders, with serial fallback.
- **Index:** the classical result followed by bounded, exact Boolean queries.
- **Exhaustive:** the same bounded improvement policy with direct enumeration
  instead of index construction and retrieval.

Scheduling queries vary at most six operations by at most two cycles. They
include dependencies, memory ordering, engine capacity, the reduced cycle
target, and scratch lifetime constraints, including external consumers and
pending writes. Addresses stay fixed during a scheduling query; allocation may
then improve them. Allocation queries vary at most four addresses, with the
schedule fixed and the reduced footprint target included in the predicates.
The two decisions are alternated, not jointly optimized over the entire program.

A query builds local predicate decision programs and intersects them. It follows
one accepting path to return an anchor and free mask. Every filling of those free
coordinates is a satisfying assignment. Domain maps translate the assignment
codes to actual cycles/addresses. These index decimals are **not** physical
scratch-memory addresses. No full joint truth table is constructed, but local
predicate construction enumerates assignments to each predicate's support.

The index adapter calls the existing private `_Manager` interface in
`doppel-challenge/src/doppel_challenge/repertoire_program.py`; tests and source
hashes guard this coupling. No existing method code is changed.

An `UNSAT` result excludes a solution only in the specified neighborhood.
Timeout and node-budget exhaustion return `UNKNOWN`, never `UNSAT`.
Each query has a 0.12-second budget and a 30,000-node limit. The optimizer checks
a two-second overall budget between queries; this is a soft budget, excluding
uninterruptible setup for a query, not a guaranteed hard process limit.

## Measurement scope

Three fresh-process repetitions per public program and method measure compiler
time separately from process startup and correctness checks. Peak RSS includes
interpreter and imports. The eight private programs are unavailable. Generated
tests use only documented operations and deliberately include overlapping
memory accesses, unused values, scalar/vector interactions and wraparound data.

Matched queries compare both solvers on exactly the same domains and predicates,
including feasible bounds and bounds tightened by one. Enumeration follows the
same low-first bit order as symbolic retrieval. Completed results must agree on
both satisfiability and the first witness. The test suite additionally checks
all fillings of small returned schemata and compares complete small candidate
spaces with the frozen machine validator.

`one_output_decision_bits` is a logical payload measure for **one Boolean
acceptance function**, with the variable count known to its decoder. It excludes
domain maps, original program, predicate construction, interpreter and runtime
objects. `truth_table_bits` is `2**b` for that acceptance function's `b` encoded
bits, including invalid domain codes as false. Neither quantity is the target
program's scratch footprint. Allocated nodes include intermediate nodes; final
reachable nodes can be much smaller, especially for an unsatisfiable predicate.

This pilot is not preregistered. It supplies a reproducible correctness and
measurement foundation, not evidence of global optimality, performance on the
private grader, or a new asymptotic bound. Stronger claims require larger
independent families, equal-budget comparisons with established constraint
solvers, variable-order experiments and explicit construction-cost bounds.
