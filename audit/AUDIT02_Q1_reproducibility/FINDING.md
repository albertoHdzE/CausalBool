# AUDIT02/Q1 — arm-1 reproducibility sweep across the five replication packages

The audit so far graded the *our-method* arms. This grades the other sense: **do
the committed replication results still regenerate from current code?**

Method, per artefact: re-run the producer, compare to the git-committed file
elementwise (U8 — which keys differ, never a count alone), restore the tree.
Outcomes were declared before running: *identical* / *differs* / *will not run*.

## Provenance precondition

All **85** committed artefacts across the five packages map to a producer
script. **Zero orphans.** So every number is in principle re-derivable, and the
only open question was whether it still re-derives to the same value.

## Result

| package | identical | differs | will not run |
|---|---|---|---|
| imp-causal-paper | 1/1 | — | — |
| imp-causalNet-paper | 1/1 | — | — |
| imp-pathinfo-paper | 3/3 | — | — |
| index-deconvolution | 6/8 | 2 | — |
| imp-prices | 3/8 | 3 | 2 |

`index_method_comparison/run_comparison.py` reproducing byte-identically is also
the positive control for AUDIT02/P9: that finding's harness is the same
measurement, not a re-implementation.

---

## Q1-A — two index-deconvolution artefacts are stale (pre-existing, NOT caused by AUDIT02)

`exp02_exact_recovery_{summary,records}.json` and `exp03_ca_to_network.json` do
not reproduce.

**Phase 1 is exonerated, and this was checked rather than asserted.** A read-only
worktree at `f17e839` (pre-Phase-1) runs the same producers and emits output
**byte-identical to HEAD's**. `deconvolution.py` is unchanged since `f17e839`;
the only edits to `causalbool.py` are declarations plus the `MAJORITY`/`KOFN`
branches, both proven equivalent on their default paths (8,190 and 106,494 cases,
0 mismatches, with a planted-defect control giving 1,274).

The artefacts are stale with respect to commits `b74953b` / `69156ce`, which
added `REGULATORY` and `REGULATORY_DNF` to `identify_gate` without regenerating.

**The headline numbers do not move.** 200/200 exact repertoire and 96.12%
connectivity/gate-function recovery are identical before and after — those
compare truth tables, not names.

**What does move is the ambiguity histogram**, and it is a clean shift: every old
class 2–7 count survives unchanged one bin higher; the old class 1 (679) splits
into 292 still-unique and 387 that gained a second name.

```
committed   1:679  2:368  3:72  4:298  5:49  6:39  7:195
regenerated 1:292  2:387  3:368 4:72   5:298 6:49  7:39  8:195      (both total 1700)
```

This matters because `bitacora/02_experimental_results.md` read *"Roughly 40% of
nodes have a unique canonical name."* The true figure is **17.2%** (292/1700) —
too high by more than a factor of two, and it is precisely the identifiability
claim. Artefacts regenerated; prose corrected with a dated note.

`exp03`'s change is `LUT → REGULATORY_DNF` on some CA records: the same function,
renamed to the more compact representation now available. Directly relevant to
P9's expressivity point.

---

## Q1-B — imp-prices `phase1_b4_description_length.py` was not reproducible

Two invocations with identical arguments returned different hill-climb winners:
`WTI_Spot @ 0.375` versus `WTI_CL @ 0.4583`. The committed artefact recorded one
draw from an unpinned distribution rather than a result.

**Attribution, stated plainly: the project found this first.** AUDIT01/T2.1
(`bitacora/04`, 2026-08-24) ran a 45-value `PYTHONHASHSEED` sweep, established
that the statistic is hash-seed-unstable, and closed with an explicit rule —
*"any future structural claim from this search must fix and record
`PYTHONHASHSEED`."* My two draws land inside the 5–7 winners / 35–55 per cent
band that sweep had already mapped, so this is a cross-validation of it.

**What was actually open: the rule was written but never wired into the
producer.** The script still ran unpinned, so every regeneration kept drawing
afresh.

Isolation, so the cause is named rather than assumed:

| candidate | verdict |
|---|---|
| resampling rng | not it — `np.random.default_rng(42)`, seeded |
| pgmpy `HillClimbSearch` | not it — deterministic *within* a process (six `learn_structure` calls on one frame agree) |
| `PYTHONHASHSEED` | **it** — pinning makes runs byte-identical, `content_sha256` included |

Fixed, in the producer:

1. Re-exec with `PYTHONHASHSEED=0` when unset. The variable is read at
   interpreter start-up, so it cannot be set from inside a running process;
   re-exec is the only correct remedy. Recorded in the output.
2. Tie-break `ranked` on the parent tuple rather than dict insertion order — a
   second, independent source of variation when counts tie.

Verified: three fresh runs, no environment set by the caller, agree elementwise
including `content_sha256`. Regenerated at the recorded config (`--boot 300`);
the pinned triple is now **(5, {WTI_CL}, 48.33%)**. The CPT arm is unchanged at
0.5167, confirming it was always deterministic and only the comparator moved.

The stability verdict is unaffected: 22 distinct index-set winners remain far
less stable than the CPT's 4 or hill climbing's 5.

---

## Q1-C — two imp-prices producers will not run at all

`phase2_gate.py` and `phase2_forecast.py` both abort:

```
NonPositivePriceError: 1 non-positive price(s) at index [2588] (min -37.63)
```

That is the April 2020 negative WTI settlement, and the guard is behaving
correctly. But it means the committed `phase2_gate.json` and
`phase2_forecast.json` **cannot be regenerated from current code** — they predate
the guard. Either they were computed over the negative-price episode the guard
exists to exclude, or the pipeline has since changed.

**Not remediated.** Both routes (call `clean_prices()` and report the exclusion,
or restate the artefacts as pre-guard) change a Phase-2 result under a frozen
pre-registered protocol. That is the author's call, exactly as with P9.

---

## Q1-D — process notes, minor

- `phase1b_gate_network.json` and `gate10_feasibility.json` differ **only** in
  `provenance.runtime_seconds`. Harmless, but it defeats byte-identity as a
  reproducibility check. `imp-causal-paper` already excludes wall-clock for this
  reason; imp-prices should follow.
- `imp-pathinfo-paper/results/campaign_status.txt` differs only by its
  `generated:` date. Same class.
- My own sweep initially tracked only `.json/.csv/.jsonl/.md` and so missed
  `.txt` artefacts; caught and checked separately.
- **The root repo has the same defect.** `make closure` rewrites
  `results/tests/algo004closedformsetaudit/Metrics.json` and
  `mixed001FormulaVsExhaustive/Summary.json` on every run, differing only in
  wall-clock fields (`setMaterialisationSeconds`, `baselineTime`,
  `predictiveTime`, …) and in `Status.txt` timestamps. Verdicts stay `OK`. So
  running the closure gate dirties the tree, which trains the reader to ignore
  churn in exactly the directory where a real change would appear. Timing
  belongs in a separate, untracked profile file.

## Verification

```
imp-causal-paper 28 · imp-causalNet-paper 47 · imp-pathinfo-paper 41
imp-prices 97 · index-deconvolution 146      — all pass
make closure                                  — all five members green
```
