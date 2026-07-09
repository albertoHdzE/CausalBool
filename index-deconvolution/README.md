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

The method rests on the pivots/sumandos structure of the forward transform:
connected nodes (pivots) participate in the output; disconnected nodes
(sumandos) form a free offset dimension and never change it. Single-bit
perturbation against the exact output column therefore recovers the functional
connectivity, after which the reduced truth table identifies the gate. Because
the forward method is exact, the inverse is exact and verifiable.

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
    experiments/
      exp01_pivots_sumandos.py   verifies the pivots/sumandos factorisation
      exp02_exact_recovery.py    main result: exact recovery over a batch
    tests/
      test_deconvolution.py      unit and end-to-end tests
    crosscheck/
      generate_crosscheck_cases.py   emits networks + Python repertoires as JSON
      wolfram_equivalence.wl         recomputes them with the Wolfram reference
    results/                     JSON outputs of the experiments
    bitacora/                    scientific logbook

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

## Current status (2026-07-09)

- Unit tests: 9 / 9 pass.
- Exact repertoire reproduction: 200 / 200 networks (sizes 7 to 10, full 12-gate
  family).
- Pivots/sumandos: disconnected nodes never sensitive across 1700 nodes (100%).
- Functional connectivity recovered exactly for all gates except degenerate
  CANALISING parameterisations (which are functionally independent of a declared
  input; the deconvolution correctly recovers the smaller functional set).
- Python forward model proven equivalent to the Wolfram reference: 45 / 45
  repertoires identical.

## Conventions

- Node and bit indices are 0-based in the Python code (Wolfram is 1-based; the
  offset does not affect any value).
- Input enumeration is LSB-first, matching `CausalBoolCore.wl`.
- `C[k][i] = 1` iff node `i` feeds node `k`.
- No mocks and no simulated data: every repertoire is computed by the real
  forward method, and every result is produced by an executed run.
