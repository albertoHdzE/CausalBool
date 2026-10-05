# Claude delegation — finite causal abstraction validation, V/D/X

This packet is ready for the user to send to Claude Code. Upon that delegation, implement and
run the scoped phase below. Do not execute merely because this file exists. No further design-only
cycle is required. Codex has accepted the design with this prospective addendum and the core
ownership ticket. The old draft remains NOT AUTHORIZED FOR EXECUTION as a historical artifact;
this separate delegation governs the new study.

## Read and lock the inputs

Read adjacent REVIEW.md and these files relative to the repository root:

- `index-deconvolution/results/causal_abstraction_design/review_closure/abstraction-design-v1-r1/corrected/{DESIGN,MODEL_AND_MAPS,EVIDENCE_AND_LIMITS,DECISION,DRAFT_EXECUTION_PROTOCOL}.md`
- the closure's `OWNERSHIP_TICKET.md`, `HANDOFF.md` and manifests.
- the accepted causal-target closure's corrected `ABSTRACTION_CONTRACT.md` and `EVALUATION_SPEC.md`.

The corrected execution draft's SHA-256 is
`876c43401eaeee313e110969610782248999784c848b935a52ad9d0ce447cb68`.
Verify it and all manifested closure inputs/outputs before work. Hash this packet and the
review, and preserve those identities in the new run. Resolve copied documents' relative links
against their actual original location; do not silently read similarly named files.

New run: `abstraction-validation-v1-r1` under
`index-deconvolution/results/causal_abstraction_validation/abstraction-validation-v1-r1/`.
Do not overwrite an existing run; report a collision instead.

## Ownership and authorized scope

Extend **only** `index-deconvolution/src/deconvolution.py` for the reusable induced-map checker
and comparison API. Preserve existing APIs and unrelated edits. Add focused tests in the new
`index-deconvolution/tests/test_abstraction.py`; study orchestration, fixture declarations,
reporting tests and an independent audit belong inside the new run directory. No new production
package, simulator, gap implementation or competing core. Reuse the declared Network, ECA,
knockout and bnet owners. Check actual imported `__file__` paths.

You are not alone in this repository. Snapshot status and hashes before editing; never revert
other work. Preserve all previous studies, notebook 19/build_19, other notebooks, hierarchy/,
protocols, governance and bitacora. Record the original bytes and your own patch to the permitted
core file. No commits, pushes, publication, schedules or recurring tasks.

Execute V, D and X only. Write `results_g.json` with status `DEFERRED_DEPENDENCY`, reasons U2/U3,
and zero executed G work. Do not edit or install the sibling series-deconvolution repository.
Do not describe the four-track study as complete: V/D/X completion and G deferral are separate.
No notebook is required for this phase. No new models, candidate maps, time scales or tuning.

## Binding prospective addendum (takes precedence over corrected draft)

1. **Primary status is total, with control as a separate flag.** For each row record E2 and each
   E3 as PASS (complete evidence), FAIL (a valid observed witness), or UNKNOWN (incomplete with
   no witnessed failure). INVALID evidence is an error, not UNKNOWN. Apply this order:
   - E2 FAIL: AUT-FAIL.
   - E2 UNKNOWN and any non-identity q FAIL: NOT-FULL-INCOMPLETE.
   - E2 UNKNOWN with no q FAIL: INCOMPLETE.
   - E2 PASS, some non-identity q PASS and some q FAIL: RESTRICTED; Q-prime is a lower bound
     when any q is UNKNOWN.
   - E2 PASS, every non-identity q FAIL: AUT-ONLY.
   - E2 PASS, at least one q FAIL, no non-identity PASS, and at least one UNKNOWN:
     NOT-FULL-INCOMPLETE.
   - E2 PASS, no q FAIL, at least one UNKNOWN: INCOMPLETE.
   - E2 PASS, every q PASS: FULL.
   Keep `is_control` from complete E1 alongside the status. For complete, valid constant or
   injective rows, display CONTROL in the scientific summary and exclude them from findings.
   A control flag must never hide incomplete or invalid evidence. A valid failure of the
   injective/constant existence theorem is CHECKER-INVALID. Missing E1 cannot be inferred as zero.
   At run level use FAILED-RUN for harness errors, CHECKER-INVALID for failed checked predictions,
   INCOMPLETE for absent required evidence; none permits a scientific pass. Retain observed
   structural failures even when other records are missing. Test all branches, particularly
   unknown E2 plus a failed intervention and a control with missing evidence.

2. **Coarse hypotheses:** H-OUT is a separate additional F3 column: merge q_id and all resets,
   flips and knockouts acting outside the retained block; leave tick and each in-block
   intervention in its beta_fine singleton. F3's primary test remains beta_fine. H-COARSE uses
   the declared lossy-map coordinates; F4 coarse coordinates are level 2, fine labels retain
   level-1 block/local position. These labels need only be injective in the primary scheme;
   do not describe them as independent macro interventions supplied in advance.

3. **Comparison units:** retain both macro-state disagreement count and micro-state pair
   mismatch count (the latter weighted by fibre sizes), explicitly named. Intended/inspected/
   evaluable E4 pair counts use micro states. If the representative has no map, comparisons
   are not evaluable with a reason and null mismatch counts, even when a member's separate
   E3 fails. If a representative is absent, mark comparison missing. No substitute representative.
   Canonicalise partition labels by first appearance while visiting integer micro states in
   ascending order. Use the lexicographically smallest valid micro-state pair as each fibre
   witness, and smallest macro code for a disagreement witness. Independently verify witnesses.

4. **Audit selection:** replace r mod 10 = 0 with
   `r_j = 10*j + (j % 5)`, j = 0,...,272. These are 273 unique rows in [0,2729], with counts
   55,55,55,54,54 across tau = 1,2,4,8,16. Freeze the explicit list before D. This is deterministic
   coverage, not a random sample or a statistical certificate for unaudited rows. Recompute all
   supplied V controls, both calibrations and these D rows independently. The audit oracle
   must not import the production checker or producer/reporting functions; shared model owners
   and frozen declarations may be used and must be disclosed. Compare all scientific fields,
   excluding runtime metadata, plus check exact whole-run row coverage and cross-field arithmetic.
   The single-owner guard explicitly allows this named run-local validation oracle and fixtures;
   it must reject a planted second production implementation. Do not claim grep proves semantic
   uniqueness across arbitrary code.

5. **Pre-freeze tests:** retain all declared fixtures, ragged-block/counting tests, wrong-beta
   witnesses, representative failure and missingness tests. Add the status/audit-list tests above
   and meaningful mutations: merge different local flips; suppress a representative failure;
   treat UNKNOWN as PASS; reverse intervention timing; drop ragged tails; let a control hide
   missingness. Each must fail a relevant test with evidence. Declaration of fixture cases must
   precede their first execution. Fixtures may use the already specified models and witnesses;
   record all such exposure. Do not inspect other D results before freeze.

## Stages and stopping rules

1. Record start, git status, preservation, input hashes and prospective fixtures. Implement the
   owner extension and thin orchestration, then run focused tests and the existing
   `index-deconvolution/tests/test_deconvolution.py` regression suite. Run applicable scoped lint
   and repository guards. Known historical guard failures must be compared to saved evidence,
   not called passes. Do not run make ci-local if it rewrites unrelated dirty artifacts; report
   that omission and actual scoped checks. No unrelated repairs.
2. Freeze this packet, accepted documents, fixture/order/audit lists and every source used in
   scientific computation or verification, including imported owners. Hash the independent audit
   before production. Tests and import-origin checks must pass. Record immutable source identities.
3. Run V, calibrations, theorem checks and X after freeze. X may compute E2 for its declared F3
   cross-check. Deviations from hand predictions stop the run as CHECKER-INVALID; do not revise
   predictions or resume under the same identity. Only then run D, all 2,730 rows, all declared
   intervention/state pairs, without early exit on failing candidates. Expected D workload is
   59,312,640 pairs; do not conflate cached table work with declared pair coverage. Count extra
   validation/audit work separately.
4. Run independent audit, report all rows and raw/deduplicated partitions, preserve every attempt.
   No post-freeze scientific fix or rerun under the same freeze; if necessary stop with evidence
   for review. Presentation-only changes are separately hashed and may not alter measured rows.
5. Snapshot preservation after, write manifests and handoff. Handoff status: ready for Codex
   review; not yet accepted. Stop. Do not autonomously start another phase.

## Budget and deliverables

New allowance: **2,160 executor wall-clock seconds**, including development/tests 900, freeze
60, run 600, audit 300, reporting/handoff 300. Reserve **300 additional seconds for Codex**.
Do not transfer category charges or consume supervisor time. Record conservative continuous
wall-clock intervals including failures. Stop optional work at 80%; reserve handoff time within
reporting. At any cap, stop and write honest INCOMPLETE counts. Runtime is unmeasured; this budget
is not a claim of feasibility. Historical design charges stay in their original ledgers.

Deliver fixtures, freeze/source manifests, core before/after patch, tests/mutations/logs,
results_v.json, results_d.jsonl, results_x.json, deferred results_g.json, independent audit source
and audit.json, REPORT.md, DECISION.md, preservation, attempt/time ledgers and HANDOFF.md.
Report fine existence and coarse hypotheses separately; identify model, tau, map and witnesses
for any claimed lossy non-F3 result. Negative results concern only declared A/Q/beta. No claim
of compression gain, discovered grammar, fractal scaling, biological causation, novelty, or a
completed general causal-deconvolution method. The substantive question is whether these finite
models admit the specified intervention-compatible macro variables.
