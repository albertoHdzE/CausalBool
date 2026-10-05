> **Corrected copy** (`review_closure/abstraction-design-v1-r1`, closing REVIEW R1–R3 and nonblocking notes). Original unchanged at `../../../abstraction-design-v1-r1/`. Changes: `../CHANGELOG.md`.

# Decision — `abstraction-design-v1-r1` (corrected)

**A useful finite design is justified; one draft is issued, NOT AUTHORIZED FOR EXECUTION.**

Choices and why:
- **Rule 150 ring (M1)** gives a nontrivial, hand-provable, intervention-testable abstraction
  (block-2 parity at τ = 2) and an exact negative (single-bit resets). Rule 90 was considered and
  rejected: on an 8-ring it is nilpotent (F⁴ = 0), so every **autonomous** check is trivial at
  τ ≥ 4 (knockout and tick checks need not be).
- **Counter (M2)** makes origin and time scale matter by hand (block start a valid iff 2^a | τ),
  supplies the temporal negative control (tick) and the R1 counterexample.
- **Rule 30 (M3), EGFR (M4)** carry the substantive question; M4 is an owned file at the 10-bit cap.
- **Family A** unchanged (135 / 141 candidates; 2,730 (α, τ) rows); tokens are globally aligned
  block values.
- **β_fine (R1)** keeps the local bit position, so per-q existence is the primary test; coarse
  grouping survives only as declared hypotheses H-COARSE (lossy maps) and H-OUT (F3), scored
  separately and never tuned.
- **Decision table (R2)** makes every label exclusive and scoped to A / Q / β; X is restricted to
  autonomous support closure; the majority-F3 stop rule is removed.
- **Gaps** enter only as a ranking heuristic; fractal and scale-invariance claims are untested.

Decided in this closure (following REVIEW R3): prospective checker owner
`index-deconvolution/src/deconvolution.py` (ticket `../OWNERSHIP_TICKET.md`; no source edited).
Description length deferred. Still open (for Codex/user): U2 owner/route for the block-value
occurrence extractor and U3 the import route to the sibling repository; whether `lac_operon.bnet`
becomes a held-out model in a later, separate protocol (not in this draft).
