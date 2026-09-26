# Phase 2 implementation contract — revision 1

Owner and final reviewer: Codex, acting for Alberto Hernández Espinosa.
Implementer: Claude Code. Research plan: 2.1. Protocol: `PROTOCOL.json`.
This is the executable clarification of the scientific plan, not a results report.

## 1. Authority, scope and completion

The author has requested this delegation. Implement and run P0–P5 in dependency
order, subject to the scientific gates. No additional approval is needed for
routine implementation, local tests or the frozen experiments. A missed gate is
a complete and reportable outcome when all independent authorised stages and the
handoff are complete. Do not fabricate positive results to reach a later stage.

Order of authority: user instructions; pinned machine semantics and glossary;
scientific plan 2.1; this contract and its frozen JSON inputs. A contradiction
between these is a blocker to the affected task: retain evidence and hand it to
Codex. It is not permission to choose a more convenient interpretation. Formatting,
local helper names and internal data structures are implementation choices;
algorithms, domains, budgets, seeds, gates and denominators are not.

Read the complete scientific plan, canonical index plan, optimisation plan,
AGENTS.md and STATUS.md. Read the owners of every reused API before coding.
Use graph discovery tools when available; their absence permits source search.
Do not launch additional agents or external services for this assignment.

This assignment implements an isolated research system and its evidence checker.
It does not replace the production compiler, change export wiring, or submit a
solution. The existing production method requirement is evaluated separately
before any integration. A local enumeration research baseline must be named as
such; wrapping individual enumerated points in cubes does not establish a new
symbolic production algorithm.

## 2. Exclusive writable files

You are not alone in this repository. Preserve all pre-existing and concurrent
edits. At startup save `git status`, HEAD and the full diff in the new run root.

Allowed new source files, each with one responsibility:

| File, relative to luminal-challenge | Responsibility |
|---|---|
| `research/__init__.py` | Package marker only |
| `research/structural_encoding.py` | Domain, fixed layouts, options, encode/decode; all codec variants |
| `research/structural_search.py` | DFS, bounds and conditional model proposal policies |
| `research/structural_models.py` | Exact cover merge, serialization, expansion proposals |
| `research/structural_oracle.py` | Independent finite-domain enumeration and hidden evaluation |
| `research/run_structural_experiments.py` | CLI, subprocess harness, corpus freeze, P0–P5 orchestration |
| `research/check_structural_evidence.py` | Independent artifact checks and gate recomputation |
| `research/README.md` | Actual run instructions, ownership and limitations |
| `tests_direct/test_phase2_encoding.py` | Codec/domain/property tests |
| `tests_direct/test_phase2_search.py` | Bounds, budgets and search tests |
| `tests_direct/test_phase2_models.py` | Cover, proposals, serialization and leakage tests |
| `tests_direct/test_phase2_evidence.py` | Harness/checker/ownership mutation tests |

Allowed artifacts: new directories beneath `results/phase2_structural_encoding/`.
Everything else is read-only, including the plan package, STATUS.md, shared test
initialisation, accepted evidence, production source, notebooks and manuscript.
If a listed new file already exists at startup, do not replace it: report the
collision. Do not stash, reset, clean, amend, merge or change branches. Do not
commit or push; return a reviewable working-tree diff. Codex owns acceptance and
subsequent git actions. The plan rewrite already in the working tree is lead-owned.

Existing `.build` exports may be regenerated only by the unchanged
`export_direct.py` for validation; these are derived ignored files. No historical
result directory may be a command's output destination.

## 3. Preflight and frozen inputs

Verify every file in BASELINE_LOCK.json and every reference.json hash. Verify
PACKAGE_LOCK.json before every stage. A documentation-only HEAD change is not
source drift; record both commits. Any content mismatch blocks dependent work.

FIXTURES.json holds twelve complete program/domain/incumbent records generated
from existing test fixtures by the lead. Treat them as data; do not import the
old test module to regenerate or replace them. Check every incumbent with the
pinned validator and cases. Cartesian sizes are counts before legality filtering.
These inputs carry no candidate feasibility, structure or performance results.
Use all twelve in P0–P4. Additional unit fixtures exercise edge conditions but
must never enter the frozen structure denominator.

Before tuning, materialise held-out seeds 800000–800099 inclusive using
`tests_direct.generate_programs.additional_program`. This gives exactly twenty
per existing family and uses a range disjoint from the recorded old evaluation
seed range 200000–399999. Check actual historical manifests for seed collisions
and compare semantic program digests after excluding only `name`; keep operation
IDs, constants, buffers and cases. Also compare against public/regression/old
extra programs. Any collision or invalid generation is a preflight failure;
there is no replacement seed policy. Freeze JSON and hashes without inspecting
candidate outcomes. Test cases are validator inputs, never search inputs.

Use `additional_program(seed)` as the sole generator owner. Do not rewrite its
implementation. The held-out manifest order is family order from FAMILIES,
then increasing seed. All ten search seeds apply to stochastic arms; deterministic
arms execute once per timing repetition and have `search_seed: null`.

## 4. Codec APIs and unambiguous semantics

Expose these public interfaces; annotations may use immutable dataclasses:

    Domain.from_record(record) -> Domain
    layout(domain, codec) -> Layout
    decode(domain, index, codec, budget=None) -> DecodeResult
    encode(domain, compilation, codec) -> int
    options(domain, prefix, decision) -> tuple[int, ...]

Codec names: `absolute`, `static_rank`, `vector_block`, `structural_rank`.
A Domain contains program, selected operation IDs, explicit nonempty sorted
unique integer domains, fixed times/addresses, incumbent, and optional target.
Selected values are exactly the results of selected operations. All operations
and values must be covered exactly once by variable or fixed fields. Reject
booleans, negative/out-of-range values, duplicate domains, missing keys and
malformed incumbents. An empty feasible set is legal; malformed empty option
arrays in an input domain are not. Express contradictory fixtures through fixed
constraints, not a malformed Domain.

Layout is fixed for the entire Domain: all selected time fields in operation-ID
order, then all selected address fields in producer-ID order. Each field owns
its offset independently of traversal order. Allocation traversal is vectors
first, then scalars, ordered by `(write_cycle, producer_id)` after scheduling.
Never pack fields in this schedule-dependent traversal order.

For structural ranks, field width is `(len(declared_domain)-1).bit_length()`.
Static ranks use the same width and rank the declared domain without filtering.
Both order incumbent choice first if present, then remaining choices numerically.
Absolute fields use canonical time width and eight-bit physical addresses, with
explicit domain restrictions. Vector-block differs only in vector addresses:
five-bit block index multiplied by eight; scalars still have eight-bit addresses.
Do not truncate scaled arithmetic. Zero-width rank constants occupy no bits.
Their options are still checked; an empty local list returns DEAD_END.

Validate index type and `0 <= index < 2**B` before decoding (B=0 admits only 0).
At a decision, check empty options first, then rank validity. This resolves the
otherwise overlapping DEAD_END/INVALID_CODE cases. Scheduling options check all
already assigned and external predecessor/successor constraints and capacity;
an external successor can have a larger ID. Also reject fixed-fixed scheduling
contradictions at initialisation of the decoding state, as DEAD_END. At the
scheduling/address boundary, recompute all lifetimes and check fixed-fixed
address overlaps. If selected reads made them conflict, return DEAD_END.

Address options check all fixed and previously assigned blocks with full inclusive
lifetimes. Allocation/scheduling pruning must not look at unassigned choices
except for the proved bounds enabled in the search arm. No oracle lookup or
objective pruning changes the codec's option lists. Codec legality and quality
are separate predicates. A target, when present, is checked as an explicit
Domain predicate; final target failure is DEAD_END, not a validator discrepancy.

DecodeResult status is `COMPLETE`, `INVALID_CODE`, `DEAD_END` or `INTERRUPTED`.
Only COMPLETE carries compilation, C/S/J and canonical index. All results carry
consumed decisions, counters, reason and trace reference. A fully decoded illegal
compilation is a defect: retain it and fail; do not translate it to DEAD_END.
`encode` rejects compilations outside F_d. Exact inverse tests compare structural
ranks only on successful codes; absolute/vector codes still enforce all domains.

Use direct_contract for derivation, lifetimes, assembly and footprint. Import
machine specifications; do not copy constants. Oracle code must assemble its own
simple candidate dictionaries and use machine.check_compilation, machine.check_case
and machine.scratch_footprint. It must not import the codec, search or derived
legality checker. Sharing immutable JSON and schema algebra is allowed; sharing
candidate feasibility predicates is not.

## 5. Fixed search and model policies

Expose `search(domain, incumbent, arm, budget) -> SearchReport`. The reference
research traversal is DFS, decision-order traversal and ascending option ranks.
Use one immutable incumbent for rank ordering within each query. Updating the
best solution must never reinterpret an already constructed index. Strict J
improvements only; equal products retain the earlier incumbent. Validate complete
proposals and every case before accepting. Cache complete compilation identities
only within the run and account for duplicate lookup/work.

Structural-bound uses only these initial admissible bounds:

- L_C = max(facts.cycle_lower_bound(), 1 + maximum assigned/fixed issue time),
  with the maximum omitted if no operation is assigned.
- L_S = max(widest result, maximum assigned/fixed address end).
- After scheduling completes, also include peak simultaneous live width in L_S.

No incumbent-lifetime bound before scheduling completes. Prune when L_C*L_S is
at least the best validated product for strict improvement. Identical local
feasibility checks apply to unpruned and pruned arms. Do not add learned bounds,
new priorities, beam widths, restarts or adaptive window selection.

Matched-window policy reuses `targets_for` and `windows_for` on the same current
incumbent, with the original max_queries=32. Record every domain before solving.
Direct absolute-query controls use unchanged JointQuery/solve. Structural arms
use the identical physical time/address domain and target. A target excluding
the incumbent cannot claim a zero-origin property. Expanded search uses all
operations, times 0..facts.horizon-1, and every aligned physical base; this arm
is never labelled a matched encoding comparison.

Use the three seconds budgets and counters from PROTOCOL.json. Accepted-budgeted
uses the unchanged compiler with `Limits(optimise_seconds=b, query_seconds=min(0.1,b))`
and all other defaults unchanged; its internal reserve/deadline logic remains
unchanged. Structural workers use the same direct bootstrap, then a separate
b-second optimisation deadline covering domain construction and validation.
Report measured overshoot; soft budgets are not exact wall-clock equality.
Accepted-default and accepted-bootstrap are unbudgeted reference arms with their
actual defaults recorded; do not replicate identical rows across budgets.

Model cover construction follows the scientific plan's deterministic merge.
Model serialization uses shortest unsigned base-128 varints (reject overlong
varints), sorted unique pairs, zero padding and exact EOF. Cover construction
limits are per set; an interrupted cover is INCONCLUSIVE, never exact evidence.
Use schema_index.Cube/intersect/difference; do not create a second cube algebra.

For P4 use structural ranks only. Shuffle lexicographically sorted canonical
compilation JSON identities with Random(20260925), separately reinitialised for
each fixture. n_train=floor(N/2), n_validation=floor(N/4); test gets the remainder.
At least ten train and five test objects are required for an informative fixture.
No hyperparameter tuning is allowed; validation is diagnostic only. The training
threshold includes ties at the ceil(n_train/10)-th ordered objective.

Every proposal arm starts from the same training elite E, excluding every
training index from new queries. Empirical-cover cannot produce unseen indices
and records exhaustion. Model-expand frees exactly one coordinate from each
training-cover cube, in cube `(anchor,free_mask)` order then ascending coordinate;
deduplicate cubes, visit the resulting union in ascending integer order, and
exclude previously evaluated indices. One-bit explores ascending distinct indices
formed by flipping one bit of any elite index. Uniform-bits draws getrandbits(B)
with the designated search seed; count every duplicate and invalid attempt.
Construct proposal sets lazily; do not materialise a full 2**B universe.

The evaluator may see the hidden complete domain. The learner receives only
training labels and results of its own paid queries. Report validation/test
proposals separately; test discoveries are indices with J at most the frozen
training threshold. Invalid/dead-end codes consume budget. Maintain best test
quality from the training-best incumbent, updating only on paid discoveries;
this defines the paired J endpoint even when an arm discovers nothing.

H4 advances only if at least three fixture families have informative tests and
the primary paired quality interval is above zero against BOTH one-bit and
uniform controls. Apply Bonferroni: each of these two advancement intervals is
97.5% (percentiles 0.0125/0.9875, 10,000 resamples). Also report descriptive 95%
intervals. No multiple-testing adjustment is needed for the sole H2 primary
contrast; secondary comparisons are exploratory.

The two domain variants of one fixture program are not independent programs.
Average paired log ratios over eligible variants within the semantic program
digest before family-stratified resampling. Average technical repetitions within
seed, then seeds, then variants; report every intermediate denominator. A family
with one informative program supplies no estimate of between-program variation
within that family; disclose this limitation. Percentiles use linear interpolation
at index `(N-1)*p` in the sorted resample list. Do not select the interpolation
method after examining the result.

For P5 the fixed H2 candidate is structural_bound versus accepted_budgeted;
structural_dfs, structural_expanded and reference arms are diagnostic controls.
If H4 passes, add `structural_model`: at each matched query allocate the first
half of its available search time to structural_bound collecting complete
observations; freeze the elite top decile (ties included), then spend the remaining
time on one-coordinate expansion under the same acceptance logic. If no complete
observations exist, record model unavailable and retain incumbent; no extra
fallback search. Control structural_bound uses its full budget. Model building
and all observations are paid. No cross-program learned state is retained.
The query's total time is min(0.1, remaining global optimisation time); phase
fractions are of that fixed query allowance, not repeatedly renewed deadlines.
This is the sole authorised large-domain model extension.

## 6. Stage machine and CLI

Implement this CLI from `luminal-challenge/`:

    PYTHONPATH=.reference:. python3 -m research.run_structural_experiments \
      --stage all --run-id RUN_ID --contract plan/phase2
    PYTHONPATH=.reference:. python3 -m research.check_structural_evidence \
      --run results/phase2_structural_encoding/RUN_ID --contract plan/phase2

`--stage` accepts preflight, p0, p1, p2, p3, p4, p5, all. `--run-id` permits only
letters, digits, underscore and hyphen. Create the run root exclusively; refuse
an existing run. Single-stage invocations may use `--inputs PRIOR_RUN` read-only
with verified dependency hashes and gate records, always writing a new run.
No flag disables gates, reduces corpus size, changes seeds, ignores failures or
allows overwrite. Internal subprocess worker entry points must validate identity
and are not alternative acceptance modes.

Stage graph: P0 -> P1 -> {P2,P3}; P3's triage -> P4; P2 -> P5 for the fixed
search candidate. H4 gates only the optional P5 model arm. P1's public coverage
requirement applies before P2–P5. An inconclusive P1 returns a factual handoff;
Claude cannot revise its domain or sampling policy on his own. P2 runtime null
results do not block P3/P5. P3 miss does not block non-model P5. Independent
stages execute sequentially in this assignment, without competing benchmarks.

P2 uses all tiny fixtures and public programs. For tiny fixtures run exhaustive
matched-domain oracle comparison. For public programs measure the frozen arm
matrix across all three budgets with fifteen timing repetitions; deterministic
search_seed=null. P3 uses all frozen fixtures and 100 controls. P4 stochastic
arms use all ten seeds and fifteen fresh-process repetitions. P5 uses all public
and 100 held-out programs, the P2 arm matrix, plus conditional model arm. Run
public and held-out analyses separately; do not pool them. Keep the official
three-repeat comparator as a separate unchanged control report.

Exit 0: all required runnable stages completed with valid evidence, including a
scientific null result and correctly marked conditional omissions. Exit 1:
correctness, integrity or checker failure. Exit 2: missing inputs, preflight
problem, or incomplete mandatory evidence. A lower-stage failure must still
write a handoff and mark all dependants BLOCKED_BY_GATE.

## 7. Required evidence structure and row identities

Each run has `manifest.json`, `commands.jsonl`, `gates.json`, `HANDOFF.md`,
`OWNERSHIP.md`, `PROOFS.md`, `logs/`, `inputs/`, and subdirectories p0..p5 for
executed stages. Manifest includes full SHA256s, immutable contract files, code
snapshot, baseline state, expected membership keys, actual row counts and stage
status. Use JSON with finite numbers; undefined values are null with reasons.

Rows identify `(stage, corpus, program_sha256, domain_sha256, codec, arm,
 budget_seconds, search_seed, repetition, attempt)`; null is explicit where
inapplicable. Never identify programs by display name alone. Store raw rows as
JSONL. A worker process emits one JSON result on stdout; diagnostics go to stderr.

Every decoder row includes index (decimal string), B, status, reason, decisions,
option counts, consumed work and compilation hash if complete. Every benchmark
row includes command/exit, timeout, all phase times, process peak RSS, C/S/J,
validator/case counts, original/best incumbent hashes, query/status counts and
budget configuration. Every complete candidate has enough retained decisions to
reconstruct and independently replay it. For raw sampling, store all indices and
outcomes; a trace may be compact or shared, but cannot depend on mutable state.

Status accounting must reconcile exactly: draws = COMPLETE + INVALID_CODE +
DEAD_END + INTERRUPTED; all COMPLETE outcomes have validator results. Rejected
COMPLETE results remain counted and fail the stage. Attempted optimiser queries
reconcile all recorded verdict buckets. Model novel/duplicate/invalid partitions
must cover every attempted proposal. Keep benchmark and profiling data separate.

The checker independently derives expected membership from locked inputs. It
must not accept a report-provided denominator, seed or bootstrap count as policy.
Recompute serialisation lengths, cover equality on tiny sets, control medians,
triage, statistics and decision gates. Confirm plan/protocol/package/source
hashes and protected files. Complete artifacts and complete scientific success
are distinct report fields.

## 8. Validation before handoff

Run all new unit modules explicitly and the unchanged existing verification:

    PYTHONPATH=.reference:. python3 -m unittest \
      tests_direct.test_phase2_encoding tests_direct.test_phase2_search \
      tests_direct.test_phase2_models tests_direct.test_phase2_evidence -v
    python3 export_direct.py
    python3 verify_direct.py --stage all --output NEW_RUN/production_verification
    python3 compare_direct.py --repeats 3 --timeout 20 \
      --output NEW_RUN/production_comparison

NEW_RUN means the actual new run directory, never that literal placeholder.
Retain complete command logs and return codes. New research tests may be slower
than canonical tests, but may not raise existing test timeouts. Neither the
production verification nor the new unit tests replaces experimental evidence.

Inject every defect listed in ACCEPTANCE_MATRIX.json in temporary fixtures.
Do not edit protected source to test failure. A checker that passes its happy
path but accepts missing programs, changed seeds or omitted failed rows is not
complete. Test wrong source hashes, forbidden imports and a planted duplicate
owner. Static checks are supporting evidence; add runtime guards and document
their limits. Do not claim an AST scan proves semantic absence of duplication.

Fill HANDOFF_TEMPLATE.md into HANDOFF.md. Finish with READY_FOR_REVIEW and the
exact run path. Report all unrun stages and why. Do not say ACCEPTED, publication
ready, superior, or globally optimal. Codex will rerun and adjudicate independently.

## 9. Deterministic data and random-stream conventions

Canonical JSON is UTF-8 `json.dumps(value, sort_keys=True, separators=(',', ':'),
ensure_ascii=False, allow_nan=False)` without a trailing newline. Object digests
hash those bytes. File digests hash actual file bytes. Distinguish them explicitly.
Program semantic digests omit only the top-level display name. Compilation
identities contain canonical scratch keys and engine bundles with sorted IDs;
retain internal empty bundles and remove only trailing empties. For `encode`,
normalise first and compare round trips to that normalised object. Duplicate or
missing operations are errors, not normalisation opportunities.

For P1 reinitialise Random(raw_bits_seed) and Random(option_paths_seed) independently
for each program. Raw sampling calls getrandbits(B). Option-path sampling calls
randrange(m) once per decision with m>1, no draw for m=1, and stops on m=0;
use the resulting ranks to assemble the fixed-layout index. Never resample a
failed attempt invisibly. Do not replace pseudo-random streams with Python's
process-randomised hash().

For P3 reinitialise Random(structure_controls_seed) per fixture; sample from
sorted canonical compilation identities without replacement within each control,
retaining all 100 controls even if two happen to coincide. Map the same physical
control subset into each codec. This pairs representation comparisons on the
same objects. Control construction must not favour a codec's index adjacency.

For balanced timing order, within each (program, budget, search_seed) block,
start from the sorted eligible arm list, shuffle it once using the recorded
arm-order RNG, and rotate by repetition modulo the arm count. Initialise that
RNG once for the full stage; iterate programs in manifest order, budgets ascending,
then seeds ascending (null first). No competing benchmark processes. Use
perf_counter for elapsed durations and process_time for CPU, and record the
platform-specific conversion of peak RSS to bytes.

Freeze no minimum number of successful experiments beyond the declared gates.
Do not silently retry a timed-out measurement or repeat seeds until a gate passes.
For an implementation defect, retain the failed run; repairs receive a new run
ID and source snapshot. Scientific policy changes require a lead amendment.
