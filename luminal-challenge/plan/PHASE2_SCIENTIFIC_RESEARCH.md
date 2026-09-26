# Scientific diagnosis and proposed next method

2026-09-24 · Codex · design research, not a measured compiler improvement.

## Finding 1: the current expansion is a neighborhood operator, not a distinct learned predictor

Let E be the observed elite set of B-bit indices and let Q be ANY exact union of Boolean cubes representing E. Let R(Q) free each fixed coordinate of each cube separately, then take the union. Let N1(E) be the union of the one-bit-flip neighbors of members of E. Then

    R(Q) \ E = N1(E) \ E.

Proof, forward: a point in an expanded cube either belonged to that cube already, or differs in the released coordinate from a point in the original cube. If it is not in E it is therefore a one-bit neighbor of E. Reverse: take x outside E and e in E differing in exactly coordinate j. Some original cube contains e. Coordinate j cannot be free in that cube, because then x would already be in E. Freeing j therefore includes x. Empty/full universes and zero-bit layouts have no exceptional novel points. Removing any larger training exclusion set T containing E preserves equality.

The implementation's ordered_union emits ascending unique indices; one_bit also sorts unique neighbors. Thus after excluding training points the complete novel sequences agree, not just the sets. Timed prefixes may differ because construction, duplicate and bookkeeping costs differ. This result does NOT prove equal wall time or rule out an efficient compressed representation; it rules out a distinct set of predictions from this expansion alone.

Taking the union of expansion depths 1 and 2 gives the same novel set as Hamming distance at most 2 from E. Comparing that to one-bit mutation confounds search radius with learning. A matched-radius baseline is necessary.

This derivation is ours in this review; novelty relative to all literature has not been established. Actual-code checks pass for all 278 elite sets at widths 0–3 and 500 seeded larger sets at widths 4–8. See scientific_design_20260924/check_expansion_equivalence.py and EXPANSION_EQUIVALENCE.json under results/phase2_structural_encoding/. The finite checks support the general proof; they do not substitute for it or measure performance.

Consequence: the previous optimization plan's larger fixtures remain useful, but its depth-1/depth-2 expansion selection is not an adequate test of predictive learning. The new protocol replaces that experiment. Original H4 stays INCONCLUSIVE; this finding does not invalidate accepted non-model Phase 2 comparisons.

## Finding 2: the current target list can miss admissible product trade-offs

The accepted controller asks a small list of (cycle ceiling, scratch ceiling) queries. These rectangles are heuristics; they need not cover every strict improvement of J=C*S. Searching only more of the same rectangles may miss an improvement even when a local physical domain could contain it.

A concrete objective-space counterexample is incumbent (10,10), J=100, versus (12,8), J=96. Calling the actual targets_for owner with nonbinding lower bounds/horizon produces (9,10), (10,9), (11,9), (9,11); none contains (12,8). PRODUCT_TARGET_COUNTEREXAMPLE.json records this. It proves a gap in the target geometry, not the existence of that particular physical compilation in any measured program.

For positive integer C,S and incumbent J0, an improvement satisfies C*S <= J0-1. If valid lower bounds are LC,LS >=1, every such improvement must satisfy

    C <= floor((J0-1)/LS), S <= floor((J0-1)/LC).

Use those necessary caps plus the existing declared horizon, machine scratch bound and chosen neighborhood, then enforce the ACTUAL product cutoff during branch-and-bound. Do not replace the product by independent desired reductions in both C and S. This preserves all strict improvements within that declared neighborhood relative to the uncapped domain. It does not establish completeness over schedules beyond the neighborhood/horizon. If a program has zero footprint or a zero objective, handle it without dividing by zero; there is no strictly smaller nonnegative product than zero.

## Research basis and limits of transfer

These are primary sources, consulted on 2026-09-24. Their empirical improvements belong to their problems and machines; none proves an improvement for Luminal or originality of our proposed combination.

| Source | Relevant result or method | Proposed use here |
|---|---|---|
| Castañeda Lozano et al., *Combinatorial Register Allocation and Instruction Scheduling*, 2019, [paper](https://arxiv.org/abs/1804.02452) | Joint scheduling/allocation, propagation and branch-and-bound can trade compilation effort for output quality. | Keep joint index decisions; add sound domain filtering and a direct product objective. We do not import Unison or its machine-specific transformations. |
| Shaw, *Using Constraint Programming and Local Search Methods to Solve Vehicle Routing Problems*, CP98, [publisher](https://link.springer.com/chapter/10.1007/3-540-49481-2_30) | Large neighborhoods release related decisions and repair them through constraint search. | Release groups implicated in schedule length or memory pressure, then solve using our index representation. Transfer to this compiler is a hypothesis. |
| Harvey and Ginsberg, *Limited Discrepancy Search*, IJCAI 1995, [paper](https://www.ijcai.org/Proceedings/95-1/Papers/080.pdf) | Search that permits deviations from a preferred decision order. | Try low-discrepancy combinations rather than spending the whole budget below one early choice. Our finite frontier implementation is a specified adaptation, not a reproduction of their algorithm. |
| Ohrimenko, Stuckey and Codish, *Propagation via Lazy Clause Generation*, 2009, [author institution](https://research.monash.edu/en/publications/propagation-via-lazy-clause-generation/) | Constraint propagation can expose logical reasons for rejecting assignments. | Require checkable reasons for every new pruning rule. Full clause learning/SAT integration is deliberately deferred; state-dependent rank codes make careless reuse unsafe. |
| Gasse et al., *Exact Combinatorial Optimization with Graph Convolutional Neural Networks*, NeurIPS 2019, [paper](https://proceedings.neurips.cc/paper/2019/hash/d14c2267d848abeb81fd590f371d39bd-Abstract.html) | A learned policy can guide an exact search rather than replace feasibility constraints. | Use learning only to rank candidates. A small schema-valued tree suits our standard-library constraint; we are not reproducing their GNN or transferring its reported gains. |

## Proposed solution

The proposed method is objective-directed index search with sound propagation, multiple related-decision neighborhoods, resumable exploration and an optional supervised schema ranker. Exact schemata/structural decoding remain the representation and validation boundary. The learned tree also represents index regions as decimal anchors plus free-coordinate masks, but attaches estimated usefulness to regions rather than declaring them feasible or good by theorem.

The ranker learns from all observed training outcomes, including poor ones. Its probability estimates change search order only. This separates two notions previously conflated: a logically certified schema may eliminate candidates; a statistically estimated schema may prioritize candidates but cannot certify correctness or prune the remainder as impossible.

The explanation is falsifiable. Product cuts should find trade-offs missed by target rectangles; propagation should reduce explored states enough to pay for its cost; multiscale traversal should improve anytime quality; informative training labels should rank unseen candidates better than shuffled labels and matched non-learning orderings. Each mechanism has its own ablation. If costs exceed gains, the development rule retains a simpler candidate and the release records the negative result.

No claim of universal dominance is defensible. The target is the best measured output quality among the named candidates at a fixed budget on a frozen fresh cohort, with compilation cost reported separately. The execution contract is CLAUDE_PHASE2_RESEARCH_PROTOCOL.md; it supersedes the pending optimization campaign's algorithm and learning experiment while preserving historical evidence.
