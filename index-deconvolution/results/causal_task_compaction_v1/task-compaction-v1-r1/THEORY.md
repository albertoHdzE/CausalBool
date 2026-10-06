# THEORY — task-preserving state compaction (task-compaction-v1-r1)

Written before implementation (preflight category). These are project-specific
statements of classical facts about state equivalence of deterministic automata
(Knuutila 2001, §§2.3, 3.1, Proposition 4; see SOURCES.md). No novelty is claimed.
The guarantee is exact sufficiency relative to the supplied full transition model;
it is not causal identification from passive observations.

## 0. Objects

- X = {0, ..., N-1}, finite, N >= 1. EVERY x in X is an admissible initial state;
  no start state, no reachability pruning.
- Q = (q_0, ..., q_{m-1}), m >= 1, an ordered list of action identifiers; each
  T_q : X -> X is total. Two identifiers with equal tables remain distinct.
- h : X -> O, the observable (O any set of labels; the 24 study tasks have O = {0,1}).
- A word w = q1 q2 ... qd over Q acts in written order: T_w = T_qd o ... o T_q1,
  T_empty = id_X. Hence T_{q w'}(x) = T_{w'}(T_q(x)).
- x ~ y  iff  h(T_w(x)) = h(T_w(y)) for every finite word w over Q.

A *grouping* is a function alpha : X -> Lambda; its kernel ker alpha is the equivalence
alpha(x) = alpha(y). alpha is *output-preserving* iff a decoder H with h = H o alpha
exists (ker alpha saturates h), and *closed* iff for every q a G_q with
alpha o T_q = G_q o alpha exists (ker alpha is a congruence for every T_q).

## 1. Proof obligations (THEORY_AND_FIXTURES.md)

**(1) ~ is an equivalence.** ~ = intersection over w of ker(h o T_w); each kernel of a
function is reflexive, symmetric and transitive, and so is any intersection of
equivalences.

**(2) ~ preserves h and is closed under every T_q.** Taking w = empty gives
x ~ y => h(x) = h(y). If x ~ y and q in Q, then for every w,
h(T_w(T_q x)) = h(T_{qw}(x)) = h(T_{qw}(y)) = h(T_w(T_q y)), so T_q x ~ T_q y.

**(3) Every output-preserving transition congruence refines ~.** Let rho be an
equivalence that saturates h and is closed under every T_q. By induction on |w|:
x rho y => T_w x rho T_w y (|w| = 0 trivial; T_{qw'} x = T_{w'}(T_q x) and
T_q x rho T_q y by closure). Saturation then gives h(T_w x) = h(T_w y) for every w,
i.e. x ~ y. So rho is a subset of ~.

**(4) The quotient.** Write [x] for the ~-class. H([x]) := h(x) is well defined by (2);
G_q([x]) := [T_q x] is well defined by (2). By induction on |w|,
G_w([x]) = [T_w x] where G_w composes in the same written order, hence
H(G_w([x])) = h(T_w x) for every finite action sequence w and every x in X.

## 2. The refinement recurrence (stage lemma)

P0 := canonical_partition(h).
P[d+1](x) := canonical_partition( (P[d](x), (P[d](T_q x) for q in Q in frozen order)) ).

Canonical labelling (first appearance over ascending x) is injective on the signature
values, so P[d+1](x) = P[d+1](y) iff P[d](x) = P[d](y) and P[d](T_q x) = P[d](T_q y)
for every q. It also depends only on the partition: two label vectors with the same
kernel have the same canonical vector. This is Knuutila's
rho_{i+1} = {(a,b) in rho_i | for all x in X: (x(a), x(b)) in rho_i}, with
rho_0 = ker h generalising {A', A - A'} to an arbitrary output alphabet.

**Lemma S.** P[d](x) = P[d](y) iff h(T_w x) = h(T_w y) for every word with |w| <= d.

Proof by induction. d = 0: P0 = ker h and only the empty word has length 0.
d -> d+1: every word of length <= d+1 is either of length <= d or of the form q w' with
|w'| <= d, and h(T_{qw'} x) = h(T_{w'}(T_q x)). By the induction hypothesis the first
group agrees iff P[d](x) = P[d](y), and the second iff P[d](T_q x) = P[d](T_q y) for
every q. Their conjunction is exactly P[d+1](x) = P[d+1](y). QED.

**Refinement and termination.** P[d+1] refines P[d] because its signature contains
P[d](x); blocks never merge, so the block count K_d is nondecreasing. A refinement with
the same number of blocks is the same partition, and then the canonical vectors are
equal; therefore a *strict* round (vectors differ) increases K_d by at least one.
K_0 = |h(X)| and K_d <= N, so there are at most N - K_0 strict rounds. If
P[s+1] = P[s] then the signature defining P[s+2] coincides with that defining P[s+1],
so P[s+2] = P[s+1], and every later stage is equal. Saving P0, ..., P[s], P[s+1] (the
first repeated vector) is a finite certificate of termination.

**Stable quotient = ~.** By Lemma S, x ~ y iff P[d](x) = P[d](y) for every d, and since
the sequence is constant from s on, iff P[s](x) = P[s](y). Define alpha* := P[s].

**Minimality and uniqueness.** alpha* saturates h (it refines P0) and is closed
(P[s+1] = P[s] says exactly that P[s](x) = P[s](y) implies P[s](T_q x) = P[s](T_q y)).
For any deterministic full-domain grouping alpha that is output-preserving and closed,
ker alpha is a subset of ~ = ker alpha* by (3), so |alpha(X)| >= |alpha*(X)| = K*, with
equality iff ker alpha = ker alpha*, i.e. alpha equals alpha* up to relabelling. This
does NOT minimise total encoding length (decoder, macro tables, state map), nor
history-dependent, stochastic or approximate predictors.

**Indexing convention.** "Strict refinement rounds" = s = the number of indices d with
P[d+1] != P[d]. Depth d in Lemma S counts actions, including the empty word at d = 0.
When s >= 1 the largest first-separation depth over pairs is exactly s (round s is strict,
so some pair is equal in P[s-1] and different in P[s]); when s = 0 every pair that is
separated at all is separated by the empty word.

**Intermediate stages are horizon refinements, not models.** P[d] for d < s need not be
closed. The coarsening map P[d+1] -> P[d] is well defined because of refinement; only
the stable quotient is a reusable exact state model.

## 3. Witnesses

For x < y define the first-separation depth sep(x, y) = least d with P[d](x) != P[d](y)
(undefined iff x ~ y).

**Lemma W.** If sep(x, y) = d >= 1 and P[d-1](T_q x) != P[d-1](T_q y), then
sep(T_q x, T_q y) = d - 1 exactly.

Proof: if they differed already in P[d-2] then, by the definition of P[d-1], x and y
would differ in P[d-1], contradicting sep(x, y) = d. QED.

Hence the shortest distinguishing word has length sep(x, y) (Lemma S), its admissible
first letters are exactly {q : P[d-1](T_q x) != P[d-1](T_q y)}, and choosing the first
such q in Q order and recursing on (T_q x, T_q y) yields the lexicographically least
shortest word (lexicographic in action index). If h(x) != h(y) the word is empty.
One witness per round is an explanation; the complete stage certificate is the proof.

## 4. Candidates, actions and constant tasks

**Candidate factorisation.** If a candidate alpha passes decoding and closure for every
declared q then, by §2, ker alpha is a subset of ker alpha*, so f(alpha(x)) := alpha*(x)
is well defined, alpha* = f o alpha, and K_candidate >= K*.

**Refining alpha* is necessary, not sufficient.** Counterexample: X = {0,1,2,3},
T = [1,0,3,2], h = [0,0,0,0]. Then alpha* = [0,0,0,0] (K* = 1). The candidate
alpha = [0,1,1,2] refines alpha*, but 1 and 2 share a block while T(1) = 0 and
T(2) = 3 lie in different blocks: closure fails. The explicit closure check is retained.

**Adding actions refines the optimum.** If Q is a sub-list of Q' (same tables for shared
identifiers), every word over Q is a word over Q', so ~_{Q'} is a subset of ~_Q and
K*_{Q'} >= K*_Q. In this study AUTO uses Q = [id] with T_id = F = q_table(id, 1), and
INTERVENTION = track_d_q(n) begins with the same id; hence INTERVENTION must refine
AUTO for every model and task. This is an implication, not a hypothesis.

**Constant tasks.** If h is constant, P0 is a single block and every signature is
constant, so K* = 1 for any dynamics. That is why the 24 cells use nonconstant tasks
(K* >= K0 = 2), and why K* = 1 on a primary cell is a harness failure.

## 5. Mapping to Knuutila (2001)

| Knuutila | here |
|---|---|
| states A | micro states X (all 2^n) |
| alphabet X (letters) | action identifiers Q (positional) |
| delta(a, x) = x(a) (unary algebra, §2.4) | T_q(x) |
| final states A' | h^{-1}(1) for binary h; ker h in general (Moore output) |
| initial state a0, connectedness (§2.3) | not used: all-start contract, no pruning |
| rho_A (state equivalence, §2.3) | ~ |
| greatest congruence (§2.3) | coarsest output-preserving congruence alpha* |
| Proposition 4 layers rho_i | stages P[d] |
| quotient DFA A/rho | (alpha*(X), H, G_q) |

Knuutila's minimality (Proposition 3) is stated for the language from a0 of a connected
DFA. Our minimality statement in §2 is the all-start one: it is proved directly from
(3), quantifying over every x in X, and does not rely on connectedness.
