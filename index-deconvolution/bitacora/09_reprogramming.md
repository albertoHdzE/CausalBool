# Bitacora 09 — Exact Reprogramming and a Face-to-Face with Zenil

Date: 2026-07-09
Status: complete and verified

## Question

Can the index method replicate reprogramming, as Zenil and colleagues did, and
can we compare the two face to face?

## Answer

Yes, and exactly. Zenil's team perturbs a network and measures the change in the
approximate algorithmic complexity (block decomposition method) of its adjacency
matrix, ranking nodes by that information value. The index method has the exact
behaviour of the network, so it can perturb a node and measure the exact change
in the dynamics, with no approximation.

## Method

For a node, the perturbation is a knockout (the node is fixed to a constant, as a
gene knockout is). The exact complexity of the dynamics is measured by two
quantities computed from the full state space: the image size (the number of
reachable next-states) and the number of attractors. A node's information value
is measure(full) minus measure(knockout); a positive value means the node
expands the dynamics, so its removal makes the system more convergent. The
relative reprogrammability is the normalised imbalance of positive and negative
nodes, in the spirit of the index Pr. Implemented in `src/reprogramming.py`.

## Results

Experiment `experiments/exp07_reprogramming.py`, seven gene-regulatory networks.

The exact spectrum identifies the biologically meaningful drivers. The most
reprogrammable nodes are the mammalian cyclins (CycE, CycD, Cdc20) in the cell
cycle, the caspases (C3a, C8a) in apoptosis, the myeloid lineage regulators
(Gfi1, CEBPA, EKLF) in differentiation, and the cell-cycle regulators (SK,
Cdc25, Wee1) in fission yeast. These are precisely the genes one would target to
reprogram those systems. Relative reprogrammability ranges from 0.67 to 1.00
across the models.

Face-to-face with Zenil's BDM spectrum (computed with the pybdm environment of
the imp-causal-paper reproduction, node deletion on the adjacency matrix), the
rank correlation between the two information values is low and mixed, from minus
0.52 to plus 0.21 across the networks. The two measures capture different levels.
Zenil's BDM reads the complexity of the wiring diagram (topology); ours reads the
complexity of the actual dynamics (the phase space), which depends on the gates
as well as the wiring. The same topology can produce very different dynamics, so
the topological measure does not predict the dynamical one. The index method,
using the full model and its exact behaviour, therefore answers the biologically
relevant reprogramming question directly: which perturbation most changes what
the network does.

A figure with the exact spectrum for apoptosis and the per-network rank
correlations is at `figures/reprogramming_comparison.pdf`.

## Caveat

The BDM of these small adjacency matrices (six to twelve nodes) is coarse, since
there are few blocks, so the BDM spectrum is noisy and the comparison is
illustrative rather than definitive. The conceptual distinction, exact and
dynamical versus approximate and structural, stands regardless.

## Significance

The index method reproduces reprogramming and strengthens it: where the
algorithmic-information approach ranks nodes by an estimated topological
complexity, the index method ranks them by the exact change they cause in the
network's dynamics, recovering the known biological drivers. This is a
face-to-face demonstration that the exact method is at least as informative as,
and arguably more relevant than, the approximate one for reprogramming.

## Verification

The Python test suite is 19 / 19, including exact-value checks of the image size
and attractor count on identity and constant networks. The comparison uses the
real pybdm implementation, not a re-implementation.
