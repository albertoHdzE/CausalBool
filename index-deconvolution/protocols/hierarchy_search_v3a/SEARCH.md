# Fixed algorithm and telemetry contract

## 1. Two independent full-method arms

`hid_full`: accepted search-v2 full arm, boundary refinement seed count k=1.
`hid_refine4`: identical full method except k=4 under the schedule below.
Each independently starts with the complete raw archive and reruns L, P, C, D,
G, B in order. No previously encoded arm, saved incumbent, cross-arm cache or
generator metadata enters inference. Both receive bits and frozen configuration
only. Complete archive bytes include every header, model and reference field.

Keep stages L–G, period grids, residual gates, candidate caps, NodeFactory,
strict full-incumbent replacement and earlier-incumbent tie rule unchanged.
Do not add a second k=1 search inside `hid_refine4` as a free safety incumbent.
Wider refinement can choose a different path and finish worse; count such cases.

Use one boundary-search implementation with an explicit policy. Preserve the
existing `BoundaryConfig()` and search-v2 configuration serialization/hash for
old callers: do not add a default-valued key to their serialized config. Bind
the new arm's k=4 policy, schedule and trace schema into its own config hash.
A thin v3a adapter may call a shared internal orchestrator; it may not copy L–G
or segmentation into a competing implementation. Study registration, not method
name prefixes or module-global monkeypatching, selects the policy.

## 2. Unchanged boundary mechanics

Use current `BoundarySearch.leaf` and `evaluate` semantics unchanged. Start with
one leaf over [0,n). Parents are eligible at length >=64, children at least one
bit; stop at eight segments. Same literal/shortest-period <=256 leaf heuristic,
sharing, complete serialization, admissibility (4,096 rules/depth 64), caches,
duplicate-archive accounting and independent decode checks.

Caps per invocation, shared across every seed and round: 512 root trials,
2,048 cached leaves, total length charge 256*n. Charge leaves atomically before
their uncached owner call; charge root evaluation as the existing owner does.
Cached partitions, graph-rejected partitions and ties retain existing semantics.
No per-seed budget reset. On a cap, stop immediately and offer the best complete
archive already serialized under the old best_seen/earliest-serialization tie
rule; never finish another seed without charges or serialize an unpaid fallback.

## 3. Exact multi-seed schedule

At each round, current partition/cuts remain fixed throughout proposal evaluation.

1. Enumerate eligible parents left to right. For each, enumerate the same sorted
   distinct coarse positions `{a+1,b-1} union {a+floor(j*(b-a)/32): j=1..31}`.
   Evaluate them in this order. A priced admissible tuple is
   `(archive_length_bytes, parent_start, cut, archive_bytes, resulting_cuts)`.
2. If the coarse phase hits a cap, use the cap exit immediately. Otherwise sort
   admissible coarse tuples by the first four entries (bytes lexicographic).
   Deduplicate only by resulting partition tuple. Select the first min(k,count)
   as a **fixed seed list for this round**. Multiple seeds may share a parent;
   there is no diversity rule or data-dependent replacement of a seed.
3. Each seed owns a local refinement state: original parent [a,b), center c from
   that seed, bracket `[max(a+1,c-ceil((b-a)/32)), min(b-1,c+ceil((b-a)/32))]`,
   and a pool initialized to **all admissible coarse trials of that parent**.
   Add only this seed's refinement trials to its local pool. Other seeds share
   evaluation caches and charges, not their local winner pools.
4. Schedule **level-major, then seed-rank-major**: for level 1 through 5, visit
   active seeds in their fixed rank order. Complete one seed's entire level
   before visiting the next seed. For its current bracket compute
   `step=max(1,ceil((hi-lo)/16))`; evaluate sorted distinct positions in
   `{lo,hi,c} union {c+j*step:j=-8..8}` clipped to [lo,hi].
   Existing cached evaluations still enter the local/global candidate pools.
5. Update that seed's center to the local-pool minimum by
   `(archive_length_bytes, cut, archive_bytes)` after the level. The winner can
   be a previously priced coarse point outside the last bracket, as in k=1.
   At step=1 mark the seed finished. Otherwise its next bracket is
   `[max(a+1,c-step), min(b-1,c+step)]`. At five levels it is finished regardless.
   Do not deduplicate, merge, skip or replace seeds whose paths converge.
6. After all active seeds finish, select the global minimum over every admissible
   coarse and refinement trial by `(length,parent_start,cut,bytes)`. Commit only
   if strictly shorter than the round's current archive. Call the same offer
   callback on commit and final output. On no strict improvement stop.

The k=1 path must reproduce old bytes and deterministic old telemetry. When k=4
finds fewer than four admissible coarse trials, use all available; zero gives
the old no_admissible_trial outcome. The initial graph failure and any decode
disagreement remain fatal, never ordinary raw fallback. Document unresolved
round/seed/level/bracket on cap exits. No additional refinement pass after a cap.

## 4. Direct observational trace

Emit a separate trace sidecar for both HID arms during fixed development and
prospective jobs; add no charged search operation and make no algorithm choice
from the observer. Freeze trace enabled for both arms. Wall/RSS measurements
include its overhead and are labelled as instrumented measurements.

One event per trial request: round, fixed current partition, coarse/refinement,
seed rank where applicable, level, parent interval, proposed cut, resulting
partition, pre/post deterministic charges, cache hit, and outcome. Outcomes
distinguish newly serialized, cached admissible, new/cached graph rejection,
and cap-blocked-before-completion. Store archive length/hash for admissible
evaluations, and an ordered initial/commit/final summary with selected cuts.
Trace position order must match calls, not a post-hoc sorted reconstruction.
Set an 8,192-event defensive bound per B invocation; exceeding it is a trace
implementation failure, never silent truncation. The fixed search is bounded
below this by seven rounds of <=7*33 coarse plus <=4*5*19 refinement requests.

Definitions for saved-trace analysis:

- proposed cut: any recorded trial request, including one blocked by a cap;
- evaluated cut: a request whose partition has a completed priced/archive or
  graph-rejection outcome, including cache hits; separately count newly serialized
  admissible evaluations, since graph rejection is not an encoded candidate;
- returned cut: a cut in B's final selected archive; never call this proposal
  coverage. Report commits separately from best_seen cap output.

No trace record contains family, case ID, generator seed, true cuts or expected
winner inside the inference boundary; the parent attaches case/arm IDs afterward.
For development, compare trace cuts with all retained supplied cuts on all 176
fixed target strings, not only prior witnesses. For each string and each kind
(proposed/evaluated/returned), report numerator and denominator for supplied cuts
within 8 bits; each supplied cut counts once. Report string proportions using
pair-then-cell means and the pooled cut count separately. Empty supplied lists
are explicitly unavailable, never 0/0=0. Also show newly serialized counts, cap
stops and full-arm better/tie/worse counts. No efficacy gate or tuning uses these
statistics. On prospective data traces are cost/search diagnostics only; no new
truth-assisted partition enumeration or oracle selection is authorized.
