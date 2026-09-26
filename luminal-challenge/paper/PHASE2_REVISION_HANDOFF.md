# Phase 2 manuscript revision handoff

Status: **READY FOR LEAD REVIEW**. No peer review, scientific acceptance,
commit, publication or new experiment is claimed.

## Changes

- Revised main.tex with a bounded abstract statement and a Phase 2 feasibility
  section before related work. It specifies both sampling streams and the
  finite domain, distinguishes stream draws from their distinct union, reports
  finite-check denominators and stage disposition, and bounds conclusions.
- Added phase2_evidence.py, called by generate_figures.py. It derives the
  coverage rows and metrics from accepted JSON, checks declared statuses and
  counts, and streams SHA256 over raw inputs to compare with P1's hash map.
  main.tex includes the generated table.
- Updated artifact reproduction text, README.md and CLAIMS_AND_EVIDENCE.md
  with the evidence map, dates, storage limit and claim boundaries.
- Rebuilt main.pdf and BUILD_VALIDATION.json. Existing production
  generated/metrics.json is unchanged.

## Preserved baseline

The pre-edit manuscript is preserved under baselines/20260921/, including the
PDF, source, evidence documentation, both Python build scripts and generated
directory. BASELINE_MANIFEST.json contains SHA256 for all 24 copied files and
records starting HEAD 1aef90681e3dead3ab1f560da8b7823ab66dabf4. Integrity check:
24/24 match; no existing baseline was overwritten.

## Evidence and limits

The accepted Phase 2 run is
../results/phase2_structural_encoding/phase2_repair_20260923c/. Its acceptance
record is LEAD_ACCEPTANCE.md; stage verdicts are in gates.json; checker
disposition is in checker.json; finite and public results are in p0/summary.json
and p1/summary.json. The sampling design is in
../plan/phase2/PROTOCOL.json and ../plan/PHASE2_STRUCTURAL_ENCODING_PLAN.md.

Generated phase2_metrics.json records source SHA256 values and the five raw
P1 artifact hashes. Raw hashes were computed in 1 MiB chunks and match the P1
summary. Principal verified hashes:

| Evidence | SHA256 |
|---|---|
| P1 summary | 5835d695cfc89ab5d2a05ae629877a574e75e9aa694c826ac889ab69e0a80e8d |
| Stage gates | 7e512dfbefc87597cbcf7744c8f3d21fd41c602666572b737751383c4a4d2bc8 |
| Checker disposition | a6f355038ed1d6f1f1bc1260d56437f22f0bd0fdb1ac1983494a648a7984eae4 |
| Raw sampling attempts (local, about 113 MB) | 55c1943099fb7952eed197c4d67ee2fc489fce8504ed72204c33575b0f2f180a |

The checks establish 12 fixtures, four codecs, 24 exhausted code universes and
564 round trips. Sampling retained 160,000 attempts across 16 streams, 819
completed draws and 1,356 case checks, with zero observed discrepancies.
Raw-bit streams produced zero completions; distinct union counts in protocol
order are 0, 234, 194, 55, 135, 16, 168 and 17. Four programs miss the
100-distinct-completions minimum. P0 is PASS, P1 INCONCLUSIVE and P2-P5
BLOCKED_BY_GATE and unmeasured. The checker has zero findings and reports
internally consistent artifacts, while artifacts_complete=false and
scientific_success=false remain explicit in the generated evidence record.

The 113 MB attempts file remains local; packaging and portable storage are
unresolved. The evidence is not described as portable, published or fully
archived. No sampling amendment or new experiment is proposed.

## Validation

Commands were run from the repository root.

| Command | Exit | Result |
|---|---:|---|
| python3 luminal-challenge/paper/phase2_evidence.py | 0 | Evidence assertions and raw hashes pass; eight rows generated |
| venv/bin/python luminal-challenge/paper/build_paper.py | 0 | PDF built; no unresolved references, LaTeX warnings or overfull boxes |
| git diff --check -- luminal-challenge/paper | 0 | No whitespace errors in changed tracked paper files |
| Baseline SHA256 and production-metrics integrity check | 0 | 24/24 copied hashes match; production metrics unchanged |
| pdfinfo luminal-challenge/paper/main.pdf | 0 | 16-page A4 PDF |
| pdftotext -f 11 -l 11 -layout luminal-challenge/paper/main.pdf - | 0 | New section and table present on page 11 |
| pdftoppm -f 11 -l 11 -scale-to 1300 -png -singlefile luminal-challenge/paper/main.pdf /tmp/phase2-paper-page-11 | 0 | Rendered page 11 for visual inspection |

Page 11 was visually inspected; the table is legible and text fits. Production
score and compiler-time figures are unchanged. The 5.6321% figure remains a
composite-score improvement, not runtime speedup or an isolated causal effect
of representation. September 20 production tests remain separate from
September 23 Phase 2 evidence.

The lead should check the derived table against source JSON, verify wording
against gate verdicts, and record the final disposition in ../plan/STATUS.md.
No other issue is known.
