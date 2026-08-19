---
name: paper2code
description: When user ask for implementation or convertion of a paper document given as a path, local or remote
---

# Paper2Code Skill

A Skill for converting research papers into executable code.

## Files

| File | Description |
|------|-------------|
| `SKILL.md` | Main entry point - orchestrates the entire pipeline |
| `01_algorithm_extraction.md` | Phase 1: Extract algorithms, equations, pseudocode |
| `02_concept_analysis.md` | Phase 2: Analyze paper structure and components |
| `03_code_planning.md` | Phase 3: Create detailed implementation plan |
| `04_implementation_guide.md` | Phase 4: File-by-file code generation |
| `05_reference_search.md` | Phase 0 (Optional): Find reference implementations |
| `06_memory_management.md` | Context management for long papers |

## Installation

Copy this folder to your Claude skills directory:

```bash
cp -r paper2code ~/.claude/skills/
```

## Usage

The skill activates automatically when you request paper implementation:

- `"Implement this paper"`
- `"paper2code"`
- `"Convert paper to code"`

## Pipeline

```
Phase 0 (Optional) → Phase 1 → Phase 2 → Phase 3 → Phase 4
   Reference         Algorithm   Concept    Code      Code
   Search            Extraction  Analysis   Planning  Implementation
```