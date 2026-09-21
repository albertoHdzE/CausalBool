# CausalBool arithmetic Boolean-to-quadratic contract

Version: `causalbool-arithmetic-v1`
Base checkpoint: `9cd7509` (worker checkout was already dirty; unrelated edits are outside this subtree)

## Boolean DAG

`BooleanDAG(n_inputs, gates, outputs)` uses integer wires `0..n_inputs-1` for
ordered inputs and `n_inputs+i` for gate `i`. Every operand must refer to an
earlier wire. Duplicate operands and fan-out are legal; malformed references,
cycles (which cannot satisfy the prior-wire rule), unsupported gate kinds and
wrong arities fail explicitly. Outputs are selected wire references and are
evaluated after the complete combinational DAG. A synchronous CausalBool
`Network.step` is not used as a multilevel circuit evaluator.

Supported gates are `AND`, `OR`, `XOR`, `NOT`, `MAJORITY` (three ordered
operands), and zero-input `TRUE`/`FALSE`. Evaluation calls the existing
`index-deconvolution/src/causalbool.py:apply_gate` for each gate. The existing
`BooleanCircuit`/`MAJ3Gate` API remains unchanged and MAJ3-only.

Arithmetic inputs are little-endian bit vectors (`b0` is weight 1). Scalar
bindings are exact field equations

```
1 * scalar = sum(2^i * b_i)
```

and every supplied or generated bit has a row `b*(b-1)=0`. Public, private and
auxiliary signal lists are deterministic and disjoint. A witness generator is
only a convenience: serialized rows are the acceptance boundary and are
evaluated independently.

## Quadratic lowering

Rows are always `A(w)*B(w)=C(w)` over the frozen BN128 scalar field `P` from
`oxparc_challenge.FIELD_PRIME`.

* `AND(a,b)=z`: `a*b=z`.
* `OR(a,b)=z`: `a*b=a+b-z`.
* `XOR(a,b)=z`: `(2a)*b=a+b-z`.
* `NOT(a)=z`: `1*(1-a)=z`.
* Constants use `1*1=z` and `1*z=0`.
* `MAJ3(a,b,c)` uses `t=a AND b`, `x=a XOR b`, `y=c AND x`,
  `z=t OR y`, with explicit auxiliary rows and bitness rows.

For Boolean inputs, these identities are sound by their truth tables. Their
quadratic relations plus bitness are complete because each relation uniquely
determines the named output bit for each input tuple. Induction over the
topological gate order gives soundness and completeness for a whole DAG.

## Question coverage

Q5 binds a private 64-bit `x`; a double-NOT identity DAG is compiled through
CausalBool before packing the bits. Q6 uses `Q6_WIDTH = P.bit_length()` bits,
packs private `r`, enforces `r < P` with a Boolean comparator, and accepts only
the Boolean `r != 1` predicate. The canonical bound is mandatory: a `P+1`
bit decomposition paired with scalar alias `r=1` must fail the comparator.

Q7 is intentionally bounded to width 4. It uses a full `2w`-bit shift/add
multiplier built from AND/XOR/NOT/OR gates, keeps stage carries, binds the low
product bits to public `n`, constrains all high product and stage-carry bits to
zero, and accepts only `u>=2` and `v>=2`. No 64-bit CausalBool Q7 claim is made.

Q8 is feasibility/design only in this milestone; no implementation or target
size claim is made.
