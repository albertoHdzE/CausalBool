# Closure of the per-query learner (efficiency phase, R4)

2026-09-25 · Claude Code · plan `CLAUDE_PHASE2_EFFICIENCY_PHASE.md` §3 R4.

**Conclusion.** Under the controller that was measured, a query's learner can hold
at most one valid observation when its model is first prepared. The learner needs
20 distinct validated objects (`schema_ranker.MIN_TRAINING`). So the first
preparation always returns `MODEL_UNAVAILABLE`, whatever the propagation speed.
This architecture is retired. No further learning campaign is proposed or run.

The claim covers **this controller at its first model-preparation boundary**. It
does not cover every possible learner, and it does not cover an observation hook
placed elsewhere. It rests on two assumptions:

- **A1, sound bounds.** The product bound `LC·LS` is a valid lower bound on the J
  of every completion below a node.
- **A2, validator agreement.** A fully assigned leaf that survives propagation
  passes the pinned validator.

A1 is proved in the objective-index protocol and exercised by the inherited
`PropagationSoundness` tests, which pass on R0. A2 held in every retained row:
`discrepancy_count` is 0 in every measured row of the next round. It also held in
every run of the regressions below (0 rejected candidates).

## The invariant, step by step

Line numbers refer to `research/efficiency_search.py` (R0). The parent
`research/next_round_search.py` is given in brackets.

1. **Product-bound pruning at full assignments.** `Propagation.prune` removes a
   child when `LC·LS >= best`, at `:592` [`:557`]. The expander calls it with
   `best_ref() = product`, the J of the epoch's incumbent. The last address
   assignment is where every selected time and address becomes a singleton. There,
   `LC` equals the leaf's cycle count and `LS` equals its footprint, so the bound
   is exactly C·S.
   *Regression:* `LeafBoundIsExact` enumerates every leaf of 22 exhaustible fixtures
   (12 original and 10 recipe fixtures), first without pruning and then at the
   incumbent threshold. It finds `LC·LS == C·S` on all 4,213 unpruned full leaves.
   All 22 leaves that survive at the incumbent strictly improve it, and all 9
   pruned leaves do not.
2. **Only strict improvements survive.** A leaf that reaches
   `_Acceptor.consider` therefore has J strictly below the epoch incumbent. The
   acceptor observes it at `:930` [`:895`], before its own
   `product >= best` test at `:938` [`:903`]. Every observation is a strictly
   improving leaf.
3. **`stop_on_improvement`.** Each A4 query builds its acceptor with
   `stop_on_improvement=True` at `:1830` [`:1754`]. The first strictly improving
   leaf that validates raises `_Improved` at `:978` [`:943`], and the query ends
   `SAT`.
4. **Query-local observations.** `learner_factory(domain)` creates a new learner
   for each query at initialization. Observations are never shared between
   queries.
5. **Epoch disposal.** An accepted improvement ends the epoch. Every resident
   query is finished as `SUPERSEDED` at `:2108` [`:2008`], the resident set is
   discarded at `:2115` [`:2015`], and a new catalog of new queries, with new
   learners, is built from the new incumbent. Nothing carries across epochs.
6. **The half-time exception.** A learned query searches for half its allowance.
   If a leaf is observed after that boundary, the pre-validation deadline check
   raises `_Stop`. Because the query is still inside its full allowance, the
   controller moves it to `model_prepare` (`:2040–2042` [`:1940–1942`]), and the
   leaf has already been observed. This is the only way a query can reach model
   preparation holding an observation, and it holds exactly one. A frontier-limit
   switch (`:2032` [`:1932`]) reaches preparation too, but it cannot add
   observations beyond steps 1–3.

Under A1 and A2, steps 1–6 give **at most 1 observation at the first
preparation**, and at most 1 + (validator rejections) in general. That is below
20. `QueryLearner._prepare` then returns `MODEL_UNAVAILABLE`
(`objective_index_learned.py:111`).

## Why faster propagation cannot supply the labels

None of steps 1–6 depends on time. `ObservationsPerQuery` runs the real controller
on development programs 800000–800019 with a recording learner, under a
**constant clock**, which models infinitely fast search:

- 315 queries: at most **1** observation in any query, and 0 reached preparation.

It then uses stepping clocks so that the half-time boundary is reached:

- 1e-5 s per reading: 330 queries, 1 preparation.
- 1e-4 s per reading: 370 queries, 15 preparations.
- 1e-3 s per reading: 400 queries, 45 preparations.

In every case there are at most **1** observation per query and **0** at
preparation, with 0 rejected candidates. `test_every_observed_leaf_strictly_improves_its_epoch`
confirms step 2 against each learner's own epoch J.

The earlier reading, that faster propagation would let the controller collect
20 labels, is rejected. Search speed changes how many queries run, not how many
labels one query can hold.

## Historical diagnostic

The next round's acquisition pilot found 0/100 development programs with a query
reaching 20 validated observations. That result is **consistent with** this
invariant. It stays a historical diagnostic only: it ran while oracle fixture
qualification used another core, so it is not a clean, isolated timing study.

## Evidence

| What | Where |
|---|---|
| Leaf-bound exactness, observation counts, epoch-J check | `research_tests/test_efficiency_learner_closure.py` (4 tests) |
| Model-phase late-validation seam, now counted | `research_tests/test_efficiency_search.py::ModelPhaseLateValidations` |
| Inherited soundness tests on R0 | `research_tests/test_efficiency_inherited.py` |
