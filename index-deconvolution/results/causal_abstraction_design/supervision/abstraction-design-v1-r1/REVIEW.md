# Codex review — abstraction-design-v1-r1

2026-10-05. **CHANGES REQUESTED. Design direction retained; execution not authorized.**

The finite models, globally aligned state maps, separation of supplied validation
from induced-model discovery, and explicit limits on gaps/nesting are useful.
No new compression extension or query-recovery study is warranted by this design.
The following three findings should be closed together in a document-only revision.
No empirical result is being rejected: no experiment has run.

## R1 — intervention grouping confounds the intended comparison (high)

`MODEL_AND_MAPS.md` §5 assigns every in-block F3 flip the same beta label,
regardless of its position. It likewise merges within-word flips for reversible
F1 `val`. These operations generally have different effects on retained values.

Concrete proof, without running a model: M2, tau=1, alpha=low nibble (P2).
At x=0, flipping bit 0 then stepping gives alpha=2; flipping bit 1 then
stepping gives alpha=3. Track D assigns both `(flip, in)`. Its representative
macro map therefore cannot agree with both. P2's correctly position-labelled
macro operations do agree. For reversible F1 `val`, the two successor states
also have different macro encodings, despite the claim in §4 that recodings
are "always consistent". Injectivity guarantees individual induced-map
existence, not consistency under an arbitrary many-to-one beta.

The coarse grouping is mathematically legal as a hypothesis, but it is not a
neutral test of whether the retained variable admits intervention dynamics.
Correct value-preserving maps' beta to retain the local bit position (F3) or
coordinate plus within-word position (F1 val). Keep coarse grouping for lossy
maps only as an explicit, separately scored hypothesis. Do not tune it after
observing results. Distinguish existence failure from disagreement of otherwise
existing maps sharing beta. Identity/recoding control labels must never mask
the latter. Add the counterexample above to the prospective fixture declarations.

## R2 — conclusions and failure states exceed the tested property (high)

`DESIGN.md` §6 says absence of FULL non-F3 results leaves only recodings,
constants and support-closed projections as exact abstractions. A failure of
the declared beta does not establish that: another beta may work, or a map may
be autonomous but fail a declared intervention. Every negative conclusion must
name the candidate family, Q and beta. Report autonomous existence, per-q
existence and shared-beta agreement separately.

Track X proves only autonomous closure under F^tau. It does not predict full
intervention consistency, especially mechanisms replaced throughout tau steps.
The execution draft's majority-F3 "falsifier" cannot turn the whole study into
dependency-graph analysis, nor erase any non-F3 successes. Replace it with a
descriptive count; keep the scope of X explicit everywhere.

Also specify what happens when a class representative has no induced map.
This is an observed structural failure, not missing evidence or a harness
defect. E4 cannot compare against a nonexistent map; store that reason and
separate intended/inspected pairs from evaluable equation comparisons. Do not
invent numeric mismatch counts. Define RESTRICTED versus AUT-ONLY exactly
(identity is always present for an autonomous pass), representative/hold-out
failures, and mixed missing/failing evidence. A decision table should make
implementation possible without further scientific choices.

## R3 — complete the prospective execution specification (medium)

The draft still leaves implementation-affecting choices unresolved:

- Resolve an owner for the checker before code. Codex's prospective choice is
  `index-deconvolution/src/deconvolution.py`: extend the existing core, with
  thin study orchestration, no new competing core. Write the proposed ticket
  in the closure; this review authorizes no source edits. Resolve import paths
  explicitly: root `src/description_lengths.py` and index-deconvolution's
  `src/deconvolution.py` are different source roots. Confirm the occurrence-gap
  owner's actual path/API by reading; document an unavailable dependency.
- Give total candidate ordering, including F2/F4/controls, unique ID numbering,
  exact deterministic audit subset and its count. "10%" by ID mod 10 is not
  necessarily exactly 10%, and the current ID scope is unspecified.
- Define Track G's eligible population N and m consistently, pooling of
  occurrence sets across trajectories, unavailable ordering, and whether
  duplicate partitions remain in the scheduling population. The random-order
  formula is valid only for that same fixed population. Retain deterministic
  ranking and no significance/causal claim.
- E7 does not define an encoding or cost API for a mixed-alphabet nested map.
  Specify a defensible owned encoding, or explicitly defer description length
  and retain only execution/selection costs. No new codec is required merely
  to provide an optional descriptive number.
- Specify development fixtures and meaningful tests before production freeze;
  hash implementation sources as well as declarations at freeze. Include
  wrong beta, failed representative, missing evidence, ragged blocks and
  counting controls. Freeze the audit selection before observing D. Compare
  scientific fields canonically, excluding runtime metadata; bytewise
  comparison of independently timed complete records is not appropriate.
- The expected <300 s runtime is an unmeasured estimate, not a feasibility
  result. The future execution allowance must explicitly cover development,
  tests, run, audit and handoff, with a supervisor reserve. No execution is
  authorized by revising that budget.

## Nonblocking corrections to include in the same revision

M1 degenerates at 3 of 5 temporal scales, not "half". Rule 90's F^4=0 makes
autonomous maps trivial at those scales, not necessarily all knockout/tick
intervention checks. Per-string first-occurrence labels can be deterministic
functions of that string/state; the problem is the undeclared semantic alignment
and information they discard, not automatic failure to be a function.
Remove the "repeated structure found" endpoint unless a precise test is added;
the design already says scale invariance and grammar are untested. Imposed
nesting remains a candidate construction, not an empirical discovery.

No literature correction cycle is needed. Primary text confirms the limited
prior-art statements: [Song–Grochow, §I–II](https://arxiv.org/pdf/2012.12153)
defines the CA coarse-graining equation and studies elementary-CA pairs through
supercell size 7; it does not enumerate every map at every larger size after
finding a pair. [Israeli–Goldenfeld, §III.B.1](https://arxiv.org/pdf/nlin/0508033)
explicitly calls rule 150 a fixed point of its coarse-graining transition map.
Neither observation establishes novelty for this proposed intervention study.

## Verification, preservation and budget

`audit_review.json`: 10/10 document-integrity/arithmetic checks pass: 18 input
hashes, 11 manifested output hashes, 56 protected files, matching preservation
records, JSON parsing, declaration arithmetic and all 12 design files unchanged.
The seven supplied-control formulas and their 2,080/30,976 failing-pair total
are consistent by mathematical inspection; no simulator, witness or experiment
was run. This review does not certify the yet-unimplemented checker.

Review started 14:50:09 UTC. Charge 300 s conservatively from the reserved
supervisor allowance. Executor 738 + review 300 = **1,038 / 1,800 s**.
The remaining 762 s can support one document-only closure: at most 462 s Claude,
300 s retained for Codex. No historical budget is rewritten or transferred.
If incomplete at the cap, hand off the truthful partial correction and stop.

See `CLOSURE_CLAUDE.md` for the complete delegation. No commit, push or scheduling.
