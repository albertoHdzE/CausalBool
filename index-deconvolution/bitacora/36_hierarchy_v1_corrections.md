# 36 · HID-v1 correctness amendment and replay (`confirm-v1-r1`)

Date: 2026-10-02. Developer: Claude Code. **Not yet reviewed by the supervising session.**
Responds to `35_hierarchy_v1_supervisor_review.md` (R1–R5). Bitacora 34 is kept as the
historical record of `confirm-v1`; this note corrects its claim wording without
rewriting its numbers. Handoff: `hierarchy/HANDOFF_CORRECTIONS.md`.

## What changed and why it matters

The supervisor showed that the reporting code would have called a study `supported`
from **one unit of 420**, because the population was read off the rows that happened to
exist. The original numbers were right, but only because nothing was missing. The
amendment makes that dependence explicit and fail-closed.

* **R1.** `hierarchy/validation.py` builds the expected population from the declared
  design and checks every row, archive and portfolio selection; `report` and `verify`
  both pass through it. Verdicts are reached in a fixed order — engineering validity,
  completeness of the claim's own population, censoring, and only then the interval. An
  invalid or incomplete population is `not_assessed`; a censored baseline makes the
  result `inconclusive` whatever the sign; any aggregate over the units that remain is
  printed only as a labelled partial diagnostic.
* **R2.** A proposal of the right length that expands to a different string now raises
  `CandidateExpansionMismatch`. It becomes an `error` row, never a candidate rejection
  or a raw fallback.
* **R5.** `benchmark`, `diagnostics` and `report` refuse to run under a different
  interpreter, zlib, liblzma fingerprint, numpy or pybdm than the freeze recorded;
  `verify` records the difference and carries on.
* **R3–R4.** Claims rewritten to their estimands (below); development scope disclosed.

## The replay

Protocol §7 requires a new run ID and a new freeze after a correctness fix. `confirm-v1-r1`
(freeze `f970efff…`) regenerated and rescored all 1,632 strings and 26,112 method rows
from scratch, with the original resource policy, in 3,266 s of the 21,600 s budget
(`confirm-v1`: 3,325 s). Against `confirm-v1`, every one of the 26,112 case × method rows
agrees in every deterministic field — archive hash, size, path, codec, portfolio
selection, rule count, depth, candidate count, work units, stop reason, counters, best
source and trace — and the content-addressed archive manifests are byte-identical
(16,402 archives each). Only wall time and RSS differ. The BDM diagnostic matrices,
p-values and Holm corrections are identical. Evidence:
`results/hierarchy_v1_corrections/compare_confirm-v1_vs_confirm-v1-r1.json`.

That identity is the expected outcome of a correctness-only change, so it confirms the
amendment did not move the result; it is **not** a second, independent test of the
hypothesis. The strings, seeds and families are the ones whose results were already
seen in `confirm-v1`.

Separately, the corrected report applied to the retained `confirm-v1` rows reproduces
the supervisor's independent estimates and intervals to at most 6×10⁻¹⁷
(`results/hierarchy_v1_corrections/original_rows_under_corrected_report.json`), so the
new gates do not touch the complete-data arithmetic.

## Results, unchanged, with corrected readings

Primary endpoint (structured confirmation, 21 cells, 420 units, 840 strings; gates
passed): mean saving **−0.04462** bits per input bit, 95 % bootstrap interval
[−0.05368, −0.03582]. **C1 not supported.** The full method costs 0.0446 more bits per
input bit than the portfolio; the denominator is input length, not archive length.

The five ablations are all positive at 99 % (largest `flat`, +0.26360 [+0.24348,
+0.28251]; smallest `no_transform`, +0.00188 [+0.00148, +0.00227]). They describe the
configured algorithm under the frozen budget: removing a component also changes what
the bounded search reaches, so they are not the intrinsic value of each opcode.

**C4, reworded.** *Is there a positive equal-weight portfolio saving on the structured
families at 16,384 and 65,536 bits?* No: −0.06280, descriptive 95 % interval
[−0.07690, −0.04853], four units per cell. Descriptively, F04 is positive at both sizes
(+0.04602 and +0.01155) and F05 at both (+0.00305 and +0.00218). The reserved seeds
2000–2003 and the held-out families F03, F10, F11, F12 were not used before the freeze,
but the 65,536-bit **length** was: development-resource probes at that size (F02, F05,
F06, F07, development parameter ranges) informed the work cap, and the setting was
chosen partly on an encoded length (F06 11,992 → 11,720 bits). The largest transfer
length is therefore not an unseen length. This scope note belonged in the high-level
records of `confirm-v1` and was only in a search appendix.

**C5, reworded.** The old text — "no advantage over the statistical baselines" — named
a comparison the endpoint does not make. The endpoint is the equal-weight aggregate of
F07–F09 against the **nine-code portfolio**: −0.26335 [−0.28105, −0.24511], so *a
positive aggregate saving on the controls* is not supported. That is not a statement
about each family, and failing to win is not equivalence. Against the better of the two
statistical codes alone, the picture differs by family (descriptive, unweighted string
means): F07 +0.01798, HID shorter on 117 of 120 strings; F08 −0.44668, longer on all
120; F09 −0.34338, longer on 118, tied on 2. The F07 difference is raw fallback against
the statistical codes' own overhead on fair coins, not structure discovered by HID.

All twelve families (descriptive, not the primary population, seed 43001): −0.10226
[−0.10922, −0.09531].

## Search versus language — what is and is not established

Bitacora 34 and `SEARCH_SPEC.md` §8 attributed the losses to the language. That was
more than the evidence carries. Every HID number is the best archive *found* under the
budget, and no large-instance optimum has been computed. Wire overhead, proposal
coverage (fixed segmentation grids, no boundary discovery), caps (44 of 1,440
confirmation full searches ended at the candidate cap; in transfer 50 of 192 ended at the
work cap and 21 at the candidate cap) and search quality are separate contributors, and
the benchmark does not say which dominates.

The supervisor's witness makes one gap concrete. For `transfer-F12-65536-2000-base`, a
legal archive in the unchanged language is 22,480 bits; the search found 28,528; the
portfolio has 23,240. The witness used the generator's construction boundaries — evaluation
metadata — and is therefore post hoc, outside every benchmark number and claim, never an
inference input or tuning target, and not an optimality certificate. It shows the
search-to-feasible gap is real on at least one input, not how large it is in general.

The suggestion at the end of bitacora 34 — an entropy-coded reference stream or a
statistical leaf — would change the wire language. It is a new version with its own
specification, not an addition to W3, and on already-inspected families it would be
exploratory until confirmed on newly reserved seeds.

## Status

Engineering: valid and complete (`verify --full` exit 0; 317 tests; ruff clean; the
single-engine guard fails only on the pre-existing `.kilo` worktree). Scientific verdict
for the prespecified primary endpoint: **not supported**. Neither outcome depends on
the sign of the result, and neither amounts to acceptance; the revision awaits Codex's
review.
