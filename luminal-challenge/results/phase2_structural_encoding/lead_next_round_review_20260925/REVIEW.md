# Independent review: next_round_20260925

2026-09-25 · Codex · **CHANGES_REQUIRED for release assurance.**
The original R1 candidate-interruption defect is **CLOSED**. The main numerical
results are independently supported. The practical enhancement targets remain
**TARGET_NOT_REACHED**. No production promotion or manuscript update is accepted.

## Verification actually performed

- Assignment verifier: PASS, four package files and 83 protected inputs.
- All **51 new tests**: PASS, 197.897 seconds, exit 0, no skips. The inherited
  frozen suite was not rerun in this review; Claude's complete 443-test log is
  retained separately and is not presented as a fresh lead run.
- Original lead probe against successor: internal count 1, returned count 1,
  accepted improvements 0; all nine queries UNKNOWN_DEADLINE. R1 is closed.
- Fresh isolated CLI acceptance of the exact retained candidate export:
  **142 programs / 277 cases PASS**, input files unchanged, each process under
  the external 20-second timeout. Only compiler.py, pinned machine.py and input
  JSONs were placed in the temporary workspace. Concurrent tests mean this was
  a correctness check, not a new performance measurement.
- Fresh checker: exit 1, exactly 420 ORACLE_LEAK plus one FROZEN_SOURCE_CHANGED.
- Fresh independent numerical auditor: exit 0, 52,013 checks, zero findings.
  The new mutation probe below shows that this PASS has incomplete coverage.
- Separate standard-library recount of 11,000 confirmation rows, public scores
  and all 30 learning fixtures reproduces the reported point estimates. Training
  draws, code/J pairing, common-pool membership and useful novel prefix objects
  were checked against the fixture oracles, not trusted from row yield fields.

Outputs are retained beside this review. `probes.py` reproduces the two findings
without editing measured source or historical artifacts. Its exit 0 means the
diagnostic completed, not release acceptance.

## Supported conclusions

| Candidate / control at .1 s | Geometric J ratio | Compile-time ratio | W/T/L |
|---|---:|---:|---:|
| Repaired A4 / earlier optimizer | 0.969239 | 0.977588 | 55 / 123 / 22 |
| A4 catalog + DFS / earlier optimizer | 0.958592 | 0.916223 | 70 / 116 / 14 |
| A4 catalog + DFS / repaired A4 heap | 0.989015 | 0.937228 | 29 / 161 / 10 |

The declared primary A4-versus-earlier interval supports average quality improvement
on the 200-program generator cohort. The frozen DFS candidate has smaller gains
over heap A4 and misses both prespecified practical routes. Do not turn a missed
2%/20% target into a claim of no measured improvement, or silently lower the target.

Fixed public score, all five repetitions: DFS **2.187956501380014**, earlier
optimizer **2.102746654351309**, heap A4 **2.088945490290080**. Public inputs were
development-visible; no private-grader or cross-generator inference follows.

The development factorial supports the larger catalog in this tested controller.
Traversal and interaction intervals span zero; the handoff's shorthand "the
catalog" must not be read as excluding every traversal contribution. The selected
DFS candidate is the next engineering baseline, not a newly integrated compiler.

## F1 — incomplete construction interruption accounting

`research/next_round_search.py:1830–1862` returns terminal initialization outcomes
before setting `construction_interrupted`. The flag is set later only when a
nonterminal initialization reaches the search-loop deadline check.

The deterministic probe computes a real NO_STRICT_IMPROVEMENT cap on program
800000 while advancing the controlled clock from 0 to 1 second against a 0.1 s
allowance. The query reports active_seconds=1.0, nodes=0, and
construction_interrupted=false; aggregate construction count is zero despite
0.9 s overshoot. The mathematical cap conclusion itself is not falsified and no
invalid incumbent is accepted. The advertised construction accounting is incomplete.

Repair all initialization exits in a successor, retaining both the derived proof
reason and whether it was obtained after the allotted deadline. A post-deadline
terminal proof must not be presented as an in-budget query result. Test caps,
root-conflict/root-prune, Infeasible/DomainError, query/global expiry and normal
returns. Scope the primary count to a precisely defined event, not just one path.

## F2 — numerical auditor accepts a fabricated learning PASS

`research/next_round_audit.py:443–452` compares each learning point and lower CI
bound, but not upper bounds, per-contrast pass flags or the joint mechanism verdict.
The same release describes `not_audited=[]` as "nothing left unaudited".

The lead substitutes only the loaded learning report in memory: sets the joint
mechanism verdict and all component flags to PASS and each learning upper bound
to 999. The unchanged auditor still returns **PASS, 52,013 checks, zero findings,
not_audited=[]**. The unaltered report correctly says FAIL_OR_INCONCLUSIVE; there
is no evidence Claude fabricated its results. This is an assurance defect.

Require independent recomputation of both interval endpoints, every declared gate
and decision label, denominator/family membership, and economics status. Check
the other promised report endpoints too; do not claim complete coverage for fields
never checked. Add mutations for each omitted class and require a failing exit.

## Disposition of disclosed findings

**Post-freeze source change:** the diff in next_round_analysis.py skips None values
in per_program_median. It explains the crash on descriptive control-only fields.
The primary and candidate endpoints use complete values and reproduce independently.
Accept this as a narrowly documented report deviation for those supported estimates;
keep the frozen-source finding and old hash visible. No inference that a worker
may generally edit analysis after seeing outcomes, and no blanket waiver for new drift.

**ORACLE_LEAK ×420:** the ranker imports structural_oracle transitively through
existing owners; this flags capability, not demonstrated access to hidden labels.
The actual ranking function accepts only training codes/J and an unlabeled pool.
The retained file-open audit found only ranker input data reads and reproduced all
ordering hashes. The lead recount independently confirms the negative ranking result.
Treat it as a dependency-isolation defect, not established oracle-data leakage.
The next release needs an oracle-free ranker dependency boundary and a guarded
deterministic replay of all 420 orders, with unchanged digests and no retuning.

## The learning wall is structural, not just expensive training

The tree loses to Hamming on **30/30 fixtures**, mean novel elite-yield difference
−0.1072917. It beats random by 0.0611458 and shuffled labels by 0.0447917, below
the predeclared 0.05 point-gain threshold for the latter. No learning gate passes.

More fundamentally, the controller cannot supply the requested training batch:

1. The product bound prunes nodes with lower bound >= incumbent J
   (`next_round_search.py:553`). At a fully fixed, valid leaf, the bound is exact
   C×S; therefore a surviving valid leaf strictly improves the incumbent.
2. The acceptor observes that leaf, validates it and raises _Improved with
   stop_on_improvement=True (`:895`, `:942`, `:1754`).
3. The controller retains that improvement and discards the epoch's query learners
   (`:1990` onward). If the half-time boundary interrupts acceptance, at most that
   one valid observation is available at first model preparation instead.

Under sound bounds and validator agreement, this path cannot accumulate 20 valid
observations before its first model preparation. Faster propagation alone cannot
fix this incompatibility. The observed 0/100 is consistent with that invariant;
the acquisition run also overlapped fixture generation, so it is not clean
evidence isolating training runtime. Close this per-query learner architecture.
This says nothing about every possible learning architecture. Reopening learning
would require a different data-collection/domain-transfer design, justified first
without another expensive campaign.

## Next phase

Close F1/F2 and the dependency/report provenance issues first. Preserve all frozen
results. Then profile the DFS baseline below the broad "propagation" category and
attempt at most one semantics-preserving improvement. The failed worklist variant
already showed that a high profile share does not guarantee a large saving.
Measure equal-work execution cost as well as output quality at equal time: a solver
that always spends its 0.1 s allowance may use a faster implementation to search
more rather than finish earlier. No new learner, public-score tuning or broad grid.

The separate next-phase plan and locked Claude prompt specify ownership, closure
criteria, fresh seeds, denominators and stop rules. Worker completion still requires
lead review; neither this document nor preparation of a prompt launches Claude.
