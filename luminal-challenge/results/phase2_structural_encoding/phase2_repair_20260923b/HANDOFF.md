# Phase 2 implementation handoff — bounded repair of the 2026-09-23 lead review

Status: READY_FOR_REVIEW.
Implementer/model: Claude Code (Opus 5).
Start/end time: 2026-09-23T09:05:05 to 2026-09-23T09:05:43 for the campaign run;
the whole repair session ran on 2026-09-23.
Source HEAD, dirty diff SHA256, source snapshot SHA256:
`1aef90681e3dead3ab1f560da8b7823ab66dabf4`,
`5e32299313189de840b17e72c01b572b898a00685b62d7974dc047c5d4f192f9`,
`b56ddc277dc10e122829c72b6927c55f314f2514485ab8bfd5c8e7d23a100bbd`.
Plan/protocol/package hashes: plan `PHASE2_STRUCTURAL_ENCODING_PLAN.md`
`d2e5ceaef78f18bd5af6b7f7747a0335c883aad46e1c0ab8784d9126d8f7a9a5`;
`PROTOCOL.json` `58af676952df5503765fe2ae1a0f5302e5631d9b8c3dbb2e5b69d635bc522431`;
`PACKAGE_LOCK.json` `f29910c945e67e6328083d8bd1d0d4bc7af7a544a42b3d5afd8afe1b2cd6e152`;
`BASELINE_LOCK.json` `e77c790b717605b401873123f49987f120b4d5aa6b81ac3f80c9dd7bc3764438`;
`FIXTURES.json` `ba19024daacc7c33300ed01b2ee13f0222ab2deed9af30f59bfb33e2f131e679`;
`ACCEPTANCE_MATRIX.json` `7c499e12cdd516adef03866400c6a7c104e825c4771bf50b8c7f7a4d4e68c93a`.
Amendment inputs, recorded in this run's manifest and verified by the checker:
`LEAD_REVIEW.md` `71b64cc172d6b5e2d30066efd0ca69de07c51071fb81f21d7ae48bb0667aae4d`,
`REPAIR_HANDOFF.md` `fbf1867c55d0ce69b66f75aa7fea3169d289f0ae8d586d8c07eb3724d05a3cce`.
Run directory: `results/phase2_structural_encoding/phase2_repair_20260923b`.

**This handoff claims no acceptance and no scientific success.** P1 is
INCONCLUSIVE for the same reason the lead independently reproduced, P2–P5 remain
BLOCKED_BY_GATE, and there is still no measured runtime, compression or discovery
result. A passing unit suite establishes none of that; only Codex accepts.

## Correction to the previous handoff

The 2026-09-22 handoff
(`results/phase2_structural_encoding/phase2_20260922_final/HANDOFF.md`, preserved
unedited) stated that the codec's correctness obligations were discharged for the
sampled public outputs and that the reference manifest was fully checked. **Both
claims were too strong and are withdrawn here.**

* No sampled public compilation was ever *executed*. `se.decode` checks static
  feasibility and `machine.check_compilation`; neither runs a case. Across the
  original 160,000 draws the case validator was called **0 times**.
* `Contract.verify_locks` read `reference.json['files']`, a key the manifest does
  not have. It iterated **0 of 16** reference entries and reported PASS with 58
  checks. The claim of a full reference check was false.

Both are now measured facts of this run: 1,356 case executions over 819
completions, and 76 lock checks of which 16 are reference entries.

## Disposition of every finding

| ID | Verdict | Disposition | Where |
|---|---|---|---|
| L1 | test-placement contradiction | **FIXED** | four modules relocated to `research_tests/`; `verify_direct.py --stage all` now PASS (0 failing) |
| R1 | P1 omits case execution, discards raw attempts | **FIXED** | `run_structural_experiments.py` `AttemptSink`, `_run_stream`, `stage_p1` |
| R2 | checker accepts erased evidence | **FIXED** | `check_structural_evidence.py` `check_p1`, `recheck_sampling_legality`, `check_stage_digests`, `check_amendment`, `check_commands`, `recompute_comparisons`, `recompute_p4_contrasts` |
| R3 | single-stage resume bypasses gates | **FIXED** | `Run.dependency_status`, `Run.verify_imported`, `Run.prior`, `main` |
| R4 | construction time refunded to search | **FIXED** | `structural_optimise`, `_model_optimise`, `structural_search.search(deadline=…)` |
| R5 | conditional model implementation incomplete | **FIXED** | `_model_optimise`, `_benchmark_corpus(extra_arms=…)`, `stage_p5`, `structural_models.ordered_union` |
| R6 | reference manifest reads the wrong key | **FIXED** | `Contract.verify_locks` |

No finding is left unresolved. Two items are **outstanding but out of scope**, and
are listed under *Limitations*: the P1 coverage shortfall itself (retained, not
tuned away) and the size of the raw evidence file, which needs a lead decision
before any commit.

### L1 — relocation

| From | To | SHA256 at the new location |
|---|---|---|
| `tests_direct/test_phase2_encoding.py` | `research_tests/test_phase2_encoding.py` | `a1203e41ac84335a54be217bc09c529d69062890ca616a4357d13f82c421df0d` (byte-identical) |
| `tests_direct/test_phase2_search.py` | `research_tests/test_phase2_search.py` | `26929b7c34c5d8ab92c61b0d82b331c3189a65170e7ab01248709189a3b9b6eb` (byte-identical) |
| `tests_direct/test_phase2_models.py` | `research_tests/test_phase2_models.py` | `b19e27f06af17b2209f35eaf5113fc6b0de02d1e6b773f977f3ed5ce9ee1474f` (one assertion updated: `proposals` gained `budget_check`) |
| `tests_direct/test_phase2_evidence.py` | `research_tests/test_phase2_evidence.py` | `df9a97676c1ecea030649a483ba4b8a7170b17b1138b542bd7381d5e1c9a0a4a` (own-path reference, digest resync helper, valid P2 control) |
| — | `research_tests/__init__.py` (new) | `705e9d649e9efa0477c812d350ecb9806d65c5d5b2c8bd6317b12acd09d485f3` |
| — | `research_tests/test_phase2_repair.py` (new) | `686a9e3a8a2ead5729ab747044f16d74dd5dd8d6ec54ae64c262392f743a7039` |

`source_snapshot()` now hashes `research_tests/*.py`
(`run_structural_experiments.py:307`), and `research/README.md` documents the new
command and why the path moved.

Before: `tests_direct.test_evidence_checker` 2 of 64 failing, both
`recorded_hashes:final`; `verify_direct.py --stage all` → `evidence: FAIL`,
`overall: FAIL (1 failing)`.
After, with all six research test modules present in their final location:
`Ran 64 tests … OK`; `verify_direct.py --stage all` → **`overall: PASS (0
failing)`**, 12 of 12 stages, `acceptance/corpus` 142 programs.
`check_optimization_evidence.py`, the historical provenance record and the
original tests are byte-identical; nothing was moved aside and no exclusion was
added. Regression: `research_tests.test_phase2_repair.L1TestPlacement` (4 tests,
one of which re-runs the frozen suite in a subprocess).

### R1 — every attempt retained, every completion executed

Code: `AttemptSink` (`run_structural_experiments.py:654`), `_run_stream`
(`:698`), `stage_p1` (`:2203`).

* One raw JSONL row per draw, streamed as it happens, to
  `p1/sampling_attempts.jsonl`. Immutable identity per row: stage, corpus,
  program, `program_sha256`, stream, seed, codec, `domain_id`, `domain_sha256`,
  bits, attempt index, index as a decimal string, status, reason, decisions,
  trace reference, `compilation_sha256`, `cases_declared`, `cases_checked`,
  `case_failures`.
* Every COMPLETE decode is handed to `machine.check_case` once per declared case,
  inside the stream's own time budget.
* A rejected completion becomes a retained discrepancy artifact
  (`sampled_completion_failed_case`, with times, addresses, index and the
  validator message), the status stays COMPLETE, and `stage_p1` fails. It is
  never converted to DEAD_END.
* No cap. `completions` holds the full decoder row of every distinct completion;
  `complete_examples_excerpt` is a separate ≤50-row display field.
* `p1/sampling_identities.jsonl` retains the per-program identity union with the
  raw-only, path-only and both partitions, so the union denominator is
  reconstructible; `identity_multiplicities` gives the duplicate counts.
* `_run_stream` refuses to return if the rows it contributed do not equal its
  draws (this guard fired once during development and is regression-tested).

Lead reproduction, re-run: the probe installs a `machine.check_case` mock that
raises when reached. It recorded **3 completions, 0 case-validator calls**. It now
raises, which ends the lead's script at that probe —
`lead_probe_replay/probes_replayed.log`. The non-fatal replay records
**3 completions, 3 case calls, 3 case checks, 3 raw rows**
(`lead_probe_replay/probes_after_repair.json`, `sampler_case_validation`).
Regressions: `R1SamplingEvidence`, 6 tests.

### R2 — the checker derives, requires, and recomputes

Code: `check_p1` (`check_structural_evidence.py:433`),
`recheck_sampling_legality` (`:784`), `check_stage_digests` (`:169`),
`check_amendment` (`:206`), `check_commands` (`:274`), `check_p0` public
membership (`:394`), `recompute_comparisons` (`:1022`),
`recompute_p4_contrasts` (`:1120`), `check_p3` control recomputation (`:1312`),
status-vocabulary and manifest-agreement checks in `main` (`:1725`).

What changed, in the order the review listed it:

1. **Expected keys from locked inputs only.** P1 fixture membership is the twelve
   locked fixtures; the four codecs are required per fixture; the public corpus
   and the 16 `(program, stream)` pairs come from `runner.public_programs()`, not
   from the reported coverage list.
2. **Stage summary and raw artifact hashes required.** `stage_digests` must exist
   and match for every stage with a summary; the five P1 raw files must exist,
   be non-empty, and match the digests the summary records; `row_counts` in the
   manifest are re-counted from disk.
3. **Independent recomputation.** Status accounting, case denominators, attempt
   indices, identity unions, coverage counts, `meets_minimum`, `coverage_met`,
   and the `origin_is_incumbent` claim are all recomputed. Every one of the
   160,000 retained attempts is re-decoded against a domain rebuilt from the
   frozen program, and every completion is re-validated on every case
   (`p1.legality_recompute`: 160,000 attempts re-decoded, 1,356 case executions).
4. **Hashes alone do not pass.** The review's erased-evidence probe is rejected
   *with the manifest digests recomputed to match the edited files*: exit 1, 20
   findings, `artifacts_complete=false`. Without the re-hash it is exit 1 with 26
   findings. Before the repair it was exit 0, 0 findings,
   `artifacts_complete=true`.
5. **Later-stage statistics recomputed from raw measurements.**
   `recompute_comparisons` recomputes each P2/P5 paired contrast — status,
   programs, wins/ties/losses, point estimate, both intervals, family
   denominators — from the benchmark rows and compares exactly (the bootstrap is
   seeded, so exact agreement is the expectation; a `1e-12` relative tolerance
   covers only float summation order). `recompute_p4_contrasts` recomputes the
   P4 contrasts, the Bonferroni gate bounds and `advance_to_model_arm`.
   `check_p3` now rebuilds the 100 controls per fixture per codec and re-measures
   their median and the triage margin.
6. **Failed or missing commands cannot be labelled complete.** A nonzero exit or
   a timeout in `commands.jsonl` is now a finding; an empty log for a stage
   recorded as run is a finding; a gate status the protocol does not declare is a
   finding; a disagreement between `gates.json` and the manifest is a finding.

Because these recomputations must have one owner, the P3 control covers and the
P4 contrasts were *extracted* from the stages into
`runner.control_serialisation` and `runner.p4_contrasts`; both stages and the
checker call the same function, and what makes the checker independent is that it
supplies the locked inputs and the raw rows rather than the summary. That is
enrich-the-owner, not a second copy.

Regressions: `R2EvidenceChecker` (14 tests against a fresh valid control),
`R2IntervalRecomputation` (6), `R2P4Recomputation` (4),
`R5CheckerRequiresModelRows` (3), and
`test_an_edited_summary_whose_digest_is_not_resynced_is_detected`.

**A note on the control.** The strengthened provenance now legitimately rejects
`phase2_20260922_final` (131 findings: no amendment record, no raw attempts, a
stale source snapshot). Rejecting that run is *not* evidence that the targeted
mutation was caught, so every corruption probe is applied to a **new valid
control** instead — `R2EvidenceChecker` builds one inside the test, and
`lead_probe_replay/probes_after_repair.py` corrupts a copy of this run. Both
outcomes are recorded side by side.

### R3 — a dependent stage cannot be entered on a failed dependency

Code: `Run.dependency_status` (`run_structural_experiments.py:1861`),
`Run.verify_imported` (`:1880`), `Run.prior` (`:1958`), `main` dependency block
(`:3965`).

* Blocking happens **before** the stage body is called, and `--inputs` no longer
  skips it.
* A local dependency must have recorded PASS in this run.
* An imported dependency must satisfy, all of them, or the stage does not start:
  gate PASS in the prior manifest; a **present** and matching stage digest (a
  missing hash is a FAIL, not an absent expectation); identical protocol id;
  byte-identical contract files; an identical research source snapshot; and the
  whole transitive dependency chain, checked recursively.
* Prior runs are opened read-only; nothing writes into `--inputs`.
* No `--force`, `--skip-gate`, `--no-gates`, `--allow-blocked` or
  `--ignore-dependencies` flag exists; a test asserts their absence.

Lead reproduction, re-run: requesting P2 with this INCONCLUSIVE P1 as `--inputs`
and a stub P2 body. Before: exit **0**, stub entered with `coverage_met=false`.
After: exit **2**, `p2` = `BLOCKED_BY_GATE`, reason
`blocked by p1 (INCONCLUSIVE, imported)`, **stub never entered**
(`lead_probe_replay/probes_after_repair.json`, `resume_gate_bypass`).
Positive control: the same invocation against a prior run whose P1 is recorded
PASS enters the stub exactly once and exits 0
(`R3DependencyGate.test_a_valid_prior_pass_is_the_positive_control`).
Regressions: `R3DependencyGate`, 8 tests.

### R4 — one absolute deadline

Code: `structural_optimise` (`run_structural_experiments.py:959`), its matched
loop (`:1120`), `_model_optimise` (`:1199`), `structural_search.search`
(`structural_search.py:163`).

* `ss.search` takes an absolute `deadline` (a `perf_counter` instant). The
  meter's `seconds` is a *relative* allowance and cannot express time already
  spent, which is exactly how construction came to be refunded.
* Expiry is checked before the traversal starts, at every node, immediately
  before candidate validation, and immediately after it — validation being the
  uninterruptible step.
* Per query the allowance is fixed once, **before** construction, as
  `min(now + query_seconds, global deadline)`. After construction the remaining
  time is recomputed; if it is not positive the query is recorded
  `UNKNOWN_CONSTRUCTION` with an `after_construction` interrupted attempt and the
  pass stops. No fresh full allowance is ever issued after building.
* `max(remaining, 1e-6)` is gone; the `1e-9` floor exists only because
  `si.Budget` (production, unchanged) rejects a non-positive `seconds`, and the
  expired case is handled by the caller before that floor can matter. A test
  asserts the old expression is absent.
* A candidate whose validation crosses the deadline increments
  `interrupted_validations`, does **not** become the incumbent, and the
  previously validated incumbent is retained.
* Measured overshoot stays in `overshoot_seconds`; the new
  `interrupted_attempts` / `interrupted_attempt_count` fields and a literal
  `budget_renewals: 0` keep the two statements apart.

Lead reproduction, re-run: a controlled clock, a 0.01 s global allowance, and a
constructor that advances the clock to 1.0 s. Before: search was invoked at clock
1.0 with **another 0.01 s**. After: search is **not invoked at all**;
`stopped_because` is `deadline` and the interruption is recorded with its phase,
window and domain digest. The same is checked for `structural_expanded`
(`whole_program_record`), and a 0.004 s constructor under a 0.01 s query
allowance now reaches search with **0.006 s**, not 0.01 s.
Declared caps: `max_visited=1` → UNKNOWN "visited-cube budget exhausted";
`max_records=1` → UNKNOWN "expression-record budget exhausted", on a domain that
demonstrably pays for two validations.
Regressions: `R4SharedDeadline`, 9 tests.

### R5 — the conditional model arm, completed

Code: `_model_optimise` (`run_structural_experiments.py:1199`), dispatch from
`structural_optimise` (`:1085`), `_benchmark_corpus(extra_arms=…)` (`:2466`),
`stage_p5` (`:3324`), `structural_models.ordered_union` (`:211`), `proposals`
(`:378`).

* **Routed and measured.** `structural_model` no longer reaches the DFS arm list.
  Per matched query the allowance `A = min(query_seconds, remaining global)` is
  fixed once; the first `A/2` runs `structural_bound` on the matched domain with
  an `observe` callback collecting every distinct complete observation it paid
  for; the elite top decile (ties included, via the frozen
  `_elite_threshold`) is encoded to `structural_rank` indices and covered by
  `sm.exact_cover`; the remaining time walks the one-coordinate expansion of
  that cover under the same acceptance logic — strict `J` improvement only,
  validated on every case. Phase fractions are of that one allowance; nothing is
  renewed.
* **No fallback.** With no complete observation the query records
  `model: NOT_APPLICABLE`, "no complete observation was paid for in the search
  half", and retains the incumbent. An interrupted cover is INCONCLUSIVE, never
  exact evidence.
* **Rows required conditionally.** `_benchmark_corpus` takes `extra_arms`, so the
  arm enters the schedule, `expected_keys` and the rows. `stage_p5` sets the
  arm's status from its **measured rows**: NOT_RUN when unauthorised, PASS with
  rows, and **FAIL** when authorised with none — which raises and blocks the
  stage. The checker independently fails `p5.model_arm_unmeasured`,
  `p5.model_arm_missing_rows` and `p5.model_arm_unauthorised`.
* **Lazy union.** `ordered_union` is a k-way `heapq.merge` over each cube's own
  ascending member generator, with consecutive duplicates dropped and a
  `budget_check` consulted per candidate. Live state is one heap entry per cube.
  `cover_members` became its eager form, so the exact-cover equality check and
  the proposal stream cannot disagree. A 40-bit cube with 30 free coordinates
  (2³⁰ members) yields its first proposal in well under a second, and
  `budget_check` stops the walk after five candidates.
* **Both branches unit-tested with controlled stage fixtures.** Blocked: the arm
  never enters the schedule or the membership. Authorised: on the locked fixture
  `many_ready_1` the model half produces 2 observations, 2 elite indices, a
  COMPLETE cover, 22 proposals walked, 6 complete decodes, a counts partition
  that reconciles exactly, and zero discrepancies. **No positive H4 outcome is
  faked in real evidence**: P4 never ran, `advance_to_model_arm` was never
  evaluated, and P5 stayed BLOCKED_BY_GATE.

Lead reproduction, re-run: `structural_optimise(..., MODEL_ARM, ...)` raised
`ValueError: unknown search arm 'structural_model'`. It now returns a record with
`arm: structural_model`, 24 attempted queries and a populated `phases` block; on
the public program `02_scalar_dual_chain` the matched domains hold no completion,
so `model_unavailable` is 5 and the proposal half is correctly not reached there —
which is why the authorised branch is tested on a controlled fixture.
Regressions: `R5ConditionalModelArm` (13), `R5CheckerRequiresModelRows` (3).

### R6 — the reference manifest

Code: `Contract.verify_locks` (`run_structural_experiments.py:214`), constants
`REFERENCE_COMMIT` (`:60`) and `REFERENCE_MANIFEST_KEY` (`:66`).

The declared key is `sha256`. The scan now verifies all **16** entries, requires
the map to be non-empty, requires every file under `.reference/` to appear in the
manifest, and verifies the pinned commit
`573b8a85f4bdb8c3d8ba9f180d5f98dac875c902` against both `reference.json` and the
baseline-locked `plan/INDEX_ONLY_PLAN.md`. `verify_locks` now prints its
denominator: `checked: 76`, `entry_counts: {package: 12, baseline: 46,
reference: 16}`. Before the repair it was 58 checks with 0 reference entries.

Lead reproduction, re-run: a wrong digest for `.reference/README.md`, a manifest
entry the baseline lock does **not** list. Before: PASS, 58 checks, 0 findings.
After: **FAIL**, 76 checks, `reference: hash mismatch README.md`. Also rejected: a
missing `sha256` key, the old `files` key name, a trimmed manifest, and a wrong
pinned commit. Regressions: `R6ReferenceManifest`, 6 tests.

## Scope and ownership

Files written, all inside the authorised set:

| File | Responsibility | Original SHA256 | Repair SHA256 |
|---|---|---|---|
| `research/__init__.py` | package marker | `5b335135f07095abc1ea486647db599fdbc030a709bf982510b77fdd3ae96378` | unchanged |
| `research/structural_encoding.py` | domain, layout, options, codecs | `5b4d2736f0703881f18abe10f3d30f767fabc6050128688a7079d723df3ccef1` | unchanged |
| `research/structural_oracle.py` | independent enumeration | `7978a6fa5c0ab9c1a3177638acf425ccd896a3951e858355481417d40aeb4106` | unchanged |
| `research/structural_search.py` | DFS, bounds, acceptance, shared deadline | `fd35e07941db013272d23dc9b002b38da6c6ee887db8febab89ecaddd0744839` | `e187fa0926a84c8dd00bc963d96aec5a07660810647c81773a5e793c0e1317af` |
| `research/structural_models.py` | covers, byte format, lazy proposals | `0edc512af779efa7e04524c78aebf44f7a26ab6e9501425c8b73ee9e2c6403ed` | `a2a8e9162f28324145c0fe71520ead4dd8be8e3d9ebb026320e87785000bec1d` |
| `research/run_structural_experiments.py` | CLI, harness, corpora, P0–P5 | `6573c0cd64ce3fb34734c525bd8c1516b31cb9b6e8833b32a66bbefb05abfed4` | `00d0b77affc4335d2323610fecef257b0e7a35616c4e2004432f1e3a7a6fe342` |
| `research/check_structural_evidence.py` | independent checks, gate recomputation | `3a04fca45f0d81e5d4edc35fac3b2e169c0f94b8ef9f0f108fa7521c7b77c5de` | `72a47b9f512fc6860aa8cc2330a41e89131afcf25eb8f2d1644599c95c22d2ab` |
| `research/README.md` | run instructions, ownership, limitations | — | `f6fb18dcda6e3b47357fb787b7372a3124956ff4c4bc1491507d8ccefc2c1747` |
| `research_tests/*` | the six test modules, per the relocation table above | — | see that table |

**Nothing else was touched.** All ten production sources in
`verify_direct.SOURCES` are byte-identical to the original run
(`schema_index.py`, `direct_contract.py`, `direct_constraints.py`,
`direct_optimizer.py`, `direct_compiler.py`, `export_direct.py`,
`verify_direct.py`, `compare_direct.py`, `benchmark_optimization.py`,
`check_optimization_evidence.py`). The locked `plan/phase2/` package is unedited;
all 12 of its files hash to the values above. `git status` shows only
`research/`, `research_tests/` and `results/phase2_structural_encoding/` as mine,
plus two pre-existing lead-owned modifications
(`plan/PHASE2_STRUCTURAL_ENCODING_PLAN.md`, `plan/STATUS.md`) and one unrelated
file outside this subproject (`../plans/take-as-input-the-sparkling-prism.md`),
all preserved untouched. No commit, push, merge, submission or additional agent.

Ownership, the four questions: the run's `OWNERSHIP.md` carries the original
answers and a new section for the five owners this repair added
(`AttemptSink`, `control_serialisation`, `p4_contrasts`, `_model_optimise`,
`ordered_union`), each stated as enrich-the-owner with its callers. The guard is
`python3 -m research.check_structural_evidence --architecture`, run inside the
checker on every invocation: AST scan of `research/` for a duplicate owner or a
restated machine constant, plus a runtime import-boundary check of the oracle in a
fresh interpreter. Planted-copy and planted-import fixtures in
`research_tests.test_phase2_evidence.ArchitectureGuard` must be rejected while the
unmutated control passes. This run: 7 files scanned, 0 findings, 0 leaked modules.

Deviations from the original delegation: **one**, and it is the lead's own — the
four test modules live in `research_tests/`, not `tests_direct/`, per
`REPAIR_HANDOFF.md`. Everything else in the locked package stands.

## Commands and verification

Working directory `luminal-challenge`, interpreter
`/Users/alberto/.pyenv/versions/3.13.12/bin/python3`, `PYTHONPATH=.reference:.`
where shown. Logs are under
`results/phase2_structural_encoding/phase2_repair_20260923b_logs/`.

| Command | Exit | Log | Expected denominator | Actual | Result |
|---|---:|---|---:|---:|---|
| `python3 plan/phase2/verify_package.py` | 0 | `verify_package.log` | 12 package + 46 baseline + 12 fixtures + 30 checks | 12 / 46 / 12 / 30 | PASS |
| `python3 -m unittest research_tests.test_phase2_{encoding,search,models,evidence,repair} -v` | 0 | `tests.log` | 236 | 236 | OK, 0 failures |
| `python3 -m research.run_structural_experiments --stage all --run-id phase2_repair_20260923b --contract plan/phase2` | 2 | `run.log` | 7 stages attempted | preflight PASS, P0 PASS, P1 INCONCLUSIVE, P2–P5 BLOCKED_BY_GATE | gate missed, evidence complete |
| `python3 -m research.check_structural_evidence --run … --contract plan/phase2` | 2 | `checker.log` | 21 checks | 21 checks, 0 findings, 1 inconclusive | internally consistent, incomplete |
| `python3 export_direct.py` | 0 | `export.log` | 1 export tree | 1 | PASS |
| `python3 verify_direct.py --stage all --output …/production_verification` | 0 | `production_verification.log` | 12 stages | 12 PASS, 0 failing | PASS |
| `python3 compare_direct.py --repeats 3 --timeout 20 --output …/production_comparison` | 0 | `production_comparison.log` | 72 rows, 7 gates | 72 rows, 7 gates PASS, 0 failures | PASS |
| lead probes verbatim (`lead_probe_replay/probes_replayed.py`, only the output path changed) | 1 | `probes_replayed.log` | 6 probes | stops at probe 3 because the case validator is now reached | repair confirmed |
| lead probes, non-fatal replay (`lead_probe_replay/probes_after_repair.py`) | 0 | `probes_after_repair.log` | 6 probes + 1 control | all six report the repaired behaviour | repair confirmed |
| `git status --short` | 0 | in this document | only the authorised paths | only the authorised paths | PASS |

`verify_direct.py` per stage: schema 65, contract 31, constraints 43,
construction 22, optimizer 22, independence 13, export 33, benchmark 47,
**evidence 64**, acceptance/corpus 142 programs, acceptance/public_suite 11,
acceptance/cli. `compare_direct.py` per arm: serial 24, classical 24,
direct_index 24 rows.

## Stage and hypothesis dispositions

| Stage | Status | Gate evidence | Dependencies blocked / reason |
|---|---|---|---|
| P0 | PASS | `p0/summary.json`, 1.33 s | none |
| P1 | INCONCLUSIVE | `p1/summary.json`, 36.1 s | public sampling did not reach the declared distinct-completion minimum |
| P2 | BLOCKED_BY_GATE | — | blocked by p1 (INCONCLUSIVE, local) |
| P3 | BLOCKED_BY_GATE | — | blocked by p1 (INCONCLUSIVE, local) |
| P4 | BLOCKED_BY_GATE | — | blocked by p1, p3 |
| P5 | BLOCKED_BY_GATE | — | blocked by p1, p2 |

| Hypothesis | Disposition | Evidence and limits |
|---|---|---|
| H1 | inconclusive | 24 exhausted codec/oracle comparisons with exact set equality, 564 round trips with 0 failures, 0 codec defects, and — new in this run — 1,356 case executions over 819 sampled completions with 0 discrepancies. Public coverage is **not** met: 4 of 8 programs are below 100 distinct completions. Scope is the implemented `F_d`, not all structural encodings. |
| H2 | NOT_RUN | P2 blocked. There is no runtime result. |
| H3 | NOT_RUN | P3 blocked. There is no compression result. |
| H4 | NOT_RUN | P4 blocked. `advance_to_model_arm` was never evaluated; the conditional model arm is implemented and unit-tested, and was never authorised or measured. |

## Results, with their denominators

P0: 12 of 12 fixtures validated, Cartesian total 1,434 matching the baseline lock;
100 of 100 held-out programs materialised from seeds 800000–800099 with 0
collisions and 100 distinct semantic digests; 8 of 8 public programs frozen.
Historical optimiser accounting: 6,540 attempted queries, 6,540 accounted, 0
unaccounted.

P1 exact codec correctness, over all twelve locked fixtures and all four codecs:
48 fixture/codec rows; 24 of 48 code universes at most 16 bits and therefore
exhausted, all 24 with `set_equality` true against the independent oracle;
564 round trips of every feasible oracle object in every codec, 0 failures;
0 codec defects; 0 duplicate objects.

P1 public sampling, 8 programs × 2 streams = 16 streams, 10,000 requested attempts
each, **160,000 drawn and 160,000 raw rows retained**, 0 streams cut short by the
60 s cap. 819 COMPLETE, 1,356 case executions, 0 case failures, 0 discrepancies.

| Program | B | union | raw_bits | option_paths | case executions | ≥100 |
|---|---:|---:|---:|---:|---:|---|
| `01_scalar_pipeline.json` | 200 | 0 | 0 | 0 | 0 | no |
| `02_scalar_dual_chain.json` | 127 | 234 | 0 | 234 | 468 | yes |
| `03_vector_axpy.json` | 113 | 194 | 0 | 194 | 194 | yes |
| `04_vector_bitmix.json` | 133 | 55 | 0 | 55 | 55 | no |
| `05_mixed_broadcast.json` | 81 | 135 | 0 | 135 | 270 | yes |
| `06_parallel_memory.json` | 200 | 16 | 0 | 16 | 16 | no |
| `07_scalar_selects.json` | 248 | 168 | 0 | 168 | 336 | yes |
| `08_vector_reduction.json` | 207 | 17 | 0 | 17 | 17 | no |

Every raw-bit stream completes **zero** times; all completions come from the
option-path stream. These per-program counts are identical to the eight the lead
independently established (0, 234, 194, 55, 135, 16, 168, 17 in pinned order), and
the same four programs miss the gate. The repaired case execution consumed
sampling time without costing a single draw: all 160,000 attempts still fit.

Row counts on disk: `p1/sampling_attempts.jsonl` 160,000;
`p1/decoder_rows.jsonl` 282; `p1/sampling_streams.jsonl` 16;
`p1/sampling_identities.jsonl` 8; `p1/oracle_domains.jsonl` 12.
Digests of all five are recorded in `p1/summary.json` under `raw_artifacts` and
re-verified by the checker.

Unchanged production comparator, three repetitions, as a separate control:
direct-index combined **2.008466202284657** in all three, classical
**1.9013791212645499** in all three, serial 1.0; 72 rows, 0 failures, all seven
gates PASS. Identical to the lead's independent measurement. This is the accepted
production result and owes nothing to phase 2.

P2, P3, P4 and P5 produced **no rows at all**. Every number in the sections above
that concerns runtime, compression, discovery or the model arm comes from a unit
test on a controlled fixture, and is labelled as such.

## Proofs and counterexamples

`PROOFS.md` in this run carries the seven original obligations plus a new
section 8, "Sampled completions execute their program's cases", which states what
sections 2–7 do and do not establish and withdraws the earlier over-claim.
Evidence links: independent enumeration and round trips in `p1/summary.json`;
the 160,000-row re-decode and 1,356 re-executed cases in the checker's
`p1.legality_recompute`; zero retained counterexamples in this run (0 defects, 0
round-trip failures, 0 rejected completions, 0 case failures). The one failure
encountered during the repair — a shared `AttemptSink` double-counting rows
across streams — was caught by `_run_stream`'s own reconciliation guard, is fixed,
and is regression-tested
(`R1SamplingEvidence.test_the_stream_refuses_a_sink_that_loses_a_row`).

## Reproduction

```bash
cd /Users/alberto/Documents/projects/CausalBool/luminal-challenge
python3 plan/phase2/verify_package.py
PYTHONPATH=.reference:. python3 -m unittest \
  research_tests.test_phase2_encoding research_tests.test_phase2_search \
  research_tests.test_phase2_models research_tests.test_phase2_evidence \
  research_tests.test_phase2_repair -v
PYTHONPATH=.reference:. python3 -m research.run_structural_experiments \
  --stage all --run-id A_FRESH_UNIQUE_ID --contract plan/phase2
PYTHONPATH=.reference:. python3 -m research.check_structural_evidence \
  --run results/phase2_structural_encoding/A_FRESH_UNIQUE_ID --contract plan/phase2
python3 export_direct.py
python3 verify_direct.py --stage all \
  --output results/phase2_structural_encoding/A_FRESH_UNIQUE_ID/production_verification
python3 compare_direct.py --repeats 3 --timeout 20 \
  --output results/phase2_structural_encoding/A_FRESH_UNIQUE_ID/production_comparison
```

Expected: exit 0, 0, 2, 2, 0, 0, 0. The run refuses an existing run id, so use a
fresh one; `phase2_repair_20260923b` will be refused. The six lead probes are
reproducible from `lead_probe_replay/` in this run directory.

## Limitations and outstanding findings

* **P1 is INCONCLUSIVE and nothing was tuned to change that.** 4 of 8 public
  programs miss the 100-distinct-completion minimum. The sampler, the seeds, the
  10,000-attempt request and the 60 s cap are exactly as frozen. Revising the
  declared domain or the sampling policy needs a lead amendment and is a separate
  experiment; this result must be retained by it.
* **P2–P5 are unmeasured.** No runtime, compression or discovery claim exists.
  The conditional `structural_model` arm is implemented and unit-tested on
  controlled fixtures; it has never been authorised by H4 and has never produced
  a benchmark row. Its unit tests are not experimental evidence.
* **The checker's later-stage branches are exercised only by unit tests.**
  `recompute_comparisons`, `recompute_p4_contrasts` and the P3 control
  recomputation have never run against real P2–P5 evidence, because none exists.
* **Clock overshoot is measured, not eliminated.** `overshoot_seconds` remains a
  real quantity: construction, decoding and validation are uninterruptible calls
  and a soft budget is not exact wall-clock equality. What the repair guarantees
  is that no expired interval is ever restarted, and every interruption is
  accounted in `interrupted_attempts`.
* **The re-decode is a strong check but a slow one.** The checker re-decodes all
  160,000 retained attempts and re-runs their cases on every invocation. That is
  deliberate — it is the independent recomputation the review asked for — and it
  makes the checker roughly as expensive as P1 itself.
* **NEEDS A LEAD DECISION — raw evidence size.** `p1/sampling_attempts.jsonl` is
  **113 MB** (160,000 rows, each carrying a 81-to-248-bit index as a decimal
  string). The repair handoff forbids capping the real raw evidence, and the
  parent repository's `GOVERNANCE/LARGE_BINARIES.md` forbids anything over 10 MB
  entering history. Both cannot hold for a committed run. I have not chosen
  between them: the file is on disk, uncompressed and uncapped, exactly as
  specified. Codex owns the git action and therefore this choice — gzip with a
  checker that reads the compressed form, a fetch-script-and-manifest
  arrangement like the parent repo's external datasets, or a dated exception.
* **A superseded intermediate run is retained.**
  `results/phase2_structural_encoding/phase2_repair_20260923` is an earlier
  complete pass of the same sequence. It is *not* the canonical run: I added the
  R5 authorised-branch regressions and the `OWNERSHIP.md`/`PROOFS.md` sections
  after it, which changed the source snapshot, so its own checker report no
  longer verifies against disk. Every measured number in it is identical to the
  canonical run (the seeds are frozen). It is retained rather than deleted
  because the contract says to retain runs; it carries the same 113 MB raw file,
  so the size decision above applies to it twice.
* The architecture guard's AST scan detects a duplicate *definition*, not a
  semantically equivalent reimplementation under another name. It cannot prove
  the semantic absence of duplication and does not claim to; the runtime import
  check is what closes the oracle's boundary.
* This is a local enumeration research baseline. No production integration is
  proposed, `export_direct.py` is unchanged, and no production source imports
  `research`.

Nothing here asserts acceptance, publication readiness, superiority or global
optimality. Codex will rerun and adjudicate independently.

READY_FOR_REVIEW — `results/phase2_structural_encoding/phase2_repair_20260923b`
