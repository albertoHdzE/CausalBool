# Duplicated code across the research programme — census and adjudication

**Date:** 2026-09-04 · **Producer:** `duplication_census.py` → `duplication_census.json`
**Guards:** `tools/check_single_engine.sh`

Previous collapses were reactive — the engine (AUDIT02/P4e), the offset family
(R2a.2), the description length (R2b) — each done when the audit tripped over
it. This asks the question once, over the root repository *and* every
subproject, and answers it with a list.

## Method, and where it is weak

- **Python** — normalised AST, docstrings and comments stripped, so a
  re-commented copy cannot hide. Names are kept, so a *renamed* copy is missed.
- **Wolfram** — normalised text, because there is no parser. **This arm is
  materially weaker and it was demonstrated to be.** It reported three
  `compressionWeight` copies when there were **six**, missing two whose
  signature differed and one written on a single line. It reported two
  `LoadJSONNetwork` copies when there were **five**.

> **The guard beat the census three times.** `check_single_engine.sh` found a
> third `givePlaces` (R2a.2), a sixth `compressionWeight`, and the third,
> fourth and fifth `LoadJSONNetwork`. A hash finds identical copies; a guard
> finds copies that have *drifted*, which are the dangerous ones.

Excluded, each with its reason: `archive/` (repository policy), `venv`/
`site-packages` (not ours), `src/external/ccapi` (vendored), `imp-prices/vendor`
(two-copies rule, pinned), and each replication's `reference/` tree holding the
**original authors'** code. That last exclusion is not cosmetic: their internal
repetition — 13 copies of one helper in `kaust_path_project` alone — dominated
the first run and would have buried ours.

## The finding that explains most of the rest

**23 of 78 MUnit files are never executed.** `run-tests.sh` globs `*Tests.m`,
and these names do not match:

```
Algo/TSK-ALGO-002-ImportanceSampling.m      Exper/TSK-EXPER-001..005
Algo/TSK-ALGO-003-SubsystemHeuristics.m     Mixed/TSK-MIXED-001-Comparison.m
Algo/TSK-ALGO-004-ClosedFormSetAudit.m      Mixed/TSK-MIXED-001-OnPossibleBehaviour.m
Algo/TSK-ALGO-PerfTable.m                   Pattern/TSK-PATTERN-Ordering-Invariance.m
Algo/TSK-ALGO-VisualSamples.m               Sampling/VerificationSamples.m
Compare/TSK-COMPARE-002-PIDSynergy.m        Stoch/TSK-STOCH-001-NoiseMonteCarlo.m
Compare/TSK-COMPARE-003-TE-MI.m             Stoch/TSK-STOCH-002-NoiseCurve.m
Compare/TSK-COMPARE-CHARTS.m                Tests/TSK-TEST-001-TruthTables.m
                                            Tests/TSK-TEST-003-PerfRepertoires.m
                                            Tests/TSK-TEST-004-AcceptanceFigures.m
```

`TSK-ALGO-004-ClosedFormSetAudit.m` *is* run, but by `verify-paper` as an
artefact producer, not by the suite. `TSK-EXPER-004` additionally exports
`Status "OK"` **unconditionally**, so it could not have failed even if run.

**Seven of the nine remaining Wolfram duplicates live entirely inside these
never-run files.** That is why their drift was never visible, and it is why
collapsing them is worth less than making them run — which is an open item, not
something to fix silently here.

## Adjudication

### Collapsed, with parity evidence and a guard

| concept | sites | evidence |
|---|---|---|
| `compressionWeight` / `computeCompression` (`C_formula`) | **6** → `Integration\`BioMetrics\`` | 4 identical; `TSK-EXPER-004` and `TSK-ALGO-003` had **drifted** — no `KOFN`, no `CANALISING`, so both fell to `1+d`. Measured: **20 of 72** `(gate, d)` cells disagreed. Owner reproduces the published `C_formula = 23`; `C -> 11.` unchanged in `theory002`; Theory and Mixed sections green. |
| `LoadJSONNetwork` | **5** → `src/scripts/NetworkIO.m` | See below — the owner choice mattered. |
| `networkUpdate` (6-node flagship) | **2** → `CausalBoolCore.composedUpdate6Node` | **Not** collapsed onto `CreateRepertoiresDispatch`: it is the *composed* reading (D-2d) and differs from the synchronous dispatch on **32 of 64** rows, on node 6 only, exactly by using the new `y5` rather than `x5`. Collapsing them would have silently changed the flagship by half its rows. |
| `_row_cost` / variant A (**cross-project**) | 2 → the declared canonical | The root wrapper *reimplemented* the variant `DESCRIPTION_LENGTHS.md` declares canonical in `imp-causalNet-paper`. Proven equal on 300 random adjacency matrices, then delegated. **Cross-project duplication is now 0.** |

### `LoadJSONNetwork` — the owner choice was wrong the first time

Five copies, drifted. Two of them — `GlobalStatsPipeline.m` and
`GlobalValidationAnalysis.m` — read only the `gates` field, which is a
**classification label**. The copies in `RunEssentialityValidation.m` and
`BehavioralKnockoutAnalysis.m` carry the **AUDIT02/H correction**: they also
read `logic`, the authoritative per-node Boolean formula, because labels outside
the twelve families otherwise reach `ApplyGate` and silently evaluate to `0`.

I promoted the first copy I found, which was one of the deficient ones. Caught
by diffing the copies the guard surfaced. **The superset is the owner**, so
adopting it *corrects* the two pipelines rather than merely deduplicating them.

Measured: 234 of 234 networks load, 0 failures, and **5,354 of 6,581 nodes
(81.4%)** carry a label outside the twelve families — the nodes for which the
label is not the semantics. Declared in `tests/MUnit/BASELINE.md`.

### Left alone, with reasons

| candidate | sites | why not collapsed |
|---|---|---|
| `makeSF`, `makeSW`, `EnsureDir`, `notSlope`, `mixSlope`, `sampleInputsVec`, `applyOutputs` | 2–3 each | All inside the **never-run** files. Collapsing code nobody executes is lower value than executing it; the coverage gap is the real item. |
| `buildNetwork` | 2, in `index-deconvolution` | One is in `crosscheck/`, one in `experiments/DemoLibrary.wl`. The crosscheck path is deliberately independent of the experiment library — that independence is what makes the 135/135 parity meaningful. **Deliberate, like the `audit/` exemption.** |
| `_paper_root` | 4, `src/analysis/` | A four-line path helper. Collapsing it would add an import to save nothing. |
| `load_edgelist` | 4, `imp-causal-paper/scripts/` | Inside one replication package; no cross-project reach. Recorded, not urgent. |
| `buy_sell_times` / `buy_sell_occurrences`, `pearson` / `_corr` | 2 each, `index-deconvolution` levels | The level directories are deliberately self-contained experiment records; each level is a dated artefact. Collapsing them would rewrite history. |
| `load_report_unverified` | `dossier_ledger_adjudication{,_v2}.py` | A v1/v2 pair in `imp-prices`. Whether v1 is superseded is a question for its author, not a refactor. |

## Open items this census raised — CLOSED 2026-09-04

1. ~~**23 MUnit files never run.**~~ **CLOSED.** Inspected surgically rather
   than renamed en masse; the glob turned out to be the smaller half of the
   problem. See `test_efficacy_census.py` and `tests/MUnit/BASELINE.md` v3:
   the 23 split **10 real conditional checks / 11 that export a literal `"OK"`
   and cannot fail / 2 artefact producers**. Renaming was ruled out on
   evidence — `TSK-ALGO-004` and `TSK-MIXED-001` are cited by name in **both
   manuscripts**. Membership is now declared in `tests/MUnit/MANIFEST.tsv`.
   Suite: `OK=65 FAIL=0 TOTAL=65`.
2. ~~**`TSK-EXPER-004` exports `"OK"` unconditionally.**~~ **Measured: it is
   one of eleven, not one.** All eleven are quarantined in the manifest with
   that reason, rather than collected as green results nothing can falsify.
   The reassuring half of the same measurement: **all 55 files the runner was
   already collecting are conditional** — the suite that ran had no fake greens.
3. The Wolfram arm of this census is **text-based and demonstrably lossy**.
   The guards, not the census, are the durable defence. Confirmed a fourth
   time: the AST arm of the Python census reported **three** copies of the
   repo-path helpers when there were **four** — the fourth was found by
   searching for the body fragment `CAUSALBOOL_PAPER_ROOT`.

## What the collapse itself broke, and how it was found

Recorded because it is the strongest evidence for the guards, and against
trusting a green suite.

The `C_formula` collapse in `019ff70` left an **orphan tail** from the replaced
body in four files, and omitted the `Get` for `BioMetrics.m` in three of them.
Three of the four were collected by the runner and **still reported green**:
the kernel prints `Syntax::sntx`, skips the malformed expression, exits 0, and
the runner then read a **stale `Status.txt`** from the file's last successful
run. Two independent harness defects had to line up for the breakage to be
invisible, and they did.

Both are now closed: `tools/check_wolfram_syntax.wl` asserts every Wolfram file
parses (**152/152**), and `run-tests.sh` deletes each status file *before*
running its test, so a missing status reads as the failure it is.

The same run corrected a long-standing entry in the ledger: `TopologiesTests.m`,
"the single owned red", was recorded as a run that *died before its export*. It
never parsed. One surplus `]` in `progressBar`.


## The complementary question: dead code (2026-09-04)

Duplication asks "is this defined twice". The other half of the same law is
"is this called at all" -- an uncalled function drifts exactly as a duplicate
does, and this audit had already tripped over two by accident (a `TSK-MIXED-001`
copy of the description length that was never invoked, and a `pair` unpack in
`complexity_analysis.py` that could only ever have raised).

Measured by `orphan_census.py`. **The sweep over-counts references, so it
UNDER-reports orphans: every name it prints is genuinely unreferenced, and the
true set is larger. A floor, not a ceiling.**

| arm | defined | never referenced |
|---|---|---|
| Python, whole programme (370 files) | 2,053 functions / 1,673 distinct names | **29 (1.7%)** |
| Wolfram packaged core (`src/Packages/Integration`) | 38 public definitions | **4** |

**Zero orphans inside a declared core owner.** That is the number that matters:
the files `GOVERNANCE/CORE.md` names are fully live.

### The one that was not merely dead

`lsb_inputs` in `papers/method/code/corroboration_6node/ordering_invariance_6node.py`
was defined and never called -- and it is the machinery for the LSB half of the
ordering-invariance claim. The **LSB one-sets were hard-coded literals**, so only
the MSB side was ever recomputed. The check still had teeth (a wrong literal
would fail it), but it *asserted* half of what it could *compute*.

Both sides are now derived from the same update rule under the two orderings,
and the published literals are verified against the computed one-sets. They
match, so no artefact moved; a planted wrong anchor exits 1. The orphan is gone
because it is used, which is the only honest way to remove one.

### Recorded, not removed

`KnockoutNetworkByIndex` (`BioExperiments.m`), `LogicParseStatus` and
`LogicVariables` (`LogicEval.m`), `SelfTestRun` (`SelfTest.m`). The last is
worth naming: **a self-test that nothing invokes.** These are API surface, not
proven dead, and deleting a public symbol on a grep is exactly the reasoning
this document exists to discourage. Left for the author.
