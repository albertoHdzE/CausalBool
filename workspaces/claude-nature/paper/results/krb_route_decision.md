# KR-B Route Decision (TSK-LEV8-04B-001)

**Document ID:** KR-B-ROUTE-DECISION-LEV8  
**Date:** 2026-04-05  
**Gate Alignment:** Gate B, Gate C  

## Decision
- **Primary route (frozen): Route 1 — curation-heavy paired logical models.**
- **Contingency route: Route 2 — TCGA tumor + matched normal expression → inferred networks → CCLE/DepMap anchoring.**

## Why Route 1 is primary (in this repository state)
- It is **immediately executable** with existing artifacts and does not require external downloads that would otherwise dominate the schedule and introduce provenance risks.
- It allows a **Nature-grade matched-pair analysis** with full reproducibility (locked JSON models, deterministic runs, checksum manifests) while still supporting external anchors (DepMap stratification; known oncogene enrichment).
- It aligns with the current strongest reliability constraint: **Gate A reproducibility lock** can be enforced now, while Route 2 depends on new acquisition, harmonization, and QC pipelines.

## Success definition (quantitative; frozen)
KR-B is considered “Extended Data-grade” if all conditions hold:
- **Primary effect:** ACI (or equivalent corruption metric) is higher in cancer than matched normal under a paired protocol, with a **95% CI excluding 0** for the mean paired difference.
- **Negative control:** random/mismatched pairing destroys the paired effect direction (CI overlaps 0 and/or sign flips).
- **Anchor:** at least one external anchor shows the expected enrichment/direction:
  - DepMap dependency enrichment for high-ACI/high-ΔD genes in lineage-matched cell lines, or
  - known oncogene / tumor suppressor enrichment among algorithmic “drivers”.

## Failure modes and mitigations (predeclared)
- **FM1: Small sample of curated pairs** → treat as pilot; expand curated pairs or narrow the claim to “case studies”.
- **FM2: Pairing ambiguity (not truly matched)** → enforce explicit gene-set control (intersection mapping) and log drop reasons.
- **FM3: Metric sensitivity to ordering or null choice** → run on the frozen massive test matrix rows for KR-B and require stability within tolerances.
- **FM4: Anchors fail (no DepMap/oncogene enrichment)** → demote KR-B to follow-up and redirect effort to Route 2 acquisition.

## Next actions (operational)
- Freeze the list of curated cancer/normal pairs as versioned inputs (manifest + checksums).
- Recompute KR-B outputs under the frozen definition contract and add at least one negative control.
- Only if KR-B clears the success definition, promote it to EPIC-LEV8-04B-007 as the Extended Data pillar; otherwise keep KR-C (human vs evolved) as the Extended Data pillar.

