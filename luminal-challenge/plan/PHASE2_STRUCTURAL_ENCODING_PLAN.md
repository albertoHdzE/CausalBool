# Luminal phase 2: structural decision encoding and schema-guided search

Version: **2.1**. Date: **2026-09-22**.
Owner: **Alberto Hernández Espinosa**. Scientific and execution specification.
Status: **DELEGATION SPECIFIED; EXPERIMENTS NOT YET RUN**.

Implementation is delegated to Claude Code under the author's instruction, with
Codex retaining independent review. The [delegation package](phase2/README.md)
and [implementation contract](phase2/IMPLEMENTATION_CONTRACT.md) fix the remaining
operational choices and provide immutable inputs. Version 2.1 clarifies fixed
bit offsets versus schedule-dependent traversal, decoder status precedence,
stage dependencies, proposal policies and multiplicity control. No experimental
result or production change accompanies this amendment.

The author authorised replacing version 1.0 with this specification. Its source
is preserved in git at `1aef906`. This revision supersedes its mathematical
claims, experiment sequence, stopping rules and implementation handoff. It
preserves the author's research question: can an encoding of compilation
choices expose reusable structure that direct index schemata can exploit?

This document specifies future research. Approval to rewrite it is not evidence
that any hypothesis has passed, nor a change to the accepted compiler. Execution
can be authorised as one bounded campaign; the gates below then govern progress
without repeated permission requests. Production integration has a separate
acceptance gate. Publication and external submission remain separate actions.

## 1. Research objective and scope

Investigate whether **state-relative coordinates for compiler decisions** improve
bounded joint scheduling and scratch-allocation search, and whether **schema
models provide additional value beyond the decoder and search policy**.

There are three independently testable contributions:

1. A precise encoding with proven soundness and a stated coverage domain.
2. A search improvement attributable to the encoding or its admissible bounds.
3. A model that discovers previously unseen, independently validated good
   compilations more efficiently than matched search without that model.

Success at one level does not establish the next. A legal decoder can be useful
without learning. A compact set can be expensive to construct. A model can
compress known solutions without discovering any new solution. Negative and
inconclusive outcomes are valid deliverables with different meanings.

The initial implementation is an isolated research path. The accepted direct
compiler, reference validator, classical comparator, frozen results and paper
remain the controls. No BDD, SAT/SMT solver, classical seed or fallback enters
the production direct path. Small exhaustive reference enumerators are allowed
only as independent experimental oracles.

Read [INDEX_ONLY_PLAN.md](INDEX_ONLY_PLAN.md),
[OPTIMIZATION_PHASE_PLAN.md](OPTIMIZATION_PHASE_PLAN.md),
[STATUS.md](STATUS.md), [AGENTS.md](../AGENTS.md), and the
[glossary](../../GOVERNANCE/GLOSSARY.md) before execution. The pinned machine
is authoritative for legality. This plan adds a research protocol; it does not
silently relax the original method or release contract.

## 2. Established evidence and its limits

The accepted baseline is v4 repair2, accepted with limitations; v3 remains the
historical optimisation baseline. Record the actual source and export hashes at
execution rather than identifying production code by the current branch name.

The retained [public comparison](../results/direct_index_v4_optimization_repair2/comparison/COMPARISON.md)
contains 72 runs: eight programs, three arms, three repetitions, zero failures.
Its [raw measurements](../results/direct_index_v4_optimization_repair2/comparison/runs.json)
report:

| Arm | Combined score relative to serial | Median compiler time |
|---|---:|---:|
| Serial | 1.000000 | 0.023 ms |
| Classical | 1.901379 | 0.270 ms |
| Direct index | 2.008466 | 174.400 ms |

These measurements imply approximately 5.63% higher composite score and a
646-fold ratio of the displayed median compile times versus classical. The
latter is a ratio of aggregate medians, not a paired geometric-mean slowdown.
Neither is a new measurement or a claim about private programs. Compiler timing
excludes interpreter startup and validation; the external process limit includes
them. Fresh comparisons must retain both measurements.

The public optimiser has produced no accepted improvement in the cited evidence;
the direct bootstrap supplies its public output quality. This does not prove
that the bootstrap is optimal or that the representation contributes nothing.
The search has limited windows, targets and budgets. Generated-corpus successes
must be reported separately and must not be counted again across repetitions as
distinct successful programs.

Version 1.0's attribution of 165 out of 218 attempts to construction difficulty
is withdrawn as a causal argument. In `direct_optimizer.optimise`, `INFEASIBLE`
means a fixed decision contradicts the requested target; `UNKNOWN_CONSTRUCTION`
means a construction budget was exhausted. They are different events. Recompute
all status totals from raw reports before using that example. Report attempted,
SAT, UNSAT, INFEASIBLE, UNKNOWN_CONSTRUCTION and UNKNOWN_SEARCH separately.
A different encoding cannot make a genuinely impossible fixed context feasible
without changing that context.

## 3. Mathematical object and machine semantics

For a validated program p, a compilation is a pair x = (t, a): an issue cycle
t_i for every operation i and a scratch base a_v for every produced value v.
Normalise emitted bundles by increasing operation ID within each engine and
omit trailing empty bundles. Lane labels are auxiliary representations of
capacity and are not part of the compilation object.

Let w_v be the value width, l_i the operation latency, and consumers(v) its
consuming operations. Define:

- write(v) = t_producer(v) + l_producer(v).
- end(v) = max({write(v)} union {t_j : j in consumers(v)}).
- live(v) = [write(v), end(v)], with **inclusive** endpoints.
- C(x) = 1 + max_i t_i, the number of emitted bundles.
- S(x) = max_v(a_v + w_v), including alignment holes.
- J(x) = C(x) S(x), the optimisation objective on the positive-footprint domain.

Every operation appears exactly once. Each engine's capacity constrains issues
in a cycle, not in-flight operations. Data readers issue no earlier than the
producer's write. Ordered overlapping memory accesses issue in strict program
order when at least one is a store. Scalars occupy one word; vectors occupy
eight consecutive words with an eight-word-aligned base. All blocks lie inside
256 words. Overlapping live intervals require disjoint address blocks. Even
unused values write and occupy memory for their write cycle. Writes precede
reads, so same-cycle last-read/new-write reuse is forbidden.

Fix a finite domain specification d = (p, incumbent, window, time domains,
address domains, fixed decisions, normalisation rule). Define F_d to be all
normalised compilations satisfying this domain and the pinned machine rules.
For an objective threshold q, define G_d(q) = {x in F_d : J(x) <= q}.
The domain and threshold are part of every result, including UNSAT.

Two study modes are permitted:

- **Matched window:** exactly the same window, external decisions, domains and
  targets as `JointQuery`. This isolates representation and search costs.
- **Expanded domain:** explicitly enlarged windows or whole-program domains.
  This evaluates practical reach, but cannot attribute gains to encoding alone.

A finite codec cannot represent all schedules with arbitrary idle cycles.
Completeness always means completeness over the declared F_d. A new domain
restriction, symmetry quotient or schedule policy must have its own name and
coverage statement. Never compare a whole-program width with a window width as
though they encoded the same objects.

## 4. Claims corrected from version 1.0

| Earlier assertion | Contract in version 2.0 |
|---|---|
| Every fixed-width bit string becomes one distinct legal compilation. | Not generally possible: a finite feasible set need not have power-of-two cardinality. Define validity and failure codes explicitly. |
| A free-list index removes address-renaming symmetry. | Ranking available addresses does not quotient renamings. Address geometry, alignment and footprint can make renamings inequivalent. |
| Legal next choices guarantee a complete solution. | A locally legal prefix may have no legal completion. Detect and report dead ends; prove extendibility before claiming their absence. |
| Constraints disappear from the search. | Option construction and state transitions enforce constraints; their computational cost remains chargeable. |
| Deterministic schemata have no parameters or estimation error. | The model has structural choices and hyperparameters. Exactness on observed examples does not imply accuracy on unseen assignments. |
| An exact cover can generate new good individuals. | An exact cover of a finite observed set generates only that set. Novel proposals require explicit generalisation or exploration. |
| A near-unit sampled cover ratio refutes structure. | Sparse observations can miss adjacent members of a large cube. This may be inadequate sampling rather than absence of structure. |
| UNKNOWN demonstrates NP-hardness. | UNKNOWN demonstrates exhaustion of a particular budget. Complexity claims require a formal problem family and proof. |
| Register allocation is uniformly NP-complete. | General allocation formulations can be hard; fixed-schedule scalar live intervals admit interval colouring. Mixed widths and joint scheduling require separate analysis. |
| All mutations remain valid and Hamming radius measures semantic distance. | Neither follows from state-relative encoding; one prefix change can reinterpret many subsequent fields. |
| Prior canonical decoders prove this construction. | They motivate the discipline. Their correctness proofs do not transfer automatically to a different object and transition system. |

The core proposal survives these corrections. Its scientific question becomes
whether paying for explicit state and domain structure yields a net benefit.
No claim of a new complexity class, universal optimality, parameter-free learning
or first-ever use of the idea is part of this plan.

## 5. Reference structural codec

### 5.1 A partial, fixed-layout encoding

The first codec is deliberately **partial** on binary strings. It provides a
well-defined coordinate system for schemata without concealing invalid codes.
For a fixed d, declare a width B and functions:

    decode_d : {0,1}^B -> F_d union {INVALID_CODE, DEAD_END}
    encode_d : F_d -> {0,1}^B

Budget interruption is a separate execution status, not a mathematical output
of these functions. A completed decode must satisfy the machine contract;
invalid binary codes are expected and counted. A decoded compilation rejected
by the independent validator is a correctness defect.

At each decision, construct a deterministic ordered option list O(s) from the
prefix state s. A fixed field stores the rank r. If O(s) is empty, return
DEAD_END. Otherwise, if r >= |O(s)|, return INVALID_CODE; else apply O(s)[r].
Choose each field width from a proven maximum option count for that field over
the declared domain, not from the observed count on one path. A constant field
needs no bits and must be handled without constructing a zero-width `si.Field`.
No modulo mapping, silent clipping, retry, default choice or ignored padding is
allowed in this codec.

Concretely, if field j has maximum option count M_j, reserve
b_j = ceil(log2(max(1, M_j))) bits and set B = sum_j b_j. Use the declared
time-domain size as a safe scheduling bound and the declared aligned address
count as a safe allocation bound. State dependence can reduce branching without
reducing these fixed widths. Measure both; do not promise a width reduction.

For example, three choices require two bits and leave rank 3 invalid. Padding
the list by duplicating an option would make decoding total at this point but
would destroy injectivity and bias uniform-bit sampling. Both designs are
possible; they are different experiments. A total decoder would additionally
need a proof that every chosen prefix can be completed, including capacity and
horizon restrictions. It is not an acceptance requirement of this first phase.

The first reference order is:

1. Assign selected issue times in increasing operation ID. Offer all values in
   that operation's declared domain that respect constraints whose participants
   are already fixed, including external operations and issue capacity. Constraints
   involving later selected operations remain obligations for later decisions.
2. Once all issue times are fixed, obtain complete lifetimes from
   `direct_contract.lifetimes`. Assign selected vector addresses first, then
   scalar addresses, in a stable order declared in the domain manifest.
   Offer every aligned in-bounds address compatible with fixed and already
   assigned live blocks. An empty list is a dead end.
3. Assemble the canonical compilation and check any remaining domain predicates.

Use increasing `(write cycle, producer ID)` within each width class for the
reference allocation order, matching the bootstrap convention. This order is
schedule-dependent but fully determined before address decoding starts.
Field offsets remain fixed: all selected time fields by operation ID, then all
selected address fields by producer ID. Traversal reads those preassigned fields;
it never repacks their offsets according to the decoded schedule.
Selected allocations must respect all fixed external allocations, including
values whose lifetime changed because a selected consumer moved.

This is a reference experiment in state-relative coordinates, not a claim to
have implemented the more ambitious online network in the author's notes. It
still searches pairs (t, a), and each complete schedule admits allocation
branches; it is not limited to one greedy allocation per schedule.

### 5.2 Proof obligations

Before scaling, supply short arguments and exhaustive small-domain checks for:

| Obligation | Required argument or evidence |
|---|---|
| Termination | A fixed finite number of decision fields; finite option lists. |
| Soundness | State invariants imply all machine rules for every completed decode. |
| Completeness over F_d | Every target x in F_d has its next choice in O(s); induction constructs its encoding. |
| Round trip | decode_d(encode_d(x)) = x for every x in F_d. |
| Injectivity | encode_d(decode_d(z)) = z for every successfully decoded z; no ignored bits or auxiliary lane multiplicity. |
| Domain equivalence | Independent enumeration yields the same normalised F_d for absolute and structural codecs. |
| Origin | If the incumbent belongs to F_d and its next choice is ordered first whenever available, decode_d(0) equals that incumbent. |

Completeness requires offering all declared locally compatible choices. Restricting
to active schedules, lowest free addresses or earliest issue times changes F_d.
Removing lane permutations is safe only with a capacity-equivalence argument.
Address canonicalisation requires a separate equivalence relation and proof that
legality and J are invariant; none is assumed here.

The intended completeness argument is constructive: follow any x in F_d in
the prescribed decision order. Its next decision belongs to its declared domain
and cannot violate a constraint against already fixed decisions, since x is
legal. It therefore appears in the option list. The unique sequence of ranks
encodes x. Soundness follows by checking each constraint once all its arguments
are fixed, with a final assertion that none remains unchecked. Injectivity
follows by induction on the deterministic prefix and distinct options. These
arguments are implementation obligations: a shortcut that removes options,
changes field layout or misses a constraint must re-establish them.

The origin property is conditional. An improvement target may exclude the
incumbent. Define the codec over an incumbent-containing domain and apply the
improvement predicate separately when studying distance from the origin.
Measure Hamming distance alongside changed decisions, changed issue cycles and
changed addresses; do not interpret it as a metric on compilation quality.

### 5.3 Online construction is a later extension

A chronological decoder must represent pending writes, remaining consumers,
current-cycle reads, memory predecessors and future reservations. A locker free
now is not necessarily free when an in-flight result arrives. Releasing at the
last read requires the inclusive endpoint rule. Scalar choices can fragment
aligned vector blocks. A capacity-feasible prefix may block future completion.

Such a decoder requires new invariants and comparison with the reference codec.
If it excludes legal schedules, report that restriction. A state-relative
free-list cannot be substituted for the current affine address field in
`JointQuery` without translating the dependent predicates. The old E-1 is
therefore withdrawn as a presumed small drop-in change.

Vector block indices, a_v = 8 b_v, are a separate static encoding ablation.
They remove misalignment codes but require exact scaled arithmetic and
nonwrapping overlap predicates. They do not justify an online decoder.

## 6. Search, bounds and verdicts

Use exact direct schema operations wherever a candidate production path claims
the canonical direct-index method. The research reference codec may enumerate
local options and small oracles may enumerate complete domains, but neither is
automatically admissible as the production solver. Integration must show how
scheduling and allocation witnesses come from direct schema queries.

Investigate deterministic branching over structural decisions, with and without
admissible lower bounds. The full compiler objective stays J = C S. Bounds can
combine a dependency/engine lower bound on C with a proven lower bound on S.
For a completed schedule, peak simultaneous live width is a scratch lower bound;
it need not be achievable under vector alignment. For a partial schedule, do
not treat lifetimes from the incumbent as immutable lower bounds.

If L_C <= C(x) and L_S <= S(x) for every completion x and both are nonnegative,
then L_C L_S <= J(x). Prune a prefix seeking strict improvement only if this
bound is at least the incumbent product. Record the bound and reason. Current
live occupancy alone is neither footprint nor necessarily a valid bound after
unassigned decisions change lifetimes. Every proposed bound must be checked
against all completions of the tiny oracle domains.

Verdicts are scoped as follows:

- SAT: a complete independently validated witness meets the declared target.
- UNSAT: the entire declared finite domain has been exhausted or excluded by
  sound bounds. Exhausting a radius excludes only that radius.
- UNKNOWN: a resource budget prevented completing the existence decision.
- INFEASIBLE: a direct fixed-context contradiction, with the reason retained;
  logically this excludes that particular query, not a broader domain.
- INVALID_CODE / DEAD_END: decoder outcomes; they are not global solver verdicts.

An unvalidated model's rejection of candidates cannot prove UNSAT. Bounded
heuristic search reports best found and budget consumed, not optimality. Report
wall time, CPU time, visited states/cubes, option-construction work, validation
work, cache costs and memory. Radius supplements these measurements; it never
replaces them. Charge construction and model building to the same budget as
search, including failed attempts.

## 7. Schema structure, learning and deconvolution

For a fixed codec, define V_d = {z : decode_d(z) is a compilation} and
A_d(q) = {z in V_d : J(decode_d(z)) <= q}. A cube is the canonical
`Cube(B, anchor, free_mask)`. Coordinates are LSB-first; free coordinates and
their sumandos belong to each schema. An exact cover K of A_d(q) satisfies:

    union(denotation(c) for c in K) = A_d(q).

A cover of observed elite indices E alone reconstructs E. Repeatedly sampling
that cover, selecting and covering cannot introduce an index outside E.
This is the key distinction between lossless deconvolution of a known repertoire
and discovery of an unknown good repertoire.

Study two separate model operations:

1. **Exact reconstruction:** on completely known small domains, build and verify
   an exact cover. This measures representability and construction cost.
2. **Proposal generalisation:** remove fixed coordinates or combine patterns
   under an explicitly frozen rule to propose unseen indices. Either certify
   the entire proposed cube against A_d(q), or mark it uncertified and validate
   each decoded candidate. Sample agreement is not a certificate.

The first conditional proposal algorithm is deterministic: start from the
training elite cover, try freeing one fixed coordinate in ascending coordinate
order, deduplicate proposed cubes, and retrieve previously unqueried members in
ascending index order under a shared budget. Record every invalid, dead-end,
nonelite and improving outcome. Compare against direct one-bit exploration from
the same training examples and against matched-budget random proposals. A more
elaborate learner requires a dated protocol amendment before its evaluation.

A deterministic cover still has model structure and design choices. Uniform
sampling from disjoint cubes weights cubes by their cardinalities; choosing
cubes uniformly induces a different distribution. Overlapping covers require
an explicit deduplication or union-sampling rule. Determinism of membership does
not eliminate sampling distributions or generalisation error.

No attractor or basin claim is needed for these experiments. Recovering an
acceptance set does not uniquely identify a Boolean network. A future dynamics
study must specify state, update map, boundary conditions, encoding of a
compilation, fixed points/cycles and basins, and then test soundness and reachability.
It needs evidence beyond a static cover. There is no theorem here that every
such dynamics is an energy-descent system or that every attractor is optimal.

## 8. Hypotheses and experimental order

The following defaults are prospective experimental choices, not measurements.
Freeze them in a machine-readable manifest before collecting confirmatory data.
Exploratory repairs retain their failed outputs and receive new run identifiers.

| ID | Question | Evidence required | Failure interpretation |
|---|---|---|---|
| H1 | Is the structural codec sound, canonical and complete over F_d? | Proof obligations plus exact tiny-domain equivalence and independent validation. | A correctness counterexample blocks dependent experiments until repaired. |
| H2 | Does it reduce total effort on matched problems? | Equal-domain, equal-budget comparisons including construction. | No practical encoding advantage under tested conditions. |
| H3 | Are good sets more compact in these coordinates than controls? | Complete-domain structure experiments and representation controls. | No demonstrated compactness for this representation/domain; not a universal impossibility. |
| H4 | Does generalisation improve discovery of unseen good compilations? | Held-out outcomes and matched no-model baselines. | Model contribution unsupported even if compression works. |

### P0 — provenance, domains and feasibility diagnostic

Record source commit, dirty diff, full hashes, interpreter/platform, pinned
reference manifest and all experimental parameters. Preserve accepted baselines.
Recompute optimiser status totals and identify the fixed decisions responsible
for INFEASIBLE cases. Freeze at least twelve tiny fixtures, including scalar,
vector, mixed-width, aliasing, unused-result and inclusive-boundary examples.
Each oracle Cartesian domain must contain at most 65,536 assignments. Record
all bounds and exact sizes before running the candidate codec.

Include cases with three and five legal choices, no legal choices, a locally
legal prefix with no completion, simultaneous last read/new write, pending
writes, fixed external consumers, alignment fragmentation and address holes.
Empty feasible domains are legitimate fixtures; an empty fixture collection or
missing measurements must refuse with exit code 2.

Deliverable: manifest, fresh baseline diagnostics and explicit task ownership.
Gate: baseline hashes and frozen integer controls agree; domain definitions and
oracle independence are reviewable.

### P1 — codec correctness and coverage

Enumerate each tiny oracle domain independently using the pinned validator;
compare complete normalised solution sets, round trips and target verdicts.
Do not call candidate transition logic from the oracle. Exhaust the codec bit
universe where B <= 16; otherwise round-trip every feasible oracle object and
add budgeted raw-bit and decision-path probes.

On all eight public programs, draw 10,000 raw strings per program using seed
20260922, and separately draw 10,000 sequential uniform-option paths per program
using seed 20260923. Use the declared whole-program domain with issue cycles
0 through facts.horizon - 1 and all legal physical scratch bases; keep the
incumbent for option ordering. This domain contains the bootstrap but can have
dead ends. The two sampling distributions are different and neither is assumed
uniform over compilations. Record attempted, completed, INVALID_CODE, DEAD_END,
interrupted, distinct compilations and multiplicities for each stream. No
retries that disappear from the denominator. Give this diagnostic 60 seconds
per program and stream; retain partial counts and label the stream incomplete
if its time cap prevents 10,000 attempts.

Check every completed compilation with `machine.check_compilation` and every
case with `machine.check_case`. Retain the offending index and full prefix trace
for every discrepancy. Zero completed decodes is inadequate evidence, not a pass;
require at least 100 distinct completed compilations per program across the two
streams or explicitly report the smaller exhaustively established F_d. Failure
to meet coverage under the cap is INCONCLUSIVE and triggers a documented domain
or sampling revision before dependent public experiments.

Gate: zero validator discrepancies, exact oracle agreement and all proof
obligations discharged for the implemented domain. Random tests support but do
not prove universal correctness. A defect refutes this implementation or claimed
invariant; it does not refute all possible structural encodings.

### P2 — representation and search attribution

Compare absolute physical fields, static compact domain ranks, vector block
indices where applicable, and state-relative ranks on identical F_d. Report B,
valid-code count where known, feasible object count, duplicate count, option
counts, decoder time and total query time. A sum of log2(option counts) along a
path is not fixed width or log2(number of leaves). No Shannon quantity becomes
a complexity measure.

Run ablations: baseline direct bootstrap; accepted full optimiser; structural
search without pruning; the same search with admissible pruning. Keep incumbent,
target policy, window policy and domain constant for the matched comparison.
Then report expanded-domain search in a separate table. Both full and bootstrap
baselines are mandatory: removing ineffective work cannot be attributed to a
better search algorithm.

Gate: H1 remains satisfied. Classify H2 as supported, unsupported or inconclusive
from the full cost/quality results. Continue the inexpensive complete-domain
structure study even if runtime has not improved; H3 is a separate question.

### P3 — complete-domain structure experiment

Use all P0 fixtures with nonempty F_d. Score every feasible object. Set q to
the smallest integer objective at which at least 10% of objects have J <= q;
include all threshold ties and report the actual count. Mark all-equal objectives
and empty sets as uninformative for elite discrimination.

Construct exact covers of A_d(q) and of 100 uniformly sampled subsets of V_d
with the same cardinality, seed 20260924. Use the same cover algorithm and
budget for every arm. Also compare absolute/static/structural representations
of the same objects. Freeze the cover procedure: start with minterms; repeatedly
merge equal-mask cubes differing in one fixed coordinate, choosing the smallest
`(coordinate, anchor, free_mask)` eligible pair, until no merge remains. Verify
exact equality and disjointness by expansion on these small universes. This is
a reproducible cover heuristic, not a minimum-cover theorem.

The primary representation measure is one declared algorithmic description
length: the length in bits of an actual deterministic lossless serialisation.
For the initial format use unsigned base-128 varints for B and cube count;
then sorted `(anchor, free_mask)` pairs as two little-endian, ceil(B/8)-byte
integers per cube, with zero padding. Reject duplicates, malformed integers,
extra bytes and nonzero padding. Compare with the same format using minterms.
Decoder and domain-manifest bytes are reported separately and included in any
claim about total standalone storage. Time and memory are separate engineering
measures, not blended into an invented complexity score. Cube count is a
structural diagnostic, with its denominator, not a second complexity definition.

A preregistered exploratory signal for proceeding with H4 is at least 20% shorter
elite-cover encoding than the median cardinality-matched control in at least
half of informative fixtures spanning three fixture families. This is a research
triage threshold, not statistical proof of novelty. Report every fixture and
its control distribution. If fewer than three families are informative, report
insufficient coverage. A missed gate suspends this model experiment; it leaves
correct encoding and search results intact.

### P4 — discovery beyond observed examples

Only after P1 and the P3 triage gate pass, split each complete small domain's
feasible objects into disjoint training/validation/test partitions using a
seeded permutation (seed 20260925; 50%/25%/25% with deterministic rounding).
Compute the elite threshold from training only. The learner sees only training
labels. Use validation only for choices explicitly listed in the manifest;
freeze them before revealing test labels. Report splits too small to support
evaluation rather than silently reallocating members.

Run the proposal procedure in section 7. Use the complete oracle only as the
hidden evaluator. Report test-set unseen proposals, unique legal proposals,
precision at the training threshold, improvement discoveries, oracle calls,
duplicates, construction time and validation time. Compare the model with an
exact empirical-cover sampler (which cannot discover unseen indices), one-bit
exploration and random proposals under the same budgets. Training objectives
and previously evaluated indices are shared fairly across arms.

Advance to large-domain model search only if the frozen test results show a
positive discovery advantage over both exploration controls under section 9's
paired analysis. For these two advancement contrasts use Bonferroni-adjusted
97.5% intervals, while retaining descriptive 95% intervals. The delegation
contract fixes the small-domain split rules and the sole large-domain model
extension before any test outcomes are observed.
If advancement intervals include no advantage, label H4 inconclusive or
unsupported and stop model expansion. Compression alone is insufficient.

### P5 — external validity and release decision

P5's non-model comparison depends on P1/P2, not on a positive P3 or P4 outcome.
Only its model arm is conditional on H4. Missing public P1 coverage blocks later
stages and requires a lead-reviewed amendment; it cannot be silently waived.

Evaluate the surviving search algorithm on the public corpus and new held-out
program families. Reuse the existing corpus generator; freeze its code and a
new manifest of seeds before candidate tuning, excluding all previous
optimisation training/evaluation seeds and duplicate program digests. Use at
least 20 new programs per existing family and report sizes and all exclusions.
The previously evaluated 20260921 corpus remains a regression corpus, not a new
untouched test set. Public programs are development evidence, not holdout data.

Release requires all canonical correctness, isolation, export, frozen control,
score and external-timeout gates, plus an independent review of the new method
boundary. Research success alone does not switch the production compiler.

## 9. Budgets, statistics and success criteria

For performance comparisons use candidate optimisation budgets of 0.01, 0.1
and 1.0 seconds per program, always including decoder/model construction and
validation used by search. The 0.1-second point is primary; other points are
sensitivity analyses. Use the same legal incumbent and budget for matched
search arms. Retain the unmodified accepted default compiler as an additional
reference arm, whose different total budget is labelled explicitly. No timeout
or existing acceptance gate is enlarged. Research oracle preprocessing time is
reported separately and can never be supplied free to the candidate solver.

Use ten fixed search seeds, 20261001 through 20261010. Deterministic methods do
not acquire ten independent solution-quality observations from repeated seeds.
Perform fifteen fresh-process timing repetitions with balanced random arm order,
seed 20261020. Log startup/import/compile/validation/process times separately;
retain all timeouts and failures. Honour the official 20-second external limit
for every compiler acceptance process; diagnostic oracle jobs use their own
explicit limits and are never reported as compiler runtime.

The primary quality endpoint is paired log(J_control / J_candidate) at the
primary budget on held-out programs, comparing against structural search without
the model for H4 and the accepted search policy for H2. Report program-level
wins/ties/losses, C and S individually, and quality-versus-time curves. Aggregate
seeds and repetitions within each program first; do not treat them as independent
programs. Report a paired 95% bootstrap interval, 10,000 resamples, seed 20261021,
resampling programs within family and weighting families equally. The scope is
the sampled families, not arbitrary compilers or the private grader. Public
results remain descriptive and receive the official three-repeat comparison.

For stochastic quality, average the paired log ratios across search seeds
within each program; repeated timing runs of the same seed are technical
replicates, averaged within that seed first. For runtime, use per-program
medians and their paired log ratios. This family-stratified interval targets
variation among the sampled programs. Also retain the optimisation contract's
paired within-program repetition bootstrap for timing uncertainty on a fixed
suite; identify the two intervals separately. At an orderly optimisation
deadline, retain the validated incumbent and count all work. A crashed process,
missing output or invalid incumbent is a failed row and blocks a success claim,
not a timing outlier or an observation to impute away.

A quality advantage requires the primary interval lower bound above zero, zero
correctness discrepancies, and all failed/incomplete runs accounted for. A
runtime advantage requires equal-or-better validated quality and a paired speedup
interval above one, with all necessary computation included. A positive estimate
with an interval crossing the null is inconclusive. Any additional confirmatory
comparisons need a prespecified multiplicity adjustment; unplanned comparisons
are exploratory. Report effect sizes even when a gate is missed.

No post-hoc corpus deletion, target change, seed search or time-budget extension
can rescue the same confirmatory run. A revised protocol creates a new run and
retains the previous one. A local optimum or a successful public example is
valuable evidence, but does not support a general superiority claim.

## 10. Ownership, evidence and implementation boundaries

The pinned `machine` module owns hardware semantics and independent acceptance.
`direct_contract` owns derived program facts, lifetimes, assembly and footprint.
`schema_index` owns cubes and exact set/query operations. `direct_constraints`
owns the existing absolute-field query. The research codec owns only its
coordinate layout, transition state and encode/decode operations; the experiment
runner owns sampling, comparison and evidence generation.

Proposed new source locations are `research/structural_encoding.py`,
`research/run_structural_experiments.py`, and dedicated tests under
`tests_direct/`. Before implementation, search for existing owners and answer:
where does each new concept live, does it already exist, why is a new owner
needed, and what executable guard prevents duplication? Reuse program facts
rather than restating machine rules. An ownership/import guard must fail when
a prohibited copy/import is deliberately planted in a temporary test fixture.
This is an architectural check, not evidence of mathematical correctness.

Write new measurements under
`results/phase2_structural_encoding/<run_id>/`; refuse overwrite. Each run keeps:

- Plan version/hash, git commit, dirty diff, full source/export/reference hashes,
  Python/platform, command, start/end times and exit codes.
- Domain/corpus manifests, seeds, budgets, arm order and actual membership keys.
- Raw per-attempt statuses and objective counts, independent validator outcomes,
  all case denominators and minimal counterexamples with traces.
- Proof notes, oracle comparisons, model bytes and construction costs.
- Per-program comparisons, analysis script/configuration, intervals and failures.
- A handoff stating supported claims, limitations and explicit gate outcomes.

The evidence checker must recompute aggregates from raw rows, reject missing or
duplicate keys, refuse empty scans, verify codec round trips and detect omitted
failures. Test it with deliberately corrupted counts, hashes, statuses, budgets,
model membership and missing programs. Keep logs and exact exit codes. No output
banner alone establishes acceptance. A timeout is retained, never dropped from
a denominator. A zero denominator is undefined, never reported as zero error.

## 11. Execution handoff and acceptance checklist

When execution is authorised, implement P0 and P1 first, then proceed through
the declared dependency gates. Stop on a correctness counterexample, preserve
it, repair in a new identified run and repeat the affected gates. Report missed
research gates without building dependent machinery. No author consultation is
needed for routine choices already fixed here; scientific scope changes require
a dated amendment before collecting the affected confirmatory data.

The final reviewer checks:

1. The exact object, finite domain and objective are explicit and immutable
   within a comparison; oracle and candidate have independent acceptance paths.
2. No totality, symmetry, completeness or optimality claim exceeds its proof.
3. Invalid codes, dead ends, incomplete searches and defects remain distinct.
4. Address lifetimes include external consumers, unused results and pending
   writes; code widths and vector scaling introduce no arithmetic truncation.
5. Model novelty is tested on unseen indices; exact reconstruction is not
   mistaken for generalisation; overlap and sampling bias are disclosed.
6. Construction, certification, validation and duplicate work are paid for.
7. Matched-domain and expanded-domain results remain distinguishable; both
   bootstrap and full accepted controls are present.
8. Historical evidence remains intact; scientific findings and production
   acceptance are recorded separately.

The final handoff is `READY_FOR_REVIEW`, with a table for H1–H4 and P0–P5.
Only measured gates receive PASS. Unrun stages are NOT_RUN, incomplete evidence
is INCONCLUSIVE, correctness failures are FAIL, and research null results are
reported as such. Acceptance does not require a positive scientific result.

## 12. Related work and defensible contribution

Decoder-based evolutionary scheduling already exists. Gonçalves and Resende's
[primary report on random-key job-shop scheduling](https://optimization-online.org/2011/04/2995/)
constructs schedules from chromosomes and applies local search. Structural
validity by decoding is therefore context, not a novelty claim by itself.

Pelikan, Goldberg and Cantú-Paz's BOA is documented in
[the author's publication record](https://martinpelikan.net/publications.html);
[Pelikan's account of BOA and hBOA](https://link.springer.com/book/10.1007/b10910)
describes learning and sampling Bayesian networks. These establish a relevant
model-building comparison class, without implying that every EDA uses the same
model or that a deterministic cover avoids model-selection errors.

The [Saarland SSA allocation project](https://www.compilers.cs.uni-saarland.de/projects/ssara/)
provides the relevant qualification to blanket graph-colouring hardness claims.
For this pinned straight-line machine, the fixed-schedule scalar subproblem can
also be analysed directly as interval colouring; joint scheduling and aligned
mixed-width placement require their own arguments. No hardness theorem for this
precise bounded machine is asserted by citation to a different formulation.

The potential contribution is a measured relationship between **decision
coordinates, exact schema structure and search efficiency** under independently
checked compiler semantics. The strong result would be a model that generalises
to unseen good compilations and earns back its construction cost. A weaker but
useful result would be a correct representation or a faster bounded search. A
carefully delimited negative result would establish where this representation
and model fail, with reproducible counterexamples and costs.
