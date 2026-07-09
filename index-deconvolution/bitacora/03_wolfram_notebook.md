# Bitacora 03 — Wolfram Demonstration Notebook

Date: 2026-07-09
Status: complete and verified

## Purpose

A single Wolfram notebook that runs the full pipeline on two ten-node networks,
end to end, using the project codebase: naive exhaustive calculation, then the
index-set causal reduction, then deconvolution back to the original network.

Notebook: `experiments/full_pipeline_demo.nb`.

## Design for reliability

The deconvolution was ported to Wolfram Language (`src/Deconvolution.wl`) so the
notebook is pure Mathematica and needs no external interpreter. Following the
style of `CausalBoolCore.wl`, both files define plain global symbols rather than
packages, so the forward and inverse methods share a context and see each
other's definitions. An early failure came precisely from making
`Deconvolution.wl` a package: inside the package context the global `ApplyGate`
from `CausalBoolCore.wl` was invisible, so every gate truth table failed to
evaluate and every node fell through to the look-up-table fall-back. A second
early failure came from `Log[2, Length]` not reducing to a machine integer;
`IntegerExponent[Length, 2]` fixes it. Both are recorded here because they are
easy traps for a future maintainer.

The stage logic lives in `experiments/DemoLibrary.wl`, so the notebook code
cells are short calls (`NaiveRepertoire`, `IndexReductionReport`,
`DeconvolutionReport`) and the headless verification exercises the identical
functions. Paths are resolved from `NotebookDirectory[]`, so the notebook runs
unchanged for any user who has the repository.

## Verification

`crosscheck/verify_notebook.wl` extracts the input cells from the generated
notebook and evaluates them in order, overriding only `NotebookDirectory[]` (the
single value the front end would supply), which faithfully emulates
"Evaluate Notebook" without a front end.

Result: 3 input cells, 0 messages raised, both examples pass.

- Example A (AND/OR, 10 nodes): naive repertoire 1024 x 10; causal model 30
  units; compression factor 341.3; model regenerates behaviour; all ten
  closed-form AND/OR one-sets match the naive index sets without scanning;
  deconvolution reproduces the repertoire exactly with functional connectivity
  identical to the original.
- Example B (mixed core family, 10 nodes): compression factor 320; exact
  repertoire reproduction; functional connectivity identical. Gate naming shows
  the expected equivalence-class substitutions (KOFN with k = 2 of 3 recovered
  as MAJORITY; single-input NOT recovered as NAND), each reproducing the
  behaviour exactly.

## How to regenerate and verify

    ROOT="$(git rev-parse --show-toplevel)"
    # regenerate the notebook
    HOME="$HOME" CB_NB_OUT="$ROOT/index-deconvolution/experiments/full_pipeline_demo.nb" \
      /Applications/Wolfram.app/Contents/MacOS/WolframKernel -script index-deconvolution/experiments/build_notebook.wl
    # verify it runs
    HOME="$HOME" CB_NB="$ROOT/index-deconvolution/experiments/full_pipeline_demo.nb" \
      CB_EXPDIR="$ROOT/index-deconvolution/experiments/" \
      /Applications/Wolfram.app/Contents/MacOS/WolframKernel -script index-deconvolution/crosscheck/verify_notebook.wl
