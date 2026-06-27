# Computational Paper: Planning Document

## Paper Identity

**Working title**: Causal Compression of Boolean Networks via Algorithmic Querying

**Authors**: Alberto Hernández-Espinosa, Hector Zenil

**Framing**: This paper extends the algorithmic querying and compressed
representation approach from the 2019 Entropy paper (arXiv:1904.10393) to all
12 canonical Boolean gate families, overlapping multi-node queries, and networks
up to n=200. It is framed purely within Algorithmic Information Dynamics (AID)
and Boolean network analysis — no IIT/φ/consciousness apparatus.

**Target venue**: Entropy (same journal as the 2019 paper), or Complexity

**Relationship to formal paper**: The formal mathematical foundations
(closed-form index-set formulae, ordering invariance proofs, complexity
propositions) are developed independently in `manuscript_formal/method_paper.tex`
and may be submitted separately to an applied mathematics venue. This
computational paper cites those results as "formal foundations developed in [B]"
without reproducing the proofs.

---

## Intellectual Lineage

```
Wolfram: simple discrete rules generate complex behaviour (PCE)
  ↓
Zenil et al.: Algorithmic Information Dynamics (AID)
  — perturbation analysis, programme-size descriptions, causal querying
  ↓
Hernández-Espinosa & Zenil (2019, Entropy): arXiv:1904.10393
  — perturbation test on Boolean networks
  — DecimalRepertoire + Sumandos = compressed representation
  — onPossibleBehaviour querying function
  — demonstrated on AND/OR/XOR gates, 7-node and 9-node networks
  ↓
UNAM thesis (Hernández-Espinosa):
  — extended thesis version with metacompression pipeline
  — attractor-based analysis, sensitivity formula
  — 16-node tractability demonstration
  — full DecimalRepertoire/Sumandos mechanism with unfolding
  ↓
THIS PAPER:
  — all 12 canonical gate families (not just AND/OR/XOR)
  — exact compressed representations with overlap-aware multi-node queries
  — scalability to n=200 with sub-millisecond evaluation
  — causal compression: D_formula vs H_total (two orders of magnitude)
  — dynamical landscape analysis (attractors, basins)
```

---

## Source Documents

### Primary sources (for content and results)
1. **2019 preprint**: `arXiv:1904.10393` — the condensed published version
2. **UNAM thesis**: `doc/Tesis-UNAM/` — Chapters 2–5 + Appendices 1–3
   - Ch.2 `Capitulo2/marco_teorico.tex` — theoretical framework (IIT background, skip for this paper)
   - Ch.3 `Capitulo3/diseno_experimento.tex` — methods: perturbation test, causal analysis, UBPD, programme-size divergence
   - Ch.4 `Capitulo4/resultados_y_analisis.tex` — results: compression sensitivity, fractal behaviour, DecimalRepertoire/Sumandos, onPossibleBehaviour, metacompression, 5-node/7-node/9-node/16-node demonstrations
   - Ch.5 `Capitulo5/conclusiones.tex` — conclusions and future directions
   - `Apendice1/` — 9-node exhaustive schemas
   - `Apendice2/` — pseudocode algorithms for IIT computation (reference only)
   - `Apendice3/` — metacompression experimental pipeline
3. **Formal manuscript**: `papers/method/manuscript_formal/method_paper.tex` — 34 pages, all formal results
4. **Companion code**: `papers/method/code/` — verified Wolfram + Python scripts

### Key terminology mapping (thesis → this paper)
| Thesis / 2019 preprint | This paper |
|---|---|
| DecimalRepertoire | Base set L |
| Sumandos | Offset family Ω |
| onPossibleBehaviour[nodes, pattern, dyn, cm] | Causal query |
| "Unfolding" the compressed form | Deconvolution: Dec(L, Ω) |
| "Fractal behaviour" / fractal information distribution | Support-locality: compression governed by local gate structure |
| Behaviour tables | Gate one-sets over ordered repertoire |
| System "answering questions about its own behaviour" | Causal querying: which repertoire positions satisfy a target pattern |

---

## What Drops (relative to formal manuscript)

- All theorem/proposition/proof environments (Prop 1–8, Thm 1–2, Cor 1–6)
- Algorithm2e pseudocode environments → replaced by Mathematica code
- Formal ordering invariance section → one-paragraph computational observation
- Formal scalability propositions → keep benchmark data, drop proposition statements
- "Related Work" section on ML contrast → unnecessary without formalism framing
- Any IIT/φ/consciousness references or framing

## What Stays (from formal manuscript)

- 6-node corroboration (AND and XOR cases) — re-presented as Mathematica code + output
- 10-node mixed-gate benchmark with all 6 query patterns — computational demonstration
- Overlap analysis showing compression from 2^21 to 2^10 — explained computationally
- Scalability benchmarks at n=30,60,80,200 — timing tables
- Description-length comparison: D_formula=101.07 bits vs H_total=10229.61 bits
- Dynamical landscape: 206 reachable states, 4 attractors, basin sizes 488/320/204/12
- Numerical anchors: all verified values carry over unchanged

## What Is New or Re-framed

- Explicit citation and extension of 2019 paper from paragraph 1
- Inline Mathematica code (adapted from companion code in `papers/method/code/`)
- Narrative framing as AID: causal querying, algorithmic compression, simple rules
- Extension story: "the 2019 approach handled 3 gate types on small networks; we now cover 12 types at n=200"
- Figures: network diagrams, behaviour patterns, compression visualisations
- Connection to Wolfram's programme: simple local rules ↔ short causal descriptions

---

## Proposed Section Structure

### 1. Introduction (~1.5 pages)
- Boolean networks in biology and computation
- The cost of exhaustive enumeration (2^n)
- AID as intellectual framework: simple rules, causal querying, programme-size descriptions
- Connection to [2019 paper]: what was achieved and what remained open
- This paper's contribution: complete gate coverage, overlap compression, scalability
- "All computational experiments are reproducible via the companion code repository (Appendix)"

### 2. Background (~2 pages)
- Boolean networks: connectivity matrix cm, dynamics vector, ordered repertoire
- Gate semantics: the 12 canonical families (brief table, no formal propositions)
- Ordered repertoire and the querying problem: "at which positions does pattern σ occur?"
- AID principles: perturbation, algorithmic description, causal compression
- Brief recap of 2019 approach: perturbation test → fractal patterns → DecRep/Sumandos

### 3. Causal Querying and Compressed Representations (~4 pages)
- **3.1 Single-gate case: AND deconvolution**
  Show via Mathematica code: define network, compute base set, compute offsets, unfold.
  Compare against exhaustive table. Exact equality on all 64 rows.
- **3.2 Extension to all gate families**
  Table showing base set / offset structure for each of 12 gate types.
  Key observation: monotone gates → band intersections, parity → symmetric-difference,
  threshold → Hamming-weight layers, canalising → hierarchical collapse.
  Presented as computational findings, not propositions.
- **3.3 Ordering conventions**
  One paragraph: bit-reversal involution φ transports all results between LSB and MSB.
  Verified computationally on 6-node benchmark. No formal proof.

### 4. Mixed-Gate Networks and Overlap Compression (~4 pages)
- **4.1 The 10-node benchmark**
  Network definition (Mathematica code). Mixed gate types.
  Show the 6 query patterns (F1–F4, S1, S2) with base sets and offsets.
  Demonstrate exact equality against exhaustive baseline on all 1024 rows.
- **4.2 Overlap analysis**
  Explain computationally: when queried nodes share inputs, the effective search space
  shrinks from 2^d_q to 2^μ_q. Show the 10-node numbers: d_q=21, c_q=10, μ_q=11,
  reduction factor 2048. Subsystem queries: S1 (μ_q=3), S2 (μ_q=4).
- **4.3 What the compression reveals**
  Different output patterns share the same offset family → combinatorial skeleton.
  The overlap structure explains analytically what appears as dispersed behaviour
  in the full repertoire.

### 5. Scalability and Causal Compression (~3 pages)
- **5.1 Resource-envelope benchmarks**
  Timing results at n=30,60,80,200. Median analytic time sub-millisecond throughout.
  Cost governed by support size |C_q|, not network size n.
  Tables from formal manuscript (tab:exact-method, tab:synthesis) re-presented.
- **5.2 Description length**
  D_formula=101.07 bits, C_formula=23, ZIP=1600 bits, H_total=10229.61 bits.
  The causal description is two orders of magnitude shorter than statistical encoding.
  "This is causal compression in a precise, non-rhetorical sense."
- **5.3 Validation summary**
  Brief: exact at n≤13, sampled accuracy 1.0 at n∈{20,50}, sub-ms at n=200.
  Validation-map table.

### 6. Dynamical Landscape (~2 pages)
- Forward dynamics on the 10-node network
- |Im(F)|=206 reachable states, 4 attractors, basin sizes
- Connection: the causal descriptions (backward query) and the dynamical landscape
  (forward iteration) are complementary views of the same network

### 7. Discussion (~1.5 pages)
- What causal compression means: short generative descriptions of complex behaviour
- Connection to Wolfram: simple rules generate rich behaviour; we make this quantitative
- Connection to AID: the querying approach discovers causal structure algorithmically
- Limitations: bounded in-degree, synchronous update
- Future: asynchronous schedules, biological network applications

### 8. Conclusion (~1 page)
- Summary of contributions
- The method as a tool for any domain using Boolean networks

### Appendix: Companion Code and Reproducibility
- Repository structure, how to run, expected outputs

---

## Numerical Anchors (DO NOT CHANGE — verified in formal manuscript)

- 10-node overlap: d_q=21, c_q=10, μ_q=11, R_q=2048
- S1 subsystem: d_q=10, c_q=7, μ_q=3, R_q=8
- S2 subsystem: d_q=14, c_q=10, μ_q=4, R_q=16
- Dynamical landscape: |Im(F)|=206, 4 attractors, A1 basin 488, A2 basin 320, A3 basin 204, A4 basin 12
- D_formula=101.07 bits, C_formula=23, ZIP=1600 bits, H_total=10229.61 bits
- Scalability: median |C_q|=10 for T3 across all n=30,60,80,200; exact time sub-ms

---

## Writing Conventions

- Language: British English, no contractions
- Style: computational/experimental — show code, show output, explain what was observed
- Inline Mathematica code in lstlisting or similar environments (as in the 2019 preprint)
- No theorem/proposition/proof environments
- Figures: network diagrams, behaviour tables, compression visualisations
- Tone: precise but accessible; "we observe that..." not "Proposition X states..."
- Standard: elite complexity science researcher — no vague claims, but no unnecessary formalism
- No Claude as co-author; commit messages substantive

---

## Execution Plan

### Phase 1: Scaffolding
- Create LaTeX file with preamble and section stubs
- Copy references.bib from manuscript_formal
- Set up lstlisting style for Mathematica code

### Phase 2: Core sections (3–4)
- Adapt 6-node AND/XOR examples from formal manuscript into Mathematica code format
- Adapt 10-node benchmark
- Write overlap analysis computationally

### Phase 3: Framing sections (1–2, 7–8)
- Write introduction with 2019 paper connection
- Write background with AID framing
- Write discussion and conclusion

### Phase 4: Scalability and dynamics (5–6)
- Adapt benchmark tables
- Adapt dynamical landscape section

### Phase 5: Polish and compile
- Full bibtex build
- Verify all numerical anchors
- Review for consistency with formal manuscript (no contradictions, no duplication of proofs)
