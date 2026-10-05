# Causal state grouping: gap-ranking-v1-r1

Status: executable delegation packet, activated when the user sends NEXT_CLAUDE.md to Claude Code. This authorizes the bounded work below, including an isolated dependency extension. It does not authorize modifying the active sibling repository or starting another study. No implementation or scientific execution has been performed in preparing this packet.

## 1. Question and scope

Does the already declared recurrence-gap ordering place FULL causal state groupings earlier than canonical candidate order and the exact expectation for random ordering, on the accepted finite reference population?

This completes deferred Track G from corrected DESIGN.md §4. It is an exploratory scheduling benchmark on already inspected models and labels, not fresh confirmation or a discovery of new causal groupings. The heuristic, widths, trajectories, time scales, population, ties and endpoint were declared before its execution. Labels are now known to the researchers; process separation prevents mechanical leakage but cannot make this a blinded study.

Use causal state grouping and state compaction in new prose. A successful rank result would support a search heuristic. It would not establish shorter archives, useful macro dynamics, a discovered grammar, nested causal mechanisms, fractal dynamics, biological interpretation or a finished general causal deconvolution method.

## 2. Authority and inputs

Read adjacent OWNERSHIP_AND_IMPORTS.md and manifest.json. Read the accepted design's corrected DESIGN.md §4 and MODEL_AND_MAPS.md, the binding design supervision addendum, the V/D/X REPORT.md, and the latest closure acceptance REVIEW.md and adoption.json (exact paths are in the input manifest).

The latest correction is accepted. Use the active deconvolution.py owner at the adopted identity and the separately identified abstraction-validation-v1-r1-source-r2/study.py. Never use the old freeze as a declaration that the newly corrected active core still has its historical hash. Historical frozen source snapshots are explicitly recorded in adoption.json.

Reference labels come only from the original results_d.jsonl, whose exact 2,730-row set, model/candidate/tau identities, complete coverage and hashes must be verified. Do not rerun V, D or X, nor reconstruct every induced map. The original FULL labels, including the 11 constant-dynamics rows, stay unchanged.

Output: index-deconvolution/results/causal_grouping_gap_v1/gap-ranking-v1-r1/. Stop on a pre-existing output directory; do not overwrite it or silently choose a new run ID. New test fixtures and implementation belong inside this output tree or an isolated working copy. Do not modify active core, historical result trees, notebooks (especially 19 and build_19), bitacoras, governance, README files, or others' work.

## 3. Close the two dependencies within this phase

U2: implement token_occurrence_frames in an isolated copy of the existing seqdecon/operators.py owner, with dedicated tests and an unapplied patch against the exact sibling bytes. Contract and registry/version details are in OWNERSHIP_AND_IMPORTS.md. Do not create a local competing production occurrence extractor or gaps implementation.

U3: import that isolated seqdecon package through the explicit, recorded source path. Record resolved __file__ and SHA-256 for every imported repository module; assert the routes match the manifest before production. No package installation, .pth edits or active sibling changes. Deliver the dependency source snapshot and upstream patch, so the run can be reproduced without the temporary directory.

These tickets are approved for isolated development and this run upon activation of the packet. Upstream integration is a later review decision. If the route or required owner cannot be established within budget, hand off BLOCKED_DEPENDENCY; never silently substitute an extractor.

## 4. Fixed computation

Models M1–M4, candidate IDs, partitions and temporal scales come from the accepted source revision. Temporal scales are 1, 2, 4, 8, 16. The six starting states per model are 0, 1, 2^(n-1), 2^n-1, sum(2^i for even i), sum(2^i for odd i). Generate exactly 64 autonomous micro updates and retain x_0 through x_64: 65 states for each of 24 trajectories. Reuse these trajectories across temporal scales. No interventions or new model classes are generated.

Sample states x_0, x_tau, ..., x_(floor(64/tau)*tau). Occurrence indices are sampled-frame indices 0,1,...,floor(64/tau), not positions in a concatenated trajectory.

For each of the nine (w,o) partitions (w in 2,3,4; o in range(w)), retain every head and ragged tail. Token value for block [a,a+l) is (x >> a) & ((1 << l)-1), matching the existing LSB-first declaration. For every trajectory, block, and observed token value, call the owned token_occurrence_frames and then the existing gaps. An occurrence set is eligible iff it has at least three occurrences. It is regular iff all its consecutive gaps are equal. Count each eligible (trajectory,block,value) once. Never concatenate trajectories or average per-trajectory fractions.

Score R = number of regular eligible sets / number of eligible sets, using integer numerator and denominator. Denominator zero means UNAVAILABLE, not zero. Preserve raw occurrence sets and gaps for audit. This gives 180 score records (4 models x 5 temporal scales x 9 partitions).

Per (model,tau), retain all raw candidates except the nine F1 value recodings and identity and constant controls: N=124 for M1–M3, N=130 for M4. Total ranked positions: 2,510. Keep duplicate partitions. F1/F3/F4 inherit the score for their first-level (w,o); F2 is UNAVAILABLE. The nesting operation itself is not scored: explicitly report that this tests first-level scheduling of nested candidates, not the value of nesting.

Rank by available score descending, comparing rational values exactly; ties use ascending original candidate ID. UNAVAILABLE comes last, again in candidate-ID order. Do not break ties by labels, map size, family, dynamic nonconstancy or any new criterion.

Run scoring and ranking in a separate process with no access to results_d, summaries, reports or FULL labels. Hash and seal the 180 score records and all 20 ranked lists before joining outcomes. A read-access guard should reject attempts to read the outcome tree; demonstrate it with a fixture. If imports require an unexpected scientific file, stop and report; do not broaden the allowlist silently. Reading reference identities in a separate preflight process is allowed.

## 5. Endpoint and exact comparisons

Only after sealing ranks, join D labels by exact (model,candidate_id,tau), retaining all 20 cells.

For each cell: N; m=number of FULL candidates; all candidate IDs in each ordering; r_G and r_C, the one-based first FULL rank under gap and canonical ordering. If m=0, both first ranks and random expectation are null with reason NO_FULL_REFERENCE; no zero, infinity or imputed win.

For m>0: exact expected first rank under uniform random permutation of the same N raw candidates is (N+1)/(m+1). Save numerator/denominator. Report delta_random=(N+1)/(m+1)-r_G and delta_canonical=r_C-r_G; positive means fewer candidates inspected. Classify each comparison EARLIER/TIE/LATER using exact arithmetic.

There is no significance test or across-cell population inference. The random reference holds fixed the complete candidate multiset, FULL labels, N and m, and destroys only ordering. It is an ordering baseline, not a causal null. No permutation simulation is needed.

Report a descriptive table of earlier/tie/later cell counts separately for each comparator and all unavailable cells. Do not invent a single GO/HARMFUL verdict or claim wall-time speedup from rank alone. Log the actual cost of trajectory production and scoring separately; no full search-runtime benchmark is authorized.

For each first hit display its original family and candidate description. Flag known constant-dynamics first hits by joining the saved supplemental nonf3_full_maps evidence after ranking, with exact IDs. If that evidence does not cover a row, say NOT_CHARACTERISED; do not infer usefulness from FULL. No new nonconstant endpoint or revised FULL definition.

## 6. Fixtures, failure policy and freeze

Declare hand-computed fixtures before execution. Required checks:
- tokens [2,1,2,2,1,2], value 2 -> frames [0,2,3,5] -> gaps [2,1,2]; constant tokens retain every frame (not only transitions); absent value and empty tokens -> [].
- reject malformed token inputs per the dependency contract; no partial output.
- occurrence [0,2,4] is eligible and regular; [0,2,5] is eligible and irregular; two occurrences are ineligible.
- two separate trajectories that would manufacture a third occurrence if joined remain ineligible; counting-pool and mean-of-fractions differ on a declared fixture.
- preserve nonzero origins and ragged heads/tails; exact frame counts 65,33,17,9,5.
- equal fractions with different denominators tie; available score zero precedes UNAVAILABLE; F2 last; F4 inherits the first-level score; duplicate candidates survive.
- N=5,m=2: enumerate all 120 permutations to verify expected first rank 2; m=0 is unavailable; missing or duplicate outcome IDs fail; missing evidence cannot generate a pass.
- the score/rank process refuses outcome reads and produces the same ranks regardless of shuffled fixture labels given only to the joiner.

Mutate six behaviors independently: substitute flip indices; concatenate trajectories; average trajectory fractions; float/tolerance tie collapse of genuinely unequal rational fixture scores; put unavailable first; deduplicate candidates. Each must fail a relevant assertion rather than merely fail to import. Keep logs, including every failed attempt.

Before production, freeze this protocol, dependency patch and complete isolated dependency sources, all implementation and audit sources, fixtures, declarations, imported source identities and expected inputs. The gap registry change must have a new version/hash before this freeze. Verify the 73 accepted regression tests using the adopted source revision, plus the new focused tests. Do not repair unrelated historical guards or stale tests.

After freeze, no algorithm/fixture/tie-rule change under this run ID. A scientific defect means FAILED_RUN and handoff, not a tuned retry. Presentation-only repairs are separately identified with all attempts preserved; they cannot change scores or measured values.

## 7. Audit and completeness

An independent audit must not import producer score/rank/join functions. It may use original model owners for trajectory validation, but directly verifies occurrence membership, first differences, pooled integer counts, rational ordering, coverage, all joins and all 20 endpoint calculations from saved bytes. Hand-written oracle logic is a run-local audit exception, not a second production owner.

Audit every one of the 180 scores and 2,510 rank positions; all 24 trajectories have 65 states and every transition agrees with the declared owner. Small control expectations should also be checked directly (counter modular increment and a declared rule-150 state), to avoid validating only internal consistency.

Three deliberate artifact corruptions must be caught: alter one occurrence index, swap ranked IDs while preserving the ID set, and change one FULL label in a copied join input. The last must fail its trusted-input hash/identity check. Never mutate original artifacts.

Evidence status is INVALID for an observed scientific inconsistency; otherwise INCOMPLETE if expected records are absent; otherwise VALID_COMPLETE. INVALID outranks missingness. A known unavailable score or a cell with no FULL candidates is a legitimate complete result, not missing evidence.

## 8. Outputs and budget

Deliver PROTOCOL snapshot; fixtures; dependency ticket closure, unapplied upstream patch, original/corrected hashes and isolated dependency snapshot; import manifest; freeze; trajectories; occurrence/gap records; scores; sealed rank lists; joined per-cell JSON and readable table; independent audit and corruption logs; focused tests and mutation logs; REPORT.md, DECISION.md, HANDOFF.md; attempts, wall-clock ledger, before/after preservation and output manifest. One command must reproduce the new outputs in a fresh destination using the delivered source snapshot. Do not overwrite the completed run during this check.

A notebook is optional within the reporting budget: if created, keep builder and notebook inside this new run, load only saved artifacts, and forbid model/checker execution, subprocesses and writes to evidence. No edits to the notebooks index or existing notebooks.

Fresh executor cap: 3,300 wall-clock seconds: dependency closure 600; development/fixtures/tests 1,200; freeze and production 300; independent audit 600; reporting/preservation/handoff 600. Separate Codex reserve: 300 seconds (total envelope 3,600). These are new-phase limits, not transfers from earlier allowances. Include failed attempts and overhead; no category transfers. At 80% stop optional work; at a cap stop and report accurately. No recurring tasks, commits, pushes or publication.

Finish all authorized stages autonomously if their gates pass. Stop at HANDOFF marked ready for Codex review; not yet accepted. Do not launch follow-up tuning or a new model study whatever the result.
