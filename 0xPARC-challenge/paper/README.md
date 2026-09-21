# Manuscript and supplementary information

- [Main paper](response.pdf): natural-language explanations and six figures. Figures 2–3 connect the actual seven-gate majority network, its connection matrix, internal states, patterns and full repertoire; the arithmetic section adds a pipeline diagram running from a stated integer relation, through the gates deconvolution recovers, to verified constraint rows.
- [Supplementary Information](supplementary.pdf): full proofs, conventions, reconstruction limits, Fourier search and validation inputs, arithmetic bounds, witness cases and recorded results.
- [Reading companion](response.md): concise explanation with the network figures.
- Sources: [main](response.tex), [supplement](supplementary.tex).

Figures 1, 4 and 5 also use operation networks: weighted sums and digit recovery, an eight-slot Fourier butterfly example with the actual large stage groupings, and decimal partial products with explicit carries. Their numerical examples are checked before rendering.

The figures use the teal/orange palette and network–matrix–pattern presentation of the earlier Doppel response. The worked graph is the actual emitted five-input circuit. Both figure panels and numerical data are derived from its evaluated states.

## Build documents

From the challenge directory, using the environment established by the project setup:

```sh
PYTHONPATH=src .venv/bin/python tools/build_paper.py
```

This reruns the bounded index-deconvolution examples and the per-question certificates, verifies the stored figure sources and assets by hash, regenerates the recorded results table, and compiles both PDFs. Three LaTeX passes resolve references and the supplementary contents. Checks reject overfull text, unresolved references and words outside the page bounds.

This document build reuses the prior compiled arithmetic and large Fourier results. It does not rerun those experiments. Full scientific verification remains available through the command in the [reproduction guide](../README.md).

## Regenerate all explanatory figures

The plotting environment is separate from the original scientific-run dependency pins. To recreate it with Python 3.13:

```sh
python3.13 -m venv .build/figure-env
.build/figure-env/bin/python -m pip install -r paper/requirements-figures.lock
.build/figure-env/bin/python tools/build_paper.py --regenerate-figures
```

The plotting script evaluates all 32 input states, records all seven internal gate outputs, verifies the threshold output, reconstructs the five functional inputs, expands all ten schemata, and checks the exact 16-index union before rendering. The operation-network checks also verify exact digit recovery, all eight Fourier basis vectors against the direct transform, and every column of the decimal multiplication example. The scripts produce standalone vector PDFs and PNG previews.

- [Circuit, repertoire and schemata](generated/worked_network.json)
- [Complete state and internal-output table](generated/worked_repertoire.csv)
- [Network PDF](generated/majority_network.pdf) and [pattern PDF](generated/majority_patterns.pdf)
- [Figure checks](../evidence/paper_figures.json), [index checks](../evidence/paper_index.json), and [PDF checks](../evidence/pdf.json)
- [Index-deconvolution capacity map](generated/index_deconvolution_capacities.pdf), showing the exact forward, inverse, schema and query stages

The original release record describes the earlier complete verification run. The manuscript revision record identifies the reused evidence and the checks executed for this edition.

- [Query network](generated/query_network.pdf), [Fourier network](generated/fourier_network.pdf), and [carry network](generated/carry_network.pdf)
- [Checked operation examples](generated/operation_examples.json)
