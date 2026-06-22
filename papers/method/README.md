# Method Paper Track

This is the first paper track to be written after the repository reorganization.

Its focus is the formal method: deriving short exact expressions for gate-level and network-level behaviour over ordered exhaustive repertoires, then validating those expressions against deterministic experiments.

## Active Manuscript Workspace

- `papers/method/manuscript/`

## Canonical Upstream Sources

- Formal derivations and pattern documents: `papers/method/derivations/`
- Theory/process backbone: `doc/newIntPaper/docProcess.tex`
- Experimental validation backbone: `doc/newIntPaper/expProcess.tex`
- Core implementation: `src/Packages/Integration/`
- Deterministic tests: `tests/MUnit/`
- Experiment outputs: `results/`
- Shared figures: `figures/`

## What Should Not Lead This Paper

- old tickets as the primary narrative
- old phased plans as the manuscript outline
- historical Nature-facing framing unless directly needed for comparison

## Writing Rule

The method paper should be built from stable scientific content:

- definitions
- closed-form formulae
- validation experiments
- performance and invariance evidence
- distilled conclusions

Historical execution scaffolding can support the paper, but should not structure it.
