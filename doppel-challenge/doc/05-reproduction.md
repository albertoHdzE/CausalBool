# Repaired exact study

The historical files under `out/`, `runs/`, and the pilot directories are
exploratory and are retained unchanged. Repaired records are written to a new
directory.

From the repository root:

```sh
PYTHONPATH=doppel-challenge/src python -m doppel_challenge \
  --out-dir doppel-challenge/results/exact_small
```

After a contract or implementation change, regenerate the namespace once
with `--fresh`; subsequent invocations use deterministic resume:

```sh
PYTHONPATH=doppel-challenge/src python -m doppel_challenge \
  --fresh --out-dir doppel-challenge/results/exact_small
```

The command runs the prespecified N=6 ring, sparse-random, modular, and hub
families with two independent seeds, separate edge additions/removals, exact
full-state enumeration, max in-degree 3, no empty inputs, and no self-loops.
Each perturbation has an atomic checkpoint and a self-digest. Re-running the
same command resumes accepted cases. `study_summary.json` is the only summary
for this repaired run; `summary.json` within each family/kind directory retains
the declared denominator, exclusions, failures, and constrained value.

No exact claim is made for larger N by this path. Approximate trajectory
estimators, finite-observation detectors, and a paper are follow-on work that
must consume validated artifacts and declare their uncertainty model.

To regenerate the descriptive report from only accepted rows:

```sh
PYTHONPATH=doppel-challenge/src python -c \
  'from doppel_challenge.analysis import analyse_validated_study; analyse_validated_study("doppel-challenge/results/exact_small", out_path="doppel-challenge/results/exact_small/analysis.json")'
```

The manuscript source compiles with:

```sh
pdflatex -interaction=nonstopmode -halt-on-error \
  -output-directory /tmp/doppel-paper doppel-challenge/paper/main.tex
```

## Optional dependency quarantine

The current environment has `psutil` but does not provide `pybdm`. Parent
engine and analysis checks that require the native BDM backend are therefore
quarantined; no BDM number is used by the exact repertoire study. The release
audit reports `pybdm.status = "quarantined_missing"`. Installing the pinned
optional dependency (`pybdm==0.1.0`) is required before re-running those
checks, and their results must remain separate from the exact-study gate.

The doppel-challenge contract suite is dependency-free and currently passes
55 tests. The root repository’s broader suite also has unrelated optional
plotting/BDM checks; a missing optional dependency is a blocked validation
item, not evidence for or against the scientific claims in this project.
