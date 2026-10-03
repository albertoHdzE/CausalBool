# Supervisor decision: confirm-v1-r1

Date: 2026-10-02. Reviewed `hierarchy/HANDOFF_CORRECTIONS.md` and freeze
`f970efff16a2d08bf1dd22eee1386c164af5ba67b22137fefcf06cd182b27f5c`.

**Frozen experiment and numerical findings: accepted, with the scope below.**
**Unqualified software handoff / complete closure of R1: changes still requested.**

The distinction is deliberate. The retained study is complete, its archives are
correct, and its results reproduce. Three remaining validator cases do not occur
in this run, but the claim that R1 is fully resolved is too broad. They should be
closed before reusing the pipeline for another study. No additional compression
experiment is requested to establish the already verified numerical findings.

## 1. Independent checks completed

- **317 tests passed** in 28.38 s: package tests plus the shared description-length
  owner tests. Production package and the new supervisor audit script pass ruff.
- All **1,632 strings and 26,112 case/method rows** match the complete declared
  design. All statuses are `ok`. All individual row files contain exactly the
  sixteen unique methods; no out-of-design rows are present.
- All **16,402 distinct archives** decode to regenerated inputs. Every row's hash,
  byte length, selected codec, raw upper bound and portfolio selection checks out.
- Every retained archive byte and every deterministic row field agrees with
  `confirm-v1`. The archive manifests are byte-identical. No cases were dropped.
- An independent implementation of the prespecified arithmetic/bootstrap reproduces
  the primary, five ablation, transfer and all-family results, exactly matching the
  earlier supervisor audit's output. It does not use `hierarchy.report` for its
  numerical calculations.
- Search configs, restricted oracle config, baselines, corpus/seed specification,
  expected counts, resource policy, environment, methods and protocol hashes are
  unchanged between freezes. The source changes match the correction scope.
- The original source archive's SHA-256 and its 22 source/protocol/documentation
  file hashes match the original freeze. It preserves the old implementation.
- The stored BDM diagnostic objects match the original diagnostic objects except
  for freeze identity and runtime. The previous supervisor review independently
  regenerated/ranked those scores; that calculation was not rerun again here.

The new audit is `experiments/review_hierarchy_corrections.py`. Its outputs are
under `results/hierarchy_v1_supervision/confirm-v1-r1/`:
`audit.json`, `replay_audit.json`, and `source_changes.diff`.

I did not rerun all encoders, overwrite either run's verification record, or change
frozen sources. The archive/corpus checks reuse the inspected production decoder
and generator; they are not an independent formal implementation of both. Developer
logs and differing timing fields support a new execution, but retained artifacts
alone cannot independently prove the historical act of running every process.

## 2. Accepted scientific reading

The primary saving is **−0.0446156382 bits per input bit**, with 95% interval
**[−0.0536775270, −0.0358242637]**, over 21 cells / 420 paired units / 840 strings.
HID therefore uses more bits than the baseline portfolio on this prespecified
population. The denominator is input length, not compressed archive length.

All five ablation increments remain positive with the prespecified 99% intervals.
These compare configured search algorithms under the fixed budget. They do not
prove language-intrinsic component contributions or overcome the negative portfolio
comparison. The transfer aggregate remains negative and descriptive.

The replay is **not independent replication evidence** and creates no new holdout.
Statements that families/seeds were unused “before the freeze” refer to the
**original confirm-v1 freeze**, not the replay freeze: their results were already
known by the time confirm-v1-r1 was frozen. The handoff and amendment correctly
state this distinction; read abbreviated ledger wording in that context.

The 65,536-bit length was exercised during development. The boundary-assisted F12
witness remains a post-hoc diagnostic only. Neither caveat is erased by replay.
No claim of Kolmogorov complexity, causal identification, recovery of the true
generator, prediction, or universal generalization is accepted.

Correction to my own bitacora35 §4: F09 loses against the two statistical codes on
**118/120** strings and ties on **2/120**, rather than losing on all 120. There are
zero HID wins. The original mean and scientific conclusion are unchanged. The
corrected handoff's counts are right.

## 3. R1–R5 disposition

| Item | Disposition |
|---|---|
| R1: design and verdict integrity | Original false-positive/negative-gate defects fixed; remaining cases below prevent unconditional closure |
| R2: semantic mismatch | Resolved: raises `CandidateExpansionMismatch`; real subprocess fault test records error, without raw success fallback |
| R3: claims and estimands | Resolved for this study: C4/C5 now name the actual superiority comparisons; search/language attribution narrowed |
| R4: development scope | Resolved: oversized development probes and transfer limitations disclosed |
| R5: environment | Resolved within the requested policy: relevant recorded fields enforced by purpose; offline verification reports its environment |

The existing `.kilo` single-engine guard issue is not a new stage failure. The
outdated command example in a frozen docstring and the decision not to run
`make ci-local` are not grounds to invalidate these scientific results. Do not
edit a frozen source merely to update an example command.

## 4. Three remaining validator cases (medium severity for pipeline reuse)

Each was reproduced with the actual tiny-run fixtures and real production calls in
temporary directories. **Three reproduction tests passed**, meaning they exhibited
the defects; this is not a claim that three acceptance tests passed. The artifact
`test_retained_validator_edges.py` preserves the reproductions, and
`validator_edge_reproductions.json` records the outcomes.

### R1a: missing archive crashes verification after detection

`validation.validate_study` correctly records `archive file missing`. Subsequently,
`cli.cmd_verify` calls `_separate_process_sample`, which attempts an unconditional
`shutil.copy` of the missing file and raises `FileNotFoundError`. Verification never
finishes its structured invalid report/exit-2 path, and any old verification record
may remain on disk. `report.representative_ledgers` also reads chosen archive files
without guarding missing/malformed artifacts.

This is fail-stop, not a successful false validation. It nevertheless violates
the documented behavior for a missing artifact and can leave stale status files.
Handle expected artifact failures in presentation/sample layers, retaining the
validator's reasons and exit state. Do not catch arbitrary programmer exceptions
and present success.

### R1b: duplicates in individual row files disappear

`validation.validate_run` reconstructs each `rows/<case_id>.json` using a dictionary
comprehension keyed by method. Appending a second identical row to that file, while
leaving `cases.jsonl` unchanged, still returns engineering-valid and complete.
The merged JSONL duplicate check is good; the independent row-file check needs its
own exact length and unique-key validation before dictionary construction.

### R1c: undeclared split rows are ignored

`validation.validate_run` filters JSONL rows to requested splits before calling
the exact-design validator. An additional row marked `split="undeclared"` is
silently removed, and production validation returns valid/complete with no unknown
rows. In production, a run declares its whole split set; validate all its rows
against that set. If subset inspection is useful, make it explicit and label it
partial so it cannot become whole-study acceptance.

**Impact on confirm-v1-r1:** none found. The independent audit checked exact complete
membership, existing archives and unique per-file keys, bypassing all three gaps.
These findings restrict approval of the reusable validator, not the observed
negative estimate or the retained archive correctness.

## 5. Bounded next action

The remaining assignment is [KICKOFF_hierarchy_validator_closure.md](../KICKOFF_hierarchy_validator_closure.md).
It asks for a reviewable patch and regression tests in an isolated copy, **not** a
third encoding benchmark or edits to a frozen run. Only validation/presentation
error handling is in scope. Freeze/provenance handling for applying that patch is
a separate supervisor decision after the patch is reviewed; do not claim a patched
tree matches the old freeze.

The next scientific direction remains a separate proposal: measure feasible
description cost versus automatically found cost before assuming a new language
operator is necessary. Do not tune on this replay or count it as new evidence.
