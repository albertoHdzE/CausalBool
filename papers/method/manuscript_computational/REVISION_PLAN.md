# Revision Plan — `comp_paper.tex`

Agreed 2026-08-14. Derived from the seven-point review plus two code verifications
(`src/integration/Alpha.m`, `papers/method/code/complexity_analysis/`).

Line anchors refer to `comp_paper.tex` at revision time (1375 lines). Re-locate by
`\label{}` if the file has shifted.

---

## Pass 0 — Correctness (blocking; do before any framing work)

### 0.1 The ZIP figure is wrong and is contradicted by our own companion code

`comp_paper.tex:1052` states ZIP-compressed output $=1600$ bits and
`:1056` states $D_{\mathrm{formula}}/\mathrm{ZIP}=0.0632$, described at `:1057`
as "an order of magnitude smaller".

`papers/method/code/complexity_analysis/complexity_analysis.py:210-217` records that
the archived 1600-bit value came from a Wolfram ZIP file containing only a 64-byte
path-reference string, not the compressed output table. It is a measurement artefact.
The recomputed values in `complexity_results.json` are:

| quantity | manuscript | companion code | status |
|---|---|---|---|
| `C_formula` | 23 | 23 | agrees |
| `D_formula` | 101.07 bits | 101.06574 bits | agrees |
| ZIP | **1600 bits** | **10016 bits** (zlib -9 over the CSV) | **wrong in manuscript** |
| `H_total` | 10229.61 bits | 10229.61016 bits | agrees |
| $D/\mathrm{ZIP}$ | **0.0632** | **0.01009** | **wrong in manuscript** |
| $D/H$ | $9.88\times10^{-3}$ | $9.8797\times10^{-3}$ | agrees |

Action: replace both values; change "an order of magnitude" to "two orders of
magnitude". The corrected number *strengthens* the claim.

### 0.2 `H_total` is a weak baseline and invites a straw-man objection

`H_total` $=2^{10}\times 10\times 0.99899 = 10229.61$ bits, i.e. 99.9 per cent of the
raw 10240-bit table, because the output bits are near-balanced. A referee will observe
that beating an i.i.d. entropy baseline is trivial.

Action: promote the **ZIP comparison to the headline** ($101.07$ vs $10016$ bits, also
two orders of magnitude) and retain `H_total` only as the uncompressed-coding reference.
State plainly that `H_total` is near-maximal *because* the realised outputs are
statistically featureless — which is exactly the point: statistical featurelessness
coexists with extreme algorithmic compressibility. This converts the weakness into
the paper's sharpest argument.

### 0.3 Declare the encoding behind `D_formula`

The encoding is fully specified in `complexity_analysis.py:159-203` but appears
nowhere in the manuscript: per node, $\log_2 K$ with $K=12$ gate types; $\log_2\binom{n}{d}$
for the input set; plus parameter costs ($\log_2(d{+}1)+1$ for KOFN, $\log_2 n + 2$ for
CANALISING, $\log_2 \max(1,d(d{-}1))$ for IMPLIES/NIMPLIES, $\log_2\max(1,d)$ for NOT).

Action: add this as a displayed definition in §4.2. Without it, `D_formula` is an
undefined quantity and the whole compression claim is unfalsifiable. This is also the
precondition for the invariance argument in Pass 3.

### 0.4 `D_formula` in-degree field — RESOLVED 2026-08-14

`encode_node_cost` charged $\log_2\binom{n}{d}$ for the input set without transmitting
$d$. A decoder cannot read that field, nor interpret it as an index into the $d$-subsets
of $[n]$, without $d$ — so the code was not uniquely decodable and the reported figure was
not a valid description length. This was a defect, not a convention.

**Resolved by fixing the code, not by annotating the paper.** A $\log_2(n{+}1)$ in-degree
field is now charged per node:

| | superseded | corrected |
|---|---|---|
| $D_{\mathrm{formula}}$ | 101.07 bits | **135.66 bits** |
| $D/\mathrm{ZIP}$ | 0.01009 | **0.01354** |
| $D/H_{\mathrm{total}}$ | 0.00988 | **0.01326** |
| BDM / $D_{\mathrm{formula}}$ | 5.74× | **4.28×** |

Propagated to `complexity_analysis.py`, `bdm_comparison.py` outputs, both notebooks,
`comp_paper.tex`, **and `manuscript_formal/method_paper.tex`**, which carried the same two
errors (101.07 and the artefactual ZIP = 1600). No conclusion changes: the mechanism remains
two orders of magnitude below every description of its behaviour.

Standing principle established here: the papers report what the experiments yield. Where a
manuscript figure and a corrected computation disagree, the computation wins and the
manuscript is updated — internal or cross-paper consistency is never a reason to retain a
figure known to be invalid.

### 0.6 Repository-wide sweep for stale figures — DONE 2026-08-14

Swept all `.tex/.md/.py/.wl/.m/.json/.ipynb/.txt/.csv` sources and all PDFs for `101.07`,
`0.0632` and `1600 bits`. Finance JSONs and biological CSVs matched coincidentally and were
excluded.

**Fixed (live):**
- `tests/MUnit/Mixed/TSK-MIXED-001-FormulaVsExhaustive.m` — `encodeCostBits` now charges the
  `log2(n+1)` in-degree field. This was the root cause: `complexity_analysis.py` cites it as
  its source, so leaving it would have regenerated the defect on the next test run.
- `papers/method/code/complexity_analysis/README.md` — table corrected, correction record added.
- `papers/method/manuscript_computational/PAPER_PLAN.md` — three stale anchors corrected.

**Marked superseded (no live consumers):**
- `results/tests/mixed001FormulaVsExhaustive/` — added `SUPERSEDED.md`. `Complexity.json` and
  `MixedFormulaVsZIP.tex` came from a removed code path and cannot be regenerated from the
  current suite. The ZIP diagnosis is now confirmed physically: `OutputsBaseline.zip` is 200
  bytes containing one 64-byte entry whose content is the literal string
  `"results/tests/mixed001FormulaVsExhaustive/OutputsBaseline.csv"` — the path, not the data.

**Left intact (provenance archives, per `CLAUDE.md`):**
- `doc/Tesis-UNAM/` — inception of the research; explicitly out of scope by decision.
- `doc/finalpaper/` and `doc/newIntPaper/`, including their PDFs — historical execution
  artefacts in the same category. They record what was believed at the time. Rewriting them
  would falsify provenance rather than correct science.

No talks or slide decks were found in the repository.

### 0.5 Housekeeping

- Title page lists one author; `PAPER_PLAN.md` specifies Hernández-Espinosa & Zenil. Resolve.
- Add to `references.bib`: Holland (1975) *Adaptation in Natural and Artificial Systems*;
  Zenil, *Compression is Comprehension*, arXiv:1904.10258; Zenil, Kiani & Tegnér,
  *Algorithmic Information Dynamics*, CUP 2023; Sakabe, Abrahão, Hernández-Orozco,
  Gudwin & Zenil, arXiv:2606.23471 (preprint — re-check for a published version at
  submission).

---

## Pass 1 — Rebuild §2.2 (point 6; highest value) — DONE 2026-08-14

Current text (`:207-224`) asserts a 128-element string and a flat run-length expression
with no network, no table, no figure, no derivation. Two defects: it is unverifiable,
and the flat RLE reads as symbol counting, which undercuts the paper's central claim.

The example is recoverable and exact. It is node 4 of the thesis 7-node network
(`doc/Tesis-UNAM/Capitulo4/resultados_y_analisis.tex:365-380`):

- `cm07` row 4 = `{1,0,1,0,1,0,1}` → inputs $\{1,3,5,7\}$, gate AND
- connected weights $1+4+16+64 = 85$ → base set $L=\{85\}$ (0-based)
- disconnected nodes $\{2,4,6\}$, weights $\{2,8,32\}$ → $\Omega = \{0,2,8,10,32,34,40,42\}$
- one-set (0-based) $=\{85,87,93,95,117,119,125,127\}$, verified against the thesis
  zero-set listing

Every step checks by hand. This is the ideal worked example: $|L|=1$, $|\Omega|=2^3$.

Rewrite as:

1. Show `cm07` / `dyn07` as a listing (already exists in the thesis).
2. Show node 4's isolated 128-bit output as a figure or compact table.
3. Give the **nested** thesis rule
   $\{85\to0,\ \{\{\{1\to1,1\to0\}\}\to2,\ 4\to0\}\to2,\ 16\to0,\ \{\ldots\}\to2\}$,
   not a flattened list of $(k\to v)$ pairs. The recursion *is* the self-similarity;
   flattening it is what makes the description look statistical.
4. Give $(L,\Omega)$ and a one-line deconvolution reproducing the eight positions exactly.

Scope constraint (per your instruction): present the **behaviour rules as nested patterns**;
do *not* import the behaviour-table construction apparatus from thesis Chapter 4
(the `node-1=pow` / `2^(pow-1)` column machinery). The tables were the route to discovery,
not the result, and reproducing them would bury the point.

Hazards:
- **Indexing.** The thesis is 0-based; the manuscript defines $\mathcal{U}_n=\{1,\ldots,2^n\}$
  (1-based). Convert explicitly and state the convention at the point of use, or the
  worked example will not check.
- **Polarity.** The thesis worked example queries the **zero**-set of node 4
  ($|L|=15$, $|\Omega|=8$); §2.2 discusses the **one**-set. Keep them distinct.
- **Code path.** Generate through the companion library (`CausalBoolCore.wl` / `Gates.m`),
  not the legacy `Alpha.m` path, whose `combiningRepersWithSharedInputs` dispatch
  (`Alpha.m:2126-2133`) implements only XOR/OR/AND/MAJORITY and cannot support the
  twelve-family claim.

**Delivered.** `papers/method/code/worked_example_7node/worked_example_7node.py`
(6/6 self-checks pass), emitting `worked_example_7node.json` and a LaTeX fragment; added to
`run_all.sh`. §2.2 now carries the `cm07`/`dyn07` listing, the full 128-bit output with the
eight firing positions marked, the flat tally, and the generative rule.

**Deviation from plan, deliberate.** The plan called for reproducing the thesis's nested
run-length expression. A first implementation attempted to derive that nesting by
pattern-matching repeated run-pairs; it failed, because the separators differ (1, 5, 21) and
no repeated pair exists. The failure was informative: the thesis nesting is an ad-hoc
presentation of a structure that is exactly expressible. The true generative form is the
**sumset factorisation of the offset family**,
$\Omega = \{0,2\}\oplus\{0,8\}\oplus\{0,32\}$ — one independent binary choice per free
coordinate, verified in code against $\Omega$ itself. This is exact rather than heuristic,
it explains the gap lengths (1, 5, 21 are consequences of the weights 2, 8, 32 rather than
primitive data), and it makes the compression quantitative: 4 tokens against 32.

This single passage supplies the *evidence* for points 2, 4 and 5, which are otherwise
asserted.

---

## Pass 2 — Framing (points 1, 2, 4) — DONE 2026-08-14

### 2.1 AID positioning (point 1) — intro `:110-118`, Discussion `:1243-1255`

Reframe from "grounded in AID" to **the exactly solvable limit of AID**: the corner
where the generating mechanism is given, so algorithmic probability need not be
approximated and the shortest description in the declared language is written in
closed form.

Do **not** write "subset" (subordinates without characterising) and do **not** let the
paper imply it performs AID-style inference. AID proper is perturbation-based discovery
for *unknown* generators; this work does exact querying under a *known* one. The
contribution to AID is a ground-truth regime, not a new estimator. Amend the Discussion
claim that the method "materialises the AID principle" (`:1243`) accordingly.

### 2.2 Compression-as-comprehension (point 2) — intro and Discussion only

Add Zenil (arXiv:1904.10258) and the CUP AID book as the justification for using
programme length rather than Shannon cost as the currency: a short programme that
reproduces behaviour exactly constitutes an explanation; an entropy figure constitutes
a coding cost. Keep it as framing — "comprehension" is philosophical and must not be
presented as a measured quantity. Depends on Pass 0.3: invoking comprehension raises
the evidential bar on `D_formula`, so the encoding must already be declared.

### 2.3 Base set and offset family in the introduction (point 4) — `:140-155`

Compress rather than expand; most of this is already present. Retain "semantics and
topology" (exact, already stated). Restate self-similarity **mechanically**: $\Omega$ is
a sumset of powers of two, hence dyadic, hence the base pattern recurs at geometrically
spaced intervals. Drop "propagation of information/patterns/behaviour" unless the
multi-step sense is meant, which the querying sections do not treat.

---

## Pass 3 — Schemata and the invariance/BDM argument (points 3, 5) — DONE 2026-08-14

### 3.1 Holland schemata (point 3) — §2.2, immediately after the worked example

Claim the **exact** relation, not "confirmation": Holland's don't-care is a definition,
and definitions cannot be empirically confirmed. The true and stronger statement is that
the one-set of every gate is precisely a union of schemata, and $(L,\Omega)$ is a
**schema-normal form** — $L$ fixes the determined coordinates, $\Omega$ enumerates the
don't-care fillings. §2.2 currently gestures at schemata (`:230-236`) and then drops it.

Add the quantitative bridge, which is currently unused: schema **order** is exactly
$|C_q|$, so the scalability result (cost governed by $|C_q|$, not $n$) is a statement
about schema order.

State the disconnected-node claim at three levels, confirmed against
`Alpha.m:2515-2518` (`sum = 2^# &/@ ((Complement[Range[Length[cm]], joinedNames]) - 1)`)
and the accumulation of `joinedNames` across the query (`Alpha.m:2457`, loop `:2493-2505`):

- *Per node, per step*: coordinates in $D_i$ do not affect the output **value** — this is
  what makes them don't-cares.
- *Per repertoire*: they determine **where and how often** the pattern occurs —
  $|\Omega| = 2^{\,n-|C_q|}$, with dyadic spacing set by their bit weights. Causally inert
  as to the value, constitutive of the structure of the behaviour.
- *Per query*: membership in $D$ is **not intrinsic** — it contracts as more nodes are
  jointly interrogated, and the contraction $\mu_q$ *is* the measure of integration.

Also record that $L$ is a constrained join, not a product: `combiningRepersWithSharedInputs`
(`Alpha.m:2075 ff.`) intersects supports, enumerates only the free extension of each added
node, and filters the joined rows on the shared columns. Non-decomposability is in the code.

Formulation to avoid: "disconnected nodes causally influence the output" (false under
one-step semantics). Formulation to use: **causally inert per node, structurally
constitutive of the repertoire, and query-relative rather than intrinsic** — this is the
novel statement and nothing in the current manuscript says it.

Boundary to state explicitly: this concerns the geometry of the one-set under one
synchronous step, not multi-step information flow.

### 3.2 Invariance and BDM (point 5) — §4.2, beside `D_formula`

Invariance, careful version only. Do **not** claim the additive constant disappears; $K$
remains defined up to a constant and $(L,\Omega)$ is optimal only within the chosen formula
language, never call it "the shortest programme". The defensible claim: the description is
a canonical, declared, reproducible encoding of a formula with exact semantics, so the
constant is *fixed and published* rather than unknown and potentially arbitrarily large.
Cite Zenil's own statement of the constant problem (the BDM/decomposition line,
arXiv:1609.00110, and the 2020 Entropy review) so this reads as building on his framing.

**BDM — corrected 2026-08-14. The earlier framing was wrong and must not be used.**

The review originally argued that BDM's block-locality would leave it blind to the
repertoire's long-range structure. That claim was tested and is **false**. Pilot results
(all-column `PartitionRecursive`, seed 7):

| object | BDM | ZIP | H_total |
|---|---|---|---|
| true repertoire (1024×10) | **580** | 10016 | 10229.61 |
| row-shuffled repertoire | 14714 | 16856 | — |
| density-matched random matrix | 15545 | 20912 | — |

BDM separates the true repertoire from a density-matched random one by 27×, and from its
own row-shuffled version by 25×. The effect is robust to partition strategy
(`PartitionIgnore` 29×, `PartitionRecursive` 27×, `PartitionCorrelated` 12×). The reason is
straightforward in hindsight: dyadic offset structure produces literal block repetition at
4×4 scale, which is exactly what BDM's multiplicity term captures.

The corrected ordering, which is what the paper must report:

$$D_{\mathrm{formula}} = 101 \;<\; \mathrm{BDM} = 580 \;\lll\; \mathrm{ZIP} = 10016 \approx H_{\mathrm{total}} = 10230$$

The argument this supports is **stronger** than the one it replaces:

1. BDM beats ZIP and Shannon by a factor of ~17 on this object — algorithmic methods do real
   work where statistical ones do none. State this plainly; it is true and it is favourable.
2. The exact method still lands **5× below the best available algorithmic estimator**, and
   does so exactly rather than approximately.
3. That factor of 5 is the quantity to report: **the price of not knowing the generator**.
   On a class where ground truth exists, BDM comes within 5× of the true programme length.
   This is a quantitative characterisation of BDM's efficiency — a contribution *to* BDM,
   with a number attached.

Still cite Sakabe, Abrahão, Hernández-Orozco, Gudwin & Zenil (arXiv:2606.23471) for the
reusable-code direction, and still frame $(L,\Omega)$ as the limiting case of code reuse
(base pattern described once, reused $|\Omega|$ times, reuse schedule in closed form rather
than inferred). But do **not** claim BDM cannot see the structure. It can.

---

## Pass 4 — Consolidation (point 7) — DONE 2026-08-14

The paper already argues "this is not statistics" in three places: §2.4 (`:344-375`),
§4.2 (`:1025-1080`) and the Discussion (`:1198-1281`). Adding schemata, invariance and
comprehension without deletion will make it repetitive and polemical.

One argument, one location:
- schemata → §2.2, on the worked example
- invariance and BDM complementarity → §4.2, beside `D_formula`
- comprehension → introduction and Discussion only
- delete the resulting duplication in §2.4

Then propagate to the **abstract**, which currently mentions neither the AID-limit
positioning nor comprehension, and to the **conclusion** (`:1281-1327`), whose
"two orders of magnitude" sentence must carry the corrected ZIP figure.

---

## Pass 5 — The BDM comparison programme (new, 2026-08-14)

Rationale: comparing only against ZIP and Shannon invites the objection that weak opponents
were chosen. Including BDM — and showing it wins decisively against them while still costing
5× the exact description — forecloses that objection and converts Pass 3.2 from an argument
into a measurement.

Feasibility confirmed: `pybdm` is already installed in `CausalBool/venv`; no new dependency.

**Framing constraint, non-negotiable.** Every result is reported as *characterising BDM's
efficiency on a class with known ground truth*, never as BDM failing. With Hector Zenil as
co-author this is both the honest reading and the diplomatic one — and after the pilot the
honest reading is genuinely favourable to BDM.

### 5.1 Data side (primary; carries the argument) — LANDED IN §4.2 2026-08-14

BDM over the $2^n \times n$ output repertoire, alongside ZIP and `H_total`, with the
row-shuffle control that holds every row constant and destroys only the LSB-ordering
geometry, thereby isolating the structure the method exploits from the marginals it does not.
Add a density-matched random control. Pin all seeds.

### 5.2 Gate side (secondary; answers "how complex is a gate definition")

**Use truth tables at fixed arity.** For each gate family at common in-degree $d$, the
$2^d$-bit truth table is the gate's *extensional definition* — canonical, representation-free,
and identical length across families, so BDM values are directly comparable. Pilot at $d=4$
(16-bit tables, `PartitionRecursive`, min_length 2):

| gate | BDM | | gate | BDM |
|---|---|---|---|---|
| XOR / XNOR | 41.54 | | MAJORITY | 38.17 |
| KOFN ($k{=}2$) | 41.14 | | OR / NOR | 34.98 |
| NOT / IMPLIES / NIMPLIES | 38.22 | | AND / NAND | 33.80 |

Two sanity checks pass: parity gates rank above monotone gates, as they must; and every
complement pair (XOR/XNOR, AND/NAND, OR/NOR) receives an *identical* value, correct because
complementation costs $O(1)$ bits. The measure is tracking logical structure, not surface form.

Note: `_eval_gate` in `complexity_analysis.py` implements 11 of the 12 families —
`CANALISING` is absent and raises `ValueError`. Add it, or take the gate semantics from
`src/Packages/Integration/Gates.m`, before reporting a twelve-family table.

### 5.3 Rejected variants — do not implement

Two proposed binarisations were piloted and must not be used.

**(a) Synthetic label codes.** Assigning each gate an $m$-bit code and running BDM over the
resulting stream measures *the labelling*, not the gates. Pilot: three arbitrary label
assignments over the identical 10-node network give BDM = 104.67, 108.00, 108.80. Same
network, same gates, three different answers. (Also: 12 gates need 4 bits, not 3 — $2^3 = 8 < 12$.)

**(b) Binarised gate-name text.** BDM over ASCII of the gate names measures English word
length: `OR` 16 bits → 39.59, `AND` 24 → 64.43, `XNOR` 32 → 84.47, `MAJORITY` 64 → 162.47,
i.e. ~2.5 bits of BDM per input bit throughout. It would rank `MAJORITY` as the most complex
gate because the word is longest. This is exactly the failure mode already documented in the
imp-pathinfo replication, where AOAC correlated $r = +0.998$ with molecule size — a size proxy
presenting as a complexity measure.

Both fail the same test the `D_formula` note now states: a measure must respond to the object,
not to its representation.

### 5.4 Mechanism side (tertiary; appendix at most)

BDM(adjacency) $= 103.86$ bits versus $D_{\mathrm{wiring}} = \sum_i \log_2\binom{n}{d_i} = 54.22$
bits. The combinatorial index code is ~2× tighter because it knows the model class (exactly
$d_i$ ones per row) and BDM does not. Interesting but not clean: $D_{\mathrm{formula}}$ also
encodes gate types and parameters, which the adjacency matrix does not contain, so the only
fair pairing is $D_{\mathrm{wiring}}$ against BDM(cm). At 10×10 the object is small enough
that CTM-table coverage is a real concern. Appendix, or omit.

### 5.5 Methodological caveats to state explicitly

- **Partition strategy must be declared.** pybdm's default `PartitionIgnore` silently drops
  leftover columns — at $n=10$ it measures 8 of 10. Report `PartitionRecursive`.
- **CTM coverage.** State BDM's known convergence toward Shannon entropy once blocks outrun
  the CTM tables. Do not present BDM values at scales where this dominates.
- **Seeds pinned and recorded** for every shuffle and random control (project determinism rule).
- **Units.** BDM values are CTM-derived bits; say so, and do not silently treat them as
  interchangeable with the $D_{\mathrm{formula}}$ code length without noting both are bits
  under different conventions.

### 5.6 Deliverables

1. **DONE** — `papers/method/code/complexity_analysis/bdm_comparison.py`, emitting
   `bdm_results.json`; 9/9 internal self-checks pass. `CANALISING` added to
   `_eval_gate` (mirrors `myCanalising`, `Gates.m:18`), so all twelve families now evaluate.
2. **DONE** — experiments R3/R3b in `notebooks/replication_comp_paper.ipynb`, including the
   rejected binarisations as worked negative results.
3. **PENDING (Pass 0)** — revised §4.2 table in the manuscript:
   `D_formula` / BDM / ZIP / `H_total`, four rows.

Measured values to carry into §4.2: BDM(true) = 580.01, BDM/D = 5.74×,
BDM separation from random 26.8× and from row-shuffled 25.4×, ZIP/BDM = 17.3×.
Gate-level: XOR/XNOR 41.54 > KOFN 41.14 > CANALISING 40.15 > NOT/IMPLIES/NIMPLIES 38.22 >
MAJORITY 38.17 > OR/NOR 34.98 > AND/NAND 33.80. Rejected variants: label-code spread
4.91 bits across arbitrary labellings; name-ASCII Pearson r = 0.9978 against word length.

---

## Repository layout for release

```
papers/method/
  code/                                  base code, shareable
    complexity_analysis/
      complexity_analysis.py             D_formula, ZIP, H_total  (+ IMPORTANT note at :158)
      bdm_comparison.py                  Pass 5 experiments
      *_results.json
    corroboration_6node/  mixed_interaction_10node/  scalability_resource_envelope/  lib/
    run_all.sh
  manuscript_computational/
    comp_paper.tex                       the paper
    REVISION_PLAN.md                     this document
    notebooks/
      replication_comp_paper.ipynb       replication of all paper results (31/31 PASS)
      D_formula_explained.ipynb          didactic companion, D_formula only
      replication_results.json
```

Release triad: base code, replication notebook, paper. The didactic notebook rides along as
a companion; further didactic notebooks are to be written on request, not pre-emptively.

---

## Verification

1. `pdflatex -interaction=nonstopmode -halt-on-error comp_paper.tex` — 0 errors,
   0 undefined references.
2. Every number in §4.2 re-checked against `complexity_results.json`.
3. The §2.2 worked example regenerated by script and checked by hand
   ($85 = 1+4+16+64$; $\Omega$ = subset sums of $\{2,8,32\}$; eight positions).
4. All four new citations resolve in the `.bbl`.

## Sequencing

Pass 0 is blocking and independent. Pass 1 is the highest-value change and supplies the
evidence Passes 2 and 3 depend on. Pass 3 depends on Pass 0.3 (declared encoding) and on
Pass 1 (worked example to attach schemata to). Pass 4 is last by construction.


---

## Cross-paper impact review (2026-08-14, after Pass 2)

Pass 2 created forward references to a BDM calibration that did not yet exist in the
manuscript, so Pass 5.1's manuscript deliverable was brought forward to keep the intro and
Discussion truthful. Consequences traced and applied:

1. **§4.2 table** gains a BDM row (580.01 bits) and $D/\mathrm{BDM} = 0.234$, plus a
   "Calibrating an algorithmic estimator against known ground truth" paragraph with both
   controls and a footnote on partition strategy and CTM scale-dependence.
2. **Abstract** rewritten for the AID-limit framing and now states the calibration result.
3. **Conclusion** now cites ZIP alongside $H_{\mathrm{total}}$ and the factor of 4.3.
4. **Appendix dependency claim invalidated and fixed** — "no external dependencies beyond the
   standard library" became false once BDM entered; now states numpy plus a BDM implementation
   with CTM tables, and that seeds and partition strategy are recorded.
5. **§2.4 trimmed** — its algorithmic-versus-statistical paragraph duplicated the new intro.
   Pass 4 consolidation applied early here because Pass 2 caused the duplication.
6. **Formal paper updated** — its "interpretive caution" understated the result as
   \(D\) being "comparatively insensitive" to rewiring. The experiments show it is
   *bit-identical* under rewiring (440/1024 rows change, 206 -> 172 distinct states), and its
   claim that BDM-style estimators "respond to realised output structure" is now supported by
   measurement (580.01 vs 14714 shuffled vs 15545 random). Both stated exactly.

**Verification.** All 17 numbers quoted across both manuscripts checked programmatically
against `bdm_results.json`, `complexity_results.json` and `worked_example_7node.json`: all
match. Replication notebook extended from 31 to **38 checks**, now covering every figure
quoted verbatim in either paper (BDM values, separations, the 2.2 token counts, and the
sumset factorisation of $\Omega$). Both papers compile clean: computational 21pp, formal
34pp, 0 errors and 0 undefined references each.


---

## Pass 3 completion record (2026-08-14)

**3.1 delivered in §2.2**, immediately after the worked example:
- Schema normal form stated as an identity, not an analogy: the one-set of every family is a
  union of schemata and $(L,\Omega)$ is a normal form for it. Node 4 fires on the schema
  $1\ast1\ast1\ast1$.
- Quantitative bridge added: schema order $=|C_q|$, don't-care count $=n-|C_q|$, hence
  $|\Omega|=2^{\,n-|C_q|}$; the scalability result is therefore a statement about schema order.
- Three-level statement of the disconnected-coordinate role (per node/step, per repertoire,
  per query), with the one-step boundary stated explicitly.
- "Confirmation of Holland" avoided throughout, as agreed: a definition cannot be confirmed.

**3.2 completed in §4.2.** The invariance half landed in Pass 0 and the calibration half in
Pass 2; what remained was the reusable-code framing, now added: $L$ is the code written once,
$\Omega$ the schedule of its reuse, given in closed form because it factorises. Cited to
`sakabe2026reusable`. The 4.3× gap is attributed to the estimator having to infer both code
and schedule, which is why the comparison is a calibration and not a competition.

**Error caught during drafting.** The schema string was first written
$\ast1\ast1\ast1\ast$; the connected inputs are $\{1,3,5,7\}$, so the correct template is
$1\ast1\ast1\ast1$. Corrected against the generated JSON before compiling. This is precisely
the class of error the regeneration scripts exist to catch.

**New verification.** The schema-normal-form claim was checked for all twelve families at
arity 3 in a 7-node host: the one-set is a *disjoint* union of $|L|$ schemata
($|{\rm one\text{-}set}| = |L|\cdot|\Omega|$ exactly, for every family), schema order equals
$|C_q|$, and $|\Omega| = 2^{\,n-|C_q|}$. Added to the replication notebook as **R1c**.

**Status.** All five new citations are cited and resolve (14 bibitems). Computational paper
22pp, 0 errors, 0 undefined. Replication notebook **40/40 checks**.


---

## Pass 4 completion record (2026-08-14) — ALL PASSES COMPLETE

Consolidation applied, plus one substantive fix found during the read-through.

**Contradiction resolved in §4.2.** The section stated that perturbation "restructures the
one-sets across all affected nodes" and then, two sentences later, that rewiring leaves
$D_{\mathrm{formula}}$ unchanged. Both are true but the juxtaposition read as a
contradiction. Merged into a single passage in which one experiment makes both points: the
behaviour changes substantially (440/1024 rows, 206 -> 172 distinct states) while the
description length is bit-identical, and both are consequences of the same design.

**Duplication removed.**
- Discussion "Scalability" no longer restates the description-length ratio (it appeared in
  §4.2, the Discussion twice, the Conclusion and the Abstract). It now points to schema order,
  linking Pass 3's result to the scalability claim.
- Discussion perturbation paragraph no longer re-narrates the rewiring; it cites §4.2 and
  keeps only what is distinct — the perturbation asymmetry and the random-mapping pole, now
  tied to the measured density-matched control.

**Limitations strengthened.** Three qualifications added to the description-length results:
$D_{\mathrm{formula}}$ is an upper bound under one declared encoding and not an estimate of
$K$; the 4.3x calibration is one measurement on one network at one scale, not a general
constant, with the cross-family study named as the natural next step; and the estimator is
scale-dependent, converging toward entropy once blocks outrun the base tables.

**Duplication audit (rendered PDF).** "not a complexity measure" 1x; "440 of the 1024" 1x;
"two orders of magnitude" 2x; "factor of 4.3" 4x across abstract / measurement / limitation /
conclusion, each serving a distinct function.

### Final state

| artefact | status |
|---|---|
| `comp_paper.tex` | 23 pp, 0 errors, 0 undefined, 14 citations |
| `manuscript_formal/method_paper.tex` | 34 pp, 0 errors, 0 undefined |
| `worked_example_7node.py` | PASS |
| `complexity_analysis.py` | PASS |
| `bdm_comparison.py` | PASS |
| `replication_comp_paper.ipynb` | 40/40 checks |
| `D_formula_explained.ipynb` | ALL PASS |
| numeric claims cross-checked against generated JSON | 21/21 |

All seven review points are addressed. Remaining optional work: Pass 5.2 (gate-level BDM) and
5.4 (mechanism-side BDM) are computed and verified in `bdm_results.json` but not yet written
into the manuscript; 5.2 would suit an appendix, 5.4 is weak and may be omitted.


---

## Appendix A (gate-level BDM) and a timing-claim correction (2026-08-14)

**Pass 5.2 landed as Appendix~\ref{app:gate-bdm}.** BDM over truth tables at arity 4 for all
twelve families, with the two sanity conditions stated as checks: parity > threshold > monotone
ordering, and identical values for every complement pair (complementation costs $O(1)$ bits).
The two rejected binarisations are included as worked negative results, since they justify the
choice of representation: arbitrary label codes give 104.58/101.91/106.82 bits for the *same*
network, and name-ASCII correlates with English word length at $r=0.998$. Cross-referenced from
§4.2. **Pass 5.4 (mechanism-side BDM) omitted** as recommended: $D_{\mathrm{formula}}$ and
BDM(cm) do not describe the same object, and the caveats would exceed the value.

**A timing claim was found to be unsound and has been corrected in both papers.** The
replication notebook's R5 check failed on a re-run: median wall time for the heaviest query
tier at $n=200$ came in at 1.004 ms against a claimed "sub-millisecond". Repeating the
benchmark four times gave 0.95-1.00 ms for that tier, with maxima to 3.5 ms. The claim was
knife-edge and hardware-dependent.

Corrected in six places (three per paper) to state what is actually robust: analytic time is of
the order of a millisecond or below and, decisively, **does not grow with $n$** --
$t(n{=}200)/t(n{=}30)$ is 1.03, 0.86 and 2.05 for the three query tiers against a size ratio of
6.67. The absolute figure is incidental and hardware-dependent; the size-independence is the
scientific claim and it is strongly supported.

The notebook check was rewritten accordingly: it now tests the time ratio against the size
ratio rather than an absolute wall-clock threshold, and reports the measured times for the
record. A hard threshold on wall-clock time is not a reproducible test.

**Final state:** comp_paper 24 pp, method_paper 34 pp, both 0 errors / 0 undefined.
Replication notebook **45/45 checks**.
