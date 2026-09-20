# Luminal direct-index task status

Canonical contract: [INDEX_ONLY_PLAN.md](INDEX_ONLY_PLAN.md), version **1.0**.
Last updated: **2026-09-19**.

The current request is to persist the plan, not to implement the new compiler.
The older hybrid prototype and its passing checks do not count as completion of
the direct-index implementation tasks below.

| Task | State | Owner | Evidence / next action |
|---|---|---|---|
| L00 — persistent contract and navigation | READY_FOR_REVIEW | Lead | Plan, agent instructions, status, and README links written; document audit pending |
| L01 — direct schema algebra and solver | READY_FOR_REVIEW | Worker (Claude Opus 5) | `schema_index.py`, 34 tests pass; see record below |
| L02 — machine facts and independent corpus | READY_FOR_REVIEW | Worker (Claude Opus 5) | `direct_contract.py`, corpus of 142; 31 tests pass; see record below |
| L03 — comparisons and joint constraints | READY_FOR_REVIEW | Worker (Claude Opus 5) | `direct_constraints.py`, 22 tests pass; see record below |
| L04 — independent bootstrap compiler | READY_FOR_REVIEW | Worker (Claude Opus 5) | `direct_compiler.py`, 19 tests pass; 142/142 corpus compiles and validates; see record below |
| L05 — joint optimization | READY_FOR_REVIEW | Worker (Claude Opus 5) | `direct_optimizer.py`, 18 tests pass; 7 validated improvements over the corpus; see record below |
| L06 — packaging and verification runners | READY_FOR_REVIEW | Worker (Claude Opus 5) | Export, verification and comparison runners; `--stage all` PASS, exit 0; see record below |
| L07 — integration and independent review | PENDING | Lead | L01–L06 all offered for review; `results/direct_index_v1/REVIEW.md` is the lead's to write and has deliberately not been created |

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

## Version and decision log

- **1.0 / 2026-09-19:** persisted the approved plan with explicit arithmetic,
  command, test-corpus, evidence, delegation, and independent-review contracts.
  User-selected boundaries: direct schemata, incremental index construction,
  correctness/runtime/serial improvement required, classical comparison reported.
  No new compiler implementation or benchmark result is claimed.
