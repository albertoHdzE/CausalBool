Phase 4: Implementation Guide
Goal
Generate a complete and executable codebase based on the implementation plan created in Phase 3.
Core Behavioral Rules
⚠️ CRITICAL BEHAVIORAL RULES
⚠️ SINGLE FILE PER RESPONSE:
- Implement exactly one file per response
- Do not ask for permission between files
- Continue implementing until completion

DO:
- Implement exactly what is specified in the paper
- Write simple and direct code
- Prioritize working code, elegance comes later
- Test each component immediately
- Move to the next file immediately after completing implementation

DON'T:
- Do not ask "Should I implement the next file?" between files
- Do not waste time on advanced tooling instead of paper requirements
- Do not write extensive documentation not needed for core functionality
- Do not write optimization utilities not needed for reproduction
- Do not use excessive abstraction or design patterns
- Do not just provide instructions without writing actual code
Tool Calling Strategy
TOOL CALLING STRATEGY:
1. ⚠️ Implement one file per message
2. Plan the next step after checking results
3. File implementation cycle: Analyze → Implement → Next file

EXECUTION PATTERN:
- Plan First: Explain reasoning before each task
- One Step at a Time: Execute → Check results → Plan next → Execute
- Iterative Progress: Build the solution gradually
- Strategic Sequencing: Choose logical next steps based on previous results

⚠️ CRITICAL: Use bash and python tools to directly replicate the paper
            - Do not just provide instructions, actually implement it
Top Priority Goal
Implement all algorithms, experiments, and methods mentioned in the paper.
Success is measured by completeness and accuracy, not code elegance.
Core Strategy
Thoroughly read the paper and implementation plan to identify all algorithms, methods, and experiments
Implement core algorithms first, then environment, then integrated implementation
Use the exact versions and specifications specified in the paper
Test immediately after implementing each component
Focus on a working implementation rather than a perfect architecture
Implementation Approach
Incremental build per file
At each step:
Identify: Confirm what to implement next from the implementation plan
Implement: Implement one component at a time
Test: Test immediately to catch problems early
Integrate: Integrate with existing components
Verify: Verify against paper specifications
Implementation Order
Step 1: Setup and Environment Files
pyproject.toml     # uv project setup (generated with uv init)
config.py          # All hyperparameters and settings

Step 2: Core Utilities and Base Classes
utils/__init__.py
utils/helpers.py   # Common utility functions

Step 3: Main Implementation Modules
models/__init__.py
models/network.py      # Core network architecture
models/components.py   # Individual components

algorithms/__init__.py
algorithms/core.py     # Main algorithm implementation

Step 4: Training Pipeline
training/__init__.py
training/losses.py    # Loss functions
training/trainer.py   # Training loop

Step 5: Evaluation and Experiments
evaluation/__init__.py
evaluation/metrics.py        # Evaluation metrics
experiments/run_main.py      # Main experiment script

Step 6: Entry Point and Documentation
main.py            # Main entry point
README.md          # Usage documentation (including uv run commands)

Environment Setup Commands (Using uv)
# When starting the project
uv init
uv add torch numpy [required packages]

# Run
uv run python main.py

Code Quality Standards
Completeness
No placeholders, TODOs, or incomplete functions
Full feature implementation with appropriate error handling
Complete API with correct signatures and documentation
All specified features working immediately

Quality
Production-level code following language best practices
Comprehensive type hints and docstrings
Proper logging, validation, and resource management
Clean architecture with separation of concerns

Domain-Specific Adaptations
Research/ML Papers:
Mathematical accuracy
Reproducibility (seeds, deterministic operations)
Evaluation metrics
Experiment logging

Systems/Tools:
CLI interfaces
Configuration management
Error handling
Documentation

✅ Completion Checklist (MANDATORY)
Must verify before considering the task complete:
✅ COMPLETENESS CHECKLIST:
- [ ] All algorithms mentioned in the paper (including abbreviations or alternative names)
- [ ] All environments/datasets with exact specified versions
- [ ] All comparison methods referenced in experiments
- [ ] A working integration that can run the paper's experiments
- [ ] A complete codebase reproducing all metrics, figures, and tables in the paper
- [ ] Basic documentation explaining how to reproduce the results

⚠️ Not complete unless all items are checked!
Critical Success Factors
CRITICAL SUCCESS FACTORS:

1. Accuracy:
   - Exactly matches paper specifications (versions, parameters, settings)
   - Accurately translates equations into code
   - Uses hyperparameter values exactly

2. Completeness:
   - Implements all discussed methods, not just the main contribution
   - Implements variations needed for ablation studies
   - Implements what is needed for baseline comparisons

3. Functionality:
   - Code actually works and runs experiments successfully
   - Can train/evaluate without errors
   - Can actually reproduce the paper's results
Execution Guidelines
Before implementing each file
Check the requirements for that file in the implementation plan
Verify that dependent files have already been implemented
Refer to relevant equations/algorithms in the paper

When implementing each file
Write complete import statements
Define class/function structures
Translate paper equations/algorithms into code
Add appropriate docstrings
Add error handling

After implementing each file
Check for syntax errors
Verify all imports are resolved
Run a simple test if possible
Move to the next file immediately (do not ask for permission)

File Writing Template
Python File Basic Structure
"""
[File description]

Paper: [Paper title]
Section: [Related section number]
"""

import ...

# Hyperparameters from the paper
PARAM_NAME = value  # Source: Section X / Table Y


class ComponentName:
    """
    [Component description]

    Implements Equation X from the paper:
    [Equation]
    """

    def __init__(self, ...):
        ...

    def forward(self, ...):
        # Implement Eq. X
        ...


def main():
    """Main execution function"""
    ...


if __name__ == "__main__":
    main()

Final Check
After completing implementation:
Run Test: Does `python main.py` run without errors?
Training Test: Does training proceed with small data?
Result Check: Can you reproduce the main results of the paper?
Documentation Check: Is the execution method clear in README.md?
If all items pass, implementation is complete!
⚠️ REMEMBER
The goal is to replicate the entire paper.
Not a single part or a minimal example.

The file reading tool is PAGINATED,
so you must call it multiple times to read all relevant parts of the paper.

If you find patterns in reference code, use them only for inspiration,
and always implement according to the original paper specifications.