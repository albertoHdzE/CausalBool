# Successor Transfer for the Method Paper

## Purpose of This Document

This document is a deliberate research handover from one AI assistant to a successor AI assistant.
Its goal is not only to summarize files, but to transfer the working model, scientific intent,
manuscript logic, mathematical posture, evidential architecture, and remaining tasks required to
complete the method paper at the same intellectual standard already established in the cleaned draft.

Read this document before editing anything substantial.

The manuscript has reached a strong and relatively clean state from the beginning through
`Ordering Invariance`. The remaining sections, from `Ordering Invariance` to the end, are useful
but still too rough, compressed, and archive-driven for the intended journal standard. Your task
is to continue the work in a way that feels like a continuation of the same mind, not a stylistic
reset.

---

## Project Identity

### What This Project Is

This repository supports a three-paper scientific programme. The present paper is the first paper:
the formal method paper.

Its central scientific claim is:

> Complex Boolean-network behaviour can be represented, reconstructed, and analysed by short exact
> causal formulas over ordered exhaustive repertoires, provided that ordering is treated as part of
> the mathematics rather than as an implementation accident.

This is not primarily a biology paper.
This is not primarily a machine-learning paper.
This is not primarily an algorithm-engineering paper.

It is a causality-first, mathematics-first, complexity-science paper about exact rule-based
representation of Boolean-network behaviour.

### The Deep Idea

The project began from a simple but powerful question:

Given a Boolean network, can one avoid treating the exhaustive repertoire as an opaque table and
instead derive short exact formulas that specify where outputs occur?

The answer developed here is yes.

The manuscript shows that:

- each gate family admits an exact one-set description
- those one-sets can be written as band, parity, threshold, or canalising constructions
- these local sets can be composed to reconstruct network-level behaviour exactly
- ordering conventions can be controlled analytically by an explicit transform
- mixed-gate interactions admit compression through overlap of queried supports
- broader dynamics can also be analysed on top of the exact repertoire layer

### Publication Ambition

The user wants journal-grade work and repeatedly asked for the standard of an elite complexity
science researcher. That means:

- no vague claims
- no decorative complexity language
- no careless use of "causality"
- no replacing proof with empirical anecdote
- no replacing exactness with mere benchmark success
- no archive dump disguised as narrative

Every section must answer:

1. What exactly is being claimed?
2. What mathematical object supports the claim?
3. What executed evidence corroborates it?
4. Why does it matter scientifically?

---

## Current Status of the Manuscript

### Clean Draft Boundary

At the time of this handover, the manuscript is considered comparatively clean from the start of
the paper through the section:

- `Ordering Invariance`

Everything before and including that section has already undergone major conceptual cleaning,
mathematical strengthening, reframing, and evidence integration.

### What Comes After

From `Ordering Invariance` to the end, the manuscript still contains valuable content, but these
sections remain scientifically rough in several ways:

- too compressed relative to their conceptual importance
- too dependent on older process-documentation prose
- too often declarative when they should be theorem-linked
- not always explicit about what is exact, what is empirical, and what is interpretive
- not yet fully harmonized with the tone and rigor of the earlier cleaned sections

### Main Delegation Target

The next AI assistant should treat the following as the active revision block:

- `Ordering Invariance`
- `Complexity Analysis`
- `Validation Evidence`
- `A Structured Example from Mixed Dynamics`
- `Relation to Algorithmic Causality and Statistical Learning`
- `Discussion`
- `Conclusion`
- appendices from `Appendix A` onward

Do not assume these sections are bad. They are not.
They are scientifically promising but under-polished.

---

## Non-Negotiable Scientific Tone

### Tone Required

The manuscript must sound like a serious mathematical-complexity paper.

Preferred tone:

- precise
- causality-first
- theorem-aware
- conservative where necessary
- interpretive only after exact claims are secured
- explanatory without becoming pedagogically loose

Avoid:

- inflated rhetoric
- speculative philosophy detached from formulas
- generic references to complexity or chaos
- overclaiming novelty
- casual use of "fractal", "emergence", "attractor", "algorithmic", or "causal"

### How to Use Strong Language Correctly

You may use strong language only when it is earned.

Examples:

- good: "The map has only 206 one-step image states out of 1024, so the forward image is strongly constrained."
- bad: "The network exhibits deep emergent order."

- good: "The recurrent set consists of four attractors with basin sizes 488, 320, 204, and 12."
- bad: "The system naturally self-organises into elegant attractors."

### Core Style Principle

Move in the order:

definition -> proposition/theorem -> interpretation -> executed corroboration -> consequence

Do not reverse that order.

---

## The Central Mathematical Architecture

The paper is built around the following objects and ideas.

### Ordered Exhaustive Repertoire

The universe is the ordered exhaustive set of binary inputs for an `n`-node network.
Ordering is mathematical, not implementation trivia.

LSB-first and MSB-first are both allowed, but the manuscript makes the transport between them explicit.

### Gate One-Sets

Each gate family is represented by the exact index set on which its output equals `1`.

Families already integrated in the manuscript include:

- AND
- OR
- NAND
- NOR
- XOR
- XNOR
- NOT
- IMPLIES
- NIMPLIES
- KOFN
- exact-k
- CANALISING

### Deconvolution / Unfolding Logic

The important operator is:

- `Dec(L, S)` in the manuscript as `\operatorname{Dec}(L,S)`

This is the algebraic mechanism by which a compressed base set plus an offset family unfolds to the
full exact repertoire.

### Ordering Transform

The manuscript uses a bit-reversal involution `\varphi` to transport index sets between LSB-first
and MSB-first orderings.

This is not a cosmetic detail.
It is one of the reasons the method is mathematically serious rather than encoding-fragile.

### Network Reconstruction

The core network-level claim is that local exact formulas can be composed to reconstruct exact
network-level behaviour, including mixed-gate cases.

### Overlap Compression

For mixed queries over several nodes, the crucial quantities are:

- `C_q`: query support union
- `F_q`: free coordinates
- `d_q`: sum of local arities
- `c_q = |C_q|`
- `mu_q = d_q - c_q`
- `R_q = 2^{mu_q}`

This is one of the paper's strongest conceptual contributions because it converts the user's earlier
"distribution of information" intuition into exact combinatorics.

### Dynamical Enrichment

The newly added 10-node dynamical subsection does not replace exact repertoire analysis.
It enriches it by distinguishing:

- one-step reachable or realizable image states
- true recurrent attractors under iteration

This distinction is crucial and must not be blurred.

---

## What Has Already Been Achieved

The following are major accomplishments already integrated into the current paper or its direct
paper-local reproducibility assets.

### 1. Repository Reorganization for the Paper Programme

The repository was previously cleaned into a paper-oriented structure.
For the method paper, the key top-level area is:

- `papers/method/`

### 2. Formal Reframing of the Paper

The manuscript is no longer framed as a biology-led narrative.
It is framed as a causal-computational mathematics paper with later relevance to complex systems.

### 3. Consolidated Exact Gate Expressions

The old derivations were recovered and integrated into a unified section with exact gate-family
one-sets.

### 4. Worked Examples

The paper now has:

- a detailed AND case
- a brief XOR case
- a strong 10-node mixed-gate benchmark

The AND example provides the pedagogical template.
The mixed 10-node case provides the compositional power case.

### 5. Real Executed Corroboration

The paper includes real executed code sessions and real outputs rather than invented pseudocode.
This was an explicit requirement from the user and is scientifically important.

### 6. Mixed-Query Overlap Treatment

The 10-node section includes exact overlap definitions, a proposition, a corollary, an overlap graph,
statistics tables, and explicit subsystem factorisation.

### 7. Dynamical Confirmation Layer

A new subsection has been added before `Ordering Invariance` showing how the six analysed 10-node
patterns sit inside a broader reachable/recurrent landscape.

This is important because it grounds the user's "predictability and order" intuition in exact
dynamical classification rather than vague metaphor.

---

## Exact Results You Must Preserve

These values are important anchor points and should not be changed without explicit re-verification.

### 10-Node Overlap Results

For the full 10-node queries:

- `d_q = 21`
- `c_q = 10`
- `mu_q = 11`
- `R_q = 2^11 = 2048`

For `S1`:

- `d_q = 10`
- `c_q = 7`
- `mu_q = 3`
- `R_q = 8`

For `S2`:

- `d_q = 14`
- `c_q = 10`
- `mu_q = 4`
- `R_q = 16`

### Mixed-Query Exact States

The selected full-output cases are:

- `F1 = 1111111111`
- `F2 = 1111111110`
- `F3 = 1111111101`
- `F4 = 1111101111`

Subsystem cases:

- `S1` on nodes `{4,6,7,10}` with projection `0111`
- `S2` on nodes `{4,6,7,8,9,10}` with projection `011101`

### Dynamical 10-Node Results

The new forward-dynamical layer produced:

- image size `|Im(F)| = 206`
- total state space `1024`
- image fraction `206 / 1024 ≈ 0.201171875`

Exact recurrent structure:

| Attractor | Period | Basin Size | Recurrent States |
| --- | ---: | ---: | --- |
| `A1` | 1 | 488 | `0000010100` |
| `A2` | 2 | 320 | `1101010110`, `0110010110` |
| `A3` | 6 | 204 | `1111010101`, `1111010001`, `1111010000`, `1111010010`, `1111010110`, `1111010111` |
| `A4` | 2 | 12 | `1111010100`, `1111010011` |

The three dominant basins cover:

- `488 + 320 + 204 = 1012`
- `1012 / 1024 ≈ 98.8%`

Case status:

| Case | Reachable | Recurrent | Eventual Attractor | Steps to Recurrence |
| --- | --- | --- | --- | ---: |
| `F1` | yes | no | `A2` | 3 |
| `F2` | yes | no | `A2` | 3 |
| `F3` | yes | no | `A2` | 3 |
| `F4` | yes | no | `A1` | 6 |
| `S1` | yes | no | spans `A1,A2,A3,A4` | varies |
| `S2` | yes | no | spans `A1,A2,A3` | varies |

This exact distinction between reachable and recurrent states is one of the most important scientific
discipline points in the current draft.

---

## Files You Need to Understand

## Main Method-Paper Area

- `papers/method/README.md`
  - high-level track framing
- `papers/method/manuscript/README.md`
  - manuscript workspace note
- `papers/method/manuscript/method_paper.tex`
  - the main manuscript and primary active file
- `papers/method/manuscript/references.bib`
  - bibliography source of truth

## Derivation Sources

- `papers/method/derivations/01_causalBool_inputs.tex`
- `papers/method/derivations/02_cb_and.tex`
- `papers/method/derivations/02_cb_or.tex`

These are historically important because they preserve the derivational DNA of the method.

## Paper-Local Code for Reproducibility

### Six-node corroboration

- `papers/method/code/corroboration_6node/corroboration_6node.wl`
- `papers/method/code/corroboration_6node/session_excerpt_and.txt`
- `papers/method/code/corroboration_6node/session_excerpt_xor.txt`
- `papers/method/code/corroboration_6node/exhaustive_rows.tex`

### Ten-node mixed interaction

- `papers/method/code/mixed_interaction_10node/mixed_interaction_10node.wl`
  - the executed mixed-query script for full and subsystem cases
- `papers/method/code/mixed_interaction_10node/session_excerpt_full.txt`
- `papers/method/code/mixed_interaction_10node/session_excerpt_subsystem.txt`
- `papers/method/code/mixed_interaction_10node/full_case_rows.tex`
- `papers/method/code/mixed_interaction_10node/subsystem_case_rows.tex`
- `papers/method/code/mixed_interaction_10node/summary.json`

### Ten-node dynamical layer

- `papers/method/code/mixed_interaction_10node/dynamical_landscape_10node.py`
  - current reliable generator for the dynamical enrichment
- `papers/method/code/mixed_interaction_10node/dynamical_landscape_10node.wl`
  - Wolfram attempt; keep as research record, but the Python fallback is the reliable executed path
- `papers/method/code/mixed_interaction_10node/dynamical_summary.json`
- `papers/method/code/mixed_interaction_10node/dynamical_cycle_rows.tex`
- `papers/method/code/mixed_interaction_10node/dynamical_case_rows.tex`
- `papers/method/code/mixed_interaction_10node/dynamical_sample_rows.tex`
- `papers/method/code/mixed_interaction_10node/dynamical_session_excerpt.txt`

## Important Upstream Knowledge Sources Outside `papers/method`

- `doc/newIntPaper/docProcess.tex`
  - process/theory backbone
- `doc/newIntPaper/expProcess.tex`
  - experimental-validation backbone
- `doc/Tesis-UNAM/tesis.tex`
  - source of the manuscript's Mathematica listing style
- `doc/Tesis-UNAM/Capitulo4/resultados_y_analisis.tex`
  - conceptual ancestor for some explanatory patterns
- `src/scripts/PhaseTransitionExperiment.m`
  - important for robust attractor logic
- `src/integration/Alpha.m`
  - important mainly as a caution: old "attractor" language there is not strict enough

---

## The Evolution of the Research

The paper did not emerge linearly. The evolution matters because it explains why some sections are
clean while others still feel archival.

### Stage 1: Method Formalization

The earliest mature layer was the gate-by-gate formalization of exact expressions over ordered
repertoires.

### Stage 2: Deterministic Corroboration

The next layer was verifying that those formulas matched exhaustive truth-table style generation and
synchronous update outputs.

### Stage 3: Mixed Composition

The method then moved beyond single gates to mixed-gate networks, where the real scientific strength
appeared: exact reconstruction from local formulas in the presence of heterogeneous interaction.

### Stage 4: Overlap and Compression

The overlap analysis transformed a qualitative intuition about "information reuse" into exact
combinatorics.

### Stage 5: Dynamical Enrichment

The recent dynamical subsection was added to show that the analysed mixed patterns are not isolated
artifacts but belong to a broader forward image and eventual attractor skeleton of the same network.

### Stage 6: Archive Integration

Material from `docProcess.tex` and `expProcess.tex` was progressively integrated into the manuscript.
This enriched the paper but also introduced the current problem:

the later sections still retain too much "archive integration" texture and not enough final-paper
shaping.

That is now your job.

---

## What Is Already Strong in the Current Draft

The successor AI should recognize and preserve the paper's current strengths.

### Strength 1: Exactness Is the Backbone

The paper already avoids the common trap of presenting benchmark success as if it were theory.

### Strength 2: Real Executed Evidence

The manuscript contains real code, real outputs, real corroboration tables, and real network cases.

### Strength 3: Compositional Power Is Visible

The 10-node benchmark is much stronger than a collection of isolated gate examples.

### Strength 4: The User's Intuitions Have Been Disciplined

Ideas like information spread, reuse, predictability, and order have been retained, but increasingly
in exact mathematical language.

### Strength 5: The Paper Has a Clear Identity

It now reads as a method paper rather than as a project notebook.

---

## What Is Still Weak from `Ordering Invariance` Onward

This is the most important operational diagnosis for the successor AI.

## 1. `Ordering Invariance`

Current state:

- conceptually correct
- too brief
- theorem is serviceable but underdeveloped

What to improve:

- make explicit the domain and codomain of `\varphi`
- state more clearly why every gate formula is transportable under a consistent relabelling
- connect not just to representation invariance, but to reproducibility and comparability of results
- consider whether a short remark or example should illustrate how the same pattern changes index
  numbers under LSB/MSB while preserving causal meaning

Do not overcomplicate this section, but make it intellectually firmer.

## 2. `Complexity Analysis`

Current state:

- good intentions
- some strong propositions
- still partly archive-translated

Main problems:

- method complexity vs output complexity is present but not yet maximally elegant
- some tables need tighter scientific interpretation
- the distinction between exact predictive semantics and exhaustive materialization should be made
  sharper and more systematic
- description-length discussion is promising but should be made more disciplined

What to do:

- distinguish at least four levels cleanly:
  - local gate evaluation cost
  - network predictive evaluation cost
  - exhaustive output materialization cost
  - validation cost
- explicitly state what the method does not beat, namely the lower bound implied by materializing the
  full exhaustive output
- sharpen the mechanism-vs-dataset complexity argument; this can become one of the strongest late
  sections if written carefully
- interpret the empirical comparison table as evidence for exact-method discipline, not merely speed

## 3. `Validation Evidence`

Current state:

- rich in substance
- not yet elegant enough as a final-paper section

Main problems:

- reads partly as archive summary
- could more clearly map each validation layer to a specific theorem or proposition
- needs stronger separation between semantic-validation layers and performance-validation layers

What to do:

- structure the validation section around the theorem sequence
- build a table with columns like:
  - formal claim
  - validation layer
  - repository evidence
  - scale
  - scientific role
- make the logic explicit:
  - implementation consistency first
  - local gate algebra second
  - ordering invariance third
  - network reconstruction fourth
  - large-scale audit fifth
  - perturbation/noise sixth
- where possible, name concrete result families rather than speaking abstractly

## 4. `A Structured Example from Mixed Dynamics`

Current state:

- interesting idea
- currently underintegrated

Main problems:

- feels more like a thesis echo than a fully justified manuscript section
- may not yet earn its current amount of space
- relation to the main causal-index-set argument is underexplained

Decision options:

- either strengthen it substantially by showing exactly how it illuminates the main method
- or compress/move it to an appendix if it distracts from the theorem-to-evidence line

My recommendation:

- probably reduce its prominence unless you can connect it explicitly to local-rule recoverability,
  node-wise isolation, and interpretation of apparently irregular repertoires

## 5. `Relation to Algorithmic Causality and Statistical Learning`

Current state:

- conceptually correct
- too terse for how important positioning is

Main problems:

- the distinctions are right, but not yet rich enough for publication-level positioning
- the paper's relation to Wolfram, Zenil-style algorithmic causality, and machine learning can be
  sharpened without overclaiming

What to do:

- preserve the current modesty
- say "aligned in spirit, distinct in method"
- emphasize that this paper studies deterministic consequences under known mechanism, not causal
  discovery from data
- distinguish explicit generative rule expression from statistical fitting

## 6. `Discussion`

Current state:

- already contains the right central idea
- still feels more summary-like than journal-definitive

What to do:

- strengthen the four consequences with slightly richer interpretation
- explicitly defend why the unit of explanation shifts from tables to exact rule-induced index sets
- distinguish explanatory compression from ordinary data compression
- reinforce publication strategy: this paper is the method foundation for later domain-facing papers

## 7. `Conclusion`

Current state:

- correct
- slightly compressed relative to the manuscript's ambition

What to do:

- ensure the conclusion restates the theorem-evidence architecture cleanly
- preserve exactness, causality, ordering, composition, and validation as the five key pillars
- avoid introducing new claims here

## 8. Appendices

Current state:

- scientifically useful
- likely too lightly curated

What to do:

- keep appendices as exact support rather than archival overflow
- consider whether Appendix C and D should be tightened so they feel like curated support material,
  not pasted process residue

---

## Practical Guidance for Editing the Remaining Sections

### Editing Rule 1

Do not rewrite everything at once.
Revise section by section, preserving working cross-references.

### Editing Rule 2

Do not degrade precise claims into broader prose.
If a sentence currently carries an exact claim, preserve or strengthen it.

### Editing Rule 3

Where a section still sounds like archive integration, ask:

- what is the theorem-level point?
- what is the exact empirical role?
- what is the journal-worthy interpretation?

Then rewrite around those answers.

### Editing Rule 4

Use tables where they genuinely reduce ambiguity.
This is especially true in the remaining sections.

Good candidates:

- theorem-to-validation mapping table
- complexity-level comparison table
- mechanism-vs-dataset comparison table
- section-by-section claim taxonomy if needed

### Editing Rule 5

Avoid redundant repetition of numbers unless the numbers are doing argumentative work.

---

## Reproducibility Knowledge

### Build Command

To compile the manuscript:

```bash
cd /Users/alberto/Documents/projects/CausalBool/papers/method/manuscript
pdflatex -interaction=nonstopmode -halt-on-error method_paper.tex
```

If bibliography state requires it:

```bash
pdflatex -interaction=nonstopmode -halt-on-error method_paper.tex
bibtex method_paper
pdflatex -interaction=nonstopmode -halt-on-error method_paper.tex
pdflatex -interaction=nonstopmode -halt-on-error method_paper.tex
```

### Ten-Node Dynamical Artifacts

Reliable executed path:

```bash
cd /Users/alberto/Documents/projects/CausalBool
python3 papers/method/code/mixed_interaction_10node/dynamical_landscape_10node.py
```

### Important Caution About Wolfram

The Wolfram version of the dynamical script was created, but the environment produced:

- `No valid password found.`

Therefore:

- do not rely on the `.wl` dynamical path as the primary executable evidence unless the environment
  is repaired
- keep the `.wl` file as a research record and possible future convergence point
- use the Python path for current reproducible dynamical outputs

### Exactness Caution

The paper is exact.
Sampling is used only for validation at large sizes, not as part of the method's definition.
Never blur this distinction.

---

## Working Tree Status at Handover Time

At the time of this transfer, the working tree contains:

- modified `papers/method/manuscript/method_paper.tex`
- untracked dynamical artifacts in `papers/method/code/mixed_interaction_10node/`
- a generated `papers/method/manuscript/method_paper.pdf`

Before making substantial new changes, inspect `git status`.

If the user later asks for a clean commit, include only scientifically relevant outputs.

Possible policy options for the successor:

- keep the generated `.tex`/`.json` dynamical artifacts because they are paper-local reproducibility assets
- avoid committing generated PDFs unless explicitly desired

---

## How the Mathematics Was Deduced

This matters because the successor should preserve not only the results but the mode of reasoning.

### Gate Families

The core deductions were not statistical fits.
They were derived from the exact structure of ordered binary inputs.

Examples:

- AND is the intersection of the `1`-bands of its connected inputs
- OR is the union of those bands
- XOR/XNOR are parity classes on the connected-input set
- thresholds are unions of fixed Hamming-weight layers
- implication families are asymmetric pair conditions
- canalising rules are trigger-set constructions plus fallback logic

### Network Composition

The mixed-network logic follows from intersecting local query conditions and then identifying:

- which coordinates actually matter
- which are free
- how free coordinates generate exact offsets

### Dynamics

The forward-dynamical layer was deduced by explicit functional-graph analysis over all 1024 states
of the 10-node benchmark, separating:

- image states
- eventual cycles
- basin sizes

The conceptual discipline here is:

exact repertoire analysis tells you which rows realise an event;
dynamics tells you how those realised outputs sit inside the network's global evolution.

---

## What Not to Do

Do not do any of the following.

### 1. Do not re-biology the paper

The user explicitly wanted a causality-led, mathematical manuscript.

### 2. Do not turn the late sections into survey prose

The manuscript should not become a review of complexity, ML, algorithmic information theory, or
Boolean-network literature.

### 3. Do not oversell algorithmic causality links

The correct relation is:

- inspired/aligned in spirit
- methodologically distinct

### 4. Do not use "attractor" loosely

Only use it for true recurrent states under iteration.
Use "reachable", "realizable", or "image state" for one-step outputs.

### 5. Do not let performance claims dominate

Speed is secondary.
Exact causal representation is primary.

### 6. Do not let appendices become a dump

If something remains in an appendix, it still needs a clear scientific role.

---

## Suggested Successor Work Plan

This is the order I recommend.

### Phase 1: Tighten `Ordering Invariance`

- strengthen theorem statement
- sharpen proof language
- add a brief interpretive remark if useful

### Phase 2: Rebuild `Complexity Analysis`

- separate exact levels of complexity
- improve tables
- make mechanism-vs-dataset asymmetry a highlight

### Phase 3: Reconstruct `Validation Evidence`

- align validation layers explicitly with theorems and propositions
- make it read like evidential architecture, not archival catalog

### Phase 4: Decide the Fate of `A Structured Example from Mixed Dynamics`

- either upgrade and integrate it
- or compress / move to appendix

### Phase 5: Strengthen Positioning Sections

- expand relation to Wolfram, algorithmic causality, and ML carefully
- keep claims modest and exact

### Phase 6: Upgrade `Discussion` and `Conclusion`

- make them publication-definitive rather than merely accurate

### Phase 7: Curate Appendices

- preserve the exact support material
- remove any lingering sense of process dump

---

## Final Intellectual Instruction to the Successor

You are not inheriting a generic repository.
You are inheriting a partially crystallized scientific argument.

The best way to continue this project is to preserve the following identity:

- exact rather than heuristic
- causal rather than merely descriptive
- compositional rather than table-bound
- mathematically disciplined rather than rhetorically ambitious
- empirically corroborated without letting empiricism replace proof

If you succeed, the later sections will stop feeling like "useful remaining material" and will become
the natural completion of the exact causal-calculus story already established in the first half.

That is the real continuation target.

