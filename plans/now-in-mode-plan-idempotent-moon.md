# AUDIT03 — R0: read the theory, then collapse to one owner per concept

## Context

**This file previously held the AUDIT02 Phase 2 plan (2026-09-02). Every phase of
it is now closed** — A0/Finding H by `aca0842` and `2ee4d59`, A1/A2 by `5646fbd`,
B1/B2 by `2ee4d59`, Phase C by `5567064` and `a757618`. Its regression bar was
also stale (`OK=52 FAIL=1 TOTAL=53`, `verify-paper 3 of 8`; the live values are
`OK=54 FAIL=1 TOTAL=55` and `7 of 8`). It is replaced here.

### Why this plan exists

AUDIT02 verified *computations*. AUDIT03 exists because three defects were then
found that no amount of computational verification would have caught, and **all
three were found by an author question, never by my own triage**:

1. **The bio description length was not a description length.**
   `bio_D_experiment.py` and `BioMetrics.m` charged `log2 C(n,d)` for a node's
   input set without ever transmitting `d`. Kraft sum `n+1`, not 1. Fixed and
   proved by decoder in `2fd5082`.
2. **I reached for Shannon entropy inside an algorithmic accounting**, then used
   the same error a second time to "find" a bug in my own W1.1 codec that was not
   a bug.
3. **I asserted Ω is the disconnected coordinates.** It is not — sumandos are the
   don't-cares of each schema, wherever they fall. Rule 110 has three inputs, all
   connected, and decomposes as `01*`, `10*`, `*10`. The correct reading had been
   recorded on 2026-07-09 and I did not find it. Purged and guarded in `cbfe02a`.

All three share one signature: **I read an implementation and inferred a
definition.** R0 is the response, and it blocks every judgement below it.

A fourth finding reframed the work: one concept has many homes.

```
per-node description length : 8 implementations   (2 were wrong for 18 days)
gate semantics              : 8 implementations
allOffsets / offset family  : 3 sites
"sumandos"                  : 2 incompatible definitions
```

The author considered splitting the project into sibling repositories and
**decided against it** (2026-09-03), on evidence: the one thing already split
carries a defect left unfixed *because* of the boundary (`GLOSSARY.md:236`,
deferred in `AUDIT02_QUEUE` Q4), while the in-repo vendored copy
`imp-prices/vendor/causalbool.py` is byte-identical to its source. **Split by
ownership of a concept, not by repository.** That is R2.

The durable record is `audit/AUDIT03_PLAN.md` (committed `61a923f`). This file is
the operative near-term plan.

---

## Where the work stands

| phase | what it is | state |
|---|---|---|
| **R0** | Read the primary sources → `METHOD_ACCOUNT.md` → **author gate** | **NEXT** · blocks R2b, R3, R4 |
| **R1** | Correct the record | not started |
| **R2** | The collapse: one owner per concept | R2a.1 census **done**; R2a.2 partly blocked |
| **R3** | The measure decision, then regenerate | **author gate** |
| **R4** | The thirteenth family (`REGULATORY_DNF`) | after R0.3 + R3 |
| **R5** | W1.2–W1.5 | blocked on Q2.1–Q2.3 |
| **R6** | Leftover guards | R6.3 done (`cbfe02a`) |
| **R7** | Repo hygiene — `.git` is 8.8 GB | independent |

---

## R0 — the work of this session

### R0.1 Read, in this order

| source | lines |
|---|---|
| `papers/method/derivations/01_causalBool_inputs.tex` → `02_cb_and` → `02_cb_or` → `03`–`12` | ~990 total |
| `papers/method/derivations/exam.tex` — the computational sampling step | |
| `papers/method/manuscript_formal/method_paper.tex` | 2,139 |
| `papers/method/manuscript_computational/comp_paper.tex` | 1,803 |
| `doc/Tesis-UNAM/Capitulo4/resultados_y_analisis.tex` — the IIT-influenced origin | 1,377 |
| `doc/newIntPaper/bioProcess.tex` and `bioPlan*.md` | |

Read the `.tex` sources, not the PDFs. Record, while reading, every point where a
document states something the code contradicts — that list is an R1 input.

### R0.2 Write `audit/METHOD_ACCOUNT.md`

**Format decision (mine, stated so it can be overruled): one checkable claim per
line, each with a source citation `file:line`.** Not a narrative. The whole
purpose of this document is that the author can falsify it quickly; a narrative
account is pleasant to read and hard to check, which is the wrong trade for a
gate. Target ≤ 120 claims.

It must state explicitly:

- what a **family** is — an arity-parametric closed form, not a table entry;
- what a **one-set**, **base set `L`** and **offset family `Ω`** are, with **Ω
  defined per schema** and the disconnected coordinates named as *the special
  case that is always present*, per `GOVERNANCE/GLOSSARY.md` §1d;
- what **deconvolution** `Dec(L,Ω)` is, and why the word is used;
- how **description length** is charged, and **in what declared language**;
- where **BDM** legitimately applies, and to what objects;
- where **Shannon** is a permitted comparison baseline (as `BDM_Wrapper` labels
  it) and where it must never appear;
- the **ordering convention** (LSB/MSB and the `φ` bit-reversal), since every
  index-set statement is ordering-relative.

### R0.3 — the gate

The author reads `METHOD_ACCOUNT.md` and confirms or corrects it. **R2b, R3 and
R4 may not start until it passes.** This is the only defence against the failure
mode above, because a control only ever tests the question you thought to ask.

### R2a.2 — runs alongside R0, needs no theory

Comparing implementations against each other is immune to the blindness. From the
census (`audit/AUDIT03_R2_collapse/census.py`, committed `61a923f`):

- **offset family — CLEARED to merge.** The three sites differ *textually*
  (`corroboration_6node.wl` lacks the `If[Length[ws]==0, {0}, ...]` guard) but are
  *functionally* identical: `Dot[{},{}]` is 0 in Wolfram, and over `n=1..6` with
  every connected subset the two forms agree on **126 of 126** cases
  (`probe_alloffsets_parity.wl`). Merge to one owner; the survivor's **name** is
  an R2b question, because it computes the special case.
- **gate semantics — BLOCKED.** `complexity_analysis._eval_gate` and
  `causalbool.apply_gate` agree on **value** in all 300 cells but disagree on the
  **call contract**: the first raises `KeyError 'pair'` for `IMPLIES` at `d=1`
  where the second returns `1`. Reconcile the contract, and **re-run** the
  AUDIT02 135/135 Wolfram parity claim rather than citing it, before any deletion.
- **description length — R2b.** Its 8 sites split 4 with the in-degree field and
  4 without; which becomes canonical *is* the `D_formula` vs `D_schema` decision.

**The rule, on the face of the phase:** no copy is deleted until an elementwise
parity run against the survivor is committed as evidence, and every collapse adds
its symbol to `tools/check_single_engine.sh` **in the same commit**.

---

## Files this session will touch

- **create** `audit/METHOD_ACCOUNT.md` — the deliverable.
- **create** `audit/AUDIT03_R2_collapse/parity_offsets.md` — the R2a.2 evidence.
- **edit** the surviving `allOffsets` owner and its two call sites; **archive**
  the redundant definitions per the archive policy, not delete.
- **edit** `tools/check_single_engine.sh` — add the offset-family symbol.
- **edit** `audit/AUDIT03_PLAN.md` — mark R0.2 delivered, R2a.2 progress.

Nothing in `src/Packages/`, `src/integration/` or either manuscript changes in
R0; the reading phase produces a document, not a diff.

---

## Verification

```bash
# R0 has no automated test. Its gate is the author reading METHOD_ACCOUNT.md.
# What CAN be checked is that the account does not contradict the guards:
zsh tools/check_glossary_conformance.sh      # sec.1d must stay clean

# R2a.2 — parity BEFORE any deletion, and the guard AFTER it
HOME=$HOME /Applications/Wolfram.app/Contents/MacOS/WolframKernel -script \
  audit/AUDIT03_R2_collapse/probe_alloffsets_parity.wl     # 126/126, 0 differ
venv/bin/python audit/AUDIT03_R2_collapse/census.py
zsh tools/check_single_engine.sh                            # must list the new symbol

# the producers that consume allOffsets must be re-run after the merge
HOME=$HOME .../WolframKernel -script papers/method/manuscript_computational/generate_paper_outputs.wl
HOME=$HOME .../WolframKernel -script papers/method/code/corroboration_6node/corroboration_6node.wl
HOME=$HOME .../WolframKernel -script papers/method/code/mixed_interaction_10node/mixed_interaction_10node.wl

# standing regression bar — must not move
zsh tests/MUnit/run-tests.sh --all     # OK=54 FAIL=1 TOTAL=55, sole red TopologiesTests
make closure                           # paper-number 109 identical; sync clean;
                                       # conformance clean; single-engine clean;
                                       # verify-paper 7 covered, 1 pending
(cd index-deconvolution && ../venv/bin/python -m pytest -q)      # 146
(cd imp-prices && .venv/bin/python -m pytest -q -p no:warnings)  # 97
venv/bin/python -m pytest -q tests/analysis                      # 23
```

**Acceptance.** `METHOD_ACCOUNT.md` exists, every claim carries a `file:line`
citation, and it is handed to the author for R0.3. The offset-family merge ships
with its parity evidence and its guard in one commit. Every bar above unmoved.

**Stop condition.** R0.3 is a hard gate. When `METHOD_ACCOUNT.md` is delivered,
**stop and report** — do not begin R2b, R3 or R4 on my own reading of the theory.
That is precisely what produced the three defects this audit exists to repair.
