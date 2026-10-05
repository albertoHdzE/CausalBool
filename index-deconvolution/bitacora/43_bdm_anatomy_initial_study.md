# 43 · The anatomy of BDM: how, why and when it works, and where it meets index-set deconvolution

> **Superseded in part (2026-10-04).** The pre-registered protocol bdm_anatomy_v1 (notebook 19,
> bitacora 44) tested this note's claims. Withdrawn or corrected: the "fill ratio" law (§4),
> the emulation statement (§6), the "any object / noisy data" rows of §5, the reading of C3, and
> the scale of C5 (rule 30 is the top of the distribution; the mean over rules is 0.107). This
> file is kept unedited below as provenance.

**Date:** 2026-10-03. **Status:** initial study, exploratory. Nothing here is pre-registered;
it is the evidence base for writing the protocol. **Sources read:** notebook 15
(`notebooks/15_shifted_zero_bdm_probe.ipynb`), Hector Zenil's talk notes
(`doc/AIT-hector-video&ideas.pdf`, 24 pages), `imp-causalNet-paper/COMPARISON.md` and
`RESEARCH_NOTES.md`, `imp-causal-paper/imp-results.md` and `SESSION_HANDOFF.md`,
`imp-pathinfo-paper/FINDINGS.md`, `arena-planner/VERDICT.md` and `PROTOCOL.md`.
**New probes:** five scripts in `43_probes/`, each calling only the repository's owner
(`src/description_lengths.py`: `ctm_1d`, `bdm_1d`, `bdm_1d_trace`, `bdm_2d`). Run them from
the repository root with `venv/bin/python index-deconvolution/bitacora/43_probes/<name>.py`.
All values are from pybdm's D(5) tables (1-D words up to 12 bits, 2-D blocks of 4×4).

The aim, as the author set it, is understanding, not attack: how BDM works, why it works,
when it works, and how it relates to our method.

---

## 0. The short answer

1. **Your picture of the mechanics is right, with one correction to the example** (§1).
2. **BDM is a "bag of words".** It looks up each distinct block once, adds the logarithm of
   how many times it occurred, and throws away *where* the blocks were. A complete
   description of a string has three parts: the dictionary of words, how many times each
   occurs, and the order in which they occur. BDM keeps the first two and drops the third.
   Shannon block entropy is, almost exactly, the third. So BDM is not "Shannon one level up"
   on the same axis: it is the *other half* of the description (§2).
3. **That single fact produces every counterexample we found** (§3): two strings whose
   complexity differs by about 10,000 bits get the *same* BDM; a binary counter and a random
   shuffle of the same blocks get the same BDM; a period-9 string looks random to blocks of 8;
   and on fair coin flips BDM per bit falls from 2.7 to 0.13 as the string grows.
4. **The parameters decide what BDM can see** (§4). One number governs it: how many blocks
   the input contains compared with how many different words of that length exist. When
   words repeat only because of structure, BDM is sharp. When words repeat because the
   dictionary is full, BDM goes blind.
5. **Perturbation results depend on where the block grid falls** (§3, C5). On a rule-30
   diagram, moving the 4×4 grid by one to three columns (an exact symmetry of the system)
   reverses the sign of a single cell's perturbation effect for half of the cells tested.
6. **The two methods agree on the published examples for a precise reason** (§5): both detect
   departures from a short generator. They agree when the generator's regularity is local,
   noiseless and aligned with the blocks, and when conclusions are read at the level of signs
   and groups. They part ways on order, on mechanism identity, on noise and on ranking.
7. **Other algorithms can approximate BDM** (§6): simply counting distinct blocks reproduces
   BDM's ranking with Spearman 0.93 on 600 test strings. The arena-planner algorithms solve a
   different problem and cannot emulate BDM, but its *method*, a lower-bound headroom gate
   before any building, is exactly what this study needs.

---

## 1. Your four assumptions, checked one at a time

### 1a. "With words of 5 bits, BDM uses only the 5-bit part of the lookup table." **True.**

BDM with block length *b* only ever reads the 2^b table entries for strings of length *b*
(32 entries for *b* = 5), plus shorter entries if a leftover tail is scored. Everything else in
the table is unused for that run.

One nuance matters. The CTM value of each 5-bit word was obtained by running billions of
small Turing machines, so each number carries global information about *that word*. But no
number in the table carries information about how two words relate to each other. All
cross-block information must come from the aggregation rule, and (§2) that rule keeps very
little.

At very short words the table also collapses. CTM('00') = CTM('11') and CTM('01') = CTM('10')
(checked, `bdm_probe5.py`), because the Turing-machine space is symmetric under complement
and reversal. So at *b* = 2 BDM only knows whether each aligned pair is "same" or
"different". At *b* = 1 it only knows how many 0s and 1s there are, and notebook 15 showed it
then ranks all 256 eight-bit words *exactly* as Shannon entropy does (Spearman 1.000).

### 1b. "Overlap 3 with words of 5 reads bits 1–5, then 3–7." **True, and here is the precise rule.**

pybdm does not take an overlap; it takes a **step** (it calls it `shift`). Overlap = word
length − step. Word 5 with overlap 3 is step 2, so windows start at bits 1, 3, 5, … (counting
from 1). That is your description.

### 1c. The example `1111100000`. **Partly wrong; corrected here** (`bdm_probe1.py`).

You wrote that the second window is `111000`. That is six bits; it cannot be a 5-bit window.
The actual walks are:

| setting | windows read | bits covered | BDM |
|---|---|---|---|
| word 5, no overlap | `11111`, `00000` | 10 of 10 | 21.43 |
| word 5, overlap 3 (step 2) | `11111` (1–5), `11100` (3–7), `10000` (5–9) | **9 of 10** | 33.55 |
| word 5, overlap 4 (step 1) | `11111`, `11110`, `11100`, `11000`, `10000`, `00000` | 10 of 10 | 67.11 |

Note the middle row: with step 2, the tenth bit is **never read**. pybdm silently drops it;
our owner refuses to score it unless told to drop. A third window `00000` would need step 5,
which is no overlap at all.

### 1d. "BDM keeps a count of repetitions and adjusts at the end." **True, and it is the crux.**

The final value is

> BDM(x) = sum over each *distinct* word w of [ CTM(w) + log2(number of times w occurs) ].

The count is applied once per distinct word, not as a running correction, and checked:
four copies of `11111` give CTM(`11111`) + log2 4 to machine precision. A word seen four
times costs 2 more bits than a word seen once, regardless of where the copies are.

### 1e. "So it is really a separation into patterns." **Yes. Formally, a multiset.**

Your phrase is the right intuition. The formula above depends only on *which* words occur and
*how often*. It is the same for every rearrangement of the blocks. That is what a multiset (a
"bag") is.

---

## 2. The central reinterpretation: BDM is two thirds of a description

Think of sending a string to someone, cut into *m* blocks of length *b*. A complete message
needs three things:

| part | what it says | who pays for it |
|---|---|---|
| **D** dictionary | which distinct words occur | BDM, at CTM price per word |
| **N** counts | how many times each occurs | BDM, log2 of each count |
| **A** arrangement | in which order the *m* blocks appear | **nobody in BDM** |

The arrangement costs log2( m! / (n1! n2! …) ) bits for an arbitrary order. For long strings
that is, by Stirling's formula, almost exactly *m* times the Shannon entropy of the block
histogram. So:

> **BDM keeps what Shannon block entropy drops (what each word is, priced algorithmically),
> and drops what Shannon keeps (how the words are arranged).**

This is a more precise version of your intuition that BDM is "a next level of Shannon". It is
not further along the same road; it is the complementary half of the same message. Hector
says something close to this on page 10 of the notes: the slide reads "BDM is a weighted
version of Shannon entropy", and he says that in the worst case it converges to Shannon
entropy. The table above says exactly which part is weighted and which part is missing.

**Evidence** (`bdm_probe2.py`, E4). Fair coin flips, block 12. For a random string the honest
answer is about one bit per bit.

| length N | BDM | BDM / N | missing order term | (BDM + order) / N |
|---|---|---|---|---|
| 1,200 | 3,244 | 2.70 | 525 | 3.14 |
| 12,000 | 28,960 | 2.41 | 8,413 | 3.11 |
| 120,000 | 126,107 | 1.05 | 109,328 | 1.96 |
| 1,200,000 | 151,895 | **0.13** | 1,182,211 | 1.11 |

BDM starts *above* one bit per bit (each 12-bit word costs 25.6 to 37.5 bits of CTM, median
32.7, which is more than the 12 bits of the word itself) and ends far *below* it, because once
every word has been seen, each new block adds only a logarithm. Adding the missing order term
brings the total back towards one bit per bit as the string grows. With a fixed block, BDM
can never exceed (sum of all CTM values) + 2^b × log2(m): it grows logarithmically, on random
data too. Notebook 15 had already shown this bound.

**What overlap does.** With step 1 the windows overlap by *b* − 1 bits, so consecutive
windows must agree on their shared bits. The collection of overlapping windows therefore
constrains the order, much as overlapping reads constrain a genome assembly. Overlap is the
**only channel by which BDM sees order at all**. The price is that every distinct window pays
its full CTM, so one local feature is paid for once per window that contains it (notebook 15,
the "tent" profile). Evidence: on a counter versus a random shuffle of the same blocks
(next section), aligned BDM cannot tell them apart, but step-1 BDM gives 69,154 versus
91,718 bits on the first 4,800 bits of each.

---

## 3. Counterexamples: where BDM can be fooled, and why

Each one comes from §2. None of them says BDM is wrong in general; each marks a boundary.

**C1. Order blindness: the two-word alphabet** (`bdm_probe2.py`, E2). Build a string from *m*
blocks, each either twelve 0s or twelve 1s. In one string they alternate (a tiny program); in
the other their order is random (an arbitrary order of *m*/2 of each needs about log2 C(m, m/2)
bits to state).

| m | length | BDM, alternating | BDM, random order | bits needed to state the order |
|---|---|---|---|---|
| 100 | 1,200 | 62.51 | 62.51 | 96.3 |
| 1,000 | 12,000 | 69.15 | 69.15 | 994.7 |
| 10,000 | 120,000 | 75.80 | 75.80 | 9,993.0 |

The two strings get identical BDM at every size, while the information that separates them
grows without limit. For most random orders, Kolmogorov complexity is at least about the last
column (a counting argument), so BDM understates it by a factor that grows with *m*.

**C2. The counter and the shuffle** (`bdm_probe2.py`, E3). Write all 4,096 twelve-bit words in
counting order: a tiny program. Then shuffle them at random: stating the order needs up to
log2(4096!) ≈ 43,250 bits. BDM with block 12 gives **133,138.5 bits for both**, the sum of the
whole 12-bit table. Note also that this is 2.7 times the 49,152-bit length of the string
itself: CTM values are not on the same scale as raw bits.

**C3. A period that does not fit the block** (notebook 15). A string of period 9 scores 0.91
of a random control at block 8 and 0.13 at block 9. Choosing the block by "lowest BDM"
picks 3, not 9. Repetition is credited only where the grid happens to make it visible.

**C4. Size drift.** Shown in §2: BDM per bit on random data changes by a factor of 20 between
1,200 and 1,200,000 bits. Comparing objects of different sizes therefore compares different
regimes of the measure. This is the mechanism behind the pathinfo finding that the paper's
BDM score correlates with molecule size at r = +0.998.

**C5. Perturbation depends on where the grid falls** (`bdm_probe4b.py`). This is the one that
bears most directly on the causal-perturbation programme. Take a 64 × 64 elementary CA
diagram with periodic space. Rolling the space axis by 1, 2 or 3 columns is an exact
symmetry: the same system, the same cells, relabelled. Only the position of the 4×4 BDM grid
changes. Flip the *same physical cell* and measure the change in BDM in each of the 4 grid
positions, for 60 cells:

| rule | BDM of the same diagram, 4 grid positions | cells whose effect changes sign | median spread of the effect | median size of the effect | rank agreement of cells, position 0 vs 1, 2, 3 |
|---|---|---|---|---|---|
| 30 | 4,756 – 4,981 | **50 %** | 29.7 bits | 27.5 bits | 0.35, 0.17, 0.00 |
| 110 | 3,121 – 3,252 | 27 % | 7.6 | 28.8 | 0.07, 0.04, 0.10 |
| 90 | 2,569 – 2,618 | 22 % | 1.8 | 24.3 | 0.71, 0.58, 0.73 |
| 4 | 176 – 281 | 2 % | 1.0 | 24.3 | 0.17, −0.48, 0.08 |

For rule 30 the spread caused by moving the grid is as large as the effect being measured.
For rule 110 the ranking of cells by their effect is essentially unrelated between grid
positions (rank agreement under 0.1), even though most signs survive. (Rule 4 has many tied
effects, so its rank numbers are unreliable; its signs are stable.) The value 3,121 for
rule 110 matches the number recorded independently in `imp-causalNet-paper`, which is a
useful cross-check of the setup.

*Reading:* a single-cell causal attribution by BDM is a property of the cell **and the
grid**. Aggregates (the sign of a group of cells, averages over many perturbations) are more
stable. This is the same phenomenon, in a CA, as the `imp-causal-paper` finding that BDM is not
a graph invariant: reordering the nodes of the adjacency matrix moves the grid over the
graph, and the magnitudes moved with it while the signs mostly held (97–99 % agreement,
under a node ordering chosen after the fact).

**C6. Many programs, one number** (from `imp-causalNet-paper`, already on record). Over the
256 elementary CA rules, 41 pairs of rules lie within 0.5 bits of each other in BDM, and
BDM exceeds a certified upper bound (a program we actually have) on 254 of 256 rules. Rules
110, 30 and 45 all have a 19.02-bit mechanism and receive 3,121, 4,837 and 5,238 bits.

---

## 4. Granularity: when can BDM find a disruption point?

The test (`bdm_probe3.py`): 128 bits, the first half `0101…` and the second half random, as in
Figure 1 of the 2019 causal-deconvolution paper. Flip each bit, record the change in BDM,
and ask whether the size of the change separates the two halves (AUC: 0.5 means no
separation; near 0 means the regular half reacts much more strongly). The reference band is
the 5–95 % range of the same statistic on 30 fully random strings with no seam.

| block | tiled: AUC | null band | sliding: AUC | null band |
|---|---|---|---|---|
| 1 | 0.484 | 0.42–0.56 | — | — |
| 2 | 0.312 | 0.42–0.59 | 0.228 | 0.41–0.59 |
| 3 | 0.436 | 0.39–0.57 | 0.333 | 0.40–0.59 |
| 4 | 0.205 | 0.40–0.60 | 0.306 | 0.41–0.56 |
| 6 | 0.111 | 0.37–0.54 | 0.221 | 0.39–0.68 |
| 8 | **0.012** | 0.38–0.60 | 0.055 | 0.40–0.57 |
| 12 | 0.024 | 0.40–0.61 | **0.008** | 0.32–0.61 |

*(While running this I found a bug in my own first null — a fresh random generator per
character produced strings of all 0s. It is fixed, and the script now asserts that its null
strings are distinct and balanced.)*

**So, to the question in your notes, "with a length of 2, is discovery of disruption points
possible?":** barely. At block 1 the seam is invisible (inside the null band). At block 2 it is
just outside the band, because the alternating half makes every aligned pair "different"
and the table only knows "same" or "different". At block 3 it falls back inside the band. From
block 4 upwards it becomes clear, and at block 8 or 12 it is almost perfect.

**Why: one number governs it.** Call it the fill ratio: the number of blocks in the input
divided by 2^b, the number of possible words.

* **Fill ratio well below 1** (long words, short input): a random half almost never repeats a
  word, so any repetition is the generator's fingerprint. BDM is sharp. Here 128 bits at
  block 8 is 16 blocks against 256 words.
* **Fill ratio well above 1** (short words, long input): every word repeats anyway, and random
  and structured halves look alike. BDM is blind. At block 3 there are 42 blocks against 8
  words.

This is also the boundary your own notes reach for on pages 12–14, where you look for "the
minimal word length at which unmatched patterns start to appear". That length is where the
fill ratio drops below one. It is a property of the input length, not of the object.

**About 2-D.** pybdm's 2-D tables exist only for 4×4 (and 3×3) blocks, so a "block of 2" for a
CA diagram is not available. The 2-D form of the parameter question is the grid position,
which C5 answers.

**About DNA.** The same mechanics apply to genomic strings over four letters (each base is
two bits, or a 4-symbol table is used). A tandem repeat whose period does not divide the block
length is C3; a reordering of the same motifs is C1; the size of the genome segment sets the
fill ratio. These are hypotheses to test on synthetic sequences with known generators before
touching any real genome.

---

## 5. Why both methods reproduced the same published results, and where they part

**The shared target.** Both methods detect departures from a short generator. BDM sees the
generator indirectly, through its footprint: a short program writes the same blocks again,
and repeated blocks are cheap. Our method sees the generator directly: it asks which index
set and which Boolean rule reproduce every observation, and checks.

**They agree when all of these hold**, and the published test objects satisfy them by design:

1. the generator's regularity is **local** (it fits inside one block) or its period fits the grid;
2. the data are **noiseless**;
3. objects being compared have the **same size** and the **same alignment**;
4. conclusions are read as **signs or group-level orderings**, not single magnitudes.

**They part ways here:**

| | BDM sees it, we do not | we see it, BDM does not |
|---|---|---|
| any object, with no mechanism class assumed | yes | |
| a graded number; ranking unrelated objects | yes | |
| noisy data (we need the robust variant, which held to 20 % noise on rule 110) | yes | |
| how much complexity a program *produces* (its output) | yes | |
| the **program itself**, by name and runnable | | yes |
| **order** between blocks (C1, C2) | | yes |
| an **exact seam** (bit 52 in the causalNet replication) | | yes |
| two rules of similar complexity (Fig. 2: 96.7 % versus failure) | | yes |
| a **certified upper bound**, and falsification by running it | | yes |
| results that do not move with the grid (C5) | | yes |

**Are they equivalent?** No. They give different kinds of answers: a number about how much
structure, versus a mechanism. There is, however, an exact bridge between them: the
two-part code. Our certified length, *D(mechanism) + C(initial state) + log2(steps)*, is
an upper bound on Kolmogorov complexity because the program exists and runs. BDM is an
estimate with a known missing term. The smaller of the two is a better estimate than either
alone, and that is the most promising constructive result this line of work could produce:
an improvement to BDM, not a critique of it.

---

## 6. Can other algorithms emulate BDM?

**A plain dictionary count comes close** (`bdm_probe5.py`). Over 600 strings of 96 bits (ECA
rows from random rules, periodic strings, biased coins), the code length
12 × (number of distinct 12-bit blocks) + sum of log2(counts), with no CTM at all, ranks the
strings the same way as BDM with Spearman 0.93. Replacing that 12 by the average CTM value
leaves a residual of median −5.5 bits (5–95 %: −24.6 to +6.2) on a BDM range of 28.6 to 276.4.
At this scale, most of BDM's ordering comes from *how many distinct blocks there are*, a
combinatorial quantity that dictionary compressors (the LZ family) also track; the CTM table
refines it by tens of bits. Where CTM really earns its place is on short strings, where
compressors have nothing to work with (Hector's "complementary methods" slide, page 11, makes
the same point). The protocol should measure exactly how much of each published BDM result
survives when CTM is replaced by a flat price.

**The arena-planner algorithms cannot emulate BDM, and I would not try.** That project's
planners (TFLM linear and greedy, greedy-by-size, the two-ended layout on path-shaped
conflict graphs) solve interval packing: placing buffers in memory. Description length is a
different problem. What does transfer is the *method* that ended that project in 16 minutes:
compute a lower bound before building anything, and stop if there is no headroom. Here the
analogue is: for each object family, compute BDM and our certified upper bound; the
"headroom" is where BDM sits above a program we can exhibit (254 of 256 CA rules already).
That map tells us where a new method can win and where it cannot.

---

## 7. What Hector's talk does and does not say

Fair reading first. The talk says plainly that BDM is "a weighted version of Shannon entropy"
(page 10), that in the worst case it converges to Shannon entropy, that BDM "traverses the
object" and that "there is a paper where overlapping" changes the estimates, and that the
invariance theorem in practice is a negative result (page 8). It also presents CTM for short
strings and BDM for long ones as complementary regimes. So the existence of these parameters
is acknowledged.

What the talk does not do, as you noticed, is say how to choose them, or how the conclusions
of the applications (CA reconstruction, E. coli, Th17, cell landscapes) change when they
move. That is the gap this study fills: not whether the parameters matter, which is known,
but **which conclusions survive which parameter changes, and why**.

Two places in your own notes line up with what the probes found. Your page-9 point 3, that
splitting into chunks may not be the right way because it hides nested dynamics, is the
multiset result of §2. Your pages 18–20 (A, AX, AXM; P1–P3) are the C1/C2 counterexamples in
small form, and notebook 15 §8 already confirmed that BDM_8 cannot tell AX64 from AXM64.

---

## 8. Proposed skeleton for the protocol

**Questions.** Q1 How does each BDM conclusion depend on block length, step, boundary policy,
grid position and input length? Q2 Which of those dependencies are explained by the
three-part decomposition (§2) and the fill ratio (§4)? Q3 On objects with known generators,
where is BDM above, near or below a certified bound? Q4 How much of BDM's power is the CTM
table, and how much is the dictionary count? Q5 Under which conditions do BDM and index-set
deconvolution agree, and does the agreement survive the parameter sweep?

**Hypotheses to freeze.**
H1 Aligned BDM is invariant under any rearrangement of whole blocks (provable; test as a guard).
H2 BDM's ability to separate a structured from a random region is predicted by the fill ratio.
H3 Single-element perturbation signs and ranks are not stable under grid position, and
their instability rises with the visual randomness of the CA (rule class).
H4 Group-level conclusions of the published applications survive averaging over grid
positions; single-element magnitudes do not.
H5 Adding the arrangement term makes BDM a decodable-style code length whose per-bit value on
random data is stable in length.
H6 A dictionary count with a flat price reproduces most published BDM rankings.

**Factors.** Block length 1–12 (1-D) and grid position 0–3 per axis (2-D); step 1 to *b*;
boundary policy (drop, recursive, refuse); input length over at least three decades; alphabet
(binary, four-letter).

**Object families, all with known generators.** Incommensurate periodic strings;
two-word random orders; counters and de Bruijn sequences versus their shuffles; all 256
ECA rules; Boolean-network repertoires from our corpus; synthetic four-letter sequences with
tandem repeats and motif shuffles. Real data only after the synthetic arms are read.

**Measures.** BDM in each variant; BDM plus arrangement term; the flat-price dictionary count;
an LZ-family compressor as a foil; our certified two-part code; index-set recovery (exact or
not, and where it breaks).

**Controls and gates.** Matched random controls at equal length and alignment for every
number; every result reported over all grid positions, never one; a headroom gate in the
arena-planner style before any new estimator is built; refuse-on-empty and printed
denominators on every check.

**Before claiming novelty.** The original BDM paper (Zenil et al., *Entropy* 20:605, 2018)
states error bounds for BDM and discusses overlapping and boundary variants. It is not on
disk and I did not re-read it for this note. The protocol's first task is to read its bounds
and record exactly which of §2–§4 it already states, so that we cite rather than rediscover.

---

## 9. Limits of this note

* All numbers come from pybdm's D(5) tables; earlier work established that these equal the
  algodyn and Mathematica tables to machine precision, but the 2-D grid result has not been
  repeated in the authors' own code.
* The probes are exploratory: single seeds for the CA diagrams, 30 null strings for the seam
  test, 60 cells per rule. They justify hypotheses, not conclusions.
* "Kolmogorov complexity at least …" statements in C1 and C2 are counting arguments about
  most orders, not values for one particular string.
