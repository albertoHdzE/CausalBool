Phase 3: Code Planning
Goal
Integrate the results of Phase 1 (Algorithm Extraction) and Phase 2 (Concept Analysis) to generate a detailed plan that allows a developer to implement the entire paper without reading it.
⚠️ Content Volume Guidelines (STRICTLY FOLLOW)
📏 CONTENT BALANCE GUIDELINES:

Section 1 (file_structure):           ~800-1000 characters
Section 2 (implementation_components): ~3000-4000 characters  ← Core section
Section 3 (validation_approach):       ~2000-2500 characters
Section 4 (environment_setup):         ~800-1000 characters
Section 5 (implementation_strategy):   ~1500-2000 characters

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Total Target: 8000-10000 characters
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ Section 2 is the most important! Include all algorithms, equations, and parameters
⚠️ If the volume is insufficient, details are missing - double-check
Input
Phase 1 Result: Complete algorithm extraction (algorithm_extraction.yaml)
Phase 2 Result: Comprehensive paper analysis (concept_analysis.yaml)
Planning Process
1. Information Integration
Combine everything from both analyses:
All algorithms and pseudocode
All components and architectures
All hyperparameters and values
All experiments and expected results
2. Implementation Mapping
Link each component to a concrete implementation:
[For each algorithm/component/method in the paper]:
  - What it does in the paper and where it is described
  - How to organize the code (files, classes, functions)
  - Specific equations, algorithms, and procedures needed for implementation
  - Dependencies and relationships with other components
  - Implementation approach suitable for this paper
3. Technical Details Extraction
Collect all technical details related to implementation:
[Collect all implementation-related details from the paper]:
  - All algorithms with complete pseudocode and mathematical formulation
  - All parameters, hyperparameters, and configuration values
  - All architecture details (if applicable)
  - All experimental procedures and evaluation methods
  - Mentioned implementation hints, tricks, and special considerations
Output Format: 5 Mandatory Sections
complete_reproduction_plan:
  paper_info:
    title: "[Full paper title]"
    core_contribution: "[Main innovation to reproduce]"

  # ============================================
  # Section 1: File Structure (~800-1000 characters)
  # ============================================
  # Design the most suitable file configuration for this paper
  # - Analyze paper content (algorithms, models, experiments, systems, etc.)
  # - Organize files and directories in the most logical way for implementation
  # - Meaningful names and grouping based on paper content
  # - Clean, intuitive, and focused on actual implementation
  # - Include documentation files (README.md, requirements.txt) but implement them last

  file_structure: |
    project_name/
    ├── main.py                    # Main entry point
    ├── config.py                  # Configuration and hyperparameters
    ├── models/
    │   ├── __init__.py
    │   ├── network.py             # Core network architecture
    │   └── components.py          # Individual components
    ├── algorithms/
    │   ├── __init__.py
    │   └── core_algorithm.py      # Main algorithm implementation
    ├── training/
    │   ├── __init__.py
    │   ├── trainer.py             # Training loop
    │   └── losses.py              # Loss functions
    ├── evaluation/
    │   ├── __init__.py
    │   └── metrics.py             # Evaluation metrics
    ├── utils/
    │   ├── __init__.py
    │   └── helpers.py             # Utility functions
    ├── experiments/
    │   └── run_experiments.py     # Experiment scripts
    ├── requirements.txt           # Dependencies (implement last)
    └── README.md                  # Documentation (implement last)

  # ============================================
  # Section 2: Implementation Components (~3000-4000 characters) - Core Section
  # ============================================
  # Identify and specify all components to be implemented
  # - List all mentioned algorithms, models, systems, components
  # - For each: purpose, location, algorithm, equations, technical details
  # - Organize according to the actual content of the paper

  implementation_components: |
    ## 1. Core Algorithms

    ### 1.1 [Algorithm Name]
    - Location: algorithms/core_algorithm.py
    - Purpose: [What this algorithm does]
    - Pseudocode:
      ```
      [Copy pseudocode from the paper]
      ```
    - Core Equations:
      - [Eq. X]: L = ...
      - [Eq. Y]: ...
    - Hyperparameters:
      - param1: value1 (Source: Section X)
      - param2: value2 (Source: Table Y)

    ## 2. Model Architecture

    ### 2.1 [Model/Network Name]
    - Location: models/network.py
    - Input: [shape, meaning]
    - Output: [shape, meaning]
    - Layer Configuration:
      - Layer 1: ...
      - Layer 2: ...
    - Special Initialization: [If any]

    ## 3. Training Procedure

    ### 3.1 Training Loop
    - Location: training/trainer.py
    - Epochs/Iterations: [Value]
    - Steps:
      1. [Step 1 description]
      2. [Step 2 description]

    ### 3.2 Loss Functions
    - Location: training/losses.py
    - Equation: L_total = ...
    - Meaning of each term: ...

    ## 4. Evaluation

    ### 4.1 Evaluation Metrics
    - Location: evaluation/metrics.py
    - Metric List: [metric1, metric2, ...]
    - How to calculate each metric: ...

  # ============================================
  # Section 3: Validation Approach (~2000-2500 characters)
  # ============================================
  # Design how to verify the implementation works correctly
  # - Define necessary experiments, tests, and proofs
  # - Specify expected results from the paper (figures, tables, theorems)
  # - Design a validation approach suitable for the domain
  # - Include setup requirements and success criteria

  validation_approach: |
    ## 1. Unit Tests
    - [ ] Each component generates the correct output shape
    - [ ] Loss functions return correct values
    - [ ] Gradients flow correctly

    ## 2. Integration Tests
    - [ ] Run the entire training pipeline
    - [ ] Overfitting test with a small dataset

    ## 3. Reproduce Paper Results

    ### 3.1 Reproduce Table X
    - Expected Result: [Specific numbers]
    - Tolerance: ±[Value]
    - How to run: `python experiments/run_experiments.py --exp table_x`

    ### 3.2 Reproduce Figure Y
    - Expected Behavior: [Qualitative description]
    - How to run: `python experiments/run_experiments.py --exp figure_y`

    ## 4. Success Criteria
    - [ ] [Specific result 1]
    - [ ] [Specific result 2]
    - [ ] [Qualitative behavior 1]

  # ============================================
  # Section 4: Environment Setup (~800-1000 characters)
  # ============================================
  # Specify what is needed to run the implementation
  # - Programming language and version requirements
  # - External libraries and exact versions (if specified in the paper)
  # - Hardware requirements (GPU, memory, etc.)
  # - Special configurations or installation steps

  environment_setup: |
    ## Python Version
    - Python 3.10+ (uv recommended)

    ## Package Management (Using uv - Recommended)
    Configure an isolated and reproducible environment using uv:
    ```bash
    # Initialize project
    uv init

    # Add dependencies
    uv add torch numpy [other required packages]

    # Run
    uv run python main.py
    ```

    ## Core Dependencies
    ```
    torch >=2.0.0
    numpy >=1.24.0
    [other required packages]
    ```

    ## Hardware Requirements
    - GPU: [NVIDIA GPU with X GB VRAM]
    - RAM: [Minimum X GB]
    - Storage: [X GB]

    ## Dataset Preparation
    - [Dataset Name]: [How to download]
    - Preprocessing: [Required steps]

  # ============================================
  # Section 5: Implementation Strategy (~1500-2000 characters)
  # ============================================
  # Plan a step-by-step implementation approach
  # - Break down implementation into logical steps
  # - Identify dependencies between components
  # - Plan testing and validation at each step
  # - Handle missing details with reasonable default values

  implementation_strategy: |
    ## Phase 1: Foundation (First)
    1. config.py - Define all hyperparameters
    2. utils/helpers.py - Common utility functions

    Validation: Test configuration loading

    ## Phase 2: Core Implementation
    3. models/components.py - Individual components
    4. models/network.py - Entire network
    5. algorithms/core_algorithm.py - Main algorithm

    Validation: Check output shapes of each component

    ## Phase 3: Training Pipeline
    6. training/losses.py - Loss functions
    7. training/trainer.py - Training loop

    Validation: Overfitting test with small data

    ## Phase 4: Evaluation and Experiments
    8. evaluation/metrics.py - Evaluation metrics
    9. experiments/run_experiments.py - Experiment scripts
    10. main.py - Main entry point

    Validation: Reproduce paper results

    ## Phase 5: Documentation (Last)
    11. pyproject.toml - uv project setup and dependencies
    12. README.md - Usage documentation (including uv run commands)

    ## Handling Missing Details
    - [Missing item 1 in paper]: [Proposed default value]
    - [Missing item 2 in paper]: [Proposed approach]
Core Principles
Completeness: All 5 sections must be included
Detail: All algorithms, equations, parameters, and files must be specified
Feasibility: Code must be writable using only this plan
Logical Order: Provide implementation order considering dependencies
Include Validation: Specify success criteria and testing methods
File Priority Guidelines
First: Core algorithm/model files (highest priority)
Second: Supporting modules and utilities
Third: Experiment and evaluation scripts
Fourth: Configuration and data processing
Last: Documentation files (README.md, requirements.txt)
Note: README and requirements.txt depend on the final implementation, so write them last
⚠️ Self-Check: Mandatory Verification Before Completion (MANDATORY)
Before considering the implementation plan complete, you must verify the following:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ SELF-CHECK BEFORE FINISHING (Must all be YES to complete)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Section Inclusion Check:
□ Is the file_structure section included?           → YES / NO
□ Is the implementation_components section included? → YES / NO
□ Is the validation_approach section included?       → YES / NO
□ Is the environment_setup section included?         → YES / NO
□ Is the implementation_strategy section included?   → YES / NO

Content Completeness Check:
□ Are all algorithms in the paper mapped to components?     → YES / NO
□ Are all equations specified with Equation numbers and sources?     → YES / NO
□ Are all hyperparameters specified with values and sources?      → YES / NO
□ Are dependencies correctly reflected in the implementation order?        → YES / NO
□ Does the validation approach include specific expected results?       → YES / NO

Volume Check:
□ Is the total volume over 8000 characters?                → YES / NO
□ Is Section 2 the most detailed?                  → YES / NO

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ If even one is NO, continue writing until completion!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DO / DON'T Guidelines
DO:
✓ Integrate all extraction results from Phase 1 and 2 into the plan
✓ Specify concrete algorithms/equations to be implemented in each file
✓ Clearly indicate dependencies between files
✓ Make all information needed for implementation self-contained
✓ Specify concrete numbers/behaviors in the validation approach

DON'T:
✗ Incomplete explanations like "refer to the paper for details"
✗ Abstract component descriptions (without specific equations/algorithms)
✗ Writing only an implementation plan without a validation approach
✗ File placement ignoring dependency order
✗ Briefly writing the core section (Section 2)