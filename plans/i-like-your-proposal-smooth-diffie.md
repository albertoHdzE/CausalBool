# Making index deconvolution the responsible instrument for all eight answers

## Context

The 0xPARC response currently answers Q1–Q8, but index deconvolution is genuinely
load-bearing in only one of them. Q2 recovers majority from its repertoire and
replays it exactly (2,730 states, plus a nine-input negative control that
disagrees on 54 of 512 states). Q5/Q6/Q7 use CausalBool's *forward* gate
evaluator — `apply_gate` — under hand-written DAGs in
`0xPARC-challenge/src/oxparc_challenge/boolean_arithmetic.py`. The six-node
"deconvolution" probe in `tools/verify_boolean_arithmetic.py` is a forward
replay by its own comment and certifies nothing about the constraint systems.
Q1, Q3 and Q4 are pure mathematics with no CausalBool involvement.

The goal is that every answer's decisive predicate is **recovered from
behaviour and verified**, not asserted — and that the recovery is exact and
measurable. Cost is explicitly not a constraint; accuracy, scientific strength
and measurability are.

The enabling fact, which reframes the whole plan: the project already owns an
exact **non-exhaustive** engine. `doppel-challenge/src/doppel_challenge/repertoire_program.py`
is a reduced ordered decision-diagram manager with a canonical unique table
(`_Manager.unique`), so structural node identity *is* functional equality over
all 2ⁿ inputs. `0xPARC-challenge/src/oxparc_challenge/symbolic.py:45` already
uses it: `verify_majority` composes the MAJ3 circuit, independently builds
`threshold`, and compares roots — reported as `"exact canonical decision-node
identity"`. That is how n=13 and n=15 were settled without a 2ⁿ pass.
`_Manager.gate()` builds all twelve CausalBool gate families symbolically;
`src/Packages/Integration/Gates.m:192` `IndexSetAnalytic` is the closed-form
one-set on the Wolfram side.

Deconvolution has not yet been lifted onto that engine. It still consumes a
materialised `2**n x n` table (`index-deconvolution/src/deconvolution.py:356`).
Lifting it is the scientific core of this plan.

---

## Phase 0 — Checkpoint the current state (do first, before any edit)

`doppel` is 9 commits ahead of `origin/doppel`; `0xPARC-challenge` is clean at
`6842cdd`; 91 unrelated working-tree entries remain (63 regenerated artefacts
under `results/tests/`, plus `GOVERNANCE/VERIFICATION.md`, `figures/`,
`papers/method/code/scalability_resource_envelope/`, `tools/run_closure.sh`,
and untracked `audit/AUDIT04_H_stall/`, `results/step35_*`, `tools/joint_*`).

1. Commit the unrelated AUDIT04 artefacts as **one separate, clearly-labelled
   commit** — they are not 0xPARC work, but full reversibility requires a clean
   tree. Message names them as regenerated audit artefacts. Exclude `.DS_Store`
   (add to `.gitignore` if not already ignored).
2. Annotated tag `pivot-immediate-past` on the resulting 0xPARC head, matching
   the existing `pivot-ca-deconvolution` convention. Tag message records:
   branch, SHA, "bounded CausalBool arithmetic compiler; forward gate evaluator
   only; deconvolution load-bearing in Q2 alone", and the three commits
   `947a014 / 8f9f411 / 6842cdd`.
3. Push `doppel` and the tag to `origin`.
4. No Claude co-authorship, no `Generated with` trailer, substantive messages.

Recovery from this point is then `git checkout pivot-immediate-past`.

---

## The scientific pivot: symbolic index deconvolution

**Enrich the owner, do not fork it.** The owner of deconvolution is
`index-deconvolution/src/deconvolution.py`; the owner of gate semantics is
`index-deconvolution/src/causalbool.py`; the owner of the symbolic engine is
`doppel-challenge/src/doppel_challenge/repertoire_program.py`. The 0xPARC
subproject loads owners — the precedent is already set by
`tools/paper_index_examples.py:9` and `symbolic.py:11-16`. No second
deconvolution is written inside `0xPARC-challenge`.

Add a symbolic backend to the deconvolution owner, alongside (not replacing)
the exhaustive path, so the two can be cross-checked:

| Concept | Exhaustive (today) | Symbolic (to add) |
|---|---|---|
| essential variable | loop 2ⁿ, flip bit *i* | cofactors `f\|ᵢ₌₀` vs `f\|ᵢ₌₁` differ as canonical node ids |
| gate identification | build reduced table, compare | root identity against `_Manager.gate(g, Ic, params)` over the same twelve-family candidate list |
| forward verification | rebuild `2**n x n`, compare | canonical root identity of recompiled network vs original |
| schema / sumandos | enumerate on-set | `export_output_schemata` on the program |

This requires one small enrichment of the DD owner: a `restrict(root,
coordinate, value)` cofactor method (`apply`-based, memoised). Everything else
already exists.

The equivalence of the two backends is the guard: on every case small enough to
enumerate, exhaustive and symbolic must return identical essential sets,
identical canonical gates and identical match classes. That parity test ships
in the same commit as the symbolic backend.

**Stated barrier.** Bryant (1991) proves any decision diagram for the middle
bit of an *n*-bit multiplier is exponential in *n*. A monolithic 64-bit
multiplier program is therefore not constructible, and the plan does not
attempt one. Q7/Q8 recover and verify *cells* symbolically, then compose
structurally — see below. Threshold, comparator and equality functions have
polynomial diagrams, which is why Q2/Q5/Q6 scale directly.

---

## Per-question work and role ledger

Every question declares its role explicitly in the paper. Only **DERIVES** and
**CERTIFIES** count as load-bearing; anything that would only ILLUSTRATE is
said to illustrate.

### Q1 — hidden list (CERTIFIES)
Build the base-*B* digit-extraction decoder as a Boolean DAG at small width
(e.g. 3 entries × 4 bits), reusing `recovery.py:unpack` as the integer oracle.
Deconvolve each output bit: the recovered essential-variable set must equal
exactly the intended digit window of *R*, proving no digit leaks across slots.
Report the match/ambiguity class from `identify_gate` — this is the same
identifiability notion as the two-query lower bound, which stays a proof.
Measurable: recovered windows == expected windows, forward replay exact.

### Q2 — majority (DERIVES)
Already load-bearing; extend it. Move the recovery to the symbolic backend and
push past n=11 to the largest n the diagram admits (threshold diagrams are
polynomial, so this should reach well beyond 15). Report recovered essential
sets, canonical gate, full match classes, and schema counts via
`export_output_schemata`. Keep the nine-input negative control and add the
symbolic/exhaustive parity result.

### Q3 — Fourier (CERTIFIES structure; cost stays numeric)
The complex arithmetic is outside Boolean scope and the paper says so. What
deconvolution certifies is the **support structure**: for a candidate schedule
from `fourier.py:build_fourier`, derive the Boolean dependency indicator
(output *r* depends on input *j*) per stage block, deconvolve it, and check the
recovered dependency pattern against the radix-2 / bit-reversal prediction
already owned by `fourier_search.py:support` and `bit_reverse`. The fused
transform's support must be total; a deliberately wrong partition must fail the
check. Measurable: per-stage recovered support == predicted support; wrong
schedule detected. The 6.347× / 4.743× cost figures remain numeric measurements.

### Q4 — modular power sums (CERTIFIES exemplars)
For each small prime p ∈ {3,5,7,11,13,19}, build the solution-set indicator over
4-tuples from `modular.py:solutions`, deconvolve it, and report essential
coordinates and canonical structure. The p ≡ 3 (mod 4) cases must collapse to
the trivial schema; p=3 (9 solutions) and p=13 (73) are the exceptions already
recorded. The p = 2¹²⁷−1 result itself stays a proof; deconvolution certifies
the exemplars that motivate it.

### Q5 — 64-bit range (DERIVES)
Retire the double-NOT demonstration. Recover the comparator cell from its
repertoire, verify it symbolically, and build the 64-bit range predicate from
the *recovered* cell. Replace the hand-written `build_less_than_constant_dag`
path with the recovered-cell composition. Verify the full 64-bit predicate by
canonical root identity against an independently built specification — exact,
no enumeration. Compile to quadratic rows and re-check forged assignments.

### Q6 — r ≠ 1 (DERIVES)
Same pattern at 254 bits: recover the equality/comparator cells, compose to the
canonical-field exclusion predicate, verify by root identity, compile, forge.
The direct one-row system `(r−1)s = 1` is retained as an independent cross-check
and the size difference is reported plainly, not hidden.

### Q7 — 64-bit factorisation (DERIVES at cell level; structural at full width)
The strongest case. Deconvolve the full adder and the AND partial-product cell
from their repertoires — `identify_gate` will name sum = XOR and carry =
MAJORITY exactly, which is the method recovering the classical result rather
than being told it. Replace `build_full_adder_dag` and the inner cells of
`build_multiplier_dag` with the recovered cells. Then:
- exhaustive rows at width 4 (4,096 triples — already passing) and width 6;
- symbolic cell-level identity at every width;
- structural induction over the array composition (each column's carry
  obligation discharged by a verified cell);
- compiled-row checks on random and adversarial witnesses at full 64-bit width,
  including the truncation and alias attacks already in the suite.
`Q7_WIDTH = 4` at `boolean_constraints.py:22` is removed as a ceiling.

### Q8 — 4096-bit factorisation (DERIVES at cell level; structural at limb level)
Compose the same recovered cells into 64-limb multiplication with the existing
bound discipline (q < P, column sides < 2¹³⁵ < P, 70-bit intermediate carries).
Verify at reduced limb counts exhaustively, cell-level symbolically, and the
64-limb system by structural identity against the existing direct
`gadgets.py:build_factor4096` (25,725 rows) plus adversarial witnesses.

---

## Files

**Owners enriched (outside 0xPARC-challenge):**
- `index-deconvolution/src/deconvolution.py` — symbolic backend for
  `essential_variables`, `identify_gate`, `verify_forward`; exhaustive path kept.
- `doppel-challenge/src/doppel_challenge/repertoire_program.py` — add
  `_Manager.restrict` cofactor.

**0xPARC-challenge (composition and evidence only):**
- `src/oxparc_challenge/boolean_arithmetic.py` — cells sourced from recovery,
  not hand-written; `build_full_adder_dag`, `build_multiplier_dag`,
  `build_less_than_constant_dag`, `build_not_equal_constant_dag`.
- `src/oxparc_challenge/boolean_constraints.py` — remove the width-4 ceiling;
  compile recovered cells.
- `tools/verify_boolean_arithmetic.py` — replace the decorative replay probe
  with the real per-question certificates; emit the role ledger.
- New `tools/paper_certificates.py` — Q1/Q3/Q4 certificates, following the
  established shape of `tools/paper_index_examples.py`.
- `tests/` — parity tests (symbolic vs exhaustive), per-question certificate
  tests, recovered-cell regression tests.
- `evidence/` — regenerated records; every table entry traceable to a command
  and source hash, as now.

**Paper — keep the existing organisation and visual language exactly:**
`response.tex` (main), `supplementary.tex` (S-sections), `results.tex`
(generated by `tools/build_paper.py`, never hand-edited), `response.md`
(reading companion), `README.md`, figures in `generated/` from
`paper_network_figures.py` and `paper_operation_figures.py` — teal/orange
palette, network–matrix–pattern panels, figures generated from evaluated states
and hash-checked before use. Changes: rewrite §`sec:index-capability` as the
role ledger; per-question subsections stating what was recovered and verified;
one new figure in the established style showing repertoire → recovered cell →
composed circuit → constraint rows → verification.

---

## Verification

Run from `0xPARC-challenge`:

```sh
PYTHONPATH=src ../venv/bin/python -m pytest tests -q
PYTHONPATH=src ../venv/bin/python tools/verify_boolean_arithmetic.py \
    --output evidence/causalbool_arithmetic/verification.json
PYTHONPATH=src ../venv/bin/python tools/paper_certificates.py
PYTHONPATH=src ../venv/bin/python tools/build_paper.py
```

Acceptance:
1. Symbolic/exhaustive parity holds on every enumerable case — identical
   essential sets, canonical gates and match classes. **Print the denominator**:
   "parity over 0 cases" is the failure this guards against.
2. Each of Q1–Q8 emits a certificate naming its role, the object recovered, the
   verification method (exhaustive / canonical identity / structural +
   adversarial), and its explicit limit.
3. Q5 and Q6 verified at full width by root identity; Q7 and Q8 verified at
   cell level symbolically and at full width structurally with adversarial
   witnesses.
4. Both PDFs compile with no overfull boxes, unresolved references or clipped
   words (already enforced by `build_paper.py:86-98`).
5. Every number in the paper comes from `results.tex`, generated from evidence.

## Limits to state in the paper, not discover later

- Circom/snarkjs remains **UNKNOWN** — the pinned tools are absent, so all
  Q5–Q8 claims rest on the project's own serialized-row evaluator. This applies
  to both the direct and recovered routes.
- Bryant's bound forbids a monolithic 64-bit multiplier diagram; Q7/Q8
  full-width correctness is structural induction over symbolically verified
  cells, not a single exact object.
- The recovered-cell route is larger than the direct route (Q6 is 1 row direct
  versus thousands compiled). Reported plainly as a representational result,
  with no performance claim.
- Deconvolution recovers the computed function, not a unique gate arrangement;
  several circuits share a repertoire. Already stated at `response.tex:264`.
