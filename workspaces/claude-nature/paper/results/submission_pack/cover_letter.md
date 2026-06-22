# Cover Letter (Nature Submission Draft; LEV8)

**Manuscript title:** Algorithmic Efficiency Signatures in Curated Gene Regulatory Networks  
**Corresponding author:** Alberto Hernández (Department of Computer Science, University of Oxford)  

Dear Editors,

We submit our manuscript proposing an algorithmic-information perspective on gene regulatory network (GRN) structure: beyond topology, executable wiring diagrams contain reusable regularities that make them more compressible than randomized comparators under a frozen encoding. We formalize this as a null-comparison problem using a deterministic adjacency serialization and evaluate curated Boolean GRNs against three null families (density-matched ER, degree-preserved rewiring, and gate-permuted nulls where annotations exist). Across $n=232$ curated models ($5\le N\le 100$), biological networks occupy a consistently more compressible regime than degree-preserved nulls (mean fold reduction $D_{\mathrm{null}}/D_{\mathrm{bio}}=1.022$, 95\% CI $[1.016,1.027]$; paired $p=3.6\times10^{-12}$), with the same direction under alternative null families.

We anticipate the strongest predictable objections—proxy ambiguity and curation bias—and address them directly. We (i) lock an explicit theory-to-computation mapping table that distinguishes distinct computable proxies used in different parts of the work, (ii) execute a bias-defense grid including source-exclusion and selection-sensitivity tests, and (iii) include an independent cohort standardized from SBML-qual Cell Collective models. We further provide a checksum-based reproducibility lock and a one-command reproduction workflow so that all manuscript-grade outputs can be regenerated and verified.

We are careful in the biological positioning. Node-removal information loss ($\Delta D$) and external anchoring analyses are implemented with uncertainty and controls, but we report them conservatively: in the current repository state they do not yet constitute decisive external validation and are presented as bounded evidence and experimentally testable hypotheses rather than overclaimed “prediction.”

We believe this work is timely for *Nature* because it reframes a long-standing question—how to quantify structural order in biological regulation—through a rigorous, falsifiable, and reproducible algorithmic lens, while explicitly separating what is robust from what remains to be validated.

We confirm that this manuscript is not under consideration elsewhere and that all authors approve submission. We are happy to provide additional materials or to tailor the presentation to editorial preferences.

Sincerely,  
Alberto Hernández  
Department of Computer Science, University of Oxford

