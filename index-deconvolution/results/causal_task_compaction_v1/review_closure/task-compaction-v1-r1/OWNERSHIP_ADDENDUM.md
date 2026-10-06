# Ownership addendum (closure of task-compaction-v1-r1)

- **Owner unchanged:** `index-deconvolution/src/deconvolution.py`. Public names are
  `minimal_task_partition`, `distinguishing_task_word` and `task_word_path`. The third
  is authorized by this ticket with the R2 contract.
- **Change inside the owner (private):** `_transition_contract(transitions, N=None)` is
  factored out of `_task_contract`. `_task_contract` validates `outputs` and delegates,
  and its error messages are unchanged. `task_word_path` calls `_transition_contract`
  with no N, then validates x and the whole word before replaying. No new public API and
  no second engine.
- **New test-owned file:** `index-deconvolution/tests/fixtures/task_compaction_v1.json`,
  a byte copy of the run file `task-compaction-v1-r1/fixtures.json` (sha256
  6f7f7cd5f456f5b9c389c5fab93dd63773ba6d6246a337c75983e6cafbcef690).
  `tests/test_task_compaction.py` changes only its fixture lookup and docstring, plus 21
  new R2 tests appended.
- **Read-only dependency (recorded, unchanged):**
  `doppel-challenge/src/doppel_challenge/repertoire_program.py`, mirrored byte-identically
  in `isolated/` (origin in `isolated/ORIGINS_at_copy.json`, inherited from the original
  run).
- **Historical regressions:** the 73 accepted regression tests still read their accepted
  historical study fixtures under
  `results/causal_abstraction_validation/abstraction-validation-v1-r1-source-r2/`. This is
  disclosed and not moved.
- **Run-local verification exception:**
  - `src/audit_r2.py` is a revision of the frozen audit with its own identity. It
    imports the frozen `audit.py` checks by path after verifying sha256 3198a656…; it
    does not copy them.
  - `src/probe_matrix.py` imports the frozen `corruptions.py` functions.
  - `src/owner_check_r2.py` imports the frozen `owner_check.py` scan.
  - None of them imports the producer, the minimizer, the witness or the replay helper.
- **Guard:** `src/owner_check_r2.py`. Over 18 files it finds exactly one definition of
  each of the three names, in the closure's isolated owner, and no copy of the
  refinement-signature fragment. Planting a renamed copy and a same-name copy makes it
  fail.
