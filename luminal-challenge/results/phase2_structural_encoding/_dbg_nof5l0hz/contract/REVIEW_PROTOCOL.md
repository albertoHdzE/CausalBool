# Independent review protocol

Reviewer: Codex. This file is a review specification, not a completed review.
The implementer reads it so acceptance is predictable, but must not write the
reviewer's verdict or fabricate reviewer reruns.

## 1. Entry and integrity

Record review HEAD, status, complete changed-file list and the worker handoff.
Run `python3 plan/phase2/verify_package.py`; verify worker source snapshots against
the actual tree. Hash the full reviewed diff. Check exclusive file ownership,
reference hashes, unchanged production and all pre-existing edits. A contract
edit by the worker requires lead adjudication; it cannot be self-approved.

Inspect each gate's raw inputs before running its checker. In particular, derive
expected program/seed/budget/repetition identities from the frozen protocol and
compare sets, not counts alone. Confirm the twelve fixture inputs are unchanged,
held-out generation preceded tuning, and none of the original failed runs vanished.

## 2. Mathematical and source review

Trace actual callers from CLI through Domain, layout, decode, candidate acceptance,
search and serialization. Review encode/decode as inverse maps with fixed offsets.
Check malformed input, B=0, non-power-of-two ranks, all external constraints,
fixed-fixed scratch conflicts after selected reads move, pending writes and
same-cycle boundaries. Verify no filtering can conceal a completed illegal output.

Re-derive the induction in PROOFS.md against the implementation. Enumerate tiny
domains independently from JSON and machine, without using candidate option logic.
Compare full normalised sets, not just the first witness. Inspect each pruning
bound against every completion in small fixtures. Check both satisfiable and
unsatisfiable domains and interruption during construction, decoding and validation.

Review cube serialization, exact merge equality, disjointness, tie handling and
empty-set behavior. Check that model proposals really include unseen codes, that
all such codes are paid and independently checked, and that training indices
cannot become test discoveries. Inspect sampler bias and duplicate accounting.
Trace runtime dependencies and plant a forbidden import and duplicate owner in
temporary fixtures to verify the architecture guard's actual scope.

## 3. Required reruns

Run all four new unit modules and all acceptance-matrix failure injections in a
new reviewer-owned result directory. Recompute P0/P1 tiny sets and P3 covers and
controls from raw inputs; rerun public P1 streams with the frozen seeds and caps.
Compare deterministic outputs exactly; treat timing-dependent outcomes according
to actual limits. A new inconclusive coverage result is reported, never waived.

Rerun the unchanged export, canonical verification and three-repeat comparator
using fresh output paths. Revalidate every retained best candidate with every
case. Recompute statistical summaries independently from retained raw rows,
using protocol constants rather than reported constants. Check family weighting,
program-level resampling, technical replicates, seed aggregation, failure rows
and the two Bonferroni-adjusted H4 advancement intervals.

For a positive performance/discovery claim, repeat the full claimed primary
comparison on the relevant frozen corpus with fresh isolated processes and the
same budgets; a handful of examples cannot accept it. Secondary sensitivity
results may be audited from raw rows after their harness is verified. Record
all inter-run changes, including failure to reproduce a positive interval.
For a null result, independently reproduce the decisive failed gate and verify
all independent stages required by the dependency graph were still completed.

## 4. Adversarial evidence checks

Apply every mutation in ACCEPTANCE_MATRIX.json to a valid copied artifact set.
The checker must reject the mutation for its intended reason; a missing unrelated
file is not a successful test. The unmutated control must pass first. Mutation
fixtures stay separate from real evidence. Force clocks/counters through test
seams; do not enlarge real timeouts or edit the pinned validator.

## 5. Verdict

Write a separate `LEAD_REVIEW.md` with source/diff hashes, commands, raw evidence,
numbered findings, severity, exact file/line references and reproduction steps.
Use `ACCEPTED`, `ACCEPTED_WITH_LIMITATIONS` or `CHANGES_REQUIRED` for research
implementation acceptance. Keep H1–H4 scientific dispositions separate; accepting
a reproducible null result does not mean accepting a hypothesis.

Production integration remains NOT_PROPOSED unless a later explicit integration
assignment satisfies the original direct-schema architecture, export and release
contract. No review verdict automatically authorises publication or submission.
