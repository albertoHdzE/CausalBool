# Claims and evidence: the Luminal paper, version 2 (26 September 2026)

This file maps every claim of `main.tex` and `supplementary.tex` to one evidence
file. It holds no numbers of its own. Each claim names ledger keys; the value,
source file and field of every key are in the generated
[claim table](generated/claim_table.md) and in Supplementary Section S10. Both are
written by `generate_figures.py` through `phase2_evidence.Ledger`, and
`verify_ledger` re-derives every pointer and derived entry from disk on every build.

The previous contract, for the 20 September Phase 1 draft, is preserved in
`baselines/20260921/CLAIMS_AND_EVIDENCE.md` and in git history.

## Binding sources

| Source | Status |
|---|---|
| `results/phase2_structural_encoding/lead_resume_review_20260926/REVIEW.md` | Acceptance ruling for C1. **Self-review.** Errata E1–E2 and qualifications Q1–Q3 are binding. |
| `.../third_round_20260925_resume/PAPER_HANDOFF.md` | Evidence classes, claims 1–8 and limits. |
| `.../third_round_20260925_resume/RELEASE_HANDOFF.md` | Contains two known errors (E1: wrong C1 hash; E2: inaccurate D-auditor disclosure). Never cited for either. |
| `lead_{objective,next_round,efficiency,third_round}_review_20260925/REVIEW.md` | Earlier rulings still in force. |
| `results/direct_index_v4_optimization_repair2/REVIEW.md` | Phase 1 acceptance. |

## Evidence classes (kept apart in the text)

| Class | Keys | Evidence file | May support |
|---|---|---|---|
| (a) historical registered M result | `tMReg`, `tMGate` | `third_round_20260925/MECHANISM_DECISION.json` | History only; the model was scope-defective. |
| (b) post-hoc development forecast | `tMCons`, `tMPoint`, `tMFam*`, `tMOldAdapter`, `tMReplayOnly` | `third_round_20260925_resume/RECALIBRATED_PREDICTION.json` | A forecast; neither a measurement nor an interval. |
| (c) kernel-only replay | `tKernelMed`, `tKernelMin`, `tKernelMax` | same file (`kernel_speedup_*`) | Not a compiler speed-up. The median is the corrected value, not the upper median. |
| (d) real compiler, development | `tDev*`, `tMem*` | `third_round_20260925_resume/DEVELOPMENT.json` | Descriptive. |
| (d) real compiler, confirmation | `tCost*`, `tQual*`, `tParity*`, `tWTL*` | `third_round_20260925_resume/COMPARISON.json` | **The only inferential evidence.** |

## Claims

| # | Claim (as worded in the paper) | Keys | Evidence file |
|---|---|---|---|
| 1 | C1 makes the same decisions as R0 at equal work; parity holds on the tested inputs and is not a proof. | `tParityPairs`, `tParityMismatch`, `tSubstantive`, `tZeroNode`, `tTraces`, `tCertMedian` | `COMPARISON.json`; row counts from `stages/C_fixed_work/rows.jsonl` |
| 2 | At fixed work C1's compile call costs `tCost` of R0's (97.5% interval). | `tCost`, `tCostLo`, `tCostHi`, `tGateCost`, `tNodes`, `tResamples`, `tSeed`, `tPctLo`, `tPctHi`, `lvThree` | `COMPARISON.json`; `plan/phase2_third_round/PROTOCOL.json` |
| 3 | At 0.1 s C1's J is not worse within the registered margin. | `tQual`, `tQualLo`, `tQualHi`, `tGateQual`, `tWTLB*`, `tProg*` | `COMPARISON.json`; `lead_resume_review_20260926/RECOMPUTE.json` |
| 4 | Robustness probes: import and process scope, order, drift, per-program spread, search-size thirds, wall-mode time. | `tImport`, `tProcess`, `tOrder*`, `tDrift*`, `tPP*`, `tTer*`, `tSummed`, `tWallTime*`, `tAltSeed*` | `RECOMPUTE.json` |
| 5 | Q1: quality is not monotone in speed; losses at 1 s; program 980183. | `tLossRuns`, `tLossPrograms`, `tLossNoUnknown`, `tLossUnknown*`, `tSeed980183*`, `weQone980183*`, `tQoneSeed` | `stages/C_wall/rows.jsonl`; first answer from `worked_example.py` |
| 6 | Q2: the speed-up is an engineering property of one Python implementation on one machine; no claim of beating classical compile time. | text only; supporting `rOneClTime`, `pOneSlowFull`, `aZeroClTime` | `objective_index_20260924/COMPARISON.json`; Phase 1 `final/runs.json`; `recovery_campaign_20260923_r3/COMPARISON.json` |
| 7 | Q3: memory, development programs only. | `tMemMed`, `tMemMax`, `tMemPrograms` | `DEVELOPMENT.json`; `stages/D_memory/rows.jsonl` |
| 8 | Public scores of every method. | `tabPubSerial`, `weStarterScore`, `rTwoPub*`, `pOneScore`, `aZeroPub`, `rOnePub*`, `tPubSix*` | `next_round_20260925/PUBLIC_SCORE.json`, `objective_index_20260924/PUBLIC_SCORE.json`, `lead_release_review_20260924/PUBLIC_SCORE_RECOUNT.json`, `COMPARISON.json`, `worked_example.py` |
| 9 | Per-program C, S and J on the public programs. | `tabPP*` | `next_round_20260925/PUBLIC_SCORE.json`; `stages/C_public/rows.jsonl` |
| 10 | Every measured pair, each with its own comparator. | `rOne*`, `rTwo*`, `aZero*`, `pOneExtra*`, `lad*` | round 1, round 2 and Phase 2 `COMPARISON.json` files |
| 11 | Compile-time costs; C1 against classical was never measured. | `rOne*Time*`, `rTwoTime`, `rTwoDfs*T`, `aZero*Time`, `pOneSlow*` | as in 10 |
| 12 | Correctness: exports, acceptance corpus, re-validation, audits, tests. | `tAccPrograms`, `tAccCases`, `tExportRows`, `tExportValid`, `tAuditC`, `tAuditD`, `tAuditM`, `tPytest`, `tInherited`, `tRawStdout` | `stages/C_acceptance/rows.jsonl`, `RECOMPUTE.json`, `checks/AUDIT_*.json`, `D_AUDIT_BOTH.json`, `PYTEST.log`, `INHERITED.log` |
| 13 | Negative results: ladder, factorial, reversal, TARGET_NOT_REACHED, worklist, rule-2 filter, learner, H_LEARN. | `lad*`, `fac*`, `rTwoPubCap`, `rTwoPubHeap`, `rTwoQRoute`, `rTwoERoute`, `rTwoWorklist*`, `effPred`, `effCeil`, `lrn*`, `rOneLearn*` | `objective_index_20260924/{COMPARISON,LEARNING}.json`, `next_round_20260925/{COMPARISON,FACTORIAL,ENGINEERING_DECISION,LEARNING_FEASIBILITY,PUBLIC_SCORE}.json`, `efficiency_20260925/MECHANISM_PROPOSAL.json`, `plan/phase2_next_round/PROTOCOL.json` |
| 14 | Worked example (illustrative, one program): every method's C, S, J; queries; catalogue; caps; propagation; shared state; epochs. | `we*` | `generated/worked_example.json`, produced by running the real modules; cross-checked against notebook 04's recorded outputs |
| 15 | Worked-example compile times (frozen, never measured by the build). | `weTime*`, `wePub*` | Phase 1 `comparison/runs.json` and `final/runs.json`; `stages/C_public/rows.jsonl` |
| 16 | Errata E1 and E2; self-review. | `hCOne`, `tAuditD` | `CONFIRMATION_FREEZE.json`, `research/third_round_candidate.py`, `D_AUDIT_BOTH.json` |
| 17 | Phase 1 details. | `pOne*` | `results/direct_index_v4_optimization_repair2/{lead_review,final}/...` |
| 18 | Structural-encoding feasibility (inconclusive). | `fe*` | `phase2_repair_20260923c/p1/summary.json` |
| 19 | Machine definition. | `mWords`, `mVlen`, `mBits`, `mTwoSlot`, `mOneSlot`, `mPublic` | `.reference/machine.py`, `.reference/programs` |

## Forbidden or superseded content (the build rejects it)

- `2.3948` (the retracted upper median); `5ccbaaa3` (E1);
- `0.827` used as a verdict;
- "identical decisions" without "at equal work";
- runtime superiority over classical;
- Shannon or entropy wording;
- any detail of the index-deconvolution construction.

`build_paper.py` checks both manuscripts and the generated tables for all of the
above, rejects any digit in the LaTeX sources that does not come from the ledger,
and verifies that every cited value appears in the PDF text.
