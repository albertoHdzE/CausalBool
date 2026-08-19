Memory and Context Management Guide
Purpose
Prevent context overflow when processing long papers and ensure efficient workflow progression.
Core Strategies
1. Save Output Step-by-Step
Save the results to files upon completion of each Phase to reduce context burden:
paper_workspace/
├── paper.txt                      # Original paper text
├── 01_algorithm_extraction.yaml   # Phase 1 result
├── 02_concept_analysis.yaml       # Phase 2 result
├── 03_implementation_plan.yaml    # Phase 3 result
└── src/                           # Phase 4 generated code
    ├── config.py
    ├── models/
    ├── algorithms/
    └── ...
Save command examples:
# Save Phase 1 result
cat > paper_workspace/01_algorithm_extraction.yaml << 'EOF'
[Phase 1 YAML output]
EOF

# Save Phase 2 result
cat > paper_workspace/02_concept_analysis.yaml << 'EOF'
[Phase 2 YAML output]
EOF
2. Pass Context Between Phases
When moving to the next Phase, pass only the core summary instead of the full output:
# Phase 1 → Phase 2 passed summary
phase1_summary:
  algorithms_found: 3
  key_algorithms:
    - "Algorithm 1: [Name] - [Core content in 1 line]"
    - "Algorithm 2: [Name] - [Core content in 1 line]"
  hyperparameters_count: 15
  critical_equations: [3, 5, 7, 12]

# Phase 2 → Phase 3 passed summary
phase2_summary:
  components_count: 5
  implementation_complexity: "Medium"
  key_dependencies:
    - "Component A → Component B"
    - "Component B → Component C"
  experiments_count: 4
3. Optimize Memory During Implementation
Context management in the per-file implementation cycle:
File implementation cycle:
┌─────────────────────────────────────────────────────┐
│ 1. Load only the information needed for the         │
│    current file implementation                      │
│    - The section for that file in implementation_   │
│      plan.yaml                                      │
│    - Interfaces of dependent files (not full code)  │
├─────────────────────────────────────────────────────┤
│ 2. Implement the file                               │
├─────────────────────────────────────────────────────┤
│ 3. Move to the next file after completion           │
│    - Refer to previous file contents only if needed │
│    - Do not keep the entire code in memory          │
└─────────────────────────────────────────────────────┘
Tips for Processing Long Papers
Read Paper in Chunks
If the paper is very long, analyze it section by section:
Reading order (priority):
1. Abstract + Introduction (Grasp core contributions)
2. Entire Method section (Algorithm extraction)
3. Experiments section (Environments, baselines, metrics)
4. Appendix (Detailed hyperparameters)
5. Related Work (Only if necessary)

Can be skipped:
- Detailed Related Work content (Unnecessary for implementation)
- Long Discussion/Conclusion (Summary only)
- Acknowledgments
Split Large Algorithms
Split complex algorithms into sub-components:
# Split without processing the whole thing at once
large_algorithm:
  component_1:
    extracted: true
    summary: "[Summary]"
  component_2:
    extracted: true
    summary: "[Summary]"
  component_3:
    extracted: false  # Not yet processed
Self-Monitoring Checkpoints
Intermediate saving is recommended in the following situations during implementation:
Intermediate save triggers:
□ Every 5 files implemented
□ Upon completion of a complex algorithm (50+ lines)
□ Save current state when an error occurs
□ Before starting a new Phase
□ Before starting a long task (expected to take 30+ minutes)
Save Checklist
checkpoint_save:
  current_phase: "[Current Phase number]"
  completed_files:
    - "config.py"
    - "models/network.py"
  current_file: "algorithms/core.py"
  current_progress: "50%"  # Progress of the current file
  next_steps:
    - "[Next task 1]"
    - "[Next task 2]"
  blockers:
    - "[Blocked part, if any]"
Context Recovery Protocol
If the conversation is interrupted or context is lost:
Recovery steps:
1. Check the paper_workspace/ directory
2. Read the most recently completed Phase result file
3. Check the list of generated code files
4. Identify the last work point
5. Resume from that point
Recovery command examples:
# Check current status
ls -la paper_workspace/
ls -la paper_workspace/src/

# Check the last Phase result
cat paper_workspace/03_implementation_plan.yaml

# Check generated files
find paper_workspace/src -name "*.py" -type f
Efficient Reference Patterns
Reference Only Interfaces
When referencing other files, only the interface is needed, not the full implementation:
# Reference only signatures instead of full code
# Interface of models/network.py:
class NetworkModel:
    def __init__(self, config: Config): ...
    def forward(self, x: Tensor) -> Tensor: ...
    def get_features(self, x: Tensor) -> Tensor: ...
Leverage Dependency Graph
Reference the dependency graph when determining implementation order:
config.py (No dependencies)
    ↓
utils/helpers.py (Depends only on config)
    ↓
models/components.py (Depends on config, utils)
    ↓
models/network.py (Depends on components)
    ↓
algorithms/core.py (Depends on network)
    ↓
training/trainer.py (Depends on all)
⚠️ Cautions
⚠️ MEMORY MANAGEMENT RULES:

1. Do not process the entire paper at once
   → Process by dividing it into sections

2. Do not include the full output of the previous Phase in the next Phase
   → Pass only the core summary

3. Do not keep all generated code in memory
   → Save to files and refer to them when needed

4. Periodically save progress during long tasks
   → To allow recovery if interrupted

5. Avoid unnecessary repetitive reading
   → Summarize and store information once read
Recommended Workflow
[Paper Input]
    │
    ▼
[Phase 1: Algorithm Extraction]
    │ → Save 01_algorithm_extraction.yaml
    │ → Generate core summary
    ▼
[Phase 2: Concept Analysis]
    │ → Save 02_concept_analysis.yaml
    │ → Maintain Phase 1 summary + Phase 2 summary
    ▼
[Phase 3: Implementation Plan]
    │ → Save 03_implementation_plan.yaml
    │ → Maintain only core information needed for implementation
    ▼
[Phase 4: Code Implementation]
    │ → Implement and save file by file
    │ → Checkpoint every 5 files
    ▼
[Completion]