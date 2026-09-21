# 0xPARC response v1 — authoritative implementation specification

Contract: v1. Baseline main: 37dae1623295f168017789e58b08eadfe0c12aa8.
Integration checkout: /private/tmp/oxparc-response-v1 (isolated local clone).
Original working tree and all unrelated changes are preserved. Preliminary
challenge documents/probes are copied unchanged; hashes are in STATE.json.

## Scope and acceptance
Produce a readable response paper, PDF, reproducible package and fail-closed
verification record for Q1 secret recovery, Q2 MAJ3 majority, Q3 packed Fourier,
Q4 modular sums, Q5 range, Q6 excluding one, Q7 64-bit factorization, Q8 4096-bit
factorization. Proofs and verified circuits are required. Actual ZK proofs,
CKKS ciphertext timing, and materializing the 2025-input circuit are deferred.
Distinguish existing mathematics, CausalBool reuse, new implementation, and
measured improvements. No publishing, submission, push, merge, or AI attribution.

## Mathematical contracts
Q1: positive integer lists, exact integer dot-product oracle. Unknown bound:
query ones for S, then powers of B=S+1; n=1 uses one query. Known U: B=U+1,
one query. Two rational queries are necessary for unbounded n>=2 by integer
nullspace. Rationally independent real coefficients give idealized injectivity,
not a finite-precision algorithm.
Q2: weighted odd-total majority. Choose first three nonzero coordinates a,b,c;
children merge b into a, c into b, a into c; combine with MAJ3. If any weight
exceeds half total return that variable. Memoize exact weight tuples; preserve
ordered ports and stable construction order. Monotonicity proves the cyclic
identity; identification preserves self-duality; <=2 active variables are a
projection. Loose unshared bound (3^(n-2)-1)/2. No 2025 materialization claim.
Q4: q=2^127-1, distinct from constraint field. Substituting d=-a-b-c gives
sum cubes=-3(a+b)(a+c)(b+c). Opposite pairs imply a^2+c^2=0; q=3 mod 4 implies
zero only. p=3 exceptional; 5,13 contrasting; 7,11,19 zero-only examples.
Q5-Q8 field P=21888242871839275222246405745257275088548364400416034343698204186575808495617.
Every explicit row is A(w)*B(w)=C(w) mod P. All external field scalars canonical.
Bits satisfy b(b-1)=0. Range reconstructs sum 2^i b_i. Exclude one by
(r-1)s=1. Q7: public n and private u,v range-checked to 64 bits, uv=n,
factors >=2; u*v<2^128<P prevents alias. Q8: B=2^64; 64 limbs per factor
and public n, all range-checked; 4096 q_ij=u_i*v_j; 128 columns;
sum_(i+j=k) q_ij+c_k=n_k+B*c_(k+1), n_k=0 for k>=64; c_0=c_128=0;
127 intermediate carries constrained to 70 bits. q<P; column sides<2^135<P,
so congruences lift to integer equations. True carries<64B; every valid product
has a witness. Sum factor bits except bit zero has inverse, enforcing >=2.
Q3: forward unnormalized negative-sign DFT, natural input/output. R_k(x)[j]=
x[(j+k) mod N]. Costs in microseconds: add 4, known-vector multiply 5600,
rotate 6100. Each known-vector multiply consumes one depth level. Radix-two
DIF stages m=N,N/2,...,2: y[t]=x[t]+x[t+h],
y[t+h]=(x[t]-x[t+h])*exp(-2*pi*i*t/m), within each block, h=m/2.
Output bit reversal is included in final fused transform. Partition contiguous
stages into <=3 nonempty blocks; enumerate 106 (15 stages), 121 (16 stages).
For each block evaluate BSGS baby sizes all powers of two dividing N.
Diagonal convention d_k[j]=A[j,(j+k)%N]; use R_(gb)(sum_i
R_(-gb)(d_(gb+i))*R_i(x)). No free permutations. Select by cost, multiplies,
rotations, lexicographic schedule. Claim best only in fully enumerated family.
Coefficient vectors lazy, no dense full-size DFT. Both N=32768 and 65536 required.

## Frozen interfaces
`BooleanCircuit(n_inputs,gates,outputs)`; `MAJ3Gate(operands)` exactly three
ordered integer refs. Inputs 0..n-1, gate refs n+i, topological; duplicates and
fanout legal, no constants/inversions/other gates. One input returns wire.
`build_majority(n,limits)`, `evaluate_boolean(circuit,bits)`,
`verify_majority(circuit,limits)`. Evaluation uses existing CausalBool apply_gate.
Versioned stable JSON; structural hash excludes timings. Additive symbolic API
uses existing shared decision manager, preserving Network and legacy codec.
`LinearExpression(constant,terms)`; `QuadraticConstraint(A,B,C,label)`;
`ConstraintSystem(prime,public_inputs,private_inputs,auxiliary_signals,constraints)`.
Terms mapping names to integer coefficients. Decimal-string large integers in JSON.
Separate builders, witness generators, serialized-row evaluator, generic Circom
export. Export treats all supplied witness signals as circuit inputs so every
constraint is enforced independently of witness-generation assertions.
Fourier explicit `rotate`, `add`, `multiply_known_vector` DAG, input ref zero;
lazy coefficient descriptors. Independent DAG counts and maximum path depth.

## Acceptance tests (lead owned)
A-Q1: lengths 1,2,16,128; big integers, ones, repeats, unequal, max digit;
instrumented query count, malformed lengths/entries/bounds/responses.
A-Q2: exhaustive n=1,3,5,7,9,11; exact DD n=13,15; independent basis validation;
invalid refs, duplicate ports, shared DAG, even n, resource failure, altered
circuit, nine-input naive-majority counterexample. Report emitted counts only.
A-Q4: exact polynomial coefficients and exhaustive p=3,5,7,11,13,19 examples.
A-Q5-8: compile all four families, executable witnesses, snarkjs check; export
actual compiled rows and witness, independently check mutated assignments.
Range 0,1,2^64-1 and >=2^64; nonbinary bits; one exclusion; zero/unit factors;
changed public product; aliases. Q8 balanced 2048-bit and 2*(2^4094+1) both
orders; overflow; partial product/carry/endpoints/high-limb mutations; exposed
omitted range/carry constraints. Witness-generator refusal alone never counts.
A-Q3: every basis through N=128 vs direct DFT; N=512,1024 conventions;
at targets zero, constant, boundary/interior impulses, modes, four random seeds.
Normalized max error <=1e-10. Independent DAG counts/depth<=3; malformed rotation,
bit reversal, twiddle detected. Every candidate status recorded, selected cost
strictly below same-model dense baseline. Incomplete search forbids best claim.
A-INT: new suite actually collects required tests; affected CausalBool regressions
and legacy serialized outputs unchanged; CI; PDF resolves references, no clipped
math; every numerical result traceable to command and evidence. Keep source,
small examples, final results and hashes, omit caches and bulky intermediates.

## Evidence, environment, and execution
Each check records requirement/test IDs, PASS/FAIL/UNKNOWN, hashes, size/seed,
exact/numerical comparison and tolerance, command/exit, elapsed/resource outcome.
`python -m oxparc_challenge verify-release` fails on missing tools or UNKNOWN.
Python 3.13, numpy 2.4.3, pytest 9.1.1, separate locked environment;
Circom 2.2.3, snarkjs 0.7.6; exact runtime versions retained. Existing LaTeX.
At most two concurrent Luna workers with disjoint files. Default timeout 300s,
Circom 600s, Fourier 900s/case; heavy processes individually, 4 GiB memory;
challenge DD budget 2,000,000, existing defaults unchanged. Exhaustion UNKNOWN.
Lead owns proofs, shared contracts, acceptance tests, integration and claims.
Workers may add component tests, never weaken acceptance or alter fixtures.
Task states: planned -> ready -> assigned -> submitted -> accepted;
assigned -> blocked; submitted -> changes_requested -> assigned. Only lead accepts.
Every task card has all fields in TASKS.yaml. Handoff: ID/base/contract, changed
files, exact commands/exits, artifacts/hashes, failed/skipped/unexecuted checks,
limitations/requested changes. Worker completion is submission, not acceptance.
Dependency graph and task scopes are in TASKS.yaml. Resume by reading all three
plan files, verifying hashes/revisions, and continuing dependency-ready tasks.
Final checkpoint records accepted revisions, versions, artifact/source hashes,
reproduction commands and deferred followups; all Q1-Q8 gates must pass.
