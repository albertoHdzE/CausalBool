# DECISION — `abstraction-validation-v1-r1`

**V/D/X executed under freeze. The checker is validated against every hand prediction, and the
exhaustive D reference is complete. G is deferred (U2/U3). Status: ready for Codex review; not yet accepted.**

Choices made during execution, none of which alters a declaration:
- **Core owner.** The fibre condition lives only in `index-deconvolution/src/deconvolution.py`. The patch is additive:
  five functions, `canonical_partition`, `fibre_sizes`, `induced_map`, `compare_induced` and
  `commutation_failures`. No existing API changed. The guard is in
  `tests/test_abstraction.py`; it is textual and rejects a planted copy. It allowlists only the named audit oracle.
- **E2 is the q_id record.** F_{q_id} = F^τ, so the E2 fibre check and the q_id E3 check are one computation, stored
  in both fields. The audit checks that the two fields are equal in all 2,730 rows.
- **Witness rules** follow addendum §3. Fibre witnesses are the lexicographically smallest violating micro pair.
  Macro witnesses are the smallest disagreeing canonical code. All of them were re-verified in-run (94,363).
- **Presentation-only files** (`report.py`, `render_nonf3.py`, `report_tables.*`, `nonf3_full_maps.json`) were
  written after D. They are hashed separately and change no measured row.

Scientific reading, scoped to A / declared Q / β:
- The substantive question asked whether lossy, intervention-compatible macro variables exist in rule 30 and EGFR
  beyond the dependency structure. In rule 30, every FULL lossy map is the all-ones indicator, whose induced maps are
  constant. In EGFR, the only non-constant non-F3 FULL map is `F4 or∘or (4,1) o2=1` at τ ∈ {8,16}. Its dynamics
  reduce to the retained self-looped input v000.
- Position-free coarse grouping (H-COARSE) is falsified on every row except the 11 constant-map rows. H-OUT holds
  exactly on the FULL F3 rows of M2 and M4.

Not decided here: whether the degenerate (constant-G) FULL rows should be excluded by a future declared
non-triviality endpoint. That would be a new design question for Codex and the user, not a post-hoc relabelling of this run.
