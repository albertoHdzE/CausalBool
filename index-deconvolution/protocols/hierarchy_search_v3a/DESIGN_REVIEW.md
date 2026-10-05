# Codex protocol review and delegation decision

Decision: **ready for full Claude implementation/execution delegation**.
Date: 2026-10-04. This is a design review, not acceptance of an implemented study.

The packet completes the previously exploratory Draft A. Draft B/TILE remains
outside scope. R1/R2 interpretation limits and R3 evidence gates carry forward.
No experiment, new corpus or algorithm implementation was run while preparing it.

Resolved choices:

| Previously open issue | Fixed decision |
|---|---|
| Which continuation first? | Search-only Draft A; representation requires its own later protocol. |
| Several seeds under finite caps | Four distinct ranked coarse partitions; level-major, fixed seed-rank order; shared caches/caps, independent local refinement pools. |
| Ties and duplicate paths | Existing archive-based keys; partition dedup at seed selection; no merged/replaced converged seed. |
| How to preserve the comparator | Shared owner k=1 path, old config serialization/hash, all 1,792 old full archives reproduced byte for byte. |
| Proposal coverage | Actual ordered requests/evaluation outcomes, distinguished from returned cuts; development metadata joined only afterward. |
| Development stopping/selection | Engineering completeness only; no tuning or efficacy threshold and no extra candidate. |
| Small large-size/stress samples in draft | Twenty paired units in each of six primary cells; 120 units, 240 target strings. |
| Prospective controls and costs | Eight control units; all 256 strings receive two full HID arms and all nine baselines, plus a derived portfolio row. |
| Primary inference | One full k=1 versus k=4 contrast; paired/equal-cell mean, shared bootstrap, 10,000 draws, seed 55001, 99% percentile interval. |
| Other comparisons | Descriptive only; no portfolio rescue or mechanism/causal identification claim. |
| New-phase finite allowance | Eight hours, split 4/3/1; protected final reporting reserve; explicit cumulative attempt accounting. |
| Freeze/launch autonomy | Claude continues when executable gates pass; redesign, exposure or post-freeze repair returns for supervision. |
| Notebook ownership collision | Notebook 19/build_19.py belong to BDM; reserve notebook 20 and preserve 19. |

Code inspection confirmed the existing BoundarySearch coarse ordering, per-parent
refinement pool, cache/charging behavior, best_seen cap exit and callback semantics.
The proposed k=1 schedule specializes to these rules. The full orchestrator runs
L–G before B, so the treatment must independently rerun those stages and cannot
receive an old saved incumbent. The shared report owner supports unequal cell
matrices and the fixed within-cell draw ordering; no new statistical engine is
needed. Existing StudySpec, watchdog, generators, raw fallback and validation are
the integration owners; thin new-study adapters are allowed.

Static checks verify keys, pairs/cells/jobs/rows, baseline order, every boundary
default, the patch hash, unchanged active/protected sources and vacant new run
and notebook paths. The median repair passes `git apply --check`. These checks
do not substitute for implementation tests, untouched-namespace preflight or
the future scientific freeze.

The current reporting integration's ten source/notebook equalities pass. Its
scientific source/result protected trees still match; the bitacora aggregate
differs from the earlier integration record and is explicitly carried as the
current protected initial state, without attributing or reverting others' work.
The reserved 30-second prior-phase supervisor integration-check charge is
recorded separately in INTEGRATION_CHECK.json; old ledgers are not rewritten.

No unresolved scientific option is delegated for Claude to optimize after seeing
new data. Remaining software choices are ordinary implementation choices subject
to the exact semantics, tests, ownership and budget. Completion may be supported,
harmful, inconclusive, incomplete or invalid. Final acceptance remains Codex's.
