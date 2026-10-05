# DRAFT — query-mode functional recovery in C(n,k)

> **NOT AUTHORIZED FOR EXECUTION.** Draft produced by `causal-target-spec-v1-r1` on 2026-10-04.
> It may not be run, implemented or partially implemented until the preconditions P1–P4 in
> `DECISION.md` are met and a supervisor explicitly authorises a named run. Nothing below has been
> executed. All numbers are design parameters, not results.

## 1. Question

Under chosen state–successor queries (TARGET_CONTRACT R4), how many queries does a deterministic
adaptive learner need to **certify** exact functional recovery of every node of a network in
C(n,k), compared under the same access and the same certifier with random states and with the
full table?

**New relative to existing deconvolution**: the input is an oracle rather than the 2^n table.
Identification is certified relative to a declared class, and AMBIGUOUS is an explicit outcome.
The owner perturbation test (flip pairs x, x ⊕ e_j) is applied to chosen pairs instead of all
pairs. Nothing new is claimed about naming, which stays with `identify_gate`.

## 2. Finite access class

- Networks with n ∈ {10, 12, 14, 16}, every f_i having at most k = 3 essential variables, with any
  Boolean function on its support. Self-loops and constants are allowed. Labels are known.
- The oracle accepts a state x, returns F(x) with all n bits, and costs one unit. Repeated queries
  are answered from a cache and are not charged. There is no equivalence query and no access to
  the network object.
- Ground truth: the full table, through `causalbool.repertoire`, owned in `src/causalbool.py`.

## 3. Certifier (identical for every query arm)

For node i and the set A of answered pairs (x, y):
1. A support T with |T| ≤ k is **consistent** iff no two answers agree on x_T and disagree on y_i.
2. A consistent T is **determined** iff all 2^|T| patterns of x_T occur in A. Its table g_T is then
   fixed. Write (ess(g_T), reduced table) for its canonical form.
3. Node i is **IDENTIFIED** iff at least one T is consistent, every consistent T is determined,
   and all the canonical forms coincide. It is **AMBIGUOUS** if some consistent T is undetermined,
   or if two canonical forms differ. It is **INVALID** if no T is consistent.

*Correctness within the class.* Two different tables on the same T differ at a realisable state,
so they are different functions. Hence an undetermined consistent T contributes at least two
consistent functions. Conversely, if every consistent T is determined and all give one canonical
form, exactly one function in C(n,k) agrees with A. The cost is Σ_{j≤3} C(n,j) supports per node
(697 at n = 16), times |A|.

## 4. Arms, candidate ordering and ties

- **ADAPT** (the new arm). It first queries 0^n, then e_1, …, e_n (n + 1 queries). Each later
  step forms the set H of holes (i, T, p): node i uncertified, T consistent and undetermined, p an
  unobserved pattern on T, with T and p ordered lexicographically. For each hole the candidate
  state sets x_T = p and every other coordinate to 0. It picks the candidate that fills the most
  holes and breaks ties by the smallest state integer (LSB-first, as `causalbool.input_vector`).
  It stops when every node is IDENTIFIED or INVALID, or when the budget is reached.
- **RAND** (baseline, same certifier). Uniform i.i.d. states from a pinned stream
  `ctv1:rand:<instance-id>`, distinct states only. The stopping rule is the same as ADAPT's.
- **FULL** (ceiling). `deconvolve` on the full table, charged 2^n queries.
- **BOOLNET** (historical continuity, optional). Random samples, lenient and unique criteria, as
  in `screen_s2_queries.py`. Run only if the installed version matches the screen's record. No
  new installation.
- **AKUTSU2003**. Included only if precondition P1 maps its access regime onto R4. Otherwise
  UNAVAILABLE, with the reason.

## 5. Instances and fresh-data separation

- **Predeclared witnesses**, run first as unit fixtures: W1 (n = 2, under R4 the query 01 must
  separate) and W2 (n = 3, IDENTIFIED with support {x1, x2}), plus two hand fixtures declared now.
  AND3 on {x1, x2, x3} at n = 10 has a single 1-point, which stresses hole filling. PARITY3 on
  {x1, x2, x3} at n = 10 gives full sensitivity.
- **Development set**: `random_network(n, seed, max_arity=3, gate_pool="all")` with seeds from
  namespace `ctv1-dev`, 3 per n. It may be used to debug the harness, and its results are never
  reported as evidence.
- **Confirmation set A**, the gate family: the same generator with namespace `ctv1-conf`, 10 per n
  (40 networks). Seeds are written to a frozen manifest with sha256 before the first ADAPT call.
- **Confirmation set B**, class-uniform: each node draws a support size uniformly in {0..3}, then a
  support, then a function with **exactly** that many essential variables, uniformly. Namespace
  `ctv1-confB`, 10 per n. This needs a sampler that does not exist (P3).
- Development and confirmation seeds never overlap. The certifier, the arms and the ordering are
  frozen by hash before confirmation.

## 6. Endpoints (EVALUATION_SPEC §1–§2)

The endpoints are (i) functional recovery, (ii) support recovery and (iii) predicted answers for
every reset of a single coordinate to 0 or 1, and for every mechanism replacement f_i := c,
exhaustive over x. Endpoint (iv) is not applicable. Per instance and arm, record: the outcome
vector, queries to certification, wall time and peak RSS. Report the full per-instance list,
medians, and intended and available denominators. Also report the per-n value ⌈log2 N(n,3)⌉ as
a worst-case reference only, never as a target.

## 7. Budgets and stopping rules

- Per instance and arm: at most 2^n distinct queries and 600 s wall. On reaching either, the
  remaining nodes are ABSTAIN.
- Per run: at most 3,600 s executor wall, all arms included, with no borrowing.
- **Halt the run** on any INVALID for an in-class instance (a harness defect), or on any
  IDENTIFIED-WRONG for an in-class instance (a certifier defect). Record the halt and do not repair
  it within the same run.

## 8. Falsifiers of the draft's value, fixed now

- **F1, adaptivity adds nothing.** On confirmation sets A and B, the median RAND
  queries-to-certify is at most 1.1 × the median for ADAPT, at three or more of the four values
  of n.
- **F2, no saving against the table.** The median ADAPT queries-to-certify at n = 16 is at least
  2^16 / 16 = 4,096.
- **F3, certification is impractical.** More than 20% of nodes under ADAPT end ABSTAIN because
  of the 600 s wall limit. At the full 2^n budget every support is determined, so for in-class
  instances an AMBIGUOUS outcome at that budget is impossible; one would count as a harness
  defect, not as a scientific outcome.
- **F4, prior art.** P1 finds a published exact algorithm with a guarantee for the same class and
  access. The study then counts at most as a labelled replication, and DECISION reverts to
  NO_JUSTIFIED_IMPLEMENTATION.

If none of F1–F4 occurs, the claim is limited to the stated one: certified exact functional
recovery in C(n ≤ 16, 3) with the reported query counts, under a simulator oracle. It says nothing
about biological networks, about noisy data, or about causal claims beyond the reset and
replacement predictions of endpoint (iii).

## 9. Out of scope

R1 strings, the order-discovery objective, abstraction validation, n > 16 without symbolic ground
truth, and any change to historical results or to the screen's verdict.
