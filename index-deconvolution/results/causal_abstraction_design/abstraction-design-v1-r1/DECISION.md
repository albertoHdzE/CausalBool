# Decision — `abstraction-design-v1-r1`

**A useful finite design is justified; one draft is issued, NOT AUTHORIZED FOR EXECUTION.**

Choices and why:
- **Rule 150 ring (M1)** gives a nontrivial, hand-provable, intervention-testable abstraction
  (block-2 parity at τ = 2) and an exact negative (single-bit resets). Rule 90 was considered
  and rejected: on an 8-ring it is nilpotent (F⁴ = 0), making every map trivially consistent.
- **Counter (M2)** makes origin and time scale matter by hand (block start a valid iff 2^a | τ)
  and supplies the temporal negative control (tick).
- **Rule 30 (M3), EGFR (M4)** are the only cases without a built-in answer; they carry the
  substantive question. M4 is an owned file at the 10-bit cap.
- **Family A** covers widths 2–4, all origins, ragged blocks, five block functions (one
  reversible), global maps, projections and one imposed nesting level; tokens are globally
  aligned block values.
- **Structural β with representative hold-out** is the only predictive element of discovery
  and is declared independently of outcomes.
- **Gaps** enter only as a ranking heuristic against the exhaustive reference; fractal and
  scale-invariance claims are explicitly left untested.

Not decided here (for Codex/user): whether the checker core belongs in `src/deconvolution.py`
or a new declared core with a guard; whether `lac_operon.bnet` should be added as a declared
held-out model in a later, separate protocol.
