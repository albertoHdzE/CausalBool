# T5.5 SWEEP INVENTORY — post-AUDIT01 accuracy review of replications & notebooks

Generated 2026-08-24 (plan amendment v1.3). Purpose: every executed notebook and
every document quoting numbers must be reconciled against the post-fix state of
the code and artifacts it depends on. This file is the triage; execution follows
the task card in AUDIT_FIXING_PLAN_01 v1.3.

## Triage table (phase 1 — inventory, done 2026-08-24)

| # | object | quotes numbers downstream of changed code? | last-executed status | action class |
|---|---|---|---|---|
| N1 | imp-causalNet-paper `paper_walkthrough.ipynb` | YES — imports renamed module; CTM cell path changed | **re-executed green post-rename, T2.3** (`e348d68`); fresh outputs reproduce every quoted number elementwise | DONE |
| N2 | imp-causal-paper `paper_walkthrough.ipynb` | NO code renames; reads committed artifacts | **DONE** — re-executed green from `notebooks/` cwd (`4d9701f`+this wave); every number-bearing output IDENTICAL to committed; only delta = `sys.executable` line: historical run had used ROOT venv instead of the README-prescribed `.venv` (provenance drift, recorded); "1 unexecuted cell" in triage was a false positive (`!source` magic emits no output) | DONE |
| N3 | imp-causal-paper `sup_info_plots.ipynb` | no | **DONE** — executed green (41.7 s) | DONE |
| N4 | imp-pathinfo-paper 5 notebooks | glob `results/runs*.jsonl` (ledgers unchanged by fixes) | **DONE** — `campaign_status.py` regeneration byte-identical to committed block; notebooks error-free | DONE |
| N5 | imp-prices notebooks 00–04 | quote C15–C36 era numbers; C18/C22/C26/C29/C36 prose corrected by T2.1/T2.2 | **DONE** — checker exit 0; pattern scan finds no stale triples; nb03 already carries its own C27 demotion cells (12, 14); no action needed | DONE |
| N6 | index-deconvolution `notebooks/` (16 files) | method-section language changed in README only | **DONE** — 15/15 non-empty notebooks executed 0 errors under root venv (matplotlib stack); `031_financial_honest_negative.ipynb` found to be a **0-byte corrupt stray** and removed (dated here, 2026-08-24; content duplicated notebook 03's topic) | DONE |
| D1 | imp-results.md E. coli row | — | was FALSE ("nothing exists") | **FIXED** `4d9701f` (dated addendum) |
| D2 | index-deconvolution exp04: script pins 10 `.bnet` models, persisted artifact records **8 considered / 8 exact** | — | **RESOLVED — FALSE ALARM (retracted).** Field semantics: `n_models_considered` counts models graded *within the documented n≤16 cap*; the other two are recorded in-artifact as `skipped: too_large` (n=18 budding yeast, n=40 T-cell). Re-ran exp04 today: **8/8 exact reproduced**. My triage misread the field; correction dated here 2026-08-24 | CLOSED |
| D3 | REPRODUCTION_LEDGER sign-agreement claims | DoF paragraph added `3eb87ac` | recorded | none further |
| D4 | comp_paper/method_paper numbers | governed by snapshot gate | **PASS** (112 entries identical, checked 2026-08-24) | keep gating every .tex commit |

## Known ground-truth taxonomy (for claim-scoping across all docs)

| data kind | example | exactness-gradable? | where used |
|---|---|---|---|
| explicit Boolean rules (.bnet) | exp04's PyBoolNet models | YES — repertoire exists | index-set exact recovery (8/8 recorded) |
| automaton rule | ECA rules 0–255 | YES — global map exists | CA arm of T2.4 comparison (10/10 exact), exp03 |
| digitised figure + known rule | Fig. 2 image (rules 60/110) | YES (withheld-ground-truth scoring) | imp-causalNet-paper mirror |
| signed interaction graph, NO rules | RegulonDB E. coli confC | **NO** — repertoire undefined without inventing gates | BDM perturbation signatures only (paper's method) |
| version-substituted network | paper ~9.x vs our 14.5 | numeric equality impossible BY CONSTRUCTION | V3 stamp |
