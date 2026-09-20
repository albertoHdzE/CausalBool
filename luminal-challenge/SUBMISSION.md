# Luminal compiler take-home — submission notes

**Status: prepared locally, not submitted.** Nothing here has been emailed,
pushed, merged or published. The exercise asks that it not be shared publicly,
and it has not been.

Compiler: [`.build/direct_index/compiler.py`](.build/direct_index/compiler.py),
2,104 lines, Python 3.10 or later, standard library only beside the supplied
`machine` module.

## Measured public scores

Three arms, each in a fresh process, three repetitions per program, arm order
rotated between repetitions. Scores are relative to the frozen serial baseline
on the eight public programs.

| Arm | Cycle speedup | Scratch reduction | Combined | Median compile |
|---|---:|---:|---:|---:|
| serial (frozen baseline) | 1.0000x | 1.0000x | **1.000000x** | 0.022 ms |
| classical (frozen prior work) | 1.4936x | 2.4204x | **1.901379x** | 0.267 ms |
| direct index (this submission) | 1.5099x | 2.6717x | **2.008466x** | 437.5 ms |

72 measured runs, 0 failures. Every run was validated with
`machine.check_compilation` and `machine.check_case` before it was scored. The
direct arm scored 2.008466x in every recorded repetition, so it clears 1.0
throughout. The classical control reproduced its historical aggregate
`1.9013791212645499` to a difference of 0.000e+00, with identical integer cycle
and footprint values, which is the evidence that the harness itself is sound.

Worst case whole-process time was 0.70 s against the grader's 20 s allowance.
`compile_seconds` above is the compiler call alone; the 20 s limit applies to
the whole process, which also pays interpreter start and imports.

**The direct compiler is roughly 1,600 times slower to run than the classical
one.** It scores better because it allocates scratch better, not because it is
efficient. That trade is the honest headline.

## Method

Every issue cycle and every scratch address is the answer to an exact query
over index schemata. A schema is a decimal anchor with a free-coordinate mask,
denoting every filling of the free coordinates.

**Construction.** Operations are taken in source order. For each one the
compiler builds the interval of cycles from its predecessors' bound up to a
horizon, removes the cycles whose engine already holds its allowed number of
issues, and takes the minimum member of what remains. Addresses follow the same
shape: the aligned address domain, minus the exclusion range of every value
whose lifetime overlaps, minimum member. One query answers each decision,
because the window is bounded by something provable rather than by scanning.

**Improvement.** A bounded joint query then varies the issue times of at most
four operations, the addresses of the results they produce, and their engine
lanes, against targets that strictly lower `cycles × footprint`. A witness is
decoded, independently validated, measured again, and accepted only on a strict
product improvement.

There is no list scheduler, no first-fit allocator, no decision diagram, no
external solver, and no call to `serial_compile`. There is no fallback: a query
that cannot finish is a compilation failure.

## What was verified

`python3 verify_direct.py --stage all` — **PASS**, exit 0:

| Stage | Result |
|---|---|
| schema, contract, constraints, construction, optimizer | 124 tests |
| independence, export | 23 tests |
| acceptance: corpus through the standalone export | 142 programs, 277 cases |
| acceptance: unchanged public suite | 11 tests |
| acceptance: documented command line, per program | 8 programs under 20 s |

The corpus is 8 public, 30 regression, 100 generated across five families, and
4 stress fixtures that fill the scratchpad exactly. The acceptance process runs
with only the standard library and `machine` importable, so nothing can lean on
the development tree.

Claims are checked against independent oracles rather than against the code
that makes them. Cube intersection, difference and restriction are compared
with explicit Python sets over every cube pair of widths zero to five, 66,430
pairs. Comparison covers are compared with plain integer predicates at every
index of their universe. Chosen cycles and addresses are compared with
brute-force integer scans, and every alternative below a choice is confirmed
infeasible.

## Limitations, stated plainly

- **The optimiser contributes nothing on the public programs.** 158 of its 205
  queries there are infeasible as posed, because operations outside a
  four-operation window already breach the target. The public score above is
  the construction pass alone. Across the whole 142-program corpus it accepts 7
  improvements.
- **UNSAT is local.** It excludes solutions in the queried neighbourhood only,
  and says nothing about the program. No global optimality is claimed anywhere.
- 480 searches over the corpus exhaust the 100 ms per-query budget and are
  recorded as UNKNOWN. UNKNOWN is never treated as UNSAT.
- **The private grader is unavailable**, so no result on the hidden eight is
  claimed or inferred.
- Construction places operations in source order with no priority function. A
  critical-path priority was not explored.
- The 256-word scratchpad is assumed sufficient; no spilling is implemented,
  consistent with the exercise's statement that all programs fit.

## Unfinished work

- Independent lead review (task L07) is outstanding. Tasks L01 to L06 are
  offered as READY_FOR_REVIEW and none is self-accepted.
- One deviation from the written plan needs a ruling: the comparison split rule
  is read as most-significant-bit-within-its-field rather than
  highest-absolute-coordinate. See `plan/STATUS.md`, task L05.
- The per-query search budget, not the method, limits the optimiser's reach.

## Time and tool assistance

Implementation ran from commit `add0ff3` at 18:52 to roughly 19:57, about
**1.1 hours** of wall clock for tasks L01 to L06. That figure is the span
between commit timestamps, and it excludes the earlier session that produced
the plan, `AGENTS.md` and `STATUS.md`, which is where the design decisions were
actually made. A human working from the same plan would not finish in that
time; the number measures an agent's elapsed clock, not comparable effort, and
it is recorded as measured rather than adjusted in either direction.

The work was carried out by Claude Opus 5 (Anthropic) acting as a delegated
implementation agent, under a written plan and review contract prepared
beforehand. Output was checked by running it: every claim in this document
traces to a recorded command, exit code and artifact under
`results/direct_index_v1/`. Where a test and the code disagreed, both were
examined; several failures turned out to be defects in the tests and are
recorded as such in `plan/STATUS.md`, along with the two genuine code defects
that the tests caught.
