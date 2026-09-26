# Independent lead review — Phase 2 release

Date: 2026-09-24. Reviewer: Codex.
Status: ACCEPTED_WITH_LIMITATIONS — bounded experimental release; H4 remains INCONCLUSIVE.
Run of record: `recovery_campaign_20260923_r3`. `_r2` remains historical replication/checker-repair evidence; its observations are not pooled with `_r3`.

## Independent verification

- Re-ran the immutable delegation/amendment/baseline verification with `--policy-only`: PASS. This permits authorized source repairs without relaxing the scientific policy.
- Re-ran the full evidence checker: zero findings, internally consistent, exit 2 because required P4 remains scientifically INCONCLUSIVE. Its `artifacts_complete=false` is retained; this review does not turn the whole protocol or H4 into a success. Raw evidence supports the completed fixed-candidate comparison.
- Re-ran all 286 research tests: PASS in 140.395 seconds. Logs, command arguments and exit codes are retained here.
- Verified all 18 current research source/test hashes against Claude's final v2 manifest. Its starting/ending tracked diff and HEAD records are identical. This does not imply a clean or committed repository.
- Re-ran the original lead auditor, which imports no research implementation, against raw P5 rows. Exact membership, objective products, correctness/exit fields and all 24 fixed-candidate comparisons passed. Independently compared quality and compile/process estimates and intervals against COMPARISON.json, plus every primary program-level effect: agreement within 1e-9. Output also equals Claude's retained independent audit.
- Counted 1,800 P2 benchmark, 7,020 P4 model and 24,300 P5 measurement rows (33,120 total), plus 32 P2 representation rows. Technical repetitions are not independent programs.
- Inspected the seven repair areas, new regression tests and start-to-v2 source changes. H2 now uses the frozen held-out endpoint; amended P2 uses paired log ratios; P4 non-advancement remains INCONCLUSIVE. Deadline-interrupted probes are independently replayed for recorded evidence and discrepancies, and excluded from distinct-completion coverage. Their original elapsed time cannot be experimentally reconstructed by a later replay.
- Inspected retained production-control validation: verification PASS, no failures, all eight comparator gates pass over 72 rows. Independently verified the current exported compiler SHA256 is `d14bf39b450aaa5fe73c41a3236980e219089e527ae43007781d78e0059a5864`, matching the retained export. Production benchmarks were not rerun during this review; protected inputs are covered by the policy verification.

## Scientific result accepted only within the stated scope

Candidate: fixed `structural_bound`, primary budget 0.1 seconds. Objective J = cycles × scratch, lower is better. The budget is a ceiling, not equal realized search work. Population: 100 generated held-out programs, 20 in each of five frozen families, on one machine.

| Comparison | Mean paired log(J control / J candidate), 95% interval | Candidate wins / ties / losses | Interpretation |
|---|---|---|---|
| Accepted budgeted direct v4, primary | 0.0438923 [0.0251331, 0.0659551] | 26 / 74 / 0 | About 4.3% lower geometric J; interval about 2.5–6.4% reduction |
| Frozen classical, descriptive secondary | 0.0881997 [0.0592311, 0.1193954] | 53 / 35 / 12 | About 8.4% lower geometric J; interval about 5.8–11.3% reduction |

Intervals use the frozen family-stratified bootstrap. Secondary intervals are unadjusted. Classical is an unbudgeted control; the candidate's paired geometric compile-time ratio is 7.2857, so the quality gain has a compile-cost trade-off. Against budgeted direct, that ratio is 0.07258, explained in part by the candidate's query cap and early stopping, not an equal-work speedup. These are not official-score improvements or private-grader results.

Public comparisons remain inconclusive. H3 is supported as protocol-defined structure triage. H4 remains INCONCLUSIVE: only one fixture/family qualifies for the required train/test split, whereas three families are required, and the eligible fixture shows ties. All 7,020 P4 measurements ran; the conditional P5 model arm correctly did not run. This is insufficient evidence for model benefit, not proof that models cannot help.

## Required wording for the manuscript

These qualifications supersede stronger wording in Claude's handoff/readiness documents; those documents remain unchanged as historical evidence.

1. Preserve the original random-stream P1 verdict as **INCONCLUSIVE**: its coverage minimum was not met. The amended local-probe coverage passes. Do not relabel the historical scientific outcome FAIL or imply diverse/uniform feasible-set sampling.
2. Describe codec correctness using the conditional implementation arguments in PROOFS.md, exact set agreement on the 24 exhausted fixture universes, and observed round trips. Finite tests alone do not prove arbitrary-program correctness. Any bijection is between successful canonical codes and the declared feasible domain, not all binary strings.
3. Equal output quality for bound/no-bound arms at the measured budgets establishes no observed quality advantage from the bound there. It does not identify a unique causal source of every gain or show the bound can never help.
4. Replace claims that classical schedules are unreachable by the matched window with: the measured candidate did not attain those outcomes under the frozen domain, policy and limits. A reachability claim needs a domain-exclusion argument or exhaustive evidence.
5. Call H4 measured but inconclusive with inadequate informative-family coverage; distinguish this from its unrun conditional P5 arm. Do not call every model measurement unmeasured.
6. Technical repetitions are averaged within programs. Most objective values were stable, but deadline-sensitive arms had variation; do not claim repetitions measure timing only universally. Report the recovery amendment and checker repairs transparently. The primary was fixed by that amendment; do not imply the entire study was prospectively preregistered before recovery.

## Decision and next task

Accept the bounded Phase 2 experimental release and its fixed-candidate comparisons. No blocking implementation or numerical-integrity finding remains in this review. The manuscript qualifications above are required. This is sufficient for a bounded manuscript revision, not a globally superior compiler or completion of every Phase 2 hypothesis. No algorithm optimization is necessary to report this result honestly.

The next task should update the manuscript, generated tables/figures and claim-to-evidence mapping from the accepted `_r3` raw evidence, preserving the old draft and these qualifications. Optimizing the query cap, domain/window or search cost is a separate study: this cohort becomes development data and a fresh frozen held-out cohort is required for a new confirmatory result. A model-benefit claim additionally requires fixtures capable of satisfying the H4 family/split requirements and a new specified experiment.

No paper, production source, historical campaign or Claude handoff was changed by this review. No commit, push or submission was performed.

## Public-score clarification — 2026-09-24

The earlier statement that public-score superiority was unproven was too broad.
`PUBLIC_SCORE_RECOUNT.json` independently joins the eight public candidate rows
against the frozen serial C/S values and applies the pinned challenge formula.
All 15 repetitions yield Phase 2 score 2.0327602339438613, original direct
2.0084662022846573 and classical 1.9013791212645499. Thus Phase 2 has a measured
1.2095813% higher score than original direct and 6.9097799% higher than classical
on this fixed public suite. These are reconstructed benchmark scores, not an
external submission or a standalone Phase 2 export acceptance. The zero-touching
bootstrap interval concerns population inference across programs; it does not
erase the exact finite-suite arithmetic improvement. A public-suite score claim
must name the fixed suite and must not be generalized to the private grader.
