# Wet-lab Collaboration Readiness Pack (LEV8)
## Objective
Produce a collaborator-facing, testable prediction set grounded in the mechanistic information-loss score ΔD, with explicit negative controls and decision rules.
## What ΔD means experimentally
- ΔD(v)=D(G)−D(G\v) quantifies the information lost when removing a node from the wiring diagram under a frozen encoding.
- The operational hypothesis for wet-lab: high-ΔD perturbations should induce larger functional disruption than low-ΔD perturbations under lineage-matched conditions.
## Candidate targets (MAPK-large scaffold; DepMap-mapped subset)
|Gene|Mean ΔD|DepMap dependency proxy|Notes|
|---|---:|---:|---|
|ELK1|4.266|0.1831|Top-ΔD candidate|
|ERK|3.979|0.1995|Top-ΔD candidate|
|PI3K|2.035|0.2826|Top-ΔD candidate|
|DUSP1|1.802|-0.02437|Top-ΔD candidate|
|AKT|1.753|0.05421|Top-ΔD candidate|
|FGFR3|1.529|-0.06429|Top-ΔD candidate|
|MDM2|1.487|0.5772|Top-ΔD candidate|
|FRS2|1.214|0.2685|Top-ΔD candidate|

## Negative controls (low-ΔD; same scaffold)
|Gene|Mean ΔD|DepMap dependency proxy|
|---|---:|---:|
|MAX|-0.801|0.8431|
|FOXO3|-1.177|0.3535|
|RAF|-1.227|0.1637|
|SOS|-2.252|0.1941|

## Experimental design (minimal viable)
- Perturbation: CRISPRi (preferred for graded loss) or CRISPR knockout for non-essential viability endpoints.
- Readout: viability/fitness (primary), plus at least one pathway-relevant phenotype (e.g., ERK phosphorylation for MAPK nodes) if feasible.
- Cell lines: choose lineage-matched lines where the target gene shows strong DepMap dependency; recommended candidates per gene are recorded in the JSON bundle.
- Controls: low-ΔD genes + non-targeting guides; match expression band when possible.
- Decision rule: success if ≥6/8 high-ΔD targets exceed control viability impact in ≥2 lineage-matched lines with consistent sign.

## Provenance
- Inputs: /Users/alberto/Documents/projects/CausalBool/4ClaudeCode/claude-Nature/paper/figures/figure3_depmap_validation_mapk_large.csv
- DepMap release dir: /Users/alberto/Documents/projects/CausalBool/data/DepMap
- Machine-readable bundle: 4ClaudeCode/claude-Nature/paper/results/wetlab_readiness_pack.json
