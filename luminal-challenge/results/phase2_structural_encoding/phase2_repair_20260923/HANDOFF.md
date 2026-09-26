# Phase 2 implementation handoff

Status: READY_FOR_REVIEW (only after the fields below are complete).
Implementer/model: Claude Code (Opus 5), run `phase2_repair_20260923`
Start/end time:
Source HEAD, dirty diff SHA256, source snapshot SHA256: `1aef90681e3dead3ab1f560da8b7823ab66dabf4`, `5e32299313189de840b17e72c01b572b898a00685b62d7974dc047c5d4f192f9`, `fa60c4e8a750fa6f603bcec0bef6b7ac3e5597a62b5bc8c648fe38c7331eb96b`
Plan/protocol/package hashes:
Run directory: `results/phase2_structural_encoding/phase2_repair_20260923`

## Scope and ownership

List every changed/new file and its responsibility. List pre-existing changes
preserved. Answer the four ownership questions and cite the executable guard
and its planted-copy/import tests. Explain every deviation; write NONE if none.

## Commands and verification

| Command | Exit | Log path | Expected denominator | Actual denominator | Result |
|---|---:|---|---:|---:|---|

Include package preflight, new tests, mutation tests, exact oracles, experiment
stages, checker, canonical verification, comparator and git diff check.
Do not replace command evidence with this table.

## Stage and hypothesis dispositions

| Stage | Status | Gate evidence | Dependencies blocked / reason |
|---|---|---|---|
| P0 | PASS | `p0/summary.json` | gate satisfied |
| P1 | INCONCLUSIVE | `p1/summary.json` | public sampling did not reach the declared distinct-completion minimum |
| P2 | BLOCKED_BY_GATE | `p2/summary.json` | blocked by p1 (INCONCLUSIVE, local) |
| P3 | BLOCKED_BY_GATE | `p3/summary.json` | blocked by p1 (INCONCLUSIVE, local) |
| P4 | BLOCKED_BY_GATE | `p4/summary.json` | blocked by p1 (INCONCLUSIVE, local), p3 (BLOCKED_BY_GATE, local) |
| P5 | BLOCKED_BY_GATE | `p5/summary.json` | blocked by p1 (INCONCLUSIVE, local), p2 (BLOCKED_BY_GATE, local) |

| Hypothesis | Disposition | Evidence and limits |
|---|---|---|
| H1 | inconclusive | 24 exhausted codec/oracle comparisons with exact set equality, 0 round-trip failures, 0 defects; public coverage met: False. Scope is the implemented F_d, not all structural encodings. |
| H2 | NOT_RUN | P2 did not produce a summary |
| H3 | NOT_RUN | P3 did not produce a summary |
| H4 | NOT_RUN | P4 did not produce a summary; see its gate reason |

## Results

Report every program and fixture, including losses, invalid codes, dead ends,
interrupted searches, null/informative structure fixtures and failed processes.
Give ratios with their numerator and denominator. Distinguish source hash,
program digest, domain digest, codec index and physical address. State the
primary effect and interval, its sampling unit and all conditional exclusions.

## Proofs and counterexamples

Link PROOFS.md, independent enumeration, round trips, domain-equivalence evidence,
all bound checks and every retained counterexample, including repaired failures.

## Reproduction

Give exact working directory, interpreter, environment and commands for the
reviewer to reproduce the decisive result in a fresh output directory.

## Limitations and outstanding findings

List incomplete stages, gates missed, clock overshoot, sampling coverage,
method-boundary limits and claims the evidence cannot support. Do not assert
production acceptance or novelty. Include any blocker requiring a lead decision.

READY_FOR_REVIEW
