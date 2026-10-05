# Fixed representation, proposals and diagnostic definitions

## 1. Four arms and common limits

- A0 `k1`: unchanged `search_v2.infer_v2(bits, ARMS['hid_full'])`.
- A1 `word8_l1`: retained A0 plus width 8, level 1 proposals.
- A2 `multi_l1`: retained A0 plus widths (4,8,12,16,24,32,48,64), level 1.
- A3 `multi_l4`: retained A0 plus the same widths, levels 1 through 4.

Every width uses two origins, 0 and floor(width/2), ascending. These are two
separate non-overlapping partitions, not a sliding-window mixture. Never stitch
across partitions or choose a partition using family/truth metadata. Input-only
parameters are bits, immutable config, and the completed baseline archive bytes.
No case ID, namespace, family, seed, truth, notebook score or baseline portfolio
may enter search. Canonical symbol IDs follow first appearance at each level.
For an empty input, retain the verified empty baseline, request no views or
proposals, and record normalized diagnostics as unavailable (not division by zero).

Common augmentation ceilings: 64 views; 256 full-root proposal requests; at most
64 pair-grammar rules per view; maximum 4,096 reachable rules and depth 64 per
archive. Each requested root consumes one proposal slot, including a duplicate,
patch rejection or graph rejection. A view with no admissible proposal still
consumes its view slot. No extra serializations for unrecorded leaf selection.
All arms share these ceilings, but have different eligible proposal sets; report
actual work. Identical ceilings are not equal observed compute or latency.

## 2. Reversible levels and schedule

At width b, origin o, level l, span s=b*2**(l-1), let m=floor((n-o)/s).
The view covers x[o:o+m*s], with exact literal prefix x[:o] and suffix
x[o+m*s:] retained. A view requires m>=2; otherwise record INELIGIBLE_SHORT.
At level 1, each distinct b-bit word is a literal dictionary entry. At the next
level, group consecutive lower-level symbols in pairs; each distinct pair has
one Concat rule referencing the lower dictionary. Assign new IDs in first
appearance order. Never encode the binary spelling of an ID as original content.

An odd trailing symbol moves into the exact input suffix for the higher-level
view. No bit is dropped and no dictionary of discarded tails is assumed free.
Build each higher dictionary through the paired lower-level entries, preserving
sharing. Store reversible mappings and occurrence spans in observational records.
Only reachable rules are serialized; intermediate whole token streams are not
all transmitted in addition to the top stream.

Enumerate views by (level ascending, width ascending, origin ascending). For
A1/A2 use only their allowed levels/widths. If a lower level is saturated (k=m),
skip its descendants with SATURATED_REPETITION_BRANCH: grouping unique symbols
cannot introduce exact repeated phrases on that path. This is a restriction on
this repetition search, not a statement that the input/dictionary lacks structure.
When k=1, serialize its proposals then stop that path with SINGLE_SYMBOL_BRANCH.
No stopping because a previous view failed to improve; gains can be nonmonotone.

## 3. Proposals per view, in this exact order

Use one NodeFactory for a view and the existing `to_model`/wire serializer.
For all proposals, prepend the exact prefix and append the exact suffix, omitting
empty pieces. A single child needs no Concat. Expand and decode every distinct
admissible full-input archive back to x before accepting it. A decode discrepancy
is fatal INVALID, not a failed candidate that search may silently ignore.

G0: reconstruct the ordered top-symbol stream through the nested dictionary.
Replace each maximal consecutive run of the identical top symbol by Repeat when
its count is at least two; concatenate the resulting children left to right.

G1: call the existing `candidates.pair_grammar` on the top integer-symbol stream,
first_id=k, max_rules=64. Rebuild its returned rules as Concat of the referenced
dictionary/rule nodes. Apply the same consecutive-run construction to its final
start stream. Reuse the owner algorithm and its ties; do not reimplement it.
The intermediate dictionary depth and the pair-grammar rule depth are different
quantities and must be reported separately.

G2/G3: occurrence-gap templates. For each symbol w form sorted J(w), its top-token
positions. Pool consecutive positive differences J[i+1]-J[i] across symbols.
Rank distinct gap values by (descending count, ascending gap); take the first
two p satisfying 1<=p<m. A proposal uses the first p top symbols as a template
T; construct Repeat(T, floor(m/p)) followed by the first m%p top symbols of T.
The template uses exact dictionary expansions. Compare this predicted core to
the actual core in bit coordinates, and Patch all differing positions. If more
than 64 bit flips are required, record PATCH_LIMIT_REJECTION and no archive.
Then wrap the prefix/suffix outside the patch. No consensus fitting, gap imputation,
omission of exceptional bits, new mask opcode or free dictionary is permitted.
If no gap qualifies, record NO_GAP_TEMPLATE; it is not an error or numeric zero.

G2/G3 are an exact use of occurrence-index analysis within today's binary grammar.
They do not assert that an arithmetic progression of one symbol determines the
intervening symbols: the full reconstruction and paid patches test that claim.
More general multi-symbol L/Omega placement is deferred where the grammar lacks
an operator; keep token coordinates distinct from original bit coordinates.

## 4. Selection and failure isolation

The parent persists and verifies A0 before launching augmentation. Augmentation
starts with that archive as incumbent, offering complete candidates in the above
order. Replace only for strictly fewer bytes; retain the earlier incumbent on a
tie. Atomic parent-visible checkpoints preserve valid candidate archives and their
traces. On a normal work cap, return the best completed archive. On a 30 s/1 GiB
child breach, retain the best parent-verified checkpoint, or A0 if none exists,
and explicitly label the breach and unfinished work.

An augmentation crash, corrupt checkpoint or decode mismatch is INVALID evidence,
even though the parent can still preserve A0. A legitimate watchdog fallback is
valid deployed output, not proof that the candidate search completed. Missing
jobs are INCOMPLETE, never zero-cost jobs. INVALID takes precedence. If A0 is
unavailable or invalid, skip dependent jobs and report their unavailability.
Verify the saved A0 input hash, length and decode before any use as incumbent.

This construction makes a valid composite archive no longer than its retained
baseline. Such non-regression is an engineering invariant, not a scientific
discovery. Running A0 and then augmentation incurs both costs. Reusing the one
A0 run across ablations saves experimental work; attribute its entire measured
cost to each hypothetical deployed composite, never call that cost free.

## 5. Width-by-level gap map and explanations

For every eligible view store b, origin, level, span, m, k, k/m; top token stream,
dictionary rule references, original spans, prefix/suffix lengths; requested,
rejected, duplicate, serialized and decoded counts; complete root costs and
selection; time and observed resource charges. Store unavailable metrics as null
with a reason. Use a distinct observed status for cap-blocked/not-reached views.

Three meanings of “gap” must remain separate:

1. Occurrence gaps: for each symbol the J(w) list and consecutive differences.
   Its modal gap is the most frequent difference, tie smaller; irregular fraction
   is differences unequal to that mode divided by the difference count. If there
   are no differences, both are unavailable. Report pooled gap counts as well.
2. Weak repetition support: union of spans of singleton top symbols plus the
   view's prefix/suffix, normalized by n; show their locations. This is a proxy
   for support under this vocabulary, not unexplained causal information or
   irreducible complexity. Dictionary internals are not captured by this proxy.
3. Description gap: view's shortest valid archive minus A0 bytes, and change
   relative to the same path's preceding evaluated level. Distinguish “no shorter
   candidate among evaluated proposals” from no admissible candidate, unvisited
   view or exhausted resources. Plot the full map; do not infer a universal first
   bad word length or monotone threshold from these finite observations.

For dictionary contents record each unique word's exact owner `shortest_period`
and whether it is a complete repeat (length divisible by period). This is a
bounded content diagnostic, not a new uncharged encoder or proof of optimality.
It illustrates why an all-distinct token stream can still have structured words.

Explain each selected augmentation archive as its actual reachable DAG plus
dictionary/span provenance and the byte ledger, reconciling every archive byte.
Depth caused merely by forced grouping must not be called discovered nesting.
Report reused nonterminal rules/occurrences and actual lower-cost candidates.
Per-level BDM is optional only as a saved-input diagnostic explicitly outside the
selection rule; do not run new BDM sweeps in this phase or use entropy as code cost.
