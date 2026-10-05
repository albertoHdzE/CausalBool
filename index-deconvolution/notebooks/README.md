# Didactic Notebooks — From Deconvolution to the Fractal Clock

A progressive, visual course that teaches the whole programme to a non-expert
audience, one notebook at a time. Each notebook is self-contained, richly plotted,
and explains every result in plain language. Run them **in order**.

| # | Notebook | What you learn | Bitácora |
|---|----------|----------------|----------|
| 00 | `00_forward_method_and_deconvolution` | Boolean networks, the behaviour table, and the exact inverse: recover wiring + gates from behaviour alone | 00–02 |
| 01 | `01_cellular_automata` | Recover a cellular-automaton rule from its space-time picture; prove equivalence; why it cannot fit noise | 04, 10 |
| 02 | `02_biological_networks` | Real gene networks, the regulatory gate (activators AND NOT inhibitors), and in-silico reprogramming | 05, 07, 09 |
| 03 | `03_financial_honest_negative` | The market carries no deterministic rule — proven against a cellular-automaton control | 06, 08, 12, 13 |
| 04 | `04_behaviour_tables_volatility` | Multi-bit binarisation: the direction bit is inert, the volatility bit is self-similar and forecastable | 14, 15 |
| 05 | `05_representation_free_pivots` | Pivots (turning points), the (Δt, Δv) encoding, Benford's law, and the discovery that the information is a **clock** | 16 |
| 06 | `06_fractal_and_shared_clock` | The clock is a self-similar fractal point process, and largely shared across instruments | 17 |
| 07 | `07_recursion_and_leg_shape` | The clock of the clock (bursts of bursts) and within-leg sub-diffusion | 18 |
| 08 | `08_from_structure_to_strategy` | Turning the structure into a **risk** strategy — and the honest ceiling (no return alpha) | 19 |
| 15 | `15_shifted_zero_bdm_probe` | A zero shifted through 8-bit blocks: BDM sees each block, not the shift; its answer depends on whether the partition matches the hidden period 9. Revised 2026-10-02: names A64/A72/A24, characters versus bits versus archives, full-coverage scans beside the historical drop policy, P1–P3 executed | 32, 33 |
| 16 | `16_hierarchical_index_generalization` | HID-v1: a decodable hierarchical code, a frozen bounded search, and its benchmark against a strong baseline portfolio on unseen strings (run `confirm-v1`) | 34 |
| 17 | `17_hierarchy_search_v2` | HID-search-v2: consensus/dense/global templates and bounded boundary search inside the unchanged HID-v1 language; prospective run `search-confirm-v2-r1` read from saved artefacts | 40 |
| 18 | `18_hierarchy_search_diagnosis` | search-diagnosis-v1 (post-hoc, artifact-only): where the full HID search loses — saved cost map, 8x boundary caps, the supplied-cut subset lattice and HID translations of the saved period/pair-grammar archives (run `search-diagnosis-v1-r1`) | 42 |
| 19 | `19_bdm_and_index_complexity` | Protocol bdm_anatomy_v1 (frozen, 2 amendments, run `a3`): BDM is dictionary + counts with no arrangement; not a code length, neither an upper nor a lower bound on K; perturbation signs depend on the grid on complex rules; simpler methods emulate BDM only where it is saturated; our certified ECA code and HID-v1 against BDM; two-rule boundaries | 43, 44 |

## How to run

1. **Kernel.** These need `matplotlib` and `numpy`, which live in the repository
   `venv`. A kernel named **CausalBool** has been registered for it. In Jupyter,
   open a notebook and choose *Kernel → Change kernel → CausalBool* (top-right).
   From the command line:

   ```bash
   # execute a notebook in place (uses the CausalBool kernel)
   ../../venv/bin/jupyter nbconvert --to notebook --execute --inplace 05_representation_free_pivots.ipynb
   ```

2. **Run the first cell first.** Every notebook opens with a bootstrap cell that
   locates the repository and puts all the code layers (`src`, `level2`…`level8`)
   on the path. After that, **any cell runs from anywhere** — the notebook does not
   care what folder you launched it from.

3. **Order matters.** The notebooks build on each other; read them 00 → 08.

## Regenerating

Each notebook is produced by a small builder script (`build_00.py` … `build_08.py`)
that uses the helper `_nblib.py`. To rebuild and re-execute one:

```bash
python build_05.py
../../venv/bin/jupyter nbconvert --to notebook --execute --inplace 05_representation_free_pivots.ipynb
```

Nothing else is required to *build* the notebooks (only the standard library);
*executing* them needs the CausalBool kernel.

## Current revision of notebook 18

Notebook 18 now shows reporting revision **report-r3**, accepted by Codex on 2026-10-04.
It is the retained executed copy of
`results/hierarchy_search_diagnosis/review_closure/search-diagnosis-v1-r1-followup/corrected/18_hierarchy_search_diagnosis.report-r3.executed.ipynb`,
and `build_18.py` reads `review_closure/search-diagnosis-v1-r1-followup/report-r3/outputs`.
The computations remain attempt a1 (`518ebc13…`); report-r3 (`7b1590bb…`) supersedes
report-r2 for reporting only. The acceptance record is
`results/hierarchy_search_diagnosis/supervision/search-diagnosis-v1-r1/closure_acceptance/ACCEPTANCE.md`,
and the integration record is `results/hierarchy_search_diagnosis/integration/search-diagnosis-v1-r1/`.

## Notebook 20 (HID-search-v3a)

`20_hierarchy_search_v3a.ipynb` (builder `build_20.py`) presents run
`results/hierarchy_search_v3a/search-confirm-v3a-r1`: four refinement seeds (k = 4)
against the accepted one-seed method (k = 1). It is artifact-only and was executed under
the reviewed guard from both the notebook directory and the repository root
(`results/hierarchy_search_v3a/search-confirm-v3a-r1/notebook/run2.checks.json`; run1
failed on a builder formatting bug and is retained). Status: ready for Codex review, not
yet accepted. Notebook 19 belongs to the BDM workstream.
