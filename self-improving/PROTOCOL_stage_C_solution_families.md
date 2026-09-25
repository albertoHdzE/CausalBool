# PROTOCOL — Stage C: solution families, forced perturbation and self-consistency basins

**Draft of 2026-09-25. It becomes frozen at the commit that removes this
sentence, and no experiment may run before that commit.** Amendments after the
freeze are dated entries at the foot, each with its reason.

**Depends on:** `PROTOCOL_capability_repertoire.md` (Stage A). Stage C inherits
from it, unchanged:
- the task family (§2);
- the selected model and its hash;
- the first-success times T;
- the tickets and owners.

Stage C adds nothing to the primary hypotheses of Stage A and cannot rescue a
failed one.

---

## 0. The idea, stated so that it can fail

Repeated sampling finds a correct answer by waiting for the model's own
probability mass to land on it [1, 2]. Evolutionary systems built on LLMs make
the model the **mutation operator** and a program the genotype [9, 10, 11], and LLM-driven
mutation is now known to collapse onto previously visited structures [23]. This
protocol tests a different division of labour:

- **Genotype:** a binary structure describing a *plan* of solution steps. We
  hold the exact algebra over it.
- **Development:** the language model turns a plan into a concrete answer, the
  phenotype. It does nothing else.
- **Selection:** an outcome verifier (ORM [4]) scores the answer. An exact
  step verifier (PRM [5, 6]) scores each intermediate state. Both are exact in
  this synthetic family, so neither is a learned, gameable model.
- **Variation:** computed, not sampled. A deconvolved schema of past successes
  says which positions of the genotype are **neutral** (don't-care: moving
  along them keeps a solution in its family [16, 17]) and which are
  **essential** (flipping them changes the outcome). Mutation is directed at
  the essential positions.
- **Memory:** successful families are archived as **schemata**, not as
  individuals [14]. One clause with d don't-cares stores 2^d plans, so the size
  of the archive is a description length. This is the archive of [8] and [12],
  compressed.

The claim is that computed variation reaches correct answers in **fewer
language-model calls** than sampled variation, on the questions where sampling
struggles most. If it does not, the idea is falsified for this family.

---

## 1. Standing rules

Rules R1–R6 of Stage A hold. In addition:

**RC1 — Only language-model calls are counted.** Plan validity, parsing and
verification are free for every arm, because they are exact functions in this
family. The asymmetry is declared, not hidden. Stage C says nothing about
domains where the step verifier would itself be a learned model.

**RC2 — Development is deterministic.** Every plan-conditioned call uses greedy
decoding. The map from plan to answer is then a function, and §5 applies our
dynamics machinery to it without a stochastic approximation. Sampling appears
only in arm (a), whose data are the Stage A times T, reused.

**RC3 — Compliance is measured, never assumed.** A forced plan is forced only if
the model executes it. Every call's realised plan is parsed (§3). If
compliance is low, gate GC2 changes what the result means.

---

## 2. Genotype

The genotype has two parts:
- **Inclusion bits:** 8 bits, one per stage (Stage A §2).
- **Precedence matrix:** P[i][j] = 1 iff stage i is executed before stage j.
  The matrix is written in the adjacency convention of
  `doppel-challenge/src/doppel_challenge/perturbations.py` (`A[target][source]`),
  so the entry for the edge i → j is `A[j][i]`.

A genotype is **admissible** iff the precedence matrix restricted to the
included stages is a transitive tournament, that is, a linear order. All other
entries are don't-care.

**A plan is valid on an instance** iff executing its stages in its order on
that instance gives the cell's correct answer. Validity is computed exactly in
Python, with no language-model call.

The family of valid plans has a known structure, and that structure is the
positive control. Two stages **commute** iff their composition in either order
agrees on all 10^6 six-digit lists. This is checked by exhaustion over the 28
pairs. The orders reachable from the canonical one by swapping adjacent
commuting stages form a Mazurkiewicz trace [18, 19]: the linear extensions of a
partial order. In that family's schema:
- the precedence bits of **non-commuting** pairs are fixed;
- the bits of **commuting** pairs are don't-care.

This is the literal content of the analogy with a gene and its neutral
background. Coincidental equivalences outside the trace (orders that agree on
all inputs without being related by commutations) are enumerated separately
and reported.

**Gate GC0 — something to search.**
- Heavy-tail cells are the cells with y_256 = 0 in Stage A, or with median
  T > 64.
- At least 20 heavy-tail cells must each have at least three valid plans.
  Otherwise Stage C stops, and that is reported.
- Cells are selected by this rule alone, in pinned lexicographic order, up to
  40 cells.

---

## 3. Development and the realised plan

**The prompt.** A plan g is presented as the Stage A prompt, with the stages
listed in g's order. The model is asked to print every intermediate list. The
template is committed with the freeze.

**Stage identification.** Each printed intermediate list is compared with the
result of applying each of the 8 stages to the previous list:
- if exactly one stage matches, the step is attributed to it;
- if none or more than one matches, the step is marked `?`.

The sequence of attributed stages is the **realised plan** g′ = parse(output).

**The step verifier.** Step t is correct iff its list equals the exact
intermediate list of plan g at step t. The answer is correct iff the final list
equals the cell's ground truth.

**Gate GC1 — parsing.**
- On a pinned calibration set, at least 90 % of outputs must parse into a
  realised plan with no `?`.
- Below that, the step verifier is not exact in practice. §5 does not run, and
  §4 runs on the outcome verifier alone.

**Gate GC2 — compliance.**
- Compliance is the fraction of calls whose realised plan equals the forced
  plan. It is reported per arm.
- If it is below 0.5 in arm (c), a positive HC1 is reported as "reformulation
  helps", not as "forced perturbation helps".

---

## 4. Search arms and the primary test

**Units.** Each unit is a (heavy-tail cell, instance) pair. The instances are
the 8 half-B instances of Stage A. The language-model budget is B = 64 calls
per unit. A unit is solved at the first call whose answer is correct.

| Arm | Variation | Memory |
|---|---|---|
| (a) repeated sampling | sampling at temperature 0.7 on the canonical prompt; this is Stage A's T, reused at no cost | none |
| (b) random valid plans | uniform order over valid plans, without replacement | none |
| (b2) random single-edge mutation | from the last failed plan: one uniformly chosen precedence flip, via `ball(A, 1, "EDGE_FLIP")` filtered by admissibility and validity, without revisiting | none |
| (c) schema-directed | from the last failed plan: the admissible, valid, unvisited single-edge flip that best satisfies the current success schema | the archive (§4.1) |

Arms (b), (b2) and (c) have the same information: validity, the step verifier
and the outcome verifier. **They differ only in how variation is chosen.** Arm
(a) additionally measures the value of plan information over pure sampling.

### 4.1 The archive and the success schema in arm (c)

- **What is recorded.** After every call in arm (c), the record
  (genotype, success) is appended to a global archive. Cells are processed in
  their pinned order, so later cells inherit what earlier cells taught. This is
  "save it as reference for future tries".
- **The schema.** The success function s(g) over the 36-bit genotype space is
  known only on the archived points. The minimal consistent schema (the
  MIN-FEATURES bias [20]) is recovered by the owner once ticket T1 is closed,
  with the number of essential variables bounded by 4. A clause's score is its
  archived success rate.
- **The choice.** Candidates are ranked by the number of top-scoring clauses
  they satisfy, with ties broken in pinned random order. If the archive is empty
  or no clause exists, arm (c) takes the (b2) move.

**The null for the schema.** The archive labels are shuffled once per cell with
a pinned seed, and arm (c) is rerun on the shuffled archive. This keeps the same
machinery and the same number of archived points, and destroys the association
between genotype and success.

### 4.2 Hypotheses

**HC1 (primary).** Arm (c) beats arm (b2).
- **Statistic:** the mean, over units, of the area under the solve curve
  (fraction solved by call n, for n = 1…64).
- **Uncertainty:** a paired cluster bootstrap over cells, with 10 000 resamples
  and a pinned seed.
- **PASS** if the difference is at least 0.05, its 95 % CI excludes 0, **and**
  arm (c) on the real archive beats arm (c) on the shuffled archive by at least
  the same margin.
- The second condition is what makes this a test of schemata, not of the
  search loop.

**HC2 (secondary).** Arm (c) against arm (a), at an equal number of calls.
- Report the fraction of heavy-tail units solved within 64 calls by each.
- This is the "forced, not waited for" comparison of the brainstorm. It is
  secondary because the two arms differ in information as well as in variation.

**HC3 (secondary).** Transfer.
- **Statistic:** the success rate of arm (c)'s *first* call on cells 21–40,
  against arm (b)'s first call.
- **Meaning:** the archive of cells 1–20 predicts which plans the model can
  execute on cells it has not seen.

**HC4 (descriptive).** The success schemata themselves.
- **What to report:** which precedence bits are essential for the model's
  success, beyond validity (for example, "value maps before permutations").
  Each is rendered as a schema clause over stage names.
- This is the answer to "which families of solutions can this model
  execute?".

### 4.3 Fusion as crossover: Archon's operators mapped onto this design

Archon [7] builds inference-time systems from seven LLM components:
Generator, Fuser, Ranker, Critic, Verifier, Unit Test Generator and Unit Test
Evaluator. In this family each has an exact counterpart, and only one of them
introduces new variation.

| Archon component | Role in [7] | Counterpart here | Kind |
|---|---|---|---|
| Generator | samples candidate responses | development of a plan (§3), or sampling in arm (a) | development |
| **Fuser** | merges several candidates into one | **crossover**: arm (d) by the LLM, arm (e) computed | **variation** |
| Ranker | orders candidates by quality | ordering by the step verifier: the number of correct leading steps | selection |
| Critic | lists strengths and weaknesses of each candidate | the step verifier's per-step labels, stated exactly | selection |
| Verifier | checks the reasoning of a candidate | the step verifier (PRM) | selection |
| Unit test generator / evaluator | writes tests and ranks by pass count | the outcome verifier (ORM) on the instance; exact, so no tests are generated | selection |

Ranker, Critic, Verifier and the unit tests are selection operators, and in
this family they are exact and free (RC1). They are therefore not tested as
separate arms. The Fuser is the only component that can create a genotype no
candidate had, so it is the one tested.

**Parents.** Within a unit, after three developed candidates exist, the
parents are the three most recent developed outputs. They are ranked by the
step verifier: the number of correct leading steps, with ties broken by
recency.

| Arm | Every 4th call is replaced by | Counted calls |
|---|---|---|
| (d) LLM fusion | a Fuser prompt: the three parent outputs, each with its intermediate lists, followed by the Aggregate-and-Synthesize instruction of [24] adapted to this task. Greedy decoding. The fused output is parsed into a realised plan as in §3 | 1 per fusion |
| (e) computed crossover | the developed output of a child genotype. The child keeps the best parent's longest correct prefix (by the step verifier) and completes it with the remaining included stages in the relative order of the second-best parent. This is order crossover [25], restricted to admissible, valid, unvisited children. If no such child exists, the (c) move is taken instead | 1 per child |

The other three calls in every four follow arm (c). Arms (d) and (e) are
therefore arm (c) plus a crossover operator, and the comparison with (c)
isolates crossover.

**HC5 (secondary).** Crossover adds to schema-directed mutation.
- **Statistic:** the solve-curve area of HC1, for (e) against (c) and for (d)
  against (c).
- **Uncertainty:** a paired cluster bootstrap, as in HC1.
- Each difference is reported with its confidence interval. **PASS** for an
  operator if its difference is at least 0.05 and the CI excludes 0.

**HC6 (descriptive, and the main reason fusion is here).** What does LLM
fusion actually do? Every fused output in arm (d) is placed in exactly one of
these classes, using the valid-plan families of §2:

1. **Selection:** the realised plan equals a parent's plan.
2. **Recombination within families:** it is none of the parents, but it
   belongs to the union of the parents' valid-plan families.
3. **Novel valid:** it lies outside the parents' families and is valid.
4. **Invalid:** it is unparseable, contains `?`, or is not valid.

For each class, report its frequency, its correctness, and whether the step
verifier's correct steps from the parents were preserved. This fraction is
the PRM-preservation rate.

Archon reports that the Fuser improves as more candidates are supplied, and
that it gains more on instruction following than on reasoning [7]. HC6 asks the
mechanistic question those aggregate numbers cannot: whether LLM fusion
recombines or only selects. It also asks how often its recombinations are
exactly the children that computed crossover would have proposed, which can be
checked directly because (e)'s children are computable for every fusion event.

**Capacity caveat.** Fusion needs the model to read three solutions at once.
The 0.5–3B models of Stage A may be weak at this. That is measured by HC6's
class-4 rate, and a high rate is a finding about small models, not a defect of
the design.

---

## 5. Self-consistency dynamics: cycles and basins (exploratory)

**The map.** Under RC2, the map

F(g) = parse(LLM_greedy(prompt(g)))

is a deterministic map on a finite set, per instance. Its codomain is the set
of realised plans plus a sink ⊥ for unparseable or `?`-containing output.

**The run.** For each unit in cells 1–20, iterate F from every valid plan, and
from the canonical plan, until a genotype repeats or 16 steps pass. Report:
- **Fixed points** F(g) = g: plans the model executes faithfully and
  reproduces. Report the fraction of valid plans that are fixed points.
- **Cycles** of length at least 2: the model oscillates between plan
  families. Report the frequency and length of cycles, and whether they
  straddle correct and incorrect answers.
- **Basins:** for each attractor, the number of valid starting plans that flow
  into it, and whether the attractor gives a correct answer. A correct
  attractor with a large basin is a robust solution family. A large basin
  draining to ⊥ or to a wrong answer is a measurable form of the collapse
  discussed in [13].

This is the attractor landscape of Boolean-network theory [21, 22], applied to
a self-refinement loop [15]. No PASS or FAIL: the section exists to find out
whether the landscape is informative, and any claim about it needs its own
pre-registration.

---

## 6. Positive and negative controls

- **PC1 (must pass before any language-model call).** Deconvolve validity V(g)
  per cell over the precedence bits, with invalid orders as 0 and inadmissible
  genotypes as don't-care. The recovered essential bits must equal exactly the
  non-commuting included pairs (§2), and the don't-care bits exactly the
  commuting ones. This must hold in every cell that has no coincidental
  equivalences. PC1 needs T1.
- **PC2.** A simulated developer replaces the language model. It executes any
  plan correctly, **except** that it fails whenever a planted precedence holds
  (stage x6 before x2), with probability 1. Arm (c) must beat arm (b2) under
  HC1's rule, and HC4 must report exactly the planted clause. If PC2 fails, HC1
  on the real model is not reported.
- **NC1.** A simulated developer whose failures are independent of the plan
  (Bernoulli, with its rate matched to the model's). HC1 must **not** pass. If
  it does, the loop has an advantage that is not due to schemata, and the
  pipeline is repaired.

---

## 7. Owners and tickets (monolithic-code)

| Concept | Owner | Use |
|---|---|---|
| Edge-flip perturbation ball | `doppel-challenge/.../perturbations.py` (`ball`, `admissible_ball`) | arms (b2) and (c) |
| Essential variables, clauses, gate naming | `index-deconvolution/src/deconvolution.py` (`essential_variables`, `minimal_dnf`, `identify_gate`) | PC1, HC4 |
| Attractors and basins | `doppel-challenge/.../attractors.py` (`enumerate_attractors`) and `index-deconvolution/src/reprogramming.py` (`num_attractors`) | §5 |
| Program length, BDM | `src/description_lengths.py` | archive size |

**Tickets. None is solved in this subproject.**

- **T1** (from Stage A): deconvolution of a partially specified function, over
  sparse observations up to n = 36, with a bounded number of essentials. It
  needs a parity guard that it equals the present path on complete tables. Note
  the known failure mode of MIN-FEATURES [20]: a single feature that separates
  the data spuriously. Here every feature is a plan bit, but the owner should
  still report ties among minimal sets rather than pick one silently.
- **T2:** attractor enumeration on an **explicit finite map** (a successor
  table), not only on a `Network`.
  - **Pre-existing duplication (Q2 finding).** `_next_index` exists in both
    `doppel-challenge/.../attractors.py` and
    `index-deconvolution/src/reprogramming.py`. Attractor counting exists in
    both files. Their pairwise disagreement must be measured, and the superset
    promoted, **before** T2 extends either one.
- **T3:** an admissibility predicate `acyclic_on(included)` for
  `is_admissible_perturbation`, meaning the tournament is transitive on a given
  node subset. It is added to the owner, not reimplemented here.

The permutation and bootstrap utilities follow Stage A §7.

---

## 8. Outcomes

| HC1 | Shuffled-archive condition | Reading |
|---|---|---|
| PASS | PASS | Computed variation from exact schemata beats random variation with the same information. This is the paper's second result. |
| difference ≥ 0.05 | FAIL | The loop helps, but not because of the schemata. Report as NEGATIVE for the schema claim. |
| FAIL | — | For this family, sampled and computed variation are equivalent. Report as NEGATIVE. |
| PC2 FAIL or NC1 PASS | — | Nothing is reported; repair first. |

---

## 9. Budget

- **Worst case, arms (b), (b2) and (c):** 40 cells × 8 instances × 64 calls ×
  3 arms = 61 440 greedy calls.
- **Shuffled archive:** a further 20 480.
- **Fusion arms (d) and (e):** a further 40 960. The worst case for Stage C is
  then 122 880 greedy calls, before §5.
- **§5:** at most (valid plans per unit) × 16 per unit.
- Throughput comes from the Stage A smoke run. Nothing is estimated here.

---

## References

1. Brown, B., Juravsky, J., Ehrlich, R., Clark, R., Le, Q. V., Ré, C. and Mirhoseini, A. (2024). Large Language Monkeys: Scaling Inference Compute with Repeated Sampling. arXiv:2407.21787.
2. Schaeffer, R., Kazdan, J., Hughes, J., Juravsky, J., Price, S., Lynch, A., Jones, E., Kirk, R., Mirhoseini, A. and Koyejo, S. (2025). How Do Large Language Monkeys Get Their Power (Laws)? *Proceedings of the 42nd International Conference on Machine Learning*, PMLR 267:53132–53176. arXiv:2502.17578.
3. Yue, Y., Chen, Z., Lu, R., Zhao, A., Wang, Z., Yue, Y., Song, S. and Huang, G. (2025). Does Reinforcement Learning Really Incentivize Reasoning Capacity in LLMs Beyond the Base Model? *NeurIPS 2025*. arXiv:2504.13837.
4. Cobbe, K., Kosaraju, V., Bavarian, M., Chen, M., Jun, H., Kaiser, L., Plappert, M., Tworek, J., Hilton, J., Nakano, R., Hesse, C. and Schulman, J. (2021). Training Verifiers to Solve Math Word Problems. arXiv:2110.14168.
5. Uesato, J., Kushman, N., Kumar, R., Song, F., Siegel, N., Wang, L., Creswell, A., Irving, G. and Higgins, I. (2022). Solving math word problems with process- and outcome-based feedback. arXiv:2211.14275.
6. Lightman, H., Kosaraju, V., Burda, Y., Edwards, H., Baker, B., Lee, T., Leike, J., Schulman, J., Sutskever, I. and Cobbe, K. (2023). Let's Verify Step by Step. *ICLR 2024*. arXiv:2305.20050.
7. Saad-Falcon, J., Gamarra Lafuente, A., Natarajan, S., Maru, N., Todorov, H., Guha, E., Buchanan, E. K., Chen, M., Guha, N., Ré, C. and Mirhoseini, A. (2024). Archon: An Architecture Search Framework for Inference-Time Techniques. arXiv:2409.15254.
8. Zhang, J., Hu, S., Lu, C., Lange, R. and Clune, J. (2025). Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents. arXiv:2505.22954.
9. Lehman, J., Gordon, J., Jain, S., Ndousse, K., Yeh, C. and Stanley, K. O. (2022). Evolution through Large Models. arXiv:2206.08896. Also in *Handbook of Evolutionary Machine Learning*, Springer (2023), 331–366.
10. Romera-Paredes, B., Barekatain, M., Novikov, A., Balog, M., Kumar, M. P., Dupont, E., Ruiz, F. J. R., Ellenberg, J. S., Wang, P., Fawzi, O., Kohli, P. and Fawzi, A. (2024). Mathematical discoveries from program search with large language models. *Nature* 625(7995), 468–475. doi:10.1038/s41586-023-06924-6.
11. Novikov, A., Vũ, N., Eisenberger, M., Dupont, E., Huang, P.-S., Wagner, A. Z., Shirobokov, S., Kozlovskii, B., Ruiz, F. J. R., Mehrabian, A., Kumar, M. P., See, A., Chaudhuri, S., Holland, G., Davies, A., Nowozin, S., Kohli, P. and Balog, M. (2025). AlphaEvolve: A coding agent for scientific and algorithmic discovery. arXiv:2506.13131.
12. Mouret, J.-B. and Clune, J. (2015). Illuminating search spaces by mapping elites. arXiv:1504.04909.
13. Zenil, H., Uthamacumaran, A. and Ozelim, L. (2026). Large Language Models As Shannon Lossy Compressors Not Solomonoff Induction Estimators: The Singularity Is Not Near Without Symbolic Model Synthesis. arXiv:2601.05280v5.
14. Holland, J. H. (1975). *Adaptation in Natural and Artificial Systems*. University of Michigan Press.
15. Madaan, A., Tandon, N., Gupta, P., Hallinan, S., Gao, L., Wiegreffe, S., Alon, U., Dziri, N., Prabhumoye, S., Yang, Y., Gupta, S., Majumder, B. P., Hermann, K., Welleck, S., Yazdanbakhsh, A. and Clark, P. (2023). Self-Refine: Iterative Refinement with Self-Feedback. *NeurIPS 2023*. arXiv:2303.17651.
16. Schuster, P., Fontana, W., Stadler, P. F. and Hofacker, I. L. (1994). From sequences to shapes and back: a case study in RNA secondary structures. *Proceedings of the Royal Society B* 255(1344), 279–284. doi:10.1098/rspb.1994.0040.
17. Wagner, A. (2005). *Robustness and Evolvability in Living Systems*. Princeton University Press.
18. Mazurkiewicz, A. (1977). Concurrent Program Schemes and their Interpretations. DAIMI Report Series 6(78), PB-78, Aarhus University. doi:10.7146/dpb.v6i78.7691.
19. Diekert, V. and Rozenberg, G. (eds.) (1995). *The Book of Traces*. World Scientific.
20. Almuallim, H. and Dietterich, T. G. (1991). Learning with many irrelevant features. *Proceedings of AAAI-91*, vol. 2, 547–552. Extended as: Learning Boolean concepts in the presence of many irrelevant features. *Artificial Intelligence* 69(1–2), 279–305 (1994).
21. Kauffman, S. A. (1969). Metabolic stability and epigenesis in randomly constructed genetic nets. *Journal of Theoretical Biology* 22(3), 437–467.
22. Wuensche, A. and Lesser, M. (1992). *The Global Dynamics of Cellular Automata*. Santa Fe Institute Studies in the Sciences of Complexity, Addison-Wesley.
23. Gurkan, C., Stonedahl, F. and Wilensky, U. (2026). Mutation Without Variation: Convergence Dynamics in LLM-Driven Program Evolution. arXiv:2606.05408. (When an LLM is the mutation operator, 87 % of mutation chains revisit earlier structures, which is the failure mode that computed variation is meant to avoid.)

24. Wang, J., Wang, J., Athiwaratkun, B., Zhang, C. and Zou, J. (2024). Mixture-of-Agents Enhances Large Language Model Capabilities. *ICLR 2025*. arXiv:2406.04692.
25. Davis, L. (1985). Applying adaptive algorithms to epistatic domains. *Proceedings of the 9th International Joint Conference on Artificial Intelligence (IJCAI-85)*, vol. 1, 162–164.

## Amendments

(none)
