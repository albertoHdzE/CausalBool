# Supervisor review: confirm-v1

Date: 2026-10-02. Reviewed handoff: `hierarchy/HANDOFF.md`.
Disposition: **REQUEST CHANGES for final engineering/claim acceptance; retain the
reproduced negative numerical result as evidence about the frozen implementation.**

This is a source/evidence review, not a demand for positive findings. I have not
changed the frozen package, protocol, original archives, rows, freeze, or reports.
The corrective assignment is [KICKOFF_hierarchy_v1_corrections.md](../KICKOFF_hierarchy_v1_corrections.md).

## 1. What independently checks out

The supervisor audit verified all 1,632 planned strings and all 26,112 method rows
(23,040 confirmation; 3,072 transfer), including exact case/method membership,
no duplicates, row-file/JSONL agreement, source/protocol hashes, original delegation
hashes, archive hashes, measured byte lengths, raw upper bounds, and baseline
portfolio selection. All **16,402 distinct archives** decode to the regenerated
input hashes. All recorded statuses are `ok`.

The 285 package/shared-owner tests passed independently in 19.60 seconds. The
statistical reimplementation uses the complete prespecified Cartesian design and
does not call `hierarchy.report` for its arithmetic or bootstrap. Results match:

| Endpoint | Estimate, bits saved per input bit | Interval |
|---|---:|---|
| Structured confirmation, portfolio minus full | -0.0446156382 | 95% [-0.0536775270, -0.0358242637] |
| no_schema minus full | +0.0089568286 | 99% [+0.0059536690, +0.0121072898] |
| no_arithmetic minus full | +0.0392325019 | 99% [+0.0335290773, +0.0451448700] |
| no_transform minus full | +0.0018777612 | 99% [+0.0014804041, +0.0022726859] |
| flat minus full | +0.2636049256 | 99% [+0.2434811220, +0.2825125703] |
| fixed8 minus full | +0.0115240741 | 99% [+0.0067012915, +0.0166768667] |
| Structured transfer, descriptive | -0.0627969551 | 95% [-0.0768953593, -0.0485332320] |

Thus the deployed full method costs, on average, **0.04462 additional bits per
input bit** versus the portfolio in the primary population. This is not a 4.46%
relative increase in compressed file size: the denominator is input length.
There are 21 primary cells, 420 paired units and 840 strings.

BDM scores were regenerated through the inspected shared owner and null generator.
An independent inclusive-rank/minimum-rank/Holm calculation reproduces all ten
adaptive p-values and corrections. BDM remains a separate diagnostic, not a code
length or evidence of prediction. The re-audit retains the full score matrices.

Review limits: decoding and corpus regeneration reuse the inspected production
decoder/generator; this is not a formal proof or a second fully independent
codec/generator implementation. The complete encoding benchmark has not been
rerun by the supervisor. The test run does not erase the defects below.

## 2. R1 — reporting and verification must fail closed (high)

Locations: `hierarchy/report.py:57,105,146,222` and `hierarchy/cli.py:193,213,242`.

Reproduction: retain only both lengths for confirmation/F04/1024/replicate1000,
with all its methods, and call the current summary with the declared 1,440-string
confirmation design. It reports:

```text
primary.verdict = supported
primary.cells = 1                 # required 21
primary.units = 1                 # required 420
primary.units_missing = []
status_counts.confirmation.hid_full.absent = 1438
```

`cells_matrix` discovers units only from present rows, so wholly missing units do
not enter its missing list. `cmd_report` records `study_complete` separately but
does not gate the scientific verdict with it. Duplicate method rows are silently
overwritten by dictionary indexing. Ablation support likewise ignores missingness
and engineering validity. A separate fault is that `verdict((-.2,-.1), False, True)`
and the engineering-invalid equivalent both return `not_supported`: the negative
branch runs before validity gates.

The verifier also skips a row with a null `archive_path` even if its status is
`ok`, skips archive decoding for `baseline_best`, and checks method count rather
than exact membership. These are source-inspection findings; I did not mutate
the frozen run to exercise them. Checking only portfolio size does not prove that
the selected archive actually equals the winning constituent archive.

Required: validate the exact declared design and unique method keys first; use
explicit validity/completeness gates for primary and component claims; validate
every required archive and portfolio identity. Censoring must override either
direction of a confidence interval. Distinguish invalid engineering, incomplete
study, and scientifically inconclusive findings. The valid, complete negative
study must still pass engineering verification.

**Effect on this run:** none found in the retained numbers; the independent audit
verified completeness and archives without relying on these gates. This is a
reusable research-software correctness defect, not evidence that the present
negative estimate is fabricated or incomplete.

## 3. R2 — candidate semantic mismatch is silently suppressed (medium)

Location: `hierarchy/infer.py:214`.

`_Search.consider` increments `rejected_verify` and returns when a proposed graph
has the right length but the wrong expansion. A fault-injection reproduction
confirms no exception is raised. This conflicts with SEARCH_SPEC's promise that
a mismatch is an engineering failure, never a silent fallback. Expected cap or
arm-language rejection is different from an internally generated wrong string.

Required: fail with a precise exception for this semantic mismatch, carry the
error through worker/runner/verification, and test that a completed raw result
cannot conceal it. Keep legitimate timeout/resource fallbacks and cap rejections.
All retained rows have `rejected_verify=0`, so this defect has no observed effect
on the original result.

## 4. R3 — claims must match their actual estimands (medium)

Locations: `hierarchy/report.py:433-448`, SEARCH_SPEC §8, HANDOFF §8 and generated
claim tables in bitacora34/notebook16.

**Controls claim C5:** its endpoint compares against the nine-code portfolio,
but its prose claims no advantage over statistical baselines on all three control
families. Against the minimum of the actual Bernoulli/context codes, HID is
shorter on **117/120 F07 confirmation strings**, with descriptive average saving
+0.0179785334 bits/input bit. It loses on all 120 F08 and all 120 F09 strings.
Raw fallback and code overhead explain why this comparison differs; this is not
a claim that HID discovers fair-random structure. Rewrite C5 as the measured
equal-weight **aggregate portfolio comparison**. An aggregate also does not prove
every individual family satisfies the same assertion. Do not infer equivalence
from failure to establish superiority.

**Search versus language:** SEARCH_SPEC §8 calls losses “all language limitations
rather than search failures.” The handoff is more nuanced, but still mixes wire
overhead, search caps and segmentation policy as causes. No large-instance optimum
has been computed, so this causal attribution is not established.

A concrete diagnostic makes the distinction material. For
`transfer-F12-65536-2000-base`, a legal archive in the **unchanged** HID language
using literal/concat/repeat has:

| Description | Complete archive bits |
|---|---:|
| Frozen automatic full search | 28,528 |
| Winning baseline | 23,240 |
| Supervisor boundary-assisted witness | 22,480 |

The witness has 15 rules, depth 4 and exact independent decoding. It uses known
construction boundaries `[0,13107,13108,21847,43693,52431,65536]`, with all lengths,
references and literal bits transmitted. It establishes a **6,048-bit gap between
the search result and a feasible description**, not an optimality certificate.
It is post hoc and metadata-assisted: exclude it from every benchmark result,
automatic recovery claim and confirmatory comparison. It does not demonstrate
that a practical metadata-free search will find the archive under the budget.

Required: distinguish representational cost from search failure, state “best found
under the frozen budget,” and remove unsupported causal certainty. C4 should
explicitly test a positive portfolio saving at larger sizes, not the ambiguous
phrase “the result transfers.” An entropy-coded leaf/reference stream requires a
new wire specification/version; it cannot be added while claiming unchanged W3.

## 5. R4 — disclose expanded development scope (medium)

SEARCH_SPEC §7 explicitly records tuning the work cap using `development_resource`
strings at **65,536 bits** and selecting a setting partly from encoded length
(F06 11,992 -> 11,720 bits). The declared development size grid is 256/1024.

This is an additional development experiment outside that grid. It does **not**
by itself show that the reserved transfer strings/seeds or F03/F10/F11/F12 were
used before freezing. It does mean the largest transfer length was already
exercised in development. The high-level deviation/scope records should say so,
rather than leave the disclosure only in a search appendix.

Required: list this design deviation and distinguish reserved strings/parameters/
families from unseen sizes. Preserve transfer as descriptive. A rerun cannot
make the already exercised length unseen again. No new scientific experiment is
needed merely to repair the wording.

## 6. R5 — enforce the recorded environment on resume (medium)

Location: `hierarchy/benchmark.py:207`.

The freeze records interpreter/dependency/compressor versions, but
`load_and_validate_freeze` compares only source, protocol and search-config hashes.
Resuming with a changed Python or codec library can combine different byte
generators under the same freeze identifier. This is not evidence of environment
drift in confirm-v1; it is a gap in its reproducibility enforcement.

Required: compare the scientific environment fields actually used, including the
recorded liblzma fingerprint when no version is available, before benchmark/resume
or diagnostics. Separate informational hardware fields from mandatory equality.
Offline archive inspection should still be possible with a clearly labeled
verification environment. Test deterministic mismatches without installing other
versions.

## 7. Scientific direction after correction

The result supports retaining this as a lossless, bounded automatic description
system with useful components, **not claiming an overall baseline advantage**.
The five ablations describe the configured algorithms; search-budget interactions
mean they do not separately identify a language-intrinsic contribution.

Before changing the format, the next research design should separate two gaps:
(a) best known legal description versus what automatic search finds, and (b)
legal-description overhead versus the baseline. The witness shows (a) is real.
It does not establish which gap dominates the whole population. Such a study
would be exploratory on already inspected families, followed by a prospectively
frozen evaluation on newly reserved seeds. Do not implement or tune it during the
correctness pass assigned here.

## 8. Evidence and reproduction

From the repository root:

```sh
PYTHONPATH=index-deconvolution:src venv/bin/python -m pytest index-deconvolution/hierarchy/tests tests/analysis/test_description_lengths_values.py -q
venv/bin/python index-deconvolution/experiments/review_hierarchy_confirm_v1.py
venv/bin/python index-deconvolution/experiments/review_hierarchy_failure_modes.py
```

Evidence is under `results/hierarchy_v1_supervision/confirm-v1/`:

- `audit.json`: complete archive/design audit and independent bootstrap results;
- `failure_reproductions.json`: missing-design/censoring faults, mismatch injection,
  comparator correction and witness metadata;
- `F12_oracle_boundaries_witness.isd`: the diagnostic's actual transmitted bytes;
- `bdm_reaudit.json`: regenerated 200-by-24 score matrices for ten objects and
  independently recomputed p-values/corrections.

The first script validates against the original source hashes and will deliberately
fail after those files are edited. Preserve a source snapshot before correction.
The second script describes bugs in that original version; its expected bug
reproductions must not be treated as desired behavior for a corrected version.

**Acceptance decision:** the measured negative result and positive within-system
ablations are reproducible. Final handoff acceptance remains pending R1-R5,
accurate claims, and the protocol-required new freeze/replay for correctness
changes. No positive performance threshold is added.
