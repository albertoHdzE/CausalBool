# Proposed next delegation — multilevel abstraction-validation design

When the user sends this task, complete the design phase below. It does not
authorize implementing or running the resulting experiment.

## Objective and ownership

Prepare one finite, executable research protocol that tests whether candidate
abstractions suggested by multiple word widths and levels preserve declared
dynamics and interventions. Use the accepted corrected causal-target contract
and `REVIEW.md` beside this file, including its interpretation notes.

The user delegates selection of a small illustrative model class, state encoding,
candidate-map family and intervention set to you within these constraints. Do
not return those routine choices as questions. Explain your choices and their
limits. Your aim is a useful validation design, not a new compression contest
or a claim of a universally novel abstraction criterion.

Write only into a new directory:
`index-deconvolution/results/causal_abstraction_design/abstraction-design-v1-r1/`.
You are not alone in the repository. Preserve notebook19/build19, all sources,
protocols and historical results. Read existing implementations but execute none.
No package, simulator, map search, sampler, notebook, dependency installation,
benchmark, encoder or query learner is authorized. No commit, push, publication
or recurring task.

Separate allowance: 1,800 seconds controller wall, at most 1,500 for you and 300
reserved for Codex. Stop optional work at 1,200 seconds; preserve failed attempts
and finish a truthful handoff. Do not transfer unused time from earlier phases.

## Concrete design requirements

1. Choose a finite Boolean state space with at most 10 bits and fully specified
   deterministic dynamics. Prefer an existing owned model or a short declared
   family with exact ground truth; no random generator or newly executed model.
   Specify bit order, state-to-string encoding, temporal sampling and intervention
   timing. Keep this simulator access distinct from unknown-string discovery.

2. Declare a finite candidate family with explicit formulas and a computable cap
   on its size. Include multiple word widths/origins and at least two candidate
   abstraction levels where meaningful. Every alpha must be the same function
   of state across examples: per-string first-occurrence token IDs cannot be
   treated as globally stable macro labels without a defined alignment rule.
   Distinguish reversible recodings from lossy maps and nesting imposed by the
   analyst from repeated structure found by the method. Preserve ragged tails
   when relevant; no information loss hidden as preprocessing.

3. State how occurrence gaps would propose or rank candidates. Exhaustive
   evaluation of the declared family must be a reference if computationally
   feasible, so a scheduling improvement is not mistaken for better attainable
   abstraction. Distinguish a statistic over one state's encoding from a
   statistic requiring a temporal history; a history-based alpha requires an
   explicitly declared extended state. Do not force gaps, grammar and fractality
   into a causal claim when the proposed setting does not test them.

4. Declare micro interventions including identity, macro operations and beta.
   Supplied macro maps must be specified independently of checking their success.
   If maps or beta are instead inferred, state the finite search/selection rule,
   charge that search, label the result as induced-model discovery, and separately
   evaluate it. Do not construct a macro map from every tested transition and
   then claim agreement on those same transitions as predictive validation.
   Test consistency of interventions sharing beta and domain/codomain closure.

5. Include positive controls with a known nontrivial valid abstraction, negative
   controls with autonomous consistency but intervention failure, and constant
   and identity maps. They validate the checker, not a discovery claim. The
   substantive question must go beyond reproducing W3/W4. Separate choosing
   among candidates from evaluating supplied candidates; state exactly what a
   success or a failure would establish. Exhaustive finite verification is valid
   for its declared domain; any generalisation claim needs separate held-out
   models or interventions and a justified split.

6. Define endpoints: nontrivial information retained, exact autonomous and full
   intervention consistency, coverage, ambiguity, and selection/verification
   costs. No compression improvement substitutes for these endpoints. Define
   intended/available denominators, failure precedence and missingness. If
   claiming predictive utility, specify a fair baseline with identical access.
   If claiming scale invariance or fractal dynamics, give a separate identifiable
   statistic, null and falsifier; otherwise explicitly leave that claim untested.

7. Produce one draft with exact model/candidate counts, ordering, tie rules,
   budgets, existing source ownership, fixture declarations, validation and
   independent audit requirements, stopping rules and deliverables. All counts
   should follow by hand arithmetic from finite declarations. Mark it
   **NOT AUTHORIZED FOR EXECUTION**. Assess novelty against relevant primary
   literature before claiming any; a carefully labelled validation of a known
   criterion is acceptable. If no useful finite design is justified, explain
   the precise obstacle instead of inventing an experiment.

## Deliverables

`DESIGN.md`, `MODEL_AND_MAPS.md`, `EVIDENCE_AND_LIMITS.md`, `DECISION.md`, at most
one `DRAFT_EXECUTION_PROTOCOL.md`, input/output manifests, before/after preservation
records, attempts and time ledgers, and `HANDOFF.md`. Hash all local inputs read
and record source URLs/versions and inspected sections. Record notebook19 drift
without reverting it. Only document/hash/JSON checks are needed in this phase.

Finish the handoff **ready for Codex review; not yet accepted**, then stop. Do
not execute, partially implement, or schedule the draft.
