Phase 0: Reference Search - Optional Step
Purpose
Find similar implementations before paper implementation to improve implementation quality.
Reference code is for inspiration only, and the original paper specifications always take priority.
⚠️ Critical Principles (CRITICAL)
⚠️ REFERENCE CODE USAGE PRINCIPLES:

1. Reference code is for inspiration
2. Original paper specifications always take priority
3. Understanding and application, not copying
4. Adapt patterns found in references to meet paper requirements
5. License verification is mandatory

DO:
✓ Reference structure and patterns
✓ Learn implementation tricks and optimization techniques
✓ Identify common pitfalls
✓ Reference testing methodologies

DON'T:
✗ Do not copy code as-is
✗ Do not copy bugs from reference implementations
✗ Do not follow reference designs that differ from the paper
✗ Do not violate licenses
Search Protocol
Step 1: Analyze Paper References
Identify papers likely to have GitHub repositories from the paper's References section:
High-priority references:
1. Papers cited in the Method/Implementation section
2. Papers mentioned with "We build upon..." "We extend..." etc.
3. Methods used as baselines
4. Previous papers by the same authors

Exclude:
- Official implementation of the target paper (if exists, just use it)
- Pure theory papers
- Unrelated background citations
Step 2: Find Repositories via Web Search
Search queries using Claude's web search capability:
Search Query Patterns:

1. Direct Search:
   - "[Paper Title] GitHub"
   - "[Paper Title] code repository"
   - "[Author Name] [Paper Title] implementation"

2. Algorithm-based Search:
   - "[Algorithm Name] PyTorch implementation"
   - "[Algorithm Name] TensorFlow GitHub"
   - "[Key Methodology] code example"

3. Keyword Combinations:
   - "[Key Term 1] [Key Term 2] GitHub stars: >100"
   - "[Method Name] official implementation"
   - "[Dataset Name] [Method Name] benchmark"

Search Tips:
- Search both the paper's acronyms and full names
- Check the author's GitHub profile
- Search Papers With Code (paperswithcode.com)
Step 3: Quality Assessment and Ranking
Evaluate discovered repositories using the following criteria:
evaluation_criteria:
  repository_quality:  # 40% weight
    - stars: "[>100: Good, >500: Excellent]"
    - recent_activity: "[Commit within 6 months: Active]"
    - documentation: "[README, docstrings quality]"
    - issues_resolved: "[Issue response rate]"
    - tests: "[Presence of test code]"

  implementation_relevance:  # 30% weight
    - algorithm_match: "[Whether implemented algorithm matches the paper]"
    - completeness: "[Full pipeline vs partial implementation]"
    - paper_citation: "[Whether it cites the paper]"

  technical_depth:  # 20% weight
    - code_quality: "[Readability, degree of structuring]"
    - performance: "[Whether benchmark results exist]"
    - flexibility: "[Configurability, extensibility]"

  academic_credibility:  # 10% weight
    - author_affiliation: "[Author affiliation]"
    - official: "[Whether it's an official implementation]"
    - peer_reviewed: "[Peer-reviewed with the paper]"
Step 4: Select Top 5 and Analyze
For each repository, record the following:
selected_references:
  - rank: 1
    title: "[Paper/Repository Title]"
    repository_url: "[GitHub URL]"
    relevance_score: 0.95  # 0-1 scale

    key_contributions:
      - "[What can be learned from this repository 1]"
      - "[What can be learned from this repository 2]"

    implementation_value: |
      [Detailed explanation of how it helps implementation]

    usage_suggestion: |
      [Which parts to reference and how to apply them]

    caveats:
      - "[Points to note - differences from the paper]"
      - "[License restrictions]"
Output Format
reference_search_results:
  search_summary:
    total_found: "[Number of related repositories found]"
    evaluated: "[Number of repositories evaluated]"
    selected: 5

  official_implementation:
    exists: true/false
    url: "[URL if exists]"
    note: "[If official implementation exists, prioritize using it]"

  selected_references:
    - rank: 1
      title: "..."
      repository_url: "..."
      relevance_score: 0.95
      key_contributions: [...]
      implementation_value: "..."
      usage_suggestion: "..."
      caveats: [...]

    - rank: 2
      # ... same structure

    # ... rank 3, 4, 5

  search_queries_used:
    - "[Search query 1 used]"
    - "[Search query 2 used]"

  papers_with_code_link: "[URL of the PWC page for the paper]"
Usage Guide
When to Perform This Step
Recommended to perform:
✓ When implementing complex algorithms
✓ When implementation details are lacking in the paper
✓ When implementation patterns for a specific framework (PyTorch, TensorFlow) are needed
✓ When performance optimization tips are needed

Can be skipped:
- Very simple algorithms
- When the paper has detailed implementation descriptions
- When you already have experience with similar implementations
- When time is limited
How to Use References
1. Reference Structure:
   - File organization method
   - Class/function separation patterns
   - Config management approach

2. Learn Implementation Tricks:
   - Numerical stability handling
   - Memory optimization
   - Parallelization techniques

3. Testing Methodology:
   - Unit test structure
   - Integration test scenarios
   - Benchmark scripts

4. Identify Caveats:
   - Common bug patterns
   - Performance bottlenecks
   - Environment compatibility issues
⚠️ Self-Check: Verify Reference Search Completion
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ REFERENCE SEARCH CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

□ Have you checked for the existence of an official implementation?        → YES / NO
□ Have you tried at least 3 or more search queries?                        → YES / NO
□ Have you checked Papers With Code?                                       → YES / NO
□ Have you evaluated the quality of discovered repositories?               → YES / NO
□ Have you completed detailed analysis of the top 5?                       → YES / NO
□ Have you verified the license of each reference?                         → YES / NO
□ Have you recorded differences from the paper (caveats)?                  → YES / NO

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Caveats
⚠️ REMEMBER:

Reference code is only supplementary material.

The final implementation must follow the paper specifications.
If you find differences from the paper in the reference code,
prioritize following the paper's specifications.

Bugs or inconsistencies with the paper in the reference code
must not be included in our implementation.
