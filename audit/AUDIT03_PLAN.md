# AUDIT03 — re-audit under corrected understanding of the method

**Opened 2026-09-02. Revised 2026-09-02 after the author's question on
Shannon vs algorithmic complexity, which changed two conclusions.**

The concern: prior work may rest on a shallow reading of the method. It is
legitimate and **partly** confirmed. This plan locates it on evidence, and is
deliberately proportionate — neither a revert nor a whole-project sweep, for
reasons recorded in the decision note at the end.

---

## R0 — Read the primary sources. Blocks everything else.

**Root cause, stated plainly.** My understanding was assembled from *code and
governance documents*. I never read `method_paper.tex`, `comp_paper.tex`, the
twelve derivations, the UNAM thesis, or `doc/newIntPaper`.

Its specific content, now diagnosed twice over:

1. I treated the catalogue as an **unstructured list under a uniform code**,
   anchored at **arity 3**, when a family is an arity-parametric closed form
   and real in-degrees run to 7+.
2. Worse, when correcting (1) I reached for **Shannon entropy** — a property of
   an ensemble — inside an accounting that is **algorithmic**: the length of the
   shortest program that writes the object down, in a fixed declared language.

The second error is the deeper one, and it produced a *second-order* mistake:
I then "found" a bug in my own W1.1 codec that was not a bug. That is the
signature of not knowing the theory: the corrections are as unreliable as the
original.

**R0.1** Read, in order: `papers/method/derivations/01_causalBool_inputs`,
`02_cb_and`, `02_cb_or`, then `03`–`12`; `method_paper.tex`;
`comp_paper.tex`; thesis ch. 4; `doc/newIntPaper/bioProcess*`.

**R0.2** Write `audit/METHOD_ACCOUNT.md` — the method in my own words, stating
explicitly: what a family is; what a one-set / base set / offset family is; how
description length is charged and in what declared language; where BDM applies
and to what; and where Shannon is legitimately used (baselines only) versus
where it must never appear.

**R0.3 — the gate.** The author reads `METHOD_ACCOUNT.md` and confirms or
corrects it. **No task below may start until R0.3 passes.** This is the only
defence against the failure mode above, because controls only ever test the
question you thought to ask.

---

## R1 — Falsify the triage, do not trust it

The classification below is **mine, about my own work**, which is precisely the
thing that should be checked independently. It is a hypothesis with a binary
outcome, not a verdict.

**Claim under test:** *"These 13 commits were settled solely by elementwise
comparison against an exhaustive truth table, an independent implementation, or
a byte-level diff, and none quotes a codelength or judges expressibility."*

| class | commits |
|---|---|
| **MECHANICAL — claimed immune** | `8463895` W0.3 · `2072d7c` P4a-c · `0603eb4` P1-P3 · `5646fbd` A1-A2 · `2ee4d59` B1-B2 · `aca0842` H · `5567064` P4d-e · `d420b3b` P8 · `a4de229` Q1 · `85717ab` W0.5 · `b166b36` W0.1 · `8ebf794` W0.2 · `f245195` Q1-C |
| **PROCESS — no scientific claim** | `091797b` · `a757618` · `177776c` · `ee77251` · `673747f` · `f056cfd` |
| **ECONOMIC — exposed** | `2fbdddc` P9 · `16bbb36` P9-census · `6c6beae` W1.1 · `dad63cd` P9-closure |

**R1.1** For each MECHANICAL commit, read the diff and its recorded evidence and
answer one question: does its verdict depend on any quantity measured in bits,
or on a judgement about what the method *should* express? Any "yes" moves it to
ECONOMIC.

**R1.2** Run this as an independent falsification pass, given the claim and the
evidence and asked to **break it** — not to survey. A general "review
everything" invitation reproduces the blindness; a bounded falsification does
not.

---

## R2 — The exposed set: corrected status

The author's question changed two of these. Recorded so the thrash is visible
rather than hidden.

| item | status after correction |
|---|---|
| `2fbdddc` **P9 vacuity** | **SOUND.** "The criterion is passed by construction because `LUT` is functionally complete" is a fact of logic with no coding theory in it. No action. |
| `16bbb36` **P9 census** | **Measurement sound, framing exposed.** "The informative statistic is canonical-only 40/256" silently assumes a *fixed* catalogue, when expandability is the method's point. **R2.1: reword. No number changes.** |
| `6c6beae` **W1.1 codec** | **NOT infected — my accusation was withdrawn.** `ceil(log2 220)` indexes a *declared catalogue*: a program addressing a fixed library, which is the correct algorithmic cost. My "5.73 bits overcharge" applied the Shannon error a second time. **R2.2: re-verify once more after R0.3, since I have now been wrong in both directions.** |
| `dad63cd` → `1eb27a1` **P9-closure** | **Twice wrong, now right.** Original: "expansion is self-defeating" — wrong. First correction: right direction, **Shannon justification** — wrong. Second correction (pure program length): paid `log2(13)−log2(12)=0.1155` bits × 6,577 nodes = 759 bits; saved 2,486 nodes × raw `2^d` table = 58,976; **net 58,217 bits.** **R2.3: supersede the 18.36 bits/node figure in `CATALOGUE_EXPANSION.md`; it is a Shannon quantity and must not be quoted.** |

---

## R3 — The live metric defect (new, highest priority after R0)

Found by following the author's question, not by my own triage.

`papers/method/code/complexity_analysis/complexity_analysis.py:238` charges an
in-degree field, commented *"required for the code to be uniquely decodable"*:

```python
cost += _log2(n + 1)          # in-degree d
cost += _log2(max(1, math.comb(n, d)))
```

This is what made `D_formula = 135.66` self-delimiting and superseded 101.07.

**`src/integration/bio_D_experiment.py:41` and
`src/Packages/Integration/BioMetrics.m:7` do not charge it.** They go straight
to `log2(C(n,d))`, which no decoder can read without already knowing `d`. The
bio pipeline therefore computes the **old, non-prefix-free D** — the wrong
metric the author remembered, still live in two files.

Magnitude, measured through the pipeline's own loader: **27,756.72 uncharged bits
over 170 networks and 5,204 nodes, 5.3337 bits/node.** (This supersedes the
provisional 34,469, which was over 6,577 — the `nodes` key across all 234 files,
including the 64 the loader rejects. A third count, 4,626, is in circulation in
`CATALOGUE_EXPANSION.md`. Three node counts for one corpus is its own governance
item.) Because it is not a valid code, every bio ΔD was a difference of two
invalid lengths.

**R3.1 — DONE.** Both implementations now charge the field. Proof by decoder, not
by argument: Kraft sum exactly **1** with it and exactly **n+1** without it,
n = 1…8, by exhaustive enumeration; every description round-trips at n = 1…6; the
negative control exhibits **168** colliding descriptions at n = 3 and **404** at
n = 4 once the field is stripped.
**R3.2 — DONE.** Four-way parity, **572 cells, 0 disagreements**:
`bio_D_experiment.py`, `BioMetrics.m` (dumped from the kernel),
`complexity_analysis.py`, and the declared language. All of it in
`audit/AUDIT03_R3_description_length/`.

**R3.2a — the finding that outranks the fix.** The gate field charges `log2 12`,
which indexes twelve labels. **3,977 of 5,204 corpus nodes (76.4%) carry a label
that is not one of them** — `CUSTOM` 2,486, `IDENTITY` 762, `INPUT` 729. The code
cannot *write* three quarters of the corpus, let alone decode it. So the
corrected cost is a valid code **for the twelve-family language**, and the corpus
is largely outside that language. Fixing the in-degree field was necessary and is
not sufficient. **R3.4 is therefore blocked behind R4 as well**: regenerating bio
numbers under a language that cannot express the corpus replaces one invalid
figure with another.

**R3.3 — enumerated, not acted on.** Four further copies still lack the field
(`TSK-THEORY-002`, `TSK-THEORY-004`, the pathinfo mirror, `src/description_lengths.py`),
plus `GOVERNANCE/DESCRIPTION_LENGTHS.md` §1–§2. Also recorded: `D_v2` has no
decodability proof at all (its motif and hierarchy fields are looked-up numbers,
not emitted lengths); input nodes are priced 0 in WL and full cost in Python; and
the T4.5 parity gate structurally cannot see Wolfram drift — it passed today on a
now-stale stored value, which is worse than a red. Full table in the FINDING.
**R3.4** Regenerate, reporting old vs new elementwise. ΔD rankings may move;
that is the finding, not a failure. Note the correction is `n·log2(n+1)`, constant
within a network, so it **cancels in every knockout ΔD** and does **not** cancel
in cross-network comparisons or in `fold_reduction`.

**Author gate:** R3.4 changes published bio numbers, and is now also gated on R4.

---

## R4 — The thirteenth family (scheduled, gated)

`REGULATORY_DNF` — 83.6% of the corpus `CUSTOM` set (2,079 of 2,486), net
saving **58,217 bits** in pure program length.

**R4.1 — the gate, before any derivation is written.** Measure what fraction of
the 2,079 AND/OR/NOT formulas the closed form reproduces **elementwise**. The
58,217-bit figure is an upper bound and may not be quoted until that fraction is
known.
**R4.2** Derive by the established method: visual exploration → computational
expression → formal closed form → band decomposition and Φ-transport reading.
**R4.3** Derivation document `13_cb_regulatory_dnf.tex` with executed witnesses
at arity 2–6, matching `01`–`12`.
**R4.4** Wolfram implementation; cross-language parity against the Python
engine; two-copies rule for the vendored copies.
**R4.5** Consequences: re-run the ECA census (much of the 216/256 becomes
family 13); amend A3.1's pinned expressivity.

**Author gate:** catalogue growth requires a dated amendment with the catalogue
cost paid in code, and it moves a frozen protocol number.

Explicitly **out of scope**: the ~16% `LEQ/GEQ/EQ/LT` residue. That is threshold
logic over multi-valued levels — a different object, matching the 512
multi-valued and 407 threshold formulas already recorded unevaluable. It must
not be forced into a Boolean family.

---

## R5 — Resume the frozen R4 programme

Only after R0.3, R1 and R3 close.

- **W1.2** segmenter (§5 refine-on-residual) + AC-R4-4 refusal path.
- **W1.3** controls C1–C3 — **blocked on the three author decisions below.**
- **W1.4** C4 WTI case, two-tier surrogate null per A1-as-amended-by-A3.
- **W1.5** write-up under label discipline; every recovery claim elementwise.

**Author-gated, blocking W1.3:**
| id | question |
|---|---|
| Q2.1 | rule 232 is multiplicity-3 in A3.3 RS-A while C3 accepts on tuple equality |
| Q2.2 | calibration v2 unreconciled — my MC runs high, Stouffer z = +3.27, p ≈ 0.001 |
| Q2.3 | rule 110 not designated as the AC-R4-4 out-of-frame refusal control |

---

## R6 — Standing guards, so the class of error cannot recur silently

**R6.1** A suite test that fails if any description-length path computes a
frequency-weighted or entropy-derived cost. Shannon is permitted only where the
code already labels it a comparison baseline (as `BDM_Wrapper` correctly does).
**R6.2** Extend `verify-paper` so every quoted bit-count names its declared
language and its decodability proof.
**R6.3** A glossary entry fixing the distinction, so it is enforced by
`check_glossary_conformance.sh` rather than by memory.

---

## Decision note — why not revert, and why not a whole-project sweep

**Not revert.** Reverting restores every pre-existing defect the audit repaired
— silent `0` for eight gate families, `Null` returns, `{}` attractors on 21 of
40 networks, a producer resolving to an interpreter with no pybdm, 6-of-12 gate
coverage, an unpinned `PYTHONHASHSEED`, two unrunnable producers — in order to
undo framing errors in four commits. Those repairs were settled by elementwise
comparison and are re-checkable today. And the fault was in *understanding*;
reverting code does not fix understanding.

**Not a whole-project sweep.** A parallel review starts cold, with the same
blindness, and no way to acquire the method from the code — which is exactly
what failed. It would produce many confident wrong reviews whose agreement
would read as corroboration. The exposure is concentrated in 4 of 24 commits;
sweeping spends the most effort where there is least to find.

**What the sweep proposal gets right** is that self-assessment is not evidence.
R1 keeps that, aimed narrowly: one falsifiable claim, handed out to be broken.
