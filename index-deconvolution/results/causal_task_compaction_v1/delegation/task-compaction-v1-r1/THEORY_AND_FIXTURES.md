# Mathematical contract and pre-execution controls

## Established foundation and explicit mapping

Primary reference: Timo Knuutila, “Re-describing an algorithm by Hopcroft”, Theoretical Computer Science 250 (2001), 333–363, https://www.cs.cmu.edu/~cdm/resources/Knuutila2001.pdf . Read §§2.2–3.1. It treats state equivalence, congruences and classical partition refinement. This packet does not request Hopcroft's optimized algorithm or claim its runtime bound for the simple implementation.

Our mapping: micro states become automaton states; named interventions become alphabet symbols; T_q is the transition; h is the observed output. For each binary task, the accepting set is h^{-1}(1). Unlike a single-start language recognizer, EVERY micro state is a possible initial condition. Therefore do not discard states unreachable from one selected start. This all-start interpretation is part of our contract and must be proved explicitly. Multiple-output fixtures generalize equality of h; they do not change the 24 binary tasks.

Codex consulted the primary paper's definitions and partition-refinement section while preparing this contract. Claude must record what it actually reads. No novelty claim is licensed by this mapping. The following proof obligations are project-specific statements of the required guarantees, not claimed original results.

## Proof obligations (write before implementation)

For w=q1...qd, define T_w=T_qd∘...∘T_q1 and T_empty=id_X. Define x~y iff h(T_w(x))=h(T_w(y)) for every finite word w over Q.

Prove: (1) ~ is an equivalence; (2) it preserves h and is closed under every T_q; (3) every output-preserving transition congruence refines ~; (4) the quotient supplies H and every G_q and preserves outputs for every action sequence by induction. This is exact sufficiency relative to the supplied full transition model, not causal identification from passive observations.

Prove by induction that Pd(x)=Pd(y) iff outputs agree for all action words of length <=d. The recurrence retains Pd(x) as well as all successor labels. A strict round increases the number of blocks. There are at most |X|-K0 strict rounds; equality implies all subsequent stages are equal. Saving the first repeated stable vector certifies termination. Hence the stable quotient equals ~ and has the fewest states among deterministic full-domain groupings with these properties, unique up to labels. It does not minimize total encoding length or arbitrary history-dependent/approximate predictors.

For an arbitrary candidate alpha, output decoding and transition closure jointly imply a function f with alpha*=f∘alpha. Prove K_candidate>=K*. Merely refining alpha* is necessary but not sufficient for a candidate's own transition closure; retain the explicit closure check. Adding actions can only refine the optimum partition. Constant h permits K*=1 even for complicated dynamics; that is why nonconstant tasks, rather than a post-hoc constant-map exclusion, are declared.

Horizon refinements Pd+1->Pd form a nested chain, but an intermediate Pd need not be closed for iteration. Only the final stable quotient is a reusable exact state model. Do not present intermediate partitions as individually valid causal models.

## Hand fixtures: declare these in JSON BEFORE executing any new code

State order is the written table index; vectors below use first-appearance canonical labels. These expectations are mathematical declarations, not executed outcomes.

1. Identity dynamics T=[0,1,2,3], h=[0,0,1,1]: P0=[0,0,1,1], next vector identical, K*=2. Identity grouping with K=4 is valid but not minimal; audit must distinguish these claims.
2. One-step separation T=[0,2,2,3], h=[0,0,1,1]: P0=[0,0,1,1], P1=[0,1,2,2], P2=P1, K*=3. Pair (0,1) first separates at depth1, witness [a]. Empty word does not distinguish that pair.
3. Two-step separation T=[1,2,2,0], h=[0,0,1,0]: P0=[0,0,1,0], P1=[0,1,2,0], P2=[0,1,2,3], P3=P2. Pair (0,3) first separates at depth2 with [a,a]. This catches one-step-only stopping.
4. Adding an action: use h from fixture1, action a=identity and b=[0,2,2,3]. With [a] the optimum is P0, K=2; with [a,b] it is [0,1,2,2], K=3. Keep the two action identities. This catches ignoring a nonfirst action.
5. Action order: a=[1,1,2,3], b=[0,2,2,3], h=[0,0,1,1]. From x=0, word [a,b] has final h=1; [b,a] has final h=0. This tests replay composition, not a prediction that either word is shortest for an unspecified pair.
6. Constant task: h=[0,0,0,0] on fixture2 dynamics gives K*=1 and no strict round. Full-identity task h=[0,1,2,3] gives K*=4 immediately. Do not delete either case or turn it into missing data.
7. Three-bit counter, T(x)=x+1 mod8, autonomous: bit0 task has K*=2 with alpha=x mod2; bit2 task has K*=8. Explain by the distinct cyclic shifts of the 00001111 output sequence for the latter. Include the full declared 3-bit intervention set for bit0 as a separate fixture: K*=2 remains, with actions interpreted as in PROTOCOL §2.
8. Four-bit rule150 ring, autonomous: total parity is conserved because every input contributes three times over GF(2), hence K*=2. Reset bit0 to0 before the step distinguishes x=0 and x=3 although both initially have parity0. Adding that named reset therefore invalidates the parity-only grouping. Do NOT infer the final number of groups under all interventions from this witness.
9. Relabeling outputs to [7,7,2,2] in fixture1 gives the same canonical partition with decoder [7,2]. This prevents confusing class IDs with outputs. Retain all four domain states with no designated start.
10. Malformed contracts: empty h, empty Q, unequal table lengths, negative/out-of-domain/noninteger transition entries, bool entries, invalid output types and nonbinary but valid integer output labels per the API. Invalid input must fail before partial results. Tests distinguish invalid evidence, missing evidence, both together, and a legitimate negative candidate.

Declare any additional development fixture before it is first run and label it supplemental. Do not construct fixtures from observed primary outcomes. No silent replacement of these controls.

## Six required semantic mutants

Independently: initialize all states in one group; stop after the first update even when unstable; use only the first action; drop one domain state; reverse witness replay order; report an arbitrary stable identity partition as minimal. A relevant test must fail for each, rather than import failure, a changed-hash gate or an absent field alone. Record exactly which assertion catches each mutant; fixture1 separates validity from minimality.

## Roles of the earlier proposals

| Proposal | Role in this phase | Limit |
|---|---|---|
| Multiple word widths and offsets | Existing F1/F3 candidates compared with an exact task optimum | Width is a construction parameter, not a discovered cause |
| Levels of grouping | Exact prediction-horizon refinement chain and coarsening maps | Intermediate levels need not support closed dynamics |
| Nested patterns | F4 candidate comparison and partition-equivalence checks | Nesting is supplied; equivalent partitions add no new state information |
| Occurrence gaps | Prior negative result retained; not used as a selector | No automatic retuning or inference of causal relevance |
| Grammar and self-similarity | Explicitly outside this finite task benchmark | Require separately defined objects and evidence |

This establishes a precise link between task, intervention alphabet, and necessary retained state distinctions. It does not settle a final general theory of causal deconvolution.
