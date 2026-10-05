# Starting evidence and reading boundaries

## Local anchors

- `results/hierarchy_synthesis/supervision/representation-review-v1-r1-closure/REVIEW.md`:
  accepted stop decision and remaining causal-target boundary.
- `results/hierarchy_synthesis/review_closure/representation-review-v1-r1/SYNTHESIS.md`:
  corrected structural evidence and limitations.
- `README.md`, `src/deconvolution.py`, `src/causalbool.py`, and
  `bitacora/01_deconvolution_method_design.md`: existing full-table target and owners.
- `PROTOCOL_screen_identification.md`, `results/screen_identification/VERDICT.md`,
  `bitacora/screen_identification/02_verdict.md`, `RELATED_METHODS.md`:
  existing screen, qualifications and direct competitors. These are evidence to
  assess, not authority to repeat unchecked lower-bound or headroom claims.
- `PROTOCOL_order_discovery.md`: distinct unknown-sequence objective. Its broad
  universality/causal language is not an established theorem; reconcile access
  assumptions explicitly.
- `GOVERNANCE/GLOSSARY.md` and `GOVERNANCE/DESCRIPTION_LENGTHS.md` at repository
  root: current terminology and description-length contract. Later explicit
  author rulings take precedence over superseded passages in the same document.

## Primary external background

These sources motivate separating descriptions at different levels from agreement
under interventions. They do not validate this code or imply an efficient learner.

1. Rubenstein et al., *Causal Consistency of Structural Equation Models* (2017).
   https://arxiv.org/abs/1707.00819
   Author/institute PDF: https://is.mpg.de/uploads/publication_attachment/attachment/427/UAI_2017_Rubensteinetal.pdf
   Background: exact transformations relate levels through their intervention
   predictions. Inspect the actual assumptions before applying the definition.
2. Beckers and Halpern, *Abstracting Causal Models* (AAAI2019; preprint2018).
   https://arxiv.org/abs/1812.03789
   Author PDF: https://www.cs.cornell.edu/home/halpern/papers/abstraction.pdf
   Background: several different strengths of causal abstraction are defined;
   the allowed interventions and state map matter. Do not collapse them into
   one unqualified "multilevel causal" label.

Metadata/abstracts were checked during packet preparation on2026-10-04. This is
not a claim that every theorem in these papers was reviewed. Claude must identify
the definitions/propositions actually used and record access limitations. The
four tiny deterministic witnesses in TASKS are specified here independently.

For Boolean-network query identification, start with Akutsu et al.(1999,2003)
and the exact references in RELATED_METHODS.md. Verify their observation and
perturbation assumptions in primary sources if relying on their guarantees.
Do not spend the phase surveying unrelated machine learning, installing tools,
or importing an entropy-based complexity measure into this programme.
