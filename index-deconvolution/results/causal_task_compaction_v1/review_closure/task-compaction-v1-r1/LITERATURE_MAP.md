# Literature map: where the task-compaction component sits

I read four primary sources myself on 2026-10-05. Their versions, the sections read, the
access limits and the SHA-256 identities of the retrieved files are recorded in
`logs/literature_sources.json`. This is a targeted reading of the packet's four sources,
not a survey. Wherever a statement goes beyond what was read, it is labelled a
**hypothesis**.

## Our contract, stated once

Inputs are a finite state set {0..N-1} (here N = 2^n), a finite ordered list of Q
deterministic total transition tables T_0..T_{Q-1}, and an output h: states → labels.
The output is α\*, the coarsest partition of **all** N states (every state is an
admissible start, and nothing is pruned by reachability) such that α(x) = α(y) implies
h(x) = h(y) and α(T_q x) = α(T_q y) for every q. Equivalently, x and y share a block iff
h(T_w x) = h(T_w y) for every finite word w over the Q actions, the empty word included.
K\* = |α\*|. The result is exact and minimal within *all* state partitions (THEORY.md).
The computation is the layer-wise refinement on an explicit table, so time and memory
are at least Q·N.

## Contract comparison

| | **ours** | Knuutila 2001 (§2.3, Prop. 4) | Zhang & Zhang, Def. 5 | GFB (arXiv 2206.15169) | BBE (BMC Bioinf. 2023) |
|---|---|---|---|---|---|
| object grouped | states | states | none (yes/no property of state pairs) | **variables**; the state map ψ_R aggregates each block with a monoid ⊕ | **variables**; blocks of variables forced equal |
| start domain | all N states | all states of a *connected* DFA (connectivity assumed so the quotient is the minimal recogniser from a₀) | all of Δ_N (any pair of distinct initial states) | all states (Thm 1: "for any initial state s₀") | **only states constant on each block** (Prop. 4 / Thm 5 of the supplement, as quoted in the article) |
| transition maps | Q named tables, arbitrary Q ≥ 1 | one per letter of a finite alphabet X | L_u for u ∈ Δ_M, M = 2^m inputs | a single map F (autonomous) | a single synchronous BN update |
| preserved output | arbitrary label map h | binary: membership in A₀ (final states) | H x ∈ Δ_Q | the aggregated state ψ_R(s) itself; no separate output | dynamics on the preserved subdomain; attractors that meet it |
| word quantifier | ∀ words, empty word included | ∀ w ∈ X\* | ∀ pairs ∃ word (U ∈ (Δ_M)^p, p ≥ 1; outputs y₁..y_p, with y₀ entering through "Hx₀ = Hx̄₀ ⇒") | none: one map iterated | none: one map iterated |
| exactness | exact | exact | exact decision | exact on all states (Thm 1) | exact on the preserved subdomain, no spurious behaviour |
| minimality scope | coarsest among **all** state partitions | coarsest congruence (Props 2–4) | not a minimisation | coarsest GFB refining a given variable partition (Thms 2, 4) | coarsest BBE refining a given variable partition |
| computational assumptions | explicit tables; classical refinement, at most N−K₀ strict rounds of O(Q·N) | classical O(\|X\|\|A\|²); Hopcroft O(\|X\|\|A\| log \|A\|) (§3.2 onward, not re-derived) | weighted pair graph over Δ_N × Δ_N | O(\|X\|³) decisions of Ψ, each possibly hard; randomised polynomial for polynomial updates (Thm 5) | SAT per step, at most n steps |
| implementation | `deconvolution.py` (this repository) | textbook | — | ERODE prototype | ERODE |

Licences: the BBE article is CC BY 4.0. The ERODE licence was **not verified** because
no reuse is recommended here.

## The three questions

**1. Is our component an implementation of established theory?** Yes. α\* is the
greatest congruence of the unary algebra ({0..N-1}; T_0..T_{Q-1}) that saturates the
kernel of h. This is Knuutila's ρ_A with the binary final-state partition replaced by
the output partition P₀ = ker h, which makes it a Moore-machine generalisation. Our
code is the layer-wise refinement of his Proposition 4, with the previous label kept in
each signature. Two qualifications carry forward unchanged:

- (a) Knuutila assumes a connected DFA because his goal is the minimal recogniser from
  a₀. We deliberately take the quotient of the *whole* state set, so K\* counts classes
  among states that may be unreachable from any particular start.
- (b) Hopcroft's O(|X| N log N) bound is **not** a property of our implementation. Ours
  is the classical quadratic-worst-case method.

The novelty is the contract and its packaging (named interventions, certificates,
witnesses and an independent audit), not the theorem.

**K\* = N versus pairwise distinguishability (Zhang & Zhang, Definition 5).**
*Proved here (sketch):* K\* = N holds iff every two distinct states are separated by
some word, by the characterisation above. Encode our model as a BCN as follows:

- Choose m with 2^m ≥ Q and set L_u = T_min(u, Q−1). Duplicated tables add no new
  successor pairs, so the set of distinguishable pairs is unchanged; for AUTO cells
  Q = 1 and m = 0.
- Encode h injectively into Δ_Q with 2^q ≥ the number of distinct labels.

Definition 5 asks, for each pair with Hx₀ = Hx̄₀, for an input sequence U of length
p ≥ 1 whose output sequences y₁..y_p differ. A pair with different current outputs is
our empty-word case and is excluded by the antecedent. Output sequences differ iff some
prefix has a differing *final* output. Hence **K\* = N ⇔ the encoded BCN is observable
in the sense of Definition 5**.

The equivalence requires one word **per pair**. It is strictly weaker than Definition 6,
which needs one sequence for all pairs, and by Theorem 4.1 it does not imply
Definition 4. Our 9 primary NO_REDUCTION cells are therefore "observable in the sense
of Definition 5" for their action sets. Neither K\* nor our witnesses say anything about
a single universal experiment. Zhang & Zhang decide a yes/no property and do not compute
K\* when K\* < N.

**2. Does any cited method address scalability without changing the all-state/action
contract?**

- **Hopcroft (via Knuutila §3.2+).** Improves time to O(Q·N log N) under the *same*
  contract, but still needs the explicit N = 2^n tables. It changes the constant and
  the log factor, not the exponential in n.
- **GFB and BBE.** These scale because they partition the n *variables*, not the 2^n
  states. That changes the object:
  - BBE changes the domain to states constant on blocks, so it cannot be substituted
    for our all-state result however large its reductions.
  - GFB keeps all states (Thm 1), but only for maps of the form ψ_R and for a single F.

  *Proved here:* suppose a partition R is a GFB of every D_q = (X, T_q) with one monoid
  ⊕, and h factors through ψ_R. Then ker ψ_R is a congruence of all T_q saturating
  ker h, so ker ψ_R refines α\* and |im ψ_R| ≥ K\*. GFB can therefore give a *valid*
  grouping and an upper bound on K\*, never something below it.

  *Hypothesis, not checked:* under our INTERVENTION regime, which clamps or toggles
  every variable j before or after F, any block containing j and another variable can
  break the GFB condition for the clamp table. That would force R towards singletons.
  The sketch: with ⊕ = ∧ and C = {j, k}, the states (0,1) and (1,0) have equal
  aggregates, but clamping j := 1 sends them to aggregates 1 and 0.

  Separately, the M4/T1 optimum is a *projection* onto bits {0, 1, 8, 9}. That
  drops variables rather than aggregating them, so it is not of the form ψ_R. The
  projection was rechecked in this closure from the saved `production/cells/cell_21.json`
  (first-appearance labelling identical; Codex found the same). It is an observation,
  not a theorem about GFB.
- **Symbolic (BDD/SAT) bisimulation under the same contract.** These methods may exist,
  but none of them was read in this closure, so this remains an **unverified
  hypothesis**.

**3. What would have to change for approximate or finite-horizon grouping?**

- **Finite horizon d.** The certificate already holds P_d. It is the coarsest partition
  preserving outputs for all words of length ≤ d (THEORY.md). It is generally **not**
  closed under the actions, so it has no exact macro dynamics. A finite-horizon contract
  must give up closure or carry a horizon-indexed family of maps, and must say which
  words are quantified.
- **Approximate grouping.** This needs a stated tolerance and a measure over starts
  and/or words. It therefore replaces the universal quantifier "all starts, all words"
  with a weighted one, and minimality becomes relative to that measure. *Hypothesis:*
  the relevant prior art is approximate or probabilistic bisimulation; none was read
  here.

Either change is a new contract with its own acceptance criterion, not a parameter of
this component.
