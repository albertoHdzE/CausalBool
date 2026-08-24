# Datasaurus gate verification — DEV-2.1 / DEV-2.2 ratification

Verdict: **ALL GATES PASS**

| gate | claim | result | evidence |
|---|---|---|---|
| G1 | DEV-2.1 render exists at full length | PASS | /Users/alberto/Documents/projects/CausalBool/imp-prices/figures/dev21_c18_seed_sweep.png |
| G2 | pinned map reproduced ELEMENTWISE by exactly the reported seeds | PASS | equals_pinned_map seeds=['19']; prose-triple seeds=['17', '33', '39']; comparison was full winner-frequency map equality, not counts |
| G3 | knob (hash seed) swept over its bracket; same-seed determinism | PASS | 45 seeds incl. duplicate 42; duplicate draws identical=True; winners range 5-7, interior, no ceiling/floor effect |
| G4 | verdict robustness under mechanism: 22 distinct sets >> any hill-climb draw (7) | PASS | index-set instability is sampling-driven; hill-climb variation is pgmpy tie-breaking (same resamples) - different mechanisms, both reported |
| G1 | DEV-2.2 render exists: null histograms with observed anchors | PASS | /Users/alberto/Documents/projects/CausalBool/imp-prices/figures/dev22_c29_nulls.png |
| G2 | common coordinate held (shape AND density matched); moments are CLOSE-not-equal and are REPORTED as such, never rounded into agreement | PASS | primary null means 188.58/212.26 vs prose 189.39/214.83 - published as DIVERGENT/CLOSE in results/c29_density_matched_null.json, not silently matched |
| G3 | N=20000 per cell, SE(mean) ~0.16 bits; seeds 42-45 fixed and recorded; no fitted knob | PASS | sampling SE makes the prose-vs-recomputed gap (~2.6 bits) real, not noise; documented in DEV-2.2 entry |
| G4 | robustness claim SCOPED to matched conventions (triangular/DAG null breaks the ~3sigma reading and is excluded with that stated) | PASS | matched samplers: z_gate in [-3.35,-2.40], share 66-72%; triangular z_gate=-0.75 shown in artifact and excluded from the claim's scope |

Figures: `figures/dev21_c18_seed_sweep.png`, `figures/dev22_c29_nulls.png`.
