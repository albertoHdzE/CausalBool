# imp-causalNet-paper

Replication of

> H. Zenil, N. A. Kiani, A. A. Zea, J. Tegnér,
> *Algorithmic Causal Deconvolution of Intertwined Data and Networks by Generating Mechanism*,
> `arXiv:1802.09904v8` (`papers/ACausalDeconvolutionNetGeneMecha.pdf`)

published as *Causal Deconvolution by Algorithmic Generative Models*, **Nature Machine
Intelligence** 1(1), 58–66 (2019) — together with a mirror of the same results in the
CausalBool index-set causal calculus developed in the root of this project.

Three primary sources are used: the preprint, the published paper and supplement, and the
authors' own R implementation at
[`allgebrist/Causal-Deconvolution-of-Networks`](https://github.com/allgebrist/Causal-Deconvolution-of-Networks).
The third settles four ambiguities the PDFs leave open — see `reference/official_sources.md`
and Part X of the notebook. `official.py` holds verified ports of that R code.

This is the second replication in the programme. The first, `imp-causal-paper/`, covers
Zenil *et al.* (2019); the two papers share the Coding Theorem Method and Block
Decomposition Method backbone, so this one concentrates on what is new: **deconvolution**,
the separation of an observation into the generating mechanisms that produced it.

## Quick start

```bash
cd imp-causalNet-paper
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# Part X verifies the authors' R code and CTM table against ours
git clone --depth 1 https://github.com/allgebrist/Causal-Deconvolution-of-Networks /tmp/cdn

.venv/bin/python -m pytest                                    # 47 fidelity tests

.venv/bin/python -m ipykernel install --user --name imp-causalnet
.venv/bin/jupyter nbconvert --to notebook --execute \
    notebooks/paper_walkthrough.ipynb --inplace \
    --ExecutePreprocessor.kernel_name=imp-causalnet
```

The notebook is generated from `notebooks/_build_notebook.py`, so the prose stays
reviewable as plain text. Edit the builder, re-run it, then re-execute the notebook.

Everything is deterministic: all generators are seeded and the CTM tables are fixed.

## Fidelity of the numerical backend

Section 2.4 of the paper fixes the estimator's only parameters — "12 bits for strings and 4
square bits for arrays ... based on all Turing machines with up to 5 states, with no
string/array overlapping in the decomposition". `pybdm` ships exactly those two tables
(`CTM-B2-D12`, `CTM-B2-D4x4`) from the same enumeration, so the backend here is not an
approximation *of* the paper's method; it is the paper's method. The test suite asserts
this rather than assuming it.

The Wolfram Language functions published in Supplementary Information 4.4
(`CausalDeconvolution`, `PIDMI`, `PIDNCD`, `MutualInformation`, `NCD`,
`CalculateInformationRow*`) are transcribed line by line, with the original quoted in the
docstring. One substitution is unavoidable and is flagged in place: Wolfram's `Compress` is
replaced by raw zlib deflate.

## Results

| # | Figure | Claim | Verdict |
|---|---|---|---|
| 1 | 1A–B | Short-mechanism strings are far more perturbation-sensitive; invariant under reversal | **Replicated** — 29.5x separation in mean \|I\| |
| 2 | 1F–G | Footprint separates interacting CA of grossly different complexity (255 vs 110) | **Replicated** — Cliff's delta −0.78 |
| 3 | 2 | Footprint separates interacting CA of *similar* behaviour (60 vs 110) | **Not replicated** — delta 0.15 on the paper's *own* digitised figure (medium needs 0.33) |
| 4 | 4 | Signature breaking points at log(2)+ε deconvolve a composite graph | **Partial** — signature reproduces; 2 of 4 planted edges found |
| 5 | 3C–D | Complete+S-F and E-R+S-F broken into their two components | **Not replicated** — planted edges at ranks 93–163 and ~500/980 |
| 5b | Sec. 3.2 | Same task, both components of *low* algorithmic complexity | **Replicated** — planted edges at ranks 0, 1, 2 |
| 6 | 5 | Robust to additive noise (~0.9 precision, ~5% false positives) | **Replicated in the low-complexity regime** — precision 1.000, FPR 0.000 |
| 7 | Sup. 8–9 | Entropy and compression are not sensitive enough | **Replicated** — MI collapses to a single value, exactly as reported |
| M | Part IX | *Mirror*: index-set calculus on the Fig. 2 image | **Exact** — 99.8% attribution; both rules recovered by number from 256 candidates |
| X | Part X | Authors' CTM table versus ours, entry by entry | **Identical** — all 65,536 blocks agree to 1e-6 |
| F | Part XI | CA parameters recovered by digitising the published figures | **Recovered** — 100 cells × 100 steps; rules 60/110 recovered uniquely from 256 |

The failures share one cause. BDM estimates *program length*, so it separates mechanisms
whose lengths differ and cannot separate mechanisms whose lengths are similar however
different their rules. The paper's own inequality in Section 3.2 states this restriction
("for all `G` of low algorithmic complexity"); its headline figures then apply the method
outside it. Fig. 2F appeals to statistical significance rather than effect size, which is
what lets a negligible difference be presented as a validation.

### Corrections

Two findings from earlier passes are withdrawn.

**The interaction is stochastic, not `R[531441]`.** I modelled a mixed neighbourhood as
resolving deterministically, which makes one automaton consume the other at one cell per
step. Digitising the paper's own Supplementary Fig. 2c shows otherwise: its pure regions are
100% deterministic and recover rules 60 and 110 uniquely out of 256 — confirming the
reading of the image — while its mixed transitions admit no deterministic rule at any
neighbourhood radius. This is what the main text says in prose ("the mixed neighbourhood
⟨2,2,1⟩ may sometimes yield a 0, sometimes a 1 and at yet other times a 2") and what the
pseudocode next to it does not. `evolve_interacting` now defaults to
`interaction="stochastic"`.

An earlier pass of this replication reported that **Algorithm 2's typeset criterion
contradicts the running text and destroys the graph**. That was wrong. It read the paper's
`log(2)` as a natural logarithm; the authors' R code writes `log2(2)`, i.e. **1 bit**, with
a default `epsilon = 1`. On those constants the criterion is `difference > 2` bits, the two
readings agree, and Algorithm 2 is sound. The claim is withdrawn.

One discrepancy in the paper stands: `531441 = 3**12` is the *last* word of
`Tuples[{-1,0,1},12]`, so `R[531441]` maps every mixed neighbourhood to a single fixed
value. The published figures are not consistent with any such rule. The printed enumeration
and the published dynamics do not describe the same model.

## The mirror

`causalbool_mirror.py` puts the same questions to the index-set calculus. The difference is
not a change of estimator but a change of object: BDM asks *how long is the shortest program
for this data?*; the index-set method asks *what is the program?* — for each cell, the
smallest set of inputs and the exact Boolean function reproducing every observation, or a
proof that none exists. That proof of non-existence is the boundary signal.

On the rule-60/rule-110 image that defeated the paper's own method, it attributes every
decidable cell with 99.8% accuracy, locates the interaction front as the 37 cells no
elementary rule explains, and recovers both generating rules **by number** out of 256
candidates from the binary image alone.

On graphs it is a partial improvement (Fig. 3D planted edges move from rank ~500/980 to
~80/980) and does not solve the scale-free case, for a reason stated precisely in the
notebook: an index set over an *unordered* neighbourhood has no canonical description. The
CA case does not suffer from this because a cellular automaton's neighbourhood is
intrinsically ordered.

## Layout

| path | contents |
|---|---|
| `src/imp_causalnet_paper/complexity.py` | BDM, Shannon entropy, mutual information, NCD — Sup. Inf. 4.4 |
| `src/imp_causalnet_paper/fastbdm.py` | exact incremental BDM under single-bit edits (~70x) |
| `src/imp_causalnet_paper/ca.py` | elementary CA, the twelve mixed neighbourhoods, `R[x]`, Gray-code helpers |
| `src/imp_causalnet_paper/footprint.py` | `CausalDeconvolution`, `PIDMI`, `PIDNCD`, `CalculateInformationRow*` |
| `src/imp_causalnet_paper/graphs.py` | generators per Sup. Inf. 4.2 (BA from a 3-cycle seed, E-R, K-ary trees) |
| `src/imp_causalnet_paper/deconvolution.py` | Algorithms 1 and 2, information signature, ε estimation, breaking points |
| `src/imp_causalnet_paper/strings.py` | Fig. 1A–B |
| `src/imp_causalnet_paper/experiments.py` | Figs. 3C–D and 5 runners with the paper's replicate counts |
| `src/imp_causalnet_paper/causalbool_mirror.py` | the index-set mirror; loads the root project's deconvolution code |
| `notebooks/paper_walkthrough.ipynb` | the didactic walkthrough (executed, 141 cells, 28 figures) |
| `notebooks/_build_notebook.py` | its generator |
| `tests/test_replication.py` | 25 fidelity tests |

| `src/imp_causalnet_paper/measure.py` | model description length and the two-part certificate |
| `src/imp_causalnet_paper/graph_mechanism.py` | graph deconvolution by index-set law: exact recognisers + mechanism peeling |
| `src/imp_causalnet_paper/causal_models.py` | explicit generating models: string recurrences, CA Boolean networks, verified forward |
| `src/imp_causalnet_paper/figures.py` | digitises the published figures back into cell grids; recovers rules and tests determinism |
| `src/imp_causalnet_paper/official.py` | verified ports of the authors' R: `bdm2D` (with `offset`), `get_info_signature`, `deconvolve`, `deconvolve_with_termination` |
| `reference/official_sources.md` | what each source settles, and what remains open |

`causalbool_mirror.load_root_modules()` imports `index-deconvolution/src/{causalbool,
deconvolution, ca_deconvolution}.py` from the project root; nothing is duplicated.

## Recovered from the published figures (Part XI)

No source states the CA parameters, so they were read out of the figures themselves. The
supplement embeds them as lossless, three-colour, pixel-aligned images; `figures.py` fits the
cell lattice and recovers:

| parameter | value |
|---|---|
| Tape width | **100 cells** (Sup. Fig. 2c); ~216 for the pyramidal panels 2a–b |
| Steps | **100** — 101 rows including the initial condition |
| Initial condition | **random row spanning the width**, split near cell 40; **two single live cells 22 apart** for Sup. Figs. 2a–b |
| Mixed-neighbourhood resolution | **stochastic** — no deterministic rule at any radius |
| All-white neighbourhood | **stays white** — settled from Fig. 1F, which runs rule 255 (`000 → 1`) and still produces a light cone; 2302/2302 all-white neighbourhoods have white successors |
| Rule assignment | red = 60 = left, grey = 110 = right, recovered uniquely from 256 candidates |

The recovered specification has no free parameters left, and regenerates the published
Fig. 1F **cell for cell** over the rule-255 light cone (4026/4026).

The alignment check is not cosmetic: a half-cell offset would scramble every neighbourhood,
and recovering exactly one elementary rule per colour is what rules that out.

`data/sup_fig2c_rules60_110.npy` ships the digitised panel so the notebook runs without
Poppler or Pillow.

## The two procedures, step by step (Part XV)

Part XV runs **both methods end to end on one shared object** — the paper's own Supplementary
Fig. 2c, rules 60 and 110 — with every intermediate step shown and plotted, then places the
tracks side by side.

| | Track A — Zenil (BDM) | Track B — index-set |
|---|---|---|
| step 1 | BDM of the whole object → 7402 bits | 10,000 causal observations |
| step 2 | flip every pixel, record the change | test 256 rules against each cell |
| step 3 | sort into the information signature | keep rules surviving every observation |
| step 4 | cut where the gap exceeds 2.0 bits | one rule → identified; none → boundary |
| step 5 | colour by sign | draw the truth tables; run them forward |
| **output** | a real number per pixel | **rules 60 and 110**, with their tables |
| separation | Cliff's delta +0.147 (small) | 0.967 accuracy |
| mechanism named | no | yes, from 256 candidates |
| falsifiable | no | yes — the rules regenerate the data or they do not |

The procedures diverge at **step 2**, and everything else follows. BDM asks "how much does the
estimate move?", whose answer is necessarily a number and can never later become a rule. The
index-set calculus asks "which candidate mechanisms survive?", whose answer is a set that can
be narrowed to one. No amount of downstream processing converts one into the other.

## Resuming this work

Everything needed to pick this up is in the repository. Read in this order:

1. **`README.md`** (this file) — what was replicated, what was not, and why.
2. **`COMPARISON.md`** — the face-to-face against Zenil's method, and the figure-by-figure
   parallel inside this paper's scope.
3. **`RESEARCH_NOTES.md`** — three open research threads with evidence already attached.
   This is where the next piece of work starts.
4. **`reference/official_sources.md`** — what each source settles, what remains open, and how
   to regenerate every artefact from the PDFs.
5. **`notebooks/paper_walkthrough.ipynb`** — executed, with all outputs embedded, so it can be
   read without running anything.

**External dependency to be aware of.** `causalbool_mirror.load_root_modules()` imports
`index-deconvolution/src/{causalbool,deconvolution,ca_deconvolution}.py` from the project
root. Nothing is duplicated, which is deliberate — but it does mean Parts IX, XII and XV of
the notebook depend on those root modules staying where they are.

**Ephemeral by design.** `/tmp/cdn` (the authors' R repository) is used only by the CTM
cross-check; the test skips and the notebook prints the clone command when it is missing. The
digitised figure arrays in `data/` mean the PDFs never need re-processing.

## Open research threads

Three findings that are **not** part of the replication verdict are recorded in
[`RESEARCH_NOTES.md`](RESEARCH_NOTES.md), with evidence, for later work:

1. **Returning a number is not returning a correct answer.** BDM is many-to-one on
   mechanisms — 78 rule pairs sit within a bit of each other — while the index-set calculus
   identifies all **256/256** elementary rules uniquely. And because we recover the actual
   program we can write a two-part code `D(mechanism) + C(seed) + log2(steps)`, which is a
   *certificate* rather than an estimate: **BDM exceeds it for 254 of 256 rules**, by a
   median factor of 2.8 and up to 29. On genuinely random data no certificate can be issued
   and BDM's large value is correct, so this is a statement about scope, not a refutation.
2. **The noise cliff.** The strict consistency test dies at 0.1% noise; a crude majority-vote
   variant survives to **20%**. The principled version is an MDL trade-off between mechanism
   cost and exception cost, which needs no threshold and reduces to the strict test at zero
   noise.
3. **A measure from the mechanism side.** `measure.py` prototypes one. It is exact and
   meaningful but *coarse* — only 8 distinct values over 256 elementary rules, Spearman +0.28
   against BDM. The promising direction is the pair `(mechanism cost, output complexity)`, or
   `min(BDM, two-part code)` as a strictly better estimator of `K` than either alone.

## Face to face, and the figure-by-figure parallel

Within this paper's own scope, **ten of the twelve deliverables have a genuine parallel in
the index-set calculus, and in four of those ours is stronger or solves what BDM does not** —
including Figs. 2 and 3C, the paper's two headline demonstrations. The only deliverable with
no analogue is Sup. Figs. 8-9, which measures how graded a measure is; ours is not a measure.
Full table in [`COMPARISON.md`](COMPARISON.md) and Part XIV of the notebook.

The graph side is `graph_mechanism.py`: deconvolution by *recognising* index-set laws
(complete, star, k-ary tree, cycle, path) and peeling the largest, accepted only when
detaching it costs fewer edges than it explains — the paper's own Section 3.2 inequality with
nothing fitted. On Fig. 3C, which BDM fails, this gives **precision 1.00 and recall 1.00**
and names the mechanism; on Fig. 3D it correctly reports that neither side has a law.

## Face to face

A capability-by-capability comparison of the two methods, with every row backed by a run, is
in [`COMPARISON.md`](COMPARISON.md) and Part XIII of the notebook. Summary tally across 16
capabilities: **ours 6, both 5, theirs 4, neither 1**.

The short version: BDM answers *"is there structure here, and where?"* for any object,
always, approximately, and without ever saying what the structure is. The index-set calculus
answers *"what exactly produced this?"* only where a mechanism class can be assumed, but
exactly, by name, and checkably. They are complements.

The honest limits of our side: it needs an assumed mechanism class, it produces no comparable
number, exhaustive certification costs 2ⁿ, and the strict consistency test fails at 0.1%
noise — although a one-line majority-vote variant still recovers the correct rule at 20%
noise, where BDM returns only a growing number and never a rule.

## Our own replication: the models (Part XII)

`causal_models.py` replicates the paper's results the way `imp-causal-paper/` does for the
2019 paper — by producing the **generating mechanism**, not a score.

| paper's object | what the paper returns | what the index-set calculus returns |
|---|---|---|
| Fig. 1 string | a per-bit footprint; the program in Figs. 1C–E is drawn by hand | `b[i] = NOT b[i-1]`, **inferred**, minimal, run forward to regenerate and extend the segment |
| Fig. 1 seam | a break in the signature "around" bit 50 | **bit 52** — the first observation the prior mechanism cannot account for, with a proof that bits 50–51 still can be |
| Fig. 2 / Sup. Fig. 2c | a footprint separating the halves at `delta = 0.15` | a Boolean network, one index set and gate per cell; **exact on the full 2¹² global map** in the controlled case |

`global_map_exact` is the decisive validation: the recovered network's exhaustive repertoire
over all 4096 states equals the automaton's true global map, so the mechanism was identified
rather than fitted to the eight observed trajectories. On the paper's own interacting figure
the trajectory is deliberately *not* reproduced — a deterministic network cannot reproduce a
diagram whose interaction zone came from coin tosses, and the method reports that instead of
absorbing the randomness into a bigger model.

## What is still not reproducible

* **`Compress`.** Not reproducible outside Mathematica; zlib substituted. Affects only the
  Sup. Fig. 8–9 baselines.
* **Fig. 4's subgraph sizes.** The caption gives none, and Fig. 4a is a drawn layout rather
  than a pixel grid, so it cannot be recovered the way the CA parameters were. Twelve nodes
  per block is my assumption, flagged in the notebook. It does not affect the Part VIII
  ranking results, which are reported across four independent configurations.
