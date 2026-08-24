# T5.5 SWEEP INVENTORY — post-AUDIT01 accuracy review of replications & notebooks

Generated 2026-08-24 (plan amendment v1.3). Purpose: every executed notebook and
every document quoting numbers must be reconciled against the post-fix state of
the code and artifacts it depends on. This file is the triage; execution follows
the task card in AUDIT_FIXING_PLAN_01 v1.3.

## Triage table (phase 1 — inventory, done 2026-08-24)

| # | object | quotes numbers downstream of changed code? | last-executed status | action class |
|---|---|---|---|---|
| N1 | imp-causalNet-paper `paper_walkthrough.ipynb` | YES — imports renamed module; CTM cell path changed | **re-executed green post-rename, T2.3** (`e348d68`); fresh outputs reproduce every quoted number elementwise | DONE |
| N2 | imp-causal-paper `paper_walkthrough.ipynb` | NO code renames; reads committed artifacts | 26 code cells, 0 errors, **1 unexecuted cell** | RE-EXECUTE + reconcile |
| N3 | imp-causal-paper `sup_info_plots.ipynb` | no | clean | spot-check |
| N4 | imp-pathinfo-paper 5 notebooks | glob `results/runs*.jsonl` (ledgers unchanged by fixes) | all clean, 0 errors | re-glob + diff summary stats |
| N5 | imp-prices notebooks 00–04 | quote C15–C36 era numbers; C18/C22/C26/C29/C36 prose corrected by T2.1/T2.2 | `check_notebooks.py` exit 0 (no errors/unexecuted/widgets) | reconcile notebook text vs corrected FINDINGS wording |
| N6 | index-deconvolution `notebooks/` (16 files) | method-section language changed in README only | not re-executed this wave | execute per WL/python split; verify headless |
| D1 | imp-results.md E. coli row | — | was FALSE ("nothing exists") | **FIXED** `4d9701f` (dated addendum) |
| D2 | index-deconvolution exp04: script pins 10 `.bnet` models, persisted artifact records **8 considered / 8 exact** (n = 9–13; two n=18/40 records ungraded) | — | inconsistency OPEN | adjudicate in sweep: re-run or annotate |
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
