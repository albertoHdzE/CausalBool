# Tooling and Kernel Configuration

## Kernel Path (macOS)
- Preferred: `/Applications/Wolfram.app/Contents/MacOS/WolframKernel`
- Alternatives: `/Applications/Mathematica.app/Contents/MacOS/WolframKernel`, `/Applications/WolframKernel.app/Contents/MacOS/WolframKernel`
- Optional environment variable: `WOLFRAM_KERNEL` pointing to the chosen kernel

## Console Execution
- Run tests: `"/Applications/Wolfram.app/Contents/MacOS/WolframKernel" -noprompt < tests/MUnit/Arch/TSK-ARCH-001-Tests.m`
- Exported artefacts appear under `results/` and figures under `figures/`

## Workbench and Framework
- Use Wolfram Workbench plugin with MUnit notebooks
- Configure deterministic execution

## Determinism Settings
- Set seeds in notebooks and scripts
- Record parameters and metadata in outputs

## Reproducibility
- Provide one‑click acceptance notebooks
- Record checksums for artefacts