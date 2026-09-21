# Luminal direct-index task status

Canonical contract: [INDEX_ONLY_PLAN.md](INDEX_ONLY_PLAN.md), version **1.1**.
Last updated: **2026-09-21**.

The repair implementation has received independent lead re-review.
**ACCEPTED**: F1, F2 and F3 are closed, including the lead-found expression-cache
regression. The final local acceptance matrix and evidence audit are recorded in
the [accepted review](../results/direct_index_v3_repair/REVIEW.md). This is local
acceptance only; no external submission or private-grader result is claimed.
Earlier reviews and worker records remain historical evidence.

### Runtime optimization — current disposition

**ACCEPTED WITH LIMITATIONS**, reviewed `1cf98da` on 2026-09-20.
[Final lead review](../results/direct_index_v4_optimization_repair2/REVIEW.md)
supersedes all optimization review dispositions below. F1/F2 are closed; fresh
340-test verification, 142 programs / 277 cases, official 72-run comparison,
600 public timing rows, 1,500 extra-corpus rows and 50 evidence checks pass.
The lead independently recomputed speedups: full 2.1320x, bootstrap 1.1629x versus
frozen v3 in this run. Earlier runs are retained; timing varies across runs and
bootstrap still misses its 1.20x target. Direct remains slower than classical.

The implementation is ready for paper drafting within the
[claims/evidence contract](../paper/CLAIMS_AND_EVIDENCE.md). No further repair or
optimization campaign is required before writing. Novelty, proofs and publication
readiness remain manuscript work. Historical records below are preserved.

### Paper draft — 2026-09-21

The internal [manuscript draft](../paper/main.pdf) is complete, with editable
[LaTeX](../paper/main.tex), six generated figure pairs, a method diagram,
mathematical arguments, primary-source context and reproduction instructions.
[Paper README](../paper/README.md) and [build validation](../paper/BUILD_VALIDATION.json)
record the deliverable. The retained evidence was re-audited: 50 checks pass.
The draft uses the accepted runs; no new timing campaign or production change
was made for writing. Independent manuscript review, novelty assessment and
publication readiness remain separate from this completed draft.

### Historical optimization reviews

**Previous re-review: CHANGES_REQUIRED**, reviewed `bb88b31` on 2026-09-20.
[Repair-round lead review](../results/direct_index_v4_optimization_repair/REVIEW.md):
R1 deadline and R2 phase-exit defects are closed. R3 remains partial: the checker
accepts a reduced resampling protocol and missing verification stages (F1/F2).
Fresh 300-test verification and the full acceptance corpus pass. The remaining
assignment is a bounded evidence-checker repair; no new optimization requested.
The preceding v4 review below is historical and superseded by this disposition.

**Previous lead verdict: CHANGES_REQUIRED**, reviewed `91be105` on 2026-09-20.
See [v4 lead review](../results/direct_index_v4_optimization/REVIEW.md) for R1–R4
and the bounded repair handoff. The full independent verification and official
comparison passed; deterministic probes found deadline and evidence-enforcement
defects. Retained timing improvements reproduce arithmetically, but v4 is not
accepted and the paper remains deferred. The planning record below is historical.

[Optimization execution plan](OPTIMIZATION_PHASE_PLAN.md), version **1.1**:
**READY_FOR_IMPLEMENTATION**, not implemented or accepted. Claude may execute
all stages through final handoff without an intermediate review. Official
optimization remains enabled; bootstrap is a measured ablation. The lead reviews
v4 independently after handoff. V3 acceptance above remains historical baseline
acceptance and does not extend to future optimization changes.

Plan review corrected the preliminary bootstrap timing's provenance, distinguished
legitimate resolution of UNKNOWN from budget bypass, fixed mode-selection
authority, and specified bounded experiments, performance criteria, ownership,
raw evidence and rerun commands. No production behavior changed in this review.

| Task | State | Owner | Evidence / next action |
|---|---|---|---|
| L00 — persistent contract and navigation | ACCEPTED | Lead | Canonical plan, agent navigation and review handoff inspected; v1.1 amendment below |
| L01 — direct schema algebra and solver | ACCEPTED | Worker (Claude Opus 5), lead review | F3 construction/solve accounting and cache regressions; v3 final verification |
| L02 — machine facts and independent corpus | ACCEPTED | Lead | Unchanged contract reviewed; 31 tests and all 142 inputs/277 cases pass; hashes verified |
| L03 — comparisons and joint constraints | ACCEPTED | Worker (Claude Opus 5), lead review | Joint constraints and F3 budget paths covered by final verification |
| L04 — independent bootstrap compiler | ACCEPTED | Worker (Claude Opus 5), lead review | 19 tests; 142/142 corpus compiles and validates |
| L05 — joint optimization | ACCEPTED | Worker (Claude Opus 5), lead review | Bounds, tradeoff fixture and source window covered by final verification |
| L06 — packaging and verification runners | ACCEPTED | Worker (Claude Opus 5), lead review | Exact membership and historical per-program integer controls |
| L07 — integration and independent review | ACCEPTED | Lead | Final 191-test verification, isolated corpus, seven comparison gates and evidence audit |

### Lead re-review — 2026-09-20

Reviewed commit `f3391b6`, plan 1.1, with two read-only scoped reviewers.
The lead reran staged verification (179 tests), 142 isolated inputs/277 cases,
and all 72 comparison runs. Direct score 2.0084662022846573; classical
1.9013791212645499 in every repetition. Real measurements have exact membership
and historical integer equality, independently verified. No production source
was changed by this review. New artifacts are in
`results/direct_index_v2_repair/lead_review/`.

Release acceptance is withheld for three reproducible P2 findings in the current
review. The worker's “all nine repaired” claim below is preserved as historical
handoff, superseded by the dispositions above. L04/L05 remain READY_FOR_REVIEW
pending shared schema and release dependencies; their specific prior findings
are closed. No method or success-gate amendment was made in this review.

### Lead amendment and review authority — 2026-09-19

Version **1.1** approves the implemented comparator split order: decreasing
significance within an operand field, decreasing absolute coordinate for ties,
zero branch first. Every split partitions the current cube exactly, so soundness
and completeness are preserved. This is an explicit amendment to section 4's
absolute-coordinate rule, not a change to method boundaries or success gates.
Affected tasks: L03/L05 and their performance evidence. Existing evidence for the
implemented field-significance order remains evidence for that implementation;
it cannot substantiate the old absolute-coordinate algorithm's performance.
No measured-result file is overwritten by this amendment.

The lead reviewed commit `2ab4fa8` with two scoped read-only reviewers and separate
reruns. Production files were not edited. Detailed task records below are the
worker's historical handoff and remain intact; the table above and REVIEW.md
supersede their pending lead decisions. L02/L04 remain READY_FOR_REVIEW because
dependency and integration gates remain open, despite passing checks. Repair
assignments and acceptance criteria are in REVIEW.md; no submission is authorized.

## Required task record when work starts

For each active task append: task ID, plan version, owner/model, exclusive files,
accepted dependencies and evidence paths, actual commands and exit codes,
source hashes, limitations, elapsed work time, and lead review verdict. Workers
may report READY_FOR_REVIEW; only the lead sets ACCEPTED.

## Task records

### L01 — direct schema algebra and solver

- **Plan version:** 1.0. **Owner:** worker agent, Claude Opus 5, working linearly
  without subagents at the user's instruction of 2026-09-19.
- **Exclusive files:** `schema_index.py`, `tests_direct/test_schema_index.py`.
  The shared `tests_direct/__init__.py` was created by this worker because no
  other agent is active; the lead should confirm that substitution.
- **Dependencies:** L00, which remains READY_FOR_REVIEW rather than ACCEPTED.
  Work proceeded on the user's explicit instruction to implement the plan as
  specified; the lead must still accept L00 retrospectively.
- **Command:** `PYTHONPATH=.reference:. python3 -m unittest tests_direct.test_schema_index`
  → **34 tests, OK, exit 0**, 1.83 s.
- **Source hashes (first 16):** `schema_index.py` `bb368a1c7dceaa07`;
  `tests_direct/test_schema_index.py` `1318004fb1c97559`.
- **Evidence:** intersection, difference and restriction are compared against
  explicit Python sets for **every** cube pair of widths zero through five,
  that is 66,430 pairs; differences are checked for disjointness as well as
  extensional equality; every returned SAT schema has **all** of its free-bit
  fillings confirmed against the whole query; interval covers are compared
  against integer predicates for every inclusive range at widths one to five.
- **Limitations:** the solver is a depth-first cube intersection without
  learning, so its worst case is exponential in the number of disjunctions and
  is bounded only by the declared budgets. That is reported as `UNKNOWN`.
- **Note for review:** one fixture defect was found and fixed during the run.
  The first time-budget fixture exhausted the *record* budget during
  construction, so the clock path was never exercised. It was replaced by an
  expression that is cheap to build and expensive to search.
- **Lead decision:** pending.

### L02 — machine facts and independent corpus

- **Plan version:** 1.0. **Owner:** as above.
- **Exclusive files:** `direct_contract.py`, `tests_direct/test_contract.py`,
  `tests_direct/generate_programs.py`.
- **Command:** `PYTHONPATH=.reference:. python3 -m unittest tests_direct.test_contract`
  → **31 tests, OK, exit 0**, 0.16 s.
- **Source hashes (first 16):** `direct_contract.py` `3b37ad0e7f5feb8a`;
  `tests_direct/test_contract.py` `44ac3321e492c2dd`;
  `tests_direct/generate_programs.py` `e6f56e70dab1d2b3`.
- **Corpus:** 142 programs — 8 public, 30 regression, 100 additional, 4 stress.
  Twenty additional programs per family; every program validated by the
  reference and confirmed to fit the starter allocation. The three scratch
  pressure fixtures each reach a peak live width of exactly 256 words, and the
  memory chain fixture holds at least 64 ordered pairs over at most 8 live words.
- **Ownership note:** `machine` remains the owner of every hardware fact and is
  imported, never restated. `common.py` derives four of the same quantities but
  is pinned by hash and barred from the production path by plan section 5.1, so
  the two owners coexist by declared exception. The drift is *measured*:
  `test_derived_facts_agree_elementwise_with_the_frozen_classical_helpers`
  compares predecessors, widths, lifetimes and bundles on four programs and
  finds zero disagreement.
- **Defects found and fixed during the run:** (i) `consumers` returned a
  multiset, counting an operation twice when it read one value for both
  arguments; (ii) the additional-program generator could stall once vector
  results filled the unique-allocation bound, since both the chosen opcode and
  the `const` fallback were refused. Two of my own boundary fixtures also
  asserted the wrong verdict and were corrected, not the code: one placed two
  stores in a single-slot cycle, and one claimed an address clash between
  intervals that do not overlap.
- **Limitations:** the starter-fit property is enforced by construction, by
  refusing any result that would push the unique vectors-first allocation past
  256 words. Programs needing genuine spilling are therefore outside the corpus,
  as they are outside the exercise.
- **Lead decision:** pending.

### L03 — comparisons and joint constraints

- **Plan version:** 1.0. **Owner:** as above.
- **Exclusive files:** `direct_constraints.py`, `tests_direct/test_constraints.py`.
- **Command:** `PYTHONPATH=.reference:. python3 -m unittest tests_direct.test_constraints`
  → **22 tests, OK, exit 0**, 2.42 s.
- **Source hashes (first 16):** `direct_constraints.py` `2587278813655706`;
  `tests_direct/test_constraints.py` `93c1693629e28dbd`.
- **Arithmetic evidence:** every cover is compared against a plain integer
  predicate at **every index of the universe**, so soundness and completeness
  are both established rather than sampled. This runs for `le`, `lt`, `eq` and
  `ne` at field widths one to five, with left offsets 0, 1, 2, 3, 4, 8 and
  negative offsets -1, -3, -8. Carries are checked not to truncate: a three-bit
  field offset by eight ranges over 8..15 and is compared against 10.
  A straddling predicate is confirmed to split rather than be dropped, and
  coordinates outside the support are confirmed to remain free.
- **Joint evidence:** twelve joint fixtures are solved and compared against
  **exhaustive enumeration** of their declared domains, judged by
  `machine.check_compilation` plus the explicit target bounds; the domain
  product is asserted to stay below 65,536. Where the returned schema has at
  most 512 fillings, every filling is checked, not only the anchor. Codes
  outside a declared time domain are individually confirmed to be rejected.
- **Encoding:** fields are laid out by increasing operation identifier — issue
  time, result address if any, then a lane bit only for two-slot engines. Lanes
  are solver auxiliaries and are never emitted. Capacity is enforced per issue,
  not for the duration of a latency: two selected operations may share a cycle
  on a two-slot engine in different lanes, and may not in the same lane; the
  single-slot store engine has no lane field at all.
- **Simplification:** a pair of values is dropped from scratch safety only when
  it is *exactly* constant — when their widest possible live intervals cannot
  overlap, or their widest possible address ranges cannot share a word.
  `end(u) < start(v)` is expanded over every consumer of `u`, never
  approximated by a selected one.
- **Note for review:** two of my own tests initially failed because they built
  an index from the fields under test alone, leaving unrelated addresses at
  zero, which tripped scratch safety for an unrelated reason. They now encode a
  complete assignment from the incumbent and vary one thing at a time. The
  production code was not changed for them. A general invariant test was added:
  each fixture's own incumbent must be accepted by its own acceptance
  expression.
- **Limitations:** the window is at most four operations and time domains are
  the incumbent plus or minus two, so an `UNSAT` result excludes a solution
  only in that neighbourhood. It is not a statement about the program.
- **Lead decision:** pending.

### L04 — independent bootstrap compiler

- **Plan version:** 1.0. **Owner:** as above.
- **Exclusive files:** `direct_compiler.py`, `tests_direct/test_construction.py`.
- **Accepted dependencies:** L01 and L02 are READY_FOR_REVIEW, not ACCEPTED.
  Downstream work proceeded on the user's instruction; the lead must still
  close those gates before L07.
- **Command:** `PYTHONPATH=.reference:. python3 -m unittest tests_direct.test_construction`
  → **19 tests, OK, exit 0**, 1.49 s.
- **Source hashes (first 16):** `direct_compiler.py` `9c80327c5d6aaf01`;
  `tests_direct/test_construction.py` `2e758a3fafdebf5f`.
- **Method:** every issue cycle and every scratch address is the minimum member
  of a queried cube cover. A scheduling query is the interval `[lower, hi]`
  minus the cycles whose engine is already full; an allocation query is the
  aligned address domain minus the exclusion range of each overlapping value.
  Each needs exactly one query, because the window is bounded by a provable
  quantity rather than by a scan: for time, `hi` is at least `h_i`, which
  section 5.2's argument shows is free and at least `lower`; for addresses the
  window covers the total occupied width and then widens to the whole domain.
- **Measured, in process, on the eight public programs:** cycle geometric mean
  **1.5099**, scratch geometric mean **2.6717**, combined **2.0085**. Against
  the frozen classical arm's recorded 1.9014 that is higher, and the gain is
  almost entirely in scratch, 2.672 against 2.420. This is an in-process
  measurement of the development module on eight programs; it is **not** the
  official figure, which L06 must produce in fresh processes over three
  repetitions using the standalone export.
- **Corpus:** all **142** programs compile, pass `machine.check_compilation`,
  and reproduce the complete final memory image on every case. Slowest is
  1.06 s for the 512-operation scalar pressure fixture, against a 15 s soft
  deadline and the 20 s external limit. Total compile time for the corpus 1.61 s.
- **Independence evidence:** the public programs still compile with
  `machine.serial_compile` patched to raise, and with `common`, `compilers`,
  `index_query`, `repertoire_program` and `doppel_challenge` made unimportable
  by a meta path blocker. None of those names appears in `sys.modules` after a
  compilation.
- **Witness evidence:** for at least twelve small fixtures, every chosen cycle
  equals the minimum found by an independent integer scan, every chosen address
  equals the minimum found by scanning all 256 words, and every cycle and
  address strictly below a choice is confirmed infeasible.
- **Limitations:** the bootstrap places operations in source identifier order,
  as the plan specifies. A priority function is not explored, and changing it
  would be a section 12 amendment. No optimiser is wired in yet; that is L05.
- **Lead decision:** pending.

### L05 — joint optimization

- **Plan version:** 1.0. **Owner:** as above.
- **Exclusive files:** `direct_optimizer.py`, `tests_direct/test_optimizer.py`.
- **Command:** `PYTHONPATH=.reference:. python3 -m unittest tests_direct.test_optimizer`
  → **18 tests, OK, exit 0**, 4.63 s. Whole suite:
  `python3 -m unittest discover -s tests_direct -p 'test_*.py'`
  → **124 tests, OK, exit 0**, 24.3 s.
- **Source hashes (first 16):** `direct_optimizer.py` `20ccca6e9f64dda8`;
  `tests_direct/test_optimizer.py` `44156e18046394e1`; `direct_constraints.py` `74f335de3b16b99a`;
  `direct_compiler.py` `57f6256783e42da7`.

**Integration edit for the lead to confirm.** Plan section 6 reserves the
wiring of L05 behind L04's interface for the lead. With no other agent active I
made that edit myself: `compile_with_report` imports `direct_optimizer` inside
the function, so the two modules do not form an import cycle, and it takes a
new keyword `optimise` that defaults to true. `compile_program` never passes
it; it exists so that the bootstrap can be measured alone.

**Measured over the whole 142-program corpus, with the optimiser enabled:**

| Outcome | Count |
|---|---:|
| SAT, validated and accepted | 7 |
| UNSAT, this neighbourhood exhausted | 178 |
| UNKNOWN, construction over budget | 8 |
| UNKNOWN, search over budget | 480 |
| Infeasible as posed | 3,197 |
| Candidate-validation discrepancies | **0** |

All 142 still compile, pass the frozen validator and reproduce the complete
final memory image. Total compile time 55.5 s for the corpus, slowest single
program 1.13 s.

**A performance defect found and fixed in L03 while measuring this.** The
split rule of section 3.3 says to split the highest relevant free coordinate.
Read as the highest *absolute* coordinate, a comparison between two fields held
at different offsets exhausts every value of whichever field sits higher in the
index before it looks at the other operand at all. A single `le` between two
eight-bit fields produced **977 cubes in 7.8 ms**, and construction then
overran its 100 ms budget on 418 queries. Splitting instead by place value
*within each field*, the usual comparator order, gives **393 cubes in 2.9 ms**.
Construction overruns fell from 418 to **8**, definite UNSAT results rose from
129 to 178, and accepted improvements from 5 to 7. Any split order yields the
same set, because each split partitions the cube; only size and cost change,
and the exhaustive index-by-index tests confirm exactness is unaltered.
**This is a literal deviation from section 3.3's wording and needs the lead's
ruling**, under section 12 change control.

**Honest negative result.** On the eight public programs the optimiser accepts
nothing: 158 of its 205 queries are infeasible as posed, because operations
outside a four-operation window already breach the target. The public score is
therefore exactly the bootstrap's. This mirrors the historical hybrid pilot,
where bounded queries also improved the classical incumbent by nothing.

**No naturally occurring cycle/memory tradeoff was found.** In all 7 accepted
improvements no metric worsens, so T05's tradeoff requirement is tested at the
level of the mechanism instead: `targets_for` is shown to emit a `(C+1, M)`
target whose product strictly improves, and the objective identity — that a
worse cycle count with a better product scores better under the official
formula — is checked directly. I did not manufacture a fixture and present it
as a discovered result.
- **Limitations:** 480 searches still exhaust the 100 ms per-query budget, so
  the optimiser's reach is limited by search cost rather than by the method. An
  UNSAT result excludes solutions only in the queried neighbourhood.
- **Lead decision:** pending.

### L06 — packaging and verification runners

- **Plan version:** 1.0. **Owner:** as above.
- **Exclusive files:** `export_direct.py`, `compare_direct.py`, `verify_direct.py`,
  `tests_direct/test_export.py`, `tests_direct/test_independence.py`.
  `SUBMISSION.md` was also prepared here; `REVIEW.md` was **not**, because only
  the lead writes that verdict.
- **Source hashes (first 16):** `export_direct.py` `984ffb653535772b`;
  `verify_direct.py` `e93c58ee5de88d93`;
  `compare_direct.py` `587777f8bbad10b3`.
- **Export:** `.build/direct_index/compiler.py`, 2,104 lines, SHA256
  `f31ac937e4d1735092ffbab93482a438b9187546dbbcde824b9f8752b7bb46c5`. Assembled from an explicit five-module allowlist in
  dependency order, carrying each constituent's hash. An audit refuses any
  export mentioning a baseline compiler, a decision diagram, a prohibited
  module, or `exec`/`eval`/`compile`; the audit is itself tested by feeding it
  sources it must reject.

**Commands and exit codes actually run.**

| Command | Result |
|---|---|
| `verify_direct.py --stage all --timeout 20` | **PASS, exit 0**, 153 s |
| `compare_direct.py --repeats 3 --timeout 20` | **exit 0**, 72 runs, 0 failures |
| `export_direct.py` | exit 0 |
| `PYTHONPATH=.reference python3 .build/direct_index/compiler.py ...` | exit 0, valid JSON |

**Verification stages.** schema 34, contract 31, constraints 22, construction
19, optimizer 18, independence 11, export 12 — **147 direct tests** — plus
acceptance: **142 programs and 277 cases** through the standalone export in one
isolated process, the **unchanged public suite at 11 tests**, and the
documented command line on all eight public programs under the 20 s limit.
**158 tests in total.** Every stage records its command, exit code and count; a
stage running zero tests or zero programs fails, and there is no unconditional
success banner.

**Official comparison, three fresh-process arms, three repetitions, rotated order.**

| Arm | Cycle | Scratch | Combined (mean) | Median compile |
|---|---:|---:|---:|---:|
| serial | 1.0000x | 1.0000x | 1.000000x | 0.022 ms |
| classical | 1.4936x | 2.4204x | 1.901379x | 0.267 ms |
| direct_index | 1.5099x | 2.6717x | **2.008466x** | 437.5 ms |

The frozen classical control reproduced `1.9013791212645499` with a difference
of **0.000e+00**, and its integer cycles and footprints match the historical
report exactly. That is the evidence that the harness measures what it claims.
The direct arm cleared 1.0 in **every** recorded repetition. Worst
whole-process time 0.70 s against the 20 s allowance.

**Stated plainly, as section 9 R05 requires:** the direct-index compiler scores
**higher** than the classical arm, 2.0085x against 1.9014x, and is about
**1,639 times slower** to run, 437.5 ms against 0.267 ms median. The gain is
almost entirely scratch, 2.672 against 2.420, not cycles.

**Two runner defects found and fixed while running this, both mine:** the
acceptance step parsed the worker's JSON from a 2,000-character tail, which
truncated a longer payload and reported zero programs checked; and the corpus
path was passed relative while the worker runs from a neutral directory, so it
found no files. Both surfaced as a FAIL rather than a false pass, which is the
behaviour the runner is meant to have.

**Isolation note.** A first attempt isolated the acceptance process by
replacing `sys.path` outright, which removed the standard library and made even
`__future__` unimportable. Isolation is now by `PYTHONPATH` plus a neutral
working directory, which leaves the standard library intact while keeping the
development tree off the path.
- **Limitations:** the comparison covers the eight public programs only; the
  private grader is unavailable and nothing is inferred about it.
- **Lead decision:** pending.

## Repair round — 2026-09-20, findings R1 to R9

Worker: Claude Opus 5, working linearly. Starting revision `2ab4fa8`, plan
version 1.1. Full record: [REPAIR_HANDOFF.md](../results/direct_index_v2_repair/REPAIR_HANDOFF.md).
The lead's review and evidence in `results/direct_index_v1/` are unchanged;
`lead_review/probes.json` was backed up before the probes were rerun and
restored byte-identically afterwards.

**All nine findings repaired, each with a regression that fails on the reviewed
behaviour.** The lead's own three probes now reproduce as failures: the silent
target discrepancy records 4 discrepancies where it recorded 0, the
always-infeasible mutation makes its test fail, and the oversized atomic cover
returns UNKNOWN instead of SAT.

| Command | Exit | Result |
|---|---:|---|
| `python3 -m unittest discover -s tests_direct` | 0 | **168 tests OK** (was 147) |
| `verify_direct.py --stage all --timeout 20` | 0 | **PASS**, 179 tests, 142 programs in 142 isolated processes, 277 cases |
| `compare_direct.py --repeats 3 --timeout 20` | 0 | 72 runs, **all six acceptance gates PASS** |

Scores, recomputed independently from all 72 raw runs and identical in every
repetition: serial 1.0000000000000000, classical 1.9013791212645499 (matching
history to 0.000e+00), direct index 2.0084662022846573. Median compile 423.9 ms
against classical's 0.271 ms, about 1,560 times slower. Export SHA256
`33386bc6ecc2dd82a1787cef9a0c04c369a7aacbbaf9e763a0313356653a376e`, 2,184 lines.

**Reported against interest:** accepted improvements across the corpus fell from
7 to 6. Restoring the missing tail window (R8) changes which windows are reached
before the 32-query cap, so some programs now exhaust the cap before the window
that previously helped. The public score is unchanged, because joint
optimisation contributes nothing there: 165 of 218 public queries are infeasible
as posed and none returns SAT.

Offered as READY_FOR_REVIEW. Nothing is self-accepted; only the lead may accept,
and no submission is authorised.

## Repair round two — 2026-09-20, findings F1 to F3

Worker: Claude Opus 5, working linearly. Starting revision `f3391b6`, plan
version 1.1. Full record:
[direct_index_v3_repair/REPAIR_HANDOFF.md](../results/direct_index_v3_repair/REPAIR_HANDOFF.md).
Both `lead_review` directories are unchanged; the lead's probe outputs were
backed up before rerun and restored byte-identically.

All three remaining findings repaired, each rejected through the real release
path rather than a forged report:

- **F1** — membership is exact, not counted. Each worker response is checked
  against the arm and program that were requested, and every
  `(arm, program, repetition)` must appear exactly once. The lead's duplicate
  scenario now reports `all_passed=False` and the CLI exits nonzero.
- **F2** — per-program serial and classical cycles and scratch are compared
  against the protected historical record. The product-preserving drift, which
  leaves every aggregate untouched, is now rejected while the aggregate gate
  still passes — which is precisely why the aggregate was insufficient.
- **F3** — expression nodes are charged as they are built, so construction
  stops at 534 records instead of returning 554; `solve` bills an expression
  once instead of 533 then 1,087; and the simplified constant and
  identical-field returns honour the clock.

| Command | Exit | Result |
|---|---:|---|
| `python3 -m unittest discover -s tests_direct` | 0 | **189 tests OK** (was 168) |
| `verify_direct.py --stage all --timeout 20` | 0 | **PASS**, 200 tests, 142 isolated processes, 277 cases |
| `compare_direct.py --repeats 3 --timeout 20` | 0 | 72 runs, **all seven gates PASS** |

Scores recomputed independently from the 72 raw measurements and identical in
every repetition: serial 1.0000000000000000, classical 1.9013791212645499,
direct index 2.0084662022846573. Export 2,255 lines, SHA256 `e30a1ed8090be9b4…`.

**Correction to the previous round's record.** That handoff attributed a decline
in accepted improvements from seven to six to the R8 window change. This round's
isolated corpus run accepted seven on the same code path, which supports the
lead's reading: the difference is run-to-run variation in time-bounded search,
not a deterministic regression. The earlier claim was wrong and is withdrawn.

Offered as READY_FOR_REVIEW. Nothing is self-accepted; no submission authorised.

## Lead re-review of round two — 2026-09-20

[direct_index_v3_repair/REVIEW.md](../results/direct_index_v3_repair/REVIEW.md).
F1, F2 and F3 are recorded CLOSED, F3 with a lead correction. The lead found a
real defect in my expression cache: `Meter.charge_expression` cached the charge
before `record()` completed and checked only the clock on a cache hit, so a
retry of an expression whose charge had failed returned SAT on an exhausted
meter. The fix checks the record cap on every entry and caches only successful
charges; two durable regressions cover it. No production-output failure was
demonstrated, because the optimiser solves once per meter — but the safeguard
was defeatable, which is exactly the class of defect this round was meant to
close.

The final rerun was completed and its results filled into the review: 191 direct
tests, verification **PASS** with 142 of 142 corpus programs in isolated
processes and 277 cases, comparison exit 0 with all seven gates, and an
independent evidence check confirming the four protected hashes, exact
measurement membership, every historical integer, and scores recomputed from raw
measurements — serial 1.0000000000000000, classical 1.9013791212645499, direct
2.0084662022846573. Export now **2,258 lines**, `c0574395d339dae3…`; the 2,255
lines and `e30a1ed8090be9b4…` recorded above belong to `7bdac4c`, before the
cache correction.

At the time this historical record was written, the verdict was pending. It was
subsequently set by the lead to **ACCEPTED** in the v3 review above. Still no
push, submission, or publication is authorized by that acceptance.

## Version and decision log

- **1.0 / 2026-09-19:** persisted the approved plan with explicit arithmetic,
  command, test-corpus, evidence, delegation, and independent-review contracts.
  User-selected boundaries: direct schemata, incremental index construction,
  correctness/runtime/serial improvement required, classical comparison reported.
  No new compiler implementation or benchmark result is claimed.

## Optimization phase — 2026-09-20, worker record

Worker: Claude Opus 5, working linearly without subagents. Plan:
[OPTIMIZATION_PHASE_PLAN.md](OPTIMIZATION_PHASE_PLAN.md) version **1.1**.
Full handoff: [direct_index_v4_optimization/REVIEW_HANDOFF.md](../results/direct_index_v4_optimization/REVIEW_HANDOFF.md).
State: **READY_FOR_REVIEW**. Not accepted; only the lead accepts. No submission,
push or publication is made or authorized.

**Baseline provenance is exact.** Every production and test source at the
starting commit `8e02cd7` was byte-identical to the accepted v3 record at
`35d2608`, and reassembling the export reproduced `c0574395d339dae3…`, 2,258
lines, exactly. All four protected hashes and the pinned reference manifest
verified.

**Owned files changed:** `schema_index.py`, `direct_constraints.py`,
`direct_optimizer.py`, `direct_compiler.py`, their three test modules, and the
new `benchmark_optimization.py`, `check_optimization_evidence.py` and
`tests_direct/test_benchmark_harness.py`. `verify_direct.py` gained one additive
stage for the new harness regressions — the single file outside the plan's
default ownership list, explained in the handoff. `direct_contract.py`,
`export_direct.py` and `compare_direct.py` are untouched.

Commits `922ed0f`, `305b9e9`, `9c6b9b6`, `20aaa1f`. This STATUS entry is
deliberately left uncommitted, because the file also carries the lead's own
uncommitted edits and plan section 7b forbids a worker committing those.

| Command | Exit | Result |
|---|---:|---|
| `python3 -m unittest discover -s tests_direct` | 0 | **253 tests OK** (was 191) |
| `verify_direct.py --stage all --timeout 20` | 0 | **PASS**, 142 of 142 programs, 277 cases |
| `compare_direct.py --repeats 3 --timeout 20` | 0 | 72 runs, **all seven gates PASS** |
| `benchmark_optimization.py --phase final --repeats 15` | 0 | 600 public + 1,500 corpus rows, 0 failures |
| `check_optimization_evidence.py` | 0 | **34 checks, 0 failing** |
| `git diff --check -- luminal-challenge` | 0 | clean |

**Both engineering targets were missed, and are reported as missed.**
Full-direct **1.9889x** against a 2.00x target (95% paired interval
1.9841–1.9913); bootstrap **1.1371x** against 1.20x (1.1334–1.1406). Both
speedups are real — the harness's own noise floor was measured at 1.0001x
(0.9996–1.0005) in the baseline phase — and both are short of target. No target
was adjusted after measurement.

**Correctness is unchanged.** Combined public score 2.008466202284657, the
accepted v3 value to within 4.4e-16, in every arm and every repetition. Every
public program's cycles and scratch are identical, so no per-program
`cycles × scratch` product moved at all. Bootstrap metrics are identical to the
freshly measured v3 bootstrap.

**Direct compilation is still not faster than classical and no such claim is
made:** about 714x slower on the full path and 2.14x on the bootstrap, improved
from 1,449x and 2.43x.

**Reported against interest.** One of the 100 frozen evaluation-corpus programs
is slower on the bootstrap path with the candidate; it is retained and reported.
The first final-phase run failed in its aggregation after measuring all 1,500
corpus rows, and is retained at `final_round1_failed/` rather than overwritten.

**A finding the lead should check directly.** The baseline showed 82.5% of
full-direct compile time going to queries that exhaust a 100 ms *wall-clock*
budget, which should have capped any constant-factor speedup near 1.21x. The
measured 1.9889x exceeds that because the budget system has two kinds of limit:
speeding up the search migrated queries from the clock to the declared
50,000-visited-cube cap, which is countable and therefore compresses. Those
searches now reach the full declared 50,000 cubes — more of the space explored,
not less — and reach it sooner. `max_visited` is unchanged in `Limits`.
Attempted queries are unchanged at 3,270 and infeasible at 2,475: no window was
skipped, no budget lowered, no search shortened, no pruning introduced.

**The optimiser is worth keeping.** It contributes nothing on the eight public
programs, but accepts 18 improvements on six of the 100 evaluation-corpus
programs, raising that corpus's score geomean from 2.362098 to 2.376597, and
eight improvements on the 142-program acceptance corpus. The recommendation is
to keep the official optimization-enabled entry point; bootstrap is reported as
an ablation only. Mode selection remains the lead's.

## Optimization repair round — 2026-09-20, findings R1 to R4

Worker: Claude Opus 5, working linearly. Responding to the
[lead review](../results/direct_index_v4_optimization/REVIEW.md), verdict
CHANGES_REQUIRED. Full record:
[direct_index_v4_optimization_repair/REPAIR_HANDOFF.md](../results/direct_index_v4_optimization_repair/REPAIR_HANDOFF.md).
State: **READY_FOR_REVIEW**. Nothing self-accepted; no submission authorised.
No new speed experiment was attempted and no target was altered.

All three blocking defects were reproduced first, then covered by a regression
that failed on the reviewed code, then repaired.

| Finding | State | Observable, before → after |
|---|---|---|
| R1 deadline bypass on a terminal verdict | **CLOSED** | `UNSAT, elapsed=2.0` → `UNKNOWN, "time budget exhausted"` |
| R2 failed control with a successful exit | **CLOSED** | exit `0` with 90 recorded discrepancies → exit `1`; silent corpus skip → exit `2` before measuring |
| R3 checker accepts corrupted evidence | **CLOSED** | 4 of 4 mutations passed → 6 of 6 rejected, control passes 42 checks |
| R4 reporting corrections | **DONE** | five corrections; the v4 handoff preserved with a supersession header only |

**R1** was the lead's finding exactly: `solve` charged a leaf's cover before
scanning it, so a scan that left no survivor and emptied the stack fell through
to `UNSAT` without reading the clock again. The clock is now read after every
leaf scan and before the terminal verdict, and the same rule was applied to
`relation_cover`, which had the same defect one level up. Granularity is bounded
by one cover scan, itself capped at `max_cover`. Visit and record caps, search
order and both v3 expression-cache retry regressions are unchanged.

**R2** is now one mandatory conjunction — membership, row validity, frozen
classical integers, per-program product nonregression, bootstrap metric
equality, score floor and evaluation-corpus presence — from which the exit
status is derived and nothing else. A missed speed target is deliberately not
in it: that is a reported outcome, not a correctness failure.

**R3** fixes the contract the checker enforces in the checker and the pinned
inputs rather than reading it from the report under examination, hashes both
exports from disk instead of trusting a stored boolean, recomputes scores,
products, aggregates, confidence intervals and target decisions from the raw
rows, recomputes stored gate flags, and audits the whole evaluation corpus. It
now also hashes the harness and itself, because both produce or audit the
numbers.

| Command | Exit | Result |
|---|---:|---|
| `python3 -m unittest discover -s tests_direct` | 0 | **300 tests OK** (was 253) |
| `verify_direct.py --stage all --timeout 20` | 0 | **PASS**, 142 of 142 programs, 277 cases |
| `compare_direct.py --repeats 3 --timeout 20` | 0 | 72 runs, **all seven gates PASS** |
| `benchmark_optimization.py --phase final --repeats 15` | 0 | 600 public + 1,500 corpus rows, **all mandatory gates PASS** |
| `check_optimization_evidence.py --root …_repair --baseline …/baseline` | 0 | **42 checks, 0 failing** |
| `git diff --check -- luminal-challenge` | 0 | clean |

**Both engineering targets remain missed, and the measured speedups fell
slightly because the R1 repair restores clock reads the defective version
skipped.** Full-direct **1.9536x** against a 2.00x target (95% paired interval
1.9503–1.9567), down from the defective 1.9889x; bootstrap **1.1380x** against
1.20x (1.1327–1.1411). Correctness bought that 1.8%, and it is reported as such.

**Correctness is unchanged.** Combined public score 2.008466202284657, the
accepted v3 value, in every arm and repetition; every public program's cycles
and scratch identical, so no per-program product moved at all.

**Reporting corrected.** The "714x slower" figure came from inverting a rounded
number and corresponds to no statistic: the labelled values are an inverted
geometric mean of per-program median ratios of **513.24x** and an inverted
pooled median of **663.38x**. The 82.5% / 1.21x ceiling was a heuristic
presented as a decomposition; it is withdrawn and replaced by a measured
per-query attribution — 62.00% of optimiser time ends at the countable
visited-cube cap, 22.68% at the clock, 15.13% completes. The claim that further
constant-factor work on the search is "ruled out" is withdrawn in full. The
final-phase direct row count is 1,680, not 2,100.

**Noted against interest.** One of the 100 evaluation-corpus programs,
`additional_351501`, is slower on the bootstrap path with the candidate. The
lead's retained `probes.py` can no longer run to completion, because
`phase_final` now refuses before measuring when the mandatory corpus is skipped
and writes no report; the equivalent updated probe is
`results/direct_index_v4_optimization_repair/reproduction/repair_probes.py`.

This STATUS entry is again left uncommitted, because the file carries the lead's
own uncommitted edits and plan section 7b forbids a worker committing those.

---

## F1/F2 evidence-only repair — READY_FOR_REVIEW (2026-09-20)

Responding to the lead re-review at
`results/direct_index_v4_optimization_repair/REVIEW.md`, verdict
CHANGES_REQUIRED at `bb88b31`. Handoff:
`results/direct_index_v4_optimization_repair2/REPAIR2_HANDOFF.md`.
Commits `3c9640b` (repair) and `1cf98da` (evidence and reporting).

**No production file was touched.** Two files changed, both evidence
instruments: `check_optimization_evidence.py` and
`tests_direct/test_evidence_checker.py`. Every production source hashes as it
did at `bb88b31` and the export is byte-identical, `d14bf39b450aaa5f…`, 2,652
lines.

**F1 closed.** The checker recomputed each paired interval with the resample
count and seed taken from the interval it was auditing, so an experiment run at
one resample was recomputed at one resample and passed. The protocol is now
fixed in the checker at 10,000 resamples and seed 20260920, checked before any
recomputation, used for every bound, aggregate and target decision; `--resamples`
is removed rather than kept for diagnostics; and target declarations must now be
complete, because an omitted one previously skipped its own comparison.

**F2 closed.** The recorded verification needed only a positive total test count
and the corpus totals, so a summary holding two records passed — and the suite's
positive fixture was that two-record summary. Twelve records are now required,
one per declared stage and per acceptance step, each checked against its own log
and against the artifacts behind its totals. The fixture is complete, explicit,
and materialises its own corpus through the verifier that owns writing it.

**Evidence.** The lead's probes reproduced both findings before any edit. The new
regressions gave 46 failures and 2 errors of 64 at `bb88b31`, with all 18
existing ones passing; they now pass 64 of 64. Verification PASS with **340
direct tests**, 142 programs and 277 cases; all seven comparison gates; every
mandatory benchmark gate; **50 evidence checks**, all passing; control passing
and **13 of 13** probe mutations rejected; `git diff --check` clean. Score
unchanged at 2.008466202284657.

**Both targets still missed and reported as missed:** full-direct **1.9471x**
against 2.00x (CI 1.9396–1.9509), bootstrap **1.1337x** against 1.20x (CI
1.1280–1.1428).

**Two reporting corrections, both against interest.** The earlier claim that both
speedups fell was wrong in direction — bootstrap rose, 1.1371x to 1.1380x — and
wrong in attribution. This round changed no production code, remeasured the same
binaries, and full-direct moved again to 1.9471x; so the figure varies between
runs, the within-run interval does not capture that, and the R1 clock reads
plausibly contribute to the earlier change without being isolated by these runs.
And the two slow classical medians were not "machine variation in the baseline
arm": `parallel_memory` and `scalar_selects` sit at roughly four times their v4
medians and have stayed there for two further rounds while the other six move by
under 2%. A step change that reproduces, cause not established.

**Noted.** The first pass of this round is retained at
`results/direct_index_v4_optimization_repair2/superseded_first_pass/`: the
fixture read `verification/corpus` before the acceptance stage had written it.
The lead's retained `probes.py` now additionally fails on hash drift against the
previous tree; the equivalent is
`results/direct_index_v4_optimization_repair2/reproduction/repair2_probes.py`,
which keeps every one of the lead's mutations and adds seven.

This STATUS entry is again left uncommitted, because the file carries the lead's
own uncommitted edits and plan section 7b forbids a worker committing those.
