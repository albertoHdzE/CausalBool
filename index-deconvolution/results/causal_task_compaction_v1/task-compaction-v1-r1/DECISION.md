# DECISION — task-compaction-v1-r1

Status: ready for Codex review; not yet accepted.

Run status: VALID_COMPLETE. The verdict comes from the independent audit: 0 invalid and
0 missing, over 24 of 24 cells and 3,276 of 3,276 records.

Per-cell outcomes are counts, not a global verdict.
- INTERVENTION (primary): 3 EXACT_REDUCTION, 9 NO_REDUCTION; 11 MATCHES_OPTIMUM,
  1 CANDIDATE_GAP (M4/T1).
- AUTO (controls): 10 EXACT_REDUCTION, 2 NO_REDUCTION; 5 MATCHES_OPTIMUM, 7 CANDIDATE_GAP.

What the review is asked to decide (nothing here is decided by the executor):
1. **Correctness.** THEORY.md is the proof. The audit, the corruption probes and
   reproduction are the evidence; it is in CLAIMS.md.
2. **Integration readiness.** `patches/deconvolution_owner.patch` and
   `patches/test_task_compaction.patch` pass `git apply --check` against the active tree.
   Applied in a disposable copy, they give 104 passed (73 + 31). The test reads
   `results/causal_task_compaction_v1/task-compaction-v1-r1/fixtures.json`, so that file
   must stay where it is if the patches are adopted. The extra public helper
   `task_word_path` is a declared addition to the ticket's two names.
3. **What the exact task limits imply.**
   - Under the declared 5n+2 interventions, three primary cells admit a smaller exact
     state model. The common cause is structural: the observed coordinate lies in a set
     of coordinates closed under upstream dependence (self-loop or feed-forward chain).
   - In the other nine primary cells, every state is task-relevant.
   - The earlier fixed-width, multi-width and nested family misses the one non-contiguous
     optimum (M4/T1, coordinates {0, 1, 8, 9}).
   - None of this is an archive-length result, and it does not authorise scaling, noise
     models, new tasks, a general theory claim or a successor phase.
