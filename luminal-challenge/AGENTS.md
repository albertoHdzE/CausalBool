# Instructions for agents working on the Luminal challenge

Read [the canonical direct-index plan](plan/INDEX_ONLY_PLAN.md) and
[task status](plan/STATUS.md) before implementing or reviewing this challenge.
These documents are self-contained; do not depend on conversation history.

- Follow the definitions, task ownership, interfaces, budgets, acceptance gates,
  and implementation/reviewer prompts in the plan.
- The new solution uses direct decimal-anchor/free-mask/sumandos operations.
  BDDs, classical/serial seeding, and classical allocation are prohibited in its
  production path. The existing hybrid prototype is historical, not the target.
- Read `../GOVERNANCE/GLOSSARY.md` for terminology and the pinned
  `.reference/README.md` and `.reference/machine.py` for machine semantics.
- Free coordinates are per schema. Engine limits govern issues per cycle, not
  in-flight duration. Scratch is 256 words with inclusive live intervals.
- Preserve reference files, frozen classical code, historical results, and
  unrelated repository edits. Never claim UNKNOWN is UNSAT.
- Other agents may be working simultaneously. Edit only assigned files and do
  not revert their changes. Only the lead accepts a completed task.
- Retain real test output, commands, exit codes, and hashes. Use the plan's
  independent review checklist and rerun matrix; do not trust success banners.
- Prefer codebase-memory MCP graph tools for code discovery when available;
  use `rg` for non-code searches or unavailable/insufficient graph results.
- Do not publish or submit externally as part of implementation.

Start implementation with plan section 10. Start independent review with
section 11. If no delegation tools exist, follow the same task dependencies
sequentially and preserve the review gates.
