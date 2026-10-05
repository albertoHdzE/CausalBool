# Target contract (`causal-target-spec-v1-r1`) — corrected

> **Corrected copy** (`review_closure/causal-target-spec-v1-r1`, 2026-10-05). Original preserved unchanged at
> `causal-target-spec-v1-r1/TARGET_CONTRACT.md`. Changes are marked **[C-R1]**, **[C-R2]** or **[C-R3]** and listed in `../CHANGELOG.md`.


Status of every statement: **[F]** finding (proved here or checked on a declared witness),
**[A]** proposed assumption of the contract, **[H]** untested hypothesis. Machine form:
`target_contract.json`.

## 1. Objects

- A **state** is x ∈ {0,1}^n with known coordinate labels 1..n and known bit order. [A]
- A **mechanism** is a deterministic synchronous map F = (f_1..f_n), x(t+1) = F(x(t)). [A]
- The **functional support** of node i, S_i = {j : ∃x, f_i(x) ≠ f_i(x ⊕ e_j)}, is a property of
  f_i alone (`essential_variables`). The **declared connectivity** C and the **syntax** (gate
  names, formula) are properties of an implementation, not of F. [F, W2]
- The **identifiable target** under regimes 3 and 4 is at most the pair (F, (S_i)_i); because S_i
  is a function of f_i, it is F up to the declared equivalence below. [F]

## 2. Four access regimes

| regime | what is supplied | what may be claimed by default | what is never claimed |
|---|---|---|---|
| R1 unlabelled string | a finite bit string; no coordinates, time axis, interventions or class | structural hypotheses (repetition, grammar, nesting, schema covers) with their description length | a unique mechanism, a causal variable, an intervention answer |
| R2 passive labelled trajectory | a sequence of labelled states x(0), x(1), …, x(T) with transition boundaries | the version space of maps consistent with the observed pairs within a declared class; AMBIGUOUS unless it has one member. Per (state, node) value, three labels kept apart **[C-R3]**: OBSERVED (a recorded successor), CLASS-ENTAILED (an unvisited state on which every member of the version space in the declared class agrees, conditional on the class and on (a)–(f)), and UNDETERMINED (members disagree) | any value on an unvisited state that is not class-entailed; reporting a class-entailed value as observed; identification without class + coverage argument |
| R3 complete labelled table | F(x) for all 2^n states | F exactly; S_i exactly; the equivalence class of canonical names | original syntax, redundant declared edges, hidden variables, physical mechanism |
| R4 chosen state–successor queries | an oracle: submit x, receive F(x) | F within a declared class C once the consistent set in C has one member; otherwise AMBIGUOUS/ABSTAIN | anything outside C; anything an equivalence or intervention oracle would add |

**R2 assumptions required even to treat a trajectory as one map** [A]: (a) the same F at every
step (stationarity); (b) no noise; (c) full observation (no hidden coordinates; the next state is a
function of the observed state alone); (d) synchronous update; (e) correct alignment of transition
boundaries; (f) no exogenous input. Any repeated state with two different successors refutes the
conjunction (a)–(f) [F, definitional]; absence of such a repeat does not confirm it.

**R4 semantics** [A]: a query sets the **whole** state to x by an external reset, then applies F
exactly once with F unchanged, and returns the full n-bit successor. Every x ∈ {0,1}^n is
admissible. Cost = 1 per query, regardless of which bits differ from the previous query. No
equivalence query, no counterexample, no access to the model's code. A simulator oracle used to
test a learner is **not** passive real-world evidence; a result under R4 says nothing about what a
laboratory could observe. Distinct from R4:
- **mechanism replacement** (`reprogramming.knockout`): f_i := constant, applied at every update;
- **clamp**: x_i held at c both before and after each update (mechanism replacement plus reset);
- **free model access**: reading C, gates and params, which turns identification into a lookup.

## 3. Primary future target — chosen for assessment, not authorised

**T\***: exact functional recovery of F in the class C(n,k) under R4.

| field | specification |
|---|---|
| n | 10 ≤ n ≤ 16 for exact ground truth by full table; larger n only with symbolic ground truth and stated as such |
| class C(n,k) | every f_i has at most k essential variables, k ≤ 3; any Boolean function on its support (not restricted to the twelve families) |
| self-loops | allowed (j = i may be essential for f_i) |
| constants | allowed (|S_i| = 0) |
| degree | **at most** k, defined on essential variables, not declared edges |
| determinism | required; one F for the whole run |
| observation | full: all n coordinates of every returned successor |
| labels | known and fixed; no relabelling is part of the target |
| excluded | noise, hidden state, exogenous inputs, asynchronous update, time variation |
| interventions | R4 reset-then-step only; predictions of mechanism replacement are derived, not observed (§5) |
| identifiability scope | identification is relative to C(n,k): when the consistent set in C(n,k) has exactly one member, F is identified **if the truth is in C(n,k)**; a truth outside the class may be mis-identified, and for n > 2k no set of fewer than 2^n queries certifies class membership [F: take any f in C(n,k) consistent with the answers and an unqueried state y; f' = f with its value at y flipped agrees on every query; every j non-essential for f has f(y) = f(y ⊕ e_j), hence f'(y) ≠ f'(y ⊕ e_j), so f' has at least n − |S_f| ≥ n − k > k essential variables and lies outside C(n,k). For n ≤ 2k this argument does not apply and no claim is made. T\* has n ≥ 10, k ≤ 3] |

Why this target: R3 recovery already exists and is exact (E1); R4 removes the 2^n ingestion
wall, which `bitacora/01` identifies as the real cost. It does not establish headroom
(EXISTING_EVIDENCE §2) and is not a GO.

## 4. Recovered object, equivalence and abstention

- **Output** per node: either `IDENTIFIED(S_i, reduced table on S_i)` or `AMBIGUOUS(m)` with the
  number m ≥ 2 of distinct functions in C(n,k) consistent with all answers (or a declared lower
  bound on m when enumeration is capped), or `ABSTAIN(reason)` when the budget ends first, or
  `INVALID(reason)` when answers are inconsistent with every member of the class (e.g. a
  repeated query with two answers). **[C-R3]** INVALID is a correct outcome for a deterministic
  oracle whose F lies outside C(n,k): it falsifies class membership, which is possible even
  though membership can never be certified (§3). It indicates a harness defect only for an
  oracle whose membership in C(n,k) is verified by construction.
- **Equivalence**: functional equality of f_i over all 2^n states. Two canonical names for the same
  function are the same answer; a canonical name is a representation choice and is never reported
  as the original gate. No relabelling of nodes is permitted.
- **Network-level**: IDENTIFIED only if every node is; otherwise the per-node vector is reported.

## 5. Endpoints kept separate

1. **Observed agreement**: the hypothesis reproduces every answer received. Necessary, never
   sufficient (W1).
2. **Held-out predictive accuracy** on fresh query states: a prediction score, not identification.
3. **Exact functional equivalence** with ground truth on all 2^n states (assessable class only).
4. **Interventional equivalence**: for every declared intervention q in a finite set Q (reset of a
   subset; mechanism replacement f_i := c), the hypothesis' F_q equals the truth's F_q on all
   states. For deterministic full-state maps, endpoint 3 implies endpoint 4 for mechanism
   replacement and for reset-then-step [F: F_q is a composition of F with a fixed map, or replaces
   f_i by a constant; equality of F on all states gives equality of F_q]. Endpoint 4 does **not**
   follow from 1 or 2.
- **MDL**: a shortest consistent hypothesis may be **selected**, but selection is not
  identification; IDENTIFIED requires a singleton consistent set, not a shortest member.
- Compression or forecasting never counts as evidence of endpoint 3 or 4.

## 6. What is not targeted

Original syntax and declared edges (W2), hidden variables, physical mechanism, stochastic
mechanisms, the order-discovery objective on R1 data, and any claim about biological networks
beyond the round-trip certificate already on record.
