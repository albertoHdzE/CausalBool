# Finalization of the frozen degree-five experiment

This is a downstream audit and descriptive analysis of `joint_degree5_v2`.
It preserves its manifests, records, summaries, failed attempts, and original
analysis release. No new experimental sample is introduced. The tools live
outside the original study's source manifest, which must still match exactly.

Acceptance contract, fixed before replay:

1. Verify canonical record seals and raw artifact hashes as different contracts.
   Reject missing artifacts, stale references, and changed frozen sources.
2. Replay every main and pilot network against the independent trajectory
   owner; recompile its shared program, check all output bits and exact dynamics,
   and recompute BDM with identical shape, padding, and version. Retain and check
   the historical independent Wolfram evidence; do not describe it as newly run.
3. Regenerate every declared catalogue and exclusion; reconcile every paired
   effect and every constrained frontier with the saved main summary. No failed
   or missing record can enter the analysis.
4. Derive new tables from the verified main summary. Average effects within each
   base, then give bases equal weight within family/size/perturbation kind.
   Keep additions and removals separate. Empty catalogues contribute no effect
   mean and remain explicitly counted. Report 5,000 seeded base resamples and
   percentile 95% intervals as descriptive sampling stability, not confirmatory
   population coverage. Associations use base means within each stratum.
5. Show program and raw binary lengths together, BDM in its own units, and
   dynamical effects separately. Disclose fixed decoder conventions, BDD variable
   order dependence, the degree-five sampling restriction, and N=10 BDM padding.
6. Require the full challenge suite, root description-length regressions,
   corruption regression tests for this audit, and executed notebooks without
   errors or unexecuted code cells. Seal the new release only after these pass.

The old analysis's pooled headline values remain historical descriptions of
perturbation rows. The final analysis explicitly identifies weighting and does
not interpret 21,140 perturbations as independent network replicates.

Reproduction (from the repository root, with the notebook dependencies installed):

```sh
PYTHONPATH=doppel-challenge/src python tools/joint_finalization/finalize.py --action audit
PYTHONPATH=doppel-challenge/src python tools/joint_finalization/finalize.py --action analyze
PYTHONPATH=doppel-challenge/src python tools/joint_finalization/finalize.py --action verify
```

Outputs go to `doppel-challenge/results/joint_degree5_final_analysis_v1`.
Parallel CPU workers are numerical subprocesses, not delegated model agents.
No experimental network record is modified.
