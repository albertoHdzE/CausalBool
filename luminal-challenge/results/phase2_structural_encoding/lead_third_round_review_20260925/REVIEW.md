# Third-round lead review and continuation ruling

2026-09-25 · Codex · `third_round_20260925` · protocol 1.0.

**CHANGES_REQUIRED.** The development kernel is promising and its retained
parity evidence reproduces. Neither an accepted compiler candidate nor a sound
negative mechanism conclusion has been established. R0 remains accepted and
unchanged. Do not move this round's result into the paper as an established
compiler speedup or an adequately justified rejection of the mechanism.

## Ruling on the disclosed accounting error

**Correct the scope mismatch; the correction is admissible as explicitly
post-hoc development accounting.** This does not lower a threshold or alter
fresh confirmation. The 30 programs are development inputs, no integrated C1
outcome exists, and the reserved confirmation cohort remains unmeasured.
Preserve the original formula, 0.8268222321783514 result and stop record.

The timed kernel includes `Propagation.__init__`, `address_pairs` and certificate
emission. The old timer contribution subtracted as O excludes those costs.
Adding the complete new replay cost N therefore charges overlapping work twice.
This mismatch is visible in the source and cost-ownership map independently of
which side of 0.80 its correction falls on.

My stdlib arithmetic over the retained raw rows reproduces:

| Conservative prediction | Ratio |
|---|---:|
| Original mismatched-scope O | 0.8268222321783514 |
| O = min(replay median, scope-matched deflated timer) | 0.7638230784259178 |
| O = replay median (sensitivity only) | 0.7422848903946956 |

For the continuation, use the **scope-matched minimum**, with exactly the old
component set plus `certificates`, `propagation_setup` and `address_pairs`.
Keep the 1.5× N sensitivity and <=0.80 gate. Do not choose whichever formula
looks best. These predictions are not measured compile-call ratios or confidence
bounds. The original `NO_JUSTIFIED_MECHANISM` is a historical registered result,
not the final substantive judgment once its model defect is known.

## Required repairs before Stage D

**R1 — the integration-overhead claim is unsupported.**
`third_round_mkernel.integration_estimate` times a loop calling `_adapter(holder)`,
which only reads and returns `holder.D`. It does not write a node slot, although
the spec describes a slot write plus dispatch. It is not demonstrated to be an
upper estimate of the actual adapter costs. Measure the minimal real adapter
operations, including state-reference writes/reads and release, and enumerate
any remaining integration costs. Include an explicit upper estimate for those
that cannot yet be measured. Recompute the corrected model with that evidence;
do not authorize integration merely because 0.764 is favorable.

**R2 — the auditor does not enforce several prerequisites it relies on.**
The unmodified auditor returns PASS on each of these lead mutations:

1. Append an extra malformed JSONL fragment after all 180 valid kernel rows.
   Its shared `optimization_common.read_rows` silently ignores the final fragment.
   The existing test truncates/replaces an expected row, so it catches missing
   membership without demonstrating rejection of a torn extra row.
2. Replace the measured kernel's hash in `WORKLOAD_MANIFEST.kernel_stage_sources`
   with 64 zeros. `identity_check` never compares those recorded source hashes
   with source bytes. Assignment checks protect old inputs, not all new measured
   third-round modules.
3. Set a raw M0 `instrumentation_parity` result to false. Neither numerical nor
   identity audit checks M0 parity/fingerprint agreement.
4. Remove `NOT_RUN.json`. The checker reads only the dependent labels embedded
   in MECHANISM_DECISION and never checks the required separate stage record.

See executable `probes.py` and `PROBES.json`. No worker artifact was modified;
mutations used temporary copies. The unchanged auditor reports 395 numerical
and 80 identity checks and passes its existing tests; these facts do not close
the demonstrated gaps. A successor must derive expected membership from protocol
and generator, enforce source identity, strict row parsing and all prerequisite
parity, and have a field-to-check map. Missing or contradictory evidence must
block a gate. Test the exact mutations above, including appended torn rows.

**R3 — correct the handoff's kernel-speedup summary.** The median of the 30
reported per-program `baseline replay median / shared replay median` values is
**2.3649168298633314**, not 2.3947613512067907. The range 0.9201184423–4.3607856514
reproduces. Correct this in a new handoff/addendum, preserving historical text.
This summary discrepancy does not explain the gate result; its aggregation must
still be accurate before a paper claim uses it.

## Provenance dispositions and other limits

- **Kernel-before-spec deviation:** retain it as a deviation from M1. The source
  hash in the specification is the exact first 17,377 bytes of the measured
  kernel file. The suffix adds the replay driver; the shared-state class bodies
  match the earlier draft. The one retained parity attempt names the measured
  file. This supports keeping the mechanism as exploratory development, not
  claiming that the required spec-before-code order was followed. Do not demand
  a new mechanism or retroactively rewrite the specification.
- **Post-measurement typing-import edit:** I reconstructed the old common-module
  bytes by restoring exactly `Callable, Iterable, List` to the one typing import.
  Their SHA256 matches the recorded freeze. This exact pair is a narrow accepted
  diagnostic provenance deviation. No other source drift may be waived by code
  or filename alone. Retain both byte versions in the continuation.
- **Raw stdout:** original worker stdout files were not kept. I reconstructed
  all 390 JSON stdout payloads from row fields; every digest matches its finished
  attempt record. This supports the retained row payloads, but does not turn the
  historical files into original raw logs. Future measurements must retain full
  stdout/stderr, including failures.
- **Preflight:** the 30 batched plain compiles were disclosed and charged as one
  process. Keep them outside the 210/180 matrices and all reported timing ratios.
  Smoke tests and provenance statements remain historical; do not claim perfect
  compliance with every planned measurement procedure.
- Whole-workload replay cannot establish complete compiler parity, deadline
  safety, state lifetime, memory behavior or speedup. The original Stage D tests
  and complete development/confirmation matrices remain mandatory.

## Independent verification performed

| Verification | Result |
|---|---|
| Locked assignment | PASS: 4 package files / 193 protected inputs |
| New kernel/audit tests | 26 passed, no skips, exit 0 |
| Unchanged worker auditor | PASS: 395 numerical / 80 identity checks; limitations above |
| Fresh baseline and shared replay | Both match all 30 captures, 829,993 events; output/emission lengths and certificate stream checked |
| Source/code audit | Only the disclosed typing-import drift relative to M2 freeze |
| Arithmetic | Original and both corrected-scope ratios independently reproduced |
| Raw row checks | All 390 row program hashes match the generator; 390 stdout hashes reproduced |
| Reuse-count aggregation | 87.3847% edge, 76.8586% capacity, 76.0900% interval and 84.0768% address-pair unchanged-input fractions reproduced |
| Negative mutation controls | Four auditor false-PASS cases reproduced |

These are correctness and evidence checks, not newly measured performance claims.
No full compiler candidate was created; no confirmation programs were generated;
no frozen source, production or manuscript was changed by this review.

## Next action

Finish the **same third round**, under the scoped continuation package
`plan/phase2_third_round_resume/CLAUDE_PROMPT.md`. First close R1–R3 and re-evaluate
the one fixed accounting formula. Only if the repaired M gate passes may Claude
integrate the already nominated kernel as C1 and run the original D/C gates.
One design/candidate, the original targets, fresh cohort, measurement cap and
paper transition remain unchanged. This is not a fourth improvement campaign.

If the repaired model fails or cannot be justified, stop with that supported
result. Otherwise finish D/C as authorized. Then submit a corrected paper evidence
handoff for lead review. A paper revision should not inherit the current false
assurance claims or ambiguous negative verdict.
