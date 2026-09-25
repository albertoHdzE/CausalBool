# self-improving — charter

## The goal

A **local, quantised, small language model**, embedded in a self-improving
system, must **rediscover index-set deconvolution by itself**. It receives no
clues, no description of the method, and none of our code, terminology or
examples. It must evolve to that degree. The result is to be published.

Everything else in this folder serves that goal. Stage A (the capability
repertoire) and Stage C (solution families, perturbation and fusion) are
deliberately easier. They exist to prove that the machinery is correct:
- the task generator;
- the exact verifiers;
- schema-directed variation;
- the archive;
- the controls.

They are proved on problems whose answers we can check completely, before the
same machinery is pointed at the real target. **Stage D is the goal.** Its
protocol is still to be written, and this charter fixes what it must contain.

This is the positive side of the argument in Zenil, Uthamacumaran and Ozelim
[1]: a purely statistical model does not synthesise mechanisms, but a model
inside a symbolic selection loop might. If a small quantised model plus exact
selection rediscovers a symbolic inference method, that is direct evidence for
neurosymbolic model synthesis. If it cannot, the ladder below says exactly how
far it got.

---

## 1. What "rediscover" means operationally

**The environment.** The system is given a hidden generator of synchronous
Boolean networks. Its task is to write a program that takes a network's
observable behaviour and returns the network:
- each node's inputs;
- each node's function.

**Fitness, in lexicographic order:**
1. exact functional recovery on hidden networks;
2. then the length of the returned description;
3. then the running time and query cost at growing n.

Nothing in the prompt, the fitness or the feedback names essential variables,
index sets, schemata, offsets, sumandos or gates.

**Access tiers.** Each tier removes a shortcut, so each is a harder environment.

| Tier | What the program receives | What it forces |
|---|---|---|
| T0 | the full state-transition table, small n (at most 10) | nothing beyond textbook methods: this is the **easy technical-correctness case** |
| T1 | the full table, larger n (at most 20), under a time limit | efficiency: no search over candidate wirings |
| T2 | **oracle access only**: query the next state of chosen states, under a query budget | inference from perturbation: flipping one coordinate at a time to find what a node depends on |
| T3 | as T2, and fitness rewards the **shortest description** of each node's on-set | a compressed representation of the behaviour, not a lookup table |
| T4 | as T3, at n far beyond enumeration (the Doppel reach was n = 151) | a structured symbolic representation: decision diagrams or an equivalent |

**The rediscovery ladder.** Every evolved program is audited for which rungs
it implements. The audit is behavioural, by parity with the owner on a hidden
corpus, and structural, by author inspection of the lineage.

| Rung | Content | Our owner |
|---|---|---|
| M1 | dependence detected by single-coordinate flips | `essential_variables` |
| M2 | restriction to the dependent coordinates | `reduce_column` |
| M3 | naming the reduced function in a catalogue, or schema clauses | `identify_gate`, `minimal_dnf` |
| M4 | verification by forward reproduction of the whole repertoire | `verify_forward` |
| M5 | exactness without enumeration, at T4 scale | symbolic path over `repertoire_program.py` |
| M6 | **the distinctive object**: each on-set written as a base set plus an offset family, (L, Ω), and total reproduction from it | `CausalBoolCore.wl`, the formal paper |

M1–M4 are close to textbook material (sensitivity analysis, Quine–McCluskey)
and are expected to be reachable. **M5 and M6 are the claim.** A run that stops
at M4 is reported as such, not as rediscovery.

---

## 2. The information firewall: "no clues" made checkable

- **What the system sees:** the environment's interface description (input and
  output formats, query budget), its own fitness scores, the lineage of its own
  programs, and its own archive. Nothing else.
- **What it never sees:** anything under `src/`, `index-deconvolution/`,
  `doppel-challenge/` or `papers/`; our vocabulary; any worked example of the
  method.
- **Physical separation:** the evaluator runs in a separate process. The
  evolving programs run in a sandbox without file-system access to the
  repository. Ground truth comes from the generator's known network, so the
  evaluator does not even need our deconvolution code.
- **Contamination audit, before any run.** Our method is public: the 2019
  preprint arXiv:1904.10393, and the challenge papers on the website since
  September 2026.
  - The model is chosen with a release date before the latter where possible.
  - Canary probes then ask it directly about the method, its terms and the
    preprint, and the answers are recorded.
  - Contamination cannot be excluded completely. The defence is the
    **lineage**: a rediscovery must appear as a traceable sequence of archived
    improvements, rung by rung, not as a single generation. Following
    LLM-SRBench [2], which showed that memorisation inflates scores in
    rediscovery benchmarks, a **zero-shot probe** (the same model, the same
    task, no loop, at the full call budget) is always reported next to the
    loop.

---

## 3. What "self-improving" means here

| Level | What evolves | Precedent |
|---|---|---|
| L1 | programs: a population plus a schema archive, with computed variation (Stage C machinery) | FunSearch [3], AlphaEvolve [4] |
| L2 | the improver itself: mutation and fusion prompts and operator choice, scored by how fast the lineage improves | STOP [5], Darwin Gödel Machine [6] |
| L3 (later, optional) | the weights: fine-tuning on the system's own successful lineage | outside Stage D unless amended |

The weights are frozen at L1 and L2, as in [5]. Any claim of self-improvement
names its level.

---

## 4. Nulls that Stage D must carry

- **Independent sampling at an equal number of calls, with set-level
  selection.** Li [7] reports that on LLM-SRBench, LLM evolution does not beat
  independent sampling at an equal budget, and that selecting over pooled terms
  wins with a tenth of the calls. Stage D's loop must beat this, or report that
  it does not.
- **Random-program search** in the same language subset, at the same number
  of evaluations.
- **The zero-shot probe** of §2.
- **LLM-driven mutation without computed variation.** This tests the collapse
  onto revisited structures reported in [8].

---

## 5. Models and compute

- **Models:** local and quantised (MLX, 4-bit), on the M3 Ultra (96 GB).
  Candidate families are small coder models. The family, size, quantisation and
  revision hash are fixed at the Stage D freeze.
- **Constraints:** no cloud model at any point of the loop. Throughput is
  measured in the Stage A smoke run; nothing is estimated here.

---

## 6. Folder map

| File | Role | Status |
|---|---|---|
| `PROTOCOL_capability_repertoire.md` | Stage A/B: can the model answer; capability boundary as a Boolean function | draft |
| `PROTOCOL_stage_C_solution_families.md` | Stage C: plan genotypes, schema-directed mutation, fusion as crossover, basins | draft |
| Stage D protocol | the rediscovery of §1–§4 | to be written |
| `paper/` | Zenil, Uthamacumaran and Ozelim [1] | reference |

The tickets T1–T3 (listed in the Stage C protocol) are prerequisites for Stage
D as well. The evaluator's scoring of M1–M6 relies on the same owners, and
Stage D's own verifier reuses Stage C's.

---

## References

1. Zenil, H., Uthamacumaran, A. and Ozelim, L. (2026). Large Language Models As Shannon Lossy Compressors Not Solomonoff Induction Estimators: The Singularity Is Not Near Without Symbolic Model Synthesis. arXiv:2601.05280v5.
2. Shojaee, P., Nguyen, N.-H., Meidani, K., Barati Farimani, A., Doan, K. D. and Reddy, C. K. (2025). LLM-SRBench: A New Benchmark for Scientific Equation Discovery with Large Language Models. *ICML 2025* (oral). arXiv:2504.10415.
3. Romera-Paredes, B. et al. (2024). Mathematical discoveries from program search with large language models. *Nature* 625(7995), 468–475. doi:10.1038/s41586-023-06924-6.
4. Novikov, A. et al. (2025). AlphaEvolve: A coding agent for scientific and algorithmic discovery. arXiv:2506.13131.
5. Zelikman, E., Lorch, E., Mackey, L. and Kalai, A. T. (2023). Self-Taught Optimizer (STOP): Recursively Self-Improving Code Generation. arXiv:2310.02304.
6. Zhang, J., Hu, S., Lu, C., Lange, R. and Clune, J. (2025). Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents. arXiv:2505.22954.
7. Li, P. (2026). Dictionaries, Not Darwin: Set-Level Selection Beats LLM Evolution in Scientific Equation Discovery. arXiv:2607.04108.
8. Gurkan, C., Stonedahl, F. and Wilensky, U. (2026). Mutation Without Variation: Convergence Dynamics in LLM-Driven Program Evolution. arXiv:2606.05408.
9. Cornelio, C., Dash, S., Austel, V., Josephson, T. R., Goncalves, J., Clarkson, K. L., Megiddo, N., El Khadir, B. and Horesh, L. (2023). Combining data and theory for derivable scientific discovery with AI-Descartes. *Nature Communications* 14, 1777. doi:10.1038/s41467-023-37236-y.
10. Udrescu, S.-M. and Tegmark, M. (2020). AI Feynman: A physics-inspired method for symbolic regression. *Science Advances* 6(16), eaay2631.
11. Yoran, O., Zheng, K., Gloeckle, F., Gehring, J., Synnaeve, G. and Cohen, T. (2025). The KoLMogorov Test: Compression by Code Generation. *ICLR 2025*. arXiv:2503.13992.
