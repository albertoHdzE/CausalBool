# Official sources consulted

| source | what it settles |
|---|---|
| `papers/ACausalDeconvolutionNetGeneMecha.pdf` | preprint, `arXiv:1802.09904v8` |
| `papers/CausalDeconvByAlgoGenModels.pdf` | published version, *Nature Machine Intelligence* **1**(1) 58–66 (2019) |
| `papers/SupInfoDecon.pdf` | published Supplementary Information |
| [`allgebrist/Causal-Deconvolution-of-Networks`](https://github.com/allgebrist/Causal-Deconvolution-of-Networks) | the authors' own R implementation — the decisive source |

The published paper and supplement are textually near-identical to the preprint and add no
experimental parameters. Everything below comes from the R repository.

```bash
git clone --depth 1 https://github.com/allgebrist/Causal-Deconvolution-of-Networks /tmp/cdn
```

## What the R code settles

**1. `log(2)` is `log2(2)` = 1 bit.** `deconvolveterm.R`:

```r
if(abs(information_differences[i]-log2(2)) > epsilon) {
    cutting_points <- c(cutting_points, i+1)
}
```

This is also correct on first principles: `I(G,e)` is a difference of BDM values and BDM is
measured in bits. Reading the paper's "log(2)" as a natural logarithm is what made
Algorithm 2 look self-contradictory in the first pass of this replication. **That finding
is withdrawn.**

**2. `epsilon = 1` by default** — a literal default argument of
`deconvolve_with_termination(original_graph, block_size, offset, epsilon = 1)`, not a
quantity estimated from the signature. With `log2(2) = 1` the criterion reduces to
`difference > 2` on a descending signature.

**3. The BDM partition takes an `offset`.** `bdm2D(mat, blockSize, offset)` supports
overlapping decompositions, and the test case in `deconvolve.R` uses `offset = 1` (stride
one, fully overlapping) even though the paper's Methods say "no string/array overlapping in
the decomposition". Both are implemented in `official.bdm2d`. Tested at offsets 4, 2 and 1:
**overlapping does not change the verdict on Figs. 3C/3D.**

**4. A cut removes one edge.** Algorithm 2 line 13 says "remove all candidate edges"; the R
code deletes the single edge at the row below the gap. `official.deconvolve_with_termination`
follows the code.

**5. The CTM backend is provably identical.** `data/K-4x4.csv` was checked entry by entry
against `pybdm`'s `CTM-B2-D4x4`: all 65,536 blocks agree to within 1e-6.

## What remains open

* **Cellular-automaton parameters.** No tape width, no initial condition, and no CA code in
  either PDF. The supplement defers to reference [8], the Wolfram Demonstration *Competing
  Cellular Automata* (Hermo-Reyes & Joosten). That page is a JavaScript application; the
  notebook source could not be retrieved from any of the usual download endpoints. The R
  repository covers only the network side. The all-white-neighbourhood rule and the Fig. 2
  geometry therefore remain a reconstruction.
* **`Compress`.** Wolfram's `Compress` is not reproducible outside Mathematica; zlib is
  substituted. Affects only the Sup. Fig. 8–9 baselines.

---

## Addendum: the figures as a source (Part XI of the notebook)

The two remaining gaps were attacked by digitising the supplement's own figure images
(`figures.py`). They are lossless, three-colour and pixel-aligned, so the cell lattice can
be fitted and the pictures turned into data.

**Alignment check.** Fitting a lattice is only trustworthy if a misalignment would be
detected. It is: take the pure-colour regions and ask which of the 256 elementary rules
reproduce every transition. A half-cell offset leaves none. The digitised Sup. Fig. 2c
leaves exactly `[60]` for the red region and `[110]` for the grey — the two rules its
caption names.

**Recovered.**

| parameter | value |
|---|---|
| Tape width | 100 cells (Sup. Fig. 2c); ~216 for panels 2a–b |
| Steps | 100 (101 rows with the initial condition) |
| Initial condition | random row spanning the width, split near cell 40; two single live cells 22 apart for 2a–b |
| Rule assignment | red = 60 = left, grey = 110 = right |

**Corrected: the interaction is stochastic.** `R[531441]` sends every mixed neighbourhood to
one fixed value, so one automaton must consume the other. The published figures interpenetrate
instead. Their mixed transitions admit no deterministic rule at radius 1 (63.8% best-case
accuracy against a 100% control on pure neighbourhoods), and accuracy at larger radii rises
only as the distinct-neighbourhood count approaches the sample count — memorisation, not a
wider rule. The paper's main text states this in prose; its pseudocode does not.

**Still open.** The all-white neighbourhood never occurs in the published panels, so the
figures cannot settle it.

### Addendum 2: the last CA gap, closed from Fig. 1F

The all-white neighbourhood could not be settled from Sup. Fig. 2, because rules 54, 50, 82,
110 and 60 all map `000 → 0`. The preprint's **Fig. 1F runs rule 255**, which maps every
neighbourhood including `000` to a live cell. If the automaton's own rule applied to an
all-white neighbourhood, rule 255 would blacken the whole tape at the first step.

It does not. The figure shows a light cone. Digitising it (`data/fig1f_rules255_110.npy`,
61 rows x 101 cells, two single seeds at columns 60 and 100, 60 steps) gives **2302 all-white
neighbourhoods and 2302 white successors**. The quiescent state is absorbing and overrides
the automaton's own rule.

With that fixed, the recovered specification has no free parameters, and regenerates the
published Fig. 1F exactly over the rule-255 light cone: **4026/4026 cells**.

Remaining: Wolfram `Compress` (zlib substituted, affects only the Sup. Fig. 8-9 baselines),
and Fig. 4's subgraph sizes (the caption gives none and Fig. 4a is a drawn layout, not a
pixel grid, so it cannot be recovered by digitisation).

---

## Regenerating the artefacts from scratch

Everything below is already saved, so none of this is required to re-run the notebook. It is
recorded so a future session can verify the digitisation rather than trust it.

**The authors' R implementation** (needed only by the CTM cross-check in Part X; the test
skips and the notebook prints instructions if it is absent):

```bash
git clone --depth 1 https://github.com/allgebrist/Causal-Deconvolution-of-Networks /tmp/cdn
```

**The figure images**, if the digitised arrays in `data/` are to be re-derived:

```bash
mkdir -p /tmp/figs && cd /tmp/figs
# Supplementary Fig. 2 (panels a, b, c) -- page 13 of the published supplement
pdfimages -png -f 13 -l 13 <repo>/papers/SupInfoDecon.pdf sup13
#   sup13-000 = panel a (54|50), sup13-002 = panel b (82|110), sup13-004 = panel c (60|110)
# Preprint Fig. 1F (rules 255 v 110) -- page 15 of the preprint
pdfimages -png -f 15 -l 15 <repo>/papers/ACausalDeconvolutionNetGeneMecha.pdf p15
#   p15-012 = Fig. 1F (3 colours), p15-014 = Fig. 1G (the footprint)
```

Then `figures.digitise_panel(path)` fits the cell lattice and returns the grid. The
self-validating check is `figures.recover_local_rules`: a correct lattice leaves exactly
`[60]` and `[110]`; a half-cell offset leaves none.

Saved outputs of the above: `data/sup_fig2c_rules60_110.npy` (101x100) and
`data/fig1f_rules255_110.npy` (61x101).
