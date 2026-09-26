# Luminal paper draft

[Read the PDF](main.pdf) · [Edit the manuscript](main.tex) ·
[Build validation](BUILD_VALIDATION.json) · [Claims contract](CLAIMS_AND_EVIDENCE.md) ·
[21 September baseline](baselines/20260921/BASELINE_MANIFEST.json)

**Direct Boolean Index Schemata for Scheduling and Scratch Allocation: A
Reproducible Luminal Compiler Case Study**, revised 23 September 2026.

The draft includes the machine and score definition, cube algebra with proofs,
bootstrap existence arguments, bounded joint constraints and pseudocode,
measurement design, output quality, compilation time and memory, negative
results, primary-source related work, and a concrete scope for a later
complexity study. Six generated figure pairs and a vector method diagram use
the earlier manuscripts' teal/orange palette.

Shannon decomposition is identified as the mathematical partition underlying
Boolean splitting. Shannon communication limits and Wolfram's memory-retrieval
discussion are contextual connections, not implemented channel or memory models.
The counting and parity arguments make the representation limits explicit.

The evidence supports a 5.6321% public **composite-score** advantage over the
frozen classical implementation, with substantially slower compilation. It
does not isolate representation from heuristic choice. Joint optimization
improves six of 100 generated inputs and none of the eight public programs.
Both the final lead speedup and earlier misses are retained.

## Build from existing evidence

From the repository root, using the existing Python environment:

```sh
venv/bin/python luminal-challenge/paper/build_paper.py
```

An alternative interpreter needs Matplotlib and NumPy. A TeX installation with
`latexmk` and pdfLaTeX is also required. The script works from any current
directory, regenerates the figures and tables, builds `main.pdf`, rejects
unresolved LaTeX references and overfull boxes, and records commands, exit codes
and SHA256 hashes in `BUILD_VALIDATION.json`. Build logs and previews live in
the ignored `build/` directory. Plotting uses writable temporary font caches.
No network or new timing experiment is required for a rebuild.

## Evidence and reproducibility

The primary source is the [final lead review](../results/direct_index_v4_optimization_repair2/REVIEW.md)
at commit `1cf98daf403619535e5d5b53da91d9b9d93198be` and its
[raw timing rows](../results/direct_index_v4_optimization_repair2/lead_review/final/runs.json).
Source/export hashes, protected controls, exact timing membership, public and
generated scores, and headline speedups are checked during figure generation.
[Input provenance](generated/input_manifest.json) identifies the files used.
[Derived metrics](generated/metrics.json) retain values before rounding.

The retained full evidence checker was rerun on 21 September: **50 checks
passed**. Its result is copied to [EVIDENCE_VALIDATION.json](EVIDENCE_VALIDATION.json).
The 340 direct tests, 11 public tests, 142 acceptance programs / 277 cases,
72 official comparison measurements and 2,100 timing rows reported in the
manuscript are the accepted September 20 evidence, not newly measured results
from the writing session.

To re-audit the retained measurements with a separate output, run from
`luminal-challenge`:

```sh
python3 check_optimization_evidence.py \
  --root results/direct_index_v4_optimization_repair2/lead_review \
  --baseline results/direct_index_v4_optimization/baseline \
  --output paper/EVIDENCE_VALIDATION.json
```

To run new experiments, use the final review's commands with **new output
directories**. Preserve historical runs. Source changes require the affected
compiler verification before updating the manuscript's results.

## Phase 2 feasibility evidence

The separate 23 September campaign is reported in the manuscript's structural-
encoding feasibility section. The generator reads the accepted run at
`../results/phase2_structural_encoding/phase2_repair_20260923c/`, records source
SHA256 digests, verifies raw-file SHA256 values against the P1 summary, and derives `generated/phase2_coverage_rows.tex` and
`generated/phase2_metrics.json`. It does not rerun the campaign. P1 is
INCONCLUSIVE under the declared 100-distinct-completions-per-program gate; P2-P5
remain blocked and unmeasured. The evidence record keeps
`artifacts_complete=false` and `scientific_success=false` explicit.

The 113 MB raw-attempt file remains local because storage packaging is
unresolved. The Phase 2 evidence is not portable, published or fully archived.
It is dated separately from the accepted production measurements and September
20 production tests; the two campaigns are not pooled.

## Review status

This completes the requested **internal draft**, not publication peer review.
The production implementation's local acceptance remains separate. Mathematical
arguments have been checked against their stated assumptions and the relevant
implementation; no machine-checked proof of the complete compiler is claimed.
The PDF was inspected visually after compilation. Bibliography/source notes
are in [SOURCES.md](SOURCES.md).

The challenge reference requests that the exercise and solution not be shared
publicly. This deliverable stays local; any future public release needs that
restriction resolved as well as independent manuscript review.
