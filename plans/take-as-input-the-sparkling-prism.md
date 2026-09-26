# Phase 2 structural-encoding research campaign (Luminal)

## Context

`luminal-challenge/plan/phase2/CLAUDE_CODE_PROMPT.md` delegates implementation of the
phase 2 research campaign to this session. Codex owns the scientific specification
(`plan/PHASE2_STRUCTURAL_ENCODING_PLAN.md` v2.1) and the independent acceptance review;
this session is the implementing coder.

The research question: does a **state-relative coordinate system for compiler decisions**
(issue cycles + scratch addresses encoded as ranks into option lists) expose structure that
direct index schemata can exploit — and does a schema model over those coordinates discover
*unseen* good compilations? Four hypotheses (H1 soundness/completeness, H2 search effort,
H3 compactness, H4 discovery), six gated stages (P0–P5).

The deliverable is **reviewable research evidence**, not a production change. A null
scientific result is legitimate completion. Only Codex may mark the work accepted.

Preflight already run: `python3 plan/phase2/verify_package.py` → **PASS**, exit 0
(12 package files, 46 baseline files, 12 fixtures, 30 acceptance checks). HEAD is
`1aef906`, matching `BASELINE_LOCK.json.git_head_at_preparation`. Working tree carries
two lead-owned changes to preserve: modified `plan/PHASE2_STRUCTURAL_ENCODING_PLAN.md`
and untracked `plan/phase2/`.

## Exploration findings (owners to reuse, never re-create)

| Concept | Owner | Notes |
|---|---|---|
| Hardware semantics, independent acceptance | `.reference/machine.py` | `check_compilation`, `check_case`, `scratch_footprint`, `VLEN`, `SCRATCH_WORDS`, `ENGINE_LIMITS` |
| Derived program facts, lifetimes, assembly, footprint | `direct_contract.py` | `derive`, `lifetimes`, `assemble_bundles`, `compilation`, `footprint`, `check_feasible`, `cycle_lower_bound`, `time_width`, `ADDRESS_WIDTH=8` |
| Cubes and exact set algebra | `schema_index.py` | `Cube`, `intersect`, `difference`, `restrict`, `split`, `normalise_cover`, `Budget`/`Meter` |
| Absolute-field joint query | `direct_constraints.py` | `JointQuery`, used unchanged for the absolute-query control |
| Accepted optimiser policy | `direct_optimizer.py` | `targets_for`, `windows_for` reused verbatim for matched windows; `optimise` unchanged for control arms |
| Accepted compiler + budgets | `direct_compiler.py` | `Limits(optimise_seconds=b, query_seconds=min(0.1,b))`, `bootstrap`, `compile_with_report(optimise=…)` |
| Corpus generation | `tests_direct/generate_programs.py` | `additional_program(seed)` sole generator; `FAMILIES` = scalar, vector, mixed, dependency, aliasing; `program_digest` |
| Isolated subprocess measurement pattern | `benchmark_optimization.py` | `DIRECT_WORKER` (`python3 -I -S` from a neutral temp dir), `Bench`, `per_program_medians`, `paired_bootstrap` — read as reference; phase 2 statistics differ (family-stratified, Bonferroni) so the new runner owns its own aggregation |

Frozen inputs: 12 fixtures = 6 programs × 2 domain variants, families `scalar` (8),
`memory` (2), `mixed` (2); Cartesian sizes 36–300, total 1434. Held-out seeds
800000–800099 give exactly 20 per family (`family = seed % 5`) and are disjoint from
the recorded historical evaluation range (confirmed: `results/direct_index_v4_optimization/baseline/extra_corpus_manifest.json`
spans 202158–397767).

## Constraints

- Writable: only the 12 allowlisted new files and new directories under
  `results/phase2_structural_encoding/`. Everything else read-only. No commit, push,
  stash, reset, branch change, or edit to the plan package.
- No BDD, SAT/SMT library, classical seed or fallback in the candidate path.
- Contract fixes all domains, layouts, algorithms, arms, budgets, seeds, metrics and
  denominators. A contradiction is a blocker to report, not a licence to reinterpret.

## Implementation

### 1. `research/structural_encoding.py` — domain, layout, codecs

- `Domain.from_record(record)`: validate explicit nonempty sorted-unique integer domains,
  reject booleans / negatives / out-of-range / duplicates / missing keys / malformed
  incumbent; assert selected values are exactly the results of selected operations and
  that every operation and value is covered exactly once by a variable or fixed field.
  Empty *feasible* set is legal; a malformed empty option array is not.
- `layout(domain, codec) -> Layout`: **fixed for the whole Domain** — all selected time
  fields in operation-ID order, then all selected address fields in producer-ID order,
  LSB-first. Widths: `absolute` → `dc.time_width(facts.horizon)` and 8-bit addresses;
  `vector_block` → identical except 5-bit vector block index with `a = 8*b` (exact
  arithmetic, no truncation); `static_rank`/`structural_rank` →
  `(len(declared_domain)-1).bit_length()`. Zero-width fields occupy no bits and never
  construct an `si.Field`.
- `decode(domain, index, codec, budget=None) -> DecodeResult`:
  - validate index type and `0 <= index < 2**B` first (B=0 admits only 0);
  - reject fixed–fixed scheduling contradictions at state initialisation → `DEAD_END`;
  - traversal: selected times by operation ID, then addresses **vectors first, then
    scalars, by `(write_cycle, producer_id)` after scheduling** — each field is read from
    its own preassigned offset, never repacked into traversal order;
  - at each decision: **empty options → `DEAD_END` first, then rank ≥ |options| →
    `INVALID_CODE`**;
  - scheduling options check every already-assigned and external predecessor/successor
    constraint (successor IDs may be larger) and engine capacity;
  - at the scheduling/address boundary recompute all lifetimes (`dc.lifetimes`) and check
    fixed–fixed address overlaps → `DEAD_END` if selected reads created a conflict;
  - address options check all fixed and previously assigned blocks over full **inclusive**
    lifetimes; option lists never consult an oracle or the objective;
  - target, when present, is an explicit Domain predicate; final failure is `DEAD_END`;
  - `COMPLETE` runs `dc.check_feasible` + `machine.check_compilation`; a fully decoded
    illegal compilation raises a retained `CodecDefect` and fails the stage — it is never
    downgraded to `DEAD_END`.
- `encode(domain, compilation, codec) -> int`: normalise first (bundles by increasing op
  ID per engine, trailing empties removed, internal empties retained), reject outside
  `F_d`, round-trip against the normalised object.
- `options(domain, prefix, decision) -> tuple[int, ...]` public for tests and search.

### 2. `research/structural_oracle.py` — independent enumeration

Imports **only `machine` and the standard library** (enforced by the architecture guard).
Enumerates the declared Cartesian product, assembles its own `{"scratch":…, "bundles":…}`
dictionaries, and accepts via `machine.check_compilation` / `check_case` /
`scratch_footprint`. Never imports the codec, the search, or `dc.check_feasible`.
Also serves as the hidden evaluator in P4.

### 3. `research/structural_search.py` — DFS and bounds

`search(domain, incumbent, arm, budget) -> SearchReport`. Depth-first, decision order,
ascending option ranks, no restarts. One immutable incumbent per query for rank ordering;
updating the best solution never reinterprets a constructed index. Strict `J = C·S`
improvements only; ties keep the earlier incumbent. Every complete proposal is validated
on every case before acceptance. Complete-compilation identities cached within a run, with
duplicate lookup/work charged.

Bounds (`structural_bound` only, exactly these):
`L_C = max(facts.cycle_lower_bound(), 1 + max assigned/fixed issue time)` (max omitted when
nothing is assigned); `L_S = max(widest result, max assigned/fixed address end)`, plus peak
simultaneous live width once scheduling completes. No incumbent-lifetime bound before
scheduling completes. Prune when `L_C·L_S ≥` best validated product. Local feasibility
checks are identical in the pruned and unpruned arms.

Counters/budgets from `PROTOCOL.json` (`search_max_nodes`, `search_max_candidate_validations`,
`query_max_*`).

### 4. `research/structural_models.py` — cover, serialization, proposals

- Cover: minterms, then repeatedly merge equal-mask cubes differing in one fixed
  coordinate, choosing the smallest `(coordinate, anchor, free_mask)` eligible pair, until
  no merge remains. Uses `si.Cube`/`intersect`/`difference` — no second cube algebra.
  Per-set limits `cover_seconds_per_set=10`, `cover_max_cubes=65536`; an interrupted cover
  is `INCONCLUSIVE`, never exact evidence.
- Serialization: shortest unsigned base-128 varints for B and cube count (overlong varints
  rejected), then sorted unique `(anchor, free_mask)` pairs as two little-endian
  `ceil(B/8)`-byte integers, zero-padded, exact EOF. Same format for the minterm control.
- Proposal arms (P4), all from the same training elite E, all excluding every training
  index from new queries: `empirical_cover` (cannot produce unseen indices; records
  exhaustion), `model_expand` (free exactly one coordinate per training-cover cube, in cube
  `(anchor, free_mask)` order then ascending coordinate, deduplicate cubes, visit the union
  in ascending integer order, exclude previously evaluated), `one_bit` (ascending distinct
  one-bit flips of elite indices), `uniform_bits` (`getrandbits(B)` with the designated
  search seed). Sets built lazily — never materialise `2**B`. Every attempted, failed and
  duplicate proposal stays in the denominator.

### 5. `research/run_structural_experiments.py` — CLI and stage machine

```
PYTHONPATH=.reference:. python3 -m research.run_structural_experiments \
  --stage all --run-id RUN_ID --contract plan/phase2
```
`--stage` ∈ {preflight,p0,p1,p2,p3,p4,p5,all}; `--run-id` `[A-Za-z0-9_-]+`; run root created
exclusively, refuses an existing run; `--inputs PRIOR_RUN` read-only with verified
dependency hashes. No flag disables a gate, shrinks a corpus, changes a seed or allows
overwrite. Stage graph P0 → P1 → {P2,P3}; P3 triage → P4; P2 → P5; H4 gates only the
optional P5 model arm. Exit 0 / 1 / 2 per contract §6; a lower-stage failure still writes
`HANDOFF.md` and marks dependants `BLOCKED_BY_GATE`.

- **P0** — save `git status`, HEAD, full diff into the run root; verify every
  `BASELINE_LOCK.json`, `PACKAGE_LOCK.json` and `reference.json` hash; revalidate all 12
  fixture incumbents with the pinned validator and every case; recompute optimiser status
  totals (SAT / UNSAT / INFEASIBLE / UNKNOWN_CONSTRUCTION / UNKNOWN_SEARCH separately) from
  retained raw reports; materialise held-out seeds 800000–800099 via
  `additional_program`, check semantic digests (excluding only `name`) against public,
  regression, additional and historical extra manifests — any collision is a preflight
  failure with no replacement seed; freeze the manifest and hashes; write `OWNERSHIP.md`.
- **P1** — exhaust the code universe where `B ≤ 16`, otherwise round-trip every feasible
  oracle object plus budgeted probes; compare normalised solution sets against the oracle
  for all 12 fixtures; 8 public programs × 2 streams × 10,000 attempts, seeds 20260922 /
  20260923, 60 s per program per stream, `Random` reinitialised per program per stream;
  require ≥100 distinct completed compilations per program or report the exhaustively
  established smaller `F_d`; otherwise `INCONCLUSIVE`. Write `PROOFS.md` (termination,
  soundness, completeness over `F_d`, round trip, injectivity, domain equivalence, origin).
- **P2** — tiny fixtures: exhaustive matched-domain oracle comparison and a bound check of
  every prefix bound against every completion. Public programs: the frozen arm matrix
  (`accepted_bootstrap`, `accepted_default` unbudgeted; `accepted_budgeted`,
  `structural_dfs`, `structural_bound`, `structural_expanded` at 0.01/0.1/1.0 s) × 15
  fresh-process repetitions, `search_seed=null`, balanced arm order (RNG seed 20261020
  initialised once per stage, shuffled once per `(program, budget, seed)` block and rotated
  by repetition). Structural workers use the same direct bootstrap then a separate
  b-second optimisation deadline covering domain construction and validation; measured
  overshoot reported. `structural_expanded` is reported in a separate table and never
  labelled a matched comparison.
- **P3** — all fixtures with nonempty `F_d`: score every feasible object, set `q` to the
  smallest integer objective at which ≥10 % have `J ≤ q` (all ties included, count
  reported), build exact covers of `A_d(q)` and of 100 cardinality-matched controls
  (seed 20260924, reinitialised per fixture, sampled without replacement from sorted
  canonical identities, the same physical subset mapped into each codec), verify equality
  and disjointness by expansion, and compute serialised lengths. Triage: ≥20 % shorter than
  the median control in ≥half of informative fixtures spanning ≥3 families.
- **P4** — structural ranks only. Per fixture, shuffle lexicographically sorted canonical
  identities with `Random(20260925)` reinitialised per fixture; `n_train = floor(N/2)`,
  `n_validation = floor(N/4)`, test = remainder; require ≥10 train and ≥5 test to be
  informative. Training threshold = the `ceil(n_train/10)`-th ordered objective, ties
  included. Four proposal arms under matched budgets, 10 search seeds for stochastic arms,
  15 fresh-process repetitions. The learner sees only training labels and its own paid
  queries; the evaluator may see the hidden domain. Best test quality starts from the
  training-best incumbent and updates only on paid discoveries.
- **P5** — public and 100 held-out programs, analysed **separately, never pooled**; P2 arm
  matrix plus the conditional `structural_model` arm (only if H4 passes: first half of each
  matched query's allowance to `structural_bound` collecting complete observations, freeze
  the elite top decile with ties, remaining time on one-coordinate expansion under the same
  acceptance logic; model unavailable ⇒ retain incumbent, no extra fallback). Query
  allowance `min(0.1, remaining global optimisation time)`, fractions of that fixed
  allowance. Plus the unchanged official three-repeat comparator as a separate control.

Statistics: primary endpoint paired `log(J_control / J_candidate)` at 0.1 s; average
technical repetitions within seed, then seeds, then domain variants within a semantic
program digest, then resample programs within family weighting families equally; 10,000
resamples, seed 20261021; percentiles by linear interpolation at index `(N-1)p`. H4
advancement uses Bonferroni 97.5 % intervals (0.0125 / 0.9875) against **both** `one_bit`
and `uniform_bits`; descriptive 95 % intervals also reported. Every intermediate
denominator is recorded.

Evidence per run: `manifest.json`, `commands.jsonl`, `gates.json`, `HANDOFF.md`,
`OWNERSHIP.md`, `PROOFS.md`, `logs/`, `inputs/`, `p0..p5/`. Row identity is
`(stage, corpus, program_sha256, domain_sha256, codec, arm, budget_seconds, search_seed,
repetition, attempt)` with explicit nulls; raw rows as JSONL; workers emit one JSON object
on stdout, diagnostics on stderr. Status accounting reconciles exactly:
`draws = COMPLETE + INVALID_CODE + DEAD_END + INTERRUPTED`.

### 6. `research/check_structural_evidence.py` — independent checker

Derives expected membership from the locked inputs, never from a report-provided
denominator, seed or resample count. Recomputes serialisation lengths, cover equality on
tiny sets, control medians, triage, statistics and gate decisions; confirms plan / protocol
/ package / source hashes and protected files; refuses empty scans and NaN metrics; reports
"complete artifacts" and "complete scientific success" as distinct fields. Includes the
architecture guard: an AST scan for prohibited imports and duplicated cube/machine owners,
**plus** a runtime import guard executed in a subprocess, with its limits documented — an
AST scan is never claimed to prove semantic absence of duplication.

### 7. Tests — `tests_direct/test_phase2_{encoding,search,models,evidence}.py`

Cover the contract's failure modes explicitly: fixed offsets under a changed decoded
schedule (C04); three/five choices, excess ranks, B=0 (C05); external predecessor/successor
bounds (C06); equal last-read/new-write and adjacent non-overlap (C07); a selected reader
extending two fixed values into conflict (C08); vector misalignment, address > 255,
scalar/vector overlap and holes (C09); exact domain equivalence and encode of every
feasible object (C10); hidden attempts rejected (C11); injected fully decoded invalid
compilation ⇒ stage FAIL (C12); bound admissibility against every completion (C13); budget
exhaustion ⇒ UNKNOWN/INTERRUPTED, never fabricated UNSAT (C14); membership duplication/
omission (C15); cover and varint mutations (C16–C18); empirical cover discovers nothing
(C19); leakage guard (C20); novelty/duplicate accounting (C21); interval mutation (C22);
removed failed held-out rows (C23); planted duplicate owner and prohibited import (C24);
provenance mutation (C25); dependency-truth mutation (C26); empty/malformed input (C28);
clock overshoot and incumbent retention (C29); canonical object and exact operation set
(C30). All 30 defects injected in **temporary fixtures** — protected source is never
edited — with the unmutated control passing first.

## Verification

```bash
cd luminal-challenge
python3 plan/phase2/verify_package.py                                    # expect PASS, exit 0
PYTHONPATH=.reference:. python3 -m unittest \
  tests_direct.test_phase2_encoding tests_direct.test_phase2_search \
  tests_direct.test_phase2_models tests_direct.test_phase2_evidence -v
PYTHONPATH=.reference:. python3 -m research.run_structural_experiments \
  --stage all --run-id <RUN_ID> --contract plan/phase2
PYTHONPATH=.reference:. python3 -m research.check_structural_evidence \
  --run results/phase2_structural_encoding/<RUN_ID> --contract plan/phase2
python3 export_direct.py
python3 verify_direct.py --stage all \
  --output results/phase2_structural_encoding/<RUN_ID>/production_verification
python3 compare_direct.py --repeats 3 --timeout 20 \
  --output results/phase2_structural_encoding/<RUN_ID>/production_comparison
git status --short        # only allowlisted new paths + the two lead-owned changes
```

Plus the checker run against **corrupted fixture copies** for all 30 acceptance-matrix
defects, with exit codes and logs retained.

Runtime note: P5 is 108 programs × 14 arm/budget configurations × 15 fresh-process
repetitions ≈ 22.7 k subprocesses, roughly 3–8 hours of wall clock. It runs in the
background with full logging; the earlier stages complete and are checkable first. No
timeout is enlarged and no repetition count is reduced to shorten it.

## Completion

Fill `HANDOFF_TEMPLATE.md` into `HANDOFF.md` in the run root: modified-file list, run root,
every command with exit code and log path, expected vs actual denominators, P0–P5 and H1–H4
dispositions, every failure and unrun stage with its reason, limitations. Final response
ends with `READY_FOR_REVIEW` and the exact run path. No `ACCEPTED`, "publication ready",
"superior" or "globally optimal" claim — Codex adjudicates independently.
