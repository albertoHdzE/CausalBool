# 0xPARC challenge response

This package gives executable constructions and explanations for Q1–Q8. The
authoritative scope and mathematical contracts are in [`plan/MASTER.md`](plan/MASTER.md);
the implementation is under [`src/oxparc_challenge`](src/oxparc_challenge).

The main paper is [paper/response.pdf](paper/response.pdf), with a separate
[Supplementary Information](paper/supplementary.pdf) and an illustrated
[reading companion](paper/response.md). The [manuscript guide](paper/README.md)
explains the document and figure builds. Results live in
[evidence/release.json](evidence/release.json), and SHA256 hashes in
[evidence/manifest.json](evidence/manifest.json). The manuscript edition is
tracked separately in [evidence/manuscript_revision.json](evidence/manuscript_revision.json);
it reuses the recorded large experiments and adds exact network/pattern checks.

From this directory, use Python 3.13, Node/npm, an installed LaTeX toolchain
(`pdflatex`), and Poppler (`pdftotext`). Linux x86_64 and macOS with the pinned
amd64 Circom binary are supported (Apple Silicon requires Rosetta). Set up:

```sh
python3.13 tools/bootstrap.py
```

Setup creates `.venv` with the repository's NumPy 2.4.3 and pytest 9.1.1,
installs transitive Python pins from `requirements.lock`, downloads and
SHA256-checks Circom 2.2.3, and installs snarkjs 0.7.6 from the npm lock.
It uses network access. Runtime and binary versions are recorded by verification.

Run the entire release verification:

```sh
PYTHONPATH=src .venv/bin/python -m oxparc_challenge verify-release
PYTHONPATH=src .venv/bin/python -m oxparc_challenge check-manifest
```

The command verifies required test collection, executes acceptance and affected
legacy Python tests, compiles and audits all four arithmetic families, executes
both target Fourier circuits, builds both PDFs, verifies the stored network figures, and seals final artifacts.
Missing tooling, failures, or unknown outcomes cause nonzero exit. Heavy
checks run sequentially, with recorded time and peak-memory outcomes.
Temporary compiler/witness files are kept in ignored `.build/`.

Run only the bounded checks with:

```text
.venv/bin/python -m pytest tests -q
```

To reproduce individual large checks:

```sh
PYTHONPATH=src .venv/bin/python -m oxparc_challenge.compiled_audit evidence .build/compiled
PYTHONPATH=src .venv/bin/python -m oxparc_challenge.fourier_validation 32768 evidence
PYTHONPATH=src .venv/bin/python -m oxparc_challenge.fourier_validation 65536 evidence
```

Examples (after setting `PYTHONPATH=src`):

```python
from oxparc_challenge.recovery import recover
secret = [3, 8, 19]
assert recover(3, lambda q: sum(a*b for a, b in zip(q, secret))) == secret
from oxparc_challenge.boolean import build_majority, evaluate_boolean, verify_majority
circuit = build_majority(5)
assert evaluate_boolean(circuit, [1, 0, 1, 0, 1]) == [1]
assert verify_majority(circuit)['status'] == 'PASS'
from oxparc_challenge.gadgets import build_factor64, witness_factor64
from oxparc_challenge.row_evaluator import check_rows
assert check_rows(build_factor64().to_dict(), witness_factor64(15, 3, 5)) == []
```

Published Fourier costs use the stated serial-operation model; they are not
ciphertext benchmarks. Actual ZK proofs, CKKS timing, and a fully materialized
2025-input majority circuit remain deferred. No publishing, pushing or merging
is part of this implementation. The original `doc/` and `analysis/` files are
dated preliminary evidence; final results are in `evidence/`.
