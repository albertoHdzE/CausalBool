Phase 1: Algorithm Extraction
Goal
Extract all technical details necessary for implementation from the research paper.
A developer should be able to implement the entire paper using only this extraction result.
⚠️ DO / DON'T Guidelines (CRITICAL)
DO:
✓ Copy pseudocode exactly from the paper (do not change a single character)
✓ Record equations exactly along with their equation numbers (Eq. X)
✓ Search for hyperparameters everywhere: text, tables, captions, and appendices
✓ Identify and record missing but essential items for implementation
✓ Specify the source (Section X, Table Y, Page Z) for all information
✓ Keep variable names, symbols, and subscripts exactly as in the paper

DON'T:
✗ Do not modify equations or pseudocode to "make them easier to understand"
✗ Do not guess parameter values not present in the paper
✗ Do not record information without a source
✗ Do not substitute with "commonly used" values
✗ Do not skip unclear parts (record them in missing_but_critical)
⚠️ Output Format Restrictions (OUTPUT RESTRICTIONS)
⚠️ MANDATORY OUTPUT FORMAT:
- Must output in YAML format only
- Pure YAML only, without Markdown explanations or prefaces
- All mandatory fields must be filled
- For fields with no information, record "Not specified in paper"
- Add "[INFERRED]" tag for guessed values

Output start: "`yaml"
Output end: "`"
Extraction Protocol
1. Algorithm Scan
Find and extract all of the following from the paper:
All contents of the Method/Algorithm section
Algorithm boxes (Algorithm 1, 2, 3...)
Equations and formulas (all Equations)
Pseudocode
Implementation details
2. Algorithm In-depth Extraction
For all discovered algorithms/methods/procedures:
algorithm_name: "[Exact name in the paper]"
section: "[e.g., Section 3.2]"
algorithm_box: "[e.g., Algorithm 1 on page 4]"

pseudocode: |
  [Copy the pseudocode from the paper exactly]
  Input: ...
  Output: ...
  1. Initialize ...
  2. For each ...
     2.1 Calculate ...
  [Maintain exact format and numbering]

mathematical_formulation:
  - equation: "[Copy the equation exactly, e.g., L = L_task + λ*L_explain]"
    equation_number: "[e.g., Eq. 3]"
    where:
      L_task: "task loss"
      L_explain: "explanation loss"
      λ: "weighting parameter (default: 0.5)"

step_by_step_breakdown:
  1. "[Detailed description of what Step 1 does]"
  2. "[What Step 2 calculates and why]"

implementation_details:
  - "Uses softmax temperature τ = 0.1"
  - "Gradient clipping at norm 1.0"
  - "Initialize weights with Xavier uniform"
3. Component Extraction
For all mentioned components/modules:
component_name: "[e.g., Mask Network, Critic Network]"
purpose: "[Role of this component in the system]"
architecture:
  input: "[shape and meaning]"
  layers:
    - "[Conv2d(3, 64, kernel=3, stride=1)]"
    - "[ReLU activation]"
    - "[BatchNorm2d(64)]"
  output: "[shape and meaning]"

special_features:
  - "[Unique features]"
  - "[Special initialization method]"
4. Training Procedure Extraction
Extract the complete training process:
training_loop:
  outer_iterations: "[Number of iterations or condition]"
  inner_iterations: "[Number of iterations or condition]"

  steps:
    1. "Sample batch of size B from buffer"
    2. "Compute importance weights using..."
    3. "Update policy with loss..."

  loss_functions:
    - name: "policy_loss"
      formula: "[Exact equation]"
      components: "[Meaning of each term]"

  optimization:
    optimizer: "Adam"
    learning_rate: "3e-4"
    lr_schedule: "linear decay to 0"
    gradient_norm: "clip at 0.5"
5. Hyperparameter Collection
Find everywhere: text, tables, captions:
hyperparameters:
  # Training
  batch_size: 64
  buffer_size: 1e6
  discount_gamma: 0.99

  # Architecture
  hidden_units: [256, 256]
  activation: "ReLU"

  # Algorithm-specific
  explanation_weight: 0.5
  exploration_bonus_scale: 0.1
  reset_probability: 0.3

  # Sources
  location_references:
    - "batch_size: Table 1"
    - "hidden_units: Section 4.1"
Output Format
complete_algorithm_extraction:
  paper_structure:
    method_sections: "[3, 3.1, 3.2, 3.3, 4]"
    algorithm_count: "[Total number of algorithms found]"

  main_algorithm:
    # Detail in the format above

  supporting_algorithms:
    - # Detailed information for each supporting algorithm

  components:
    - # All components and architectures

  training_details:
    # Complete training procedure

  all_hyperparameters:
    # All parameters, values, and sources

  implementation_notes:
    - "[Implementation hints mentioned in the paper]"
    - "[Tricks mentioned in the text]"

  missing_but_critical:
    - "[Essential but not explicitly stated items]"
    - "[Along with suggested default values]"
Core Principles
Thoroughly: A developer must be able to implement the entire paper using only this extraction result
Accurately: Copy equations, variable names, and values exactly
Comprehensively: All algorithms, all equations, all parameters
Cite sources: Record where each piece of information came from in the paper
Identify omissions: Identify what is needed for implementation but missing from the paper
⚠️ Self-Check: Mandatory Verification Before Completion (MANDATORY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ SELF-CHECK BEFORE FINISHING (Must all be YES to complete)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Algorithm Extraction Check:
□ Have all Algorithm boxes (Algorithm 1, 2, ...) been extracted?  → YES / NO
□ Are all procedures from the Method section included?                   → YES / NO
□ Do all equations have Equation numbers?                   → YES / NO

Hyperparameter Check:
□ Have all parameters mentioned in the text been collected?               → YES / NO
□ Have all parameters mentioned in tables been collected?             → YES / NO
□ Have parameters mentioned in captions/appendices also been checked?             → YES / NO

Completeness Check:
□ Is the training procedure fully described?                         → YES / NO
□ Are all terms of the loss function defined?                      → YES / NO
□ Is missing essential information recorded in missing_but_critical?  → YES / NO

Output Format Check:
□ Is it output in pure YAML format?                         → YES / NO
□ Are all mandatory fields filled?                           → YES / NO

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ If even one is NO, continue extracting until completion!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━