# CausalBool Method Paper — Companion Code

Computational companion for:

> **An Index-Set Calculus for Boolean Causal Networks**
> [Author · Institution · Year]
> [arXiv / DOI — to be added upon acceptance]

This repository contains the three reproducible experiments that underpin the
paper's corroboration claims. Every numerical result in the paper is regenerated
exactly from closed-form index-set formulae with no probabilistic assumptions.

---

## Repository Structure

    .
    ├── lib/
    │   └── CausalBoolCore.wl            Standalone gate dispatch; no external packages
    ├── corroboration_6node/
    │   ├── corroboration_6node.wl        Closed-form one-sets verified against exhaustive
    │   │                                  baseline for AND (node 5) and XOR (node 6)
    │   ├── ordering_invariance_6node.wl  Phi-transport check under MSB enumeration
    │   └── ordering_invariance_6node.py  Python replica (no Wolfram required)
    ├── mixed_interaction_10node/
    │   ├── mixed_interaction_10node.wl   All-gate network: index algebra for 6 query patterns
    │   ├── dynamical_landscape_10node.wl  Attractor structure and dynamical enrichment
    │   └── dynamical_landscape_10node.py  Python replica (no Wolfram required)
    ├── scalability_resource_envelope/
    │   └── scalability_resource_envelope.py  Resource benchmark n = 30, 60, 80, 200
    └── run_all.sh                        Runs all experiments in order

---

## Prerequisites

| Component | Requirement |
|-----------|-------------|
| Mathematica scripts (`.wl`) | Wolfram Mathematica 12+ **or** free [Wolfram Engine 13+](https://www.wolfram.com/engine/) |
| Python scripts (`.py`) | Python 3.8+, standard library only — no `pip install` required |

The `lib/CausalBoolCore.wl` library is fully self-contained (no external Wolfram
packages). Simply clone and run.

---

## Running

### All experiments

```bash
bash run_all.sh
```

Override the Wolfram executable if needed:

```bash
WOLFRAM=/Applications/Wolfram.app/Contents/MacOS/WolframKernel bash run_all.sh
WOLFRAM=wolframscript bash run_all.sh
```

### Individual experiments

```bash
# ── Experiment 1: 6-node corroboration ──────────────────────────────────────
wolframscript -file corroboration_6node/corroboration_6node.wl
wolframscript -file corroboration_6node/ordering_invariance_6node.wl
python3 corroboration_6node/ordering_invariance_6node.py

# ── Experiment 2: 10-node mixed interaction ──────────────────────────────────
wolframscript -file mixed_interaction_10node/mixed_interaction_10node.wl
wolframscript -file mixed_interaction_10node/dynamical_landscape_10node.wl
python3 mixed_interaction_10node/dynamical_landscape_10node.py

# ── Experiment 3: Scalability resource envelope ──────────────────────────────
python3 scalability_resource_envelope/scalability_resource_envelope.py
```

---

## Expected Outputs

All scripts exit with code 0. Key verification flags:

| Script | Verified flag(s) |
|--------|-----------------|
| `corroboration_6node.wl` | `verified061Q = True`, `verified062Q = True` |
| `ordering_invariance_6node.wl` | `verifiedAnd06Q = True`, `verifiedXor06Q = True`, `verifiedPhiInvolution06Q = True` |
| `ordering_invariance_6node.py` | `verified_and = True`, `verified_xor = True`, `verified_phi_involution = True` |
| `mixed_interaction_10node.wl` | All 10 node one-sets match exhaustive baseline; all 6 query patterns verified |
| `dynamical_landscape_10node.wl` | 4 attractors, `|Im(F)| = 206`, basin sizes 488 / 320 / 204 / 12 |
| `dynamical_landscape_10node.py` | Same dynamical summary as `.wl` counterpart |
| `scalability_resource_envelope.py` | Median `|C_q| = 10` for T3 (8-node query) across n = 30, 60, 80, 200; all runs sub-millisecond |

Pre-computed outputs (`.json`, `.csv`, `.tex`) are included in each subdirectory and
correspond exactly to the tables and figures in the paper.

---

## Licence

MIT — see `LICENSE` file (to be added upon submission).
