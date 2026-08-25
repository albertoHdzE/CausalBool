# Bitacora 11 — Gate Confusion, Arity Detection and Schemata

Date: 2026-07-09
Status: complete and verified

## The assessor's questions

1. Can a node with several inputs be misclassified, so that an OR behaves as an
   AND under a particular network configuration?
2. How is the number of inputs (arity) of a node found, and can it be wrong?
3. Is the multi-node interaction (schemata) characteristic exploited?

All answered by experiment in `experiments/audit_schemata_confusion.py`.

## First, a clarification on "counting bits"

The `Count` and `Total` arithmetic in `ApplyGate` is the forward gate semantics;
it is used to generate candidate truth tables. Gate identification compares full
truth tables for equality (`truth_table(g, m, p) == reduced`), not summary bit
counts on the observed data. So two gates with different truth tables are never
confused when their inputs are fully observed.

## The decisive distinction: exhaustive versus reachable inputs

Whether confusion is possible depends entirely on which input combinations are
observed.

Over the exhaustive repertoire every combination appears. Then:

- OR equals AND only at arity 1, where both are literally the identity. For arity
  two and above their truth tables differ and they cannot be confused (probe A).
- The only coincidences are genuine functional equalities: AND = KOFN(n),
  OR = KOFN(1), MAJORITY = KOFN(middle), and so on. These are equivalence
  classes, reported honestly, all reproducing the behaviour exactly.
- Over 420 nodes of random networks, the recovered function was exact in every
  case (zero functional errors). In 123 cases the recovered name differed from
  the generating gate, but always with an identical truth table, that is a
  relabelling within an equivalence class, never a functional error (probe B).

So the answer to question 1 in the exhaustive setting is: no functional confusion
is possible; an OR is never an AND for arity two or more.

## The counterexample (reachable states)

Confusion is real when only the reachable states of a running network are
observed, because the inputs can be correlated. Probe C builds it explicitly:
node0 toggles, node1 and node2 both copy node0, so node1 equals node2 in every
reachable state, and node3 is OR(node1, node2).

- Exhaustive deconvolution recovers node3 as OR of inputs {1, 2}, exactly.
- In the reachable set (four of sixteen states) node1 equals node2 always.
  OR(node1, node2) then equals node1, which also equals AND(node1, node2): the
  two gates are indistinguishable. Single-bit perturbation finds neither input
  essential, because neither can be flipped alone without leaving the reachable
  set, so the reachable-only method reports an inconsistency and recovers no
  valid small-support function. It does not fabricate a gate.

This is the fundamental confounding problem of causal inference, and it answers
both questions at once. The exhaustive method is immune because it probes the
counterfactual states where node1 differs from node2; that is precisely the
scientific value of working over the full repertoire. The trajectory method (used
for cellular automata and time series) is exposed to it, and guards against it
with the coverage and consistency diagnostics already in place: when coverage is
incomplete the recovered rule is flagged, not trusted (bitacora 04).

## How the arity is found

The arity is the number of essential inputs, found by exact single-bit
perturbation: input i is essential if and only if flipping bit i alone changes
the output for some observed input. Over exhaustive data this returns the exact
functional arity. Over reachable data it can be under-counted when inputs are
confounded (in probe C both confounded inputs are dropped). The arity recovered
is functional, not structural: an input the function ignores is correctly
excluded, which is the desired behaviour.

The method does not use a compression heuristic to guess the arity; it uses exact
functional dependence. This is a deliberate design choice that makes the
exhaustive recovery exact rather than approximate.

## Schemata and multi-node interaction

The multi-interaction structure is exploited and visible in the recovered rule.
Each clause of the index-set rule is a schema in Holland's sense: it fixes some
inputs and leaves the rest as don't-cares, which are exactly the sumandos (the
free offset dimension). Probe D recovers rule 110 as three schemata, 01*, 10* and
*10 over its three inputs, whose free positions are the sumandos and which cover
exactly the five minterms of the on-set. A node whose function has real internal
structure is thus expressed as a small set of schemata; the more the inputs
interact through shared don't-care structure, the fewer schemata are needed. This
is where the compression of interacting logic appears, and it is the same
pivot-and-sumandos structure used throughout.

## Verification

`python experiments/audit_schemata_confusion.py` reports all four probes passing.
Two findings are locked into the suite (now 23 tests): OR is not AND for arity two
and above, and the reachable-state confounding counterexample.

## Honest conclusion

The exhaustive index deconvolution is exact and cannot confuse gates beyond
genuine functional equivalence; the arity it reports is the exact functional
arity. The one regime where an OR can look like an AND is when only correlated
reachable states are observed, which is a property of the data, not a defect of
the method, and the method reports insufficiency there rather than guessing. The
schema structure of interacting logic is captured directly by the clause (pivot
and sumandos) form of the recovered rule.
