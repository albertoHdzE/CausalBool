# Joint validation and exact degree-five study

This is a separate, prespecified experiment (`joint_study`, schema 1), not a
replacement for the historical N=6 degree-three study. The maximum indegree
is now **five**, by user decision. It is a sampling/resource restriction, not
a mathematical limitation of the program compiler or dynamics method.

## Construction and denominators

Generate the existing ring, sparse-random, modular, and hub candidates. Remove
self-edges and, only for target rows with more than five inputs, select five
sources with Python's `random.Random` seeded by the integer SHA-256 of the
canonical JSON tuple `(bounded_indegree_v1, family, N, seed, target)`.
Retain original matrices, generator seeds, and every construction change.
Rows already within the bound are unchanged. This is a bounded construction,
not rejection sampling, uniform sampling of all networks, or an experimental
edge-removal treatment. Store the resulting matrices to avoid reliance on
future generator/library behavior. Base gates use the existing seeded four-
family assignment; all twelve supported gate types are additionally exercised
in a separate stress stratum, not pooled into the scientific sample.

The pilot freezes N=8/10/12, four families, and seeds 100–102: 36 bases. The
main candidate freezes the same sizes/families with seeds 0–19: 240 bases.
For every base, independently enumerate radius-one addition and removal
catalogues, including identity. Persist every candidate ID and changed edge,
and the reason for every exclusion (self-loop, empty input, indegree >5, gate
arity). Gates and parameters stay fixed during each perturbation experiment.
Networks with identical complete content share computation, not catalogue
membership. Identities remain in both catalogues but not frontier optima.

## Joint evidence

Every unique network receives an atomic, sealed record containing the full
network, program bytes and logical lengths, raw N*2**N bits, BDM on the original
matrix, and the exact long-run repertoire. Compilation is non-materializing;
validation and BDM materialize all output rows. N and the decoder remain shared
program conventions; BDM is a separate estimate, not a code length.

The Python worker exhaustively checks each output bit, exact codec round trips,
division-invariant program serialization, independent trajectory reconstruction,
cycles, basins and rational mass. Decoded rows must equal every successor in the
dynamics transition map. An independent Wolfram process verifies the complete
ordered output-matrix digest. Wolfram processes run sequentially. Program/raw
expansion and disagreement in scale with BDM are legitimate results, not failures.

Summary validation checks the distribution codec and NCD symmetry against each
base. Losses remain `L_SINGLE_TARGET` (baseline support index seed modulo support
size) and `L_LINEAR`; KL budgets are 0, 0.1, 0.25 and 0.5 (primary 0.25). Infinite
KL is retained explicitly, with null nonfinite display numbers. An optimum is
reported only after the entire declared catalogue passes; it is checked against
the existing KL relaxation. Perturbations are averaged within each base, then
bases receive equal weight within size/family/kind. Relationships between program
length/BDM changes and dynamical effects are descriptive paired observations,
not independent perturbation replicates or causal/detector validation.

## Execution, gates, and resources

From the repository root, with `PYTHONPATH=doppel-challenge/src`:

```
python -m doppel_challenge.joint_study --action prepare
python -m doppel_challenge.joint_preflight
python -m doppel_challenge.joint_study --action calibrate
python -m doppel_challenge.joint_study --action pilot
python -m doppel_challenge.joint_study --action forecast
python -m doppel_challenge.joint_study --action main
python -m doppel_challenge.joint_study --action audit
```

Default output: `doppel-challenge/results/joint_degree5_v2`. The v1 preflight
evidence is retained: it found the notebook imports cell incorrectly marked
as Markdown, which prevented clean execution. Only that cell's executable
type was restored; its source text was preserved. Both new manifests are
frozen before the pilot. A source/configuration change requires a new directory;
the originals are not overwritten. Provenance covers Python, Wolfram owners,
tests, dependency declarations, protocol documents and notebook source cells.
Preflight requires the full challenge suite, relevant root description-length
regressions, no skipped tests, the Wolfram gate test, existing artifact audits,
and an error-free executed notebook. The executed copy and logs are retained.

Pilot stage budget is one hour; main budget is 24 hours. Each isolated Python
or Wolfram stage is capped at 300 seconds; the compiler allocation limit is one
million nodes. Runtime includes checkpoint checking and finalization. Before a
worker starts, reserve its allowance durably; replace it with measured use on
normal completion. After a crash the reservation stays charged conservatively.
Interrupted execution cannot reset the cumulative budget. File locking prevents
concurrent writers. Completed valid checkpoints are reused; failures stay in
place and halt the stage rather than being silently retried or discarded.

The main gate requires complete pilot records, audit and summary, plus current
preflight evidence. Estimate cost by pilot mean end-to-end worker/reference
time within size/family for the serial runner. For the parallel runner, multiply
the complete observed pilot wall time by the maximum main/pilot network-count
ratio across size/family strata. This conservatively retains stress, startup,
audit and summary overhead instead of summing concurrent CPU times. Twice
this forecast must fit within 24 hours. The safety factor covers variation and
finalization; the hard runtime budget still applies. Missing strata, failed
cases, exhausted budgets and missing BDM block admission. No smaller sample is
substituted automatically. An exhausted pilot requires a new explicit budget
decision, not an unattended main launch.

### Parallel execution profile

The default CLI requires a sealed calibration profile. Select four networks
per size/family stratum (48 total) from the frozen pilot order. First execute
them serially, including individual Wolfram references. Then execute the same
networks with 8, 16 and 24 Python subprocess workers, twice, reversing the order
of worker counts on the second sweep. Compare complete scientific digests to
the serial baseline, not just counts or timings. No failed trial is eligible.
The calibration is separate from the pilot's one-hour experiment budget.

Use one Wolfram reference lane, with batches of 48 cases per kernel invocation.
Every returned network ID, shape and binary value is validated. A non-normal
batch exit cannot certify any prefix. While that lane verifies a batch, Python
computes the next. Coordinator threads launch CPU subprocesses; numerical
work is not confined to Python threads or the GIL. BLAS/OpenMP threads are
capped at one within each worker. At most two batches are buffered; checkpoint
writes and catalogue ordering remain single-owner and deterministic.

Reserve four CPU cores and one third of physical memory for system/headroom.
Admit a configuration only if twice the measured maximum Python worker RSS
times concurrency plus 4 GiB for the coordinator/reference lane fits the other
two thirds. This is measured admission control, not an OS hard memory quota.
Choose the smallest eligible worker count within 5% of the fastest median
end-to-end trial time. Store hardware, timings, RSS, all comparison digests,
and the frozen execution profile. Resuming with a different profile is rejected.
Wall-time reservations cover active and prefetched batches; they do not sum
concurrent workers' CPU time. GPUs are not used: no GPU numerical backend has
been implemented or independently validated for these methods.

`audit_stage` rechecks checksums, IDs, exclusions, serialization, output digests
and transition correspondence; `replay=True` additionally reruns the independent
trajectory owner. Failed/incomplete stages can be inspected but cannot produce
complete-study summaries. Section 12 remains based on earlier audited evidence
until a new joint result passes; sampled N=100 probes remain separate.

“Exhaustive” means every input state and every declared admissible one-edge
perturbation for the selected bases, never all Boolean networks. The experiment
does not establish universal Kolmogorov complexity or unrestricted large-N speed.
