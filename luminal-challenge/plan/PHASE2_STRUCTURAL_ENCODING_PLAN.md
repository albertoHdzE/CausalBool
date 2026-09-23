# Luminal phase 2: structural encoding and model-building search

Version: **1.0**. Date: **2026-09-22**. Status: **PROPOSED — NOT AUTHORISED FOR
IMPLEMENTATION.** Owner: author (Alberto Hernández Espinosa). Evaluation and
drafting: Claude Code, acting as reviewer, not as lead.

This document supplements `INDEX_ONLY_PLAN.md` v1.1 and
`OPTIMIZATION_PHASE_PLAN.md` v1.1. It does not replace the correctness contract,
the accepted v3/v4 implementation, or any frozen evidence. Nothing here
authorises a code change, a benchmark claim, a submission or a paper sentence.

Its purpose is to record, at the same level of rigour as the earlier plans, an
evaluation of a research direction proposed by the author, including every
objection raised against it, the author's rebuttal, which objections were
withdrawn and which survive, and the cheapest experiments that would decide the
question.

---

## 0. What this document is, and what it is not

**It is** a faithful record of a technical conversation held on 2026-09-22,
promoted to a plan so that it can be read, disputed and executed later.

**It is not** a claim that the proposed direction works. Section 10 states the
weaknesses at the same length as the strengths deliberately. The single most
likely outcome of section 12 is a negative result obtained in one afternoon,
and that outcome is treated here as a success of the protocol.

Every number quoted below carries its provenance. Estimates are labelled
**ESTIMATE** and are not to be repeated without the measurement that section 12
prescribes.

---

## 1. Provenance

### 1.1 The teaching sequence that preceded this plan

Phase 1 closed with two executed notebooks. During 2026-09-21 and 2026-09-22 the
author read them and reported, repeatedly and precisely, where the explanation
failed. Four defects were found and repaired. They are recorded here because the
last of them is what exposed the gap this plan addresses.

| # | Defect | Repair | Commit |
|---|---|---|---|
| 1 | The rule 5 caption asserted that `op0` and `op4` were "still free to reorder". False: the ordering arrives transitively through `op0 → op3 → op4`. | Caption corrected; `viz.show_memory_chain` added to draw the transitive edge. | `738be96` |
| 2 | §7 case 1 was labelled "too early (latency)" but reported an allocation overlap, because it re-derived the allocation from the broken schedule. | Case reuses the starter's private-locker map; a comment records why. | `29c107a` |
| 3 | §2 of notebook 01 printed `x0..x3:*10*` without ever stating what the string is made of, that it is a printed view rather than stored state, or that it runs LSB-first while the anchor beside it prints MSB-first. | `viz.show_cube_anatomy` added; §2.1 gives the grammar and the disjointness invariant; §2.2 shows membership as one AND and one comparison. | `90c401b` |
| 4 | §2 never connected the cube to either compiler question; the connection first appears in §4, two sections later, when `Field` arrives. The author reported being unable to see any connection at all. | §2.3 added: the act of deciding what a coordinate means, the same cube read as cycles and as addresses, and a table mapping each constraint to its set operation. | `625aceb` |
| 5 | The notebook opened at the compiler's two questions and reached the representation three cells later. A reader without the LSB-first convention had no foothold. | §0 added: eight boxes, three yes/no questions, the star, the two stored integers, then the three compiler moves and alignment — no compiler vocabulary until §0.4. | `f481ca8` |

Defect 4 is the relevant one. The notebook had been presenting a representation
without its interpretation step, and the interpretation step — *decide what a
coordinate means* — is precisely the degree of freedom this plan proposes to
exploit.

### 1.2 The author's notes

Source: `~/Downloads/COMPILER.pdf`, nine handwritten A4 pages, iOS scan dated
2026-09-22 19:47, unfinished. The notes are a page-by-page reading of notebooks
00 and 01 with four passages marked **IDEA**.

**Assessment of the notes as an account of phase 1: accurate throughout.** The
five rules, the three memory-ordering tests, the live-interval reasoning, the
slot-versus-pipeline distinction ("a slot is a doorway, not a parking space"),
the hand-built eight-cycle schedule and its arithmetic (`left = 65 + 34 = 99`,
`right = 189 xor 34 = 159`) are all correct. No misunderstanding in the notes
required repair. The only sentence this review would strike is the one about
solving an NP-hard problem, addressed in section 3.

---

## 2. The four IDEA blocks, transcribed

Transcribed from the handwriting, lightly repunctuated, not paraphrased.

**IDEA 1 (page 3).** *"What if a set of conditions at specific time can be
expressed as a string of bits where each of conditions is expressed as a binary
code. Let us say, what if I set: two numbers in memory ('01' code) with address
1 and 2 (10, 01) with a sum operation ('00') coming, with restrictions on
condition (00, 01, 10) → `011001000001 10`, all above together as a binary
string. This is an output of a network. If I know and I can enumerate the most
logical strings I can have a sampling of the possible conditions. Then I could,
by deconvolution, create or generate the known outputs. [...] By our
deconvolution method now we can ask for certain conditions, if exists as output
and by index will tell us if exist. But this queries would ask for a subset of
required conditions where schemata plays an important role. Then an allocation
would be the tree that generates in order the execution that generates the
subset of outputs that represents the compilation then execution of the
program."*

**IDEA 2 (page 4).** *"Retaken the above idea, and combining it with Chaitin
algorithm: what Chaitin does is to consider the graph as the memory
representation, literal map to the colour-the-graph problem between countries.
Then you have to start from an initial graph and play (perturb) it to find the
optimal. But our idea goes in other direction I would like to prove. Let us
represent a string as the graph in the JSON above shown. If load is a code as
001, and uses slots 0 and one I have something like 00001 which corresponds to
`"load": [0,1]`. Then we can create a string that represents the Chaitin or the
JSON or the graph. Then we might have a population of possible solutions, just
in the same spirit of an individual in genetic algorithms, in which such genome
represents a solution. But in our case we will look by deconvolution the network
that creates the behaviour of the individuals. [...] Currently we have methods
that, given a query, we can ask: 'is this behaviour possible', which is the
same: is our network capable to compute this pattern? [...] If so, the function
returns the indexes where such desired pattern is."*

**IDEA 3 (page 5).** *"See the section '2. A real program' in notebook, how a
program is represented by a graph. This graph could be for us our desired output
that should be deconvolved, taking into account the rules mentioned in section
'3. The five rules stated exactly'. For us, maybe, the compilation or the program
shown in section 2 as a table with columns id, op, engine, lat, dest, args could
be a basin, a cycle inside the network behaviour. Our first approach of
configuration of our network, or our basin, could be what is shown in section 4
of notebook 00, 'The starter compiler and what it costs'."*

**IDEA 4 (page 9, unfinished).** *"At this point, the scratchpad represents an
indexed memory where a value must be set. In the above examples, we load a
number…"*

**Synthesis.** Encode an entire compilation as one binary string whose fields are
the individual decisions; treat the space of such strings as the output
repertoire of a Boolean network; use index-set deconvolution to recover the
network that generates the good ones; use the existing query machinery, with
schemata expressing partial conditions, to ask whether a desired compilation
exists. Allocation becomes a basin or attractor of that network rather than the
output of a colouring heuristic.

---

## 3. Evaluation part 1 — the complexity claim

The author asked directly whether this problem is NP-hard and whether the method
is on the road to solving it.

### 3.1 What is true

- **Register allocation is NP-complete.** Chaitin et al. (1981) reduced it to
  graph colouring. The author's map-colouring analogy on page 3 of the notes is
  the standard one and is drawn correctly.
- **Resource-constrained instruction scheduling is independently NP-hard.** The
  notes assert hardness only for allocation. Both halves are hard.
- **The phase-coupling observation is correct and is the strongest single
  remark in the notes.** From page 2: *"the moment you change the schedule,
  every lifetime moves, and the allocation problem you were solving becomes a
  different problem."* This is the phase-ordering problem and it remains
  unsolved in production compilers.

### 3.2 What is not true, with measured evidence

The method does not dissolve the exponential, and the evidence is inside the
repository rather than in the literature.

**Evidence A — the budget and the UNKNOWN verdict.** `si.solve` accepts a
`si.Budget` and may return `UNKNOWN`. Notebook 01 §10 starves it deliberately on
a window of four operations of `02_scalar_dual_chain`:

```
 max_visited  verdict     visited  reason
       50000  UNSAT        33,983  -
       33000  UNKNOWN      33,001  visited-cube budget exhausted
       30000  UNKNOWN      30,001  visited-cube budget exhausted
       25000  UNKNOWN      25,001  visited-cube budget exhausted
       20000  UNKNOWN      20,001  stopped while building
```

If the exponential had been defeated, no budget would be needed and `UNKNOWN`
would not exist as a verdict. `UNKNOWN` is the hardness, surfacing in our own
machinery, on a four-operation window.

**Evidence B — the joint optimiser resolves almost nothing.** Over the eight
public programs (notebook 01 §11.2, regenerated live):

| program | queries | SAT | UNSAT | UNKNOWN | accepted |
|---|---:|---:|---:|---:|---:|
| 01_scalar_pipeline | 18 | 0 | 0 | 2 | 0 |
| 02_scalar_dual_chain | 24 | 0 | 5 | 0 | 0 |
| 03_vector_axpy | 28 | 0 | 4 | 2 | 0 |
| 04_vector_bitmix | 32 | 0 | 4 | 4 | 0 |
| 05_mixed_broadcast | 20 | 0 | 5 | 5 | 0 |
| 06_parallel_memory | 32 | 0 | 3 | 4 | 0 |
| 07_scalar_selects | 32 | 0 | 3 | 5 | 0 |
| 08_vector_reduction | 32 | 0 | 3 | 4 | 0 |
| **total** | **218** | **0** | **27** | **26** | **0** |

Two hundred and eighteen queries attempted; **fifty-three reached a verdict**;
**one hundred and sixty-five were abandoned during construction** as infeasible;
**zero were satisfiable**; **zero improvements were accepted.**

**Evidence C — the cost.** From
`results/direct_index_v4_optimization_repair2/comparison/runs.json`, 72 runs,
3 repetitions, all gates passed:

| arm | combined score | median compile |
|---|---:|---:|
| serial | 1.000000 | 0.000023 s |
| classical | 1.901379 | 0.000270 s |
| direct_index | 2.008466 | 0.174400 s |

A 5.63% better score bought at **646 times** the compile time.

**Conclusion of 3.2.** The correct formulation is: *a representation in which the
statement of the problem stays small and the admission of defeat is explicit.*
Not: *a route to solving an NP-hard problem.* The first is defensible and
publishable. The second would not survive one round of review.

### 3.3 What the method does provide

1. **A compact statement of a structured constraint set.** Cubes are an
   implicant-cover representation. They compress structured sets extremely well
   and do not change worst-case complexity at all; an unstructured set requires
   one cube per element. This is the same bargain reduced ordered decision
   diagrams make, and the `doppel-challenge` documentation already says so
   explicitly (`doc/06-shared-program.md`: *"parity can have exponentially many
   accepting schema paths despite a small shared graph"*).
2. **An auditable failure mode.** `UNSAT` is a proof that a declared domain was
   exhausted. A greedy heuristic cannot produce that statement; it can only say
   "I did not find one", which is `UNKNOWN` wearing a confident face. The
   refusal to conflate the two is the most defensible property of the method and
   it exists *because* the problem is hard.

---

## 4. Evaluation part 2 — the author's structural observation

The author stated that the heart of the method remains the starter of notebook
00 §4: a queue, a per-cycle evaluation of system state, issue and react.

**This is correct and it is measured.** Evidence B above: the entire public
result comes from `direct_compiler.bootstrap`. The optimiser accepts nothing on
the public corpus. The cube algebra currently *restates* a greedy bootstrap in
set language; it does not currently beat it. The optimiser only pays on the
generated extra corpus (18 accepted improvements over 3 repetitions, recorded in
the v4 evidence).

This matters for phase 2 because it identifies where the remaining value is: not
in the representation, which is built and correct, but in the search that would
justify it.

---

## 5. Evaluation part 3 — what IDEA 2 already has

The author proposes constructing *"a string that represents the Chaitin or the
JSON or the graph"*. **That string is built and running.** Notebook 01 §8:

```
window          : (1, 2, 3, 7)
index width     : 56 bits

   t1         bits   0..4   width 5      when operation 1 issues
   a_b0       bits   5..12  width 8      where value b0 lives
   l1         bits  13..13  width 1      lane bit
   t2         bits  14..18  width 5
   a_c0       bits  19..26  width 8
   l2         bits  27..27  width 1
   t3         bits  28..32  width 5
   a_d0       bits  33..40  width 8
   l3         bits  41..41  width 1
   t7         bits  42..46  width 5
   a_left     bits  47..54  width 8
   l7         bits  55..55  width 1

assignments this index can express: 2**56 = 72,057,594,037,927,936
```

One integer holding every scheduling and allocation decision for a window at
once, with named field access. Owner: `direct_constraints.JointQuery`.

Two differences from the note: the index covers **a window**, not a whole
program, and it is used to **verify a target** rather than to carry a
population. The first half of IDEA 2 is therefore not a proposal; it is a fact
that can be executed today. What is new is the second half.

---

## 6. Evaluation part 4 — what is genuinely new, and its family

The novel proposal is: *keep a population of such strings and, instead of
perturbing a graph as Chaitin does, recover by deconvolution the network that
generates the good ones, then generate from that network.*

### 6.1 The family, named

Learning a generative model from a selected population and sampling from the
model rather than mutating the population is an **estimation-of-distribution
algorithm** (EDA); the model-building genetic algorithm literature (BOA, cGA and
relatives) is the reference class. A reviewer will identify this within a
paragraph. Naming it first is protection, not concession.

### 6.2 Where the novelty actually lies

Every EDA in that literature learns a **probabilistic** model — a Bayesian
network with conditional probability tables. The proposal learns a
**deterministic, algorithmic** one: schemata. The cost argument is already
developed elsewhere in this programme (`imp-prices`): a conditional probability
table costs `3^k (3-1)` parameters estimated from finite data; a gate costs
zero. A schema-model EDA has **no parameters, no probabilities and no estimation
error**; it either admits an assignment or it does not.

This is consistent with the author directive of 2026-09-07 (no Shannon quantity
may be one of our complexity measures) and with pinned decision #96 (one
explicit algorithmic measure, no hybrids). The direction is therefore coherent
with the wider programme rather than an excursion from it.

The contrast with Chaitin is clean and is the author's own: Chaitin starts from
one graph and perturbs towards a colouring; this method states the set of
acceptable colourings and asks it for a member.

---

## 7. The two objections raised

### 7.1 Objection 1 — circularity

*The constraint set is already known in closed form. The five rules are the
generator. Learning a network that reproduces a set one can already write down
exactly buys nothing unless the learned object answers queries more cheaply than
the exact one.*

Proposed acceptance test at the time: the model must answer a query that
`si.solve` cannot answer within budget.

### 7.2 Objection 2 — legality is not the hard part

*The bootstrap produces a legal compilation in 0.27 milliseconds (classical) and
the direct bootstrap in the same order. Nobody needs a generative model of legal
compilations. The hard part is the optimal one. A model must therefore be built
from the selected population — the top fraction by cycles × words — and rebuilt
after each selection. Without the selection step the result is a sampler, not a
search.*

---

## 8. The author's rebuttal, and its assessment

### 8.1 The rebuttal

> *"The five rules, in my idea, are not the generator, but part of a valid
> string that was generated by a network whose steps of generation already
> validated the rules or constraints. See what we did in the project 0xPARC and
> doppel; we used such strategy to avoid redundancy. Same for legal
> compilations: the current state of the system can be part of the string we
> consider and that the dynamics of the network considers. Then one string not
> only says it is legal but the schedule also, the correct one."*

### 8.2 The construction, named from the author's own repositories

The rebuttal is not an intuition; it is a technique the author has already
implemented twice in this repository.

**`doppel-challenge`** represents a Boolean repertoire as a reduced ordered
decision diagram in **canonical form**, and the decoder *rejects* anything that
is not a canonical object. From `doc/06-shared-program.md`:

> *"It rejects truncation, extra bytes, nonzero padding, out-of-range
> references, forward references, inconsistent coordinate order,
> redundant/duplicate/unreachable nodes, and noncanonical numbering."*

and from `src/doppel_challenge/repertoire_program.py:223`:

```python
if _integer(v, "coordinate") >= n or low == high:
    raise ValueError("invalid or redundant decision")
```

**`0xPARC-challenge`** does the arithmetisation form of the same move: row
constraints admit only valid witnesses (`row_evaluator.check_rows`).

The shared discipline is: **one string per object, and no string for a
non-object.** Validity is a property of the representation, not the outcome of a
check applied afterwards.

### 8.3 Does the discipline transfer to the five rules? Rule by rule

| rule | structural encoding | free by construction? |
|---|---|---|
| **1 — slots**: each engine starts at most *n* operations per cycle | write each cycle as a bundle with a fixed number of slot fields per engine | **Yes.** Three operations cannot be written into a two-slot field. Note that the author's own page-4 sketch (`"load": [0,1]`) is already this shape. |
| **2 — latency**: an operation issued at *c* completes at *c + latency*; readers must issue no earlier | decode as a sequence of decisions against a carried ready-set; a field selects among operations whose inputs have landed | **Yes**, provided the string is decoded as decisions against state rather than as absolute values. This is exactly the author's second point. |
| **3a — capacity**: 256 words | address fields index the scratchpad | Yes, trivially. |
| **3b — alignment**: a vector occupies 8 consecutive words and must start on a multiple of 8 | store `address / 8` for a vector, not `address` | **Yes.** A misaligned vector becomes unrepresentable rather than rejected. |
| **4 — sharing**: two values may share a word only if their live intervals do not overlap | encode an address as *an index into the list of currently free lockers*, not as an absolute word number | **Yes**, and additionally this removes locker-renaming symmetry. This is the same discipline as a restricted-growth string for set partitions. |
| **5 — memory ordering**: same-buffer, overlapping-range, not-both-loads pairs must occupy different cycles in program order | the same carried state as rule 2: such pairs are only offerable in program order | **Yes.** |

Row 4 is the load-bearing one. By naming *the choice among what is currently
available* rather than the thing chosen, every string becomes legal **and** two
strings that differ only by renaming become impossible. Both halves of the
`doppel` property — no invalid members, no redundant members — are obtained.

### 8.4 Disposition of the objections

**Objection 1 (circularity): WITHDRAWN.** It was raised against a
generate-and-test design. The author proposed a correct-by-construction design.
Under a state-relative encoding the five rules are not checked, learned or
reproduced; they are absent from the search entirely because violating strings
do not exist. The objection does not apply.

**Objection 2 (legality is not optimality): SUSTAINED, and narrowed.** Making
the encoding structural removes infeasibility. It does not order the feasible
points. Every string in the proposed space satisfies all five rules; they do not
have equal cost; minimising cycles × words over them remains NP-hard; and a
canonical encoding provides no gradient.

What the rebuttal does buy, and it is substantial: **no repair operator, no
penalty term, no invalid offspring.** Every mutation of a valid string is a
valid string. This is the standard failure mode of population methods on
constrained combinatorial problems, and the encoding removes it structurally.
The precedent in the genetic-algorithm literature is the decoder-based or
indirect encoding (random-key and Grefenstette encodings for routing problems).
The design is principled and has a track record.

---

## 9. The design that follows

### 9.1 State-relative encoding (the core proposal)

Decode a bit string as an ordered sequence of decisions taken against the
machine state that the prefix of the string has already established:

1. Maintain the machine state the starter already maintains: ready set, engine
   slot occupancy for the current cycle, free-locker list, buffer-write history.
2. At each decision point, enumerate the **currently legal options** in a
   **canonical order**.
3. Read `ceil(log2(number of options))` bits and take that option.
4. Advance the state.

Every legal compilation has at least one encoding; no illegal compilation has
any. With canonical option ordering and symmetry-free option lists, every legal
compilation has exactly one encoding.

### 9.2 Estimated width — **ESTIMATE, to be measured, not to be quoted**

Current window index, `02_scalar_dual_chain`, window `(1, 2, 3, 7)`:
4 operations × (5 cycle bits + 8 address bits + 1 lane bit) = **56 bits**, of
which **32 bits are absolute addresses over a 256-word scratchpad in a
compilation whose entire footprint is 3 words**.

Under the state-relative encoding, per operation:

- cycle offset from the earliest legal cycle, over a window of at most 8
  cycles → 3 bits;
- address as an index into the free-locker list, where the footprint is 3 words
  so at most 4 lockers are ever offered → 2 bits;
- lane bit → 1 bit.

4 × 6 = **24 bits**, giving a declared domain of 2²⁴ ≈ 16.8 million in place of
2⁵⁶ ≈ 7.2 × 10¹⁶, with the additional property that **every point of the smaller
domain is a legal compilation** whereas almost no point of the larger one is.

This arithmetic is a paper estimate on one window of one program. Its purpose is
to justify measuring, not to be reported. Experiment **E2** replaces it.

### 9.3 The origin property

Order every option list so that index `0` is the option the starter would take.
Then **the all-zeros string decodes to the bootstrap compilation exactly**, and
Hamming distance from the origin measures departure from greedy.

Given section 4 — the bootstrap produces the entire public result and the
optimiser accepts nothing — this is the correct shape for the problem. The
starter ceases to be the answer and becomes the coordinate system, and the
search becomes a controlled expansion outwards from a known-good origin with a
single interpretable budget parameter: the radius.

---

## 10. Feasibility assessment

### 10.1 Strengths

1. **The representation already exists and is correct.** `schema_index`,
   `direct_contract`, `direct_constraints` and `direct_compiler` are accepted,
   tested and frozen-reference-validated. Phase 2 changes an encoding, not a
   theory.
2. **The correct-by-construction discipline is proven in this repository
   twice** (`doppel-challenge`, `0xPARC-challenge`), by the same author, with
   decoders that reject non-canonical input. This is not a borrowed technique.
3. **The hardest constraint is the one the encoding handles best.** Rule 4 —
   sharing, the graph-colouring core — becomes both automatic and
   symmetry-free under a free-list index.
4. **The origin property gives the search a principled starting point** and an
   interpretable budget, and it converts a measured weakness (section 4) into
   the design's coordinate system.
5. **The model class is consistent with the programme's standing directives** —
   algorithmic, not Shannon; one measure, no hybrids.
6. **A plausible near-term practical payoff independent of the research
   question.** The current optimiser spends 165 of 218 queries failing during
   construction over a 56-bit domain of mostly illegal points. A compact legal
   domain may change that without any new theory. See enhancement E-1.

### 10.2 Weaknesses

1. **Optimality remains NP-hard and the encoding gives no gradient.** This is
   sustained objection 2 and it is not repairable by encoding.
2. **The compression claim is unproven.** Cubes compress structured sets. That
   the set of *good* compilations is structured in this encoding is a
   conjecture, and it is the conjecture on which everything else rests.
   Experiment **E3** is designed to refute it cheaply.
3. **Canonical enumeration of legal options at each decision point costs
   time.** The encoding buys a smaller domain by paying per decision. Given the
   existing 646× compile-time deficit, a decoder that is slower per candidate
   could erase the benefit. This must be measured, not assumed.
4. **One encoding per compilation requires proof, not assertion.** Uniqueness
   depends on canonical option ordering at every decision point, including ties.
   `doppel` needed an explicit canonicalisation pass (`_canonical`) and an
   explicit rejection list to achieve it. The same discipline will be required
   here and it is where subtle defects live.
5. **The deconvolution step remains the least specified part of the proposal.**
   IDEA 1 and IDEA 2 describe recovering "the network that generates the good
   individuals" without stating the network's state space, update rule, or what
   an attractor corresponds to. The Boolean-network reading of *basin →
   allocation* (IDEA 3) is evocative but is not yet a definition.
6. **The attractor framing has a known failure mode.** If a dynamics whose
   attractors are good compilations is constructed, this is an energy-descent
   method in the Hopfield–Tank sense, whose documented weaknesses on colouring
   and routing problems are spurious attractors and local minima. The framing
   must acknowledge that literature rather than rediscover it.
7. **Scope risk.** Phase 1 is complete, submitted and defensible. Phase 2 is
   research with a genuine probability of a null result. It must not be allowed
   to destabilise phase 1 artefacts or delay the outstanding push.

### 10.3 What would kill the project, stated in advance

- **E1 fails**: any decoded string that `machine.check_compilation` rejects.
  The correct-by-construction claim is then simply false and everything above
  collapses. This is the first experiment for that reason.
- **E3 returns a cover ratio near 1**: the good compilations are a scatter, not
  a structured set; schemata have nothing to grip; the model-building step has
  no object. Stop, and report the negative result.
- **E2 shows no meaningful width reduction**: the domain does not shrink, so the
  search space is unchanged and only the validity property is gained. That is a
  smaller result but not necessarily a fatal one; re-scope to enhancement E-1
  alone.

### 10.4 Points to consider

1. **Decide the acceptance test before writing the encoder.** Proposed: the
   encoding must produce, on at least one public program, an accepted
   improvement that the current optimiser does not find, or a measured
   compile-time reduction, with the existing seven comparison gates intact.
2. **The frozen reference and the validator are not negotiable.** Every
   candidate is judged by `machine.check_compilation` and by case execution.
   The encoder is never its own judge.
3. **`UNKNOWN` semantics survive unchanged.** A budget that actually exhausts
   returns `UNKNOWN`. A smaller domain may legitimately convert former
   `UNKNOWN` verdicts into proven `SAT`/`UNSAT`; that is a result to record, not
   a licence to shorten a search.
4. **Do not tune on the extra corpus.** The frozen evaluation corpus (seed
   20260921) is for final evaluation only, per `OPTIMIZATION_PHASE_PLAN.md` §4.
5. **Publication framing.** If this works, it is *a parameter-free,
   schema-model estimation-of-distribution algorithm over a correct-by-
   construction encoding of VLIW compilations*. It is not a solution to an
   NP-hard problem. The distinction must appear in the abstract, not in a
   footnote.
6. **One owner per concept.** The encoder is one module. Under the
   `monolithic-code` law its owner must be located or declared before a line is
   written, and the guard that keeps it single must ship in the same commit.
   `machine.py` is frozen and may not be enriched; `direct_contract` already
   owns derived program facts and is the natural host for state enumeration.

---

## 11. Proposed enhancements

Ordered by cost, lowest first. **E-1 is independent of the research question and
may have standalone value.**

**E-1. Replace absolute address fields with free-list indices in the existing
joint query.** No population, no deconvolution, no new theory: only a narrower
`JointQuery` index. Rationale: 165 of 218 queries currently abort during
construction, and 32 of 56 bits describe a 256-word space for a 3-word
footprint. This is a contained change to `direct_constraints` with the existing
gates as its test.

**E-2. Encode `address / 8` for vector values.** Alignment becomes
unrepresentable rather than constraint-checked, removing one intersection per
vector value from every query.

**E-3. Canonical option ordering with greedy-first.** Delivers the origin
property of §9.3 and makes Hamming radius the search budget.

**E-4. Carry the partial objective in the decoder state.** Cycles consumed and
words occupied are known at each decision point, so a prefix whose partial cost
already exceeds the incumbent can be refused before completion. This is
branch-and-bound over the encoding and is the most likely source of a real
speed-up.

**E-5. Report search radius rather than visited-cube counts in the public
report.** A radius is interpretable by a reader; a cube count is not.

**E-6. Only if E3 succeeds: the schema model.** Build the cube cover of the
selected population, sample from the cover, re-select, re-cover. This is the
EDA loop with a schema model class and no probabilities. The deconvolution
framing of IDEA 1 and IDEA 2 becomes concrete here and nowhere earlier.

---

## 12. Experimental programme

Every experiment obeys the standing gates: **refuse on empty input** (exit 2),
**print the denominator**, and **never report a ratio without the counts behind
it**. No experiment may modify `machine.py`, the pinned reference, or any
existing `results/` directory. New artefacts go to
`results/phase2_structural_encoding/`.

### E1 — the refutation gate (do this first, and stop if it fails)

**Question.** Does the state-relative encoding produce only legal compilations?

**Method.** Implement the decoder for `02_scalar_dual_chain`. Draw K = 10,000
uniform random bit strings of the decoder's declared width. Decode each. Submit
every decoded compilation to `machine.check_compilation` and to
`machine.check_case` for all program cases.

**Report.** K drawn; number decoded; number accepted; number rejected, with the
validator's exact message for every rejection.

**Gate.** Rejections must be **zero**. One rejection refutes the design as
specified. Do not repair by filtering; repair the encoding or report failure.

### E2 — measured width

**Question.** How wide is the encoding actually, against 56 bits?

**Method.** Instrument the decoder to record `log2(options)` at every decision
point across the same K strings and across the eight public programs.

**Report.** Per program: declared width, mean and maximum realised width, and
the current `JointQuery` width for the same window. State the domain sizes as
powers of two, not as decimal approximations.

**Gate.** None; this is a measurement. It replaces the **ESTIMATE** in §9.2,
which must not be quoted until this runs.

### E3 — the structure conjecture (the decisive experiment)

**Question.** Are the *good* compilations a structured set in this encoding, or
a scatter?

**Method.** For `02_scalar_dual_chain` and at least two other public programs:
generate a population of legal compilations (E1's decoder, uniform sampling plus
a Hamming ball around the origin), deduplicate, score each by cycles × words
using the validator's own counts, take the top decile, and compute a cube cover
of the top decile's index set using `schema_index`.

**Report.** Population size; distinct count; decile size; cubes in the cover;
the ratio `cubes / decile size`; and the same ratio for a **control** — a
uniformly random subset of the same cardinality drawn from the legal population.

**Gate.** The control is what makes this a measurement rather than a number. If
the top decile's ratio is not materially below the control's ratio, there is no
structure to learn and the programme stops here with a reportable negative
result.

### E4 — the origin property and a like-for-like search comparison

**Question.** Does a radius-bounded search from the origin find what the current
optimiser does not?

**Method.** Verify that the all-zeros string decodes to the bootstrap
compilation, byte for byte, on all eight public programs. Then run a
radius-bounded search under a budget matched to the current optimiser's, and
compare accepted improvements against the measured baseline of **0 accepted over
218 queries**.

**Report.** Per program: bootstrap metrics, best found, radius reached, budget
consumed, wall-clock. All eight programs, including the losses.

**Gate.** No claim of improvement without the full three-repetition comparison
and all seven existing gates, per `OPTIMIZATION_PHASE_PLAN.md` §4.

### E5 — conditional: the schema model

Runs **only** if E3 passes its gate. Specification deferred: it must be written
after E3's numbers exist, not before, and it must state the network's state
space, update rule and attractor interpretation in operational terms rather than
by analogy.

---

## 13. Non-negotiable constraints

- `machine.py`, the pinned reference, `common.py`, `results/comparison.json` and
  all accepted v1–v4 evidence are immutable.
- `compiler.compile_program(program)` keeps its signature and its return
  contract.
- No BDD backend, SAT/SMT solver, exhaustive production enumeration or classical
  fallback enters the production direct path. A decoder that enumerates *legal
  options at one decision point* is not exhaustive enumeration of the space;
  this distinction must be stated explicitly in any implementation handoff.
- Exact verdict semantics are preserved. Actual exhaustion returns `UNKNOWN`.
- No test is weakened, no timeout enlarged, no score formula altered, no public
  corpus changed.
- The 0xPARC manuscript, the doppel package and all notebook work outside
  `luminal-challenge` are out of scope.
- No push, submission or paper claim is authorised by this plan.

---

## 14. Decision points

| point | decision | who |
|---|---|---|
| After E1 | Proceed, or report the design refuted. | author |
| After E2 | Proceed, or re-scope to enhancement E-1 alone. | author |
| After E3 | Proceed to E4/E5, or stop and report the negative result. | author |
| After E4 | Whether any production change is proposed at all. | author, as lead review |

The reviewer's recommendation is that **E1 and E3 be run before anything else is
written**, and that the encoder built for E1 be treated as a throwaway probe
rather than as production code until E3 has returned.

---

## 15. What this plan does not authorise

It does not authorise implementation. It does not authorise a benchmark claim,
a change to the production path, a notebook section presenting the idea as
result, a paper sentence, or a push. It records an evaluation and a protocol.

---

## 16. Delegation prompt

To be used only after the author authorises E1.

> Implement experiment E1 only, from
> `luminal-challenge/plan/PHASE2_STRUCTURAL_ENCODING_PLAN.md`.
>
> You are the implementing worker, not the lead reviewer. Read `AGENTS.md`,
> `INDEX_ONLY_PLAN.md`, `OPTIMIZATION_PHASE_PLAN.md`, `STATUS.md` and this
> complete plan before editing. Before writing any code, answer the four
> `monolithic-code` questions in the handoff: where the core that owns machine
> state enumeration lives, whether it already exists under another name, why a
> new definition beats enriching `direct_contract`, and what guard keeps it
> single. The guard ships in the same commit and is verified by planting a copy.
>
> Build the state-relative decoder for `02_scalar_dual_chain` as a probe, not as
> production code. Do not modify `machine.py`, the pinned reference, the
> production direct path, or any existing results directory. Write new artefacts
> to `results/phase2_structural_encoding/`.
>
> Draw 10,000 uniform random bit strings, decode each, and submit every decoded
> compilation to `machine.check_compilation` and to `machine.check_case` for
> every program case. The experiment refuses on an empty scan and prints its
> denominator: strings drawn, decoded, accepted, rejected. Report every
> rejection with the validator's exact message. Do not filter, retry or repair a
> rejected candidate; a single rejection is the result.
>
> Report the outcome factually, including a failure, and stop. Do not proceed to
> E2 or E3, do not touch the production compiler, do not claim any improvement,
> and do not push. End the handoff with `READY_FOR_REVIEW`.

---

## 17. Reviewer's closing assessment

The proposal is **not a dream, and it is not a solution to an NP-hard problem.**
It is a well-founded encoding change with one genuinely novel component and one
unproven conjecture.

- The encoding change (§9.1, §9.2) is sound, is proven twice in this author's
  own repositories, and I expect it to work.
- The origin property (§9.3) is elegant and converts a measured weakness into a
  coordinate system. I expect it to work.
- The conjecture — that the *good* compilations form a schema-structured set
  (§12, E3) — is the whole research content, and I do not know whether it is
  true. Nor does the literature, because no one has asked the question in this
  representation.

That is a good position for a research phase: two components likely to work, one
question genuinely open, and an experiment costing one afternoon that can refute
the open question before anything expensive is built.

The single greatest risk is not technical. It is that a correct encoding and an
elegant origin property feel like progress, and the conjecture never gets tested
because the surrounding machinery is enjoyable to build. E1 and E3 exist to
prevent exactly that, and they should be run in that order, early, and reported
whatever they say.
