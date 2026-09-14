# Response to Doppel: first manuscript

Author: Alberto Hernandez-Espinosa. Draft date: 13 September 2026.

The submission response occupies six pages including references. It presents
the solution, proof and boundary cases first, then one ten-node generator and
its admissible payoff frontier. Complexity receives one short secondary
discussion. The supplementary material starts on a new page after the
references and preserves the expanded explanations, experimental context,
encoding, executable listings, colour plot and full BDM comparisons.
The complete response and supplement are built together as `main.pdf`, so
cross-references remain clickable. The verifier records the main-response
page count from the LaTeX supplement marker.

The final editorial pass standardises phrases, category features, message
types and outcomes throughout the response. It consolidates the scope
statement in the network introduction and distinguishes the analytical
solution, constrained experiment and secondary description-length analysis.
The numerical evidence, examples and cycle explanation are retained.
The submission candidate is identified by the manuscript and PDF hashes
recorded in verification.json.

Editorial decisions:

- The company is Doppel, verified at https://www.3blue1brown.com/talent/doppel/.
  The setup is an attributed paraphrase. The full externally sourced
  challenge is not reproduced.
- Each main-text expression has an operational explanation: frequency weights,
  normalisation, the payoff ceiling, boundary budgets, cycle probabilities and
  selection from the perturbation catalogue. Numerical examples distinguish
  hypothetical phrase payoffs from results of the saved network experiment.
- A state may represent one complete combination of message features. The
  distribution over states is joint across features; an individual output is
  one combination. The long-run distribution differs in general from the
  one-step output distribution, and recurrence does not imply recipient success.
- The main setup distinguishes literal phrases, category features and complete
  message types. Boolean gates provide an abstract model of logical composition;
  description length measures the encoded generating rules, not grammatical
  quality or intelligence. Cycle weights average over initial states and phases,
  whereas a single trajectory eventually remains on its own cycle.
- The network construction preserves the meanings of the distributions, payoff
  and KL rule, but restricts the available distributions. It is not an equivalence
  between the whole probability simplex and one-edge network perturbations.
- The compiler belongs to the index-deconvolution framework; this experiment
  uses forward symbolic compilation. It does not infer an unknown network.
- A shared reduced ordered decision graph, with an ordered reference per output,
  is the executable representation. Exported decimal/Sumandos schemata explain
  its meaning, but are not an intermediate list that production must enumerate.
- No general linear-time inference or measured speed-up claim is made. Dense
  adjacency reading, compilation, individual queries and exhaustive output have
  different costs. All original validation and BDM required complete small tables.
- The Kolmogorov upper bound includes a fixed interpreter constant and is
  conditional on N and ordering conventions. The constant is not measured.
- The first release, replication, pilots and worked example have distinct roles.
  The worked example is the existing ring_n10_s1000 baseline, selected by name
  for exposition, not by compression ratio or attack success.
- Saved relaxation values are numerical upper bounds, not certified equality
  with the exact unrestricted optimum. No feasible perturbation remains missing
  rather than being assigned a score of zero.
- British English, no contractions, question-led explanatory figure captions.
- Causal description length (causal complexity under the declared encoding)
  is the executable network programme length, not a shortest-programme claim.
  A common conditional upper bound for rows is distinguished from the
  complexity of each output string.
- Equal programme lengths can accompany different payoffs. The reported
  correlations concern base-mean changes and total variation, not individual
  detection under forward KL. They establish neither independence nor a
  demonstrated improvement in attack selection or detection.
- Exact reconstruction establishes the usefulness of the executable
  representation separately from the usefulness of its scalar bit count.
  Compression against the raw table is not a comparison with other compact
  encodings of the known connections and rules.
- Cycles are part of the declared long-run observation model. The diagram
  follows actual transitions, rather than displaying sorted attractor members
  as if that sorting were temporal order.
- The explanatory extension adds one-dimensional row BDM for the ten-node
  example: one complete ten-bit block, no padding or ignored bits. It remains
  separate from the released matrix BDM results.
- Complexity/payoff plots use all 74 existing edge additions. The 29 finite-KL
  changes are plotted; the 45 infinite-KL cases remain explicit in the CSV.
  Complexity is shown as colour and, in an appendix, as a third coordinate;
  it does not change the detector or the optimisation objective.

Reproduce from the repository root:

```sh
PYTHONPATH=doppel-challenge/src python doppel-challenge/paper/response_v1/build_evidence.py
latexmk -pdf -interaction=nonstopmode -halt-on-error -cd doppel-challenge/paper/response_v1/main.tex
PYTHONPATH=doppel-challenge/src python doppel-challenge/paper/response_v1/verify_draft.py
```

`build_evidence.py` verifies input release hashes, checks the ten-node programme
at every output bit, rebuilds it from exported schemata, checks every schema
position, derives tables from existing records and generates vector PDF figures.
It writes only beneath this manuscript directory. No network study is launched.
`evidence.json` records inputs, checks, numbers and generated artifact hashes.
`verification.json` records execution of the printed Python examples, a check
of the analytical solution against an independent constrained optimiser,
boundary cases, agreement of printed result blocks with actual execution,
explanatory counts, manuscript style checks and the final PDF hash.

The explanatory_evidence.py module adds verified cycle/basin illustrations,
a decimal/Sumandos subpattern example, row BDM measurements, and recomputed
payoff/KL/complexity plots from sealed records. It does not launch a new
network sample or alter the released study.

Two current notebooks differ from the earlier release source hashes. Notebook
01 has stray text in an exception handler; notebook 02 has identical cell
sources to its archived executed snapshot but differs as a complete file.
The build records both differences and uses the intact, hash-verified executed
snapshots as historical evidence. These current files are not edited here.
All other declared release sources must still match; a mismatch stops the build.

The earlier `../main.tex` is a historical N=6 report. `main.tex` in this directory
is the new challenge response. Submission and external publication are separate
from preparing this local draft.
