# Bitacora 07 — The Regulatory DNF Gate

Date: 2026-07-09
Status: complete and verified

## Aim

Close the naming gap left by Bitacora 05. There, mixed single-clause
activator/inhibitor functions were named by the REGULATORY gate, but multi-clause
functions (unions of several regulatory contexts) fell back to explicit look-up
tables. This entry adds the natural generalisation, the regulatory disjunctive
normal form, so that regulatory logic is named end to end.

## Definition and index-set form

A regulatory DNF is an OR of regulatory clauses,

    out = OR over clauses c of ( product over a in c.activators of v_a
                                 times product over r in c.inhibitors of (1 - v_r) )

Each clause fixes some inputs (activators to 1, inhibitors to 0) and leaves the
rest as don't-care. In the index set this is a union of pivot-shifted cosets: a
single REGULATORY clause is one coset (Bitacora 05), and the DNF one-set is their
union. AND, OR, NOR, NIMPLIES and the single-clause REGULATORY are all special
cases.

## Recovery

Given the reduced truth table, the on-set is covered by regulatory clauses using
Quine-McCluskey prime implicants followed by a greedy set cover
(`minimal_dnf` in `src/deconvolution.py`). The cover reproduces the function
exactly by construction. It is offered as the gate name only when it genuinely
compresses (fewer clauses than on-set minterms) and the arity is small enough for
the cover to be meaningful; otherwise the look-up table stands. Named gates and
the single-clause REGULATORY keep priority, so the DNF names only what would
otherwise be a look-up table.

## Results

Re-running the biological experiment (`experiments/exp04_biological.py`): all 8
models still recover exactly, and every node is now named. The 20 nodes that were
look-up tables become REGULATORY_DNF (compact activation logic); the gate totals
are AND 26, REGULATORY_DNF 20, NIMPLIES 10, NAND 8, REGULATORY 5, CANALISING 2,
NOR 2, and single OR, IMPLIES, MAJORITY, TRUE, FALSE. Regulatory logic is thus
expressed entirely as activator/inhibitor conjunctions and their disjunctions,
which is the biologically natural description.

The gate is implemented in the Python forward model, the identifier, and the
Wolfram extended evaluator (`CADeconvolution.wl`), so recovered DNF networks
replay in both. The Python test suite is 18 / 18. The Wolfram biological
verification still passes exactly.

Parity note: the Wolfram identifier still names multi-clause functions as look-up
tables (it does not yet run the cover), so the Wolfram notebook histogram shows
look-up tables where Python shows REGULATORY_DNF. Both reproduce the behaviour
exactly and the single-clause REGULATORY counts agree. Porting the cover to
Wolfram via BooleanMinimize is a small, deferred item.

## Significance

Every gene-regulatory function in the tested models is now a named piece of
activation logic with a closed-form index-set expression, rather than an opaque
truth table. The CausalBool gate family, extended by REGULATORY and
REGULATORY_DNF, is expressive enough to name real regulatory dynamics
completely, which is the goal set in Bitacora 05.
