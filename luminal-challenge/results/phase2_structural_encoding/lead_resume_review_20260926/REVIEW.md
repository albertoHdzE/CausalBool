# Third-round resume: lead review and acceptance ruling

2026-09-26 · `third_round_20260925_resume` · protocol 1.0 (resume) under the parent
third-round protocol · pivot tag `pivot/luminal-phase2-third-round-20260926` (commit `9489a15`).

**ACCEPTED, with two documentation errata and three paper qualifications.**

- C1 replaces R0 as the accepted baseline of the direct-index compiler.
- The confirmation result is reproduced from the raw rows.
- The gate is met with a wide margin.
- No finding touches the measured evidence.

## Independence of this review

Codex, the designated lead, was unavailable. The author authorised Claude Code
to complete the review. The reviewer is therefore also the implementer: this is
a **self-review**, and it must be cited as such. Four measures limit the
conflict:

1. **Fresh code.** Every endpoint was recomputed by new standard-library code
   (`recompute.py`, `recompute_m.py`). It imports neither the reporter nor the
   auditor.
2. **The challenge's evaluator.** Every exported compilation was re-validated
   with `.reference/machine.py`, the challenge's own evaluator.
3. **RNG independence.** The bootstrap was repeated under three further seeds.
4. **Probes beyond the protocol.** These looked for order effects, drift, timer
   scope, heterogeneity and wall-mode trajectory effects.

The review found two errors in the implementer's own handoff (E1, E2). Evidence
that is later re-reviewed by an independent party supersedes this ruling.

## Ruling

| Item | Ruling |
|---|---|
| R1–R3 (lead review, 2026-09-25) | **Closed.** The repaired M gate reproduces exactly from the 90 raw adapter rows: point 0.6061181323165558, conservative 0.78643064888711 ≤ 0.80. |
| Stage D | **PASS stands.** The D audit gives identical results under the frozen and the current auditor (see E2). |
| Stage C | **SUCCESS stands.** Cost 0.5743 [0.5518, 0.5978] ≤ 0.80; quality 0.9908 [0.9846, 0.9964] ≤ 1.01; exact fixed-work parity on 1,000/1,000 pairs. |
| D1 (auditor append after the D freeze) | **Accepted as a provenance deviation**, with the corrected description in E2. It has no effect on any gate. |
| D2–D8 | Accepted as disclosed. |
| C1 | **Accepted.** It becomes the reference solver for any later round. R0 is retained as the historical baseline. |
| Paper | May now be revised from this evidence, within the qualifications Q1–Q3 and the limits in `PAPER_HANDOFF.md`. |

## Errata (documentation only; historical text preserved, not edited)

**E1 — wrong C1 hash in `RELEASE_HANDOFF.md`, repeated in commit `9489a15`'s message.**

- The prose gives `5ccbaaa3128c…`. That string matches no file and no record in
  the repository.
- The measured C1 is **`b9697640e202c7cf2563ef3f11423f6cbd52403f91c897b62a6ab1b044672cfa`**.
  This value appears in both freezes, the final source manifest and the export
  manifest, and it matches the current file and the committed blob.
- Every other hash quoted in the handoffs resolves.
- The error is a transcription error, not source drift. The confirmation freeze
  holds for all 40 of its sources.

**E2 — the D1 disclosure is no longer accurate.**

- The handoff says that no D function changed and that the frozen D auditor is
  the exact first 36,768 bytes of the current file. That was true at disposition
  time (file `d226a2ba…`).
- A later edit, made before the confirmation freeze (file `3270aa41…`), changed
  two places inside that prefix:
  - the shared raw-stream check gained a `raw_streams == "cli"` branch for C
    export rows;
  - one line of the D field-map check was reflowed.
- `D_AUDIT_BOTH.json` runs `development_audit` from both files. The frozen and
  the current auditor each give 32,362 checks, and the only finding is the
  frozen file's own hash. The edit is therefore behaviour-preserving for D.
- The check count differs from the handoff's 22,550, most likely because the
  shared ledger grew during Stage C; the review did not verify this. Neither
  count indicates any failure.

## Independent verification

| Verification | Result |
|---|---|
| Package verifier | exit 0 |
| Tests | 82 pytest (kernel, audits, stage D/C, candidate) and 53 inherited semantic tests: all pass |
| Row completeness | 2,000 / 6,000 / 280 / 1,248 / 284 rows, none failed, timed out or incorrect |
| Raw streams | 9,528 stdout files hash to their rows. Every in-process payload equals its row. |
| Exported compilers | 1,248/1,248 re-validated on every case by `.reference/machine.py`; cycles, scratch and J equal the rows |
| Cohort | 200 program files re-hashed (0 mismatches), 40 per family. None of the 600 cohort hashes (program, file, compilation input) occurs in any of 5,733 earlier result files (2.97 GB; `COHORT_SCAN.txt`) |
| Freezes | Confirmation: 40/40 sources unchanged. Development: only the auditor changed (E2). |
| Point estimates | Cost and quality equal `COMPARISON.json` to machine precision |
| Bootstrap | The seed 2026092802 interval reproduces exactly. Seeds 1–3 give cost upper bounds ≤ 0.5985 and quality upper bounds ≤ 0.9964. |
| Public scores | Reproduced exactly: 2.188 for both arms at 0.1 s and 1 s; 2.135 (C1) vs 2.081 (R0) at 0.01 s |
| Parity content | 196 distinct search traces over 200 programs; median 31,848 certificates per run. Five programs need no search (0 nodes), so 975 of the 1,000 pairs are substantive. |

## Probes beyond the protocol (`RECOMPUTE.json` → `probes`)

**Timer scope.**

- The timed call contains the shared base compile, contract derivation and
  trace recording in both arms. These are equal absolute costs, so they pull the
  ratio towards 1.
- The solver-module import lies outside every timer. Adding the recorded import
  time gives 0.601. Whole-process wall time, including interpreter start, gives
  **0.649**.
- The claim holds at every scope.

**Order and drift.**

| Split | Pairs | Cost ratio |
|---|---:|---:|
| R0 ran first | 539 | 0.572 |
| C1 ran first | 461 | 0.577 |

Across time quartiles the ratio is 0.567, 0.538, 0.598 and 0.597, with no
trend. There is no order artefact.

**Heterogeneity.**

- Per-program cost ratios: min 0.264, 10th percentile 0.427, median 0.554,
  90th percentile 0.878, max 1.076. C1 is slower on 7 of 200 programs.
- By search size:

  | Search size | Programs | R0 median | Cost ratio |
  |---|---:|---:|---:|
  | Smallest third (0–493 nodes) | 67 | 18 ms | 0.730 |
  | Middle third | 67 | 0.38 s | 0.527 |
  | Largest third (node cap) | 66 | 1.13 s | 0.491 |

- Summed seconds give a ratio of 0.464. The saving grows with search size,
  which is what a mechanism that reuses parent facts per node predicts.

**Model calibration.**

- The development point forecast was 0.606, a post-hoc repair.
- The measured ratios are 0.589 on the development programs and 0.574 on the
  fresh cohort.
- The conservative 0.786 was conservative, as intended.

## Paper qualifications (binding on the revision)

**Q1 — per-program quality is not monotone in speed.**

- The mechanism is R0's controller (`research/efficiency_search.py:2072-2102`):
  - eight resident queries run round-robin in slices of 2 ms or 2,048 nodes;
  - the first strict improvement ends its epoch;
  - the search is therefore greedy first-improvement.
- Under a real clock, C1 expands more nodes per slice, so a different query can
  win an epoch and the search follows a different path.
- The effect at 1 s:
  - C1 loses 17 of 1,000 paired runs, spread over 4 programs.
  - C1 is deterministic across repetitions on those programs.
  - Ten of those losses have no unknown query on either side.
  - On seeds 980026 and 980183, C1 finishes the pass with fewer nodes and a
    worse J (1440 vs 1280; 924 vs 726).
- At 0.1 s all 6 losses involve unknown queries.
- The quality claim is therefore distributional: 25 programs better, 173 equal
  and 2 worse at 0.1 s. The paper must say "decision parity at equal work".
  It must not say "identical decisions" or "never worse" under a wall budget.
- Wall-mode compile-call time is not greater for C1: the geometric ratio is
  0.984, 0.854 and 0.755 at 0.01, 0.1 and 1 s. The quality gain is not bought
  with extra time.

**Q2 — scope of the speed claim.**

- The claim is an engineering property of this Python implementation at equal
  search work, measured on one local machine.
- It is not an algorithmic complexity result, a private-grader result or a
  runtime comparison with classical compilation. Earlier accepted reviews found
  classical compilation much faster, about 7×, in compile time.

**Q3 — memory.**

- The tracemalloc peak ratio is a median of 1.051 and a maximum of 1.302.
- It was measured only on 30 development programs; no confirmation-cohort
  memory measurement exists.
- It must be reported as a development observation, not as a cost-free
  improvement.

## Not done

- No production source, frozen file, earlier run or manuscript was changed by
  this review.
- The review's outputs are confined to this directory.
- The inherited earlier failures (E1 worklist, rule-2 filter, original BS1
  registration, the next round's TARGET_NOT_REACHED) remain in the record and
  must stay in the paper.

## Files

| File | Content |
|---|---|
| `recompute.py` | Independent recomputation of the endpoints and the probes |
| `RECOMPUTE.json` | Output of `recompute.py` |
| `recompute_m.py` | Independent re-derivation of the repaired M gate |
| `RECOMPUTE_M.json` | Output of `recompute_m.py` |
| `d_audit_both.py` | D audit from the frozen and the current auditor |
| `D_AUDIT_BOTH.json` | Output of `d_audit_both.py` |
| `VERIFY_PACKAGE.log`, `PYTEST.log`, `INHERITED.log` | Fresh verification logs |
| `COHORT_SCAN.txt` | Cohort hashes found in any earlier run |

Rerun from `luminal-challenge/`:

```sh
python3 results/phase2_structural_encoding/lead_resume_review_20260926/recompute.py
python3 results/phase2_structural_encoding/lead_resume_review_20260926/recompute_m.py
```
