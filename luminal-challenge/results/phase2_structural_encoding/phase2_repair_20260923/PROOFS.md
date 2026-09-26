# Proof obligations for the structural codec

Plan section 5.2 lists seven obligations. Each is stated here as an argument
over the implementation and is accompanied by the machine-checked evidence the
run produced. An argument without its evidence file is not discharged.

Throughout, `d` is a `Domain`, `F_d` is the set of normalised compilations that
satisfy its declared domains, its fixed decisions and the pinned machine rules,
and `B` is the width of `layout(d, codec)`.

## 1. Termination

The layout fixes a finite list of decisions: one field per selected operation
and one per selected value, chosen once at `Domain` construction and never
recomputed. Each decision consults a finite option list, a subset of a declared
domain that `Domain.from_record` has already checked to be finite and nonempty.
`decode` therefore performs at most `len(layout.fields)` decisions and each does
bounded work, so it terminates. Budget exhaustion is a separate execution
status, `INTERRUPTED`, and never an infinite loop.

## 2. Soundness

Each constraint is checked exactly once, at the decision that fixes its last
free argument.

* *Precedence.* In a straight-line SSA program every data or memory predecessor
  has a smaller operation identifier, and selected times are assigned in
  ascending identifier order, so at the moment operation `i` is assigned, every
  predecessor is already fixed or already assigned. `State.time_options`
  therefore checks all of them. A *successor* may have a larger identifier; if
  it is external its time is fixed, and the same method checks it now. If it is
  selected, the constraint is re-checked from the other side when that later
  decision is taken.
* *Capacity.* `State.time_options` counts the operations, fixed and assigned,
  already at that cycle on that engine and refuses the option at the limit.
* *Allocation.* Addresses are only offered once every issue time is known, so
  `State.recompute_lifetimes` has the complete inclusive live interval of every
  value, including values whose interval moved because a selected consumer
  moved. `State.address_options` rejects any base whose block overlaps a fixed
  or already-placed block over overlapping lifetimes.
* *Closure.* Nothing is left unchecked: every completed decode is handed to
  `direct_contract.check_feasible` and to `machine.check_compilation`, and a
  rejection raises `CodecDefect` rather than being reported as `DEAD_END`.

Evidence: `p1/summary.json` -- zero defects over every exhausted code universe
and every round trip.

## 3. Completeness over F_d

Take `x` in `F_d` and follow the prescribed decision order. At each decision the
value `x` gives is (i) in the declared domain, by definition of `F_d`, and (ii)
compatible with every already-fixed decision, because `x` is legal under the
pinned machine. Both are exactly the tests `State.time_options` and
`State.address_options` apply, so the value appears in the option list and has a
rank. The induction constructs the full rank sequence, hence an encoding of `x`.

This argument fails the moment options are pruned for quality. That is why
option construction never consults the objective, the incumbent's lifetimes or
an oracle; pruning lives in `structural_search`, outside the codec.

Evidence: `p1/summary.json` -- `set_equality` against the independent oracle on
every fixture whose code universe is at most sixteen bits, and a successful
round trip of every feasible oracle object for every codec at every width.

## 4. Round trip

`encode` replays the same traversal, computing the same option lists from the
same state, and writes each rank into the field that `layout` assigned. `decode`
reads those fields back in the same traversal and reconstructs the same choices.
Hence `decode(encode(x)) = x` for `x` in `F_d`.

Evidence: the round-trip counts in `p1/summary.json`.

## 5. Injectivity

Two distinct successful codes differ in some field. Consider the first decision
at which their field values differ. Up to that point both decodes have made
identical choices, so both compute the *same* option list; distinct ranks into
one list select distinct options, so the resulting compilations differ. No bit
is ignored: `B` is the sum of the field widths and `decode` reads every field
before it can return `COMPLETE`, which the run-time reassembly check in `decode`
confirms on every successful decode. Lane labels are not part of the object, so
no auxiliary multiplicity is hidden.

Evidence: `p1/summary.json` -- no duplicate-object findings over any exhausted
universe; `encode(decode(z)) == z` on every feasible object.

## 6. Domain equivalence

`research/structural_oracle.py` enumerates the declared Cartesian product and
accepts with `machine.check_compilation` and `machine.check_case` alone. It
imports neither the codec nor `direct_contract`, so agreement between the two
sets is not a tautology.

Evidence: `p1/oracle_domains.jsonl` and the `set_equality` field per fixture.

## 7. Origin

`Domain.ordered_domain` places the incumbent's choice first whenever that choice
is present. Under a rank codec the all-zero code takes rank 0 at every decision.
If the incumbent lies in `F_d`, completeness (section 3) puts its choice in every
option list, and it is ordered first, so `decode(0)` is the incumbent.

The property is conditional, and the contract says so: an improvement target may
exclude the incumbent, in which case `decode(0)` legitimately returns `DEAD_END`
at the target predicate. Domains used to study distance from the origin contain
the incumbent and apply the improvement predicate separately.

Evidence: `origin_is_incumbent` per fixture in `p1/summary.json`, and the same
property observed on all eight public whole-program domains.

## What these arguments do not establish

They are statements about *this* codec over *this* declared `F_d`. They do not
show that the encoding is total on binary strings -- it is deliberately partial.
They do not show that every locally legal prefix has a completion; dead ends are
detected and counted, not proved absent. They do not transfer to an online
chronological decoder, which needs new invariants. A counterexample here would
refute this implementation, not all possible structural encodings.
