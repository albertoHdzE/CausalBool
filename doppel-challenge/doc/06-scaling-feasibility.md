# Step 3.5 — Scaling feasibility gate

The exact long-run repertoire remains the publication foundation. The
large-network implementation in `doppel_challenge.estimator` is a restart
estimator: it samples uniform initial states, follows each deterministic
trajectory until a cycle is detected, and averages the phase-uniform cycle
distribution. It does not enumerate the `2**N` state space. When the
trajectory budget ends before cycle detection, the default estimator records
a thinned post-burn-in finite-horizon window so sampled restarts are not
silently dropped. That result is explicitly incomplete: tail-window stability
is a diagnostic, not proof of cycle convergence.

Every approximate record declares:

- `observable: basin_weighted_attractor_repertoire`;
- `approximation: restart_trajectory_sampling`;
- `estimator_parameters` (sample count, trajectory budget, seed, convergence
  policy, and uncertainty method);
- convergence/truncation and finite-horizon-tail diagnostics, uncertainty
  intervals, wall time, and
  peak traced memory plus process-level resident-set (RSS) measurements; and
- `accepted_validation: false` unless a separate small-network benchmark has
  passed.

`run_scale_benchmark` compares independent seeded estimates against exact
repertoires. The default gate requires mean total variation at most 0.05,
95th-percentile total variation at most 0.10, mean uncertainty coverage at
least 0.90, and a trajectory truncation fraction at most 0.01. Thresholds are
arguments and are persisted in the benchmark record. The default resource
budgets are 60 seconds mean estimator time and 512 MiB mean traced peak
memory and 1 GiB mean process RSS per benchmark case. A failed gate reports
`stop_large_network_track`.

`run_scale_pilot` defaults to sizes 4, 8, 12, 20, 25, 30, 35, 40, 45, 50,
55, 60, 70, 80, 100, 120, and 160 across ring, sparse-random, modular, and
hub families, with two seeded replicates. It emits exploratory
records only; observed constrained payoffs are lower bounds over the sampled
restarts/catalogue and are not exact optima. A normal process exit does not by
itself imply convergence: cases over the truncation threshold are recorded as
incomplete and counted in `n_failures`. The suite separates `process_status`
(whether workers exited normally) from `scientific_status` (whether every
trajectory met the cycle-convergence gate). Exact and approximate outputs
should be stored in separate directories/namespaces.

Example (from the repository root; the module entry point is important on
macOS because it gives spawned worker processes an importable main module):

```bash
PYTHONPATH=doppel-challenge/src python -m doppel_challenge.scale_cli benchmark
PYTHONPATH=doppel-challenge/src python -m doppel_challenge.scale_cli pilot \
  --workers 20 \
  --out-dir doppel-challenge/results/step35_approximate_pilot
```
