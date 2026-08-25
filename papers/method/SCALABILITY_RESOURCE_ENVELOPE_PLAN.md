# Scalability and Resource-Envelope Plan for the Method Paper

## Purpose

This document is the source of truth for the new experimental and manuscript phase proposed for the
method paper. Its aim is to replace a broad and only partially aligned `Complexity Analysis` section
with a sharper, more defensible section centred on scalability, feasibility, and resource envelopes.

The proposed section will not attempt to prove the method again. Correctness has already been
established in the manuscript through:

- exact gate-family derivations
- the detailed AND case
- the XOR extension
- the exact 10-node mixed-network analysis
- the overlap/compression treatment
- the new dynamical enrichment layer
- the manuscript's `Validation Evidence` section

The new phase therefore has a distinct role:

> to show the regime in which the exact causal representation becomes operationally indispensable,
> because naive exhaustive materialization becomes computationally or physically meaningless.

This distinction is essential. The new phase is not about replacing correctness. It is about
demonstrating the scalability consequences of the representational shift introduced by the method.

---

## Core Scientific Claim of the New Phase

The method does not defeat the lower bound of materializing a full exhaustive repertoire if the task
is literally to enumerate every row and every output bit. No exact method can avoid that cost when
the full object itself is demanded.

The real gain arises because the method computes a different but exact object:

- not the fully materialized exhaustive table
- but an exact causal representation of the queried behaviour

Accordingly, the new section will defend the following scientific statement:

> The method replaces exhaustive materialization by exact causal representation, and this change of
> representational target preserves exactness while keeping evaluation feasible in regimes where
> exhaustive enumeration becomes impractical or physically meaningless.

This wording should guide the entire design.

---

## Strategic Goal

Produce a publication-grade section tentatively titled one of:

- `Exact Scalability Beyond Exhaustive Materialization`
- `Scalability and Resource Envelope of Exact Causal Evaluation`
- `Operational Regimes of Exact Causal Representation`

The section must answer, with evidence:

1. What exactly is the computational object produced by our method at large scale?
2. Why is the comparison to exhaustive materialization legitimate?
3. At what sizes does naive exhaustive materialization become unrealistic?
4. What are the real observed time and memory costs of our exact method?
5. How do query support size and overlap control scalability?

---

## What This New Phase Is Not

To avoid conceptual drift, the new phase must not become:

- a generic complexity-theory section
- a speed-claims section detached from exactness
- a benchmarking paper inside the method paper
- a comparison to machine learning or statistical fitting
- a proxy for the already-completed correctness evidence

The new phase must remain subordinated to the method paper's identity:

- exact
- causal
- representation-aware
- mathematically disciplined

---

## Phase Structure

The new phase is divided into eight explicit phases. These phases should be followed in order unless
an implementation obstacle requires a local adjustment.

## Phase 1. Formal Scope Refinement

### Goal

Define precisely what is being compared and prevent category errors before any benchmark is run.

### Deliverables

- a fixed benchmark statement
- a list of benchmark tasks
- a statement of fairness conditions

### Scientific Decision

The comparison is not:

- full exhaustive table vs full exhaustive table

The comparison is:

- naive exhaustive materialization of the queried causal object
- versus exact causal computation in compressed form

### Fairness Principle

For every benchmark task, both approaches must be interpreted as answering the same causal question.
If the naive baseline answers the question only by enumerating all rows, while the method answers it
by constructing an exact compressed representation, this difference must be stated explicitly rather
than hidden.

### Benchmark Object

The preferred benchmark object is:

- an exact query on selected output nodes of a Boolean network

because this is the object the paper already studies rigorously:

- local one-sets
- intersections of exact output constraints
- overlap-driven compression
- exact repertoire recovery by deconvolution/unfolding

---

## Phase 2. Benchmark Task Definition

### Goal

Fix a small family of tasks that are scientifically meaningful, executable at large scale, and
directly connected to the paper's mathematical machinery.

### Benchmark Tiers

The new section should use three benchmark tiers.

| Tier | Purpose | Sizes |
| --- | --- | --- |
| `Tier A` | observed exact-method execution under moderate scale | `n = 30` |
| `Tier B` | observed exact-method execution under large scale | `n = 60, 80` |
| `Tier C` | observed exact-method execution under very large scale and theoretical naive envelope | `n = 200` |

### Recommended Exact Tasks

Each benchmark size should include a fixed set of query tasks.

#### Task T1. Single-node exact one-set

- choose one node
- compute its exact one-set representation
- measure time and memory
- record its local arity and support size

Scientific role:

- isolates the simplest exact object
- shows that local causal representation remains trivial even at large `n`

#### Task T2. Small mixed query

- choose a queried set `Q` with `|Q| = 4`
- specify a target output pattern on those nodes
- compute the exact compressed representation
- record support union size `c_q`, overlap multiplicity `mu_q`, free coordinates `n - c_q`

Scientific role:

- directly tests the method's compositional overlap machinery

#### Task T3. Medium mixed query

- choose a queried set `Q` with `|Q| = 8`
- again compute the exact compressed representation
- record the same metrics

Scientific role:

- shows the effect of scaling query scope

#### Task T4. Full-network pattern query

- specify a full output pattern on all `n` nodes when feasible in compressed form
- compute exact query-support statistics and representation size
- do not require full unfolding if the free-coordinate structure makes that pointless

Scientific role:

- provides continuity with the 10-node full-output cases

### Optional Anchor Task

If execution time allows, add:

- `n = 20` or `n = 24`

for a fully executable exhaustive anchor that can be used only as a visual or methodological bridge.
This anchor is optional and should not dominate the new section.

---

## Phase 3. Network Ensemble Design

### Goal

Define how benchmark networks are generated so the results are reproducible and scientifically
interpretable.

### Requirements

- deterministic seeds
- sparse bounded in-degree
- gate-family heterogeneity
- explicit parameter generation for parameterized gates

### Recommended Network Policy

For each `n in {30, 60, 80, 200}`:

- generate `R` random networks with fixed seeds
- use bounded in-degree `d_max <= 4` or `d_max <= 5`
- sample gates from the same catalogue used in the paper:
  - AND
  - OR
  - XOR
  - NAND
  - NOR
  - XNOR
  - NOT
  - IMPLIES
  - NIMPLIES
  - MAJORITY
  - KOFN

Canalising gates may be included, but only if their parameter-handling path is already stable in
the benchmark implementation. If this introduces avoidable implementation noise, exclude them from
the first benchmark version and document that decision explicitly.

### Deterministic Parameter Policy

- `NOT`: select one input from the node's incoming coordinates
- `IMPLIES`, `NIMPLIES`: select an ordered input pair
- `KOFN`: sample a threshold `k` within admissible range
- `MAJORITY`: no extra parameter needed

### Ensemble Size

Initial recommendation:

- `R = 5` networks per size for exploratory runs
- expand to `R = 10` if timings are stable and total runtime remains acceptable

The paper can report medians and ranges rather than single-run anecdotes.

---

## Phase 4. Exact Method Definition

### Goal

Specify what exactly the benchmarked method computes.

### Method Representation

The exact method should compute compressed causal representations rather than unfolded exhaustive
lists whenever the latter would destroy the point of the section.

### Recommended Output Form

For a mixed query `q`, the preferred benchmark output is:

- queried nodes `Q`
- requested pattern
- support union `C_q`
- free coordinates `F_q`
- overlap multiplicity `mu_q`
- reduction factor `R_q = 2^{mu_q}`
- compressed solution object

The compressed solution object may be recorded as either:

- a set of support-level satisfying assignments over `C_q`
- or a `DecimalRepertoire + Sumandos` representation when that is natural

### Exactness Requirement

Every returned benchmark object must remain exact.
No approximate search, heuristic pruning, or Monte Carlo substitution is allowed in the main exact
pipeline.

### Recommended Computational Strategy

For a mixed query:

1. collect each local gate's exact admissible assignments over its own input set
2. take the union support `C_q`
3. enumerate assignments only over `C_q`, not over all `n` coordinates
4. retain those assignments that satisfy the whole query
5. encode the remaining freedom as free coordinates or offsets

This is scientifically aligned with the manuscript's overlap proposition and reduction-factor
corollary.

---

## Phase 5. Naive Baseline Definition

### Goal

Define a legitimate baseline without pretending to run impossible computations.

### Baseline Choice

The baseline is naive exhaustive materialization.

At minimum it conceptually requires:

- enumeration of all `2^n` input rows
- evaluation of the relevant outputs on all rows
- storage or streaming of the resulting exact answer

### Two Baseline Levels

#### Baseline B1. Full output materialization

This baseline constructs the full output matrix `Y in {0,1}^{2^n x n}`.

Raw output lower bound:

`n 2^n` bits

This is the strongest envelope for showing impossibility at very large `n`.

#### Baseline B2. Query-only exhaustive scan

This baseline does not store the whole matrix, but still scans all `2^n` rows to answer the chosen
query.

This baseline is useful because it is fairer to the query-focused method while still retaining the
same dominant combinatorial explosion in time.

### Reporting Policy

For large sizes:

- do not report fake empirical runtime for the naive baseline
- report theoretical lower bounds and idealized extrapolations

This is more honest and scientifically stronger.

---

## Phase 6. Resource Metrics

### Goal

Fix the exact metrics to be measured and reported.

### Metrics for the Exact Method

For each run, record:

- `n`
- seed
- number of queried nodes `|Q|`
- support union size `c_q`
- free-coordinate count `|F_q| = n - c_q`
- overlap multiplicity `mu_q`
- reduction factor `R_q = 2^{mu_q}`
- number of satisfying support-level assignments
- compressed representation size
- wall-clock time
- peak memory

### Metrics for the Naive Baseline

Report:

- total rows `2^n`
- raw output bits `n 2^n`
- raw lower-bound storage in bytes
- idealized streaming or generation time at explicit throughput assumptions

### Throughput Assumptions

To avoid ambiguity, define a few explicit hypothetical row-generation rates, for example:

- `10^6` rows/s
- `10^8` rows/s
- `10^9` rows/s

Then report the resulting time envelopes.

This prevents accusations of arbitrary rhetoric.

### Memory Units

Use both:

- exact scientific notation in bytes
- human-readable unit approximations

---

## Phase 7. Experimental Execution Strategy

### Goal

Specify exactly how the experiments should be run.

### Implementation Choice

Use a paper-local Python implementation for the new benchmark phase.

Reason:

- large-scale resource benchmarks are easier to automate and measure in Python
- the Wolfram environment is currently unreliable on this machine for long execution due to license
  issues
- the manuscript can still present the results in the same reduced symbolic style where appropriate

### Reproducibility Folder

Create a paper-local folder:

- `papers/method/code/scalability_resource_envelope/`

Expected contents:

- benchmark script
- raw JSON results
- CSV summary tables
- manuscript-facing `.tex` table fragments
- short session/log excerpt
- README if needed

### Execution Order

1. run pilot benchmark on one network per size
2. inspect times and peak memory
3. validate that support-union sizes remain in the intended regime
4. expand to the full ensemble
5. aggregate medians, minima, maxima
6. generate manuscript-facing tables

### Stop Conditions

Stop and redesign if:

- support unions become so large that the exact query object itself is being forced toward
  exhaustive behaviour
- parameter-handling bugs appear in a subset of gate families
- timing noise dominates the observed signal

In that case, reduce the query family or tighten the network generation constraints.

---

## Phase 8. Manuscript Integration Strategy

### Goal

Translate the results into a clean new section for the paper.

### Recommended Section Structure

#### 1. Framing paragraph

State:

- correctness was already established
- the present section addresses scalability and operational regime

#### 2. Exact object versus exhaustive object

Define explicitly:

- what the method computes
- what the naive baseline materializes

#### 3. Resource-envelope proposition

Include a proposition such as:

> For full exhaustive materialization, any method must pay at least `n 2^n` output bits, whereas
> query-focused exact causal representation depends on the support-union size of the query and can
> remain tractable when `c_q << n`.

#### 4. Experimental benchmark table

For `n = 30, 60, 80, 200`, report:

- exact method time
- peak memory
- median support union size
- median reduction factor
- naive raw storage lower bound
- idealized naive time envelope

#### 5. Interpretation paragraph

Emphasize:

- the method does not violate exhaustive lower bounds
- it avoids them by computing an exact compressed causal object instead
- this is the operational regime where the method becomes indispensable

---

## Mathematical Statements to Include Later

The manuscript phase should likely include at least one formal proposition and one corollary.

### Proposition A. Exhaustive Materialization Lower Bound

If the target object is the full exhaustive output matrix for an `n`-node Boolean network, then any
method that explicitly materializes that matrix must emit at least `n 2^n` bits.

### Proposition B. Query-Support Dependence

For an exact mixed query `q`, the compressed causal evaluation depends on the support union `C_q`
and overlap multiplicity `mu_q`; the method avoids dependence on the full ambient dimension `n`
except through the free-coordinate bookkeeping.

### Corollary

When `c_q` remains bounded or grows slowly relative to `n`, exact causal evaluation remains feasible
far beyond the regime in which exhaustive materialization is meaningful.

These should be written carefully when the results are in hand.

---

## Data and Artifact Policy

### Mandatory Artifacts

- machine-readable benchmark results in JSON
- manuscript-ready table rows in `.tex`
- session log excerpt with command line and summary
- clear statement of seeds and generation rules

### Optional Artifacts

- a plot of naive storage lower bound vs `n`
- a plot of exact method runtime vs `c_q`
- a plot of exact method runtime vs `n`

### Manuscript-Facing Tables

At minimum generate:

1. network ensemble table
2. exact-method performance table
3. naive resource-envelope table
4. synthesis table joining both views

---

## Risks and Mitigations

## Risk 1. Query support grows too large

### Consequence

The exact query becomes intrinsically large, making the benchmark less informative.

### Mitigation

Constrain:

- query size
- in-degree
- overlap profile

and report support-union statistics explicitly.

## Risk 2. Benchmark looks unfair

### Consequence

A reviewer may say the baseline and the method compute different things.

### Mitigation

State explicitly:

- both answer the same causal question
- the difference is representational
- the naive baseline answers by exhaustive materialization
- the method answers by exact compressed representation

## Risk 3. Large-scale numbers feel rhetorical

### Consequence

Claims may look exaggerated.

### Mitigation

Use conservative lower bounds and explicit throughput assumptions.

## Risk 4. Too many benchmark variants

### Consequence

The section becomes diffuse.

### Mitigation

Use one fixed ensemble design and a small fixed family of query tasks.

---

## Immediate Next Actions

The next operational steps after this planning document are:

1. create the paper-local benchmark folder
2. implement the exact query-focused scalability script
3. implement the naive lower-bound calculator
4. run pilot benchmarks for `n = 30, 60, 80, 200`
5. inspect artifacts and only then draft the manuscript section

This order is important: the section should be written from executed results, not from speculative
language.

---

## Final Instruction

This plan is intentionally stricter than a normal benchmark note because the method paper is already
strong in its exact mathematics. Any new section must preserve that strength.

The new scalability phase should therefore remain faithful to one principle:

> we are not claiming to compute the impossible; we are showing that exact causal representation
> remains feasible precisely because it is not the same object as exhaustive materialization.

