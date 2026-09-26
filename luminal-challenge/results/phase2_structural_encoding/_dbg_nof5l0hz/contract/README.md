# Claude Code delegation package

The author delegates implementation to Claude Code; Codex specifies and reviews.
The [scientific plan](../PHASE2_STRUCTURAL_ENCODING_PLAN.md) is version 2.1.
No phase 2 implementation or experimental outcome is claimed by this package.

1. Paste [CLAUDE_CODE_PROMPT.md](CLAUDE_CODE_PROMPT.md) into Claude Code.
2. Claude follows [IMPLEMENTATION_CONTRACT.md](IMPLEMENTATION_CONTRACT.md), runs
   the gated campaign and completes [HANDOFF_TEMPLATE.md](HANDOFF_TEMPLATE.md).
3. Return the resulting HANDOFF.md/run path to Codex for
   [independent review](REVIEW_PROTOCOL.md).

Frozen machine-readable inputs:

- [PROTOCOL.json](PROTOCOL.json): policies, seeds, counts, budgets and status rules.
- [FIXTURES.json](FIXTURES.json): twelve existing-program tiny domains and legal
  accepted-bootstrap incumbents. These are input data, not candidate results.
- [BASELINE_LOCK.json](BASELINE_LOCK.json): protected source/reference hashes.
- [ACCEPTANCE_MATRIX.json](ACCEPTANCE_MATRIX.json): mandatory checks and mutations.
- [PACKAGE_LOCK.json](PACKAGE_LOCK.json): package/scientific-plan content hashes.

From luminal-challenge run `python3 plan/phase2/verify_package.py` before starting.
The verifier is supplied now and only checks delegation inputs. The research
runner, research checker and four new test modules are deliverables Claude must
implement; they do not exist merely because this package names their commands.

Worker execution stops at reviewable research evidence. Production integration,
acceptance, commits and external publication are separate lead actions.
