# Nature Readiness Assessment (Protocol 8)

**Document ID:** LEV8-NATURE-READINESS-2026-04-06  
**Date:** 2026-04-06  
**Scope:** Holistic assessment of readiness to submit to *Nature* and a protocol-8-aligned gap list.

## Current candidate central claim (submission-safe wording)
- Curated executable gene-regulatory wiring diagrams are more compressible than randomized null ensembles that preserve coarse constraints (degree sequence; density; and gate labels where available), under a frozen adjacency encoding and a checksum-locked analysis pipeline.

## What is already Nature-grade (protocol-8 compliant)
- **Gate A (coherence + reproducibility):** Strong.
  - Proxy boundary is explicit (gzip-based corpus estimator vs UniversalDv2Encoder proxy for ΔD/corruption).
  - Deterministic artifact lock is implemented and verified (`paper/figures/repro_lock_manifest.json`).
  - One-command reproduction workflow exists (`paper/code/reproduce_all.py`).
- **Gate B (universality defense vs bias):** Moderate-to-strong.
  - Multiple null families implemented (ER, degree-preserved, gate-permuted subset).
  - Bias-defense grid and leave-one-source-out sensitivity exist (`paper/figures/bias_defense_*`).
  - Independent cohort pipeline exists (SBML-qual Cell Collective); cohort is small but methodologically clean.
  - Matched “human-designed vs evolved” control exists and is locked (`paper/figures/human_vs_evolved_*`).

## What is not yet Nature-grade (protocol-8 gaps)
- **Gate C (external validation / biological anchoring):** Not yet strong enough for a “killer” claim.
  - **KR-A essentiality:** current network-held-out performance is weak; this cannot carry a main Nature Results claim without rethinking endpoints, annotations, and leakage-safe design.
  - **DepMap anchoring:** power and lineage matching have been strengthened on the MAPK-large scaffold (46/53 nodes mapped after node→gene expansion; lineage filtering via Model.csv; conditioned residual analysis). The lineage-matched conditioned association is small and consistently negative, which is scientifically informative but not a “positive validation” pillar.
  - **KR-B cancer corruption:** paired shifts + negative controls are implemented, but pooled DepMap anchoring is neutral; Gate C promotion requires lineage/context matching and/or a true paired acquisition.

## Submission positioning (recommended)
- **Main Figure 1 (core):** universality across the curated corpus with uncertainty and multiple null families.
- **Bias defense (Extended Data):** sensitivity grid + independent cohort + human-designed matched control.
- **Gate C (Results paragraph or Extended Data depending on strengthened evidence):**
  - Either (a) strengthen KR-A with a better endpoint and revalidated cohort; or
  - (b) strengthen DepMap anchoring at scale (larger scaffold and lineage-matched tests); or
  - (c) reposition Gate C as “actionable hypothesis” with a wet-lab readiness pack (already frozen) while being explicit that external validation remains pending.

## Protocol 8: remaining steps to a Nature submission
- **EPIC-LEV8-05 (manuscript refactor):** Completed draft rewrite exists but requires editorial tightening and reference completion for submission.
- **EPIC-LEV8-06 (submission pack):** cover letter + reviewer list must be finalized (template exists) and conflicts declared.
- **Gate C hardening options (choose at least one to reduce reviewer risk):**
  - Increase DepMap anchor power by expanding the scaffold/node universe and reporting lineage-matched effect sizes with confound conditioning.
  - Rebuild essentiality benchmarking with a provenance-locked and biologically interpretable target set (avoid heterogeneous “essential genes” lists across organisms without matching).
  - For KR-B, execute Route 2 (paired tumor/normal acquisition) or a curated cancer/healthy logic pair set with explicit mutation semantics and lineage anchors.

## Risk register (what reviewers will challenge)
- **Proxy dependence:** mitigated by explicit mapping table, but reviewers may ask for proxy-robustness across encoders.
- **Curation bias:** partially mitigated; independence cohort is still small; scaling to additional SBML sources would strengthen.
- **Biological validation:** currently the main vulnerability; must be framed conservatively or strengthened before submission.
