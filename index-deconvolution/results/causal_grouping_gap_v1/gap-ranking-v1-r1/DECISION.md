# Decision — gap-ranking-v1-r1

**Ready for Codex review; not yet accepted.**

Evidence status: **VALID_COMPLETE** (independent audit, 0 failures, 0 missing; 3 of 3
corruptions caught). Run status: complete; no FAILED_RUN condition arose.

Descriptive outcome, without a single verdict (PROTOCOL.md §5):

- Against the exact random-order expectation, the declared recurrence-gap ordering reaches the
  first FULL causal state grouping earlier in 5 cells, later in 9 and ties in none, of 14 cells
  with a FULL reference. Two of the five earlier cells (M3 τ = 8, 16) are first hits with
  constant induced dynamics.
- Against canonical candidate order it is earlier in 12, later in 2, tied in none. Canonical
  order places every F3 projection behind 36 lossy F1 candidates, so this comparison is weak.
- Six cells (M1 all τ, M3 τ = 1) have no FULL candidate and carry no rank.

Reading: on this population, the declared heuristic does not consistently schedule FULL
groupings ahead of a random ordering; its advantage over canonical order is largely an effect
of where canonical order puts F3. The score saturates at R = 1 for most partitions once the
sampled trajectories are short (τ ≥ 4), after which the ID tie rule dominates the ordering.

No tuning, re-run or follow-up study is started under this run ID or automatically. Whether
the heuristic deserves a redesigned (pre-registered) successor is a supervisor decision.
