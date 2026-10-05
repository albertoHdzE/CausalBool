# Codex review — causal state grouping

2026-10-05. **V/D/X SCIENTIFIC EVIDENCE ACCEPTED. IMPLEMENTATION ROBUSTNESS CHANGES REQUESTED.**
Track G remains DEFERRED_DEPENDENCY (U2/U3). Acceptance does not mean the four-track programme or a general causal deconvolution method is complete. The original handoff and all frozen files remain untouched.

## Terminology

Use **causal state grouping** in new user-facing material. A grouping puts micro states into classes that can support a well-defined reduced dynamics under the declared interventions. Use **state compaction** for reducing the number of distinguishable states, and **multilevel state grouping** when composing grouping maps. Neither term asserts shorter archives, discovered grammar, fractal structure, or causal identification from observational data. “Causal” here refers to compatibility with the declared intervention model.

Do not rename frozen paths, identifiers, APIs or test files. The historical literature term “abstraction” can be retained when citing it or explaining correspondence to earlier documents. New prose should use the requested terminology.

## Accepted evidence and interpretation

The 26 freeze hashes, 34 manifested outputs, seven presentation hashes and handoff hash match. Independent rerun of the frozen audit, with its sole output redirected into this supervision directory, passes 18/18. The supervisor additionally checks candidate descriptions against the frozen declarations for all 2,730 rows and independently recomputes all induced maps for the 13 FULL non-F3 rows using the audit oracle. All agree. This supplements the executor audit, which excludes `candidate` from its selected-row comparison.

All 110,066 paths in the after-preservation snapshot match current hashes. Comparing before/after records shows only the permitted core edit and new test. The 43 non-bytecode run files remain byte-identical through this review. Current tests: 63 passed (36 existing, 27 new). Evidence is in audit_review.json, oracle_rerun.json, initial_checks.json and tests.log. Repository-wide success is not claimed: the documented historical single-engine failure and omitted make ci-local remain disclosed.

V has the declared 30,976 pairs and 2,080 failures; D has all 2,730 rows and 59,312,640 pairs; X has 630 agreements. There are 98 FULL non-control rows, including repeated partitions/time scales. The 11 constant-dynamics rows retain FULL: no prospective rule excluded them. The EGFR non-F3 grouping at tau 8 and 16 is one map with dynamics carried by retained v000, not evidence about biological causation. Fine intervention labels are singleton classes and supply no held-out intervention prediction.

The descriptions of constant versus nonconstant reduced dynamics are useful **post-hoc descriptive characterizations**, not a prespecified success endpoint. render_nonf3.py recomputes induced maps from the frozen owners; it is supplemental computation, not merely formatting saved fields. This review independently verifies its numerical maps. It does not change any measured row or justify relabelling the run. Future usefulness criteria must be separate from exact validity, declared in advance, and tied to a target; nonconstancy alone would not establish usefulness.

## R1 — incomplete coarse evidence can conceal failures

In frozen study.py::evaluate_classes:

- `classes=[[0]]`, no records: representative is MISSING, but output is COARSE-NO-HOLDOUT and the missing count is zero.
- `classes=[[0,1]]`, representative absent, member present with no induced map: member own_e3 is FAIL, but output is COARSE-INCOMPLETE. The known structural failure must outrank missing comparison evidence.

Both are reproduced in robustness_probes.json. These violate the missingness/failure precedence contract. All delivered D records are complete, so neither changes the accepted results. Repair in a separately identified patch, with record availability and member existence tracked independently of comparison evaluability. Keep missing-representative comparisons missing, with null mismatch counts and no replacement representative.

## R2 — malformed supplied-map inputs silently pass

The new core function commutation_failures uses zip without the length/nonempty validation already present in induced_map. Inputs alpha=[0,1], image=[0], identity macro map return [] (no failures); empty inputs also return []. An incomplete domain must not silently pass this API. Require nonempty equal-length sequences and raise ValueError for either length mismatch direction or emptiness. This is a robustness defect, not evidence that any supplied control in this run was incomplete.

## Nonblocking notes

The report's median code still chooses the upper middle item for even samples. For this run, independently computed conventional medians agree in every model because the relevant central values coincide. No numeric erratum is needed. Do not reuse this shortcut for future reports; prefer statistics.median.

The time ledger's last note mentions a reporting overrun although its measured 219 seconds is below 300. Its intervals and total 1,089 are arithmetically consistent; the handoff explains a replaced interim estimate. Clarify only in new closure prose, not by editing the frozen ledger.

## Next action and accounting

Send NEXT_CLAUDE.md for a bounded correction in copies, replacement patches and focused regression evidence. No V/D/X production rerun, no G work, no new model or research phase, and no retroactive changes to FULL. The old run is accepted as complete evidence; adoption of repaired source waits for review of those patches.

Supervisor review started 17:06:39 UTC. Charge 300 seconds conservatively, within the reserved cap. Executor 1,089 + supervisor 300 = 1,389 of the combined 2,460-second allowance. No historical ledger was edited. Only this supervision directory was written.
