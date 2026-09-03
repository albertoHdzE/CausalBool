# AUDIT03 — re-audit under corrected understanding of the method

**Opened 2026-09-02, at the author's instruction.** The concern: my prior work
may rest on a shallow reading of the method, and if so the audit is compromised
wherever that reading did any load-bearing work.

The concern is legitimate and is **partly** confirmed. This plan states exactly
where, on evidence, rather than either dismissing it or accepting it wholesale.

## R0 — Root cause, stated plainly

My understanding of the method was assembled from **code and governance
documents**. I never read the primary sources: `method_paper.tex`,
`comp_paper.tex`, the twelve derivation documents, the UNAM thesis, or
`doc/newIntPaper`. That is the blindness, precisely located.

Its specific content: I treated the gate catalogue as an **unstructured list
indexed by a uniform code**, and I anchored on **arity 3**. In fact a family is
an **arity-parametric closed form** with a band decomposition and a Φ-transport
reading, valid at every arity, and real usage is sharply non-uniform. That is
why my "expanding the catalogue is self-defeating" conclusion was wrong: it was
true only under a uniform code at k = 3, which is the one regime where the
method has nothing to offer.

**R0 is therefore the first task and blocks the rest:** read the primary
sources properly — derivations `01`–`12`, both manuscripts, thesis chapter 4,
`doc/newIntPaper` — and write down the method's own account of what a family
is, what a one-set is, and how description length is charged. No further
judgement is trustworthy until that is done.

## R1 — Dependency triage (the actual question)

Not everything can be infected. A finding that compares gate outputs
**elementwise against an independent implementation or an exhaustive truth
table** cannot be wrong because I misunderstood the economics: it is a
mechanical fact about what the code returns. A finding that rests on a judgement
about what *should* be cheap, expressible, or worth having is exposed.

Provisional classification of all 24 commits, **to be verified in R2, not
trusted as written**:

| class | commits | why it cannot / can be infected |
|---|---|---|
| **MECHANICAL — immune** | `8463895` W0.3 · `2072d7c` P4a-c · `0603eb4` P1-P3 · `5646fbd` A1-A2 · `2ee4d59` B1-B2 · `aca0842` H · `5567064` P4d-e · `d420b3b` P8 · `a4de229` Q1 · `85717ab` W0.5 · `b166b36` W0.1 · `8ebf794` W0.2 · `f245195` Q1-C | every one was settled by elementwise comparison against an exhaustive table, an independent implementation, or a byte-level diff. None quotes a codelength or judges expressibility. |
| **PROCESS — no scientific claim** | `091797b` · `a757618` P5-P7 · `177776c` · `ee77251` · `673747f` · `f056cfd` | archiving, wiring, queue bookkeeping |
| **ECONOMIC — exposed, must be re-tested** | `2fbdddc` P9 · `16bbb36` P9-census · `6c6beae` W1.1 · `dad63cd` P9-closure | each rests on description-length or expressibility reasoning |

### Status of the four exposed items

- **`dad63cd` P9-closure — WRONG, already superseded** by `1eb27a1`. The error
  is documented in `experiments/r4_segmented_grammar/CATALOGUE_EXPANSION.md`.
- **`6c6beae` W1.1 — INFECTED, measured.** `_index_width` charges dictionary
  indices at `ceil(log2 220) = 8` bits, a uniform code. The catalogue's family
  entropy is **2.267 bits**, so the codec overcharges by up to **5.73
  bits/segment**. Direction matters: `L_G` is *overstated*, so the bias is
  **conservative** — it cannot manufacture compression, but it makes C2 and
  every null comparison harder than they should be. Fix: frequency-weighted
  prefix code over the catalogue, Kraft-checked exactly as now.
- **`2fbdddc` / `16bbb36` P9 — measurement sound, framing exposed.** That the
  criterion is vacuous is a mathematical fact (`LUT` is functionally complete)
  and survives. But "the informative statistic is canonical-only 40/256"
  silently assumes a **fixed** catalogue, when the catalogue is expandable by
  construction — which is the whole point of the method. The census must be
  re-read as a statement about *this* catalogue at *this* moment, not about the
  method's reach.

## R2 — Verify the triage instead of trusting it

For each commit in the MECHANICAL class, confirm from the diff and its recorded
evidence that its verdict rests on an elementwise or byte-level comparison and
quotes no codelength or expressibility judgement. Any that does not moves to
ECONOMIC and is re-tested. **The triage above is a hypothesis; R2 is its test.**

## R3 — Re-test the exposed set

1. Rewrite the W1.1 codec's dictionary and occurrence coding as a
   frequency-weighted prefix code; re-run AC-R4-1 with all negative controls;
   re-measure C2. Expect `L_G/n` to fall while staying ≥ 1.00 — if it drops
   below 1.00 that is a Kraft violation and a finding, not a success.
2. Re-word the P9 census framing per the note above. No number changes.
3. Re-examine whether any *other* quoted number in the audit assumes uniform
   coding or a fixed arity.

## R4 — Scheduled: the 13th family

`REGULATORY_DNF`, per `CATALOGUE_EXPANSION.md`: 83.6% of the corpus `CUSTOM`
set, ~18.4 bits/node upper-bound saving. By the established method — visual
exploration → computational expression → formal closed form → derivation
document with elementwise witnesses at arity 2–6.

**Gate before any derivation is written:** measure what fraction of the 2,079
AND/OR/NOT `CUSTOM` formulas the closed form reproduces elementwise. The
18.4 bits/node figure is an upper bound and must not be quoted until that
fraction is known. Catalogue growth is an author gate and moves A3.1.

## What is NOT in scope

Re-opening the mechanical findings on suspicion alone. Silent code returning
`Null`, `0`, or an empty attractor set is wrong under **any** reading of the
method; those repairs stand independently of how description length is charged.
