# Representation, retrieval, semantic locality, and noise

Discussion record: 2026-09-19. These are distinctions and proposed research
directions, not conclusions established by the Luminal pilot.

## What the compression objection should mean

Compactness is not a separate submission requirement in Luminal. The target
scratch footprint affects the score; the compiler's symbolic model is a
different object. The implementation must also finish within its time budget.

The existing compression evidence is relevant. The stored Doppel table at
`doppel-challenge/paper/response_v1/generated/lengths.tex` reports, for example,
N=12: median 419 programme bits versus 49,152 raw output-table bits, about 0.8525%.
For N=10 it reports 339/10,240, about 3.3105%; the worked example is 325/10,240.
This does not identify the user's approximately 1.2% result as wrong: the source
experiment, aggregation and denominator need to accompany that number.

A small ratio measured on one family is not a universal scaling guarantee.
More specifically, a program for several separate output columns and a program
for their conjunction with scheduling/resource/quality constraints are different
representation targets. Shared-variable correlations introduced by conjunction
can change representation size. A fixed fraction of an exponential table would
still be exponential; bounded local rules can yield much stronger savings, but
one must measure or prove how the *composed query* scales.

## Retrieval already incorporates the criteria

For candidate encoding x, define

    A(x) = Valid(x) AND Cycles(x) <= T AND Scratch(x) <= M.

Any index returned for output A=1 already meets the criteria. A separate quality
check is not mathematically necessary. The independent validator is used to
catch implementation defects, not to add a criterion absent from the query.

For an existing ordered decision program with m reachable nodes, b input bits,
and maximum accepting-path depth d <= b, one witness can be retrieved by
following a nonzero branch at each decision in O(d) node visits. An accepting
path also gives a decimal anchor and free mask. All subset sums of the free-bit
weights are sumandos; they need not be enumerated to return the family.
Bit-level time also accounts for forming a b-bit address. Reporting all K
individual members necessarily has an output-size cost.

That explains the user's direct-lookup observation. The costs still to measure
are constructing local predicates, composing the decision program, intermediate
allocations, final storage and retrieval. The adapter in this pilot explicitly
measures those stages rather than equating retrieval time with total solution time.
Its BDD backend is established machinery already used in the repository.

## Wolfram: feature-sensitive retrieval

The matching passage is *A New Kind of Science*, Chapter 10, Human Thinking,
especially pp. 622–623:
https://files.wolframcdn.com/pub/www.wolframscience.com/nks/nks-ch10.pdf
The related note is:
https://www.wolframscience.com/nks/notes-10-12--hashing/

Wolfram discusses deriving memory lookup codes from data and keeping items
together when they differ only in features considered irrelevant. He explicitly
distinguishes this from ordinary hashing, which need not preserve similarity.

Our proposed connection is a feature map phi and a schema whose free coordinates
do not change the queried property. This is analogous to invariant feature
representations and associative lookup. The analogy with embeddings is useful,
but decimal indexing alone does not establish semantic geometry: binary 0111
and 1000 are numerically adjacent while differing in all four positions.
Meaning and task relevance require a defined feature map/equivalence relation.
An index addresses a combinatorial input state, not automatically a physical
storage location or a semantic neighborhood.

A possible compiler application is caching solutions to canonically equivalent
local constraint problems. Similarity could suggest a candidate, but exact
constraint checking remains necessary before reuse. Isomorphic/equivalent
problems can support exact reuse; approximate similarity alone cannot.

## Shannon: robust coding of the representation

Primary reference: Shannon, *A Mathematical Theory of Communication* (1948):
https://web.mit.edu/6.976/www/handout/shannon.pdf
For the binary symmetric channel and coding theorem see:
https://www.mit.edu/~6.450/handouts/6.450book.pdf

For independent bit flips of probability p (0 <= p <= 1/2), capacity is
C = 1 - H2(p), where H2(p) = -p log2(p) - (1-p) log2(1-p).
To transmit k information bits in n channel uses, arbitrarily small error is
asymptotically achievable at rates k/n < C using suitable codes. The noise model
and desired finite-block error probability matter: capacity alone does not give
an exact redundancy count or an efficient encoder/decoder.

This preserves a distinguishable encoded message; semantic meaning comes from
the agreed representation and decoder. A natural construction is:

    object -> task-relevant features/schema -> redundant codeword
    noisy codeword -> channel decoding -> exact schema/index query

Feature mapping brings equivalent information together. Error-correcting coding
separates distinct messages sufficiently to recover from corruption. These can
coexist at different layers; they are not the same geometric operation.
Schema-free bits already tolerate variation exactly. Errors in essential bits
require an additional noise model and recovery mechanism. One can also add a
Hamming-distance bound to a Boolean query for approximate retrieval, but the
resulting ambiguity and decoding cost must be measured.

The Luminal machine is deterministic, so error-correcting codes are not required
for this challenge and are not implemented in the pilot. They motivate a
separate robustness experiment, not a proof that constraint composition is
compact or easy. A complexity paper needs a precise problem family, input-size
measure, preprocessing/query/output costs and supported bounds.
