# Claude Code repair assignment — phase 2 lead review, 2026-09-23

Lead verdict: CHANGES_REQUIRED. Implementer: Claude Code. Reviewer: Codex.
Read LEAD_REVIEW.md and its retained probes before editing. This is a bounded
repair of the existing research implementation, not a new scientific campaign.

## Authority and ownership amendment

The author assigned Codex specification and acceptance, with Claude as coder.
This handoff fixes the test-path contradiction in the original delegation. It
supersedes only those path instructions; all scientific policies, seeds, budgets,
original fixtures and gates remain unchanged. Do not edit or rehash the original
locked `plan/phase2/` package. Save this handoff and LEAD_REVIEW.md hashes in every
new run's provenance and have the checker verify their presence and integrity.

You are not alone in the repository. Preserve all lead review artifacts,
original worker runs, lead-owned plan edits and unrelated files. Edit only the
existing research modules/README and research test files. Specifically authorised:

- Move `tests_direct/test_phase2_encoding.py`, `test_phase2_search.py`,
  `test_phase2_models.py`, `test_phase2_evidence.py` into `research_tests/`.
- Add `research_tests/__init__.py` as an empty package marker.
- Update the research snapshot collector, tests' file-location references,
  research README and new handoff commands to the new package.
- Add new regression tests under research_tests; do not alter historical tests.
- Write new identified repair runs under results/phase2_structural_encoding/.

Leave production sources, the historical evidence checker, original tests,
reference files and accepted evidence unchanged. Do not commit, merge, push,
submit, or launch additional agents. Codex retains final acceptance.

## Repair order and required regression evidence

1. **L1:** relocate the four tests; prove the frozen evidence test passes with
   all research tests present in their final location. No moving them aside
   during acceptance, exclusions in the historical checker, or provenance edits.
2. **R6:** verify reference.json's actual sha256 map and pinned commit. Missing,
   empty or unexpected schema is a failure. Retain every checked filename/count.
3. **R1:** stream every attempt to raw JSONL with immutable program/domain/codec,
   seed, attempt index, input index, status and case-check counts. For every
   completed decode, execute every program case inside the stream's time budget.
   Record complete discrepancy artifacts and fail without converting defects to
   DEAD_END. Retain enough information to reproduce all completions, duplicate
   counts and the union of distinct identities. Do not cap the real raw evidence
   at an example count; an optional display excerpt is separate.
4. **R2:** derive expected keys exclusively from locked inputs and the authorised
   stage request; require stage summary hashes and raw artifact hashes; enumerate
   exact P1 fixture/codec and public/stream/attempt membership. Independently
   recompute legality, case denominators, identity unions, status accounting,
   coverage and origin/round-trip/set claims. Reject the review's erased-evidence
   probe even if its summary hash is recomputed to match the edited file. Hashes
   alone do not prove completeness. Recompute P3 controls/triage and P2/P4/P5
   numerical statistics from raw measurements when those stages are present;
   verify every reported gate, not merely the parameter labels. Failed/missing
   commands and their referenced logs cannot be silently labelled complete.
5. **R3:** enforce dependency PASS plus required source/input/stage hashes on
   every entry path, including `--inputs`. Missing hashes fail. Import transitive
   dependency metadata, validate evidence before execution and preserve prior
   runs read-only. Add a CLI regression with real INCONCLUSIVE P1 input: requesting
   P2/P3 must block before its body is called. A valid prior PASS fixture is the
   positive control. Do not introduce a force/skip gate flag.
6. **R4:** pass an absolute deadline through construction, search, proposal
   expansion and validation. Check expiry before each phase and immediately after
   expensive uninterruptible work; no fresh full query allowance after building.
   If candidate validation crosses the deadline, retain the previous incumbent
   and account for the interrupted attempt. Keep measured overshoot distinct
   from deliberately renewed budgets. Exercise all declared node/validation caps.
7. **R5:** finish the conditional large-domain model policy exactly as previously
   specified. Add conditional model rows to runner and checker membership, require
   genuine measurements for PASS, and implement lazy ordered union traversal with
   deduplication and budget checks. No materialisation proportional to 2**B before
   the first proposal. Unit-test both H4-authorised and H4-blocked branches with
   controlled stage fixtures; do not fake a positive H4 outcome in real evidence.

Run the retained lead probes unchanged where their interfaces still apply. If
the strengthened provenance deliberately rejects a historical run missing new
required metadata, construct a NEW valid control and apply the same corruptions
there; do not treat rejection of the old control as proof the targeted mutation
was detected. Add the six lead reproductions as regressions with explicit expected
outcomes. A string naming a check ID is not proof that its failure mode was tested.

## Execution and handoff

From luminal-challenge run:

    python3 plan/phase2/verify_package.py
    PYTHONPATH=.reference:. python3 -m unittest \
      research_tests.test_phase2_encoding research_tests.test_phase2_search \
      research_tests.test_phase2_models research_tests.test_phase2_evidence -v
    PYTHONPATH=.reference:. python3 -m research.run_structural_experiments \
      --stage all --run-id UNIQUE_REPAIR_ID --contract plan/phase2
    PYTHONPATH=.reference:. python3 -m research.check_structural_evidence \
      --run results/phase2_structural_encoding/UNIQUE_REPAIR_ID --contract plan/phase2
    python3 export_direct.py
    python3 verify_direct.py --stage all \
      --output results/phase2_structural_encoding/UNIQUE_REPAIR_ID/production_verification
    python3 compare_direct.py --repeats 3 --timeout 20 \
      --output results/phase2_structural_encoding/UNIQUE_REPAIR_ID/production_comparison

Use a real unique ID. Retain logs and exit codes. Repaired case execution consumes
sampling time; if fewer draws fit, report INCONCLUSIVE rather than changing caps.
If P1 misses coverage again, retain the result and block P2–P5 as before. Conditional
unit tests remain required, but do not count as real P2–P5 experimental evidence.
No scientific gate is relaxed in this assignment.

Provide a new HANDOFF.md with R1–R6/L1 individually marked fixed or unresolved,
exact code locations, before/after regression evidence, full original/repair source
hashes, relocated-file map, all gate outcomes and actual experiment denominators.
Correct the earlier claim that public case validation and full reference checking
were already performed. Preserve that original handoff as historical evidence.
End READY_FOR_REVIEW. Codex will independently rerun the repaired acceptance path.
