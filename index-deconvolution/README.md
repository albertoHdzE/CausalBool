# index-deconvolution

Inverse of the CausalBool index-set method: given only the output repertoire of
a synchronous Boolean network, recover a network definition (connectivity plus
gates) that reproduces the repertoire exactly.

This directory is self-contained. It reuses the canonical Wolfram reference of
the wider repository for an equivalence cross-check, but all deconvolution code,
experiments, results, and documentation live here and run independently.

## What this is

The CausalBool forward method compresses the full dynamics of a Boolean network
into exact index-set formulae: from a connectivity matrix `C` and a list of
logic gates `D` it produces the `2^n x n` output repertoire without exhaustive
simulation. This project provides the **deconvolution**: the exact inverse,
recovering `(C, D)` from the repertoire alone, with the original hidden and used
only to corroborate correctness.

The method rests on the compressed form of the forward transform, whose two
decompositions must not be confused (`GOVERNANCE/GLOSSARY.md` §1c). In the
Boolean indexing method the *coordinates* split into **connected** inputs `I_c`,
which determine the output, and **free** inputs, which never change it. Each side
has its own decimal encoding: the connected set is encoded as the **decimal
anchor** `P(I_c)` (ranging over the **decimal family** `L`), and the free set as
the **sumandos** `S`. Unfolding is lossless — `Dec(L,S) = {ℓ+s}` reconstructs the
repertoire exactly, which is where the word *deconvolution* comes from. Single-bit
perturbation against the exact output column therefore recovers the functional
connectivity, after which the reduced truth table identifies the gate. Because
the forward method is exact, the inverse is exact and verifiable. (This
decimal-family/sumandos decomposition is *not* the finance-side pivot/residual
decomposition; there are no sumandos in finance and no residual here.)

See `bitacora/` for the full scientific logbook:

- `00_understanding_forward_method.md` — the forward method and its conventions.
- `01_deconvolution_method_design.md` — the deconvolution method and its
  correctness argument.
- `02_experimental_results.md` — the executed results and their analysis.

## Layout

    src/
      causalbool.py          forward model and gate semantics (matches CausalBoolCore.wl)
      deconvolution.py       the deconvolution method (essential vars, gate id, verify)
      network_generator.py   seeded generator of consistent test networks
      ca_deconvolution.py    cellular-automaton to network deconvolution
      bnet.py                PyBoolNet .bnet parser for biological networks
      finance.py             binarisation and determinism analysis of price series
      Deconvolution.wl       Wolfram port of the deconvolution (with REGULATORY gate)
      CADeconvolution.wl     Wolfram port of the CA deconvolution
    experiments/
      exp01_pivots_sumandos.py   verifies the pivots/sumandos factorisation
      exp02_exact_recovery.py    main result: exact recovery over a batch
      exp03_ca_to_network.py     cellular automaton to network, exact global map
      exp04_biological.py        real gene-regulatory networks, round-trip exactness certificate
      exp05_financial.py         binarised markets vs a deterministic control
      DemoLibrary.wl, build_notebook.wl, full_pipeline_demo.nb
      CADemoLibrary.wl, build_ca_notebook.wl, ca_to_network_demo.nb
      BioDemoLibrary.wl, build_bio_notebook.wl, biological_deconvolution_demo.nb
    finance/data/                real daily price series (Yahoo v8 chart JSON)
    tests/
      test_deconvolution.py      unit and end-to-end tests (network and CA)
    crosscheck/
      generate_crosscheck_cases.py   emits networks + Python repertoires as JSON
      wolfram_equivalence.wl         recomputes them with the Wolfram reference
      verify_wl_pipeline.wl          headless check of the network notebook code
      verify_notebook.wl             evaluates the network notebook's input cells
      verify_ca_notebook.wl          evaluates the CA notebook's input cells
    results/                     JSON outputs of the experiments
    bitacora/                    scientific logbook (00-31; 32 files)

## How to run

Tests:

    cd index-deconvolution
    python -m pytest tests/ -q

Experiments (write JSON to `results/`):

    python experiments/exp01_pivots_sumandos.py
    python experiments/exp02_exact_recovery.py

Wolfram equivalence cross-check (proves the Python forward model equals
`CausalBoolCore.wl`):

    ROOT="$(git rev-parse --show-toplevel)"
    python crosscheck/generate_crosscheck_cases.py
    HOME="$HOME" \
      CB_CASES="$ROOT/index-deconvolution/crosscheck/cases.json" \
      CB_CORE="$ROOT/papers/method/code/lib/CausalBoolCore.wl" \
      CB_OUT="$ROOT/index-deconvolution/crosscheck/wolfram_result.json" \
      /Applications/Wolfram.app/Contents/MacOS/WolframKernel -script crosscheck/wolfram_equivalence.wl

## Two Wolfram notebooks

- `experiments/full_pipeline_demo.nb`: two ten-node networks taken from naive
  exhaustive dynamics, through the compact index-set model, back to the original
  by deconvolution.
- `experiments/ca_to_network_demo.nb`: recovering the generating network of an
  elementary cellular automaton from its observed space-time evolution.

Regenerate and verify (paths via environment variables), for example:

    ROOT="$(git rev-parse --show-toplevel)"
    HOME="$HOME" CB_NB="$ROOT/index-deconvolution/experiments/ca_to_network_demo.nb" \
      CB_EXPDIR="$ROOT/index-deconvolution/experiments/" \
      /Applications/Wolfram.app/Contents/MacOS/WolframKernel -script crosscheck/verify_ca_notebook.wl

## Current status

### Refreshed 2026-08-24 (AUDIT01/T2.6)

- Python tests: **146 collected / 146 passed** (`python3 -m pytest` from this
  directory — the 18 per-level suites `levelN/test_levelN.py` plus
  `tests/test_deconvolution.py`; counts derive from collection, not prose).
- Wolfram-side suite health is governed by the root repo's ledger
  `tests/MUnit/BASELINE.md` (v2: OK=46 FAIL=4 TOTAL=50 @167 s; the four reds are
  owned there — see AUDIT_FIXING_PLAN_01 Appendix E).
- Bitácora inventory: `bitacora/00`–`31` (32 files).
- Levels 11–18 have no per-level READMEs yet; that documentation debt is tracked
  as backlog item T5.3 of AUDIT_FIXING_PLAN_01.
- Method language follows `GOVERNANCE/GLOSSARY.md` §1c (two decompositions;
  decimal anchor / decimal family / sumandos; lossless `Dec(L,S)`).

### Snapshot 2026-07-09 (historical, superseded for counts only)

- Unit tests: 11 / 11 pass (network and cellular-automaton cases).
- Exact repertoire reproduction: 200 / 200 networks (sizes 7 to 10, full 12-gate
  family).
- Free-coordinate insensitivity (experiment `exp01_pivots_sumandos.py` — the
  filename names a set and an encoding side by side, per GLOSSARY §1c):
  disconnected nodes never sensitive across 1700 nodes (100%).
- Functional connectivity recovered exactly for all gates except degenerate
  CANALISING parameterisations (which are functionally independent of a declared
  input; the deconvolution correctly recovers the smaller functional set).
- Python forward model proven equivalent to the Wolfram reference: 45 / 45
  repertoires identical.
- Cellular automaton to network: exact global-map recovery on 12 / 12 rules,
  agreeing between the Python and Wolfram implementations.
- Biological networks: 8 / 8 PyBoolNet models pass the round-trip exactness
  certificate — ground truth is the exhaustive evaluation of each parsed `.bnet`,
  and the deconvolution is inverted against that same repertoire, so exactness is
  a consistency property of parser + forward model + inverter (guaranteed modulo
  bugs), NOT evidence that the networks' rules were *discovered* from data.
  Scope: n ≤ 16 (larger models excluded by design). Reframing per V4 stamp,
  AUDIT_FIXING_PLAN_01 Appendix F. The REGULATORY (activator/inhibitor) gate was
  defined from the fission-yeast clause and counted on those same networks, so
  its 8 / 8 figure carries a mild training-on-test caveat and must not be read
  as out-of-sample gate validation.
- Financial data: binarised daily markets admit no deterministic Boolean network
  (contradiction rate 0.66, 0 / 9 instruments exact), while the identical
  analyser recovers a deterministic control exactly (contradiction 0, 9 / 9).
- Three demonstration notebooks verified headless: 0 messages, all checks pass.
- Unit tests at snapshot time: 16 / 16 (superseded by the refreshed count above).

## Conventions

- Node and bit indices are 0-based in the Python code (Wolfram is 1-based; the
  offset does not affect any value).
- Input enumeration is LSB-first, matching `CausalBoolCore.wl`.
- `C[k][i] = 1` iff node `i` feeds node `k`.
- No mocks and no simulated data: every repertoire is computed by the real
  forward method, and every result is produced by an executed run.
