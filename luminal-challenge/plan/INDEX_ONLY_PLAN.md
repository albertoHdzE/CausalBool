# Luminal independent direct-index compiler: implementation and review contract

Version: **1.0**. Established: **2026-09-19**.

This is the canonical, self-contained execution plan for a new Luminal challenge
solution. It is intended for Luna, Claude Code, Codex, and other agents. No
conversation history is required. Implementation has **not** been completed by
writing this plan. Read [STATUS.md](STATUS.md) for actual task acceptance.

## 1. Objective and decisions already made

Build a general compiler for the pinned Luminal machine using direct Boolean
index schemata: decimal anchors, free-coordinate masks, sumandos, intersections,
restrictions, and exact witness retrieval. Compare it against the frozen classical
compiler and Luminal's frozen serial baseline.

The user explicitly selected:

1. **Direct schemata:** no BDD backend or classical solver in the new solution path.
2. **Incremental construction:** construct a first complete solution through exact
   index queries, then improve it through joint scheduling/address queries.
3. **Correct and competitive:** meet correctness and runtime requirements and
   improve the serial baseline. Beating the classical compiler is measured, not
   assumed or required for acceptance.
4. **Delegated implementation with lead review:** bounded tasks may be implemented
   by Luna or another agent; the lead independently reviews and accepts each gate.
5. **Challenge implementation first:** research-paper development, embeddings,
   Wolfram/Shannon extensions, noisy channels, and general complexity claims are
   outside this implementation.

All scheduling and allocation decisions must be obtained from direct schema
queries. Deterministic ordering of queries, bounds, and branches is allowed.
This requirement does not assert that the resulting algorithms are new or that
all Boolean constraints have compact representations.

### Completion gates

- Correctness on all eight public programs, the unchanged public test suite, and
  the independent validation corpus described below.
- A standalone `compiler.py`, Python 3.10+, standard library only apart from the
  challenge-supplied `machine` module, exporting `compile_program(program)`.
- Only schedule JSON on stdout through the CLI; diagnostics go to stderr.
- Every acceptance process completes within the official 20-second limit.
- The direct-index compiler's combined public score exceeds **1.000x** relative
  to the serial baseline in each recorded repetition.
- Honest comparison with the frozen classical compiler, including runtime.
- Lead sign-off on method independence, semantics, packaging, and evidence.

There is no required claim of global optimality, private-grader success, or
superiority to all conventional algorithms. Do not weaken a gate to obtain a
successful status; report failures and return them to the lead.

## 2. Reading order, authority, and protected material

Read in this order:

1. [Challenge agent instructions](../AGENTS.md).
2. This complete plan and [task status](STATUS.md).
3. [Canonical terminology](../../GOVERNANCE/GLOSSARY.md), especially sections 1d/1e.
4. The pinned challenge `.reference/README.md` and `.reference/machine.py`.
5. Your assigned task, its accepted dependency evidence, and owned files.

System/developer/user instructions take precedence. Within the repository, the
glossary governs terminology, the pinned machine governs hardware semantics,
and this plan governs architecture and task boundaries. A conflict must be
reported to the lead with the exact passages and code involved; workers must
not silently adopt another interpretation.

Prefer codebase-memory MCP graph tools for code discovery when available. Use
`rg` for non-code files or as a fallback when the graph tools are unavailable or
insufficient. Their unavailability is not a blocker.

### Pinned starting point

- Reference repository: `https://github.com/luminal-ai/interview`.
- Reference commit: `573b8a85f4bdb8c3d8ba9f180d5f98dac875c902`.
- The existing [reference manifest](../reference.json) pins every reference file.
- The existing classical implementation is [common.py](../common.py), including
  its helper functions; keep it unchanged.

Initial SHA256 values:

| File, relative to repository root | SHA256 |
|---|---|
| `luminal-challenge/common.py` | `5b3ae21c5a6c3a73380069ac685fdde7d3cee2fb7bc7704b610d5e24b0056fab` |
| `luminal-challenge/reference.json` | `ef6042ce4acc2cfe531d974afb666b6ad40656e15828ad5f814d6cbb338875f0` |
| `luminal-challenge/results/comparison.json` | `f070a6691c57c78395e67f4054928cddd753b5aa0265fe1386bb7da27f9cc535` |
| `GOVERNANCE/GLOSSARY.md` | `c3d0402150fefcb1e72339ef986e9f124754c2370c0c55f3c741b311795b2b3e` |

The existing hybrid uses `classical_compile()` followed by bounded BDD queries.
Its public score, and the classical score, were approximately **1.9013791213x**.
That is historical evidence, not a result of the new direct-index implementation.
The historical report remains at [results/comparison.json](../results/comparison.json).

Preserve the old prototype, tests, reports, and exported artifacts. New work uses
new modules and `results/direct_index_v1/`. Do not rewrite previous measured
results, modify reference files, or touch the unrelated 0xPARC manuscript edits.
Do not regenerate old reports merely to update their wording or source hashes.

## 3. Method contract: exact direct schemata

### 3.1 Representation and vocabulary

Use an immutable `Cube(n, anchor, free_mask)` with nonnegative integer fields;
reject booleans where integers are required. Let `U = (1 << n) - 1`.

- Coordinates are LSB-first: coordinate `i` has weight `1 << i`.
- `anchor <= U`, `free_mask <= U`, and `anchor & free_mask == 0`.
- The cube denotes `{anchor + s}` where `s` ranges over all subsets of the
  free-coordinate weights. Those fillings are its **sumandos**.
- A free coordinate is free **in that schema**. It can be a connected input.
- A family of cubes represents the union of its members' index sets.
- An index encodes candidate decisions. Decoding a field may yield a scratch
  address; the whole index itself is not a physical scratch address.
- Do not introduce finance-only terminology such as "pivot" or "residual".
- Support `n=0`: its universe contains the single empty assignment, index zero.

Printed bit patterns must label their convention. The default textual order is
`x0, x1, ...`, matching LSB-first coordinates; do not silently use a conventional
MSB-first binary string as though it had that ordering.

### 3.2 Algebra and required operations

Two equal-width cubes `a` and `b` are compatible exactly when:

```text
((a.anchor ^ b.anchor) & (U ^ (a.free_mask | b.free_mask))) == 0
```

Their nonempty intersection is:

```text
Cube(n, a.anchor | b.anchor, a.free_mask & b.free_mask)
```

All complements must be bounded by `U`; Python's unbounded `~mask` must not leak
bits outside the declared universe.

Required interfaces in `schema_index.py`:

| Interface | Contract |
|---|---|
| `intersect(a, b)` | Exact cube intersection, or `None`; reject unequal widths. |
| `difference(a, b)` | Disjoint cube cover of `a` minus `b`. |
| `restrict(cube, coordinate, value)` | Exact cofactor/fixing within the original coordinate space, or `None`. |
| `interval(field, lo, hi, n)` | Cover of the inclusive unsigned field range; other coordinates remain free. |
| `min_member(cover)` | Minimum anchor of a nonempty cover; `None` only for an empty set. |
| `solve(expression, n, budget)` | A `QueryResult` with `SAT`, `UNSAT`, or `UNKNOWN`. |

For `difference`, first test compatibility. If compatible, split on coordinates
free in `a` but fixed by `b`, in ascending coordinate order. Emit the branch
opposite `b` at each split, continue down the matching branch, and discard the
final portion inside `b`. This produces a disjoint exact difference.

`Field(name, offset, width)` identifies a contiguous bit range. Width is positive;
constant terms do not need fields. Allocate query fields deterministically by
increasing operation ID: issue time, result address if present, then lane if
needed. Bits within every field are LSB-first.

Use `Leaf(cubes)`, `AllOf(children)`, and `AnyOf(children)` expressions. `Leaf(())`
is false; a leaf containing the all-free cube is true. Maintain deterministic
child order. In a leaf, order alternatives by `(anchor, -free_mask.bit_count(),
free_mask)` and deduplicate exact duplicates. Overlapping alternatives are
permitted. Do not sum their cardinalities or assert disjointness.

Solve by lazy depth-first intersections: AND appends required children; OR
branches; a leaf intersects its cubes with the current cube. Return an accepting
cube only after every required predicate has been satisfied. Do not materialize
the Cartesian product of all constraint families or all candidate assignments.
No BDD, truth-table inversion over the full program, or external solver is
allowed in production. Bounded exhaustive enumeration is allowed in tests.

`QueryResult` carries status, optional cube, reason, elapsed time, cubes visited,
and resource counters. A `SAT` cube must be wholly inside the acceptance set.
`UNSAT` means complete exhaustion of this query's declared domains and context.
Budget exhaustion is `UNKNOWN`. An incomplete cover must never be used as though
it were a complete acceptance set.

### 3.3 Arithmetic predicates

Implement comparisons in `direct_constraints.py` over a `Field` or integer
constant, with an optional integer offset, using `le`, `lt`, `eq`, and `ne`.
Time and address arithmetic is **nonwrapping**, including `field + offset`.
Do not truncate a carry just because the underlying field has a fixed width.

Construct exact covers with min/max interval reasoning on each partial cube:

- For `lhs <= rhs`, accept if `lhs_max <= rhs_min`; reject if `lhs_min > rhs_max`.
- For `lhs < rhs`, accept if `lhs_max < rhs_min`; reject if `lhs_min >= rhs_max`.
- For equality, accept equal singleton ranges; reject disjoint ranges.
- For inequality, accept disjoint ranges; reject equal singleton ranges.
- Otherwise split the highest relevant free coordinate and recurse, zero first.
- Simplify constant expressions and identical-field comparisons before splitting.

Straddling extrema are unresolved, not false. At a fully fixed assignment the
predicate must be evaluated exactly. All coordinates outside the predicate's
support remain free. Guard construction itself with the same query budget.

## 4. Exact machine contract

Derive facts from the pinned machine. Do not reinterpret these invariants:

| Property | Required interpretation |
|---|---|
| Scratch | 256 **words**, each word 32 bits; not 256 bits. |
| Scalars / vectors | One word / eight consecutive words aligned to eight. |
| Engine capacities | Load 2, scalar 2, vector 2, store 1, flow 1 issues per cycle. |
| Latency | Determines result availability; does **not** reserve an issue slot during all in-flight cycles. |
| Data precedence | `t_child >= t_parent + latency(parent)`. Do not add the latency twice. |
| Memory precedence | Ordered overlapping memory operations satisfy `t_later >= t_earlier + 1`. |
| Value lifetime | `[producer_issue + latency, max(write_cycle, all_consumer_issue_cycles)]`, inclusive. |
| Unused results | Occupy scratch for their write cycle even if no consumer exists. |
| Reuse | Old lifetime must end strictly before the new write. Writes occur before reads in a cycle. |
| Footprint | Highest allocated end address, including alignment holes. |
| Score cycles | Number of emitted bundles, not the completion time of the last unused result. |
| Program behavior | Operations occur exactly once; no insertion, removal, rewriting, or case-specific execution. |

For memory ordering, overlapping operations on the same buffer are ordered when
at least one is a store. Two loads can reorder. Disjoint ranges can reorder.
The final compiled program must agree with the reference on the entire final
memory image, not just a chosen output value.

The 32-bit wrapping rules apply to the source program's arithmetic. Bookkeeping
for cycles, offsets, capacities, and allocation bounds uses ordinary integers.
Include stores, unused values, and external consumers when deriving constraints.

## 5. Independent construction and optimization

### 5.1 Public and internal interfaces

`direct_compiler.py` exports:

```python
compile_program(program: dict) -> dict
# Exactly the official {'scratch': {...}, 'bundles': [...]} contract.

compile_with_report(program: dict, limits=None) -> tuple[dict, dict]
# Same compilation plus diagnostics, for internal validation and comparison.
```

Input dictionaries must remain unchanged. The production dependency path may
use `machine` for documented specifications and checking but may not call
`machine.serial_compile`. It may not import `common.py`, `compilers.py`,
`index_query.py`, their classical/hybrid helpers, or a BDD/third-party solver.
`direct_contract.py` derives producers, consumers, dependencies, widths, and
lifetimes independently. It does not allocate or schedule by a baseline call.

The compiler must not inspect case values or names to choose a schedule. Buffer
sizes and static access ranges are legitimate inputs. Public operation IDs may
be used for deterministic ordering, never for hardcoded program-specific rules.

### 5.2 Bootstrap through exact index queries

Let `H0 = sum(latency(op) for op in operations)`. This is a safe **issue-time**
horizon, not a requirement that every pending write finish before the last bundle.
Process operations in source ID order. For each operation:

1. Construct a schema domain `0 <= t < H0`.
2. Intersect it with each predecessor's already known availability/order bound.
3. Subtract cycles whose engine already has its allowed number of issues.
4. Retrieve the smallest permitted cycle using `min_member`.
5. Record it and update the issue calendar.

Do not call the classical list scheduler to obtain this decision. The calendar
is bookkeeping for the predicates; the selected time is a schema-query witness.

**Required construction argument:** define `h_i` as the sum of latencies of
operations preceding `i`. Inductively every earlier chosen time satisfies
`t_j <= h_j < h_i`. All data predecessors are ready by `h_i`; ordered memory
predecessors issue before it; no earlier operation issues at `h_i`. Therefore
`h_i` is a feasible extension, and the earliest query witness exists and is at
most `h_i`. The lead must check this argument against the implemented predicates.

After all times are fixed, compute exact lifetimes. Allocate vectors first, then
scalars; within each group sort by `(live_start, producer_id)`. For each value:

1. Construct its aligned address domain `0 <= a <= 256-width`.
2. For each already assigned value with an overlapping lifetime, exclude starts
   in `[other_base-width+1, other_base+other_width-1]`, clipped to the legal domain.
3. Retrieve the smallest allowed address through the schema engine.

**Required allocation argument:** while allocating vectors, a previously unused
eight-word block is always available below the total width of vectors processed
so far. Scalars then need no alignment padding. Reuse can only reduce the needed
high-water mark. The unique-allocation width fits the documented 256-word bound.
The lead must verify this argument and the assumption from the reference contract.

The resulting compilation is the direct compiler's own incumbent. Validate it
before optimization. An unexpectedly empty bootstrap query, input corruption,
or invalid result is an implementation error, not a reason to switch to a
classical fallback. A construction timeout is a compilation failure and fails
acceptance; do not emit a partial schedule.

### 5.3 Joint improvement query

For a selected window of at most four operations, vary their issue times,
addresses of results they produce, and engine-lane choices. All other decisions
remain fixed. Build every constraint affected by these changes, including
constraints on values whose producers are outside the window.

- Time width is `max(1, (H0-1).bit_length())`; enforce actual bounds explicitly.
- Address width is eight; vectors' low three address bits are fixed to zero.
- Two-slot engines use one lane bit per selected operation; one-slot engines
  use constant lane zero. Lanes are solver auxiliaries, not emitted instructions.
- Time domains are incumbent time +/-2, clipped to `[0, min(H0,T)-1]`.
- Selected address domains contain all aligned addresses ending at or below `M`.

Build the acceptance expression in this deterministic order: domains and target
bounds, data precedence, memory precedence, engine constraints, scratch safety.
Within each group, use increasing operation/value IDs.

For engine capacity, number external operations' lanes by increasing operation
ID within each fixed engine/cycle bundle. For every relevant pair on the same
engine require `time_i != time_j OR lane_i != lane_j`. This enforces issue
capacity; do not constrain a lane for the whole instruction latency.

For values `u` and `v`, require spatial separation OR temporal separation:

```text
a_u + width_u <= a_v
OR a_v + width_v <= a_u
OR end_u < start_v
OR end_v < start_u
```

Implement `end_u < start_v` as the conjunction of `write_u < write_v` and
`issue(consumer) < write_v` for every consumer of `u`; do not approximate the
maximum by only a selected consumer. Include writes after the emitted bundle
range when computing unused-value lifetimes. Constant-true clauses can be
removed, but only after exact simplification.

Every operation must satisfy `time < T`, and every value must satisfy
`address + width <= M`, including fixed external decisions. A fixed decision
violating a target makes this query infeasible; it does not authorize silently
enlarging the window. Optimization may choose arbitrary legal addresses; the
bootstrap's smallest-address convention is not an extra legality constraint.

### 5.4 Objective, targets, and windows

For incumbent `C` bundles and footprint `S`, minimize `P=C*S`. For a fixed
program this is equivalent to maximizing its contribution to the official
combined score. Compute dependency and engine-count lower bounds for cycles;
use the widest result as a basic memory lower bound.

Try targets in this order:

```text
(C-1, S)
(C, S-1)
(C+1, floor((P-1)/(C+1)))
(C-1, min(256, floor((P-1)/(C-1))))
```

Drop undefined targets (`C-1 == 0`), duplicates, bounds below the lower bounds,
`T > H0`, invalid memory bounds, and pairs with `T*M >= P`.

For each target, generate and deduplicate these windows:

1. Four latest-issued operations, ties by increasing ID.
2. Producers of four highest-ending scratch allocations, ties by producer ID.
3. Source-ID windows of four advancing by two, retaining the final nonempty
   shorter window. Deduplicate by the tuple of sorted selected IDs.

For targets with `M < S`, try the scratch window before the time window; otherwise
use the order above. Fixed external constraints remain present in every case.

A satisfying cube already meets the requested performance criteria. Decode its
anchor, independently validate the complete compilation, and recompute actual
cycles/footprint. Accept only strict product improvement. Restart targets and
windows after acceptance. Stop after a complete unsuccessful pass, 32 attempted
queries, or the deadline. An attempted query is one whose expression construction
has started. Cache only attempted query identities `(incumbent_digest, window,
T, M)` to avoid repeating identical work.

No global optimality claim follows from an unsuccessful bounded query. No
schema-compression ratio is an acceptance gate for this implementation.

### 5.5 Budgets and failure states

Defaults, centrally defined and recorded in reports:

| Limit | Value |
|---|---:|
| Total soft compilation deadline from entry | 15 seconds |
| Optimization allowance after bootstrap | 10 seconds, capped by total remaining time |
| Per-query construction plus solution time | 100 milliseconds, capped by remaining time |
| Atomic relation cover | 4,096 cubes |
| Visited partial cubes per query | 50,000 |
| Expression records per query | 20,000 |
| Attempted improvement queries per compilation | 32 |
| External acceptance-process timeout | 20 seconds |

Use a monotonic clock. Check limits inside construction, normalization,
intersection, and branch loops; not only between queries. Reserve the remaining
headroom for validation, serialization, and process overhead. The external
timeout remains the acceptance authority; the soft deadline is not a proof of
universal runtime for arbitrary input sizes.

`UNKNOWN` during improvement preserves the existing independently validated
incumbent. A candidate-validation discrepancy blocks release and must appear in
the report, even when returning the earlier valid incumbent is operationally
possible. Never hide a defect behind fallback success.

## 6. Task ownership and execution gates

Use Luna (`gpt-5.6-luna`) for bounded worker tasks where available, or another
agent following the same contract. The lead owns architecture, coordination,
integration, and acceptance. Model choice does not change any gate.

Paths in this table are relative to `luminal-challenge/`.

| ID | Owner and exclusive files | Deliverable | Dependencies and acceptance |
|---|---|---|---|
| L00 | Lead: this plan, `AGENTS.md`, `plan/STATUS.md`, README navigation | Persist the contract, pin existing evidence, and make it discoverable | Document/link/status audit; no implementation is implied |
| L01 | Worker: `schema_index.py`, `tests_direct/test_schema_index.py` | Cube algebra, fields, expressions, budgets, direct query solving | L00; exhaustive small-domain operation and witness tests |
| L02 | Worker: `direct_contract.py`, `tests_direct/test_contract.py`, `tests_direct/generate_programs.py` | Machine facts and independent deterministic fixtures | L00; machine-boundary tests and corpus validation |
| L03 | Worker: `direct_constraints.py`, `tests_direct/test_constraints.py` | Arithmetic covers and complete joint acceptance expressions | L01/L02 accepted; differential bounded-query tests |
| L04 | Worker: `direct_compiler.py`, `tests_direct/test_construction.py` | Complete independent bootstrap and public/internal entrypoints | L01/L02 accepted; bootstrap proof review and baseline-disabled execution |
| L05 | Worker: `direct_optimizer.py`, `tests_direct/test_optimizer.py` | Specified joint optimization policy and incumbent handling | L03/L04 accepted; improvement, tradeoff, timeout tests |
| L06 | Worker: `export_direct.py`, `compare_direct.py`, `verify_direct.py`, `tests_direct/test_export.py`, `tests_direct/test_independence.py` | Standalone export, reproducible comparison, staged acceptance runner | Frozen interfaces from L04; final integration requires L05 |
| L07 | Lead: integration edits, submission documentation, final reports | Independent scientific/engineering acceptance | All preceding tasks reviewed and accepted |

L04 initially exposes bootstrap through `compile_program`; the lead wires in L05
after both modules are accepted. L05 must not edit L04's file while L04 owns it.
L06 owns runner infrastructure; existing prototype scripts remain unchanged.
The lead creates any shared test-package initialization needed before parallel
workers start. Workers must not independently edit shared initialization files.

Waves: L00; then L01+L02; then L03+L04; then L05+L06; finally L07.
Do not exceed three simultaneous workers. If no delegation tools are available,
one agent follows the same dependency order and preserves separate review gates.

Each task moves through `PENDING -> IN_PROGRESS -> READY_FOR_REVIEW -> ACCEPTED`.
The lead can mark `CHANGES_REQUIRED` and return a task to its owner. Only the
lead marks acceptance. Downstream tasks may not rely on unaccepted behavior.

For every task, record in STATUS: owner/model, plan version, owned files,
dependency acceptance, executed commands and exit codes, evidence paths,
remaining limitations, and the lead decision. A worker's assertion that tests
passed is not a substitute for retained output and reviewer reruns.

The implementation and reviewer prompts are in sections 10 and 11. Every
delegation must include an ownership boundary and explicitly tell the worker
that other agents share the repository and their edits must not be reverted.

## 7. Required tests and independent oracles

Production predicates must not also be the only test oracle. Use Python sets
and integer arithmetic for bounded schema checks and the unchanged machine
validator/reference interpreter for compiler checks.

### T01: schema algebra and decoding

- Enumerate all cubes for widths 0 through 5. Compare intersection, difference,
  and restrictions against explicit represented sets, including every cube pair.
- Test duplicates, containment, incompatible fixed bits, empty/universal covers,
  mismatched widths, invalid anchors, and out-of-range coordinates.
- Prove differences are disjoint as well as extensionally correct.
- Test a schema with a free coordinate that belongs to a connected input.
- For every small returned SAT cube, enumerate **all** free-bit fillings and
  independently confirm that each satisfies the complete query.
- Test field decoding, LSB order, and invalid non-power-of-two domain encodings.
- Do not infer correctness only by testing one anchor from a cube.

### T02: ranges, comparisons, and resource semantics

- Exhaustively compare arithmetic covers against integer predicates for field
  widths 1 through 5, including offset values 0, 1, 2, 3, 4, and 8.
- Include operands sharing a field, constant operands, negative constant offsets,
  boundary equality, disjoint ranges, and carries beyond the field width.
- Include a predicate whose extrema straddle the boundary; it must split rather
  than be dropped. Every generated cover must be both sound and complete.
- Force time, cube, and expression limits independently. They must return
  `UNKNOWN`, not `UNSAT`, and must not expose an incomplete cover as complete.
- Include both satisfiable and fully exhausted unsatisfiable queries.

### T03: machine-boundary cases

- A consumer exactly at its producer's ready cycle is legal; one cycle earlier
  is illegal.
- Independent instructions can issue while an earlier instruction on the same
  engine remains in flight. Two-slot capacity permits two issues, not three.
- Same-cycle overlapping memory operations involving a store are illegal;
  disjoint accesses and load/load reordering remain legal.
- Equal final-read/new-write cycles prohibit scratch reuse; a write one cycle
  later permits it. Include two overlapping writes in the same cycle.
- Include unused pending writes, values with several consumers, and external
  values whose lifetime changes because a selected consumer moves.
- Test partial scalar/vector range overlap, vector alignment, exact end address
  256, footprint holes, and a value written after the last emitted issue bundle.
- Cover every opcode, unsigned comparisons, shift masking, wraparound data,
  scalar/vector selects, and the full final memory image.

### T04: independent query and construction checks

- For at least 12 small scheduling/allocation/joint fixtures, exhaust all
  combinations of the declared finite field domains when the product is at most
  65,536. Compare feasibility against the frozen machine plus explicit target
  bounds. Individually test excluded encodings for each domain as well.
- Check SAT witnesses and complete-query UNSAT results against that oracle.
- Verify bootstrap completes with `common`, hybrid modules, BDD modules, and
  `machine.serial_compile` unavailable or patched to raise on access.
- Include sparse dependencies, chains, many ready operations, memory-order
  bottlenecks, and mixed scalar/vector lifetimes.
- Verify input immutability and exact operation-ID coverage with no insertion,
  duplication, omission, or rewritten operation.
- The lead must review the two bootstrap existence arguments in section 5.2.

### T05: optimizer behavior

- Include a fixture where a valid joint time/address change meets an improving
  bound that a selected schedule-only or address-only change cannot meet. The
  independent bounded oracle must establish that distinction.
- Include a cycle/memory tradeoff: one metric worsens while `cycles*footprint`
  strictly improves. Recomputed official scoring must agree.
- Verify that changing a selected consumer updates external lifetimes.
- Verify fixed external decisions violating a target produce local infeasibility.
- Force an optimizer timeout after bootstrap and confirm that the output is the
  already validated direct-method incumbent, with UNKNOWN recorded.
- Inject an invalid candidate in a test seam: the acceptance checker must reject
  it and the release verifier must fail. Do not modify the reference validator.
- Confirm no repeated identical query and deterministic branch/window ordering.

### T06: corpus, standalone package, and independence

Run all eight public programs and their cases. Retain the existing 30 generated
programs as regression inputs; reproduce them through their existing generator,
not by changing the recorded behavior. Keep generation outside the production
compiler dependency path.

Generate an additional corpus from seeds 1000 through 1099. Assign families by
`seed % 5`: scalar, vector, mixed, dependency-heavy, memory-aliasing. Use 8, 16,
32, and 64 operations cyclically by `seed % 4`, plus any required terminating
stores. Include two cases per generated program. Use local `random.Random(seed)`.
Validate every generated program and its starter-fit property with the reference.
Do not silently discard generated failures or exclude cases because the direct
compiler performs badly. Invalid generation is a generator defect to fix and log.

Create four additional fixed stress fixtures: 256 simultaneously live scalar
results; 32 simultaneously live vector results; 16 live vectors plus 128 live
scalars; and 64 ordered overlapping load/store pairs using a small live set.
Keep earlier results live by placing their consuming stores after the creation
phase. Verify the reference confirms the intended footprint/ordering properties.

Record corpus hashes before benchmarking the completed direct compiler. The
acceptance corpus therefore contains eight public, 30 regression, 100 additional,
and four stress programs: **142 programs**, plus the targeted unit fixtures.

The standalone export must pass the unchanged public suite and corpus in fresh
processes that can import only the standard library and supplied `machine`
module. Test actual JSON CLI output, stderr separation, process exit codes,
source input immutability, and the external 20-second timeout.

Method-independence tests must combine:

- AST/import inspection for prohibited production dependencies and embedded
  classical/serial/BDD code in the export.
- Runtime import/call guards, including a raising `machine.serial_compile`.
- Behavior checks proving both bootstrap and optimization still operate under
  those guards.
- A lead source walkthrough from `compile_program` to every schedule/address
  decision. Renaming a classical routine does not satisfy independence.

## 8. Commands, evidence, and comparison contract

### 8.1 Commands available before implementation

Run commands from the `luminal-challenge/` directory. The following preflight is
available now and must pass before implementation and final acceptance:

```sh
python3 - <<'PY'
import hashlib, json
from pathlib import Path
manifest = json.loads(Path('reference.json').read_text())
assert manifest['commit'] == '573b8a85f4bdb8c3d8ba9f180d5f98dac875c902'
for name, expected in manifest['sha256'].items():
    assert hashlib.sha256((Path('.reference') / name).read_bytes()).hexdigest() == expected, name
assert hashlib.sha256(Path('common.py').read_bytes()).hexdigest() == '5b3ae21c5a6c3a73380069ac685fdde7d3cee2fb7bc7704b610d5e24b0056fab'
assert hashlib.sha256(Path('results/comparison.json').read_bytes()).hexdigest() == 'f070a6691c57c78395e67f4054928cddd753b5aa0265fe1386bb7da27f9cc535'
print('Pinned reference, classical source, and historical results: PASS')
PY
```

If `.reference` is missing, restore the pinned upstream checkout and verify the
manifest before using it. Follow the environment's network-approval rules.
Never replace the pinned reference with the current branch tip without a lead
plan revision.

### 8.2 Commands to be implemented, not existing results

The following commands are **required interfaces for L06**. They do not exist
merely because they are specified here. A missing runner is an incomplete task,
not a skipped check.

```sh
PYTHONPATH=.reference python3 -m unittest discover -s tests_direct -p 'test_*.py' -v
PYTHONPATH=.reference python3 verify_direct.py --stage all --timeout 20 --output results/direct_index_v1/verification
python3 export_direct.py --output .build/direct_index/compiler.py
PYTHONPATH=.reference python3 .build/direct_index/compiler.py .reference/programs/03_vector_axpy.json
PYTHONPATH=.reference python3 compare_direct.py --repeats 3 --timeout 20 --output results/direct_index_v1/comparison
```

`verify_direct.py` supports `--stage` values `schema`, `contract`, `constraints`,
`construction`, `optimizer`, `independence`, `export`, `acceptance`, and `all`.
The first seven run their correspondingly owned test modules; `acceptance`
executes the full corpus and original public suite against the standalone export.
`all` runs every stage, assembling the export before export/acceptance checks.
Require nonzero expected test/program counts in every stage and record them.
Use nonzero process exit status for failures, unavailable prerequisites, or a
missing test stage; never print an unconditional success banner.

Before L06 exists, L01-L05 owners use unittest discovery restricted to their
owned test file. The lead uses the complete runner once it is implemented.

The exporter must assemble an explicit allowlist of the accepted direct modules
in dependency order. It must not copy the previous export, include BDD code, or
use runtime `exec` to hide a serialized dependency bundle. Record constituent
source hashes in the export. Only local artifacts are generated.

### 8.3 Comparison design

Run independent fresh-process arms:

1. `serial`: frozen `machine.serial_compile`.
2. `classical`: unchanged `common.classical_compile` and its frozen helpers.
3. `direct_index`: the new standalone export's `compile_program`.

Use three repetitions per public program and rotate arm order. Do not run other
CPU-heavy work in parallel with benchmark measurements. The benchmark may call
baselines; the direct compiler may not. Subprocess timeout includes startup,
imports, parsing, compilation, and output. Separately measure compiler-call
time and process peak RSS and state what each includes.

Validate every run before scoring it. Per program:

```text
cycle_ratio = serial_cycles / candidate_cycles
scratch_ratio = serial_scratch / candidate_scratch
combined = sqrt(geomean(cycle_ratios) * geomean(scratch_ratios))
```

Report all raw repetitions. If valid outputs differ under time limits, compute
and report each repetition's aggregate score and the range; do not keep only
the best output or fail just because scores differ. Any correctness failure,
timeout, or missing public result fails that arm's acceptance. Do not average
away failures or mix generated and public scores into the official public score.

The frozen classical public aggregate should reproduce approximately
`1.9013791212645499` within `1e-9`; integer cycles/footprints must match the
historical report exactly. Timings are machine/run dependent and need not match.
The direct score must exceed 1.0 in every recorded repetition. It need not exceed
the classical score. No result for the inaccessible private grader is inferred.

### 8.4 Evidence and release files

L06/L07 produce under `results/direct_index_v1/`:

- `verification/summary.json`: stage status, counts, commands, exit codes,
  failures, and source/export/corpus/reference hashes.
- `verification/logs/`: retained stdout/stderr for executed acceptance commands.
- `verification/corpus_manifest.json`: seeds/families, cases, expected corpus
  membership, content hashes, and reference validity/fit checks.
- `comparison/runs.json`: every measured run with correctness, cycles, footprint,
  timings, peak RSS, compiler identity, source hashes, and query status counters.
- `comparison/COMPARISON.md`: aggregates, variability, limitations, and direct vs
  classical interpretation derived from those raw runs.
- `REVIEW.md`: lead's semantic, independence, reproducibility, and release verdict.

Do not fabricate timings, counts, hashes, test passes, or review approval. Do not
equate retrieval time with construction plus retrieval. No compression ratio is
needed for success; any optional size figure must define exactly what it measures.

Prepare `.build/direct_index/compiler.py` and `SUBMISSION.md`. The latter states
the method, measured scores, limitations, unfinished work, actual time spent,
and AI assistance. The exercise requests up to four hours of development;
record actual time honestly and never assert that limit was met without evidence.
No email, push, merge, publication, or external submission is authorized by this
implementation plan. The source exercise requests that its solution not be
shared publicly; keep delivery local unless separately instructed otherwise.

## 9. Lead review: what to inspect, rerun, and reject

The lead must approach review as an independent check, not a confirmation of
worker claims. Read the accepted plan version and all task evidence before
deciding which artifacts are current. Source changes invalidate affected hashes
and require fresh tests/results; do not simply refresh hashes on old evidence.

### R01: method audit

Trace `compile_program -> bootstrap -> query primitives -> optional optimizer`.
Identify where every time and address is selected. Verify the direct schema
operations are functional participants, not a decorative encoding of a
precomputed classical schedule. Check both the development modules and export.

Reject classical/serial seeding, classical allocation calls, hidden BDD imports,
embedded solver code, lookup tables for public cases, and input-case-dependent
scheduling. Check diagnostics and timeout paths as carefully as the happy path.

### R02: mathematical and machine audit

Review the compatibility formula, bounded masks, subtraction construction,
field decoding, and comparison cover soundness/completeness. Check all free-bit
fillings in targeted tests. Independently examine the horizon and width-first
allocation existence arguments against source code.

Verify issue-only engine capacity, predecessor latency exactly once, strict
memory-order separation, inclusive live endpoints, unused writes, and external
consumer effects. Confirm spatial OR temporal safety is used, not spatial AND
temporal separation. Confirm target cycle count follows emitted bundles.

### R03: rerun matrix

| Changed subsystem | Required reruns before acceptance |
|---|---|
| Schema algebra, branching, comparison arithmetic | Schema and constraint suites, independence, all compiler acceptance cases, export, full comparison |
| Dependency/lifetime facts or joint encoding | Contract, constraints, construction, optimizer, full acceptance, export, full comparison |
| Bootstrap or optimization policy/budgets | Construction, optimizer, independence, full acceptance, export, full comparison |
| Exporter or packaging | Export/independence tests and full corpus against exported file; final comparison uses that file |
| Benchmark/scoring logic | Frozen-baseline controls and complete comparison; recheck correctness of every measured run |
| Documentation only | Links, commands vs actual CLI interfaces, statuses, and consistency with retained evidence; no blanket rerun needed |

For initial L07 acceptance, run the pinned preflight, all direct tests, the full
verification runner, and the three-repetition comparison. Retain their actual
exit statuses and outputs. A bare compiler-module test does not establish
standalone-export correctness.

### R04: evidence audit

Check that hashes match the reviewed source and exported compiler. Recalculate
combined scores from raw integer metrics. Confirm the classical baseline is
unchanged, all eight public programs appear in every repetition, and the corpus
contains all 142 expected programs. Inspect UNKNOWN counts, candidate-validation
errors, process timeouts, and omitted outputs. Investigate unusually convenient
constant runtimes or identical hand-entered summaries.

Verify the logs include all 11 original public tests without edits. A currently
passing legacy hybrid test suite does not certify the new direct compiler.
Read counterexample fixtures and at least one successful joint improvement
trace. Trace a failure/UNKNOWN path to the unchanged own-method incumbent.

### R05: final decision

Accept L07 only when every completion gate passes. State clearly if the direct
compiler is faster/slower, has a better/equal/worse score than classical, or
merely improves serial. Correctness and method purity are mandatory regardless
of speed. A failed gate means `CHANGES_REQUIRED`, with concrete source evidence,
an assigned repair owner, and the relevant rerun set. Never call the challenge
globally solved merely because a bounded query was UNSAT.

## 10. Copy-ready implementation and delegation prompts

### Coordinator implementation prompt

```text
Implement the Luminal direct-index compiler under
luminal-challenge/plan/INDEX_ONLY_PLAN.md, using its recorded version and
luminal-challenge/plan/STATUS.md as the handoff. Read luminal-challenge/AGENTS.md
first. No prior chat is needed. Implement the challenge solution and comparison;
do not resume the research-paper program.

Honor the selected method boundary: direct decimal-anchor/free-mask/sumandos
operations, no BDD or classical/serial solution path. Bootstrap through exact
incremental index queries, then use the specified joint queries. Preserve the
pinned machine, frozen classical source, historical results, and unrelated edits.

Check current source, hashes, and accepted evidence. Do not assume a file's
presence means its task passed. Run accepted dependency checks before reuse.
Delegate bounded tasks to Luna (gpt-5.6-luna) or another available agent with
exclusive ownership. Do not exceed three simultaneous workers. Tell each worker
that other agents share the repository and their edits must not be reverted.
Keep architecture and final acceptance under lead control. Use the exact
definitions, resource limits, test corpus, commands, and gates in the plan.

Record real commands, exit codes, source hashes, evidence, and elapsed work time.
UNKNOWN is not UNSAT. A classical fallback is prohibited. Worker completion
requires lead review. If a contract is inconsistent, report the precise conflict
to the lead rather than silently changing it. Never fabricate a successful
comparison or a private-grader result. Prepare the local standalone compiler,
SUBMISSION.md, and review evidence; do not submit or publish externally.
```

### Bounded worker prompt template

The coordinator fills every bracketed field before sending this prompt; a worker
must not guess its assignment from an incomplete template.

```text
Task: [L01-L06 and title]. Plan version: [version].
Read luminal-challenge/AGENTS.md and the complete canonical plan at
luminal-challenge/plan/INDEX_ONLY_PLAN.md. Then read STATUS.md.

Own only: [exact module/test paths from the task table].
Accepted dependencies and evidence: [task IDs and evidence paths].
Required interfaces/behavior: [refer to exact plan sections].
Required test commands: [owned unittest file and applicable verification stage].

You are not alone in this repository. Other agents are editing their own files.
Do not revert or overwrite their changes, edit shared files without lead
coordination, modify the reference/baseline, or change the method boundary.
No BDD, classical seeding/allocation, external solver, or public-case lookup is
allowed in the production index path. Use schema-free coordinates per schema,
LSB-first indices, issue-only engine capacity, and inclusive scratch lifetimes.

Implement only this bounded task. Verify against independent oracles specified
by the plan. Report changed files, actual test commands and exit codes, evidence
paths, unresolved issues, and any budget-exhaustion behavior. Request lead review
as READY_FOR_REVIEW. You cannot mark the task ACCEPTED. If instructions conflict,
return the exact conflict to the lead; do not invent a different architecture.
```

## 11. Copy-ready independent reviewer/resumption prompt

```text
Review the Luminal direct-index solution independently under
luminal-challenge/plan/INDEX_ONLY_PLAN.md. Read luminal-challenge/AGENTS.md and
plan/STATUS.md first. Do not trust remembered conversation, worker conclusions,
success banners, or old hybrid results as evidence for the new implementation.

Establish the accepted plan version, current source hashes, reference commit,
frozen classical hash, expected 142-program corpus, and which tasks are ready.
Review the complete source and standalone export. Trace every scheduling and
allocation decision to direct schema queries; reject classical/serial seeding,
BDD substitution, hidden fallbacks, and public-case special treatment.

Independently check cube algebra, min/max comparison cover completeness,
LSB decoding, and every filling of returned small schemata. Review the bootstrap
existence arguments. Check issue capacity versus latency, data readiness,
overlapping memory order, inclusive scratch lifetimes, unused pending writes,
external consumers, alignment, and criteria embedded in the query.

Follow section 9's rerun matrix. For initial final acceptance run the pinned
preflight, all direct tests, full verification including the exported compiler,
and the three-repetition fresh-process comparison. Recompute scores from raw
metrics. Keep public, generated, historical, and private-unavailable evidence
distinct. A missing runner, zero test count, timeout, unsupported case, stale
hash, or candidate-validation discrepancy is not a pass.

Check UNKNOWN and rollback behavior, actual compilation time, source/corpus
provenance, and all required artifacts. Do not require beating classical; do
require correctness, independent direct-index decisions, the 20-second process
limit, and public improvement over serial. Do not assert global optimality or
general complexity advantages.

Write results/direct_index_v1/REVIEW.md with findings, severity, precise file
locations, actual commands/exit codes, expected vs observed results, source
hashes, and an ACCEPTED or CHANGES_REQUIRED verdict. Repair or assign defects
within the approved scope, then rerun affected checks. Only the lead can accept
L07 and update STATUS accordingly. Report actual time and AI assistance honestly.
Do not email, push, merge, or publish the solution.
```

## 12. Change control and resumption

This document is the single implementation contract. Other task notes link to
it; they must not redefine schema semantics or hardware rules. If the lead must
correct a discovered inconsistency, record a versioned amendment, its reason,
affected tasks, and invalidated evidence in STATUS before downstream work
continues. Changes to the user-selected method boundary or success criteria
require returning that decision to the user; routine bug fixes do not.

On resumption, inspect the working tree first and preserve other work. Read
STATUS, verify accepted hashes/evidence, select the first unaccepted task whose
dependencies are accepted, and continue from that state. Do not restart the
project or overwrite previous reports merely because conversation history is
missing. Keep new experiment results separate from the preserved hybrid pilot.

Writing this plan and its navigation completes only L00. The presence of this
file is not evidence that L01-L07 have been implemented, tested, or accepted.
