# CausalBool and the 0xPARC challenges: feasibility and solution approach

Assessment date: 2026-09-14. This is a feasibility study with bounded probes,
not a claim that the complete challenge implementation has shipped.

## Decision

A complete mathematical response is a realistic target. CausalBool provides
useful foundations for the Boolean construction and its verification. A small
arithmetic-constraint module and a packed-linear-transform module would cover
the main additional engineering needs. Building a general lattice solver,
general computer-algebra system, or new encryption implementation is unnecessary
for the stated puzzles.

The earlier unconditional promise that extensions would fully solve everything
was too strong. In particular, a competitive Fourier circuit still needs to be
constructed and measured under explicit assumptions. A solution to a puzzle,
a practical implementation, and an improvement over existing methods are three
different deliverables.

The primary problem source is the [0xPARC page](https://fieldextension.org/3b1b/).
The local challenges.txt loses superscripts: for example, `2127` means `2^127`.
The source itself has a Fourier dimension inconsistency: it specifies 32,768
complex entries but lists 65,536 entries in its rotation example. We should
parameterize the solution for both rather than silently choose one.

## What the implementation actually supplies

Code inspected:

| Existing component | Reusable contribution | Boundary |
| --- | --- | --- |
| `index-deconvolution/src/causalbool.py`, `apply_gate` | Existing Boolean semantics, including MAJORITY | A native 2025-input majority operation is a specification oracle, not a circuit built from 3-input gates. |
| Same file, `Network` and `step` | Synchronous Boolean network representation and execution | A square binary adjacency matrix has no ordered duplicate input ports; one synchronous update is not evaluation of an entire combinational circuit. |
| Same file, `repertoire` | Exact small-instance reference | Explicitly creates `2^n` rows; unsuitable at the challenge scales. |
| `doppel-challenge/src/doppel_challenge/repertoire_program.py` | Shared ordered decision diagrams, Boolean apply, threshold recurrence, canonical serialization, resource limits | Public compilation describes one-step outputs over state coordinates. It requires as many output references as input coordinates. It lacks a public arbitrary-circuit composition interface. |
| `index-deconvolution/src/deconvolution.py` | Essential-variable and named-gate recovery from a supplied repertoire | Cannot recover a minimum MAJ3-only circuit simply by identifying a large MAJORITY gate. Its input already contains the expanded repertoire. |
| `doppel-challenge/src/doppel_challenge/compression.py` | Exact encodings and validation conventions | Encoded length is not a count of encrypted rotations, multiplication levels, or arithmetic constraints. |

No specialized R1CS/Circom, CKKS linear-transform, or lattice-reduction
implementation was found in the inspected source trees. Neither `circom` nor
`snarkjs` was available on the inspected PATH. Graph discovery tools were not
exposed in this session, so discovery used repository searches and source reads.

A concrete scaling check matters here. The existing threshold routine for
2025 inputs and threshold 1013 hits its default 1,000,000-node allocation limit.
Its unrestricted allocation count, derived from its loop bounds, is 1,538,747;
the reachable reduced threshold graph has 1,026,169 nonterminal nodes.
The probe checks the counting formulas at smaller sizes and observes the actual
default-limit failure at 2025. This is a manageable target representation with
an appropriate implementation and budget, but composing an arbitrary candidate
circuit can allocate many more intermediate nodes. A small target graph does
not guarantee an inexpensive equivalence check.

The majority function depends on every input. Removing disconnected coordinates
therefore gives no reduction in its input support. Shared threshold states help;
explicitly listing its accepting inputs would still produce `2^2024` entries.

## 1. Dot-product recovery

There is a simple practical construction using exact integer arithmetic:

1. Query `(1, 1, ..., 1)` to obtain `S = v1 + ... + vn`.
2. Set `B = S + 1`, then query `(1, B, B^2, ..., B^(n-1))`.
3. Read the answer's base-B digits to recover the list.

Every positive entry is smaller than B, so there are no carries between digit
positions. If an upper bound U is known beforehand, set `B = U + 1` and only
the packed query is needed. The returned integer still contains about
`n * log2(B)` bits: saving queries does not eliminate the information cost.

The official page also gives the theoretical one-query route using coefficients
linearly independent over the rationals. This requires an idealized exact-real
answer model. For `n >= 2`, a single fixed rational-coefficient query cannot be
injective on all positive integer lists: its rational nullspace contains a
nonzero integer direction, and two sufficiently large positive lists can
differ by that direction. Thus two queries are optimal in the unrestricted
positive-integer problem when queries have rational coefficients and exact
answers. For `n = 1`, one query is enough.

Needed software: an exact packing/unpacking helper, an explicit query model,
and examples. LLL is optional exploration, not a dependency of this answer.
CausalBool's representation perspective is relevant, but its Boolean engine is
not responsible for this recovery theorem.

Probe: 320 exact round trips, covering lengths 1 through 16 and entries below
`2^80`. This tests packing, not the idealized exact-real construction.

## 2. Majority from MAJ3 gates

This is mathematically achievable without constants or inversion. It has a
known theoretical basis in the literature on majority from majority gates;
efficient formula construction is a separate issue from mere existence.
See [Cohen et al., Efficient Multiparty Protocols via Log-Depth Threshold
Formulae](https://www.wisdom.weizmann.ac.il/~/ranraz/publications/Pmajority_mpc-1.pdf).

A directly provable recursive construction is sufficient for the existence
question. Let f be a monotone Boolean function: changing an input from 0 to 1
cannot make its output decrease. Select three input variables a, b, c, and form:

```text
g1 = f with b replaced by a
g2 = f with c replaced by b
g3 = f with a replaced by c

f = MAJ3(g1, g2, g3)
```

Why the identity holds: if a, b, c agree, all three substitutions leave the
input unchanged. Otherwise exactly one substitution leaves it unchanged,
one increases a bit, and one decreases a bit. Their outputs are the original
value, a value at least as large, and a value at most as large. Their majority
is the original value.

Odd-input majority is also self-dual: complementing every input complements
the output. Identifying variables preserves both monotonicity and self-duality.
Each recursive branch loses a distinct input variable. A monotone self-dual
function on at most two variables is a projection onto one input, so recursion
ends using only wires and MAJ3 gates. For weighted majority during recursion,
identification simply merges two positive integer weights. Total weight remains
odd, and a variable with more than half of that weight is already the answer.

This proves existence at 2025, but does not establish a compact construction.
The unshared recursion has the loose gate bound `(3^(n-2)-1)/2` for `n >= 3`.
Memoization and circuit sharing help, but their performance at 2025 must be
measured rather than extrapolated from tiny examples.

The prototype calls the actual CausalBool `apply_gate` at every constructed gate.
It agrees with direct vote counting on all 680 assignments across sizes
3, 5, 7, and 9. It has not materialized a 2025-input circuit.

A naive hierarchy of local majorities is wrong. The three groups `110`, `110`,
and `000` produce local votes `1, 1, 0`, whose majority is 1; only four of the
nine original inputs are 1.

Needed software: a sparse acyclic circuit with explicit external inputs,
ordered operand references, free fan-out and repeated references, and selected
outputs. Add a strict MAJ3 basis validator and a compiler into the existing
decision-graph machinery. Keep the recursive proof as the correctness argument;
use exhaustive checks only at small sizes and bounded symbolic checks where
affordable. SAT-based equivalence can be an optional backend, not a promise of
automatic scalability.

## 3. Modular power sums

For the stated prime, the only solution is `a = b = c = d = 0` modulo p.
This can be proved directly; no general algebra module is required.

From the linear equation set `d = -(a+b+c)`. Then:

```text
a^3 + b^3 + c^3 + d^3 = -3 * (a+b) * (a+c) * (b+c)
```

Since `p = 2^127 - 1` is prime and is not 3, a pair among a, b, c must sum
to zero. Relabel to obtain `b = -a` and `d = -c`. The square equation gives:

```text
2 * (a^2 + c^2) = 0 mod p
```

Here `p mod 4 = 3`, so -1 is not a square in the field. If c were nonzero,
`(a/c)^2 = -1`, a contradiction. Thus c and then a are zero, and so are b,d.

Needed software: a short exact verification example accompanying the proof.
The probe enumerates small primes, including contrasting cases p=5 and p=13.
It also records that p=3 is an exception: division by 3 is invalid there.
The target-prime result comes from the argument, not large-scale enumeration.

## 4. Quadratic constraints

The necessary representation is a list of field equations
`A(w) * B(w) = C(w) mod p`, with A, B, C linear in the variables w.
This matches [Circom's constraint format](https://docs.circom.io/circom-language/constraint-generation/).
Generating a witness assignment and constraining that assignment are separate
operations; the implementation must enforce both.

### (a) 64-bit range

Use 64 auxiliary bits:

```text
b_i * (b_i - 1) = 0 mod p       for i = 0,...,63
x = sum(2^i * b_i) mod p
```

The sum lies between 0 and `2^64-1`, which is smaller than the field prime.
Therefore each satisfying field value has the required canonical integer
representative. Range membership here concerns field elements' canonical
representatives, not arbitrary external integers differing by multiples of p.

### (b) Excluding one

One inverse witness s is sufficient:

```text
(r - 1) * s = 1 mod p
```

A nonzero field value has an inverse; zero does not.

### (c) Factoring a 64-bit public integer

Take private factors u and v, each range-constrained to 64 bits. Enforce:

```text
u * v = n mod p
(u - 1) * s = 1 mod p
(v - 1) * t = 1 mod p
```

Because `u*v < 2^128 < p` and `2 <= n < 2^64`, the product equation is an
integer equality. Zero factors are excluded by that equality; the inverse
constraints exclude one. Conversely every nontrivial factorization supplies
valid witnesses. These constraints verify supplied factors; they do not furnish
an efficient method for finding factors.

### (d) Factoring the 4096-bit integer

The 64 public limbs describe a 4096-bit integer. A single field product is
insufficient because it would establish only equality modulo p.

Set `B = 2^64`. Represent each factor with 64 limbs `u_i`, `v_i`, each with
64 constrained bits. Introduce partial products:

```text
u_i * v_j = q_ij mod p
```

For columns k=0,...,127, set `n_k` to the public limb for k<64 and to zero
otherwise. Enforce the carry equations:

```text
sum(q_ij for i+j=k) + carry_k = n_k + B*carry_(k+1) mod p
carry_0 = carry_128 = 0
```

Range-constrain the intermediate carries to 70 bits. Each column has at most
64 products. Valid integer multiplication has carries smaller than `64*B`,
and each side of a column equation is smaller than `2^135`, far below p.
Every partial product is below `2^128`. Consequently the constrained field
equations lift to exact integer equalities and cannot hide modular wraparound.
The zero upper output limbs prevent product overflow beyond the public integer.

To require each factor to be at least two, sum its constrained bits at all
positions except position zero and require that sum to have an inverse.
That sum is between 0 and 4095, so its field nonzeroness is exactly the existence
of a set bit at position one or higher. This excludes both 0 and 1.

This baseline uses 4096 partial-product constraints, 8192 factor-bit constraints,
127 range-checked carries, and linear packing/carry equations. Constraint
optimization comes after soundness. Public-limb range checks can be included
when the problem's public-input promise is not enforced at the boundary.

The probes check 3136 toy assignments, 20 valid large products with factors
up to 2048 bits, altered outputs, altered carries, and a false factorization
whose product equals `n+p`. This is evidence for the arithmetic design, not a
compiled Circom proof or an exhaustive check of all field witnesses.

Needed software: linear-expression and R1CS representations, witness generation,
an independent constraint evaluator, bit/range gadgets, carry gadgets, and a
Circom exporter. Circom compilation and malicious-witness tests are required
before claiming a delivered circuit. A full ZK proving system is optional for
answering these constraint-design questions.

## 5. Encrypted Fourier transform

This is the largest remaining implementation task. Existing FHE work already
explores the tradeoff between depth and rotations/multiplications; our solution
should compare against those methods, not claim the tradeoff as new.
See [Cheon, Han, and Hhan, Faster Homomorphic Discrete Fourier Transforms](https://eprint.iacr.org/2018/1073).

An exact linear transform has a useful depth-one baseline. Define
`R_k(x)[j] = x[(j+k) mod N]`. For a matrix A, define
`d_k[j] = A[j,(j+k) mod N]`. Then:

```text
A*x = sum(d_k * R_k(x) for k = 0,...,N-1)
```

Products are componentwise. For Fourier, A is the DFT matrix. All d_k are
known vectors. A baby-step/giant-step regrouping reuses rotations:

```text
k = g*b + i
A*x = sum(R_(g*b)(sum(R_(-g*b)(d_(g*b+i)) * R_i(x) for i)) for g)
```

Assume known-vector multiplications are allowed, charge them at the stated
multiplication cost, count one multiplication level per such layer, and measure
serial work. For N=32768, b=128, this straightforward baseline uses 32768
multiplications, 32767 additions, and 382 ciphertext rotations. Its stated-cost
estimate is 185.962068 seconds. This is an estimate, not an encrypted benchmark
and not a competitive final answer. The probe matches NumPy's DFT on basis
vectors and random complex inputs through N=128; maximum absolute error in this
run is below `1.3e-14`.

Optimization approach:

1. Factor the Fourier transform into FFT stages with explicit index mappings.
2. Fuse stages into at most three linear transformations. For `N=2^15`, a
   `5+5+5` split is a candidate, not an established optimum.
3. Derive each fused transform's sparse diagonals and search rotation reuse.
4. Charge every permutation, or fuse it into a charged transform. In particular,
   bit reversal must never be assumed free without an input/output convention
   that explicitly permits it.
5. Compare all 106 ordered contiguous partitions of 15 stages into one, two,
   or three nonempty groups. This is an optimum only within the enumerated family,
   not over all possible arithmetic circuits. For 16 stages there are 121.
6. Check the matrix factorization, then compare numerical outputs to a separate
   FFT implementation. Report operation counts and path depth from the emitted
   circuit, not from its name or intended structure.
7. If reporting actual encrypted performance, choose CKKS parameters, state an
   error tolerance, and benchmark an established backend. Account for any costs
   outside the puzzle's simplified model.

The final answer must state the slot count, availability/cost of known-vector
multiplication, what counts toward multiplicative depth, and whether speed means
serial work or latency with parallel resources. Without those choices, there
is no uniquely determined cost comparison. We can proceed under explicit
assumptions while reporting both published dimensions.

[Lattigo's own repository](https://github.com/tuneinsight/lattigo) includes CKKS
linear-transform and DFT facilities, making it a possible independent reference
and encrypted execution backend. We should reuse a maintained backend if needed.

## Minimal implementation plan and acceptance criteria

| Step | Deliverable | Completion criterion |
| --- | --- | --- |
| 1 | Mathematical response draft: query models, majority construction, modular proof, constraint equations, Fourier assumptions | Every subproblem has a precise statement, construction/proof, and declared scope. |
| 2 | Sparse Boolean circuit adapter around CausalBool semantics | Only MAJ3 gates and permitted wires in the majority circuit; exact small-instance agreement; general recursive proof; measured resource limits. |
| 3 | R1CS and limb module | Both completeness and soundness arguments; Circom compiles; valid witnesses pass and modular-alias, range, carry, and trivial-factor attacks fail. |
| 4 | Packed linear-transform compiler and cost model | Correct DFT ordering, at most three multiplication levels, explicit counts; a materially faster candidate than the dense baseline under the chosen model. |
| 5 | Independent verification and final response | Reproducible examples, source hashes, documented assumptions; theoretical cost distinguished from measured encrypted performance. |

Only the Boolean circuit adapter and selected symbolic interfaces need to connect
directly to CausalBool's current core. Arithmetic circuits should keep field and
complex semantics explicit. Converting all arithmetic to bits would obscure the
challenge's native costs and can make verification much harder.

The strongest defensible contribution is a coherent collection of correct,
reproducible constructions with clear proofs and measured implementation costs.
We have not demonstrated that CausalBool improves on specialized cryptographic
methods, nor that description-length compression yields the fastest circuit.

## Reproduce the feasibility evidence

From the repository root:

```sh
python 0xPARC-challenge/analysis/feasibility_probe.py
```

The recorded run is in `../analysis/feasibility_evidence.json`; it includes
Python/NumPy versions and SHA-256 hashes of the probe and imported source files.
The probes create no encryption keys or proofs, and do not materialize the
2025-input circuit or execute a full-size encrypted Fourier transform.
Existing source files and the original challenge transcription were not edited.
