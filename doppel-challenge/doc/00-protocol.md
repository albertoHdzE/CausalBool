# Protocol — Exact Boolean-network repertoire laboratory

| Field | Value |
|---|---|
| Status | Authoritative protocol, version 2.0.0 |
| Project | `doppel-challenge` |
| Parent | `CausalBool` |
| Date | 2026-09-10 |
| Primary object | Basin-weighted, phase-averaged long-run attractor repertoire |

## 1. Scope and claim boundary

This project is a finite-state computational laboratory. Its publication
foundation is an exact, small-network study of how directed-edge perturbations
change the long-run distribution induced by a deterministic synchronous
Boolean network. It does not, by itself, validate a finite-observation
detector, infer a mechanism from an observed distribution, establish a
universal complexity measure, or establish exact large-network scaling.

Historical pilot artefacts under `out/`, `runs/`, and earlier pilot result
directories are retained for audit. They are exploratory and do not enter the
regenerated exact-study denominators.

## 2. Network convention

For (N) nodes, a network is `(A, gates, params)`, where `A` is an (N\times N)
binary matrix with the frozen orientation

\[
 A[\mathrm{target}][\mathrm{source}]=1.
\]

Node inputs are the ascending source indices in its target row. Updates are
synchronous. States are integers `0 ... 2**N-1`, represented LSB-first:
bit `i` is `(state >> i) & 1`. Gate semantics and gate parameters are those
implemented by the parent CausalBool adapter; the exact network and parameter
payload are persisted with every exact record.

The exact study uses the four generated families `ring`, `sparse_random`,
`modular`, and `hub`. It uses maximum target indegree three, forbids empty
target input rows, and forbids self-loops. A generated or perturbed matrix is
admissible only after these rules are applied. Gate arity is checked against
the resulting target row.

## 3. Separate observables

The one-step transition map is

\[
 F_A(x)=x(t+1) \quad\text{for current state }x.
\]

Its uniform-input image histogram is stored as
`one_step_output_distribution`. This is a diagnostic and is never called the
long-run repertoire.

For the primary observable, let (\Gamma_A(x_0)) be the eventual cycle reached
from initial state (x_0), and let (L_A(x_0)) be its length. The exact
basin-weighted, phase-averaged repertoire is

\[
 \mu_A(x)=2^{-N}\sum_{x_0\in\{0,1\}^N}
 \frac{\mathbf 1\{x\in\Gamma_A(x_0)\}}{L_A(x_0)}.
\]

Its support is the union of all attractor-cycle states. Each exact record
stores the transition map, canonical attractor cycles, basin sizes, phase
weights, support, rational probabilities, and floating-point display
probabilities. `compute_repertoire(...)` is the production owner;
`independent_repertoire(...)` is the mandatory independent trajectory owner.

## 4. Perturbations and catalogue

The dynamics are held fixed while only `A` changes. The graph distance is the
number of differing matrix entries. `ball(A0, k, kind)` includes the identity
and every matrix at distance at most `k`, in deterministic combination order.
The independently analysed perturbation kinds are:

- `EDGE_ADD`: only `0 -> 1` changes;
- `EDGE_REMOVE`: only `1 -> 0` changes;
- `EDGE_FLIP`: either direction, available for validation and exploratory work.

The exact study uses `k=1` and analyses additions and removals as separate
estimands. Every row has a stable content-derived `perturbation_id`, changed
target/source edges, graph distance, and an `is_identity` flag. Identity rows
are retained for audit and excluded from attack-frontier optima.

Admissible rows are the denominator for a run. Excluded matrices and failed
processes are retained as explicit diagnostics and are not silently counted
as accepted scientific rows. Perturbations from one base network are clustered
observations; the replication unit is the base network.

## 5. Loss and divergence

The declared loss is evaluated on the full state support:

\[
 \ell(\mu)=\sum_x\mu(x)s(x).
\]

The implementation supports the named losses `L_SINGLE_TARGET`, `L_LINEAR`,
and `L_ENTROPY`; a run records the selected loss and parameters. The exact
N=6 study uses one baseline-support target selected deterministically by seed.

The primary divergence is standard forward KL over the full (N)-bit alphabet:

\[
 D_{\mathrm{KL}}(p\Vert q)=\sum_xp(x)\log[p(x)/q(x)].
\]

Any positive (p)-mass where (q(x)=0) makes the value (+\infty). Persisted
JSON records represent that value with `D_KL_nats: null`,
`infinite_kl: true`, `divergence_status: "infinite"`, and
`p_mass_outside_q_support`. Conditional KL on the support intersection is a
separately named diagnostic and never substitutes for the primary constraint.
Total variation, Jensen–Shannon divergence, cross-entropy, and Jaccard
support distance are finite descriptive diagnostics with their own names.

For a declared KL budget (C\), the finite-catalogue value is

\[
 V_k(C)=\max_{A\in\mathcal P_k^{\mathrm{adm}}(A_0),
 D_{\mathrm{KL}}(\mu_A\Vert\mu_0)\le C}\ell(\mu_A).
\]

The code also reports the unconstrained distributional relaxation

\[
 U(C)=\inf_{\lambda>0}
 \frac{C+\log\sum_xq(x)e^{\lambda s(x)}}{\lambda},
\]

with explicit zero-budget, constant-loss, empty-support, and saturation
boundaries. `U(C)` is an upper-bound benchmark for the network-constrained
value; it is not asserted to be attained by a network perturbation.

## 6. Exact shared program for the whole output repertoire

The authoritative Section 12 representation is now
`compile_repertoire_program(Network(...))`, with codec
`shared_repertoire_program_v1`. Its complete contract, proof obligations,
binary layout, and benchmark command are specified in
[06-shared-program.md](06-shared-program.md).

Inputs remain implicit ordered decimal addresses with LSB-first coordinates.
One shared decision graph and N ordered output references reconstruct the
entire output matrix. Compilation preserves free-coordinate generators and
shared rules without enumerating states, output patterns, or explicit
Sumandos. Optional accepting-path export recovers exact decimal-anchor/free-mask
schemas, including freedom on connected coordinates.

The primary comparison is the logical binary program length, including its
decoding structure, against the already-binary raw matrix length N*2**N.
N and the fixed decoder are shared conventions; byte padding and unmeasured
decoder overhead are disclosed separately. BDM receives the original output
matrix, with shape, version, partition and padding recorded. These are
distinct observables, not universal Kolmogorov complexity.

The previous `compute_whole_repertoire_encoding` and
`compute_full_behaviour_encoding` APIs remain available as legacy column-pair
and pattern-query representations. Their artifacts are retained unchanged.
They internally materialize position sets and must not be used as evidence
of fully symbolic scalability. Their flat numeric lengths are not lengths of
the new executable program. The long-run distribution codec is unchanged.

The new benchmark verifies all N=7/8/10/12 cases exhaustively and independently.
N=100 identity/parity/majority probes have explicitly sampled validation.
A case failure or an incomplete BDM comparison prevents release readiness.
Section 12 loads saved benchmark evidence and does not rebuild large tables.

## 7. Durable execution and provenance

The public exact interface is `run_catalogue(...)`. It writes configuration
and base records, then atomically checkpoints each perturbation before updating
the append-only catalogue history. Resume is deterministic: accepted rows are
not recomputed, and a valid checkpoint can complete an interrupted append.
Retries or failures remain represented by explicit records with process status
and failure class. A catalogue manifest validates expected IDs, latest IDs,
accepted counts, exact namespace, and the scientific digest.

Every record exposes the common fields `observable`, `approximation`,
`estimator_parameters`, `uncertainty`, `process_status`,
`accepted_validation`, `provenance`, and `scientific_digest`. Scientific
digests omit volatile timestamps and runtime measurements; SHA-256 seals the
complete record. Source-tree hash, Python version, platform, configuration,
seeds, and gate parameters are retained as provenance.

## 8. Approximate scaling namespace

`estimate_repertoire(...)` is a restart/trajectory estimator of the same
long-run observable. It is explicitly approximate, records samples, trajectory
budgets, convergence/truncation diagnostics, uncertainty intervals, and
resource use, and always starts with `accepted_validation: false`.

`run_scale_benchmark(...)` compares the estimator with exact small-network
references and can open only an exploratory follow-up track when every
declared benchmark case passes. `run_scale_benchmark(...)` and
`run_scale_pilot(...)` never certify exact large-\(N\) results or an optimum.
Exact and approximate artefacts have separate record namespaces and output
directories. Incomplete large-\(N\) cases remain reported as limitations.

## 9. Detector boundary

This protocol does not define a held-out observation model. In particular,
membership in a catalogue used to generate an attack is tautological and is
not detector validation. Mechanism collisions can produce identical long-run
distributions for different networks. A future detector study must specify
observed samples or trajectories, benign and attack distributions, noise,
calibration data, false-positive rate, and held-out evaluation before making
detector-performance claims.

## 10. Reproduction and release gate

The subsequent joint validation study has a separate, frozen degree-five
construction and paired program/dynamics protocol; see
[07-joint-study.md](07-joint-study.md). Its degree-five bound does not modify
the original degree-three study or its historical denominators. Both are
experimental sampling constraints, not mathematical limits of the method.

The prespecified initial study is the N=6, four-family, two-seed, separate
addition/removal study in `study.py`. Run it from the repository root:

```sh
PYTHONPATH=doppel-challenge/src python -m doppel_challenge \
  --out-dir doppel-challenge/results/exact_small
```

Run the exact artefact release audit with:

```sh
PYTHONPATH=doppel-challenge/src python -c \
  'from doppel_challenge import run_release_gate; import json; print(json.dumps(run_release_gate("doppel-challenge/results/exact_small"), indent=2))'
```

The manuscript is a follow-on report and may cite only accepted, hashed exact
artefacts. It must not present approximate scaling as exact, use historical
rows in exact denominators, or claim detector performance without the future
held-out study.
