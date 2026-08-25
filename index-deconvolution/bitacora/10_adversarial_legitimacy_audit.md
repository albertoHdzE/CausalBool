# Bitacora 10 — Adversarial Legitimacy Audit

Date: 2026-07-09
Status: complete and verified

## Why this entry

The assessor challenged the work as a hostile reviewer: assume it is fake, that
there are mock functions, hard-wired code, and no real computation. The specific
suspicion was the cellular-automaton notebook, where the recovered network for
rule 30 is twelve identical REGULATORY_DNF gates, produced in seconds. Three
concrete accusations had to be answered: the method is a regression that force-
fits any function; the method is a Shannon-style search for statistical
regularity; and the test harness leaks the answer.

The response is a set of probes (`experiments/audit_legitimacy.py`), each
designed to FAIL if the accusation were true. All pass. Two genuine issues were
found and fixed along the way.

## Answering the rule-30 screenshot directly

Twelve identical gates is correct, not suspicious. An elementary cellular
automaton is homogeneous by definition: every cell applies the same local rule,
so every recovered node has the same gate. When the network is not homogeneous,
the recovery is not uniform: probe 4 builds a network with six different gates
and recovers all six different gates from the matrix alone.

Why REGULATORY_DNF and not AND, OR or XOR: rule 30 as a three-input Boolean
function is l XOR (c OR r). Its truth table equals none of AND, OR, XOR, NAND,
NOR, XNOR or MAJORITY (probe 5 prints the seven inequalities), so it correctly
falls to the general form, a minimal disjunctive normal form of three clauses.
By contrast rule 150, which is a genuine three-input XOR, is named XOR. The
naming discriminates; it does not default everything to one gate.

Why three clauses, and why it is exact: probe 6 expands the recovered clauses by
hand, c AND NOT l, OR l AND NOT c AND NOT r, OR r AND NOT l, which simplifies to
l XOR (c OR r), and evaluates it against rule 30 on all eight neighbourhoods with
a perfect match. The same three-clause minimal form is produced independently by
Wolfram's BooleanMinimize on the Wolfram side, a different algorithm from the
Python Quine-McCluskey cover, so the DNF is canonical, not fabricated.

Why seconds: probe 7 shows the deconvolution is a polynomial exact inversion,
about 3, 6 and 28 milliseconds for ten to fifty thousand repertoire cells at
n = 8, 10, 12, scaling as n times 2^n. It is fast because it is exact algebra,
not a search and not a lookup of a stored answer.

## The three accusations, tested

No leakage. The recovery functions (`deconvolve`, `deconvolve_ca`,
`deconvolve_ca_cell`) take only the output matrix or the diagrams; the generating
rule appears solely in forward generation and in the ground truth used for
verification, never in recovery (confirmed by reading the signatures and by
grep). Probe 1 constructs a four-node network on paper, evaluates its repertoire
with a wholly independent plain-Python evaluator, passes only the sixteen-by-four
binary matrix to the deconvolution, and recovers the exact connectivity of every
node and a network that reproduces the matrix through the forward model.

Not a Shannon regularity search. Essential-variable detection is an exact causal
criterion, not a statistical one: an input is essential if and only if the
function's value changes when that single bit is flipped with all others fixed.
Probe 2 prints the witness input for every connected bit (the exact pair that
flips the output) and shows that the disconnected bits never change the output.
This is functional dependence, not correlation or entropy.

Not a fit-anything regression. Probe 3 is the falsification. A method that
force-fits would give small rules for random data. Ours does the opposite:
random six-input functions need on average 14.5 DNF clauses, whereas AND needs
one and rule 30 needs three. The rule size tracks the true complexity of the
function; random data is not compressed. This is now also a unit test
(`test_random_data_is_not_compressed`).

## Issues found and fixed

1. Misleading and partly circular verification. `verify` reconstructs from the
   per-node reports, so for a node named LUT it replays a stored truth table and
   passes by construction, yet its docstring claimed verification was
   "independent of gate naming". The docstring is corrected to state the scope
   honestly, and a new `verify_forward` rebuilds the whole repertoire through the
   forward model from the recovered network alone, sharing no bookkeeping with
   the deconvolution. It is now asserted in the suite
   (`test_verify_forward_is_independent_and_exact`), so the exactness claim rests
   on a provably non-circular check.

2. Two bugs in the audit script itself, caught by the hostile pass: a
   variable-ordering mismatch in the hand expansion (the minimiser numbers
   variables least-significant-bit first, so clause position 0 was r, not l), and
   a miscalibrated pass threshold in the falsification probe. Both are fixed; the
   corrected probes pass. That the audit caught the auditor's own sloppiness is
   itself evidence the checks are real.

## Honest scope of the claim

The genuinely non-trivial, computational results are: the exact recovery of
functional connectivity (who influences whom), which is inferred from the matrix
and is not present in it explicitly; the recognition of named gates when the
local function has that compact structure; and the falsifiable property that the
recovered rule size grows with the function's complexity. The local function
itself is recovered exactly, but for an arbitrary function that is a faithful
re-encoding (a minimal DNF, or a look-up table when even that does not compress),
not a discovery of hidden simplicity. The method does not claim otherwise, and
the documentation now states this precisely.

## Verification

`python experiments/audit_legitimacy.py` reports all seven probes passing. The
Python test suite is 21 / 21, including the non-circular forward verification and
the random-data falsification. The rule-30 minimal DNF is confirmed by two
independent minimisers (Python Quine-McCluskey and Wolfram BooleanMinimize).
