"""causalbool data-layer helpers.

AUDIT03-B. This file did not exist, so `src/data` was a namespace package that
lost the name resolution to the repository-root `data/` directory whenever a
consumer put the repo root on sys.path before `src/`. The visible symptom:

    src/analysis/Cancer_Corruption.py
      ModuleNotFoundError: No module named 'data.cancer_network_builder';
      'data' is not a package

which made that analysis module UNIMPORTABLE. Verified pre-existing by running
the unmodified file out of `git show`, so the AUDIT03 path collapse did not
cause it.

An explicit __init__ makes `src/data` a regular package, which takes precedence
over the root namespace directory.
"""
