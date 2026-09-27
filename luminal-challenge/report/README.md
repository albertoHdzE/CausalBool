# Luminal challenge: the answer report

[Report](report.pdf) · [Build validation](BUILD_VALIDATION.json)

**Reopen and resolve: an answer to the Luminal compiler challenge.** A short,
technical report that answers the challenge directly: the serial baseline, a
classical benchmark (critical-path list scheduling with aligned first fit), and
the compiler we propose (C1), which reopens the decisions responsible for the
current cost and re-solves them exactly. It walks `05_mixed_broadcast` through
every compiler step by step and compares the final compiler with the classical
one on the public programs and on fresh generated programs.

The full research account, with every stage, ablation and negative result, is the
paper in `../paper/`. This report deliberately omits that history and the details
of the index-set representation.

## Build

From the repository root:

```sh
venv/bin/python luminal-challenge/report/build_report.py
```

The build measures nothing. It copies the cited entries of the paper's claim
ledger, derives the few report-specific values (the cycle and scratch halves of
the public score, win counts, public compile times) from the same frozen rows,
asserts that its recomputed combined scores equal the ledger's, re-derives every
pointer entry from disk, rejects any hand-typed digit in `report.tex`, compiles
twice with zero LaTeX warnings, checks every cited value in the PDF text and
writes `BUILD_VALIDATION.json`. Figures in `generated/` are hashed snapshots of
the paper's worked-example figures.
