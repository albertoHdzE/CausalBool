# Bitacora 32 — The Shifted Zero: a Probe of BDM, and the Pyramid Idea It Motivates

Date: 2026-10-01
Status: notebook complete and executed (0 errors); §7 below (P1–P3) is a scratch
measurement reproduced by the script in the appendix and not yet in the notebook.

## §0 The discussion that produced this work (2026-10-01)

This section records the exchange in full: first the author's ideas as stated, then the
assistant's comments and measurements, then what was agreed and what happens next. It is
placed first because everything below it follows from it.

### §0.1 The author's ideas, as stated

**Pages 17–18 — the shifted zero.** Take one zero shifted through a line of eight ones.
Written one by one, programs for the cases grow longer as the zero moves inward. In terms of
AIT this means the third string is more complex than the second, at least in characters. The
author's words on the plot: *"notice that there is an increment, but also a flat section of
length/complexity, in terms of AIT. Then, even, it captured certain granularity, still
suffering (less) of the same Shannon problem. At some point there are no regularities to show
as differences."*

Then the indexed program, `shift_zero_concat`, which given indexes returns any of the
patterns in any given order. On it: *"which almost twice the greatest length in the previous
approach, this version generates any of the patterns in any given order. Then the finer point
regarding AIT is its naive counting of patterns."*

The experiments requested: each of the 8 cases measured separately; the arithmetic sum of
those values against the whole concatenated string; scaling the number of zeros from
`11111111` to `00000000`, where a symmetric behaviour is expected; the same set of
experiments with the elements in random order instead of ordered; and finally a rotation,
taking the last element of the whole string and putting it at the beginning — *"Still being
the same?"*

**Page 19 — BDM walking the string, and patterns of patterns.** *"Now suppose that as BDM,
analyzing AX is walking throw AX analyzing a's one after the other and say this is the
complexity value. While the program that noticed that this is a progressive shift of zero,
might be 'almost constant' and being more intelligent."* Then the mixed version
AXM = {a8, a1, a6, a7, a2, a4, a3, a5}, and two questions: *"Can BDM do better, not get
confused, if we don't tell it to process substrings of 8 bits-length?"* and *"Is different if
we play with lengths for guiding processing, making variations for example from length = 4 to
length = 8 for BDM?"*

Then the patterns of patterns: P1 = {A, A}, P2 = {A, AX, AXM}, P3 = {AXM, AXM, AXM}, with
*"Is this different for BDM?"* and the observation that for the IBD (Index-Based Description)
approach, P1, P2, P3 are *"just about a next level of abstraction with no code changes and
minimal changes in length"*.

**Pages 19–20 — the idea behind the idea.** *"While we might spend more time analyzing BDM's
behaviour, the real goal of this idea is to create an 'Holistic analysis method' for binary
string. I like thinking in organization levels. To consider a string as a sequential
progression of bits, loose the superior levels of organization."*

The pyramid: *"the main goal for this idea is generating a analysis system that help us to
make this multilevel-pyramidal level of abstraction, and automatize to create our graph of
graphs based on the couples of (decimals, sumandos) at different levels of organization."*
Symbolic computation to characterise which expressions contain which information. The
presence vector A = [1,1,1,0,0,0,0,0] for the existence of a1, a2, a3. The remark that AXM
cannot be expressed as AX because *"order here is vital"*. The proposed mechanism:
*"my idea (naive) is to use a kind of Huffman codification based on Hamming distances to
create the networks. Then use the tree decisions to define the order of the concatenation of
elements based on our (decimal, sumandos) representation."* Growing the analysis length,
starting at 2, *"define the limit of the word (elements) at the point where marks '*' start to
appear, then creating levels of abstraction. Then rotating the target string to gener
The author's handwritten notes (pages 17–20) propose an argument about Zenil's BDM/CTM.
Take one zero shifted through a line of eight ones. Written one by one, the programs for the
cases grow slightly as the zero moves inward. CTM shows the same small variation, and this
is credited as BDM's finer granularity over Shannon. An observer who sees *the shift*,
however, writes one indexed program for every case, and its length is almost constant. The
request was a notebook that probes this with experiments: each case separately; the sum of
the parts against the whole; more zeros, from `11111111` to `00000000`; random order of the
cases; and a one-bit rotation. Pages 19–20 then extend the idea to a multi-level
("pyramidal") description, and the author asked for an opinion on it.
## The machinery

There is no new complexity measure. The repository owner of every description length,
`src/description_lengths.py`, already owned `bdm_2d` and the pybdm pin (0.1.0). It now also
owns `ctm_1d` (lookup in pybdm's CTM-B2-D12 table, lengths 1..12) and `bdm_1d` (choice of
block, an optional sliding step, and a remainder policy). pybdm silently drops trailing bits
that do not fill a block. `bdm_1d` refuses this unless the caller passes
`remainder="drop"`, following the rule already applied to `bdm_2d`: edge semantics are
chosen explicitly, never silently. Four tests pin the new functions:

- CTM is invariant under reversal and complement;
- aligned BDM equals the sum of CTM plus log2 of each block's multiplicity, with the
  expected value derived in the test rather than copied from the output;
- `bdm_1d` refuses a remainder unless asked;
- `ctm_1d` refuses lengths beyond the table.

`tests/analysis/test_description_lengths_values.py` passes 91 of 91. The owner row in
`GOVERNANCE/CORE.md` names the two new functions.

The Kolmogorov side is never a number for K. It is always an explicit Python expression,
which `program_length` executes and checks against the target before counting its
characters. Each one is an upper bound in a fixed language. Characters and CTM bits are not
commensurable, so only slopes and invariances are compared, never levels. Shannon appears
only as a labelled foil.

## Finding 1 — the designed string is a period-9 repetition

The concatenation of the eight cases a_i = 1^i 0 1^(7-i) puts its zeros at 0, 9, 18, …, 63.
Hence A = (0 1^8)^7 0 (64 bits), and with the all-ones anchor in front,
A9 = (1^8 0)^8 (72 bits). Rendered at width 8 the zeros form the designed diagonal. At
width 9 they form a single column. The shortest program found is `('0'+'1'*8)*7+'0'`
(17 characters). For comparison:

| program for A | characters |
|---|---|
| the string written out literally | 66 |
| the indexed shift program | 46 |
| the eight one-off programs, joined | 333 |
| the period-9 program | 17 |

"Shift a zero by one per 8-bit block" and "repeat a 9-bit word" are two descriptions of one
object, and the second is shorter. The analysis length that the IDEA note seeks is 9 for
this string, not 8.

## Finding 2 — per case, CTM resolves what Shannon cannot, but only within the constant

Across the eight shifted cases CTM runs from 19.625 to 20.431 bits, a spread of 0.805
bits. The all-ones string costs 18.527 bits. The profile has the shape of the author's
hand-drawn program-length plot: cheap at the ends, a plateau inside. The Shannon foil is
flat at 0.544 bits per symbol for all eight cases.

Two things limit what this shows. The mirror symmetry CTM(a_i) = CTM(a_(7-i)) is a property
of the D(5) table, which is closed under reversal and complement, so it is not a finding.
And a spread of 0.8 bits between 8-bit strings is inside the invariance constant. The
argument does not bite at this level.

## Finding 3 — BDM's verdict on one string depends on the block length

At block 8, BDM_8(A) equals the sum of the eight CTMs, 159.785 bits. They are identical by
definition, because every block is distinct. The informative experiment varies the block
length. The control is a random 72-bit string with seed 72, scored at the same block
length.

| block | BDM(A9) | BDM(random) | ratio |
|---|---|---|---|
| 8 | 178.31 | 194.96 | **0.91** |
| 9 | 24.62 | 195.26 | **0.13** |
| 12 (pybdm default) | 90.03 | 191.18 | 0.47 |
| 6 | 48.10 | 177.73 | 0.27 |

At block 8 a string made by a 17-character program scores 91% of a coin-flip string. At
block 9 one block is repeated eight times, and the ratio falls to 0.13. Block 12 lies in
between because lcm(9, 12) = 36, so every block occurs twice. BDM rewards exactly one
regularity, identical repetition of a block, and it sees that repetition only where the
partition creates it.

## Finding 4 — scaling the number of zeros: BDM is linear in the cases; the generator is constant

Two families were tested: a run of k zeros sliding (9−k cases) and every placement of k
zeros (C(8,k) cases).

- **BDM_8 grows linearly with the number of cases.** The least-squares slope over 18
  points is 21.78 bits per added case. Per-case CTM ranges from 18.53 to 22.09 bits, so the
  slope is one CTM per case.
- **The generator stays constant.** One program, with k as its only parameter, is 52
  characters for the sliding family and 98 for the placement family, whatever k is. The
  literal grows from 10 to 562 characters.
- **The placement family is exactly symmetric in k ↔ 8−k.** This follows from complement
  invariance.
- **The sliding family is not symmetric.** It has 9−k cases, and its complement partner is
  a run of *ones* sliding through zeros, which is a different family.
- **The literal is shorter than the generator for families of five cases or fewer.** The
  expected crossover is real.
- **BDM exceeds the raw length.** It is 1529.9 bits on a 560-bit string at k = 4, but every
  8-bit block carries a machine-dependent offset of about 18.5 bits. Compare slopes, not
  levels.

## Finding 5 — with aligned blocks, order is invisible

The nine cases of A9 were shuffled 2000 times (seed 15).

| block | ordered | shuffles | where the ordered string falls |
|---|---|---|---|
| 8 | 178.31 | every one 178.31 | shuffled and ordered identical |
| 9 | 24.62 | 47.14 to 179.55, median 137.33 | below every shuffle |
| 12 | 90.03 | median 171.54 | 3 of 2000 shuffles at or below it |

At block 8 BDM sees only the multiset of blocks, exactly like the block-entropy foil
(3.170 bits for every arrangement). A permutation of the nine cases can add up to
log2 9! = 18.47 bits to K.

## Finding 6 — rotation

- **A9:** every one of its 72 rotations leaves BDM_8 at 178.31. A rotated period-9 string
  is again period-9 and has the same multiset of 8-blocks, so this is not robustness.
- **A:** rotation by one moves its final zero to the front, creating `00111111` and
  `11111111`. BDM_8 moves by 0.28 bits, and by 0.92 bits across all 64 rotations. Under
  block 12 the same rotations span 59.65 bits.
- **Shuffled A9 (control):** it spans 53.69 bits at block 8.

For K, every rotation costs at most a rotation index of 6 or 7 bits.

## Finding 7 — patterns of patterns: P1, P2, P3 (scratch; appendix)

These are the author's page-19 constructions. Cases follow `shift_zero_concat`: a1 is all
ones, and a(j+1) has its zero at position j. The strings are:

- A = a1 a2 a3;
- AX = a1 … a8;
- AXM = (8,1,6,7,2,4,3,5);
- P1 = A A;
- P2 = A AX AXM;
- P3 = AXM AXM AXM.

The index-based description (IBD) is one fixed generator of 72 characters plus an index
list.

| string | bits | BDM_8 | BDM_9 | BDM_12 | IBD index list (chars) |
|---|---|---|---|---|---|
| A   | 24  | 58.1  | 22.6  | 56.3  | 7 |
| AX  | 64  | 158.7 | 24.4  | 89.0  | 8 |
| AXM | 64  | 158.7 | 135.0 | 117.4 | 17 |
| P1  | 48  | 61.1  | 67.1  | 58.3  | 9 |
| P2  | 152 | 168.4 | 161.1 | 207.6 | 33 |
| P3  | 192 | 171.4 | 256.5 | 433.2 | 19 |

- **BDM_8 cannot tell AX from AXM.** Both score 158.7; IBD charges AXM's permutation
  (8 → 17 characters).
- **BDM does see the repetition in P3 at block 8**, but it pays log2 3 once per distinct
  block (8 × 1.585 = 12.7 bits). The index description pays for "×3" once. BDM's credit for
  repetition is per block, not per higher-level unit, and that is the level argument in one
  number.
- **Under the default block 12, P3 costs 3.7 times AXM**, since lcm(64, 12) = 192 and no
  block repeats.
- **The Hamming graph over a1..a8 is complete and uniform.** Every pair of shifted cases is
  at distance 2, and each is at distance 1 from all ones. Hamming distance is blind to the
  order of the shift.

## What is supported, and what is not

Supported:

- BDM counts patterns and does not relate them.
- Its credit for structure is limited to identical repetition at a fixed partition.
- Whether a structure is seen depends on the partition matching the generator.

Not supported:

- "BDM is no better than Shannon": per case it is better, and with a matching partition it
  finds the repetition.
- "BDM is wrong about K": every K-side number is an upper bound.

This regime is the one Zenil et al. (2018, *Entropy* 20:605) describe, BDM drifting towards
block entropy when CTM is uninformative across blocks. Present the result as a constructive
instance of it, not as a refutation. The citation was given from memory and must be checked
before it enters a manuscript.

## Next

The block length that rescues BDM is the period of the generator, and index-set
deconvolution recovers the period. The next experiment is to let the data choose: compare
the minimum of BDM over block length and phase with the length of the recovered (L, Ω)
description, on families whose period is not designed in. The author's pyramid proposal
(pages 19–20) is the general form of this. The design criterion and the specific risks
recorded in the session opinion are:

- each level must be selected by total two-part description length;
- the order data must be paid for;
- Hamming/Huffman is the wrong relation and the wrong code.

## Appendix — reproduce Finding 7

```python
import sys; sys.path.insert(0, "src")
from description_lengths import bdm_1d
def a(j):
    i = j - 1; full = 255
    return f"{(full if i == 0 else full ^ (1 << (8 - i))):08b}"
cat = lambda idx: "".join(a(j) for j in idx)
A, AX, AXM = cat([1, 2, 3]), cat(range(1, 9)), cat([8, 1, 6, 7, 2, 4, 3, 5])
for k, s in {"A": A, "AX": AX, "AXM": AXM, "P1": A + A,
             "P2": A + AX + AXM, "P3": AXM * 3}.items():
    print(k, len(s), [round(bdm_1d(s, block=b, remainder="drop"), 1) for b in (8, 9, 12)])
```

---

## Errata — 2026-10-02 (HID-v1 stage H0, after the review in bitacora 33 §3)

The measured tables above are **historical records and are not rewritten**. The
statements below supersede the corresponding prose; each correction is executed in the
regenerated notebook 15 (`notebooks/build_15.py`, revision 2026-10-02), whose cell
assertions check the numbers quoted here.

1. **Incomplete quotation (§0.1).** The paragraph quoting pages 19–20 breaks off at
   *"Then rotating the target string to gener"* and is followed, without a separator, by
   the start of a different paragraph. The rest of the author's sentence was not captured
   in this record. **The quotation is incomplete**; it has not been reconstructed and must
   not be completed from conjecture. Restore it only from the author's handwritten source.
2. **Names.** "A" denotes two objects in this bitacora: the 64-bit concatenation of
   Findings 1–6 and the 24-bit "A = a1 a2 a3" of Finding 7. Notebook 15 now uses **A64**,
   **A72** (= `11111111` + A64), **A24**, **AX64** (scratch cases 1..8, i.e. the first 64
   bits of A72, not A64) and **AXM64**.
3. **Characters are not bits (Finding 1).** The 17-character period-9 expression occupies
   136 UTF-8 payload bits before any framing; it is shorter than the textual Python
   literal, not shorter than the 64-bit string. It outputs A64, not A72; A72 is generated by
   the 14-character `('1'*8+'0')*8`. Finding 3's sentence about "a string made by a
   17-character program" scoring 91 % of a coin-flip string refers to A72 and should name
   that 14-character expression.
4. **The CTM spread is not an error interval (Finding 2).** "Inside the invariance
   constant" is withdrawn: the invariance theorem supplies no numerical tolerance, so the
   0.805-bit spread is a distinction made by one reference table, not a measured difference
   in true K and not a band.
5. **Raw minimum BDM does not select the period (Finding 3).** Over b = 2..12 the minimum
   of BDM_b(A72) is at **b = 3** (17.842 bits); over 1..12 it is at b = 1 (14.029). All three
   partitions cover every bit. "Repetition is the one regularity BDM rewards" is too broad:
   CTM scores structure inside blocks; the defensible criticism is that aligned BDM
   aggregates a multiset, so relationships and order *between* blocks are not represented.
6. **The slope is not a law (Finding 4).** The 21.78 bits per case summarise 18 constructed
   points with distinct 8-bit blocks. For fixed b and m complete blocks,
   BDM_b ≤ C_b + 2^b log2 m, so fixed-b BDM grows at most logarithmically in length.
   "BDM_8 grows linearly with the number of cases" holds only within the constructed range.
7. **Coverage (Finding 7).** The drop policy scored different fractions of different
   objects: A24 at block 9 scores 18 of 24 bits; AX64 and AXM64 at block 12 score 60 of 64;
   P2 at block 12 scores 144 of 152; P3 at block 12 scores all 192. Full-coverage
   (recursive and sliding step-1) scores are now printed beside the historical values.
8. **P3 repeats a block (Finding 7).** At block 12, P3 has **16 blocks, 15 distinct**; one
   block (`111111011111`) occurs twice. The implied "no block repeats" was false.
9. **Rotation.** A specified rotation changes K by at most a constant; an arbitrary one also
   needs its index, at most ceil(log2 n) + O(1) bits.
10. **Huffman (Next).** "Hamming/Huffman is the wrong relation and the wrong code" is
    narrowed: Huffman coding is a legitimate downstream code for a specified symbol stream;
    it does not discover the transformations or determine the original order.
11. **Citation.** Zenil et al., *Entropy* 20(8):605 (2018), DOI 10.3390/e20080605, has been
    checked (bitacora 33 §2); it discusses block-permutation invariance and boundary
    conventions, so this probe illustrates that discussion rather than discovering it.

Executed evidence: `notebooks/15_shifted_zero_bdm_probe.ipynb` (13 code cells, 0 error
outputs), and `results/hierarchy_v1/confirm-v1/diagnostics_historical_audit33.json`
(the bitacora-33 audit rerun to a new path; the original
`results/shifted_zero_generalization_audit.json` is preserved).
