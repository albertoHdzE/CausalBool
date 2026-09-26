# Codex review of Claude's two completed research assignments

2026-09-25. **CHANGES_REQUIRED: interruption accounting in the objective-index release.**
This is a focused handoff, evidence and source review, not completed independent
acceptance of either entire implementation. No measured source, frozen protocol,
historical result, production compiler or manuscript was changed.

Reviewed handoffs: `../optimization_20260924/RELEASE_HANDOFF.md` and
`../objective_index_20260924/RELEASE_HANDOFF.md`. Both are completed worker
deliveries awaiting lead acceptance. The latter supersedes the former protocol;
that does not establish that its selected compiler outperforms the earlier one.

## R1 — interrupted candidate validations disappear from the non-model A4 report

At `research/objective_index_search.py:1572–1577`, `finish()` appends the
query's interrupted validations only inside `if query.learner is not None`.
The selected non-model A4 has no learner, so this diagnostic is discarded.
The per-query summary also omits `interrupted_validations`.

The retained `probes.py` forces the clock past the deadline during candidate
validation on generated program 800004. The actual validation and acceptance
code executes. The internal search report counts **one** interrupted validation;
the returned controller report says **zero** and has an empty interruption list.
It accepts **zero** improvements and returns UNKNOWN_DEADLINE, correctly.
See `PROBES.json`, including the reviewed source hash. This is an evidence
accounting defect, not evidence of accepting late or invalid compilations.

Repair the accounting in a separately preserved successor source version, add
a regression through `multiscale_optimise` without a learner, and retain both
the internal and returned counts. Do not edit the frozen implementation in
place or refresh hashes on the old measurements. The historical primary quality
estimates can remain reported for their original source; missing historical
interruption counts cannot be reconstructed as zero. A corrected measured
release needs an explicit follow-up protocol and provenance decision.

## Independently reproduced results

The research package verifier passes, including the 18 immutable accepted-control
source hashes. Fresh runs of the objective-index checker and its separate
numerical auditor pass with **116,859** and **163,281** checks and zero findings.
Those checks do not cover R1. Their outputs are retained beside this review.

The lead's separate standard-library recount reads raw measurement rows and
fixture oracle/split files without importing the experiment's analysis helpers.
It reproduces the following primary 0.1-second results on 200 generated programs,
15 repetitions each. J is cycles times scratch footprint; lower is better.

| A4 compared with | Geometric J reduction | Wins / ties / losses | Compile-time ratio |
|---|---:|---:|---:|
| Frozen Phase 2 (A0) | 6.04% | 102 / 98 / 0 | 11.65× |
| Accepted budgeted direct | 8.76% | 127 / 73 / 0 | 0.817× |
| Classical | 10.58% | 138 / 42 / 20 | 76.20× |

The independently rerun numerical auditor also verifies the declared primary
intervals. These are results for the stated generator population and controls.
They establish a quality/cost trade-off against A0 and classical, not general
compiler superiority or private-grader performance.

Both campaigns' public scores were independently recomputed from raw integer
cycles and scratch, with all eight programs in each of 15 repetitions:

| Compiler | Fixed public-suite score |
|---|---:|
| Earlier optimization's selected_nonmodel | 2.102746654351309 |
| New objective-index A4 | 2.088945490290080 |
| Frozen Phase 2 | 2.032760233943861 |
| Original direct | 2.008466202284657 |
| Classical | 1.901379121264550 |

The new A4 score is 0.656% below the earlier optimizer's recorded score. This is
a descriptive comparison of two retained runs, not a fresh randomized head-to-head
experiment. They used different generated evaluation cohorts, so their generated
effect sizes cannot establish which selected compiler wins head-to-head.

## Learning study limitation

The lead independently checked all 30 new evaluation fixtures: **zero** contain
a test solution strictly better than the best training solution. Because the
endpoint starts at the training minimum, every arm's improvement endpoint is
necessarily tied. H_LEARN=FAIL is the prescribed gate outcome, and blocking the
learned compiler pair is correct; this design cannot resolve whether learning
helps. The protocol's assertion that qualification guarantees estimability was
too strong. This is a study-design limitation, not Claude failing to obtain a
promised positive result. Preserve the negative result and redesign the endpoint
or fixtures before spending another campaign on the same learning question.

## Scope and reproduction

The disclosed post-freeze comparison wrapper was inspected. It guards the empty
`attempted_queries` summary; the separate numerical auditor and lead recount
reproduce the primary quality results. This review does not independently rerun
the full experiment, full standalone acceptance matrix or production comparison.
No acceptance is inferred from historical success banners.

Commands run from `luminal-challenge`, each with exit 0 unless noted:

```sh
../venv/bin/python plan/phase2_research/verify_package.py
PYTHONPATH=.reference:. ../venv/bin/python -m research.objective_index_checker --run results/phase2_structural_encoding/objective_index_20260924 --output /tmp/causalbool-claude-review-20260925-checker.json
../venv/bin/python research/objective_index_audit.py --run results/phase2_structural_encoding/objective_index_20260924 --output /tmp/causalbool-claude-review-20260925-audit.json
PYTHONPATH=.reference:. ../venv/bin/python results/phase2_structural_encoding/lead_objective_review_20260925/probes.py
```

The probe exits 0 when it completes its recount and records the defect; this is
not a release PASS. The full research-test rerun also exits 0: **392 tests pass
in 562.674 seconds**, with no skips reported. Command:
`PYTHONPATH=.reference:. ../venv/bin/python -m unittest discover -s research_tests`.
See `RESEARCH_TESTS.json` and `RESEARCH_TESTS.log`. Deliberate negative evidence
mutations print FAIL inside that log; the overall unittest result is OK.

No commit, push, publication, production integration or new measurement campaign
was performed. Claude's frozen deliverables remain preserved for further review.
