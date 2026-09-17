# Final independent replication, version 1

This protocol is frozen before computing the new outcomes. Its purpose is to
check the stability of the previous program/BDM/dynamics results on a larger
set of generator seeds. It is a fivefold replication of the existing design,
with the algorithms, observables and admissibility rules held fixed.

## Sample and construction

- Main: N = 8, 10, 12; ring, sparse_random, modular, hub; seeds 1000–1099.
  There are 1,200 base draws and 2,400 addition/removal catalogue definitions.
- Pilot: the same sizes and families, seeds 2000–2002 (36 base draws), plus
  the existing separate all-gate stress cases. Pilot outcomes are not pooled
  into main estimates.
- Use `bounded_indegree_v1`, maximum indegree five, no self-loops or empty
  target input rows, existing gate assignments, radius-one EDGE_ADD and
  EDGE_REMOVE catalogues, unchanged gate parameters and arity checks.
- All candidate matrices, exclusions, identity rows and content IDs are frozen
  before execution. Repeated complete networks share computation within a
  stage and retain all their declared catalogue memberships. No draw is
  replaced because it duplicates a network or gives an inconvenient result.
- New seed ranges do not guarantee distinct network content. Report actual
  overlap with the previous main/pilot and between the new main and pilot.
  Ring and hub vary gate assignments with seed while holding their structural
  template fixed. They are not 100 independently sampled graph structures.

## Questions and analysis fixed in advance

1. Does one shared program exactly reproduce every ordered output row for
   every declared main network? This is a correctness gate, not a statistical
   hypothesis. Expansion relative to raw is valid and remains reported.
2. Estimate program/raw ratio, program bits, BDM, changes in program/BDM,
   total variation, Jensen–Shannon divergence and finite forward-KL rate.
   Use the same original-output BDM convention (pybdm 0.1.0, 4×4 blocks,
   PartitionIgnore after zero padding); disclose N=10's 2,048 padding bits.
3. Average nonidentity effects within each base and perturbation kind; then
   weight base draws equally within each size/family/kind stratum. Empty
   catalogues have undefined means and remain explicit in denominators.
4. Use 5,000 base resamples with seed 20260911 plus the sorted stratum index,
   percentile 95% intervals, and Spearman correlations of base means within
   each stratum. Do not pool additions/removals for inference; do not treat
   perturbations as independent replicates. Joint cross-stratum uncertainty,
   if later needed, must resample seed blocks because seeds recur across sizes.
5. Compare all 24 stratum estimates with the earlier study, including changes
   of sign and discrepancies. Do not choose outcomes or stop sampling based
   on effect sizes, significance, compression success or correlation signs.
   This is a prospectively specified replication analysis, not a powered
   hypothesis test; no claim of a guaranteed precision follows from 100 seeds.
6. Retain L_SINGLE_TARGET and L_LINEAR, KL budgets 0, 0.1, 0.25 and 0.5,
   primary C=0.25, and all existing frontier/relaxation checks. Infinite KL is
   explicit; incomplete catalogues cannot certify optima.

## Execution and stopping

Use the existing verified owners and fresh concurrency calibration: serial
references for 48 calibration networks, followed by two sweeps of eligible
8/16/24-worker configurations. Select the smallest configuration within 5%
of the fastest eligible median, reserving four CPU cores and one third of RAM.
Use one Wolfram lane with 48-case transactions; GPUs have no validated backend.

Preflight requires the full existing prerequisites, the new controller tests,
and verification of the previous final release and all frozen source hashes.
No change to the previous experiment or its source namespace is required.

The pilot has a one-hour stage budget, and the main has a 24-hour stage budget,
both including their normal audits and summaries. Calibration is separate and
has a one-hour controller timeout. Stage workers retain the existing
300-second timeout and one-million-node compiler limit. Main admission requires
an accepted complete pilot and twice its measured stratum-scaled forecast to
fit in 24 hours. A preliminary forecast from the earlier experiment is only
planning information, never admission evidence.

Failures, missing dependencies, stale source hashes, invalid checkpoints or
an exceeded forecast stop the controller with explicit status. No automatic
sample reduction, outcome-driven seed replacement, timeout increase or failed
record retry is permitted. The next process does not continue merely because
the preceding process exited normally: sealed audit flags and coverage must pass.

The controller persists logs, stage status, checkpoints and stop reasons. It
can resume accepted stages with identical manifests and execution settings.
A controller lock prevents concurrent runs. Completed computation has status
`computation_complete_awaiting_analysis`; it is not a scientific-analysis release.
The final analysis and notebook still require reconciliation and verification
against these new records before the new study can be declared released.

## Reproduction

From the repository root:

```sh
PYTHONPATH=doppel-challenge/src python tools/joint_final_phase/run.py --action prepare
PYTHONPATH=doppel-challenge/src python tools/joint_final_phase/run.py --action launch
PYTHONPATH=doppel-challenge/src python tools/joint_final_phase/run.py --action status
```

Default output: `doppel-challenge/results/joint_degree5_final_replication_v1`.
`launch` starts a detached local controller; `run` is its foreground equivalent.
`controller.log` and the sealed `controller_status.json` report progress.
Previous results remain an external comparison dataset, not pooled new evidence.
