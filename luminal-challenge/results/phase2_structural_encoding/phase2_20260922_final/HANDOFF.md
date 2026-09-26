# Phase 2 implementation handoff

Status: READY_FOR_REVIEW.
Implementer/model: Claude Code (Opus 5), run `phase2_20260922_final`.
Start/end time: 2026-09-22, single session.
Source HEAD: `1aef90681e3dead3ab1f560da8b7823ab66dabf4`.
Dirty diff SHA256: recorded in `manifest.json` and `inputs/working_tree.diff`.
Source snapshot SHA256: `72fad0ff0a8f6afa8743ea967e6270951e566eb8846a4b67be37cff8ecea1a50`.
Plan SHA256: `d2e5ceaef78f18bd5af6b7f7747a0335c883aad46e1c0ab8784d9126d8f7a9a5` (version 2.1).
Protocol: `luminal-phase2-2.1-contract-1`. Package and baseline locks verified: 58 files.
Run directory: `results/phase2_structural_encoding/phase2_20260922_final`.

## Headline

**P1's correctness gate passed completely; P1's public coverage gate was missed,
and that blocks P2–P5 by the contract's own stage rule.** The campaign is a
reportable inconclusive outcome, not a failure of the machinery and not a
scientific null result. There is one separate, unresolved **blocker** handed to
the lead: `BLOCKER_recorded_hashes.md`.

## Scope and ownership

New files, each with one responsibility, all on the section 2 allowlist:

| File | Responsibility |
|---|---|
| `research/__init__.py` | Package marker only |
| `research/structural_encoding.py` | Domain, fixed layout, options, encode/decode, all four codecs, canonical JSON |
| `research/structural_search.py` | DFS traversal, admissible bounds, acceptance policy |
| `research/structural_models.py` | Exact cover merge, byte format, four proposal policies |
| `research/structural_oracle.py` | Independent enumeration and hidden evaluation |
| `research/run_structural_experiments.py` | CLI, subprocess harness, corpus freeze, P0–P5 |
| `research/check_structural_evidence.py` | Independent checks, gate recomputation, ownership guard |
| `research/README.md` | Run instructions, ownership, limitations |
| `tests_direct/test_phase2_encoding.py` | Codec/domain/property tests (44) |
| `tests_direct/test_phase2_search.py` | Bounds, budgets, traversal (23) |
| `tests_direct/test_phase2_models.py` | Cover, proposals, serialization, leakage (39) |
| `tests_direct/test_phase2_evidence.py` | Harness/checker/ownership mutations (56) |

New artifacts: `results/phase2_structural_encoding/phase2_20260922_final/` and
one retained superseded run, `phase2_20260922_full` (see Deviations).

Pre-existing changes preserved, untouched: the modified
`plan/PHASE2_STRUCTURAL_ENCODING_PLAN.md` and the untracked `plan/phase2/`,
both lead-owned. `git status` shows no other modified file; `git diff HEAD
--stat` reports one changed file, the lead's plan.

The four ownership questions are answered in full in `OWNERSHIP.md`, written
into this run root. In short: the core of every reused concept was located
before any code was written; `machine`, `direct_contract`, `schema_index`,
`direct_constraints`, `direct_optimizer`, `direct_compiler`,
`tests_direct.generate_programs` and `compare_direct` are imported and called,
never restated. The executable guard is
`research/check_structural_evidence.py --architecture`: an AST scan for a second
owner of a cube type, a cover operation or a machine constant, **plus** a
runtime import-boundary check that imports the oracle in a fresh interpreter and
reads the module graph the interpreter actually built. Its planted-copy and
planted-import tests are `ArchitectureGuard` in `test_phase2_evidence.py`; the
unmutated control passes first in every one of them.

One ownership decision worth naming: `structural_encoding.issue_cycles_of` calls
`machine._collect_issue_cycles`. Three test modules and `common.py` each inline
the same bundles-to-times comprehension; the owner that also validates the
engine, duplicate and missing-operation rules while doing it is the pinned
module, so it is called rather than copied a fifth time.

**Deviations: TWO.**

1. A first complete run, `phase2_20260922_full`, is retained. Its own checker
   run detected that I had edited `research/check_structural_evidence.py` after
   the run recorded its source snapshot. Contract section 9 requires a failed
   run to be retained and a repair to receive a new run ID and snapshot, which
   is what `phase2_20260922_final` is. The provenance guard catching my own edit
   is the reason both runs exist.
2. The blocker in `BLOCKER_recorded_hashes.md`, which is not mine to resolve.

## Commands and verification

| Command | Exit | Log path | Expected denominator | Actual denominator | Result |
|---|---:|---|---:|---:|---|
| `python3 plan/phase2/verify_package.py` | 0 | stdout | 12 package + 46 baseline files, 12 fixtures, 30 checks | same | PASS |
| `python3 -m unittest tests_direct.test_phase2_encoding` | 0 | stdout | 44 tests | 44 | OK |
| `python3 -m unittest tests_direct.test_phase2_search` | 0 | stdout | 23 tests | 23 | OK |
| `python3 -m unittest tests_direct.test_phase2_models` | 0 | stdout | 39 tests | 39 | OK |
| `python3 -m unittest tests_direct.test_phase2_evidence` | 0 | stdout | 56 tests | 56 | OK |
| all four together | 0 | stdout | 162 tests | 162 | OK |
| `run_structural_experiments --stage all --run-id phase2_20260922_final` | 2 | `logs/` | 7 stages | 7 | P0 PASS, P1 INCONCLUSIVE, P2–P5 BLOCKED_BY_GATE |
| `check_structural_evidence --run … --contract plan/phase2` | 2 | `CHECKER_REPORT.json` | 14 checks | 14 | 0 findings, 1 inconclusive |
| `check_structural_evidence --architecture` | 0 | stdout | 7 modules scanned | 7 | PASS, 0 leaked |
| `python3 export_direct.py` | 0 | `logs/export.log` | 1 export | 1 | PASS |
| `python3 verify_direct.py --stage all --output …/production_verification` | **1** | `logs/production_verification.log` | 12 stages | 12 | 11 PASS, `evidence` FAIL — see blocker |
| `python3 compare_direct.py --repeats 3 --timeout 20 --output …/production_comparison` | 0 | `logs/production_comparison.log` | 72 rows, 7 gates | 72, 7 | all PASS |

Exit 2 from the runner and the checker is the contract's "incomplete mandatory
evidence", not a correctness failure. The checker distinguishes the two
explicitly: `findings` drive exit 1, `inconclusive` drives exit 2.

The 30 acceptance-matrix mutations are injected in `test_phase2_evidence.py`
against **copies** of a real run directory; no protected source is edited to
produce a failure, each injection changes exactly one thing, and
`test_00_the_unmutated_control_passes_first` asserts the control passes before
any mutation is applied. `AcceptanceMatrixCoverage.test_every_check_id_is_claimed`
asserts all 30 IDs C01–C30 are named by executable tests; it currently reports
zero unclaimed.

## Stage and hypothesis dispositions

| Stage | Status | Gate evidence | Dependencies blocked / reason |
|---|---|---|---|
| P0 | PASS | `p0/summary.json` | none |
| P1 | INCONCLUSIVE | `p1/summary.json` | public coverage below the declared minimum on 4 of 8 programs |
| P2 | BLOCKED_BY_GATE | — | P1's public coverage requirement applies before P2–P5 |
| P3 | BLOCKED_BY_GATE | — | same |
| P4 | BLOCKED_BY_GATE | — | same, and P3 did not run |
| P5 | BLOCKED_BY_GATE | — | same, and P2 did not run |

| Hypothesis | Disposition | Evidence and limits |
|---|---|---|
| H1 | **inconclusive** | Every correctness obligation is discharged: 24 exhausted codec/oracle comparisons with exact set equality, 564 round trips with 0 failures, 0 defects, origin property holding on all 12 fixtures and all 8 public programs. Coverage is what is inconclusive, not correctness. |
| H2 | not run | Blocked by P1 coverage. No runtime claim of any kind is made. |
| H3 | not run | Blocked by P1 coverage. |
| H4 | not run | Blocked by P1 coverage and by P3 not running. |

## Results

### P0 — provenance, domains and feasibility diagnostic (PASS)

* 58 locked files verified by content: 12 package, 46 baseline, plus every
  `reference.json` entry. Zero mismatches. HEAD equals the lock's
  `git_head_at_preparation`, so there is no documentation-only drift to record.
* All 12 fixtures revalidated with the pinned validator: 12 incumbents accepted,
  12 case sets checked, declared Cartesian sizes reproduced exactly
  (total 1434, matching `BASELINE_LOCK.fixture_cartesian_total`). Families
  present: scalar (8), memory (2), mixed (2) — **three** families, exactly the
  triage minimum with no margin. This is a limitation, recorded below.
* Held-out corpus frozen: seeds 800000–800099, 100 programs, exactly 20 per
  family across all five `FAMILIES`, generated solely by
  `tests_direct.generate_programs.additional_program`. **Zero collisions** —
  semantic (name excluded), full-digest, internal, or against the historical
  extra-corpus manifest whose seeds span 202158–397767.
* **Optimiser status totals recomputed from the retained raw rows** of
  `results/direct_index_v4_optimization_repair2/final/runs.json`:

  | Quantity | Value |
  |---|---:|
  | Attempted queries | 6540 |
  | INFEASIBLE | 4950 (75.69%) |
  | UNKNOWN_SEARCH | 810 |
  | UNSAT | 780 |
  | UNKNOWN_CONSTRUCTION | **0** |
  | SAT | 0 |
  | Unaccounted | **0** |

  The accounting reconciles exactly. This settles plan section 2's withdrawal of
  version 1.0's claim more sharply than the plan states it: the retained rows
  contain **zero** `UNKNOWN_CONSTRUCTION` events, so attributing attempts to
  construction difficulty is not merely uncausal, it has no numerator at all.
  `INFEASIBLE` and `UNKNOWN_CONSTRUCTION` are different events and are reported
  separately here and nowhere summed.
* The fixed decisions responsible for INFEASIBLE were identified by replaying
  the unchanged `JointQuery` on the eight public programs: 194 of 258 attempted
  constructions were infeasible, 78 because a fixed external operation issues at
  or past the target cycle and 116 because a fixed external value ends past the
  target footprint. Per-reason totals are in `p0/summary.json`.

### P1 — codec correctness and coverage (INCONCLUSIVE)

**Correctness: fully discharged.**

* Exhaustive code-universe enumeration wherever `B ≤ 16`: 24 codec/fixture
  comparisons, **exact set equality with the independent oracle in all 24**.
  Status counts reconcile against `2**B` in every case.
* Every feasible oracle object round-tripped through every codec at every width,
  including the wide `absolute` and `vector_block` layouts: **564 round trips,
  0 failures**, and `encode(decode(z)) == z` on each.
* **0 codec defects** and 0 duplicate-object findings. No fully decoded
  compilation was ever rejected by the pinned validator.
* Origin property holds under both rank codecs on all 12 fixtures, and
  `decode(0)` is the bootstrap compilation on all 8 public whole-program domains.
* The seven proof obligations are argued against the implementation in
  `PROOFS.md`, each paired with the artifact that evidences it.

**Coverage: missed, and this is the decisive result of the campaign.**

Public sampling, 8 programs × 2 streams × 10,000 attempts, seeds 20260922 and
20260923, `Random` reinitialised per program per stream. Every stream drew its
full 10,000 attempts well inside the 60-second cap, so **no stream is
time-truncated** and the evidence is complete.

| Program | B | raw COMPLETE | path COMPLETE | distinct union | ≥100 |
|---|---:|---:|---:|---:|---|
| 01_scalar_pipeline | 200 | 0 | 0 | 0 | no |
| 02_scalar_dual_chain | 127 | 0 | 234 | 234 | yes |
| 03_vector_axpy | 113 | 0 | 194 | 194 | yes |
| 04_vector_bitmix | 133 | 0 | 55 | 55 | no |
| 05_mixed_broadcast | 81 | 0 | 135 | 135 | yes |
| 06_parallel_memory | 200 | 0 | 16 | 16 | no |
| 07_scalar_selects | 248 | 0 | 168 | 168 | yes |
| 08_vector_reduction | 207 | 0 | 17 | 17 | no |

Status accounting reconciles exactly on all 16 streams:
`draws = COMPLETE + INVALID_CODE + DEAD_END + INTERRUPTED`, with no attempt
resampled invisibly. Raw-bit sampling completed **0** times on every program, as
expected of an 81- to 248-bit code universe. Option-path sampling dead-ended on
**97.66% to 100%** of draws, and every one of those dead ends occurred at a
**time** decision, never at an address decision.

The mechanism is reproducible in three lines and is recorded because it is the
finding, not an accident of sampling. On `01_scalar_pipeline`, horizon 23:
operation 0 has 23 legal cycles; choosing the legal cycle 22 leaves operations 1
and 2 still with 23 options each, and operation 3 with **zero**, because its
predecessor chain pushes it past `horizon - 1`. This is precisely the failure
mode plan section 4 warned about — "a locally legal prefix may have no legal
completion" — now measured rather than asserted, on the declared whole-program
domain that plan section 8 P1 mandates (all operations, cycles `0 .. horizon-1`,
every legal physical base, incumbent kept for ordering).

Contract section 6 makes public P1 coverage a precondition for P2–P5 and says
"Claude cannot revise its domain or sampling policy on his own"; plan section 8
P5 says missing public P1 coverage "requires a lead-reviewed amendment; it
cannot be silently waived". I therefore did not adjust the domain, the horizon,
the sampling policy or the attempt cap, and P2–P5 are marked BLOCKED_BY_GATE.

### P2–P5 — not run

No runtime, compactness or discovery number is reported anywhere in this
handoff, because none was measured.

Two components of those stages were nonetheless exercised as **unit tests**,
which section 8 authorises independently of the stage machine. They are reported
here as test outcomes, explicitly *not* as P2 or P3 evidence:

* Bound admissibility (C13): every prefix bound compared against every
  completion of that prefix on all 12 fixtures — 0 violations, 118 prefixes.
* Exhaustive search agreement: both `structural_dfs` and `structural_bound`
  reach the independent oracle's minimum objective on all 12 fixtures, with
  identical answers and the pruned arm never visiting more nodes.

## Proofs and counterexamples

`PROOFS.md` in this run root argues termination, soundness, completeness over
`F_d`, round trip, injectivity, domain equivalence and the origin property
against the implementation, and states what they do **not** establish. The
supporting artifacts are `p1/oracle_domains.jsonl` (12 independent
enumerations), `p1/decoder_rows.jsonl` (282 retained decoder rows),
`p1/sampling_streams.jsonl` (16 streams) and the per-fixture `codecs` block of
`p1/summary.json`.

No counterexample was found and none is retained, because none arose: defects 0,
round-trip failures 0, rejected completions 0.

## Reproduction

```bash
cd luminal-challenge
python3 plan/phase2/verify_package.py
PYTHONPATH=.reference:. python3 -m unittest \
  tests_direct.test_phase2_encoding tests_direct.test_phase2_search \
  tests_direct.test_phase2_models tests_direct.test_phase2_evidence -v
PYTHONPATH=.reference:. python3 -m research.run_structural_experiments \
  --stage all --run-id REVIEWER_RUN --contract plan/phase2
PYTHONPATH=.reference:. python3 -m research.check_structural_evidence \
  --run results/phase2_structural_encoding/REVIEWER_RUN --contract plan/phase2
PYTHONPATH=.reference:. python3 -m research.check_structural_evidence --architecture
python3 export_direct.py
python3 verify_direct.py --stage all --output REVIEWER_RUN/production_verification
python3 compare_direct.py --repeats 3 --timeout 20 \
  --output REVIEWER_RUN/production_comparison
```

Interpreter: CPython as recorded in `manifest.json`; platform recorded there
too. The decisive result — P1's coverage shortfall — is fully deterministic:
the seeds are frozen, no stream is time-truncated, and the four short programs
should reproduce to the exact counts in the table above.

## Limitations and outstanding findings

* **P2–P5 were not measured.** No performance, compactness or discovery claim is
  made or implied.
* **H1 is inconclusive, not supported.** Its correctness half is fully
  discharged over the implemented `F_d`; its coverage half is not established on
  half the public corpus. Completeness here means completeness over the declared
  `F_d`, never over all schedules.
* **The fixture corpus spans exactly three families** (scalar, memory, mixed),
  which equals the triage minimum with zero margin. Had P3 run, a single
  uninformative family would have made the triage report insufficient coverage.
  Additionally, several families are represented by one program in two domain
  variants, and two domain variants of one program supply no estimate of
  between-program variation within that family.
* **The declared whole-program domain is dominated by dead ends.** Between
  97.66% and 100% of uniformly sampled legal option paths fail to complete. Any
  future revision of that domain is a lead decision and creates a new run.
* **The architecture guard's static scan cannot prove semantic absence of
  duplication.** It detects a duplicate definition or a restated machine
  constant; a reimplementation under a different name passes it. The runtime
  import check is what closes the oracle's import boundary, and it is verified
  to catch a transitive import, not only a direct one.
* **Two contract readings were made explicitly** and are recorded in
  `research/README.md`: an out-of-range index raises rather than returning
  `INVALID_CODE`; and P4's matched budget would have been the three declared
  second-budgets. Neither was exercised by a measured stage.
* **`verify_direct.py --stage all` fails**, for a reason that is not a source
  drift and is not mine to fix. See `BLOCKER_recorded_hashes.md`. It requires a
  lead decision before this assignment's section 8 can be satisfied.
* **This is a local enumeration research baseline.** Wrapping enumerated points
  in cubes does not establish a new symbolic production algorithm. No production
  integration is proposed; production remains unchanged and the comparator
  reproduces the accepted score exactly.

READY_FOR_REVIEW
