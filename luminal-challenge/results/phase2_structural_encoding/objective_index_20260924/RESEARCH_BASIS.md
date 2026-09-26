# Research basis

Primary sources behind each mechanism, as listed by the lead in
`plan/PHASE2_SCIENTIFIC_RESEARCH.md` (consulted 2026-09-24). Their reported gains belong
to their problems and machines; none establishes a gain for this compiler, and no claim of
novelty for our combination is made.

| Mechanism here | Source | What we take, and what we do not |
|---|---|---|
| Joint scheduling/allocation with propagation and branch-and-bound (A2, A3) | R. Castañeda Lozano, M. Carlsson, G. Hjort Blindell, C. Schulte, *Combinatorial Register Allocation and Instruction Scheduling*, ACM TOPLAS 41(3), 2019. arXiv:1804.02452 | Joint decisions under one objective, sound domain filtering, bound-based pruning. We import neither Unison nor its models; our rules are the four of protocol section 5, proved in THEORY.md. |
| Related-decision neighbourhoods repaired by constraint search (A4 catalog) | P. Shaw, *Using Constraint Programming and Local Search Methods to Solve Vehicle Routing Problems*, CP 1998, LNCS 1520, pp. 417–431 | Release a group of related decisions (latest issues, memory pressure, contiguous blocks) and re-solve exactly inside it. That the transfer helps here is the hypothesis the ladder tests. |
| Discrepancy-ordered traversal (A4 heap) | W. D. Harvey, M. L. Ginsberg, *Limited Discrepancy Search*, IJCAI 1995, pp. 607–613 | Prefer few deviations from the preferred (incumbent-first) choice. Ours is a best-first heap keyed by (discrepancies, product bound, depth, ranks) with a finite frontier — an adaptation, not their iterative algorithm. |
| Checkable reasons for every deletion (certificates) | O. Ohrimenko, P. J. Stuckey, M. Codish, *Propagation via Lazy Clause Generation*, Constraints 14(3), 2009 | Every deletion/prune carries a local, replayable reason. We do not learn clauses: state-dependent rank codes make naive reuse unsound. |
| Learning to guide, never to decide, an exact search (schema ranker) | M. Gasse, D. Chételat, N. Ferroni, L. Charlin, A. Lodi, *Exact Combinatorial Optimization with Graph Convolutional Neural Networks*, NeurIPS 2019 | A learned model orders candidates; feasibility and acceptance stay with the exact machinery. We use a depth-3 schema tree (standard library), not a GNN, and transfer none of their results. |
| Decision-tree induction with Gini impurity | L. Breiman, J. H. Friedman, R. A. Olshen, C. J. Stone, *Classification and Regression Trees*, Wadsworth, 1984 | The split criterion. Depth, minimum child size, tie-breaking and leaf smoothing are fixed by the protocol, not tuned. |
| Family-stratified percentile bootstrap | B. Efron, R. J. Tibshirani, *An Introduction to the Bootstrap*, Chapman & Hall, 1993 | Programs resampled within family, repetitions averaged inside program; Bonferroni-adjusted percentiles where the protocol requires them. |
