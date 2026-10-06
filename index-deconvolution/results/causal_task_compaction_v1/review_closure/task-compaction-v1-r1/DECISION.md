# Decision: task-compaction-v1-r1 closure

**Recommendation: adopt after Codex review. NO_NEW_STUDY_JUSTIFIED.**

1. **R1 (audit) closed in a separately identified revision.** `src/audit_r2.py` reruns
   the frozen audit's independent checks, imported by path and hash-verified. It
   replaces only the pipeline: schema, availability and integrity, then reporting.
   - All 23 declared matrix cases behave as required.
   - The frozen audit reproduces all three Codex defects on the same copies.
   - On the saved 24-cell dataset the result is VALID_COMPLETE, and every original
     scientific value is identical: 24/24 cell rows, 10/10 shared denominators, and the
     refinement, FX1 and hand-check results.
2. **R2 (replay contract) closed in the isolated owner.** `task_word_path` now uses the
   minimizer's own table validator (`_transition_contract`, factored out of
   `_task_contract`, with error messages unchanged). The 21 new tests include the three
   review examples. The old implementation fails 11 of them, all on actual behaviour.
3. **Packaging.** The fixture moves byte-identically to
   `tests/fixtures/task_compaction_v1.json` (sha256 6f7f7cd5…cbef690). The owner tests
   pass with the run directory absent.
4. **No scientific discrepancy was found.** The original production was not rerun,
   nothing was retuned, and the frozen evidence is byte-identical (397/397 manifest
   records, 59/59 freeze identities).
5. **Positioning.** The component is an established theorem, the greatest congruence
   (Knuutila 2001, Prop. 4), implemented for an all-start, multi-action, multi-label
   contract. Its K\* = N outcome is exactly Zhang & Zhang Definition-5 observability.
   GFB and BBE scale by changing the object or the domain. No new study is justified
   without a concrete need (V1_COMPLETION_PLAN.md).
