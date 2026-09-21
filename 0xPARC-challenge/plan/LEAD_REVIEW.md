# Lead review and integration decisions

The user resumed lead-owned work after the Luna submissions. The integration
checkout remains based on main 37dae1623295f168017789e58b08eadfe0c12aa8.
No commit, push, merge, publication, or proof-system deployment is authorized
by this release. The completed challenge artifacts will also be copied into
the original workspace after verification, preserving its unrelated changes.

## Review findings and corrections

- The first N02 submission hardcoded zero-only fields and omitted the square
  equation for other fields. It was returned for correction. The current
  implementation enumerates all three equations; a separately written
  exhaustive acceptance test compares complete solution lists.
- The initial Boolean memoization included irrelevant inactive references.
  It was corrected to weighted subproblem keys. Lead review then corrected
  timeout checks and converted Python recursion exhaustion into the declared
  resource failure. Existing CausalBool sources and default limits are intact.
- The submitted manuscript incorrectly said that two rational queries cannot
  recover the list. The corrected statement is that one fixed rational query
  cannot suffice without a bound when n>=2; two adaptive queries do suffice.
  The final paper supplies the missing full mathematical arguments for Q1-Q8.
- The generic Q8 export initially overflowed the Circom parser stack on the
  4095-bit nontrivial-factor sums. Balanced sum syntax solves the compiler
  failure without changing signals, rows, the field, or the witness contract.
- Circom export now validates names and declared references; version checks
  match the exact version and reject operational failures. Snarkjs's documented
  observed help/version exit 99 is tolerated only for version detection.
- One malicious public-limb fixture initially decremented a zero limb, leaving
  the canonical domain. It was corrected to a valid base assignment with
  positive limb/carry values before the mutation. API rejection alone is not
  counted as compiled-constraint soundness evidence.
- The full compiled audit evaluates exported R1CS rows and mutated assignments.
  Deliberately weakened-row controls expose omitted factor, public-limb, and
  carry ranges. The soundness proof is independent of these finite checks.
- The PDF rendered successfully, but Poppler's extracted XML contained a
  control glyph invalid in XML. The geometry audit now replaces such glyph
  text while retaining every word's bounding box. The PDF has no overfull
  content or unresolved references; rendered pages were visually inspected.

## Ownership and protocol reconciliation

R01 and the initial F01/F02 implementation were written by the lead while
bounded Luna tasks ran. Luna reviewed F01/F02 and reported passing tests without
source changes. R02 was a separate Luna task. R03/R04 and R05 were implemented
by Luna. D01 was an early draft with pending results; its submission did not
meet final paper/PDF acceptance. The lead completed the proofs, references,
companion explanation, generated tables and PDF checks under resumed authority.
These are recorded as authorship of implementation work, not commit authorship.

Earlier STATE.json entries are submission history rather than proof that a
release passed. In particular, R03's earlier hash refers to its pre-R04 module
revision, and the old D01 README hash was truncated. Final accepted revisions
use hashes of the actual verified files. No hash mismatch is silently treated
as a verified historical revision.

## Final acceptance gates

`python -m oxparc_challenge verify-release` drives required test collection,
the package and affected legacy Python suites, compiled checks for Q5-Q8,
all target-size Q3 cases, discrete result recording, and PDF rendering.
It fails on an unknown or failed gate and produces a manifest only on success.
The two excluded legacy tests exercise Wolfram and BDM backends not used or
modified by this package; neither is claimed as a passing release check.
Observed process peaks and deadlines are recorded; heavy checks run sequentially.

The CI definition is supplied and its reproduction command is exercised locally.
A hosted CI run is not claimed because this task does not include pushing.
Actual ZK proof generation, CKKS ciphertext benchmarks, globally optimal Fourier
circuits, compactness at 2025 inputs, and full 2025 materialization remain outside
the accepted scope. They are non-release follow-ups, not silently skipped tests.
