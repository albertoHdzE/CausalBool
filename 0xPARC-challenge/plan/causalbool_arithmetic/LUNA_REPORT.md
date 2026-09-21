# Luna implementation report — CausalBool arithmetic integration

Status: submitted for lead review; not self-accepted.
Base checkpoint: `9cd7509` / current HEAD at inspection:
`9cd7509cbe1831d2a1bbef26f9ed14169a292089`.
Branch: `doppel`.
Worker identity: Luna, GPT-5 implementation worker.
The checkout contained unrelated dirty files before this work; no historical
paper/manuscript file was modified.

## Delivered files

* `src/oxparc_challenge/boolean_arithmetic.py` — additive typed Boolean DAG,
  deterministic JSON/hash, validation, CausalBool evaluator adapter, full
  adder, bounded multiplier, and Boolean comparison builders.
* `src/oxparc_challenge/boolean_constraints.py` — Boolean-to-quadratic lowering,
  explicit bitness, gate-row mapping, scalar packing, Q5, Q6, and bounded Q7
  builders/witnesses. Uses the existing `ConstraintSystem` schema.
* `tests/test_boolean_arithmetic.py` — DAG contract, constants/duplicates,
  full-adder and multiplier exhaustive checks, malformed inputs.
* `tests/test_boolean_constraints.py` — serialized Q5/Q6/Q7 valid, negative,
  alias, truncation, factor, corrupted-wire and export checks.
* `tools/verify_boolean_arithmetic.py` — bounded reproducible verifier,
  independent integer oracle, local deconvolution replay, costs, hashes, and
  optional pinned-tool compile probe.
* `plan/causalbool_arithmetic/CONTRACT.md` — frozen executable contract and
  soundness/completeness argument.
* `plan/causalbool_arithmetic/STATUS.json` — stage state and blockers.
* `plan/causalbool_arithmetic/MANUSCRIPT_PROPOSAL.md` — held-for-review claims
  and reduced-table correction; no published manuscript edit.
* `evidence/causalbool_arithmetic/verification.json` — bounded evidence.
* `evidence/causalbool_arithmetic/verification.compile.json` — compile probe;
  Q5 is UNKNOWN because the pinned compiler is absent.

## Exact verification commands

Environment: macOS Darwin ARM64; CPython 3.13.12; pytest 9.1.1 from
`/Users/alberto/Documents/projects/CausalBool/venv`; Node v25.8.1. The plan's
requested `.venv` does not exist in this checkout, so the existing project venv
was used explicitly.

| Command | Exit | Result |
|---|---:|---|
| `PYTHONPATH=src /Users/alberto/Documents/projects/CausalBool/venv/bin/python -m pytest tests/test_boolean_arithmetic.py tests/test_boolean_constraints.py -q` | 0 | 25 passed |
| `/Users/alberto/Documents/projects/CausalBool/venv/bin/python -m pytest tests -q` | 0 | 88 passed |
| `PYTHONPATH=src /Users/alberto/Documents/projects/CausalBool/venv/bin/python tools/verify_boolean_arithmetic.py --output evidence/causalbool_arithmetic/verification.json` | 0 | PASS; 4096 Q7 triples |
| `PYTHONPATH=src /Users/alberto/Documents/projects/CausalBool/venv/bin/python tools/verify_boolean_arithmetic.py --compile --output evidence/causalbool_arithmetic/verification.json` | 0 | bounded checks PASS; external compile UNKNOWN |
| `PYTHONPATH=src /Users/alberto/Documents/projects/CausalBool/venv/bin/python -m py_compile src/oxparc_challenge/boolean_arithmetic.py src/oxparc_challenge/boolean_constraints.py tools/verify_boolean_arithmetic.py` | 0 | syntax check passed |
| `git diff --check -- src/oxparc_challenge tests tools/verify_boolean_arithmetic.py plan/causalbool_arithmetic evidence/causalbool_arithmetic` | 0 | whitespace check passed |
| `PYTHONPATH=src python3 -m pytest tests/test_boolean_arithmetic.py tests/test_boolean_constraints.py -q` | 1 | environment diagnostic: `/usr/local/bin/python3` has no pytest; not used as a result |
| `test -x .tools/circom` | 1 | pinned Circom absent |
| `test -x .tools/node_modules/.bin/snarkjs` | 1 | pinned snarkjs absent |

The compile probe itself records `UNKNOWN`, not PASS, in
`verification.compile.json`; no Circom R1CS, compiled-row, or snarkjs witness
claim is made.

## Evidence and costs

The verifier records SHA-256 structural hashes and serialized sizes. New route:

| Relation | Signals | Rows | Serialized bytes | Scope |
|---|---:|---:|---:|---|
| Q5 | 193 | 321 | 50,651 | 64-bit scalar range; double-NOT CausalBool DAG |
| Q6 | 1,376 | 2,499 | 427,362 | canonical field element; 254-bit comparator and exclusion |
| Q7 | 200 | 407 | 67,307 | width 4 only; complete product and stage carries |

Legacy comparator stats are Q5 65 signals/65 rows, Q6 2/1, and Q7 199/200
signals/200 rows. These are not efficiency comparisons: the new systems use a
gate-compiled Boolean route, and Q7 compares width 4 with the legacy width-64
builder. No performance win is claimed. The verifier elapsed in the final run
was approximately 39.2 seconds, with no resource exhaustion.

Checks include 8 full-adder states, multiplier exhaustive states 4/16/64/256
for widths 1/2/3/4, a deliberately defective carry block with counterexample
`bits=[0,0,1]`, expected `[1,0]`, actual `[0,0]`, and a six-node full-adder local
repertoire: 64 rows, named-gate recovery, and exact forward replay. The local
deconvolution result is diagnostic only and outside the constraint trust
boundary.

Q7 checks all `16^3 = 4096` `(u,v,n)` triples against the independent integer
predicate `u>=2 and v>=2 and u*v==n`: 16 valid and 4080 invalid. It exercises
swapped factors, unit factors, altered public product, high-product/truncation
attack `4*4` versus `n=0`, and a corrupted internal wire. The four-bit circuit
retains all 8 product bits and constrains all stage carries to zero; width 64 is
not implemented or claimed.

## Acceptance coverage

* L0: PASS locally. Ordered prior-wire DAG refs, duplicate ports, fan-out,
  constants, selected outputs, bit order, scalar/public/private semantics,
  failure behavior, and the MAJ3-only legacy boundary are documented.
* L1: PASS locally. AND/OR/XOR/NOT/TRUE/FALSE and MAJ3 lowering are explicit;
  all generated and external bits are constrained; deterministic gate-to-row
  labels are retained by `BooleanLowering`; serialized replay is independent.
* L2 Q5/Q6: PASS for local serialized rows and negative assignments. Q5 covers
  0, 1, and `2^64-1`. Q6 covers 0, 2, `P-1`, `r=1`, noncanonical bounds,
  nonbinary bits, and the `P+1` bit decomposition paired with scalar alias 1.
  Circom/compiled-row acceptance is UNKNOWN due missing tools.
* L3 Q7: PASS for the bounded width-4 acceptance scope, including exhaustive
  oracle coverage and negative assignments. Target width 64 is unmet and is
  explicitly not claimed.
* L4: PASS for evidence generation and conservative cost/design reporting.
  Q8 is feasibility/design only. Published manuscript integration and lead
  review remain outstanding.

## Hashes

Relevant reused sources:

* `../index-deconvolution/src/causalbool.py` —
  `856cd0f29549f49685de43cc8bfe0796f96ca91457d649d97275b74fdafb1100`
* `src/oxparc_challenge/constraints.py` —
  `aab64ac6a34dec80298c2fd0efba996e68313df475efeded5a66cd4113eaed98`
* `src/oxparc_challenge/row_evaluator.py` —
  `32a7844a04d8a141ecb698ccfc54d1d74e84042466290ebcf1bfd1970f822b55`
* `src/oxparc_challenge/circom.py` —
  `70ec744f68e75bb72d6d02db9b96ea501efd679cbfc5f7e4dceaac6fbd5c91ea`

New source/evidence hashes:

* `boolean_arithmetic.py` — `9d3847b34cc54ada2c9e7cbecacbbccdbef07fd3c118bec0dbcbb0769f501208`
* `boolean_constraints.py` — `a9a525278ef4c0576e3de39034301ae014e2827cdc93b47ea5c02b751731f3a6`
* `test_boolean_arithmetic.py` — `42d8b1e40352085f05617434691f794852b994c79d49e4fa2b6a667afd3419b8`
* `test_boolean_constraints.py` — `fc21bfbb1164f317a7e2a731866a49f36706873beee2a5e8f90c0ed7730a27bc`
* `verify_boolean_arithmetic.py` — `8852fd06fa898d6587d470abd7897de4959bf549bc64cea883d7d91933c5373c`
* `CONTRACT.md` — `ad18d5891c6d7a6d259effbe058c42ab26d91df7bb1c2777fb724b939f806e28`
* `MANUSCRIPT_PROPOSAL.md` — `a64e5f30961d58cddc54cc213f954f5db8f0fd2ad29a9d44a7beb8f2d538eb6f`
* `verification.json` — `38d5d7c36da9bce95b7315c76caf6b4c07735d6a8199b3d5dff764de64aafbec`
* `verification.compile.json` — `babe1fc887bbf2a347823816dd8b416d0403dfc84d12b28022721bf5338c6e60`

## Unmet criteria and reviewer reproduction

Unmet or unresolved: pinned Circom/snarkjs compile and compiled-row witness
checks are UNKNOWN; Q7 target width 64 is not implemented; Q8 remains design
only; no manuscript integration has been performed; lead review has not been
performed. These are intentional conservative boundaries, not failures hidden
by witness-constructor refusal.

Reviewer reproduction from `0xPARC-challenge`:

```
PYTHONPATH=src /Users/alberto/Documents/projects/CausalBool/venv/bin/python tools/verify_boolean_arithmetic.py --compile --output evidence/causalbool_arithmetic/verification.json
/Users/alberto/Documents/projects/CausalBool/venv/bin/python -m pytest tests -q
```

The first command should remain bounded PASS with compile status UNKNOWN until
the pinned tools are installed; with those tools installed at the plan's exact
paths, it is the lead's responsibility to rerun and independently inspect the
compiled rows and witnesses.
