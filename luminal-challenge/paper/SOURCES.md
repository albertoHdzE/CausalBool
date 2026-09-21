# Primary-source and claim notes

Checked 21 September 2026. These are scope notes for manuscript review, not a
claim that the bibliography establishes scientific novelty.

| Source | Use in this draft | Boundary |
|---|---|---|
| [Pinned Luminal reference](https://github.com/luminal-ai/interview/tree/573b8a85f4bdb8c3d8ba9f180d5f98dac875c902), retained `.reference/README.md` and `machine.py` | Machine semantics and official score | Public cases only; no private result |
| [Bryant, 1986, author-hosted paper](https://www.cs.cmu.edu/~bryant/pubdir/ieeetc86.pdf) | Ordered decision diagrams, sharing and representation-sensitive costs | No measured BDD comparison or universal dominance claim |
| [Castañeda Lozano et al., Unison](https://arxiv.org/abs/1804.02452), [author-hosted manuscript](https://chschulte.github.io/papers/castanedacarlssonea-toplas-2019.pdf) | Prior integrated allocation/scheduling via constraint programming | Different machine and transformations; its results are not our benchmark |
| [Shannon, 1948, primary paper](https://people.math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf) | Entropy and communication-capacity context | No communication-channel model or achieved Shannon limit in this compiler |
| [Shannon, 1949, primary paper scan](https://deeplearning.cs.cmu.edu/S22/document/readings/Shannon49.pdf) | Historical switching-circuit context for cofactoring | Browser indexing returned the paper but full scan extraction exceeded the tool limit; the displayed cofactor identity is justified directly by its two Boolean cases |
| [Wolfram, A New Kind of Science, p. 622](https://www.wolframscience.com/nks/p622--human-thinking/) | Motivation from exact retrieval, ordered lookup and hashing in his memory discussion | No biological, associative-memory or cellular-automaton implementation is claimed |

The subset-counting bound and flat-cover parity lower bound are proved in the
draft. They concern descriptions of sets and a specified representation. They
do not establish running-time lower bounds for the compiler. The minimum-anchor
proof concerns complete covers; a depth-first joint-query witness is not
claimed to be the global minimum index.

Empirical claims come from the final lead's retained data. The figure generator
recomputes public and generated scores, checks per-version metric equality and
verifies the six generated improvements. Bootstrap and full timings, pooled
medians and geometric means of per-program ratios are separately labelled.
The draft makes no measured representation-size or scaling claim from process
RSS. Earlier same-production-code runs remain visible rather than being
replaced by the fastest result.
