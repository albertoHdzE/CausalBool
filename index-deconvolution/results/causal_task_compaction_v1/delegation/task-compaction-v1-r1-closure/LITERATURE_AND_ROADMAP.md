# Where the programme stands

We now have a candidate exact state-compaction component for a supplied finite deterministic model, a declared output and a finite list of intervention transition tables. It returns the smallest full-domain deterministic state grouping preserving that output after every action word. This is established automata theory implemented for the project's contract, not a new causal discovery theorem.

The nine primary no-reduction outcomes are not defects to fix: under those outputs and actions, distinct states are distinguishable. A faster implementation can reduce computation, but cannot reduce the proven minimum cardinality without changing the contract. The M4/T1 gap concerns the restricted old contiguous-word family; arbitrary groupings already recover its 16-state optimum. Adding another candidate to rediscover it is not presently a justified scientific study.

Word widths, nested groupings and occurrence gaps are useful proposal or description devices. They do not guarantee task sufficiency, causal identification, archive savings or fractal dynamics. The exact reference lets us test their sufficiency and state-count optimality rather than presume them.

## Primary reading packet

Codex performed a targeted screen and read the sections noted below, not an exhaustive literature review. Claude must record its own reading and resolve the indicated mappings.

1. Timo Knuutila, *Re-describing an algorithm by Hopcroft* (2001), §§2.2–3.1, particularly state equivalence, congruence and refinement. [Primary PDF](https://www.cs.cmu.edu/~cdm/resources/Knuutila2001.pdf). This anchors the existing core theorem. Distinguish an all-start quotient from minimal recognition from one initial state, and do not attribute Hopcroft complexity to our simple refinement implementation.
2. Kuize Zhang and Lijun Zhang, *Observability of Boolean control networks: A unified approach based on finite automata*, arXiv:1405.6780v2. [Primary PDF](https://arxiv.org/pdf/1405.6780). Read §II model/automata definitions, §III definitions 4–7 and §IV distinctions; focus on Definition 5's pair-dependent distinguishing input. Codex read the model and relevant definition passages. Prove or qualify the mapping of our K*=N to pairwise distinguishability; do not confuse one word per pair with one word for all states. Explain finite named actions, empty-word observations and encoding of non-power-of-two action alphabets.
3. *Minimization of Dynamical Systems over Monoids*, arXiv:2206.15169. [Primary PDF](https://arxiv.org/pdf/2206.15169). Read §§III–V: generalized forward bisimulation, reduction and algorithm. Codex inspected Definition 3 and the associated homomorphism: a variable partition with monoid aggregation induces a restricted state map. Determine when such a map decodes our output and is closed under every T_q, not merely F. This is a relevant established direction for structured grouping, not an already proven solution for our contract.
4. Argyris et al., *Reducing Boolean networks with backward equivalence* (2023). [Primary article](https://pmc.ncbi.nlm.nih.gov/articles/PMC10207686/). Read the BBE definition and preservation properties. Its preserved domain consists of states agreeing within variable blocks; it cannot be substituted silently for our all-state contract. Codex read the definition and preservation discussion. Record this limitation even when reductions are large.

Do not count novelty from new terminology. If access fails, mark the source unverified and narrow the conclusion; do not silently replace full-paper checking with a search snippet.

## Finite completion route

Two remaining delivery rounds are proposed for this **v1 component**, contingent on the checks passing:

1. **Current closure and positioning:** fix the demonstrated audit/API issues, make tests portable, locate the method in prior work, and deliver integration-ready patches.
2. **Integration and documentation after acceptance:** adopt the reviewed patches in the existing owner, provide a stable user-facing contract and worked examples, a reproducible scoped validation command, provenance, explicit computational limits and a release acceptance checklist. No additional benchmark is intrinsically needed for these corrections.

Completion means an exact, tested, documented small finite-model tool. It does not mean a scalable method for arbitrary networks, recovery from incomplete/noisy measurements, or a final holistic causal theory. Those require a chosen application, observation/intervention model and distinct research goals. There is no scientifically honest fixed phase count for that broader aspiration.

The next scientific question should arise from a real need (for example, exact symbolic scaling under the same contract), not from discomfort with a valid negative result. Read prior methods first, state the unresolved gap, then choose at most one prospective experiment. Keep the current exact solver as the small-model reference. Do not start it in this closure.
