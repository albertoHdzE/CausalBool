# RELEASE_HANDOFF: third improvement round (protocol 1.0)

**Status: READY_FOR_CODEX_REVIEW.** Not self-accepted; only Codex accepts.

- **Path:** `luminal-challenge/results/phase2_structural_encoding/third_round_20260925/RELEASE_HANDOFF.md`
- **Implementer and authority:** Claude Code, 2026-09-25. The authorities are
  `plan/CLAUDE_PHASE2_THIRD_ROUND.md` v1.0 and the locked
  `plan/phase2_third_round/PROTOCOL.json`.
- **Package verifier:** PASS at the start and at the end (4 package files, 193
  protected inputs; `final_checks/verify_package.json`).
- **Outcome:** Stage M stops at **NO_JUSTIFIED_MECHANISM**. The registered
  conservative prediction is 0.827, against a gate of ≤ 0.80. C1 was not built,
  and Stages D and C were not run. R0 remains the baseline.
- **The one decision for the lead:** after the outcome I found a scope defect in
  my own registered prediction formula. Corrected, the conservative prediction
  would be 0.742–0.764, which passes the gate. I did not apply the correction
  (see Deviations, D1).
- **Budgets:** measurement process time was **0.117 h** of the 24 h cap (391
  charged processes). Active development was about 0.5 h of the 16 h cap
  (`WORK_LOG.md`).
- **Not done:** no commits, pushes, publication, subagents, process termination,
  production integration or manuscript edits.
  - No pre-existing file changed (`final_checks/FINAL_STATE.json`); git status is
    identical at start and end.
  - Every new file is `research/third_round_*.py`,
    `research_tests/test_third_round_*.py` or this directory.

## Stage verdicts

| Stage | Rows (expected) | Verdict |
|---|---:|---|
| M_diagnosis (M0) | 210 (210), 0 failed | COMPLETE. Instrumentation parity 30/30. Replay fidelity 30/30. |
| M1 nomination | — | One design, `BS1_branch_state_with_change_record` (`MECHANISM_SPEC.json`). Four components: precedence, issue capacity, live/product bounds, address support. |
| M_kernel (M2) | 180 (180), 0 failed | Kernel parity 30/30. Registered conservative ratio **0.827 > 0.80** (point 0.654). **NO_JUSTIFIED_MECHANISM.** |
| D_fixed_work / D_wall / D_memory | 0 (600/600/60) | NOT_RUN: M gate failed (`NOT_RUN.json`). |
| C_acceptance / C_fixed_work / C_wall / C_public / C_export | 0 (284/2000/6000/280/1248) | NOT_RUN: depends on D. The 980000–980199 reservation was not generated or touched by this round. |

## What was found

Details and the per-program table are in `DIAGNOSIS.md`.

1. **Opportunity (M0, counts over 30 development programs).** Most of R0's
   propagation work re-reads facts that have not changed since the parent node:
   - 87.4% of precedence-edge evaluations (only 3.7% fire);
   - 76.9% of issue-capacity scans (7.6% delete anything);
   - 76.1% of per-value compulsory intervals after a child;
   - 84.1% of address-pair evaluations (3.0% fire).

   The earlier whole-input cache measure could not see this.
2. **Mechanism.** Each node holds an immutable branch state that its children
   share. It carries the node's domains, R0's singles snapshot, per-value
   intervals with the peak, and pair incidence. One change record per child
   drives all four consumers. Constraints are evaluated in R0's exact sweep
   order, so certificates are identical by construction.
   - This differs from the next-round worklist E1, which reordered certificates
     and kept the full rule-2 scan and peak.
   - It also differs from the rejected rule-2 filter, which recomputed the
     singles and full sets every sweep and covered one component only.
3. **Kernel (M2).** On the 30 frozen workloads the kernel matches every output,
   every per-call certificate count and the whole stream. It replays the replaced
   work a median **2.39×** faster (range 0.92–4.36×).

   The prediction is `(T0 − O + 1.5N)/T0`, equal-family geometric mean:

   | | Conservative ratio |
   |---|---:|
   | Registered | 0.827 |
   | Gate | ≤ 0.80 |
   | Family: scalar | 0.874 |
   | Family: vector | 0.771 |
   | Family: mixed | 0.749 |
   | Family: dependency | 0.959 |
   | Family: aliasing | 0.798 |

   Small programs (for example 800023, 13 events) predict ratios above 1.

## Deviations and disclosures

- **D1: prediction scope defect, found after the outcome, not applied.**
  - **The defect.** `MECHANISM_SPEC.json` defines `O = min(replay median,
    timer-exclusive replaced / inflation)`. The timer arm leaves out certificate
    emission, `Propagation.__init__` and `address_pairs`. Those are charged to
    other owners in the timer map, but they are included in `N`, because the
    kernel re-performs them identically. `min()` chose the timer arm on 30/30
    programs, so unchanged work was counted in N but not in O.
  - **Evidence of scope.** The replay median divided by the scope-matched timer
    estimate lies in [0.90, 1.07].
  - **Corrected results.** The conservative ratio would be 0.742 (`O` = replay)
    or 0.764 (`O` = min of replay and scope-matched timer).
  - **Why it was not applied.** Plan §3/§6 forbid changing a gate computation
    after its outcome, so the registered verdict stands.
  - **Request.** Rule whether the corrected computation is admissible. If it is,
    Stage D can start from the frozen kernel with its protocol unchanged; see the
    rerun commands below.
- **D2: kernel draft written before the spec.** An unexecuted draft of
  `research/third_round_kernel.py` was written while M0 rows were being measured,
  before `MECHANISM_SPEC.json`. The spec records its hash at that moment. The
  kernel was first imported and run after the spec was written. The first
  parity run passed with no change (`KERNEL_ATTEMPTS.jsonl`).
- **D3: lint change after measurement.** `research/third_round_common.py` lost
  three unused typing imports after the M stages (ruff F401). There is no
  behaviour change; see `POST_MEASUREMENT_CHANGES.json`.
- **D4: preflight.** 30 plain compiles in one process (16 s, ledger stage
  `M_preflight`) were run only to size the 20 s timeout. The largest took 2.18 s.
  These are not evidence.
- **D5: one mutation probe replaced.** The planted "child writes into
  `parent.D`" contamination is benign for this kernel: a stale `old` domain
  only enlarges the dirty set. It was replaced by contamination of the shared
  singles map, which is caught. The observation is kept in the test docstring.
- **D6: a stage without a runner.** `M_preflight` appears in the ledger but has
  no expected-key file; it is not a protocol stage.
- **Scope of `O`/`N`:** both are development-model inputs from a replay of
  captured work. They are not compile-call measurements.

## Verification (fresh at the end, exit codes retained in `final_checks/`)

| Check | Result |
|---|---|
| `verify_package.py` | PASS, exit 0 |
| New tests: `research_tests/test_third_round_{kernel,audit}.py` | 26 passed, exit 0 |
| Independent auditor/checker `research.third_round_audit` | PASS: 395 numerical + 80 identity checks, 0 findings, exit 0 |
| Auditor mutations: fabricated ratio, false PASS, changed field, missing/duplicate/failed/torn row, parity false, wrong family weight, tampered workload, started dependent stage | all rejected (in the 26 tests) |
| Kernel mutations: stale domain summary, omitted consumer dependency, stale singles, sibling contamination, stale incumbent, stale address support | all caught |
| ruff (concise) on new files | clean |
| R0 source and export hashes | unchanged (`d0fcd441…`, `74c87b69…`) |

The inherited R0 semantic suite was not rerun: no candidate exists to bind it
to, and R0 is unchanged.

## Rerun commands (from `luminal-challenge/`)

```sh
../venv/bin/python plan/phase2_third_round/verify_package.py
R=results/phase2_structural_encoding/third_round_20260925
# M0 (resumes only missing keys; complete now)
PYTHONPATH=.reference:. ../venv/bin/python -s -m research.third_round_diagnosis --run $R
# M2 kernel rows
PYTHONPATH=.reference:. ../venv/bin/python -s -m research.third_round_mkernel --run $R
# Reporter prediction and independent audit
PYTHONPATH=.reference:. ../venv/bin/python -s -c "from pathlib import Path; from research import third_round_analysis as a; print(a.prediction(Path('$R'))['predicted_ratio_conservative_equal_family'])"
PYTHONPATH=.reference:. ../venv/bin/python -s -m research.third_round_audit --run $R
PYTHONPATH=.reference:. ../venv/bin/python -s -m pytest -q --tb=short -p no:cacheprovider research_tests/test_third_round_kernel.py research_tests/test_third_round_audit.py
```

## Deliverables

| Deliverable | File |
|---|---|
| Starting and final manifests | `SOURCE_MANIFESTS/{starting,final}.json` |
| Work log | `WORK_LOG.md` |
| Measurement ledger | `MEASUREMENT_WALL_LEDGER.jsonl` |
| Diagnosis | `DIAGNOSIS.md`, `DIAGNOSIS.json` |
| Cost-ownership and dependency map | `COST_OWNERSHIP.json` |
| Workload hashes | `WORKLOAD_MANIFEST.json` |
| Mechanism specification | `MECHANISM_SPEC.json` |
| Kernel parity, timing and prediction | `stages/M_kernel/`, `KERNEL_ATTEMPTS.jsonl`, `PREDICTION.json` |
| Mechanism decision | `MECHANISM_DECISION.json` |
| Explicit NOT_RUN reasons | `NOT_RUN.json` |
| Paper handoff | `PAPER_HANDOFF.md` |
| Stage rows, frozen keys and attempt ledgers | `stages/M_*/` |
| Commands and logs | `logs/` |

No fourth round is automatic. After lead review, the planned next activity is
paper revision from accepted evidence (`PAPER_HANDOFF.md`).
