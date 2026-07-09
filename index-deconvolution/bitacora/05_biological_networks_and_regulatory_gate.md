# Bitacora 05 — Biological Networks and the Regulatory Gate

Date: 2026-07-09
Status: complete and verified

## Aim

Apply the index-set deconvolution to real gene-regulatory Boolean networks. The
algorithmic-information causal calculus of Zenil and colleagues applies its
perturbation analysis to biological networks (E. coli, Th17, CellNet) for
reprogrammability, but it reconstructs only cellular automata; it never recovers
the biological networks themselves. This entry does exactly that, and in doing so
identifies and formalises a new gate that biological logic requires.

## The networks

PyBoolNet `.bnet` models under `data/bio/raw`, parsed by `src/bnet.py` into the
CausalBool form: each node's referenced inputs become its connectivity and its
Boolean expression is evaluated exhaustively into a look-up table, so the ground
truth is exact and assumption-free. Models used (all with exhaustive repertoire,
n <= 16): Arabidopsis root stem cell, fission yeast cell cycle, mammalian cell
cycle, IRMA synthetic yeast, myeloid differentiation, guard cell ABA signalling,
apoptosis, WNT5A melanoma. Larger models (grieco_mapk n=54, remy_tumorigenesis
n=35) exceed the exhaustive limit and are left for the trajectory route.

## The new gate: REGULATORY (activator/inhibitor conjunction)

Real regulatory logic is dominated by conjunctions of the form "the gene is
expressed when its activators are present and its repressors are absent". The
fission yeast model shows it directly:

    Cdc2_Cdc13_A = !Wee1_Mik1 & !Ste9 & !Slp1 & !Rum1 & Cdc25

This is a single conjunctive clause with one positive literal (activator Cdc25)
and four negative literals (inhibitors). The single-inhibitor case is the named
gate NIMPLIES and the all-inhibitor case is NOR, but the mixed multi-input case
has no classical name. We add it.

### Definition

Let the connected inputs partition into activators A and inhibitors R. The
REGULATORY gate is

    out = ( product over a in A of v_a ) * ( product over r in R of (1 - v_r) )

so out = 1 on exactly the one configuration with every activator on and every
inhibitor off, and 0 otherwise. It generalises AND (R empty) and NOR (A empty).

### Index-set (pivot and sumandos) expression

In the LSB-first convention with weights 2^(i-1), define the pivot as the decimal
value of the unique satisfying configuration of the connected bits,

    P = sum over a in A of 2^(a-1)          (activators contribute 1, inhibitors 0)

Then the one-set is the single pivot configuration shifted across the free
disconnected dimension (the sumandos), exactly as for AND:

    J_k = { P + 1 + Delta : Delta = sum over t in D of v_t 2^(t-1), v_t in {0,1} }

subject to the connected condition v_a = 1 for a in A and v_r = 0 for r in R,
where D is the set of disconnected nodes. AND is the special case A = I_c
(pivot = all connected bits set) and NOR is A empty (pivot = 0).

### Deconvolution signature

The REGULATORY gate is recognised without search: the reduced truth table over
the essential variables has a single 1. Its position y* encodes the split, bit j
of y* being 1 for an activator and 0 for an inhibitor. This is exact.

The gate is implemented in the forward model (`apply_gate` in
`src/causalbool.py`), in the identifier (`identify_gate` in
`src/deconvolution.py`), and in the Wolfram side (`Deconvolution.wl`,
`CADeconvolution.wl`). The canonical priority places AND and NOR above
REGULATORY, so the classical names win their special cases and REGULATORY names
only the genuinely mixed conjunctions.

## Results

Experiment `experiments/exp04_biological.py`.

- Exact repertoire reproduction: 8 / 8 models. Every biological network is
  recovered to a definition that reproduces its behaviour exactly.
- Gate totals across all nodes: AND 26, LUT 20, NIMPLIES 10, NAND 8,
  REGULATORY 5, CANALISING 2, NOR 2, plus single OR, IMPLIES, MAJORITY, TRUE,
  FALSE.

The distribution confirms the biology. Regulatory functions are overwhelmingly
canalising conjunctions: AND (co-activation), NAND and NIMPLIES and NOR (single
or pure repression), and the mixed REGULATORY clauses. The REGULATORY gate names
five nodes that would otherwise be look-up tables, including the yeast
Cdc2_Cdc13_A node above. The remaining look-up tables are multi-clause
disjunctive functions (unions of several regulatory clauses), which is the
natural next naming target.

## Cross-implementation verification

`crosscheck/generate_bio_cases.py` exports the repertoires and the Python gate
classification; `crosscheck/verify_bio_wl.wl` deconvolves the same repertoires in
Wolfram and checks agreement. Result: all five exported models reproduced exactly
in Wolfram, with the REGULATORY counts identical to Python (fission yeast 1, IRMA
0, WNT5A 0, myeloid 1, apoptosis 2).

One deliberate difference: the Wolfram identifier uses the core family plus
REGULATORY, while the Python identifier additionally tries CANALISING. For one
myeloid node Python reports CANALISING where Wolfram reports a look-up table; both
reproduce the behaviour exactly, and the REGULATORY classification is identical.

The notebook `experiments/biological_deconvolution_demo.nb` deconvolves the five
models and reports exact recovery with the gate histogram and REGULATORY count.
It is generated by `experiments/build_bio_notebook.wl` and verified by
`crosscheck/verify_bio_notebook.wl` (0 messages, all exact). The full Python test
suite is 14 / 14.

## Significance

The deconvolution recovers real gene-regulatory networks exactly, which the
algorithmic-information literature does not attempt. Beyond exact recovery, the
work yields a biologically grounded addition to the method: the REGULATORY gate,
with a closed-form index-set expression that generalises AND and NOR and captures
the activator/inhibitor conjunctions at the heart of regulatory logic. This is a
concrete new "rule" for the CausalBool family, derived from and validated on real
biology.

## Open questions

1. Name the multi-clause disjunctive functions (the remaining look-up tables) as
   unions of REGULATORY clauses, giving a regulatory disjunctive-normal-form gate
   with its own index-set expression (a union of pivot-shifted cosets).
2. Extend to the large models (grieco_mapk, remy_tumorigenesis) through the
   trajectory route of Bitacora 04, since their state space is too large to
   enumerate.
3. Relate the REGULATORY and forthcoming disjunctive gates to the nested
   canalising functions known to dominate real regulatory networks.
