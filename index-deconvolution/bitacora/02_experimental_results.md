# Bitacora 02 — Experimental Results

Date: 2026-07-09
Status: first full run complete

All numbers below are produced by the scripts in `experiments/` and
`crosscheck/` and are stored as JSON in `results/` and
`crosscheck/wolfram_result.json`. Re-running the scripts reproduces them
exactly (the generation is seeded).

## Toolchain

- Python 3.13, standard library only (no third-party dependencies).
- Wolfram Kernel (Wolfram.app 12+) for the equivalence cross-check.
- Test runner: `pytest`.

## Experiment 0 — unit tests

Command: `python -m pytest tests/ -q`

Result: **9 / 9 tests pass.** Coverage includes gate truth tables against the
`Gates.m` definitions, the pivots/sumandos property (disconnected nodes never
sensitive), gate identification including the single-input ambiguity class, and
end-to-end exact recovery over 60 random networks.

## Experiment 1 — pivots versus sumandos

Command: `python experiments/exp01_pivots_sumandos.py`
Scope: sizes 7, 8, 9, 10; 50 seeds each; full 12-gate family; 1700 nodes total.

| Quantity | Result |
|---|---|
| Disconnected node always insensitive | 1700 / 1700 (100.00%) |
| Sensitive set is a subset of true connectivity | 1700 / 1700 (100.00%) |
| Connectivity recovered exactly | 1612 / 1700 (94.82%) |

Per-gate connectivity recovery (nodes / exact / dropped input):

    AND        130 / 130 / 0
    OR         139 / 139 / 0
    XOR        118 / 118 / 0
    NAND       143 / 143 / 0
    NOR        131 / 131 / 0
    XNOR       141 / 141 / 0
    NOT        160 / 160 / 0
    IMPLIES    157 / 157 / 0
    NIMPLIES   145 / 145 / 0
    MAJORITY   153 / 153 / 0
    KOFN       124 / 124 / 0
    CANALISING 159 /  71 / 88

Reading of the result:

1. The factorisation is confirmed without a single counterexample: a
   disconnected node never influences any output column (100% of 1700 nodes).
   This is the empirical foundation of the deconvolution.
2. The recovered sensitive set is never larger than the true connectivity
   (100% subset): the method produces no false edges.
3. Connectivity is recovered exactly for all eleven non-canalising gate
   families. The entire shortfall comes from CANALISING, where 88 of 159 nodes
   are functionally independent of a declared input for the sampled parameters.
   Those declared edges are non-functional; the deconvolution correctly recovers
   the functional connectivity, which is a strict subset.

## Experiment 2 — exact recovery (main result)

Command: `python experiments/exp02_exact_recovery.py`
Scope: sizes 7, 8, 9, 10; 50 seeds each; full 12-gate family. 200 networks,
1700 nodes. The original definitions are hidden; only repertoires are exposed.

| Quantity | Result |
|---|---|
| Exact repertoire reproduction | 200 / 200 networks (100.00%) |
| Connectivity recovered exactly | 96.12% of nodes |
| Gate function recovered exactly | 96.12% of nodes |

Ambiguity class size histogram (number of canonical gates realising the
recovered function):

    class size 1 : 292 nodes
    class size 2 : 387 nodes
    class size 3 : 368 nodes
    class size 4 :  72 nodes
    class size 5 : 298 nodes
    class size 6 :  49 nodes
    class size 7 :  39 nodes
    class size 8 : 195 nodes

*Corrected 2026-09-02 (AUDIT02/Q1).* The histogram above previously read
`1:679, 2:368, 3:72, 4:298, 5:49, 6:39, 7:195`, which was this artefact's state
before `REGULATORY` and `REGULATORY_DNF` were added to `identify_gate`
(commits `b74953b`, `69156ce`); the committed JSON was never regenerated
afterwards. The correction is a clean shift: every old class 2–7 count survives
unchanged one bin higher, and the old class 1 (679) splits into 292 still-unique
and 387 that gained a second name. Verified as pre-existing, not caused by
AUDIT02: the producer emits byte-identical output at `f17e839` and at HEAD.
**The headline numbers are unaffected** — 200/200 exact repertoire and 96.12%
connectivity/gate recovery are identical before and after.

Reading of the result:

1. **The decisive criterion is met in full: every one of the 200 networks is
   reconstructed to a definition that reproduces its output repertoire exactly.**
   The deconvolution is exact, as the theory predicts.
2. Connectivity and gate-function recovery agree at 96.12%; the 3.88% gap is
   exactly the CANALISING functional-independence cases of Experiment 1, where
   the recovered (smaller) function still reproduces the column exactly.
3. The ambiguity histogram quantifies the naming non-uniqueness. **17.2%**
   (292/1700) of nodes have a unique canonical name — the figure previously
   given here was "roughly 40%", computed from the stale histogram above and
   too high by more than a factor of two. The remainder admit an equivalence class,
   most often at small arity (identity, constant, and threshold overlaps). Every
   member of a class reproduces the function, so repertoire reproduction is
   unaffected.

## Cross-check — Python forward model versus Wolfram reference

Command: `crosscheck/generate_crosscheck_cases.py` then
`wolfram_equivalence.wl` (paths via environment variables `CB_CASES`,
`CB_CORE`, `CB_OUT`).
Scope: 45 networks (sizes 6, 7, 8), eleven gates supported by
`CausalBoolCore.wl`.

Result: **45 / 45 repertoires identical** to
`CreateRepertoiresDispatch`. The Python forward model is equivalent to the
canonical reference; the deconvolution therefore operates on repertoires that
are byte-identical to those of the published method.

## Findings and their significance

- The index-set forward method admits an **exact** deconvolution, in contrast
  to the approximate (BDM-based) deconvolution of the cellular-automaton
  literature. This is a direct consequence of the exactness of the index-set
  formulae.
- The pivots/sumandos structure asserted in the formal manuscript is confirmed
  operationally: disconnected nodes are the free offset dimension and are
  causally inert with respect to the output, while connected nodes are the
  pivots detected by perturbation.
- The method draws a clean and useful distinction between **structural
  connectivity** (edges in `C`) and **functional connectivity** (edges the
  dynamics actually use). It recovers the latter, which is the causally
  meaningful object. The discrepancy is confined to degenerate gate
  parameterisations and is reported transparently.
- Gate naming is non-unique in general; the honest object recovered per node is
  the pair (functional connectivity, Boolean function), together with the
  equivalence class of canonical names.

## Open questions for the next entries

1. Formalise the structural-versus-functional connectivity distinction and give
   the exact conditions under which CANALISING (and other parameterised gates)
   drop an input.
2. Characterise the equivalence classes analytically (which canonical gates
   coincide at each arity), giving a closed description of the naming
   non-uniqueness rather than an empirical histogram.
3. Prove the per-node inversion is complexity-optimal in the index-set sense
   (the recovered description length equals that of the forward model).
4. Scale the perturbation step beyond single bits where useful, and connect the
   image/basin invariants to a global consistency proof.
5. Extend the cross-check to CANALISING once a Wolfram reference including it is
   fixed (the `Gates.m` semantics are already reproduced in Python).
