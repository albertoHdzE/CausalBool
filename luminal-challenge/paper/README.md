# Luminal paper, version 2

[Main paper](main.pdf) · [Supplementary Information](supplementary.pdf) ·
[Build validation](BUILD_VALIDATION.json) · [Claims contract](CLAIMS_AND_EVIDENCE.md) ·
[Claim table](generated/claim_table.md)

**Compiling by exact queries over index sets: a validated answer to the Luminal
compiler challenge, and evidence for a different way of computing.** Revised
26 September 2026 from the start point `paper-start/luminal-v2-20260926`.

The paper reports the whole programme: the serial, starter and classical
benchmarks, the original direct-index compiler, the structural encoding, the
A1–A4 ladder and its ablations, R0, and the final proposal C1. Every stage keeps
its own comparator. The C1 claims follow the acceptance ruling in
`../results/phase2_structural_encoding/lead_resume_review_20260926/REVIEW.md`.
That ruling is a self-review, and the paper says so.

The manuscript is prepared to publication standard but kept local. The challenge
asks that the exercise and its solution not be shared publicly.

## Build

From the repository root:

```sh
venv/bin/python luminal-challenge/paper/build_paper.py
```

The build does not time anything or rerun a benchmark. It:

1. regenerates every figure and table from frozen evidence (`generate_figures.py`);
2. runs the compared compilers on `05_mixed_broadcast` on a logical clock
   (`worked_example.py`), so that the worked-example figures draw the real
   objects; these results are cross-checked against notebook 04's recorded outputs;
3. writes the value ledger (`phase2_evidence.Ledger` → `generated/values.tex`,
   `generated/claim_ledger.json`, `generated/claim_table.md`) and re-derives every
   pointer and derived entry from disk (`verify_ledger`);
4. rejects any digit in `main.tex` or `supplementary.tex` that does not come from
   the ledger, and rejects forbidden content (`2.3948`, `5ccbaaa3`, unqualified
   "identical decisions", runtime superiority over classical, Shannon or entropy
   wording, deconvolution construction details);
5. compiles both documents twice, so that cross-document references resolve, and
   rejects any LaTeX warning, undefined reference or overfull box;
6. checks that every cited ledger value appears in the PDF text, and records
   hashes in `BUILD_VALIDATION.json`.

Each figure saves its data and its checks beside it (`generated/<figure>.json`).

## Owners

| Concept | Owner |
|---|---|
| Cited values | `phase2_evidence.py` (`Ledger`, `build_programme_ledger`, `verify_ledger`); Phase 1 values are registered by `generate_figures.py` through the same ledger |
| Compiler execution for the paper | `worked_example.py` |
| Figures and tables | `generate_figures.py` |
| Palette | `0xPARC-challenge/tools/paper_network_figures.py`, read by `ast`, never copied |
| Build and guards | `build_paper.py` |

## Baselines

The 20–23 September Phase 1 draft is preserved in `baselines/20260921/` and in
git history (tag `paper-start/luminal-v2-20260926`).
