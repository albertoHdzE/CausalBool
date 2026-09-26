# RELEASE_HANDOFF: third round, resume 1.0 (repairs, then D and C)

**Status: READY_FOR_CODEX_REVIEW.** Not self-accepted; only Codex accepts.

- **Path:** `luminal-challenge/results/phase2_structural_encoding/third_round_20260925_resume/RELEASE_HANDOFF.md`
- **Implementer and authority:** Claude Code, 2026-09-25, working to
  `plan/CLAUDE_PHASE2_THIRD_ROUND_RESUME.md` v1.0 and its locked `PROTOCOL.json`,
  with the parent third-round plan and protocol.
- **Package verifier:** PASS at the start and at the end (4 files, 285 protected
  inputs; `checks/verify_package_end.json`).
- **Outcome:** all three lead findings (R1–R3) are closed. The repaired M gate
  passes at 0.786. Stage D passes. Stage C succeeds:
  - cost ratio **0.574 [0.552, 0.598]**;
  - quality ratio **0.991 [0.985, 0.996]**;
  - exact fixed-work parity on 1,000/1,000 pairs.

  **C1 is eligible for lead acceptance.** R0 stays the accepted baseline until
  the lead rules.
- **Budgets:** combined measurement time was **0.93 h** of the 24 h cap (parent
  0.117 h + resume 0.812 h; 11,553 charged processes). Active development was
  about 2.2 h of the 16 h cap (parent about 0.5 h + resume about 1.7 h;
  `WORK_LOG.md`).
- **Not done:** no commits, pushes, publication, subagents, process termination,
  production or paper edits.
  - No pre-existing file changed (`checks/FINAL_STATE.json`); git status is
    identical at start and end.
  - The parent run, its sources, the old auditor and the lead review are
    unchanged.

## Stage statuses and counts

| Stage | Rows (expected) | Status |
|---|---:|---|
| M_diagnosis / M_kernel (parent, linked) | 210 / 180 | reused; identity and membership re-verified |
| R_adapter | 90 (90), 0 failed | COMPLETE |
| M repaired gate | — | **PASS**: 0.7864 ≤ 0.80. Successor audit PASS. |
| D_fixed_work | 600 (600), 0 failed | COMPLETE: 300/300 exact parity |
| D_wall | 600 (600), 0 failed | COMPLETE |
| D_memory | 60 (60), 0 failed | COMPLETE: fingerprints equal |
| D gate | — | **PASS**: cost ratio 0.589 ≤ 0.90; mean log J −0.0173 ≤ 0 (44/256/0) |
| Cohort 980000–980199 | 200 programs, 40 per family | VALID: no exposure, 0 duplicate compilation inputs (within or against 1,842 prior programs) |
| C_acceptance | 284 (284), 0 failed | COMPLETE: 277 cases per export; pinned tests and score exit 0 |
| C_fixed_work | 2,000 (2,000), 0 failed | COMPLETE: 1,000/1,000 exact parity |
| C_wall | 6,000 (6,000), 0 failed | COMPLETE |
| C_public | 280 (280), 0 failed | COMPLETE |
| C_export | 1,248 (1,248), 0 failed | COMPLETE |
| C joint verdict | — | **SUCCESS** |

## Repairs (R1–R3; details in `REPAIR_CLOSURE.json`)

- **R1, the adapter.**
  - `ADAPTER_SPEC.json` was written before any code. It lists every C1
    call-site difference and states what the timed replay already contains.
  - The skeleton does real node construction holding the state reference,
    reads, dispatch, streaming release and epoch disposal. It was frozen
    (`ADAPTER_FREEZE.json`) and measured in 90 fresh processes with full raw
    streams.
  - The measured cost is about 20× the old estimate, and at most 7.5% of the
    kernel replay.
  - N = kernel median + max(old adapter, repaired adapter) + 0. The zero rests
    on an itemised accounting of every other changed line.
  - Predictions:

    | Accounting | Conservative ratio |
    |---|---:|
    | Original registered (retained) | 0.8268 |
    | Scope-matched `O`, old adapter | 0.7638 |
    | Scope-matched `O`, repaired adapter | **0.7864** |
    | Replay-only `O` (sensitivity only) | 0.7650 |
- **R2, the auditor.** The successor is `research/third_round_resume_audit.py`.
  It reuses no reporter code and covers:
  - strict JSONL, including torn final fragments, blank lines and NaN;
  - membership derived from protocol and generator;
  - reconciliation of attempts, exits, stdout hashes and the ledger;
  - measured-source and transitive hashes, with the one exact disposition;
  - the spec-era kernel prefix;
  - workload bytes;
  - M0 plain/timer/trace fingerprints and instrumentation parity;
  - M2 parity recomputed from its parts;
  - optional full replay of all 30 workloads under both kernels;
  - explicit stage states and the dependency matrix;
  - recomputed numbers with a field-to-check map.

  The lead's four probes still PASS the old auditor and FAIL the successor; the
  tests assert both sides. Fifteen further mutations are rejected.

  | Final audit | Checks | Findings |
  |---|---:|---:|
  | M/repair (`checks/AUDIT_M_final.json`) | 18,219 | 0 |
  | D (see D1) | 22,550 | 1 |
  | C (`checks/AUDIT_C.json`) | 143,585 | 0 |
- **R3, the speedup median.** The corrected median is 2.3649168298633314. The
  parent's 2.3947613512067907 was the upper median (`SPEEDUP_ADDENDUM.md`).
- **Provenance** (`provenance/`):
  - `third_round_common.py`: both byte versions and the diff are retained; the
    reconstruction hashes to `bd3a7b48…`.
  - The kernel's spec-era prefix (17,377 bytes) and the measured file are both
    retained. The spec-before-code chronology remains a deviation.
  - The parent's raw stdout exists only as reconstructed payloads (hashes
    verified). Full historical stderr is not recoverable. Every new process in
    this run keeps its complete raw streams under `stages/*/raw/`.

## C1

- **Source:** `research/third_round_candidate.py` (sha
  `5ccbaaa3128c46e2edd1585888cacd522616c0827813cbbff6c225e944050430`). It is a
  byte copy of R0 plus a 67-line `Expander` diff (`candidate/C1.diff`, parent
  snapshot `candidate/R0_parent.py`).
- **BS1 kernel:** unchanged (`77c373e1…`).
- **Export:** `exports/C1/compiler.py` (sha `58ee7505…`), regenerated
  deterministically.
- **Tests:**
  - 53 inherited semantic tests bound to C1 (coverage declared, 5 exclusions
    with reasons);
  - exhaustive fixture parity;
  - fixed-work and tick-clock parity;
  - repeated compilation;
  - 6 kernel mutants caught through the compiler path.

## Deviations and disclosures

- **D1: auditor appended after the D freeze.** I appended the Stage C functions
  to `research/third_round_resume_audit.py` while D rows were being measured. No
  D function changed: the frozen bytes are the exact first 36,768 bytes of the
  file (`provenance/D_AUDITOR_DISPOSITION.json`). The D audit run from the
  frozen bytes has one finding, that file's own hash; every row, parity, ledger
  and gate check passes. Nothing was re-hashed. I proceeded to C because no
  measured source changed. Lead to rule.
- **D2: cohort inventory false positive.** My first inventory regex matched
  seed-like digit runs inside hex digests, and `cohort/COHORT.json` says
  DESIGN_INVALID. That file is retained unchanged. The corrected token boundary,
  plus an explicit `additional_98…` name check, finds only the endpoint pair
  (980000, 980199) in plans, protocols, handoffs, constants and tests
  (`cohort/COHORT_CHECKED.json`: VALID). The correction was made before the
  confirmation freeze and before any outcome. Program files were unchanged and
  there was no reseeding.
- **D3: lint left in a frozen file.** The frozen adapter file has one ruff F841
  (an unused local). It was left untouched to preserve the freeze. Two unused
  imports were removed from reporter modules that were not frozen at the time.
- **D4: D ordering.** D rows ran in the parent's global stable-seed order, as
  M2 did. C used the plan's per-program/per-repetition grouping.
- **D5: test re-targeting.** Two auditor mutation tests assumed earlier stage
  states. They were re-targeted, not weakened: the mutations still contradict
  the gates.
- **D6: uncharged smoke runs.** Development smoke calls (2 adapter calls, 8
  worker compiles, 1 C1 export CLI run, about 15 s) were not charged to the
  ledger and are not evidence.
- **D7: transitive-dependency hashes.** Recorded hashes come from the parent's
  starting manifest plus the parent package's LOCK protected inputs
  (`tests_direct/__init__.py` is recorded only in the latter).
- **D8: post-hoc status of M.** The recalibrated M forecast is a post-hoc
  development correction admitted by the lead. The inferential claim rests only
  on the fresh cohort.

## Verification (fresh at the end; outputs in `checks/`)

| Command | Exit |
|---|---:|
| `../venv/bin/python plan/phase2_third_round_resume/verify_package.py` | 0 |
| `PYTHONPATH=.reference:. ../venv/bin/python -s -m research.third_round_resume_audit --resume $R --prediction $R/RECALIBRATED_PREDICTION.json --replay` | 0 (PASS, 18,219 checks) |
| `…third_round_resume_audit.confirmation_audit($R, $R/COMPARISON.json)` | PASS (143,585 checks) |
| `…development_audit($R, $R/DEVELOPMENT.json)` from the frozen bytes | 1 finding (D1) |
| `…pytest -q research_tests/test_third_round_{kernel,audit,resume_audit,resume_stage_d,resume_stage_c,candidate}.py` | 0 (82 passed) |
| `…python -s -m unittest research_tests.test_third_round_candidate_inherited` | 0 (53 tests, 299 s) |
| `../venv/bin/ruff check --output-format=concise` (new files) | 1 (the frozen-file F841, D3) |

## Rerun commands (from `luminal-challenge/`, `R=results/phase2_structural_encoding/third_round_20260925_resume`)

```sh
../venv/bin/python plan/phase2_third_round_resume/verify_package.py
PYTHONPATH=.reference:. ../venv/bin/python -s -m research.third_round_resume_adapter --run $R
PYTHONPATH=.reference:. ../venv/bin/python -s -m research.third_round_resume_stage_d --run $R --stage D_fixed_work   # D_wall, D_memory
PYTHONPATH=.reference:. ../venv/bin/python -s -m research.third_round_resume_export --run $R --stage C_acceptance    # C_export
PYTHONPATH=.reference:. ../venv/bin/python -s -m research.third_round_resume_stage_c --run $R --stage C_fixed_work   # C_wall, C_public
PYTHONPATH=.reference:. ../venv/bin/python -s -m research.third_round_resume_audit --resume $R --prediction $R/RECALIBRATED_PREDICTION.json --replay
```

The runners resume only missing keys and refuse a key that has an attempt but
no row. Every command and log is in `logs/`.

## Deliverables

| Deliverable | File |
|---|---|
| Starting and final manifests | `SOURCE_MANIFESTS/{starting,final}.json` |
| Work log | `WORK_LOG.md` |
| Measurement ledger | `MEASUREMENT_WALL_LEDGER.jsonl` (resume; the parent's is kept in the parent run) |
| Adapter | `ADAPTER_SPEC.json`, `ADAPTER_FREEZE.json` |
| M repair | `RECALIBRATED_PREDICTION.json`, `REPAIR_CLOSURE.json`, `SPEEDUP_ADDENDUM.md` |
| Stage states | `STAGE_STATES.json` |
| Stage D | `DEVELOPMENT_FREEZE.json`, `DEVELOPMENT.json` |
| Stage C | `cohort/COHORT_CHECKED.json`, `CONFIRMATION_FREEZE.json`, `COMPARISON.json` |
| Exports | `exports/{R0,C1}/` |
| C1 candidate | `candidate/` |
| Provenance | `provenance/` |
| Audits | `checks/` |
| Paper handoff | `PAPER_HANDOFF.md` |

Paper revision from accepted evidence follows the lead's review, whatever it
decides.
