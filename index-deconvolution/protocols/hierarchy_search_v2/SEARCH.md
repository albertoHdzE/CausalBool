# Search specification: HID-search-v2

Normative companion to [the protocol](../../PROTOCOL_hierarchy_search_v2.md).
Keep the existing decoder, wire language, model factory and legacy FULL search.

## 1. Six cumulative methods

| Method ID | Included proposal stages, in execution order |
|---|---|
| `hid_legacy` | L: original `infer(bits, FULL)` |
| `hid_first_local` | L, P: first-block templates, original grid, local patches |
| `hid_consensus_local` | L, P, C: consensus templates, original grid, local patches |
| `hid_dense_local` | L, P, C, D: remaining dense-grid consensus/local proposals |
| `hid_global` | L, P, C, D, G: dense-grid consensus/global patches |
| `hid_full` | L, P, C, D, G, B: bounded automatic boundaries |

Each invocation starts from the existing complete literal archive and independently
runs every included stage. L is byte-identical to legacy FULL for a completed
invocation. Other arms retain L's incumbent; they do not reconfigure its search.
The winning archive is the smallest complete archive. On equal length retain the
earlier incumbent (raw, then L, then P, C, D, G, B; periods ascending within a
stage). This preserves previously found candidates and gives deterministic ties.
No archive metadata is free. Final selection never uses estimated leaf savings.

Each completed, uncensored arm must be no worse in bytes than its predecessor on
the same input. A watchdog timeout can break observed nesting because that arm
deploys literal fallback; flag and count this, never repair it with another arm's
archive. Unexpected encoding/decoding errors invalidate the relevant run, rather
than becoming successful fallback. Use the inherited resource-fallback statuses.

## 2. Template estimation and exact corrections

Let x be the input, n its length. Empty inputs return raw. Eligible periods are
integers 1..min(256, floor(n/2)). The original grid is 1..32 plus 64, 128, 256,
intersected with that range. P and C use that grid; D visits eligible periods
outside that grid; G visits the entire eligible dense grid.

For P, word w=x[:p]. For C, D and G, at phase j choose 1 precisely when more than
half of x[j::p] is 1; choose 0 for a tie. Construct y by repeating w and truncating
to n. Compute **all** mismatch positions between x and y. Reject a proposal if
their count exceeds floor(n/16). No generator period, noise mask, seed, label,
boundary or previous archive enters this operation. No statistical significance
test is attached to scanning periods: the archive comparison pays for the word,
repeat count and corrections, and performance is evaluated prospectively.

Use this exact existing-language periodic builder for a nonempty slice b of y:
q,t=divmod(len(b),p). If q<2, return Literal(b). Otherwise return Repeat of
Literal(b[:p]), q copies, followed by Literal(b[-t:]) when t>0. Empty tails are
omitted. This correctly carries phase into local blocks; never restart every
block with the unrotated whole-input word.

**Local proposal:** split x and y into aligned consecutive blocks of 1,024 bits,
including the final short block. For each block of length L, compute its local
zero-based mismatch list. If its size exceeds min(64,floor(L/16)), use Literal of
that observed block. Otherwise Patch its periodic builder with every mismatch.
Concatenate the resulting blocks in order. Zero-error patches collapse through
the existing factory. The whole-input floor(n/16) gate still applies.

**Global proposal:** Patch the periodic builder of the whole y with all mismatch
positions. The only correction-count restriction is floor(n/16). There is no
fixed 64-error cap. This is legal in the existing wire format. Do not add another
opcode, suppress noise, or transmit a generator instead of the observed string.

For each candidate use the existing NodeFactory, structural sharing and to_model
ordering, then serialize the complete DAG. Require at most 4,096 reachable rules
and depth 64. Reject an over-limit candidate with telemetry; never truncate its
corrections. Independently decode every admissible full-input candidate and assert
equality with x. A disagreement is fatal. Charge this work to the method.

Per invocation upper bounds are 35 first/local and 256 total consensus/local
candidates, plus 256 global candidates: at most 547 new full-input template
serializations, before boundary search. Rejected error gates can reduce this.
Cache consensus words/residuals within an invocation, preserving stage order;
do not share incumbents/computation across benchmark arms. Record period attempts,
gate rejections, graph rejections, serialized candidates, duplicate archive hashes
and strict improvements separately. Counting only successful proposals hides work.

## 3. Bounded input-only boundary discovery

This is a specified heuristic, not an optimal partition solver. It has its own
candidate graph, initially one leaf covering [0,n). Retain the best B archive
separately and offer it to the full method's incumbent; B may need several strict
improvements to beat that incumbent. All intervals are half-open zero-based.

### Leaf builder and sharing

For x[a:b], consider its literal node and one exact-period node: call the existing
shortest-period owner, and if p<=256 and floor((b-a)/p)>=2, construct the repeat
plus exact tail as in §2. Price both as complete standalone HID archives of this
slice using the existing serializer; choose the shorter, literal on a tie.
This is **shortest-period-only leaf pricing**, explicitly a heuristic. The
shortest period need not minimize encoded bytes across all periods because count
and reference encodings have thresholds. Do not claim otherwise.

Cache leaf choices by (a,b) within B. Build a partition as a flat concatenation
of its leaves, with existing factory sharing and serialization. Full-root trial
pricing captures shared subgraphs and reference costs; adding independent leaf
costs is not an acceptable final objective. No entropy-coded or noisy leaf is
added in B in this stage. This isolates a small, inspectable boundary procedure;
limitations on noisy/transform-rich segments must remain visible.

### Trial ordering and coarse search

Start with partition [(0,n)], serialize once, and set it as the current B state.
Stop when it has eight segments. A parent interval [a,b) is eligible for splitting
when b-a>=64. Each child may have length **one or greater**. For each eligible
parent, propose the distinct ascending cuts

```text
{a+1, b-1} union {a + floor(j*(b-a)/32) : j=1,...,31}
```

restricted to a<c<b. Visit parent intervals left-to-right and cuts ascending.
Every trial replaces one parent with [a,c),[c,b), holding other leaves fixed,
and is evaluated by its complete serialized full-input archive. Rank trials by
(archive byte length, parent start, cut position, archive bytes). Select the best
coarse trial even if it has not yet improved the current B state.

### Refinement

For the selected parent of length L and coarse cut c, initialize
r=ceil(L/32), lo=max(a+1,c-r), hi=min(b-1,c+r). For up to five levels:

1. Set step=max(1,ceil((hi-lo)/16)). Evaluate sorted distinct positions
   `{lo,hi,c} union {c+j*step : j=-8,...,8}`, restricted to [lo,hi].
2. Retain the best candidate for this parent among all cuts seen so far, using
   (archive byte length, cut, archive bytes); set c to its cut.
3. If step==1, finish refinement. Otherwise set
   lo=max(a+1,c-step), hi=min(b-1,c+step), and continue.

Choose the best coarse/refined trial overall. Commit it only if its complete
archive is strictly shorter than the current B state. If committed, offer it to
the method incumbent and start another coarse round; otherwise stop. Neither
coarse/refined search nor five-level completion guarantees a globally best cut.
Record the evaluated bracket and final resolution; do not label it exact.

### Deterministic caps and exhaustion

Per invocation B has these limits:

- 512 distinct full-input partition serializations, including the initial state;
- 2,048 distinct cached leaf intervals;
- total leaf shortest-period input-length charges <=256*n;
- at most eight segments, five refinement levels per accepted coarse round,
  4,096 reachable rules and depth 64 for every candidate.

Before an uncached leaf call, atomically charge its length and one cache slot.
Before a new partition serialization, charge one full-input trial. Cached calls
do not consume those budgets again. Leaf standalone serializations are separately
counted (at most two per cached leaf); they are not falsely included in the 512
root-trial budget. This length charge is a deterministic work proxy, not CPU
instructions. Also record wall time and peak memory through the runner.

When a requested charge cannot be paid, end B immediately. Offer the best valid
full-input B archive actually serialized so far, including evaluated but not yet
committed split trials. Mark the cap and unresolved refinement state. Do not
discard a useful completed trial merely because the next one hit a cap. Decoding
and model-limit checks are required for every full-input trial. Input sizes in
this study make a literal initial graph legal. Retain a safe raw fallback for
arbitrary supported inputs.

## 4. Diagnostics, distinct from inference

For each HID invocation retain stage eligibility, attempts, gate failures,
serialization/decode counts, incumbent bytes after each stage, selected stage,
rule/depth counts, deterministic charges, stop reason, total wall time and memory.
Timing is nondeterministic; candidate identities/order/bytes are deterministic
unless the external watchdog interrupts execution. Every retained row references
the exact config, input hash and final archive hash. Telemetry must not contain
truth supplied to the encoder. Stage absence because that arm stops earlier is
different from zero successful proposals in an included stage.

Parse winners with `ledger.archive_ledger`. Use exhaustive, mutually exclusive
field buckets: envelope; DAG count/opcodes; references; length/count/flag and
transform fields; literal payload (separate meaningful bits and padding);
correction deltas; other literal/baseline payload. Define the field-to-bucket map
before freeze and test that its sum is exactly 8*archive bytes for every archive.
Report both total bytes and these components; overhead removed on paper is not
a deployable competing description.

For each F12 development string and each reserved F12/stress-S02 string, compute
an **evaluation-only supplied-boundary reference** after automatic rows are
complete. Take the generator's declared construction cuts/edit-adjacent positions,
map them to final coordinates, retain distinct positions strictly inside [0,n),
partition there, and use the same B leaf builder and existing sharing/serializer.
Save the cut list, derivation, archive and decode check. If metadata does not
uniquely determine a final cut after edits, record it unavailable with the reason;
do not invent an optimal cut or modify inference. Compare automatic cost against
the smaller of this feasible reference and raw, signed in bits/input bit.
This is a restricted feasible reference, **not an oracle optimum or a bound on
all search error**. A negative gap is possible because automatic search has more
operators. Retain the earlier handcrafted witness separately with its original
post-hoc label. Neither reference is a benchmark method or a source of incumbents.

Finally, report resource fallback frequency, cap frequency, candidate yield,
stage cost and the five prospective contrasts. These distinguish observed search
opportunity, representation accounting and operational failures. They do not
fully identify their causal contributions or justify changing the wire format.
