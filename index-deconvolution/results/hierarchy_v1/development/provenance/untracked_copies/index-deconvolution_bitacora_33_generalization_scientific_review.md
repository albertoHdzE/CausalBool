# Bitacora 33 — Scientific review and protocol for generalisation

Date: 2026-10-01
Status: assessment complete; audit measurements reproduced; proposed method and benchmark not yet implemented.

## 1. Scientific judgement

The shifted-zero probe is a useful diagnostic of **fixed, non-overlapping BDM**.
The promising research direction is a lossless, automatically inferred hierarchy
that represents relationships between patterns, their occurrence positions, and
their order. Notebook 15 does not yet establish that such a hierarchy can be
discovered automatically, that it compresses better than established alternatives,
or that it generalises beyond the examples used to design it.

The central hypothesis should be:

> A fixed inference procedure using index-set schemata and compositional rules can
> discover descriptions that reconstruct unseen binary sequences exactly and use
> fewer transmitted bits than specified baselines on specified families, including
> families with structure at several scales.

This is a testable hypothesis, not a result. Exact reconstruction, economical
description, recovery of a generating rule, prediction, and causal identification
are separate claims. A finite string generally admits several generators and
arbitrarily many continuations. An inferred description is not evidence that its
generator is the unique historical or causal mechanism.

## 2. What survives scrutiny

- The period-9 identity for the 64-bit shifted-zero concatenation is exact.
- Fixed aligned BDM depends on the multiset of blocks and cannot distinguish their
  permutations. This follows directly from its formula.
- Different partitions can expose different repetitions, producing large score
  changes without changing the object.
- Repeated higher-level units can be described once with a repetition count.
- The Hamming distances between distinct single-zero words are all two. These
  distances alone contain no information about the intended shift order.

These support the motivation. They do not establish a new estimator of K.
The verified BDM reference is Zenil et al., *Entropy* **20**(8), 605 (2018),
DOI 10.3390/e20080605. Its discussion explicitly includes block-permutation
invariance, overlapping decompositions, and boundary conventions. Position the
probe as a concrete illustration and extension of that discussion.
[Original paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC7513128/).

## 3. Corrections needed before stronger claims

### 3.1 Python characters are not a binary code

The 17-character expression for the 64-bit string occupies **136 UTF-8 payload
bits**, before framing. It is shorter than the *textual Python literal*, but does
not demonstrate compression relative to a packed 64-bit literal. A compact custom
instruction language could do better; its encoding must be specified and measured.

Executing each expression correctly is valuable verification. It does not make
its character count a bit-valued bound on K. State the program encoding, fixed
decoder, framing convention, and available libraries. Do not claim an absolute
gap between BDM and a Python upper bound while declaring their units incomparable.
Slope comparisons also require a specified scaling parameter and fixed encodings.

The generator is constant-sized only over this finite, single-digit parameter
range; the run-family k=0 case is actually a different 10-character literal.
For growing inputs use a statement such as

`K(f(n,k)) <= K(n,k) + c_f`,

and encode n, k, counts, and any other instance-specific inputs. Distinguish
conditional complexity with supplied parameters from unconditional descriptions.

### 3.2 Raw minimum BDM does not identify the period

Fresh measurements using the shared owner and pybdm 0.1.0:

| Object | BDM at b=3 | BDM at b=9 | Minimising b over 2..12 |
|---|---:|---:|---:|
| A72, the period-9 string | 17.842 | 24.615 | **3** |

Allowing b=1 chooses 1, with a score of 14.029. All three partitions cover all 72
bits, so this is not caused by discarded tails. The proposed raw minimum is not
a consistent comparison of complete descriptions: changing b changes the
dictionary and how much ordering information is omitted.

Use complete code lengths to select a model. For BDM discrimination experiments,
calibrate each configuration against matched controls and run the entire selection
procedure on every null sample. Such calibration creates a diagnostic statistic,
not automatically a decodable compressor.

### 3.3 Tail dropping changes the object

The explicit `remainder="drop"` flag prevents a silent implementation choice, but
does not make whole-object comparisons valid. In the scratch P1–P3 table:

- A24 at block 9 scores 18 of 24 bits, discarding **25%**.
- AX64 and AXM64 at block 12 score 60 of 64 bits.
- P2 at block 12 scores 144 of 152 bits.
- P3 at block 12 scores all 192 bits.

Therefore the reported P3/AXM ratio mixes partition effects and different coverage.
For compression, every bit must be decoded. For BDM diagnostics use an explicit
full-coverage boundary policy, and separately retain historical drop-policy scores
with their coverage. Padding, clipping, rotations, phase, and original length must
be stated and, where necessary for decoding, encoded. Overlapping scores are also
diagnostics, not additive transmitted bit counts.

### 3.4 Fix several specific statements

- P3 at block 12 has **16 blocks, 15 distinct**; one occurs twice. The statement
  that no block repeats is false. The lcm explains alignment recurrence, not the
  absence of accidental repeated contents.
- The labels A and a1 refer to different objects in the notebook and scratch
  section. Use A64, A72, A24, AX64, and AXM64, with one explicit indexing convention.
- The 0.805-bit CTM spread is not an estimated error interval. The invariance
  theorem supplies no known numerical tolerance here. Report a table-dependent
  distinction without interpreting it as a measured difference in true K.
- A specified one-position rotation changes K by at most a fixed program constant.
  An arbitrary rotation additionally requires its index, at most
  `ceil(log2 n) + O(1)` bits when n is available from the decoded object. The
  implementation constant cannot simply be omitted. Permutation-rank bounds have
  analogous conventions and overhead; structured permutations may be much cheaper.
- CTM scores local structure. The defensible criticism concerns missing
  **relationships and order between blocks** in the aligned aggregation. The
  unqualified phrase “BDM rewards only repetition” is too broad.
- The truncated author quotation in bitacora 32 should be restored from its source
  or marked incomplete, never reconstructed from conjecture.

### 3.5 The finite slope is not an asymptotic law

The 21.78-bit regression summarises 18 constructed points with distinct 8-bit
words. They are not 18 independent observations of an unbounded scaling law.
There are only 256 distinct 8-bit words.

For fixed block size b and a finite CTM dictionary, with m complete blocks,

`BDM_b(x) <= C_b + 2^b log2(m)` for m >= 1,

where `C_b` is the sum of the dictionary CTM values. This follows by bounding each
multiplicity by m and the number of distinct words by 2^b. Thus fixed-b BDM grows
at most logarithmically in length asymptotically, including on fair random strings.
It cannot have the claimed linear growth for arbitrarily long inputs. This is an
algebraic limitation of the stated score, not a newly measured benchmark result.

A complementary exact fact: a multiset of m blocks with counts n_j has
`m! / product(n_j!)` possible orderings. Aligned BDM assigns them one value.
An arbitrary ordering can be transmitted by a rank in that class; simple orders
may be encoded much more cheaply. A proposed hierarchy must account for this
ordering information explicitly.

## 4. The bridge to decimals and sumandos must be constructive

Keep the authoritative definition in `GOVERNANCE/GLOSSARY.md` §1d: sumandos are
fillings of a schema's own don't-care positions, including positions on connected
inputs. They are not noise or a synonym for any arithmetic occurrence sequence.

For an ordinary schema sigma over d address bits, write its represented set as

`D_sigma = {ell_sigma + sum(e_j * 2^j for j in F_sigma): e_j in {0,1}}`,

where F_sigma contains the free positions and ell_sigma fixes the other positions.
Specify unions, overlap semantics, coordinate order, domain length, and polarity.
Then show how the hierarchy maps its objects into these representations and back.

The shifted-zero example makes this obligation concrete. Its zero addresses are

`0, 9, 18, 27, 36, 45, 54, 63`,

or in six-bit binary,

`000000, 001001, 010010, 011011, 100100, 101101, 110110, 111111`.

They have the form `abcabc`. No two are Hamming-one neighbours. Every non-singleton
ordinary wildcard cube contains a Hamming-one pair, so **a cube cover of this zero
support in the original coordinates needs eight singleton cubes**. There are no
stars in that cover, despite the simple period. This does not imply that the whole
string lacks a compact representation: encoding its complementary support, using
relations between coordinates, or introducing a transformation may help.

It does show that “recover period 9” is not automatically “recover compact
sumandos”. Arithmetic progressions, linked coordinates, and coordinate transforms
are possible extensions; define and charge for them explicitly. A72 also requires
an explicit non-power-of-two domain policy. Converting an arbitrary string into a
truth-table ordering introduces a representation choice, not observed causal inputs.

## 5. The method I would build

Use a directed acyclic graph of reusable rules, with **ordered children** for
concatenation. A DAG permits shared substructure without duplicating it in a tree.
Presence vectors describe membership; they do not specify multiplicities or order.

Start with a small frozen language: packed literals, concatenation, repetition,
schema-based occurrence sets, and arithmetic progressions. Add shifts, complement,
or other transformations only with defined semantics and codes. Avoid adding an
operator every time a benchmark exposes a weakness without then moving evaluation
to a fresh held-out benchmark.

For a fixed decoder U, select among searched candidates by actual encoded length:

`J(x,M) = L(format,n) + L(M) + L(ordered uses | M) + L(corrections | M,uses)`.

M includes rules, topology, coordinate maps, and parameters. Every field has a
decodable encoding. Corrections are a separate exact error channel, never called
sumandos. The correction channel may encode error positions by a combinatorial
rank and their values, with the error count and framing also included.

Require `decode(encode(x)) == x`. Always offer a packed-literal mode, so a bad
model costs at most literal size plus the declared header. Record the encoded
length rather than an informal proxy such as node count, decimal digit count,
number of parameters, or graph depth. A decoder shared across the whole study is
fixed infrastructure; a dictionary learned for an individual object must be sent.

This is a concrete application of two-part minimum description length; it is not
equivalent to computing K. [Grunwald's MDL tutorial](https://arxiv.org/abs/math/0406077).

Select word boundaries and abstraction depth by net savings, not the first
appearance of a star. Do not force a pyramid onto unstructured data. A bounded
search should consider joint changes, since a locally unprofitable rule may enable
a profitable higher-level reuse. Report search budget and call the result “best
found”; neither a greedy cover nor a bounded search certifies global optimality.

Hamming distance can propose candidates, but it should not determine the hierarchy.
Prefer a relation when its encoded transformation plus corrections is economical.
Huffman coding remains a legitimate downstream code for a specified symbol stream;
it does not discover the transformations or determine the original order. The
categorical rejection of Huffman in bitacora 32 should be narrowed accordingly.

## 6. Benchmark that could falsify the advantage

Freeze the decoder, search budget, operators, selection procedure, and primary
outcome before the confirmatory run. Notebook 15 and P1–P3 are development examples.

| Test family | Purpose |
|---|---|
| Periodic words, including periods 13, 17, 31 and ragged lengths | Detect dependence on CTM's 12-bit ceiling or convenient divisibility |
| Repeated random macros with ordered and shuffled macro streams | Separate discovery of reusable content from coding its order |
| Nested repetition and transformation families at varying depths | Test the specific value of hierarchy and relations |
| Arithmetic occurrence sets and schema-generated sets | Test both representations and their conversion cost |
| Nonperiodic computable sequences, including Thue–Morse and CA traces | Reveal the limits of the fixed language; success is not presumed |
| Bit-flip noise, insertions/deletions, and concatenated regimes | Measure degradation and exact correction costs |
| Fair IID bits; biased IID and Markov sequences | Distinguish false discoveries from ordinary statistical compression |

Use independent generated strings, multiple sizes (for example 2^8 through 2^16),
ragged companions, unseen parameters, and held-out generator families. Reserve the
largest sizes for transfer tests. Rotations and shuffles of one string are
dependent controls, not independent replications. Use pilot runs to choose sample
size for a desired confidence-interval width, then freeze that number.

Required comparisons:

1. Packed literal, run-length/gap encoding, and a direct period detector with its
   complete code. Rediscovering a period must beat the corresponding simple baseline.
2. A grammar compressor such as SEQUITUR and a conventional lossless compressor on
   packed bits. Count headers and grammar serialization consistently. Recursive
   phrase discovery already exists; the novelty must be demonstrated in the
   index-set/transform extension or its discovery performance.
   [SEQUITUR paper](https://arxiv.org/abs/cs/9709102).
3. Adaptive Bernoulli and finite-order Markov codes. Biased IID strings should
   compress; success beyond the statistical baseline is the relevant comparison.
4. BDM with fixed aligned, overlapping, and full-coverage boundary configurations,
   plus a predeclared adaptive diagnostic. Compare discrimination and stability,
   without treating BDM scores as transmitted bytes.
   [PyBDM theory and boundary policies](https://pybdm-docs.readthedocs.io/en/latest/theory.html).

The primary compression endpoint is the paired difference in complete encoded bits
against the strongest preselected code baseline, with confidence intervals over
independent strings and results broken down by family and size. Also report exact
round-trip rate, runtime, peak memory, and timeouts. Assess rule recovery against
equivalence classes where the generating representation is not identifiable.

Run ablations removing hierarchy, arithmetic relations, schema rules, and adaptive
segmentation. If an ablation performs equally well, do not attribute the advantage
to the removed component. A positive result only on pure periodic strings supports
a period detector, not the broader hierarchy hypothesis.

For null-based discovery tests, match length and marginal counts; add controls
preserving the lower-order dependence relevant to the question. Rerun **all**
selection on each null. For B Monte Carlo draws use `(r+1)/(B+1)` with a declared
tail, never report zero probability from zero observed exceedances. Account for
multiple tested families or declare a single primary aggregate in advance.

Prediction needs a separate experiment: fit on a prefix, freeze or predeclare an
online update rule, and score the unseen suffix against predictive baselines.
Full-string compression is not out-of-sample prediction. Likewise, a sequence that
resists the chosen language need not be random.

## 7. Ordered deliverables and decision gates

1. **Repair the scientific contract.** Apply the above narrative corrections to
   `build_15.py` and regenerate the notebook together; incorporate the scratch
   examples with unambiguous names and coverage columns. Preserve historical
   measurements as labelled records. Tighten the shared wrapper's binary-input,
   remainder-policy, and sliding-step validation before using it for discovery.
2. **Build the encoder and independent decoder.** Specify every bit field and
   round-trip literals, boundaries, schemata, repetitions, and corrections. Stop
   claims of compression if a field cannot be decoded without hidden information.
3. **Build bounded inference and a small exact oracle.** Exhaust tiny instances
   within a bounded candidate grammar to measure the search gap. Verify each
   recovered description against the input; retain literal fallback and timeouts.
4. **Run the frozen benchmark and ablations.** Publish per-instance outputs,
   failures, seeds, dependency versions, input hashes, and complete code lengths.
5. **Make the claim proportional to the result.** Net gains across held-out
   families support the specified generalisation. Gains disappearing after coding
   model/order/corrections reject the proposed advantage. Gains only in-sample
   do not support prediction; causal recovery requires additional evidence.

The next executable stage should be the code specification and round-trip decoder,
followed by automatic inference. Further BDM examples alone will not close the
generalisation gap.

## 8. Verification and scope of this review

Reviewed notebook 15, its builder, bitacora 32, the shared description-length
owner, the exact deconvolution implementation, the project protocol, the earlier
legitimacy audit, and the authoritative terminology. Read the original BDM paper
and primary MDL/grammar references. Graph MCP tools were unavailable in this
session; direct source inspection was the fallback.

All **11 notebook code cells executed successfully** in a fresh Python process
with the Agg backend. This checked execution and numerical output, not visual
rendering or a saved Jupyter-kernel rerun. The existing targeted suite passed:

```sh
python -m pytest tests/analysis/test_description_lengths_values.py -q
# 91 passed
python index-deconvolution/experiments/audit_shifted_zero_generalization.py
```

The audit writes `results/shifted_zero_generalization_audit.json`, recording block
scans, coverage, multiplicities, source-byte counts, address checks, and input
SHA-256 hashes. It imports the shared BDM owner and introduces no new estimator.
These checks reproduce the review's numerical corrections; they do not validate
the proposed generalised method. No historical notebook or core implementation
was changed by this review.
