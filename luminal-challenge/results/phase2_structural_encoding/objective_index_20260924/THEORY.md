# THEORY — objective-directed index search (protocol 1.0)

Four kinds of statement are kept apart below and in every other document of this release:

- **Proved** — a mathematical argument, valid for every input it names.
- **Tested** — finite, exhaustive or planted-defect checks of the implementation, with
  exact denominators (`PRUNING_VALIDATION.json`, test logs). They support the proofs; they
  do not replace them, and they do not make the implementation formally verified.
- **Measured** — empirical results under the frozen design (DEVELOPMENT, COMPARISON,
  LEARNING, PUBLIC_SCORE).
- **Open** — hypotheses this release does not settle.

Notation. B is the code width; U = {0,1}^B the code universe. A *cube* (schema) q has a
decimal anchor and a free-coordinate mask; its members fill the free coordinates in every
way. For a set E ⊆ U, N_r(E) = {x ∉ E : d_H(x, e) ≤ r for some e ∈ E} is the radius-r
novel Hamming neighbourhood.

---

## 1. Cube expansion is a Hamming neighbourhood (Proved; Tested)

**Definition.** Q is an *exact cover* of E if Q is a finite set of cubes whose union is
exactly E (cubes may overlap). R(Q) = ⋃_{q∈Q} ⋃_{j fixed in q} q^(j), where q^(j) frees
coordinate j of q. This is `structural_models.expand_cubes` followed by the union.

**Theorem 1.** For every exact cover Q of E and every T ⊇ E: R(Q) \ T = N_1(E) \ T.

*Proof.* (⊆) Let x ∈ R(Q) \ T. Then x ∈ q^(j) for some q ∈ Q and coordinate j fixed in q.
Either x ∈ q ⊆ E ⊆ T, impossible, or x differs from the member x ⊕ e_j of q only in
coordinate j; that member lies in E, so d_H(x, E) = 1 and x ∉ E, i.e. x ∈ N_1(E) \ T.
(⊇) Let x ∈ N_1(E) \ T with x = e ⊕ e_j, e ∈ E. Some q ∈ Q contains e. If j were free in
q, x would be in q ⊆ E ⊆ T; so j is fixed in q, and q^(j) contains both e and x. Hence
x ∈ R(Q) \ T. ∎

*Edge cases.* B = 0: U = {0}, N_1 = ∅, every cube has no fixed coordinate, R(Q) = ∅.
E = ∅: the only exact cover is Q = ∅ and R(∅) = N_1(∅) = ∅. E = U: N_1(U) = ∅ and
R(Q) \ U = ∅. Nothing exceptional happens.

**Corollary 1 (sequence).** `ordered_union` emits distinct members in ascending order and
the `one_bit` control emits its sorted distinct neighbours, so after removing T the two
proposal SEQUENCES are identical, not merely the sets. Timed prefixes may still differ,
because construction, duplicates and bookkeeping cost different amounts of time.

**Theorem 2 (depths 1 and 2).** (R(Q) ∪ R(R(Q))) \ T = N_2(E) \ T.

*Proof.* (⊆) A point of R(R(Q)) lies in a cube obtained from some q ∈ Q by freeing at most
two coordinates, so it differs from a member of q (hence of E) in at most two coordinates.
(⊇) Let x = e ⊕ e_i ⊕ e_j (i ≠ j) with e ∈ q ∈ Q and x ∉ T. If i or j is free in q, then x
is within distance 1 of a member of q ⊆ E and Theorem 1 puts x in R(Q). Otherwise both are
fixed in q, q^(i) ∈ R(Q) keeps j fixed, and (q^(i))^(j) ∋ x. Distance-1 points are covered
by Theorem 1. ∎

**Consequence.** The old `model_expand` proposes exactly the one-bit mutations of the
elite, in the same order; depth 1+2 proposes exactly the radius-2 Hamming ball. Comparing
either with one-bit mutation confounds search radius with learning. It is a geometric
neighbourhood operator, not a demonstrated learned predictor. This is a limitation of that
old learner, not a statement about all learning.

**Tested.** The lead's script `check_expansion_equivalence.py` was re-run from a
byte-identical copy (`theory/`), and its output JSON is identical to the lead's
(`logs/expansion_equivalence_repro.*`). `research_tests/test_schema_ranker.py` extends it to
GENERAL exact covers — singleton covers, `exact_cover`'s cover, randomly merged covers and
overlapping covers with a redundant sub-cube — over all 278 elite sets of widths 0–3 and 200
random sets of widths 4–8, each with T = E and with one or two random supersets T, for both
Theorem 1 (as ascending sequences) and Theorem 2 (as sets); plus zero-width, empty and full
cases and the depth-1 stream equality on 175 further sets. No counterexample was found.

---

## 2. The integer-cap lemma (Proved; Tested)

Fix an incumbent with product J0 = C0·S0 > 0, a window W of selected operations, a radius
r (or "full"), and the UNCAPPED neighbourhood N(W, r): selected issue times in
[t_i − r, t_i + r] ∩ [0, horizon − 1] (all of [0, horizon − 1] for "full"), selected
addresses any legal aligned base in the 256-word scratchpad, everything outside W fixed at
the incumbent. Let

- LC = max(cycle_lower_bound, 1 + max fixed issue time), LS = max(widest result,
  max fixed allocated end), empty maxima 0, then both raised to at least 1;
- Ccap = min(horizon, ⌊(J0 − 1)/LS⌋), Scap = min(256, ⌊(J0 − 1)/LC⌋).

**Lemma.** Every machine-feasible x ∈ N(W, r) with J(x) < J0 satisfies every selected
issue time ≤ Ccap − 1 and every selected block end ≤ Scap. Hence the capped domain (N with
those restrictions) holds exactly the same strict improvements as N. If Ccap < LC or
Scap < LS, N holds no strict improvement.

*Proof.* C(x) ≥ cycle_lower_bound because that bound (dependency height, per-engine issue
counts) holds for every compilation; C(x) ≥ 1 + t for every fixed operation's issue time t
because the emitted bundles run through the last issue. So C(x) ≥ LC. S(x) is the highest
allocated end, at least the widest result and at least every fixed value's end, so S(x) ≥ LS.
Both are ≥ 1 when J0 > 0. From C·S ≤ J0 − 1: C ≤ (J0 − 1)/S ≤ (J0 − 1)/LS, and C is an
integer ≤ horizon because every time is below the horizon; every selected time is ≤ C − 1
≤ Ccap − 1. Symmetrically every block end is ≤ S ≤ ⌊(J0 − 1)/LC⌋ and ≤ 256. The capped
domain is a subset of N, so the two improvement sets coincide. If Ccap < LC, no C can
satisfy LC ≤ C ≤ Ccap (likewise for S). ∎

*Scope.* The lemma is about N(W, r) and its fixed decisions only. It says nothing about
schedules outside that neighbourhood, and "no strict improvement" is scoped to N. A zero
objective has nothing strictly smaller (`ZERO_OBJECTIVE`). Capping changes the declared
value lists and therefore the numeric codes; the equality is between sets of normalised
physical compilations, not between integer indices of different domains.

*Why this matters.* The old controller searched target rectangles (C ≤ tc, S ≤ tm). Their
union need not contain every J-improvement: the lead's objective-space example (10,10) →
(12,8) lies in none of (9,10), (10,9), (11,9), (9,11) (`PRODUCT_TARGET_COUNTEREXAMPLE.json`;
re-checked in `test_objective_index.py`). Physical instances exist too: on development
seed 800016 A4 found (7,32), J = 224 → (9,24), J = 216, outside every old rectangle
(DIAGNOSIS.md §3; 4 of A4's 163 development improvements). The product domain covers such
trade-offs by construction; A2's radius-2 windows found none on development.

**Tested.** `PRUNING_VALIDATION.json`: on 12 original fixtures, 30 recipe domains
(seeds 920000–920029) and all 45 qualified fixtures, at every threshold
J* ∈ {J0} ∪ {distinct products + 1} (328 thresholds, 50 proved empty by the caps), the
strict improvements of the uncapped oracle enumeration equal those of the capped oracle
enumeration AND of three complete searches of the capped domain (A2-order DFS, A3 DFS, A4
heap): 21,853 improving objects compared, 0 violations.

---

## 3. Sound propagation (Proved; Tested)

All rules act on a search-only copy of physical domains D_i (times) and A_v (addresses);
fixed decisions are singletons. The codec's domains, options and layout are never touched.
"Feasible completion" means a machine-feasible compilation in the declared domain that
agrees with the current prefix.

**Rule 1 (precedence).** For every edge u → v with lag ℓ (data or pinned memory order,
`facts.predecessors`), t_v ≥ t_u + ℓ. Hence t_u ≤ max D_v − ℓ and t_v ≥ min D_u + ℓ in every
completion; removing values violating either removes no completion. An emptied domain proves
the branch has no completion. Edges between two fixed operations delete nothing: the root
conflict check already proved they hold, so only edges touching W are scanned.

**Rule 2 (issue capacity).** A singleton domain fixes that issue. If the singletons of one
(engine, cycle) exceed the engine's per-cycle limit (issues, not in-flight operations), no
completion exists; if they reach it, no other operation of that engine can issue there.

**Rule 3 (allocation; all times fixed).** Lifetimes are then fixed (`direct_contract.
lifetimes`: inclusive [issue + latency, last consumer issue], or the write cycle alone for an
unused result). Two values live in a common cycle need disjoint blocks. a_u has a disjoint
partner in A_v iff min A_v + w_v ≤ a_u or max A_v ≥ a_u + w_u; so exactly the values
a_u ∈ [max A_v − w_u + 1, min A_v + w_v − 1] have none and are removed. Applied to fixed and
selected values alike.

**Rule 4 (product bound).** In every completion, C ≥ LC := max(cycle_lower_bound,
max_i min D_i + 1) and S ≥ LS := max(widest result, max_v min A_v + w_v, compulsory width).
For value v with producer p: start = t_p + lat_p ≤ max D_p + lat_p =: start_hi and
end = max(t_p + lat_p, max_c t_c) ≥ max(min D_p + lat_p, max_c min D_c) =: end_lo. If
start_hi ≤ end_lo, [start_hi, end_lo] ⊆ [start, end] in EVERY completion ("guaranteed
live"). Values guaranteed live at one cycle occupy disjoint words below S, so S ≥ their total
width; the peak over cycles is the compulsory width. This covers unused results (empty
consumer set, end = start) and consumers outside W (singleton domains). Alignment can make
LS unattainable; it is only ever used to prune. A subtree with LC·LS ≥ J_best contains no
strict improvement below J_best.

Rules are iterated to a fixed point in a deterministic order (edges by IDs, then engine and
cycle, then address pairs by producer IDs). Reaching any limit yields UNKNOWN, never UNSAT.

**Canonical ranks.** Search alternatives are filtered by physical value; the rank of a
choice is always its position in the UNFILTERED `structural_encoding.options` list. So the
leaf's rank path is its codec index and `encode(decode(z)) = z` is untouched.

**Certificates.** Each deletion/prune emits a tuple with its rule and local inputs (e.g.
`("PU", u, v, lag, max D_v, removed)`). `objective_index_replay` re-derives each
conclusion from those inputs and the program's facts alone. Replay proves local logic, not
that the recorded max D_v was the true domain maximum; that obligation is carried by the
exhaustive tests. Certificate hashes are provenance, not proof.

**Tested.** `PRUNING_VALIDATION.json`, over the same 87 exhaustible domains at three
thresholds each (213 fixture-thresholds): every one of 32,621 propagation events was checked
against every oracle-feasible completion of its prefix (214,545 completion checks): no
deleted time or address value, no "inconsistent" branch and no pruned subtree ever held a
feasible (respectively improving) completion, and every completion satisfied C ≥ LC and
S ≥ LS. 6,431 certificates replayed with 0 failures (rules AL 4,520, PL 560, PB 845, PU 181,
EF 257, EMPTY 68). Planted unsound variants were detected: precedence lag + 1 (16,223
violations) and an inflated static live peak (6,652). 12,964 propagated leaves round-trip
through the unchanged codec. `test_objective_index.py` further shows node-for-node equality of
the shared traversal with `structural_search.search` (when propagation is replaced by the
owner's bounds), exact equality of A1 with `optimization_search.optimise(capnull_matched)`
under fixed work, and that A3 visits a pruned subsequence of A2's nodes with the same optimum.

---

## 4. A4: catalog, discrepancy heap, resumable queries (Proved; Tested)

Queries are ordered by the five-queue round-robin catalog of protocol §6. Inside a query,
prefixes are popped by (discrepancies, LC·LS, −depth, rank tuple). Child keys never precede
their parent's (discrepancy, bound): discrepancies only grow and every rule-4 term is
monotone under domain shrinkage. Emptying the heap without any limit is exhaustive over the
pruned tree, hence UNSAT for that declared domain; more than 4,096 queued prefixes stops the
query as UNKNOWN_FRONTIER_LIMIT; an improvement ends the epoch and every other query is
SUPERSEDED, not exhausted.

**Tested.** Run to exhaustion, the heap finds exactly the oracle's improving set at every one
of the 328 thresholds above, with (discrepancy, bound) nondecreasing along every pop order.
Sliced, interleaved queries pop exactly the sequences of uninterrupted ones on every
improvement-free run among 8 development programs (`ResumableQueries`); frontier-limited queries are never labelled UNSAT; no candidate
validated past its hard deadline is accepted; a planted validator rejection is retained and
fails the run; aggregate ceilings are never exceeded.

---

## 5. The schema ranker (Proved; Tested)

**Partition theorem.** The tree starts from the universe cube and replaces a leaf by the two
cofactors `schema_index.split(q, j)` of a coordinate j free in q. The cofactors are disjoint
and their union is q. By induction on the number of splits, the leaves are pairwise disjoint
and their union is U. ∎ This concerns the predictor's REPRESENTATION only. Leaf scores are
estimates; a coordinate free in a leaf preserves that leaf's prediction, not feasibility or J.
Predictions only order the common pool; they never prune, certify or skip validation.

**Tested.** Disjointness and exact coverage for widths 0–20 (exhaustively enumerated for
widths ≤ 10), exact rational Gini with lowest-coordinate ties, minimum child 4, depth ≤ 3,
pure/zero-gain stops, leaf scores (pos+1)/(n+2), class-count-preserving label shuffles, the
common pool construction, orderings as permutations of one pool, `stable_seed`, and a static
proof that the learner imports no oracle, fixture evaluator or split owner.

---

## 6. A design fact about H_LEARN, fixed before evaluation (Proved from frozen data)

H_LEARN's endpoint is best_test_J = min(min_training_J, J of validated TEST discoveries).
A discovery counts only if it is a test object with J < min_training_J. The frozen oracle and
split show that in **0 of the 30** evaluation fixtures (and 0 of 15 development fixtures) does
any test object have J < min_training_J (`fixtures/*/MANIFEST.json`, field
`test_headroom_objects`, computed from oracle and split only, before any learner ran). So for
every arm, fixture and repetition best_test_J = min_training_J, every H_LEARN contrast is
identically 0, every interval is [0, 0], and the gate "all three lower bounds > 0" cannot be
met. This was recorded in `FROZEN_SELECTION.json` before evaluation; the full matrices were
run anyway, as the protocol requires, and the fixed-work prefix metrics are reported
descriptively. It is a property of the inherited qualification recipe and this split, not
evidence about learning.

## 7. Open

- Whether larger neighbourhoods or the discrepancy order drives A4's development gain: the
  A3 → A4 step bundles both (protocol §3 says so explicitly).
- Whether any learned ordering helps: not testable with this fixture design (§6); the
  conditional end-to-end learned compiler is blocked by the gate. Its implementation was
  frozen and tested, but in real compilation queries rarely accumulate the 20 case-validated
  observations it needs, so even an enabled pair would mostly fall back to search.
- Anything about the private grader, other generators or global optimality.
