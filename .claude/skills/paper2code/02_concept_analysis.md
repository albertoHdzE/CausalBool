Phase 2: Concept Analysis
Goal
Understand the overall structure of the research paper and identify all elements that must be implemented for successful reproduction.
⚠️ DO / DON'T Guidelines (CRITICAL)
DO:
✓ Systematically map all sections of the paper
✓ Grasp the data flow and dependencies between all components
✓ Identify all environments/datasets/baselines used in experiments
✓ Define success criteria with specific numbers
✓ Evaluate implementation complexity and priorities

DON'T:
✗ Do not confuse Related Work with implementation requirements
✗ Do not use abstract success criteria (e.g., "good performance")
✗ Do not omit relationships between components
✗ Do not miss variations needed for ablation studies
⚠️ Output Format Restrictions (OUTPUT RESTRICTIONS)
⚠️ MANDATORY OUTPUT FORMAT:
- Must output in YAML format only
- Pure YAML only, without Markdown explanations or prefaces
- All mandatory fields must be filled
- Include specific numbers and sources

Output start: "`yaml"
Output end: "`"
Analysis Protocol
1. Paper Structure Analysis
Create a complete map of the paper:
paper_structure_map:
  title: "[Full paper title]"

  sections:
    1_introduction:
      main_claims: "[What the paper claims to achieve]"
      problem_definition: "[The exact problem to be solved]"

    2_related_work:
      key_comparisons: "[Methods this study builds upon or competes with]"

    3_method:  # Can have multiple subsections
      subsections:
        3.1: "[Title and main content]"
        3.2: "[Title and main content]"
      algorithms_presented: "[List of all algorithm names]"

    4_experiments:
      environments: "[All test environments/datasets]"
      baselines: "[All comparison methods]"
      metrics: "[All evaluation metrics used]"

    5_results:
      main_findings: "[Key results proving the method works]"
      tables_figures: "[Important result tables/figures to reproduce]"
2. Methodology Decomposition
For the main method/approach:
method_decomposition:
  method_name: "[Full name and acronym]"

  core_components:  # Decompose into implementable pieces
    component_1:
      name: "[e.g., State Importance Estimator]"
      purpose: "[Why this component exists]"
      paper_section: "[Where it is described]"

    component_2:
      name: "[e.g., Policy Refinement Module]"
      purpose: "[Role in the system]"
      paper_section: "[Where it is described]"

  component_interactions:
    - "[How component 1 passes to component 2]"
    - "[Data flow between components]"

  theoretical_foundation:
    key_insight: "[Key theoretical insight]"
    why_it_works: "[Intuitive explanation]"
3. Implementation Requirements Mapping
Map paper contents to code requirements:
implementation_map:
  algorithms_to_implement:
    - algorithm: "[Name in the paper]"
      section: "[Where defined]"
      complexity: "[Simple/Medium/Complex]"
      dependencies: "[What is needed to work]"

  models_to_build:
    - model: "[Neural network or other model]"
      architecture_location: "[Section describing it]"
      purpose: "[What this model does]"

  data_processing:
    - pipeline: "[Required data preprocessing]"
      requirements: "[What the data should look like]"

  evaluation_suite:
    - metric: "[Metric name]"
      formula_location: "[Where defined]"
      purpose: "[What it measures]"
4. Experiment Reproduction Plan
Identify all necessary experiments:
experiments_analysis:
  main_results:
    - experiment: "[Name/description]"
      proves: "[The claim this verifies]"
      requires: "[Components needed to run]"
      expected_outcome: "[Specific numbers/trends]"

  ablation_studies:
    - study: "[What is removed]"
      purpose: "[What this shows]"

  baseline_comparisons:
    - baseline: "[Method name]"
      implementation_required: "[Yes/No/Partial]"
      source: "[Where to find implementation]"
5. Core Success Factors
Define successful reproduction:
success_criteria:
  must_achieve:
    - "[Main results that must be reproduced]"
    - "[Core behaviors that must be demonstrated]"

  should_achieve:
    - "[Additional results validating the method]"

  validation_evidence:
    - "[Specific figures/tables to reproduce]"
    - "[Qualitative behaviors to demonstrate]"
Output Format
comprehensive_paper_analysis:
  executive_summary:
    paper_title: "[Full title]"
    core_contribution: "[One-sentence summary]"
    implementation_complexity: "[Low/Medium/High]"
    estimated_components: "[Number of main components to build]"

  complete_structure_map:
    # Full section breakdown as above

  method_architecture:
    # Detailed component breakdown

  implementation_requirements:
    # All algorithms, models, data, metrics

  reproduction_roadmap:
    phase_1: "[What to implement first]"
    phase_2: "[What to build next]"
    phase_3: "[Final components and validation]"

  validation_checklist:
    - "[ ] [Specific results to achieve]"
    - "[ ] [Behaviors to demonstrate]"
    - "[ ] [Metrics to match]"
Core Principles
Thoroughly: Do not miss anything. The output must be a complete blueprint for reproduction
Structured: Decompose all parts of the paper into implementable pieces
Understand Relationships: Clarify dependencies and data flow between components
Specify Validation Criteria: Define what a "successful reproduction" is
Prioritize: Distinguish core contributions from additional elements
⚠️ Self-Check: Mandatory Verification Before Completion (MANDATORY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ SELF-CHECK BEFORE FINISHING (Must all be YES to complete)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Paper Structure Analysis Check:
□ Are all Method sections mapped?                        → YES / NO
□ Are all algorithm names listed?                    → YES / NO
□ Are all experiments in the experiment section identified?                   → YES / NO

Component Analysis Check:
□ Are inputs/outputs of all components defined?               → YES / NO
□ Is the data flow between components clear?                 → YES / NO
□ Is the dependency order grasped?                            → YES / NO

Experiment Requirements Check:
□ Are all environments/datasets identified?                      → YES / NO
□ Are all baseline methods identified?                      → YES / NO
□ Are all evaluation metrics defined?                         → YES / NO
□ Are ablation study variations identified?                   → YES / NO

Success Criteria Check:
□ Do must_achieve items include specific numbers?       → YES / NO
□ Are specific tables/figures to reproduce specified?                 → YES / NO

Output Format Check:
□ Is it output in pure YAML format?                        → YES / NO
□ Are all mandatory fields filled?                          → YES / NO

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ If even one is NO, continue analysis until completion!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━