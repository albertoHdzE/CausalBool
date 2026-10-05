# Submission

`compiler.py`: one file, Python 3.10 or later, standard library only beside the
supplied `machine` module. `python3 compiler.py <program.json>` writes only the
schedule JSON to stdout; diagnostics go to stderr. The supplied tests and
machine are unchanged.

## Motivation

I work on algorithmic complexity and causality, and this challenge interested me
because it is a small, closed and fully specified world: a few engines, a fixed
scratchpad and a strict contract. Good schedules cannot be written out case by
case; they have to be found from the structure of each program.

The compiler applies an idea from my research [1, 2]. Describe the space of
admissible behaviours of a system in compressed form. Then answer each question
about the system with an exact query over that description, instead of
simulating or scanning. Here the questions are "when can this operation issue?"
and "where can this value live?". Behind this is the view that compression is a
form of understanding [3]. In practice it makes every decision the answer to a
stated query, so each choice can be traced back to the constraint that forced it.

On the public programs this gave the best combined score I obtained: 2.188x.
A classical critical-path list scheduler with first-fit allocation, which I
built as a benchmark, scores 1.901x. The gain comes from scratch allocation
(3.316x against 2.420x), not from cycle count (1.444x against 1.494x) or
compile time.

[1] A. Hernández-Espinosa, H. Zenil, N. A. Kiani, J. Tegnér, "Estimations of
    Integrated Information Based on Algorithmic Complexity and Dynamic
    Querying", *Entropy* 21(10):947, 2019. doi:10.3390/e21100947
[2] A. Hernández-Espinosa, "Causal Index-Set Calculus for Boolean Networks and
    Deterministic Reconstruction", manuscript in preparation, 2026.
[3] G. J. Chaitin, "The limits of reason", *Scientific American* 294(3), 2006.

## Time spent

9 days. This is well beyond the suggested four hours.
I treated the exercise as an open problem and kept working on it, and I would
rather state that than report a trimmed figure.

## Approach

**Scheduling and allocation are one query.** Each decision, whether the issue
cycle of an operation or the scratch address of a value, is posed as an exact
query over a compact encoding of the candidate set. The answer is the smallest
member that satisfies every constraint. Nothing is scanned by trial and error.

1. **Construction.** Operations are taken in source order. An operation is issued
   at the earliest cycle its operands allow that still has capacity on its
   engine. Its result takes the lowest correctly aligned address that is free
   for the whole lifetime of the value. Vectors are placed on multiples of
   eight, and a value's words are released after its last consumer reads them.
2. **Improvement.** A bounded search takes small windows of operations. For each
   window it re-chooses issue cycles, result addresses and engine lanes
   together, aiming for a strictly lower `cycles × scratch footprint`. Every
   candidate is checked against the machine contract before it is accepted.
   The search stops after 0.1 s and returns the best schedule it has validated.
   If it finds nothing, the construction result is returned unchanged.

The compiler never calls `serial_compile` and has no fallback to another
compiler. If construction fails, the compiler exits non-zero with a message
on stderr.

## Measured public scores

Measured with the unmodified `score.py` on Python 3.11 (Apple silicon).

| | Speedup | Scratch reduction | Combined |
|---|---:|---:|---:|
| Supplied serial baseline | 1.000x | 1.000x | 1.000x |
| Construction alone | 1.510x | 2.672x | 2.008x |
| **Submitted compiler** | **1.444x** | **3.316x** | **2.188x** |

All 11 supplied tests pass. One whole CLI run, including interpreter start-up,
takes 0.20–0.25 s per public program, against the 20 s limit.

## Tradeoffs

- **Speed for scratch.** The improvement step optimises the product of cycles
  and footprint. On the public set it therefore accepts slightly slower
  schedules (1.510x → 1.444x) in exchange for much smaller ones
  (2.672x → 3.316x).
- **A time budget, not an iteration budget.** The 0.1 s limit keeps runtime
  predictable. The cost is that a slower machine may explore less and return a
  different schedule. That schedule is still valid, but its score may be lower.
- **Source-order construction.** Construction uses no critical-path priority.
  This keeps it simple and exact, and leaves the reordering to the improvement
  step.

## Unfinished work

- A critical-path priority during construction was not explored.
- The search works on windows of a few operations, so it cannot find
  improvements that need many operations to move at once.
- No spilling. The exercise states that every program fits in 256 words.
- Only the eight public programs are available to me, so I make no claim about
  the hidden set. Beyond the public programs, I checked the compiler on 134
  generated and stress programs; every output was valid.

## Tools and how their output was checked

The method and the scheduling and allocation design are my own. I used AI
assistants (Claude Code and Codex) to implement parts of the code from my
written specifications, to build benchmark compilers from the literature, to
design tests and to review correctness. I checked everything by running it. Every schedule is validated by
the supplied `machine` (`check_compilation` on every case). The supplied tests
and `score.py` were run unmodified. Independent brute-force checks were
compared against the compiler's choices, and each check was shown to reject a
deliberately injected defect.
