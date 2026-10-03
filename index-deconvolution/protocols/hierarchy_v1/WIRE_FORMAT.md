# HID-v1 wire and baseline format — normative annex

Version 1, 2026-10-01. This is a proposed executable format, not an existing codec.
The developer implements it literally and supplies golden fixtures. Changes to
this annex require a documented protocol amendment before confirmation.

## W1. Shared conventions and envelope

An archive is:

```text
ASCII "ISD1" (4 bytes)
codec_id       (1 byte)
output_n_bits  (U)
payload_n_bytes (U)
payload        (exactly payload_n_bytes bytes)
```

`U` is canonical unsigned LEB128: seven value bits per byte, least-significant
group first, high bit means continuation. Zero is `00`. Reject redundant leading
zero groups, unterminated values, and values >2^63-1. Negative integers and bool
parameters are invalid at the encoder API. References and counts use U; no integer
has a free implicit cost. Do not use float log2 to determine field widths.

`P(s)` packs a bit string MSB-first into ceil(len(s)/8) bytes. The final byte's
unused **low** bits must be zero. Length is supplied by the surrounding field.
For n=0, P is empty. These padding bits are transmitted and counted.

`R(m,k)` is a different field: the lexicographic rank of a length-m binary string
with k ones, where 0<1. Let M=binomial(m,k), w=(M-1).bit_length(). Transmit the rank
as an unsigned **big-endian**, right-aligned integer in ceil(w/8) bytes. For M=1
transmit no bytes. Require 0<=rank<M and 0<=k<=m. The unused high bits are zero.
Use an integer combinatorial rank/unrank algorithm; JSON, decimal text, or an
untransmitted model must not be used to decode this field.

Reject wrong magic, unknown codec, wrong payload length, trailing bytes, nonzero
padding, invalid ranks, overflow, and malformed U. The entire archive is consumed
or decoding fails. The envelope transmits n, so ragged strings need no sidecar.

The measured scientific quantity is `8 * len(complete_archive)`. Detailed reports
may separately expose payload/header/padding costs, but cannot subtract them from
the primary comparison. No archive is compared using unrounded analytic bit costs.

## W2. Codec identifiers

| ID | Codec | Payload |
|---:|---|---|
| 0 | Literal | P(x), with n in envelope |
| 1 | HID DAG | W3 |
| 2 | Run length | W4 |
| 3 | Foreground gaps | W4 |
| 4 | Periodic prefix | W4 |
| 5 | Bernoulli enumerative | W5 |
| 6 | First-order context enumerative | W5 |
| 7 | zlib | W6 |
| 8 | lzma | W6 |
| 9 | Deterministic pair grammar | W7 |

Every baseline archive is decoded independently. All methods use this same
envelope, including literal. For n=0, all encoders return the literal empty
archive; nonliteral empty archives are invalid. For n>0, a requested standalone
baseline returns its own mode even if larger than raw. `baseline_best` takes the
minimum over all baseline modes including raw, ties by codec ID then archive bytes.
The ID already pays for this per-input selection; no test-set tuning is involved.

## W3. HID DAG

Payload: `q:U`, followed by exactly q rule records. Require q>=1, every reference
strictly less than the current zero-based rule ID, every node nonempty, and root
ID=q-1. The root must expand to n bits. All rules must be reachable from the root.
Encode in deterministic depth-first postorder using ordered child traversal.
Rule sharing is explicit through references. Structural deduplication is a search
choice; duplicate records are legal (needed to represent the flat ablation fairly).

Every record starts with a one-byte opcode:

| Opcode | Rule | Fields after opcode |
|---:|---|---|
| 0 | LITERAL | `length:U`, P(bits) |
| 1 | CONCAT | `arity:U`, ordered `child_id:U` repeated arity times |
| 2 | REPEAT | `child_id:U`, `copies:U` |
| 3 | AP_UNION | `length:U`, `foreground:byte`, `q_ap:U`, then q_ap triples `(start:U, step:U, count:U)` |
| 4 | SCHEMA_UNION | `length:U`, `foreground:byte`, `q_schema:U`, then q_schema pairs `(fixed_mask:U, fixed_value:U)` |
| 5 | PATCH | `child_id:U`, `q_flip:U`, delta positions as in W4 |
| 6 | XFORM | `child_id:U`, `flags:byte`, `right_rotation:U` |

Semantics and validation:

- **LITERAL:** positive length, exact packed payload, zero padding.
- **CONCAT:** arity>=2, output is children in transmitted order. Repeated references
  are allowed and their order costs bytes. Output length is the sum of child lengths.
- **REPEAT:** copies>=2; concatenate that many copies of the decoded child.
- **AP_UNION:** foreground is 0 or 1. Initialise every position to `1-foreground`.
  For each triple set positions `start+j*step`, 0<=j<count, to foreground. Require
  step>=1, count>=1, start>=0, and last position<length; calculate without overflow.
  Entries are strictly sorted lexicographically and duplicates are forbidden;
  overlapping progressions are legal and have union semantics. q_ap=0 represents
  the constant background. APs are arithmetic rules, not renamed sumandos.
- **SCHEMA_UNION:** let d=(length-1).bit_length(). Require mask<2^d and
  `fixed_value & ~fixed_mask == 0`. Set position i to foreground iff at least one
  transmitted pair satisfies `(i & fixed_mask) == fixed_value`, for 0<=i<length.
  Otherwise emit `1-foreground`. The finite domain is explicit: do not pad output
  to 2^d. Reject a schema matching no valid address. Pairs are strictly sorted
  `(mask,value)`; duplicates forbidden, overlaps allowed. q_schema=0 is constant
  background. A mask bit 0 is a don't-care, whose fillings are the sumandos.
  For length=1, d=0, mask=value=0 is a valid full-domain schema.
- **PATCH:** decode child, then XOR exactly the q_flip transmitted positions.
  Require q_flip>=1, strictly increasing positions, all within the child's length.
  Binary flips require no transmitted replacement value. An absent patch has no
  record; q_flip=0 is rejected. Patches preserve length and are not insert/delete
  operators. Transmit every exception, including positions discovered with truth
  information during testing; inference may not access that truth information.
- **XFORM:** flags bit 0 complements, bit 1 reverses, other bits must be zero.
  Apply complement, then reversal, then right circular rotation by r. Require
  0<=r<child_length; reject flags=0,r=0 as an identity record. A transform changes
  contents/order but preserves length. No coordinate mapping or permutation is
  implicit. Arbitrary permutations have no special free operator in version 1.

No node's output may exceed n, since only reachable nodes occur. Check expanded
lengths before allocating or multiplying strings. Apply explicit resource limits:
default n<=16,777,216; q<=1,000,000; total expanded intermediate bits<=64*max(1,n).
An otherwise valid archive exceeding a resource limit raises a distinct resource
exception, not a partial decoded result. Use iterative decoding; graph depth must
not trigger Python recursion failures. Benchmark archives are also constrained by
the smaller inference caps. Document payload-input size limits independently.

Represent schema rules in human reports with mask/value, free coordinate list,
decimal anchor, and generated offset family or its compact formula. Confirm that
`value + sum(e_j*2**j for j free)` gives the same addresses after domain clipping.
This is a lossless set representation, with no noise reinterpretation.

## W4. Structural baselines and position deltas

Position deltas for sorted p0,...,p(q-1): send p0 as U, then
`p_j - p_(j-1) - 1` as U for j>=1. Decode by cumulative addition plus one after the
first entry. Require all positions<n. Empty lists transmit no deltas.

**RLE (2):** `first_bit:byte`, `q_runs:U`, q_runs positive lengths U. Bits alternate
from first_bit, q_runs>=1, and lengths sum exactly to n. No zero-length runs.

**Gaps (3):** `foreground:byte`, `q_positions:U`, then deltas. Initialise opposite
background; set those positions. Try both foreground choices and transmit the
shorter complete envelope (lexicographic bytes break ties). q_positions may be zero.

**Period (4):** `period_length:U`, P(first_period). Require 1<=period_length<=n.
Decode by periodic repetition truncated to exactly n. The baseline finds the
shortest exact finite-prefix period from x itself. Charge the full first period,
even if it is statistically or schematically simple. This is the strong direct
period detector that the shifted-zero examples require.

## W5. Statistical comparison codecs

These are explicit lossless baselines; they are not inserted into D_schema or
reported as an algorithmic-complexity estimate. No floating entropy is a code.

**Bernoulli (5):** transmit `ones:U` then R(n,ones). The rank is over all binary
strings of that length and weight. Counts, rank storage, and envelope are charged.

**First-order context (6):** for nonempty x, form two outgoing transition queues:
Q_c is the sequence of next bits x[t+1] for t=0..n-2 whose previous bit x[t]=c,
preserving occurrence order. Transmit:

```text
first_bit:byte
m0:U        # length of Q_0; m1 = n-1-m0
k0:U        # ones in Q_0
k1:U        # ones in Q_1
R(m0,k0)
R(m1,k1)
```

The decoder un-ranks the two queues, starts with first_bit, and consumes the next
symbol from the queue indexed by the current last bit until n bits are emitted.
Require no queue underflow and both queues fully consumed. Validate all counts and
ranks. Invalid queue combinations fail; they are not filled with guessed symbols.
For n=1 the counts are zero and both rank fields are empty. This is a specified
first-order context code, not a claim to a particular optimal Markov type code.

## W6. Standard-library compressors

Compress P(x), not ASCII '0'/'1'. The shared envelope transmits the exact bit length.

- ID 7: zlib format, level 9, standard zlib header/trailer; no external dictionary.
- ID 8: lzma FORMAT_XZ, preset 6, CHECK_CRC64; no external dictionary.

The decoder uses bounded/incremental decompression, verifies the decompressed
length is exactly ceil(n/8), checks padding, complete end-of-stream, and rejects
unused trailing compressed data. Record Python, zlib compile/runtime versions, and
lzma environment; reproducibility guarantees are within the pinned environment.
Do not omit a library's internal headers or checksums from its measured size.

## W7. Deterministic pair grammar baseline

Define this precise bounded RePair-style variant; do not substitute a different
implementation after viewing test results.

Start symbols 0 and 1 are binary terminals. Repeatedly count adjacent pairs in the
current start stream (overlapping occurrences count toward frequency). Examine
pairs by decreasing frequency, ties by `(left_id,right_id)`. Select the first pair
that has at least two non-overlapping occurrences under a left-to-right greedy
replacement. Introduce the next rule ID, beginning at 2, with those two symbols as
its ordered right-hand side, and replace all such non-overlapping occurrences.
Stop when no pair qualifies or 4096 rules have been introduced. Back references
only; no post-hoc hand simplification or family-specific rule insertion.

Payload: `q_rules:U`, q_rules pairs `(left_id:U,right_id:U)` for IDs 2..q+1,
`m_start:U`, then m_start start-symbol IDs U. Each production references only
terminals or earlier productions. Decode the ordered start stream, require exactly
n output bits, and enforce expansion limits. A q=0 grammar is valid for n>0.
Discard unreachable rules and renumber deterministically if the implementation's
rewrites produce any; ensure encoding and decoding agree on IDs.

Use the same parser to propose an HID graph, but the baseline and HID each pay for
their own serialization. An inference improvement must beat the baseline's actual
archive, not the cost of its translation into HID.

## W8. Golden fixtures and accounting

These fixtures are hand derived. Whitespace in hex is for display only:

| Case | Complete hex | Bytes |
|---|---|---:|
| Literal empty | `49 53 44 31 00 00 00` | 7 |
| Literal `1` | `49 53 44 31 00 01 01 80` | 8 |
| Literal `0110` | `49 53 44 31 00 04 01 60` | 8 |
| Bernoulli `0110` (weight 2, rank 2) | `49 53 44 31 05 04 02 02 02` | 9 |
| Context `0101` (Q0=`11`, Q1=`0`) | `49 53 44 31 06 04 04 00 02 02 00` | 11 |
| HID literal `1`, then repeat 8 | `49 53 44 31 01 08 07 02 00 01 80 02 00 08` | 14 |

The last archive loses to the raw archive for eight ones (8 bytes). This is expected
and must not be hidden by subtracting grammar overhead. Inference must choose raw
for this comparison unless another legal archive is strictly shorter.

Supply additional independently reasoned fixtures for AP unions (including overlap),
schema overlap/ragged clipping, ordered concat, patch deltas, transform order, and
multi-byte U values. Test exact bytes as well as round trips. A field ledger must
sum to the transmitted archive size; decoder agreement alone cannot detect a
serializer/measurement pair that both omit the same information.
