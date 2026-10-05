# Multilevel abstraction: assessment and next design

Date: 2026-10-04. Status: concept review, not an executable study protocol.
Source: notebook 19, section 3b, code and retained outputs; not re-executed.
No changes to the user's notebook or builder. Implementation remains delegated
to Claude Code through a later, fully specified protocol.

## Judgment

Pursue this as a candidate search representation for HID. It can expose ordered
relationships among reusable words over larger spans, then repeat the analysis
on phrases of those words. It has not yet demonstrated an improvement in full
archive cost, computation, or causal recovery. The accepted search-v2 comparison
remains inconclusive; the harmful k=4 boundary experiment does not test this idea.

The initial target is better discovery within the existing grammar, not a new
wire format. HID already has shared DAG nodes, Concat and Repeat, index-mask
descriptions, and a RePair-style pair-grammar proposer/baseline. Therefore a new
experiment must isolate what multilevel word/index analysis adds beyond those
existing mechanisms. Recursive phrase replacement has established precedents,
including [SEQUITUR](https://arxiv.org/abs/cs/9709102); recursion alone is not a
novelty or superiority claim.

## What section 3b actually demonstrates

The retained alternating/random-order example contains the same 1,000 twelve-bit
words and the same counts. Plain block BDM is 69.15 for both; BDM on the ordered
token stream is 41.62 versus 2,699.19. The transformed windows include several
original words, exposing order that the original block histogram discards.
Those values describe the transformed representation, not complete encodings
of the original inputs. Existing period/Repeat mechanisms may already solve
this particular example; it is a mechanism illustration, not evidence of an
advantage over HID or the portfolio.

The worked 48-bit example becomes a 24-bit token stream, but its three four-bit
dictionary entries already add 12 bits before headers. Its abstracted BDM also
increases from 31.072 to 33.816 under a different block length. Neither the shorter
stream nor comparison of those BDM values establishes a compression gain.

Three distinct example families acquire exactly the same level-3 token stream
when every word is unique. Their distinctions remain in their dictionaries.
Canonical labelling gives reproducibility, not a representation-independent
complexity value; the notebook's labelling example varies by 5.9%.

## Interpretation and implementation limits

1. Narrow “costs nothing where it does not [find structure]” and “reduces work
   exactly where structure exists.” Scanning, dictionary construction, search and
   dictionary transmission cost resources. Random inputs can have repeated short
   words; short codes do not certify useful structure. Measure total runtime,
   memory and serialized cost, including unsuccessful attempts.
2. Lower correlation with word entropy does not by itself mean a better complexity
   estimate. The claim that the correlation gap “is not noise” needs an explicit
   analysis; the constructed order contrast already supports the narrower claim.
   These foils are marginal bit/word entropy, not all sequence-aware entropy models.
3. Vocabulary saturation can stop a repetition-only token branch. It is not proof
   that no useful structure remains: distinct words can be successive counter
   values, transforms, or share internal structure. The ordered dictionary also
   deserves analysis, within a fixed budget.
4. Retain every remainder. The illustrative `levels()` drops the initial partial
   word and ungrouped tails. A lossless method must encode these and preserve
   lengths, partitions, dictionary boundaries and expansion order. Explicitly
   define empty input, singleton alphabets and code widths above the CTM limit.
5. Overlapping windows require span bookkeeping and a consistent reconstruction
   rule. For q windows of width b and step s, the covered contiguous span is
   b + (q - 1)s, not qb. The notebook's `view_bits` uses qb also for the overlap
   setting. Shuffling overlapping windows need not yield a realizable input.
6. Charge the full decodable model. A suitable conceptual accounting is header
   plus hierarchical dictionary rules plus the top sequence plus tails and
   exceptions; shared rules are paid once. Do not sum standalone BDM scores or
   all intermediate streams. Prefer the actual existing wire serializer and
   independent decoder as the final cost and validity authorities. This follows
   the model-plus-data requirement of [MDL](https://web.mit.edu/6.433/www/handouts/minimumdescriptionlength.pdf).

## How to use our index analysis at each level

Maintain an ordered stream of integer symbol IDs with a reversible dictionary
and a map from each occurrence to its original bit span. At level 1, symbols
represent input words; at later levels they represent phrases of lower-level
symbols. Canonical first appearance can fix labels. Search on symbol equality
and positions, rather than treating accidental binary patterns in the IDs as
properties of the original data.

For a symbol w, form its occurrence set J(w) = {i : token[i] = w}. Apply the
existing index-set ideas to candidate regularities in these positions: repeated
spacing, periodic placement, repeated positional templates, and relationships
among phrases. Also examine word content through the dictionary. Keep token
positions and original bit coordinates distinct. Their conversion is simple
for equal-width blocks and requires explicit spans for variable-length phrases.

Compile any proposed expansion into existing legal HID nodes, then serialize
and decode to the original input. Concat/Repeat with shared children already
represents a useful subset. Existing schema/index nodes represent binary
outputs; they are not automatically a generic multi-symbol placement operator.
If an occurrence-set proposal cannot be expressed faithfully in the current
grammar, defer it or specify a separate grammar-change experiment. Do not give
it a hypothetical code length while comparing it to real archives.

A simple witness is A = a long word, B = another long word,
P = Concat(A, B, A), and X = Repeat(P, r). A higher-level search can work on
the phrase P while retaining the exact dictionary for A and B. Harder nested
examples are needed because a simple period may already be found by HID.

## Recommended next bounded experiment

Start with a feasibility and ablation phase on disclosed development inputs,
before another prospective confirmation. The future Claude packet must fix:

- Initial word partitions, canonical IDs, maximum levels, phrase proposals,
  deterministic scheduling/ties, saturation behavior and tail handling. Begin
  with non-overlapping words; defer overlap until reconstruction is specified.
- Three arms: unchanged k=1; one-level abstraction; recursive abstraction using
  the same initial representation. Include the existing pair-grammar comparison
  and full portfolio so familiar grammar compression is not mistaken for a new
  improvement. Use an equal-budget comparison to isolate recursion's effect.
- A completed k=1 incumbent retained outside the additional search's destructive
  failure scope. A shorter valid archive may replace it; ties retain it. Its
  cost is charged. Keeping this incumbent prevents archive-length regression
  only if it remains available through final selection; whole-worker timeout
  can defeat that guarantee unless persistence/fallback is designed explicitly.
- A finite additional work budget, including dictionaries, rejected candidates,
  serialization, decoding and trace overhead. Report the extra resource cost;
  do not call baseline-plus-extra-work an equal-cost improvement.
- Fixtures for nested motifs, fixed-count shuffled order, random strings,
  all-distinct structured words, shifted partitions and ragged tails. A
  dictionary-plus-top-stream round trip must recover every input bit. Test
  depth-one equivalence and cases where dictionary overhead erases apparent
  token savings. Include a relabelling check for symbol-level search decisions.
- Full archive bits per original input bit as the compression endpoint; runtime,
  memory, rule reuse and recovered hierarchy as separate outcomes. BDM at each
  level is exploratory diagnostic information, not the optimization oracle or
  a substitute for the endpoint. No choosing depth after inspecting confirmation
  results. All search-v3a strings are now exposed development evidence.

Only after this phase has a fixed implementation and convincing engineering
evidence should a new frozen protocol use fresh namespaces for confirmation.
Do not simultaneously add a cap-aware k=4 boundary variant or TILE grammar change;
each would introduce another mechanism to disentangle.

For the causal objective, distinguish exact representation from identification
of a generating mechanism. A useful multilevel factorization is not itself
causal evidence. Any claim of better causal deconvolution needs its own defined
recovery target, appropriate known-mechanism or intervention evidence, and an
explicit mapping between original variables and the higher-level representation.
