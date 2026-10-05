# Fixed dictionary-relations search

## 1. Views and control

Use widths 4,8,12,16,24,32,48,64; origins 0,floor(width/2); levels 1..4.
Enumerate (level,width,origin) ascending. Reuse multilevel-v1 `path_levels`,
canonical first-appearance IDs and exact prefix/core/suffix coverage. A view
has span width*2**(level-1), m=floor((n-origin)/span), and is eligible iff m>=2.
Do not prune descendants for k=m or k=1 in ANY new arm. Record those flags as
diagnostics, not stopping rules. Empty input retains verified A0 with unavailable
normalized diagnostics. Other ineligible views have explicit skipped records.

A0 is unchanged search-v2 `hid_full` k=1. D0/D1/D2 independently augment a completed
A0. All use the same eligible views and G0..G3 constructions from the original
multilevel ViewBuilder. Preserve original prefix/suffix and graph serialization.
Use one NodeFactory per view; dictionary alternatives share that factory. A
view's candidate is a full input root, not the encoded token stream by itself.

## 2. Four deterministic dictionary modes

Build original top dictionary nodes by the existing ViewBuilder: level1 literal
words; higher levels CONCAT of prior-level dictionary entries. Their expansions
w[i] are exact top words, numbered by first appearance.

**O (original):** those existing top nodes.

**P (periodic):** independently for each top word, obtain owner `shortest_period` p.
If p<len(w) and len(w)%p==0, use REPEAT(LITERAL(w[:p]),len(w)//p).
Otherwise retain O[i]. Apply all eligible replacements as a single dictionary
mode. Do not choose between representations using isolated word lengths.
The full input archive decides whether the mode pays. This permits new sharing
of literal period bases across entries. Keep exact repeats only; no truncated
period proposal in this version.

**R(O) and R(P) (relations):** start from the corresponding base dictionary O or
P and process IDs i ascending. Candidate predecessors are j=max(0,i-8)..i-1
(at most eight immediately preceding IDs). All are equal-length top words.
For each predecessor and flags in 0,1,2,3 use the owner's transformation semantics:
complement then reversal, rotation=0. Compare the transformed true expansion
w[j] to w[i] and record the ascending bit positions that differ (word-relative).
These flags are the existing two-bit complement/reversal flags. No rotation
search, synthetic consensus word, cross-view or cross-length predecessor.

An eligible relation has at most eight differing bits and relation-hop depth
1+hops[j]<=8. Base nodes have zero relation hops; this diagnostic is separate
from actual DAG depth. Rank eligible relations by (number_of_flips,j,flags),
ascending, and take exactly the first. Construct using the already resolved
node for j in THIS relation mode, XFORM if flags!=0, then PATCH if flips nonempty.
Identity transforms and empty patches are omitted, using owner simplifications.
If no eligible relation exists, retain base[i], hops[i]=0. Otherwise set hops[i]
to 1+hops[j]. j<i prevents cycles; never reference a discarded donor without
including its reachable graph. Record rejected comparisons, selected relation
and hop depth. A later full-graph depth/rule rejection rejects the root; do not
silently try the second-ranked relation or change the dictionary.

This is a finite candidate heuristic, not an optimal dictionary search. It
intentionally offers full bundles to test joint costs. It can miss mixtures
where only some changes help; record that limit without expanding this phase.

## 3. Arms, proposals, selection and caps

Per eligible view, dictionary modes in order:

- D0: O.
- D1: O, P.
- D2: O, P, R(O), R(P).

For each mode offer G0,G1,G2,G3 in that order, using original top IDs and replacing
only the dictionary node mapping used by ViewBuilder. Import the existing G0 run
construction, G1 owner pair_grammar(max_rules=64), and G2/G3 ranked occurrence-gap
templates with <=64 bit flips in the whole predicted core. This 64 limit is
distinct from the eight flips permitted per dictionary relation. No new top-level
proposal, dictionary rule opcode or hand-tuned word representation is permitted.
Modes that happen to be identical still count as candidate requests.

Common limits: 64 evaluated views, 1,024 full-root requests, 4,096 reachable rules,
DAG depth64, owner pair-grammar64 rules/view/mode. Missing gap templates consume
no root request; duplicates, patch-limit and graph rejections do consume one.
Maximum scheduled requests are D0=256,D1=512,D2=1,024, before missing templates.
Common ceilings do not mean equal realized work. Predecessor comparisons and
dictionary construction count in worker time and work counters; none is free.

Count and record serialization attempts even when modes duplicate one another.
Independently decode every distinct serialized archive to the complete input;
reuse validated byte-identical archives, including A0, without re-decoding.
All reachable dictionaries, shared nodes, references, exceptions, prefix, tails
and headers are paid by existing wire serialization. Never sum standalone word
archive costs or BDM values as the selection criterion. No provenance sidecar
may be necessary to decode. Fatal decode mismatch means INVALID.

Select only strictly shorter full archives, retaining earlier incumbent on ties.
Atomic verified checkpoints must survive watchdog termination. Because D1/D2
include earlier modes, completed unlimited-by-watchdog searches cannot lose
against their nested mode subsets. Treat this as an engineering invariant, not
evidence of benefit; a terminated search can miss a later subset candidate.

## 4. Diagnostics and explanations

Keep the previous three gap meanings separate: token occurrence spacing, weak
repetition support, and full archive description gap. Reuse diagnostic owners.
Every eligible view now receives diagnostics, including descendants previously
pruned. Do not compare different denominator populations without displaying them.

For each view/mode keep true input spans, top ID stream, exact dictionary expansion
hashes, O/P/relation construction metadata, p and complete-repeat flags, predecessor
comparisons (<=32 per entry), flips, relation hops, actual DAG depth, reachable rule
count, archive bits/hash, duplicate/rejection/decode status, request ordinal and
strict-improvement history. Comparison records may use compact arrays; record
flip positions for selected relations, and flip counts for rejected comparisons.
No need to store all rejected archive bytes, but retain all selected/checkpoint
archives AND the shortest serialized candidate per view/mode, even when it loses
to A0. Deduplicate stored bytes by hash. Reporting must not rebuild candidates
to obtain example ledgers; it reads those saved bytes and construction provenance.
Record mode-specific proposal gains vs A0 and vs O for the same view, with
unavailable values null, never zero. Do not assert positive dictionary savings
merely because a word has a period or a close predecessor.

Use owner archive_ledger for selected outputs and representative best candidates;
cost categories must sum exactly to the full archive. A shared DAG has no unique
per-word cost allocation: display actual rule costs/reference reuse instead of
double-counting shared nodes. Mark imposed grouping depth separately from actual
reuse or relation chains. These are structural explanations, not causal effects.
