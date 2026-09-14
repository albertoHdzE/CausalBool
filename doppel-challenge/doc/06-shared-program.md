# Shared whole-repertoire program, version 1

## Object and execution contract

The object is the complete ordered synchronous one-step binary output matrix,
not a set of distinct outputs or a long-run distribution. N and the input
enumeration (decimal row addresses, node 0 least significant) are fixed decoder
conventions. No input table is transmitted. Every output reference evaluates at
the same row address, preserving the correlations between output columns.

The public compiler accepts the existing Network object through the package
adapter. It supports AND, OR, XOR, NAND, NOR, XNOR, NOT, IMPLIES, NIMPLIES,
MAJORITY, KOFN, and CANALISING. Parameters match the Python reference:
canalisingIndex is zero-based within the ascending connected-input subvector;
the Wolfram validation boundary alone translates it to one-based. NOT uses the
first connected input; implication uses the first two, as ApplyGate does.
Undefined empty-input arities, unsupported gate labels or parameters, invalid
connectivity, and nonzero noiseFlipProb fail explicitly. Valid empty-input
constant results for the other gates are supported.

The compiler builds a reduced ordered binary decision graph. Coordinates are
ordered by node index. Terminals 0 and 1 denote false and true; each other
reference denotes (coordinate, zero-child, one-child). All outputs share one
unique node table. The default division size is two consecutive outputs;
changing division size cannot change the canonical program. Divisions are
compilation batches, not enumerated output-pattern tables.

AND/OR and thresholds use remaining-count states, parity uses odd/even states,
and the remaining gates use Boolean identities. There is no call to a truth
table, minterm minimizer, repertoire generator, or position-unfolding decoder.
Compilation has a default one-million-node allocation budget and 300-second
deadline; isolated benchmark workers additionally enforce the wall-clock limit.
Traversal, Boolean composition, and serialization use iterative algorithms.

## Decimal/Sumandos semantics and correctness

An accepting path fixes some coordinates and leaves the others free. Encode
its fixed one-bits as anchor A and its free coordinates as bitmask M, requiring
A & M = 0. Its Sumandos are exactly the submasks of M. Its positions are
A + s for every generated offset s. This frees connected coordinates whenever
the path does not test them, following GOVERNANCE/GLOSSARY.md section 1d.

For example, the three-coordinate schema 1** has anchor 1, free mask 6,
Sumandos [0,2,4,6], and positions [1,3,5,7]. The integer 6 is a generator mask,
not the explicit offset list [6]. The two representations have distinct types.

Proof obligations are compositional:

1. The direct gate recurrence equals the declared gate on every assignment.
2. A decision selects exactly the continuation for the tested coordinate.
3. Removing identical branches and merging identical nodes preserves evaluation.
4. A path's fixed/free coordinates generate exactly its accepting positions.
5. Paths to true within one output are disjoint; their union is that output's
   one-set. Different outputs may legitimately share positions.
6. Ordered output references reconstruct all N bits at each implicit address.

compile_schema_program accepts N collections of (anchor, free_mask) pairs and
unions their predicates, even when input schemas overlap. It can describe any
finite Boolean output table, but does not promise compactness for arbitrary
custom functions. export_output_schemata returns disjoint accepting paths and
defaults to a limit of 10,000 schemas per output. It raises on overflow without
returning a complete-looking partial export. A failed export does not invalidate
the compact program. Explicit offset generation is a validation/display step.

For the twelve supported one-step gate families, direct compilation uses at
most polynomially many states in their arities (thresholds use O(d^2), parity
uses O(d) reachable states). This is not a promise of fast arbitrary Boolean
minimization or joint-distribution enumeration. Writing all output bits still
requires work proportional to N*2**N. In particular, parity can have exponentially
many accepting schema paths despite a small shared graph.

The graph representation follows reduced ordered decision diagrams, an
established exact method rather than a claim of a newly invented Boolean
algebra: R. Bryant, Symbolic Boolean Manipulation with Ordered Binary Decision
Diagrams (1992), https://www.cs.cmu.edu/~bryant/pubdir/acmcs92.pdf.

## Normative binary codec

Codec identifier: shared_repertoire_program_v1. The decoder receives bytes and
N. It does not receive the original topology, gate names, or gate parameters.

Reachable nodes are numbered from 2 in postorder: visit output references in
column order, visit zero before one, and emit a node after both children.
Terminals retain 0 and 1. Equal functions under the fixed variable order have
the same canonical graph, independent of schema input order or divisions.

For M decision nodes, write:

1. Elias-gamma(M+1), using the standard zero-prefix and binary-suffix code.
2. Each node's coordinate in ceil(log2(N)) bits and each child in
   ceil(log2(M+2)) bits, all three fixed-width fields LSB-first.
3. N ordered output references, each ceil(log2(M+2)) bits, LSB-first.

N=1 uses zero coordinate bits. M=0 uses gamma(1) and one-bit terminal
references. Pack the stream left-to-right into bytes (first stream bit is the
byte's most significant bit), adding fewer than eight zero padding bits.
The decoder derives the logical length from M and N. It rejects truncation,
extra bytes, nonzero padding, out-of-range references, forward references,
inconsistent coordinate order, redundant/duplicate/unreachable nodes, and
noncanonical numbering.

The primary measured length includes all of these logical fields. The raw
baseline is N*2**N binary bits. Report count-field, decision-record, and output-
reference contributions separately, along with padding and stored byte length.
There is no raw fallback or second compression algorithm. Tiny examples can
expand: the three-node AND/OR/XOR example uses 54 program bits versus 24 raw.

Program SHA-256 is computed over compact sorted-key JSON containing codec, n,
logical_bit_length, and payload_hex. It identifies the complete decoding
context, while N is not charged in the conditional program-length comparison.
The decoder source SHA-256 is separate provenance. Fixed interpreter overhead
and total length including that overhead are unmeasured (null). This is our
fixed-codec algorithmic complexity, not universal Kolmogorov complexity or a
claim of minimum description length. Previous flat-list lengths measure a
different object and must not be relabeled as this codec.

## Benchmark and notebook release

Run from the repository root:

    PYTHONPATH=doppel-challenge/src python -m doppel_challenge.program_benchmark

The default 35 cases are the 18 ring/hub N=8/10/12 base/add/remove cases,
12 mixed-gate cases (seed 20260910), the worked N=8 and Chapter 4 N=7 networks,
and identity/shared-parity/shared-majority N=100 probes. Every small case is
verified at every output bit, independently in Python and Mathematica.
N=100 probes check two boundary addresses and 100 pseudorandom addresses
(seed 20260910); their exact symbolic programs have sampled validation, not
an exhaustive large-N proof. No complete large table is generated for them.

The benchmark persists the actual program bytes, complete network, counts,
logical/stored lengths, digest, per-stage timing, peak worker RSS, and explicit
validation/materialization scope. RSS is the worker peak including reference
validation and BDM, not an isolated compiler-only measurement. Reference-owner
time is separate. Timeout, resource exhaustion, invalid input, compiler failure,
malformed payload, reference-owner failure, and reconstruction mismatch are
distinct; the reference record additionally separates normal exit, timeout,
process failure, and malformed JSON. Failed cases cannot be accepted.

BDM uses pybdm 0.1.0 on the original binary output matrix without reshaping.
Pad bottom/right with zeros to multiples of four, use 4x4 PartitionIgnore,
and record actual version, original/padded shapes, padding, and original-output
digest. Report BDM as a model-based estimate separately from actual code bits.
Missing dependency or failed BDM blocks release readiness, never becomes zero.
BDM is not computed for sampled N=100 probes.

Section 12 loads these saved results, proves the N=8 reconstruction, explains
schema generation and the complete binary program, and saves separate
raw/program and BDM figures. Legacy column/pattern encoders and artifacts stay
unchanged for audit; their internal materialization does not establish symbolic
scalability. Long-run distribution codecs and BDM-on-index-stream diagnostics
remain separate observables.

Acceptance requires the complete doppel-challenge suite, relevant root
regressions, the Wolfram gate parity test, benchmark validation with
release_ready=true, and an error-free executed notebook. The notebook checks
that its compiler source digest and worked-network program match the results.
