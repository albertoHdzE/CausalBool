# Phase 2 repair acceptance — 2026-09-23

**Implementation accepted for the isolated research campaign.** Lead reviewer:
Codex. Claude's handoff was incomplete when reviewed; the remaining repairs and
independent acceptance were completed in the working tree. No production source,
frozen plan input, historical test or reference file was changed.

## Defect disposition

- **L1 closed:** phase 2 tests live in `research_tests/`; the unchanged historical
  evidence checker and its provenance pass in the full production verification.
- **R1 closed:** each public sample attempt is retained with stream identity and
  case-validator counts. Fresh run `phase2_repair_20260923c` contains 160,000
  attempt rows across 16 streams, 819 completed draws, 1,356 case executions and
  zero discrepancies. Checker replays the seeded draw sequence and case checks.
- **R2/F1/F3 closed:** stage verdicts and completion are derived from checked
  evidence. Hash-consistent false PASS, erased decoder rows and malformed
  finite-domain memberships are regressions. Exhaustive decoding and round trips
  are recomputed from all 12 locked fixtures and four codecs.
- **R3/F2 closed:** imported dependencies are independently checked before stage
  entry, including transitive evidence. A hash-consistent false PASS is blocked;
  the positive control imports a real P0 PASS. A resumed P1 run is independently
  rechecked and its imported provenance resolves.
- **F4 closed:** worker command records require terminal exit status, a retained
  in-run log and exact task-identity membership against result rows. End-to-end
  tests cover absent exit/log and deleted worker records.
- **R4 closed:** shared absolute deadlines cover construction, search, model work
  and validation; expiry retains the last validated incumbent. Deadline and cap
  regressions pass.
- **R5 closed as implementation only:** conditional model routing, lazy ordered
  proposal expansion and authorized/blocked controlled branches are tested.
  No H4 experiment authorized the arm in this campaign, so it has no measured
  result.
- **R6 closed:** reference manifest `sha256` membership and pinned commit are
  checked, including entries absent from the separate baseline lock.

## Independent verification

- Frozen package validation: exit 0; 12 package, 46 baseline, 12 fixture and 30
  acceptance entries (`lead_repair_review_20260923/package_acceptance.log`).
- Research tests: **243 tests pass**, exit 0; `tests_acceptance.log`.
- Fresh all-stage campaign: exit 2 with P0 PASS, P1 INCONCLUSIVE and P2–P5
  BLOCKED_BY_GATE; `campaign.log`, `campaign.exit`.
- Independent evidence checker: **zero findings**, exit 2 because required
  evidence remains scientifically inconclusive; `checker.json`, `checker.exit`.
- Production export: exit 0; `export_final.log`.
- Full unchanged production verification: exit 0, **12/12 stages pass**, zero
  failures; `production_verification_final/`.
- Production comparison: exit 0, **72/72 rows and all seven gates pass** across
  three repetitions; direct score 2.008466202284657 and classical score
  1.9013791212645499 in each repetition; `production_comparison_final/`.

## Scientific disposition

P1 remains **INCONCLUSIVE** under the frozen minimum of 100 distinct completions
per public program. The observed union counts in pinned order are 0, 234, 194, 55,
135, 16, 168 and 17; four programs miss the minimum. All 16 streams reached their
10,000-draw request, and all 160,000 attempts are retained. P2–P5 were correctly
blocked and remain unmeasured. This does not establish that structural encoding
is impossible; it establishes that this frozen sampler did not meet the declared
coverage gate. Any new sampling policy requires a separate scientific amendment.

The canonical 113 MB attempt file exceeds the repository's 10 MB history limit.
It remains local and uncapped, as the evidence contract requires. Do not stage it
for a commit until a storage representation and reader are agreed and validated.
No commit, push or merge was made. Source snapshot digest for this run:
`fa766d09fc97aa0261b9f822624750a71f421a29e7d78e51d989af7b3c6c5cdc`.
Full source file hashes are in `../lead_repair_review_20260923/final_source_hashes.txt`.
