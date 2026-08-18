> **Start here:** [`bitacora/00_kickoff.md`](bitacora/00_kickoff.md) — the kick-off
> record: why this package exists, the six adaptation designs, the risk register and
> the decisions taken. [`PROTOCOL_causal_timeseries.md`](PROTOCOL_causal_timeseries.md)
> — the pre-registered phase protocol and its falsification criteria.
> [`FINDINGS.md`](FINDINGS.md) — the ledger of established results with evidence.

# imp-prices — causality in time series: the index-set method against a belief network

A self-contained research package that asks whether the CausalBool index-set
calculus can replace a probabilistic graphical model in a forecasting pipeline,
using crude oil as the test bed.

The chain of sources is three deep:

1. **Alvi, Danish A. (2018).** *Application of Probabilistic Graphical Models in
   Forecasting Crude Oil Price.* University College London dissertation,
   [arXiv:1804.10869](https://arxiv.org/abs/1804.10869). Hidden Markov models
   discretise a macro panel; a belief network is learned over the discretised
   variables by hill climbing; inference on the network gives next month's oil
   regime.
2. **GWP3 (Zhang and Hernandez-Espinosa, 2026).** A partial replication of Alvi
   on an independent 199-month sample. Held read-only in [`reference/`](reference/)
   and [`doc/`](doc/). The procedure replicates; the magnitudes do not.
3. **This package.** The index-set mirror: the same data, the same splits, the
   same metrics, with the belief network replaced by a deterministic index-set
   network selected by description length.

## The question

Not "can we forecast the oil price". The literature already says the direction of
crude is close to unforecastable, and nine levels of the `index-deconvolution/`
programme say the same thing about every instrument tested. The question is
sharper and it is methodological:

> **Does an exact, parameter-free causal calculus recover more usable structure
> from a short macro-financial sample than a probabilistic graphical model fitted
> to the same sample?**

A conditional probability table for a node with *k* parents at three states costs
3^k(3−1) free parameters, estimated here from 139 monthly observations. A gate
costs none: it is one of twelve named Boolean functions, or a compressed DNF. The
adaptation therefore converts an ill-posed estimation problem into a search over a
finite hypothesis class ordered by description length. Whether that trade pays is
an empirical question with a measurable answer, and the answer is the deliverable
— including a negative answer.

## Status

Phase 1 in progress. 45 tests passing.

- **Reference parity** established on 3,124 numbers (bitácora 01, C1–C4).
- **Gate 1.0**, the pre-registered feasibility test: there is structure in the
  panel and it is *persistence*. Nothing adds to it — adding all six other series
  to the target's own lag gives an excess of +0.0073 over a persistence-preserving
  null, *p* = 0.323; the four macroeconomic series give −0.0003, *p* = 0.638. This
  explains, rather than merely reproduces, why the GWP3 belief network tied
  persistence (bitácora 02, C5–C10).
- **Comparison arm** ported and asserted cell for cell. Its selected causal graph
  turns out to be **orientation-unstable**: two Markov-equivalent variants occur
  across interpreter hash seeds, reversing the arrows GWP3 Figure 8 reports
  (bitácora 03, C11–C14).
- **Next:** B4, the description-length comparison, which needs the index-set
  encoder.

**Executed notebooks** carry the confirmed results as reproducible evidence:
[`notebooks/00_reference_parity_and_feasibility.ipynb`](notebooks/00_reference_parity_and_feasibility.ipynb)
(C1–C10) and
[`notebooks/01_comparison_arm_and_orientation.ipynb`](notebooks/01_comparison_arm_and_orientation.ipynb)
(C11–C14). Every number in them is recomputed rather than quoted, and the two
Markov-equivalent graphs of C13 are drawn from the sweep that found them.
Notebooks are *generated* from `notebooks/build_NN.py` rather than hand-edited, so
they cannot drift from the code they document.

See [`FINDINGS.md`](FINDINGS.md) for the ledger.

### Reproducing

```bash
.venv/bin/python -m pytest -q                              # 45 tests
.venv/bin/python scripts/gate10_feasibility.py --shuffles 1000
.venv/bin/python scripts/phase1_stability.py --seeds 20

# regenerate and re-execute the notebooks
cd notebooks && ../.venv/bin/python build_00.py && ../.venv/bin/python build_01.py && cd ..
.venv/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/0*.ipynb
.venv/bin/python scripts/check_notebooks.py notebooks/0*.ipynb
```

The validation grid of the belief network is reproducible only up to three BDeu
edge counts, because pgmpy breaks score ties in hash order; see C12. Everything
that determines an outcome is hash-invariant and is asserted as such.

## Layout

| Path | Contents |
| --- | --- |
| `doc/` | The GWP3 report, the assignment brief and the executed GWP3 notebook |
| `reference/gwp3/` | The GWP3 pipeline, its `results.json`, its discretised frames and its LaTeX source — read-only, consulted for exact comparison targets |
| `reference/figures/` | The twenty-five GWP3 figures, the replication targets |
| `data/monthly/` | `sterilized_monthly_data.csv` — the 199×7 panel, 2010-01-31 to 2026-07-31 |
| `data/daily/` | Daily WTI futures and the raw FRED pull, held for the Phase 3 frequency extension |
| `bitacora/` | The scientific logbook: 00 kick-off, 01 reference parity, 02 Gate 1.0, 03 comparison arm |
| `src/imp_prices/` | `config`, `data`, `discretise`, `feasibility`, `controls`, `belief_network` |
| `tests/`, `results/`, `figures/`, `notebooks/` | As in the sibling replication packages |
