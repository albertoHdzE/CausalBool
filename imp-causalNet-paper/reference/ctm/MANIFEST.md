# Vendored CTM table — provenance manifest

File: `K-4x4.csv` — the authors' 4x4-block complexity table (65,536 entries),
as shipped with the official R implementation of "Causal Deconvolution of
Intertwined Data and Networks by Generating Mechanisms" (arXiv:1802.09904).

- **Source repository:** https://github.com/allgebrist/Causal-Deconvolution-of-Networks
- **Upstream path:** `data/K-4x4.csv`
- **Pinned upstream commit:** `76d38039891f770c82454d1b818085bfe7acc021`
  (2018-03-22, "added data and gitignore" — the commit that introduced the file)
- **sha256:** `d0912b8db775f21d4de02d585458449d6e9967cf1641b8370490c379981627ab`
- **Vendored:** 2026-08-24, AUDIT01/T2.3, by direct download of the raw file at
  the pinned commit.

Why vendored: the CTM cross-check (Part X of the walkthrough;
`tests/test_replication.py::test_official_ctm_table_agrees_with_pybdm_entry_by_entry`)
previously depended on an ephemeral clone at `/tmp/cdn`, so on any machine
without that clone the parity check silently degraded to a skip. Vendoring the
exact bytes at a pinned commit makes the check runnable offline and permanent.
Re-verify the hash after any manual refresh:

    shasum -a 256 reference/ctm/K-4x4.csv

This is third-party data used solely for parity verification; it is not part of
this package's own results.
