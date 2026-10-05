# Claude: integrate the accepted diagnosis reporting corrections

Codex has accepted report-r3 and approved its two replacement patches. Read
`results/hierarchy_search_diagnosis/supervision/search-diagnosis-v1-r1/closure_acceptance/ACCEPTANCE.md`,
`resource_accounting.json` and `integration_manifest.json` first. Paths here are
relative to `index-deconvolution/` unless stated otherwise. This is integration
only; no new experiment or algorithm development is authorized.

You are not alone in the repository. Preserve other people's edits. Verify the
manifest against the current tree before changing any file; if a patch target
has diverged, stop and report the collision rather than overwrite that work.

Own these active files only:

- `experiments/search_diagnosis/{analysis.py,report.py,cli.py}`;
- `experiments/search_diagnosis/tests/test_reporting_pipeline.py` (new);
- `notebooks/build_18.py` and `notebooks/18_hierarchy_search_diagnosis.ipynb`;
- an appended current-revision pointer in `notebooks/README.md`;
- a new `results/hierarchy_search_diagnosis/integration/search-diagnosis-v1-r1/`
  record directory, plus temporary copies.

1. Save before hashes/status and the active notebook's original bytes in the new
   integration record directory. Preserve a1, both closure packages, report-r2,
   report-r3, all supervision records and scientific owners unchanged.
2. Apply the two accepted replacement patches from
   `review_closure/search-diagnosis-v1-r1-followup/patches/`:
   `R3_R3a_R3b_reporting_pipeline.patch` and `R1R2_build_18_report_r3.patch`.
   Do not first apply the superseded report-r2 patches. Leave the historical
   search-v2 median source repair unapplied.
3. Install the retained, executed report-r3 notebook from that follow-up's
   `corrected/` directory as active notebook 18. Append a README pointer to
   report-r3 and the acceptance record, making the current revision explicit.
4. Verify every patched source equals its accepted report-r3 source byte for
   byte, and the installed notebook equals the accepted executed notebook.
   Check the expected diff and preservation, and retain results. Exact equality
   carries forward the independently passed 51 tests and guarded notebook
   checks; no identical full test or notebook rerun is necessary. Do not call
   the active `analyse` command or any old report/verify command that would
   overwrite a1. Do not change frozen reporting references or identities.
5. Deliver an integration HANDOFF, hashes and its own ledger. State accepted
   report-r3 integrated, with no new scientific result. Stop at that handoff.

Budget remains cumulative: fixtures/development 242.092429 seconds available;
report/verification 246.015955 available. Reserve 30 of the latter for a final
supervisor integration check; allow at most 216.015955 seconds for integration
verification/documentation. Include final handoff time, preserve all historical
charges, and stop before a cap. Do not reset or transfer category allowances.

Do not edit bitacora history, old reports or other notebooks. No diagnostic job,
new seed, search-v3/TILE implementation, next-study launch, commit, push,
publication or recurring task. Protocol design for the next algorithm phase is
a separate task after this integration.
