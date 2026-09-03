# AUDIT03 — re-audit under corrected understanding of the method

**Opened 2026-09-02. Revised 2026-09-02** after the author's question on Shannon
versus algorithmic complexity, which changed two conclusions.
**Restructured 2026-09-03** after the author's question on splitting the project.
The restructure merges two phases, absorbs one into a new one, and adds one; the
phase count does not grow.

The original concern — that prior work rests on a shallow reading of the method —
is legitimate and **partly confirmed**. Three defects have now been found on
evidence, and each was found by following an author question rather than by my
own triage. That pattern is itself the finding, and R0 is the response to it.

---

## Where the work stands, in one table

| phase | what it is | state |
|---|---|---|
| **R0** | Read the primary sources → `METHOD_ACCOUNT.md` → **author gate** | not started · blocks R2b, R3, R4 |
| **R1** | Correct the record | not started |
| **R2** | **The collapse: one owner per concept** | **R2a can start now**; R2b after R0.3 |
| **R3** | The measure decision, then regenerate | **author gate** |
| **R4** | The thirteenth family | after R0.3 and R3 |
| **R5** | Resume the frozen R4 instrument (W1.2–W1.5) | blocked on Q2.1–Q2.3 |
| **R6** | Leftover standing guards | partly done |
| **R7** | Repo hygiene | independent, blocks nothing |

Closed since opening: **R3.1 / R3.2** (`2fd5082`), the **Ω purge and its guard**
(`cbfe02a`), the **(L,Ω) pricing probe** (`c43d6e5`, partly withdrawn by
`ab7e8b9`).

---

## R0 — Read the primary sources. Blocks every judgement.

**Root cause, stated plainly.** My understanding was assembled from *code and
governance documents*. I never read `method_paper.tex`, `comp_paper.tex`, the
twelve derivations, the UNAM thesis, or `doc/newIntPaper`.

The consequences, now three deep:

1. I treated the catalogue as an **unstructured list under a uniform code**,
   anchored at arity 3, when a family is an arity-parametric closed form and real
   in-degrees run to 7+.
2. Correcting (1) I reached for **Shannon entropy** — a property of an ensemble —
   inside an accounting that is **algorithmic**. That produced a *second-order*
   error: I then "found" a bug in my own W1.1 codec that was not a bug.
3. I read `allOffsets` and asserted that **Ω is the disconnected coordinates**.
   It is not. The correct reading had been recorded on 2026-07-09. I did not find
   it because I searched code, not theory.

All three share one signature: **I read an implementation and inferred a
definition.** That is what R0 exists to stop.

**R0.1** Read, in order: `papers/method/derivations/01_causalBool_inputs`,
`02_cb_and`, `02_cb_or`, then `03`–`12`; `method_paper.tex`; `comp_paper.tex`;
thesis ch. 4; `doc/newIntPaper/bioProcess*`.

**R0.2** Write `audit/METHOD_ACCOUNT.md` — the method in my own words, stating
explicitly: what a family is; what a one-set, base set and offset family are, with
**Ω defined per schema and the disconnected coordinates named as the special
case**; how description length is charged and in what declared language; where BDM
applies and to what; and where Shannon is legitimately used (baselines only)
versus where it must never appear.

**R0.3 — the gate.** The author reads `METHOD_ACCOUNT.md` and confirms or corrects
it. **R2b, R3 and R4 may not start until R0.3 passes.** This is the only defence
against the failure mode above, because a control only ever tests the question you
thought to ask.

---

## R1 — Correct the record

*(merges the former R1 and R2; both are small and both are corrections rather than
investigations.)*

**R1.1 — falsify the triage, do not trust it.** The classification below is
**mine, about my own work**. It is a hypothesis with a binary outcome.

> **Claim under test:** *"These 13 commits were settled solely by elementwise
> comparison against an exhaustive truth table, an independent implementation, or
> a byte-level diff, and none quotes a codelength or judges expressibility."*

| class | commits |
|---|---|
| **MECHANICAL — claimed immune** | `8463895` · `2072d7c` · `0603eb4` · `5646fbd` · `2ee4d59` · `aca0842` · `5567064` · `d420b3b` · `a4de229` · `85717ab` · `b166b36` · `8ebf794` · `f245195` |
| **PROCESS — no scientific claim** | `091797b` · `a757618` · `177776c` · `ee77251` · `673747f` · `f056cfd` |
| **ECONOMIC — exposed** | `2fbdddc` · `16bbb36` · `6c6beae` · `dad63cd` |

For each MECHANICAL commit: does its verdict depend on any quantity measured in
bits, or on a judgement about what the method *should* express? Any "yes" moves it
to ECONOMIC. Run as a **bounded falsification** — given the claim and the evidence
and asked to break it. A general "review everything" invitation reproduces the
blindness; this does not.

**R1.2** Reword the P9 census framing (`16bbb36`). "The informative statistic is
canonical-only 40/256" silently assumes a *fixed* catalogue, when expandability is
the method's point. **No number changes.**

**R1.3** Supersede the **18.36 bits/node** figure in
`experiments/r4_segmented_grammar/CATALOGUE_EXPANSION.md`. It is a Shannon
quantity and must not be quoted. The replacement is pure program length: paid
`log2(13) − log2(12) = 0.1155` bits × nodes, against the raw `2^d` tables saved.

**R1.4** Re-verify the W1.1 codec once more. My accusation against it was
withdrawn — `ceil(log2 220)` indexes a *declared catalogue*, which is the correct
algorithmic cost — but I have now been wrong in both directions on it.

---

## R2 — THE COLLAPSE: one owner per concept

*(new; **absorbs the former R3.3**, which specified the wrong fix — it said "patch
the four remaining copies", when the right action is to delete three and import
the fourth.)*

### Why this phase exists

The pain in this project is not file count. It is that **one concept has many
homes**:

```
per-node description length : 8 implementations   (2 were wrong for 18 days)
gate semantics              : 8 implementations
allOffsets / offset family  : 3 copies
"sumandos"                  : 2 incompatible definitions
```

Every defect this audit has found came from that list. And the disease is already
documented in our own guard's header: `Alpha.m` and `src/causal/CausalBool.m`
*"shared ancestry, then received DIFFERENT later fixes, so neither was a
superset."* The description length repeated it exactly — common ancestor, one copy
fixed in August, two not.

`tools/check_single_engine.sh` is already the cure. It guards two symbols. It must
guard the ones that matter.

### R2a — mechanical collapse. **No theory required; starts now, alongside R0.**

Where implementations are *already proven equal*, deletion is safe.

- **R2a.1** Census: for each of the three concepts, list every definition site and
  its current parity status against the others. Read-only. Nothing is deleted on
  the strength of a name matching.
- **R2a.2** For each redundant copy, run an **elementwise parity proof** against
  the intended survivor and commit it as evidence *before* the copy is removed.
  Known starting points: `Gates.m` ≡ `CausalBoolCore.wl` at 135/135;
  `imp-prices/vendor/causalbool.py` byte-identical to
  `index-deconvolution/src/causalbool.py` (0 lines of diff).
- **R2a.3** Delete or archive the copy, and add its symbol to
  `check_single_engine.sh` **in the same commit**.

### R2b — adjudicated collapse. **Blocked on R0.3.**

Where implementations differ in *what they compute*, choosing the canonical one is
a scientific decision, not a refactor. The description length is exactly this:
`D_formula` and `D_schema` are different quantities. That choice is R3.

Carried in from the former R3.3, to be resolved by collapse rather than by patch:

| # | site | note |
|---|---|---|
| 1 | `tests/MUnit/Theory/TSK-THEORY-002-Tests.m` | private copy of `encodeCostBits` |
| 2 | `tests/MUnit/Theory/TSK-THEORY-004-Tests.m` | same |
| 3 | `imp-pathinfo-paper .../causalbool_mirror.node_description_cost` | variant **B**; moves that package's published table |
| 4 | `src/description_lengths.py` | the shared wrapper the T4.5 parity gate tests |
| 5 | `GOVERNANCE/DESCRIPTION_LENGTHS.md` §1–§2 | formulae and all four pinned toy values are pre-fix |

Also carried, recorded and not yet acted on:
- **`D_v2` has no decodability proof at all** — its motif and hierarchy fields are
  numbers *looked up* from a data file, not lengths emitted by any codec here.
- **Input nodes are priced 0 in Wolfram and full cost in Python** — 729 nodes,
  two languages, each self-consistent, together divergent.
- **The T4.5 parity gate cannot see Wolfram drift** — it compares two numbers
  stored in its own fixture instead of re-deriving, and passed today on a value
  that is now stale. A green light on a stale number is worse than a red one.

### The rule that must not be broken

**No copy is deleted until an elementwise parity run against the survivor is
committed as evidence, and every collapse adds its guard in the same commit.**
A refactor across nineteen implementations is precisely where silent breakage
lives; without this rule R2 becomes a larger version of the defect it repairs.

---

## R3 — The measure decision, then regeneration. **Author gate.**

R3.1 and R3.2 are **closed** (`2fd5082`): both bio implementations now charge the
`log2(n+1)` in-degree field, proved by decoder — Kraft exactly 1 with it and
exactly n+1 without, full round-trip at n = 1…6, 168 and 404 collisions in the
negative control, four-way parity over 572 cells with 0 disagreements. Corpus
shortfall **27,756.72 bits over 170 networks and 5,204 nodes, 5.3337 per node**,
superseding the provisional 34,469.

**R3.a — the choice.** Two candidate measures are now on the table, both
verified legal codes:

| | `D_formula` (catalogue) | `D_schema` (schema normal form) |
|---|---|---|
| 10-node flagship | 135.66 bits | 232.72 bits (1.72×) |
| corpus, 1,227 covered nodes | 33,681.9 | 51,807.8 (1.54×) |
| needs a declared catalogue | yes, 12 families | **no** |
| separates OR from XOR at equal in-degree | **no** | **yes** |
| Kraft | 1 | 1, over the 3^n template alphabet |

The author has ruled out a **hybrid**. One measure, explicitly chosen.

**R3.b — the blocker.** `76.4%` of corpus nodes (3,977 of 5,204) carry a label
outside the twelve, and their formulas are multi-valued threshold expressions
already recorded unevaluable (AUDIT02/H). **No description length of any kind
reaches them.** Regenerating bio numbers before this is resolved replaces one
invalid figure with another.

**R3.c** Regenerate, reporting old versus new elementwise. Note the in-degree
correction is `n·log2(n+1)`, constant within a network, so it **cancels in every
knockout ΔD** and does **not** cancel across networks or in `fold_reduction`.

---

## R4 — The thirteenth family. **Author gate.**

`REGULATORY_DNF` — 83.6% of the corpus `CUSTOM` set (2,079 of 2,486).

**R4.1 — the gate, before any derivation is written.** Measure what fraction of
the 2,079 AND/OR/NOT formulas the closed form reproduces **elementwise**. The
58,217-bit saving is an upper bound and may not be quoted until that is known.
**R4.2** Derive by the established method: visual exploration → computational
expression → formal closed form → band decomposition and Φ-transport reading.
**R4.3** `13_cb_regulatory_dnf.tex` with executed witnesses at arity 2–6.
**R4.4** Wolfram implementation; cross-language parity; **collapse discipline from
R2 applies** — one owner, one guard.
**R4.5** Re-run the ECA census; amend A3.1's pinned expressivity (46/256).

**Out of scope:** the ~16% `LEQ/GEQ/EQ/LT` residue. Threshold logic over
multi-valued levels is a different object and must not be forced into a Boolean
family.

---

## R5 — Resume the frozen R4 instrument

Only after R0.3 and R2a.

- **W1.2** segmenter (§5 refine-on-residual) + AC-R4-4 refusal path.
- **W1.3** controls C1–C3 — **blocked on the three author decisions below.**
- **W1.4** C4 WTI case, two-tier surrogate null per A1-as-amended-by-A3.
- **W1.5** write-up under label discipline; every recovery claim elementwise.

| id | question, author-gated, blocking W1.3 |
|---|---|
| Q2.1 | rule 232 is multiplicity-3 in A3.3 RS-A while C3 accepts on tuple equality |
| Q2.2 | calibration v2 unreconciled — my MC runs high, Stouffer z = +3.27, p ≈ 0.001 |
| Q2.3 | rule 110 not designated as the AC-R4-4 out-of-frame refusal control |

---

## R6 — Leftover standing guards

Most guards now ship inside R2, one per collapsed concept. What remains:

**R6.1** A suite test that fails if any description-length path computes a
frequency-weighted or entropy-derived cost. Shannon is permitted only where the
code already labels it a comparison baseline (as `BDM_Wrapper` correctly does).
**R6.2** Extend `verify-paper` so every quoted bit-count names its declared
language and its decodability proof.
**R6.3 — DONE** (`cbfe02a`). `check_glossary_conformance.sh` now enforces
GLOSSARY §1d, verified in both directions: clean on the repaired tree, and it
fires on a planted defect. On its first run it caught a site I had missed.
**R6.4** The paper-number gate keys entries by **line number**, so any prose
insertion trips it wholesale and trains the reader to regenerate without checking.
It reported 91 moved entries today for zero value changes. Key it by content.

---

## R7 — Repo hygiene. Independent; blocks nothing.

```
.git = 8.8 GB       data/ 828 tracked files       results/ 344
```

Move `data/` and `results/` to a data store. This is the one part of the
split proposal that is unambiguously right, and it carries none of the risk,
because **nobody reimplements a dataset**.

---

## Decision note — why not revert, why not a sweep, why not a split

**Not revert.** Reverting restores every pre-existing defect the audit repaired —
silent `0` for eight gate families, `Null` returns, `{}` attractors on 21 of 40
networks, a producer resolving to an interpreter with no pybdm, 6-of-12 gate
coverage, an unpinned `PYTHONHASHSEED`, two unrunnable producers — to undo framing
errors in four commits. And the fault was in *understanding*; reverting code does
not fix understanding.

**Not a whole-project sweep.** A parallel review starts cold with the same
blindness and no way to acquire the method from the code — which is exactly what
failed. It would produce many confident wrong reviews whose agreement would read
as corroboration. R1 keeps the one thing the sweep proposal gets right — that
self-assessment is not evidence — aimed narrowly at a single falsifiable claim.

**Not a split into sibling repositories** (author question, 2026-09-03; resolved
2026-09-03). Splitting by repository freezes duplication rather than removing it.
The evidence is our own: the one thing already split, `series-deconvolution/GLOSSARY.md`,
carries a **known defect left unfixed because of the boundary**
(`GLOSSARY.md:236`, deferred in `AUDIT02_QUEUE` Q4), and cost a repair round on
2026-09-03 when the sync was clobbered. Meanwhile the in-repo vendored copy
`imp-prices/vendor/causalbool.py` is byte-identical to its source, because one
grep finds it and one commit fixes both atomically. Worse, the proposed
raise-a-ticket-and-return flow is exactly how the Ω error survived: the right
definition existed, in another sub-project, and nothing forced the two to meet.
**Split by ownership of a concept (R2), not by repository.** Once each concept has
one implementation and a guard, extracting a package becomes mechanical — the
boundary already exists in the code, and making it physical discovers nothing.
