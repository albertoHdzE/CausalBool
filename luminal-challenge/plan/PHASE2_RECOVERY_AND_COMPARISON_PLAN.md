# Phase 2 recovery and comparison — lead execution contract

Version 1.0 · 2026-09-23 · Owner/reviewer: Codex · Implementer: Luna.
Status: READY_FOR_IMPLEMENTATION under the frozen amendment below.
User objective: diagnose Phase 2, correct defects, complete its scientifically
authorized experiments, and compare with the original direct and classical
compilers. Manuscript work is explicitly out of scope.

## 1. Authority and what completion means

This contract is a scoped amendment to scientific plan 2.1 and the locked
`plan/phase2/` package. It overrides only public coverage acquisition and the
additional classical control described here. All other definitions, corpora,
codec semantics, search algorithms, model gates, budgets, seeds, statistics,
protected baselines and evidence requirements remain in force. The original
package and all historical evidence stay byte-for-byte unchanged. A negative
effect or a model triage miss is a valid result, not permission to tune until
positive. Correct implementation and favorable hypotheses are different outcomes.

The accompanying `phase2_recovery/AMENDMENT.json` is machine-readable policy.
Its `LOCK.json` pins it and this document before implementation. Every amended
run records and verifies those hashes plus the original package locks. Luna
must not rewrite these lead-owned inputs. The lead reviews unexpected scientific
choices; routine implementation and local execution are already authorized.

Required end product: a reproducible result matrix stating whether Phase 2's
fixed structural_bound arm produces better/equal/worse output and costs more/less
compile time than (a) accepted original direct, (b) original direct bootstrap,
and (c) classical, separately for public and held-out programs. Also report H3
and any legitimately authorized H4 outcome. No superiority guarantee is made.

"Original direct" means the accepted v4 repair2 production source pinned by
BASELINE_LOCK.json, not the older v3 optimization baseline. This amendment is
specified after observing the earlier public sampling failure. It is a recovery
protocol, not a claim of prospective registration before those observations.

## 2. Ownership and immutable starting point

Luna owns edits to `research/`, `research_tests/`, and new result directories
under `results/phase2_structural_encoding/recovery_*`. New helper modules may be
added there with explicit single-owner responsibilities. Lead owns this plan,
`plan/phase2_recovery/`, STATUS.md and acceptance decisions. Do not edit paper,
production, reference, frozen tests, historical runs or unrelated repository
files. You are not alone: preserve concurrent and pre-existing edits. No agents,
external services, commits, pushes, merges, branch changes or publication.

At startup, exclusively create `recovery_diagnosis_20260923` (refuse collision),
record HEAD, status, full working diff and SHA256 manifest, and copy the entire
current research/research_tests Python source into its `starting_source/`.
Capture original package/protected hashes. Starting accepted evidence is
`phase2_repair_20260923c`: P0 PASS; P1 INCONCLUSIVE; P2–P5 blocked; 243 tests.
Re-read AGENTS.md, INDEX_ONLY_PLAN.md, scientific plan 2.1, original contract,
PROTOCOL.json, latest LEAD_ACCEPTANCE.md and research README.

## 3. D0 — explain the failure before changing algorithms

Stream the historical raw rows; do not load or print the 113 MB file wholesale.
Write DIAGNOSIS.json and DIAGNOSIS.md with:

- Per program/stream: attempts, outcome partition, complete and distinct counts,
  case counts, terminal reason counts, first failing field/depth distributions,
  completed scheduling versus allocation paths, and cap/elapsed information.
- Fixed-width rejection explanation: declared field widths versus prefix legal
  option counts. Compute illustrative acceptance fractions as local diagnostics;
  never multiply them into an unjustified global independent probability.
- For at least the first failed option-path attempt of each deficient program,
  replay the prefix and identify the concrete conflicting precedence, capacity,
  lifetime, alignment or address constraint. Keep a minimal deterministic trace.
- Encode/decode the unchanged direct bootstrap on all eight public domains and
  all four codecs. Independently validate every reconstructed compilation and
  every public case. Incumbent failure is a defect, not a sampling problem.
- Distinguish implementation defects, expected invalid binary ranks, genuine
  locally legal dead ends and budget exhaustion. A conclusion needs a trace or
  regression, not a guess based on low yield.
- Audit downstream execution for unimplemented branches or report-only claims,
  especially P2 representation metrics, P3 triage, P4 paid observations,
  conditional P5 model routing and timing attribution. List concrete gaps.

Repair demonstrated implementation defects with failing regressions first.
Do not alter the mathematical codec or search policy to repair sampling yield.
Run the old protocol without the new amendment when testing compatibility:
historical failure must not become PASS by metadata relabeling.
If source-strict historical checking needs the pre-change implementation, use
the preserved source snapshot; never weaken source checks to admit source drift.

## 4. D1 — explicit supplemental codec-coverage diagnostic

Rationale: unconditioned random codes/prefixes may have negligible yield even
when many feasible objects exist. Test the codec on independently constructed
physical objects as well as random decodes. This does NOT repair random-stream
yield, demonstrate uniform sampling, or improve the optimizer by itself.

Keep both original 10,000-attempt/60-second streams, seeds and raw records
unchanged in each fresh amended P1 run. Add `physical_coordinate_probes`, which
does not import candidate option filtering, DFS or model code:

1. Use the same whole-program domain and immutable accepted direct bootstrap;
   no classical seed, new target, compressed domain or shifted horizon.
2. Enumerate fields in fixed layout order: all operation times by ID, then all
   result addresses by producer ID. For each field form its ascending declared
   physical values excluding the incumbent value. Iterate alternative ordinal
   first, then field order, skipping fields with fewer alternatives. Each
   proposal changes exactly that one field of the ORIGINAL incumbent, never
   the previously accepted proposal. Do not count the unchanged incumbent.
3. Assemble the physical candidate with the existing immutable assembly owner.
   Call pinned machine.check_compilation. A rejected physical proposal is an
   expected INVALID_PHYSICAL row, retaining its reason; it is not a decoder
   defect. If valid, run all cases before admitting the object for codec checks.
   Case failure of a structurally valid candidate is a discrepancy and fails P1.
4. For each independently valid physical object, encode/decode all four codecs
   in the original domain. Require exact normalized identity, equal C/S/J,
   COMPLETE, canonical re-encoding and pinned validation/cases. Any mismatch,
   encode rejection or validator failure is a retained correctness defect.
5. Stop at finite neighborhood exhaustion, 10,000 attempted physical proposals
   or one 60-second deadline per program, whichever comes first. Include
   construction, validation, round trips and evidence accounting in that budget.
   Do not stop when coverage reaches 100, silently retry or refund preprocessing.
   Record actual overshoot and interrupted attempts. Exceeding a cap is not
   exhaustion. No recursive/two-field fallback or per-program policy tuning.
6. Record every attempted field/value, candidate identity or reconstructible
   delta, machine verdict, validation counts, four codec results, status and
   timing. Independently replay the deterministic prefix in the checker; derive
   candidate proposals from the frozen incumbent/domain, not report-provided
   identities. Recompute all validations and round-trip outcomes.

Keep supplemental attempts in `p1/physical_coordinate_probes.jsonl` and their
summary in `p1/physical_coordinate_summary.json`. Preserve the original two-stream
artifact schemas and 16-stream denominator. P1 summary must expose separate
`original_random_coverage` and `amended_union_coverage` records. Counter partitions
must reconcile attempted physical proposals with INVALID_PHYSICAL,
VALIDATED_COMPLETE, INTERRUPTED and DISCREPANCY; expected physical rejection
cannot hide a case or codec defect. Use the original physical candidate identity
for cross-stream deduplication, not the index of a particular codec.

The amended P1 adequacy gate uses the union of distinct fully validated objects
from the old streams and this supplemental diagnostic: >=100 per public program,
with the original tiny-domain obligations and zero discrepancies. Retain and
report the ORIGINAL two-stream coverage verdict separately, even when the amended
gate passes. Supplement incompleteness is explicit: coverage attained before a
valid cap can satisfy this adequacy gate, but is never reported as exhaustion.
Historical runs cannot import this new evidence or change their own verdict.

Report unique issue-time vectors, unique address maps, per-field changes and
C/S/J ranges for each stream and the union. Many address variants around one
schedule are local codec coverage, not diverse schedule coverage or evidence of
efficient feasible-set sampling. This gate authorizes empirical comparisons; it
does not prove H1 universally. If it still fails, preserve results and return
the concrete remaining obstacle to the lead; do not lower the threshold.

Implement amendment selection explicitly as `--amendment
plan/phase2_recovery/AMENDMENT.json` on runner and checker. No argument means the
original semantics. Worker specs and imported dependencies must carry the same
amendment identity/hashes. Reject absent/unknown/mismatched policy, forged PASS,
legacy evidence relabeled as amended, and cross-protocol dependency imports.

## 5. D2 — complete the implementation under its existing promises

Do not merely unlock stubs. Complete any missing output promised by the old
contract: four-codec representation rows, fixed widths, exact feasible/code
counts only where established, duplicates, option counts, measured decode/query
costs, tiny search/oracle agreement and bound admissibility. For unknown public
cardinalities use null with reason; never extrapolate the observed sample count.

Keep structural_dfs, structural_bound and structural_expanded algorithms fixed;
only defect repairs are authorized. Model observations must not smuggle oracle
labels, invalid candidates or free validation into training. Keep construction,
search, model building and validation within the original shared deadline.
No promising public outcome may determine a new heuristic or held-out selection.

Add one unbudgeted control arm, `classical`, to amended P2 and P5, measured once
per program/repetition, with budget_seconds=null and search_seed=null. Its only
compiler owner is unchanged `common.classical_compile`, the same classical
baseline as compare_direct.py. Invoke it inside its measurement subprocess only;
it must never seed or enter the candidate/oracle dependency graph. Measure the
actual compiler call and validation separately. Do not charge direct derivation
or direct bootstrap to classical, and do not attribute them zero cost to direct.
Retain actual import/process/RSS costs and immutable source hashes. Use the same
15 fresh-process repetitions and balanced order as the other unbudgeted controls.
Do not duplicate classical observations across optimization budget cells.

Old protocol membership is unchanged. Amended P2 expects 8*15*(3+3*4)=1,800
measurement rows; non-model P5 expects 108*15*(3+3*4)=24,300. Conditional model
adds 108*15*3=4,860 rows only if H4 authorizes it. Tiny fixture checks are separate.
Raw rows, expected identities, worker commands and checker membership must agree.

## 6. D3 — frozen execution, without favorable-outcome selection

Run every research test plus new targeted regression/mutation tests. Run package
verification. Then freeze the final research source hashes before the campaign.
Perform no competing benchmarks or source edits during measurements. Timings may
take hours; do not reduce repetitions or substitute a smoke test. Record progress
and preserve partial rows durably. Repairs after a measured failure require a new
run directory and full affected-stage evidence; failed runs remain retained.

From `luminal-challenge`, with the repository environment's Python and
`PYTHONPATH=.reference:.`, use:

```
python -m research.run_structural_experiments --stage all \
  --run-id recovery_campaign_20260923 --contract plan/phase2 \
  --amendment plan/phase2_recovery/AMENDMENT.json
python -m research.check_structural_evidence \
  --run results/phase2_structural_encoding/recovery_campaign_20260923 \
  --contract plan/phase2 --amendment plan/phase2_recovery/AMENDMENT.json
```

Use fresh suffixes `_r2`, `_r3` only for documented repairs, not best-run selection.
Prefer one self-contained all-stage campaign to dependency chains. P0/P1 lead
to P2/P3; a negative H2 does not block P3 or non-model P5. P3's frozen triage
still gates P4. Failed H3/H4 must leave the model arm absent with an honest reason;
non-model P5 proceeds if its independent gates pass. Use all eight public and
100 held-out programs, original three budgets, fifteen repetitions and original
seeds. Revalidate held-out collision rules and prohibit tuning on their outcomes.

Run unchanged export_direct.py, verify_direct.py --stage all --output NEW_PATH,
and compare_direct.py --repeats 3 --timeout 20 --output NEW_PATH, saving logs and
exit codes to new recovery artifacts. Do not overwrite accepted measurements.

## 7. D4 — answer the comparisons with the right denominators

Primary H2 remains structural_bound versus accepted_budgeted at 0.1 seconds,
using the original family-stratified paired-log-quality interval (95%, 10,000
resamples, original seed). Do not select the best structural arm or budget after
seeing results. Also report structural_bound at all three budgets against
accepted_default, accepted_bootstrap and classical; these are explicitly
secondary/descriptive contrasts, not additional confirmatory tests.

For secondary contrasts, match each budgeted row to the unbudgeted control by
program/repetition; reuse is analytical pairing, not extra baseline observations.
Aggregate technical repeats within program; use per-program medians for runtime.
Retain program/family denominators. Show descriptive 95% intervals with the
original resampling rules and label multiplicity/unadjusted status. Public
results are descriptive; public and held-out programs are never pooled.

Report C, S, J=C*S, wins/ties/losses, quality effect, compile/process time, peak
RSS, failures/timeouts and budget overshoot. The official composite score is
separate from J and runtime: if reported for Phase 2, recompute it with the
unchanged official formula and pinned serial control, and label it supplemental.
The unchanged official comparator alone does NOT benchmark Phase 2.

`COMPARISON.md` must contain a table with one row per corpus/budget/control:
candidate, control, n programs, quality estimate/interval, wins/ties/losses,
runtime ratio/interval, correctness/failures and interpretation. Never collapse
quality and runtime into a single unsupported 'better'. If quality improves but
runtime worsens, state the tradeoff. Null-crossing intervals are inconclusive,
not equivalence. Expanded domains are not matched-encoding attribution.

## 8. Checker regressions and handoff acceptance

Add meaningful tests for: omitted/duplicated physical probes; changed field/value
order; forged complete identity; machine-invalid proposal relabeled valid;
valid physical proposal rejected by codec; case/roundtrip count erasure; count
100 achieved only by duplicates; original coverage failure relabeled PASS;
wrong/missing amendment; imported policy mismatch; absent classical program or
repetition; classical rows repeated under three budgets; unrecorded worker crash;
forged statistic or selected best budget. Recompute outcomes from raw records.
Reuse existing independent oracle and accounting owners rather than cloning them.

Write final HANDOFF.md, DIAGNOSIS.md, COMPARISON.md, source/input manifests,
command/exit logs, complete checker output and machine-readable comparisons.
Name all unresolved limitations and each H1–H4 disposition. Tests passing alone
is not task completion. Report actual measured advantages, disadvantages or nulls.
Status is READY_FOR_LEAD_REVIEW, never self-ACCEPTED.

Lead review will inspect counterexamples and fixes, replay amended coverage,
check both historical and amended protocol behavior, recompute comparison
statistics, validate exact row membership and confirm original baselines.
No paper update precedes this review. Large evidence remains local and uncapped;
do not commit oversized files or treat storage work as a substitute for experiments.
