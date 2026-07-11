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
