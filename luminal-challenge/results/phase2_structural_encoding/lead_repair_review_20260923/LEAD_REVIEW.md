# Phase 2 repair: independent review, 2026-09-23

**CHANGES_REQUIRED.** Reviewed `phase2_repair_20260923b/HANDOFF.md` and the
working-tree source retained in `reviewed_source/` with `source_hashes.json`.
No implementation files were edited by this review. Original runs are intact.

The repair makes substantial progress: public case execution and uncapped raw
sampling are implemented, reference verification uses the actual manifest,
research tests are relocated, the ordinary construction deadline defect is
covered, and the model arm has explicit routing and lazy union traversal.
However, the evidence/gate repairs remain incomplete. The following independent
probes run against copies of the NEW repaired control, not stale old evidence.

## Independent validation

- Frozen package verifier: exit 0; 12 package files, 46 baseline entries,
  12 fixtures, 30 acceptance checks (`package.log`).
- Research unittest discovery: **236 tests PASS**, exit 0 (`tests.log`).
- Repaired worker control checker: exit 2, zero findings, P1 inconclusive
  (`worker_checker.log`). This is the valid control for the mutations below.
- Fresh all-stage campaign: exit 2; P0 PASS, P1 INCONCLUSIVE, P2–P5 blocked
  (`../lead_repair_replay_20260923/`, `replay.log`). Its checker independently
  returns exit 2, zero findings (`replay_checker.log`).
- Export and canonical production verification: exit 0, all 12 stages pass,
  including historical evidence and the 142-program corpus
  (`production_verification/`). L1 is closed without modifying historical files.
- Fresh three-repeat production comparison: exit 0, 72 unique measurements,
  zero failures, all seven gates pass (`production_comparison/`). Direct combined
  score is 2.008466202284657 in each repetition.

P1's scientific disposition is unchanged. Passing local validation does not
establish its missing coverage, and there is no real P2–P5 experiment here.

## F1 [P1]: recomputed failed coverage can still be certified PASS

`research/check_structural_evidence.py:767` records coverage as an inconclusive
observation, but main (`:1774` onward) derives incompleteness from recorded gate
statuses. It never requires P1's gate to equal its recomputed coverage outcome.

Reproduction (`probes.py`, `probes.json`): on a copy of the repaired control,
change only P1 status in gates.json and manifest.stage_status to PASS. Keep the
summary and all raw evidence intact, including coverage_met=false. Checker
returns **exit 0, zero findings, artifacts_complete=true**, while simultaneously
reporting one inconclusive coverage observation. No digest mismatch is involved.

Required: derive each applicable stage gate from checked evidence, reconcile all
recorded statuses, and derive completeness/exit status from those results. A
mandatory coverage failure cannot be overridden by an edited status label.
Reconcile hypothesis/scientific-success labels with evidence as well.

## F2 [P1]: imported PASS metadata still bypasses actual prerequisite evidence

`research/run_structural_experiments.py:1880` (`verify_imported`) now checks
summary hashes, source/contract identity and declared PASS, but does not validate
the evidence or recompute the gate before authorising the stage body.

Reproduction (`probes.py`, `probes.json`): use F1's copy as --inputs for P2. Replace
only the expensive P2 stage body with a stub calling the actual Run.prior('p1').
The stub is entered with **coverage_met=false**, and main returns **exit 0**.
No prohibited real downstream experiment is run by this probe.

Required: validate the imported prerequisite evidence transitively before stage
entry, including actual gate conclusions, required raw artifacts, amendments,
and source/contract identity. Retain the validated dependency provenance in the
new run so its own checker can resolve imported evidence. Do not consider a
hash-consistent summary plus a user-editable PASS label sufficient.

## F3 [P1]: required finite-domain decoder evidence can be replaced by nonsense

`research/check_structural_evidence.py:457–567` requires nonempty raw files and
matching digests, but never parses oracle_domains.jsonl or decoder_rows.jsonl
for their expected membership/content. It independently counts oracle objects,
but trusts the codec exhaustion and set-equality assertions; it does not rerun
all finite-universe decodes and round trips claimed by those assertions.

Reproduction (`raw_probe.py`, `raw_probe.json`): replace all 282 decoder rows by
one JSON object `{}`, update its raw hash, P1 summary hash and manifest row count.
Checker returns **exit 2, zero findings, internally consistent**—exactly the
valid control outcome. The remaining exit 2 is the original sampling shortfall,
not detection of erased finite-domain evidence.

Required: exact raw membership from frozen fixtures/codec universes, independent
round-trip/set recomputation, and full reconciliation with summaries. Test
hash-consistent deletion, replacement, duplication and altered exhaustion flags.
Also validate sampling row seed/codec/attempt membership rather than accepting
any distinct indices and a seed drawn from either stream's seed list.

## F4 [P2]: command/log integrity remains permissive

`research/check_structural_evidence.py:278–314` explicitly accepts exit_code=None.
Its missing_logs list selects existing empty logs, not missing logs, and it does
not resolve log references in command rows. Required command membership is not
derived from execution work.

Focused reproduction (`probes.py`, `probes.json`): run the real check_commands
on an existing valid control after replacing commands.jsonl by a command with
exit_code=None and log='logs/absent.log'. It reports **zero findings**.
This is an isolated method-level probe, not a claim that a whole mutated run's
row counts were reconciled.

Required: distinguish intentionally absent subprocess work from missing required
commands. Require terminal exit codes for completed commands, existing referenced
logs and exact expected command membership for stages that launch workers. Treat
stage-internal execution separately with explicit completion records. Exercise
these through the complete checker as well as focused unit tests.

## Disposition

L1 and R6 are closed. R1's retained public sampling and case execution are
confirmed. R4's original construction/validation regressions pass; R5's original
dispatch/lazy traversal defects have implementations and passing tests. This does
not confer acceptance on every unmeasured conditional branch. R2 and R3 remain
open through F1–F4. Implementation acceptance is withheld; scientific gates and
production acceptance are unchanged.

Raw evidence size is a packaging concern before committing, not permission to
truncate evidence or change scientific gates. Preserve existing runs as-is. No
commit, push or merge was performed. See REPAIR_HANDOFF.md for the next bounded
assignment.
