# Implementation-vs-Paper Results Audit

## New Section: Face-to-Face Comparison Between the Current Implementation and the Original Paper

Paper audited:

- `An Algorithmic Information Calculus for Causal Discovery and Reprogramming Systems` (Zenil et al., iScience 2019)

Implementation audited:

- `/Users/alberto/Documents/projects/CausalBool/imp-causal-paper`

Primary implementation outputs audited:

- `results/graphs/summary.json`
- `results/graphs/complete_graph_signature.csv`
- `results/ca/summary.json`
- `results/ca/row_ranking.csv`
- `results/boolean/summary.json`
- `results/boolean/xor_complete_graph_perturbations.csv`
- `plots/*/plot_manifest.json`

## Audit Standard

This comparison uses four levels of correspondence.

- `Reproduced`: the implementation matches the paper claim in object class, scale, and measured outcome.
- `Qualitative shadow`: the implementation captures the same qualitative mechanism or direction of effect, but on reduced synthetic cases or with simplified methodology.
- `Not reproduced`: the paper result is not implemented or not empirically evaluated here.
- `Mismatch / unresolved`: the implementation produces an output that does not support the exact paper claim, or uses a definition that is not yet demonstrably identical to the paper.

## Executive Verdict

The current implementation does **not** shadow every single result documented in the original paper.

What it does achieve is more limited and should be described precisely:

- it implements a subset of the paper's **core algorithmic ideas**;
- it produces **toy-scale synthetic demonstrations** for graph perturbation, MILS/MARPA-style intervention, CA row-order reconstruction, and Boolean-network perturbation;
- it does **not** reproduce the paper's full empirical program on larger graph families, exhaustive Boolean-network experiments, real-world network sparsification benchmarks, E. coli analysis, Th17 differentiation analysis, or CellNet/Waddington landscape reconstruction;
- for at least two important result families, the current outputs are not only reduced in scale but also **not faithful enough to claim numerical reproduction**.

Therefore, the scientifically accurate conclusion is:

> the implementation is a **partial, reduced, qualitative shadow** of the paper's main computational motifs, not a full reproduction of the paper's documented results.

## Face-to-Face Comparison Matrix

| Paper result family | Paper claim / target | Implementation evidence | Assessment | Scientific note |
| --- | --- | --- | --- | --- |
| Core perturbation calculus | Elements are classified by the sign and magnitude of `C(G) - C(G\\e)` using the `log2 |V(G)|` threshold | Implemented in `perturbation.py`; graph output classifies edges as positive/neutral/negative | Qualitative shadow | The thresholding rule is present, so the core perturbation language is implemented |
| CA reconstruction, Figure 3A-3C | Reconstruct row order from scrambled observations and infer temporal direction from perturbation effects | `results/ca/summary.json` reports `exact_match = true`; plot manifests explicitly state qualitative correspondence to Figure 3A-3C | Qualitative shadow | Row-order recovery is demonstrated on a very small synthetic case |
| CA generating-rule reconstruction | Paper states the calculus helps recover the generating mechanism / rule space | `results/ca/summary.json` gives true rule `254`, but inferred rule `222` | Mismatch / unresolved | Exact rule recovery is **not** reproduced in the present run, even though the row order is recovered |
| CA scale and robustness, Figure 3D-3H | 200- and 280-step ECA examples, random-looking rules 30/73/45, single- and double-row perturbations, improvement with more observations | Current implementation restricts brute-force reconstruction to `<= 8` observations and uses one short rule-254 example | Not reproduced | The large-scale and more difficult CA reconstructions from the paper are absent |
| Graph interventions, Figure 4A | Starting from `K10`, deleting negative edges pushes the graph away from randomness in the theoretically expected manner | Current graph experiment uses `K6`, not `K10`; output shows 9 neutral edges and 6 negative edges | Qualitative shadow, with tension | The mechanism is gestured at, but the exact `K10` result and trajectory are not reproduced |
| Complete-graph natural reprogrammability | Supplement says complete graphs have analytically near-uniform signatures; all nodes are neutral/slightly positive and single edges are individually negative in the theoretical discussion | `results/graphs/complete_graph_signature.csv` is highly non-uniform: 9 edges are exactly neutral and 6 are strongly negative | Mismatch / unresolved | This output does not cleanly support the paper's idealized complete-graph behavior |
| Graph interventions, Figure 4B | Moving a network toward randomness yields ER-like behavior approaching density `0.5` | No ER-density trajectory is generated or measured | Not reproduced | There is no direct numerical demonstration of the ER target regime |
| Graph interventions, Figure 4C | Perturbing a random graph toward simplicity reveals latent structure | No random input graph and no simplification trajectory are evaluated | Not reproduced | This panel is absent |
| MARPA | Build graphs by greedily increasing algorithmic randomness toward MAR/ER-like objects | `marpa.py` implements a greedy edge-addition heuristic; output is a 6-node, 7-edge graph | Qualitative shadow | The reverse-construction idea is implemented at toy scale, but there is no validation that the output approximates the paper's MAR target beyond the local heuristic |
| Reprogrammability indices | Paper defines relative, absolute, and combined programmability using supplementary formulas | `results/graphs/summary.json` reports `relative = 0.0`, `absolute = 1.0`, `combined = 1.0` | Mismatch / unresolved | The implementation uses a simplified operationalization; equivalence to the supplementary definitions is not yet verified |
| MILS algorithm | Remove neutral elements to minimize information loss | `mils.py` removes the least informative singleton edge greedily; graph output removes 5 edges from `K6` | Qualitative shadow | The basic idea is present |
| MILS determinism under ties | Supplement states deterministic MILS should remove *sets* of equal-information elements simultaneously to avoid non-linear order effects | `mils.py` breaks ties lexicographically on single edges, not by simultaneous equal-information-set removal | Mismatch / unresolved | The implemented MILS is not fully faithful to the supplementary deterministic prescription |
| MILS empirical validation | Real-world and gold-standard network benchmarks; preservation of information signature, edge betweenness, clustering, degree distribution; comparison with transitive and spectral sparsification | No such benchmark suite exists in the implementation | Not reproduced | This is one of the paper's major validation blocks and is currently missing |
| Boolean-network exhaustive small-graph experiment, Figure 4D | Distribution of attractor counts for all possible 5-node Boolean networks under AND/OR/XOR | Current implementation studies only one complete 4-node graph with XOR | Not reproduced | The exhaustive `n = 5` experiment is absent |
| Boolean-network topology comparison, Figure 4E | Compare complete, ER, and scale-free Boolean networks under perturbation | Current implementation uses only a complete graph | Not reproduced | No ER or scale-free cases are evaluated |
| Larger Boolean-network validations, Figure 4F-4G | Larger random and scale-free graphs show consistent perturbation trends for negative vs positive vs neutral elements | Not implemented | Not reproduced | No large-graph Boolean validation is present |
| Boolean perturbation directionality | Paper uses simply directed or randomly directed networks with AND/OR/XOR node rules | Current code converts an undirected complete graph to fully bidirected form and uses XOR only in the reported experiment | Qualitative shadow | This is a much narrower dynamical regime than the paper |
| Exhaustive connected 5-node graph perturbation experiments | Supplement reports exhaustive small-graph analyses, orbit handling, and automorphism correction | No exhaustive connected-graph census or automorphism correction is implemented | Not reproduced | This matters because the paper explicitly controlled BDM boundary artifacts in that regime |
| E. coli network analysis, Figure 5A/E/H | Negative genes relate to specialization, positive genes to homeostasis, clustering/enrichment/reconstruction on validated TF network | No biological network ingestion or enrichment analysis exists in the implementation | Not reproduced | None of the E. coli claims are currently tested |
| Th17 differentiation, Figure 5B-5F | Time-resolved spectra and reprogrammability changes during Th17 differentiation, including enrichment analysis | No Th17 data or enrichment pipeline exists | Not reproduced | None of these results are currently present |
| CellNet / Waddington landscape, Figure 5G-5H | Map 16 human cell types in complexity-programmability space, reconstruct epigenetic landscape | No CellNet acquisition or landscape reconstruction exists | Not reproduced | None of the developmental landscape results are implemented |
| End-to-end execution and testing | The implementation should run as a self-contained project | `run.sh`, the isolated `.venv`, and tests succeed | Reproduced | This validates local software operability, not paper-level empirical completeness |

## Detailed Scientific Comparison

### 1. Cellular Automata

The strongest result of the current implementation is the row-order reconstruction of a small synthetic elementary cellular automaton trajectory.

Observed implementation outputs:

- `results/ca/summary.json` reports `exact_match = true`
- the generating rule used to synthesize the data is `254`
- the best-fitting inferred rule reported by the implementation is `222`
- `transition_matches = 5`, meaning all five adjacent row transitions in the recovered ordering are consistent with the inferred rule on the observed finite window

Interpretation:

- the implementation **does** show that perturbation-guided ordering of scrambled observations can recover the original row order in a toy case;
- the implementation **does not** yet reproduce the paper's stronger claim that the generating mechanism itself is recovered in a faithful way on the tested instance, because the inferred rule is not the true generating rule;
- the implementation also omits the paper's difficult cases: long trajectories, random-looking ECA rules, and the explicit scaling from single-row to double-row perturbations.

Scientific verdict for the CA block:

- `row-order recovery`: qualitatively shadowed
- `rule recovery`: not yet reproduced
- `published scale and breadth`: not reproduced

### 2. Graph Perturbation, Reprogrammability, and MARPA

The graph block captures the direction of the paper's interventionist philosophy but does not yet reproduce the paper's stronger numerical claims.

Observed implementation outputs:

- `results/graphs/summary.json` reports
  - `relative_reprogrammability = 0.0`
  - `absolute_reprogrammability = 1.0`
  - `combined_reprogrammability = 1.0`
- `results/graphs/complete_graph_signature.csv` shows:
  - 9 neutral edges with `delta = 0`
  - 6 negative edges with deltas between about `-3.21` and `-8.91`

Scientific tension with the paper:

- in the supplementary definitions, complete graphs are treated as analytically simple objects with near-uniform natural signatures;
- the implementation's `K6` signature is instead highly uneven;
- this may reflect BDM finite-size/boundary artifacts, the smaller graph size, a difference between node and edge perturbations, or an implementation-level definition gap, but it means one cannot honestly claim exact reproduction of the complete-graph analytical behavior described in the paper.

MARPA assessment:

- the paper's MARPA discussion is about approximating maximally algorithmic-random graphs by globally choosing edge additions that maximize complexity;
- the implementation uses a local greedy search and does not compare the resulting graphs against ER or MAR baselines;
- thus the implementation shadows the algorithmic idea but not the paper's full empirical validation.

### 3. MILS

The implementation contains a usable toy MILS reducer, but it is not yet a faithful reproduction of the paper's full validation story.

What is implemented:

- greedy singleton removal of the least informative edge;
- optional exact subset search for very small graphs.

What the paper requires beyond that:

- deterministic treatment of ties through simultaneous removal of equal-information sets;
- preservation analysis of the information signature;
- preservation of graph-theoretic properties;
- head-to-head comparison against transitive and spectral sparsification;
- evaluation on real-world and benchmark networks.

Therefore:

- the implementation captures the core intuition of MILS;
- it does **not** reproduce the paper's benchmark-level MILS evidence.

### 4. Boolean Networks

Observed implementation outputs:

- `results/boolean/summary.json` reports `attractor_count = 12` for a 4-node complete graph with XOR updates;
- every single directed-edge deletion reduces the attractor count from `12` to `4`, giving `delta_attractors = -8` uniformly across all 12 directed edges.

Interpretation:

- this is a valid deterministic Boolean-network perturbation experiment;
- however, the paper's Boolean-network section is much broader:
  - exhaustive `n = 5` experiments,
  - AND/OR/XOR rules,
  - complete, ER, and scale-free topologies,
  - larger-graph validations,
  - comparison of positive, negative, neutral, and control perturbations.

Thus the current Boolean results are best described as:

- a **single reduced example** illustrating the existence of a perturbation-attractor relation,
- not a reproduction of the paper's Boolean-network empirical program.

### 5. Biological Results

The biological part of the paper is currently absent from the implementation.

Missing result families:

- E. coli transcription-factor network perturbation analysis
- positive/homeostasis vs negative/specialization interpretation
- GO / KEGG / EcoCyc enrichment analysis
- Th17 temporal differentiation spectra and reprogrammability trends
- CellNet complexity-programmability mapping
- reconstructed Waddington-like landscape

Because none of the required data acquisition, curation, enrichment, or plotting pipelines are present, **none** of the biological conclusions in Figure 5 are reproduced.

## Methodological Gaps That Matter Scientifically

These are not cosmetic gaps. They change what can be claimed about reproduction fidelity.

### A. Reprogrammability Formula Fidelity Is Not Yet Proven

The supplementary material defines:

- relative programmability using `MAD(sigma(G)) / n`, with `n = max(|sigma(G)|)`
- absolute programmability via an interpolation-based comparison of positive and negative signature parts

The current implementation uses a simplified operationalization:

- relative programmability is normalized by `max(values)`, not explicitly by `max(abs(values))`
- absolute programmability uses trapezoidal areas of sorted positive and negative magnitudes

This may be a reasonable approximation, but it is not yet demonstrated to be mathematically identical to the paper's definitions. Consequently, exact claims about the reprogrammability values themselves should be withheld.

### B. MILS Tie Handling Differs from the Supplement

The supplement explicitly emphasizes simultaneous removal of equal-information sets to preserve determinism under non-linear interactions. The current implementation removes one lexicographically chosen edge at a time under ties. This is operationally useful, but not yet faithful to the stated deterministic version of MILS.

### C. Small-Scale Toy Demonstrations Cannot Substitute for the Paper's Validation Regime

The paper's empirical credibility comes from breadth:

- many graph classes,
- exhaustive small-network cases,
- larger-network simulations,
- real biological networks,
- enrichment and landscape analysis.

The current implementation demonstrates only a narrow synthetic subset of this regime. That is sufficient to validate basic software operability and the presence of the main concepts, but insufficient to claim full result shadowing.

## Final Verdict

Answer to the core question:

> Does the current implementation shadow every single result documented in the original paper?

No.

Scientifically accurate final assessment:

- `Core concepts implemented`: yes
- `Toy synthetic demonstrations produced`: yes
- `Main paper figure families qualitatively echoed`: partially
- `Exact or near-exact reproduction of all reported numerical results`: no
- `Biological validation reproduced`: no
- `Benchmark and supplementary validation reproduced`: no

The implementation should therefore be described as:

> a **partial, scientifically useful, reduced implementation** of the paper's algorithmic framework, with several successful toy demonstrations, but **not** a full reproduction of the original paper's results.

## Most Important Missing Pieces for Fuller Reproduction

1. Larger CA experiments reproducing the published long-horizon ECA cases and multi-row perturbation analyses.
2. Exact supplementary reprogrammability formulas and validation against known graph classes.
3. Graph intervention experiments that explicitly reproduce the `K10`, ER-density, and random-to-structure trajectories.
4. Exhaustive 5-node Boolean-network experiments over AND/OR/XOR and multiple topologies.
5. Real-world MILS benchmarks, including comparison against transitive and spectral sparsification.
6. E. coli, Th17, and CellNet data pipelines with documented preprocessing and enrichment analysis.

