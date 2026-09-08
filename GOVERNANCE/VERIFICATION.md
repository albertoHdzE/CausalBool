# Verification status — what is checked, how, and how well

**Status:** normative. **Last measured:** 2026-09-06 (AUDIT04).
**Regenerate every number here with `make ci-local`; none of them is typed by hand.**

This is the single page a reviewer needs. `CORE.md` says who owns what;
`BASELINE.md` is the test ledger; this says **what is actually verified, and to
what degree** — including the parts that are not.

---

## 1. How to run it

```bash
make closure-pure     # 11 gates, no Wolfram needed — this is what CI runs
make closure-wolfram  # 4 gates that need a licensed local kernel
make closure          # both
make suite            # the 72-test MUnit suite
make ci-local         # closure-wolfram + suite: everything CI CANNOT run
make lint             # ruff, enforced rule set
make hooks            # install the pre-push hook (once per clone)
```

**`make ci-local` before every push.** The pre-push hook runs it for you and
refuses a push whose Wolfram tier is red; bypass with `git push --no-verify`,
which prints exactly what went unchecked.

---

## 2. The two tiers, and why the split is not cosmetic

GitHub-hosted runners have **no licensed WolframKernel**. Roughly half this
programme's verification therefore cannot run in CI, and pretending otherwise
would be worse than not having CI at all.

| tier | members | runs in CI |
|---|---|---|
| **pure** | paper-number gate · GLOSSARY sync · GLOSSARY conformance · single-engine guard · core index · test manifest · table coverage · **verification numbers** · **import safety** · **core loading** · **coverage ratchet** | **yes** |
| **wolfram** | `.m`/`.wl` syntax (156 files) · paper artefacts (executes producers) · cross-language parity (135/135) · description-length parity | **no** |
| **suite** | 72 MUnit tests | **no** |

CI states this in its own header and emits a run warning. **A green badge means
the pure tier passed — nothing more.**

> **The aggregator used to be unable to fail.** `make closure` invoked each
> member with a `-@` prefix, which tells make to ignore the error, so it exited
> `0` even if all nine failed; one member piped into `head`, so its status was
> `head`'s. `tools/run_closure.sh` replaced it and is verified in all three
> states — planted failure → exit 1, absent sibling → `UNKNOWN` reported as
> unknown, clean → 0.

**Three states, not two.** `check_glossary_sync.sh` exits `2` when the sibling
repository is absent. That is correct refusal, and it is what CI sees.
`UNKNOWN` is never folded into a pass.

---

## 3. Measured status

| what | measured | gate |
|---|---|---|
| MUnit suite | **72 / 72**, 0 failures | `make suite`, claim gated by the tracked `SCOPE=all` rollup |
| Declared Python suite | **268** tests over **28** files (1 skipped, declared) | CI asserts the count; membership from `MANIFEST.tsv` |
| `src/` line+branch coverage | **31.74 %** over **61** files | `check_coverage_ratchet.py`, global + per-module floors |
| Complexity measures that are algorithmic | **3 / 3** — index-set, BDM, `D_v2` forwarder; 0 rank random below structured **on the chain family** | `test_complexity_measures_are_algorithmic.py` |
| Structured families ordered correctly | **BDM 5 / 5 · index-set 3 / 5** — the index-set length inverts on a checkerboard (1050.5 bits against 563.9 for random of equal density) and on column stripes (1050.5 against 568.4), because it is a run-length code over rows and an alternating row costs its maximum. **Declared, not hidden**: `DECLARED_INVERSIONS` goes red if either disappears without the declaration moving | `test_structured_families_against_matched_random` |
| `index-deconvolution` | **146** tests | CI asserts the count |
| Replication packages | **29 / 97 / 47 / 42** | CI matrix, each count asserted |
| Wolfram files that parse | **156 / 156** | `check_wolfram_syntax.wl` |
| Test files classified | **121 / 121** — 85 Wolfram + 36 Python (100 test, 15 producer, 6 quarantine) | `check_test_manifest.sh` |
| Owners named in `CORE.md` that exist | **57 / 57** | `check_core_index.sh` |
| Manuscript numbers unchanged | **138** entries identical | `snapshot_paper_numbers.py` |
| Lint, enforced rules | **clean** | `ruff check` |

### Coverage of the declared Python owners

| owner | coverage |
|---|---|
| `src/description_lengths.py` | **100 %** |
| `src/causalbool_paths.py` | **96 %** |

**That scoping is withdrawn (AUDIT04-E, 2026-09-07).** The justification used to
read: *a percentage averaged over 370 files — scrapers, one-off analyses, frozen
workspaces — moves for reasons nobody cares about and hides the one that
matters.* That is correct about the **whole tree** and wrong about **`src/`**,
and the difference is not academic: scoped to two files out of 52, the gate could
read **98.56 %** while **42 modules sat at exactly 0 %**. The two rows above are
kept because they are true, and demoted from *the* coverage figure to *a* detail
of it. `.coveragerc` now scopes to `src`, and `fail_under` has been removed from
that file so `COVERAGE_RATCHET.toml` is the single owner of every floor.

> **Coverage is a floor, not a goal.** 100 % of lines executed says nothing
> about whether the assertions are any good. The mutation harness is what
> measures that.

### This page now checks itself — for 12 of its 29 numbers

The header above claims none of these figures is typed by hand. **That sentence
was false when it was written:** the `check_core_index.sh` row read `36 / 36`
while the guard itself printed `40 / 40`. Nothing compared the page to the tools
it cites, so a governance document about verification was the least verified
artefact in the repository.

`tools/check_verification_numbers.py` (pure tier) parses **§3, §4 and §5** and
re-derives each claim from the tool named beside it. Of the **29 numeric rows**
it checks **12** and **names the 17 it does not**, so they are declared unchecked
rather than quietly skipped. Verified in all three states: a planted wrong figure
exits `1` printing both values, an unparseable table exits `2`, clean exits `0`.

It has already earned its place five times, and every one was a number in this
very document:

1. the stale `36 / 36` owner count, against a guard printing `40 / 40`;
2. adding this gate to `CORE.md` moved that count to `41`, and the page went red
   until corrected;
3. **§4's lint debt read `176 / 47 / 47` against a measured `213 / 67 / 40`** —
   because the first version of the gate parsed only §3, leaving the page's own
   *"where verification is thin"* table as the part with no verification on it;
4. **the MUnit row read `69 / 69` against a manifest declaring `72`** — it was on
   the unchecked list because *running* the suite needs a WolframKernel, and
   nobody noticed that checking the *claim* needs only the tracked rollup;
5. **§4's coverage-floor row read `2 of 61` against a floor file holding `6`** —
   its producer had printed the pair on every run since the day it landed.

The third is instructive about scope: a gate narrower than the document it guards
always leaves a comfortable corner, and the corner it left was the table that
admits weakness. **The fourth and fifth are instructive about something worse.**
Both numbers were on the NOT-CHECKED list, and the list is not a neutral record
of cost — it is a register of the numbers most likely to be wrong, because it is
exactly the set nothing re-derives. Naming an unchecked number is honest but it
is not protective, and the 17 still on that list should be read as *17 claims
that have no evidence today*, not as 17 acceptable exceptions.

Absent subproject virtualenvs report **UNKNOWN**, never a pass — the same
three-state discipline as the glossary sync.

---

## 4. Where verification is thin — stated, not buried

| gap | measured | why it is open |
|---|---|---|
| **Manuscript tables with a producer wired** | **5 of 34 (15 %)** | The gate's old summary read *"7 covered, 1 pending"*, which invites 88 %. The pending entry was an unenumerated catch-all. Wiring the remaining 29 is research-shaped: some have no producer at all. |
| **Lint hygiene debt** | enforced **0** · exempted-path residue F401 **154** · F841 **32** | **No longer debt: F401, F541 and F841 are now ENFORCED**, so a new one fails CI. F541 went 67 → 0 everywhere; F401 and F841 → 0 in every production path. The residue sits only in paths exempted **by name with a reason** in `ruff.toml`. The two figures are separate on purpose — reporting only "enforced 0" would hide the residue, which is how the old declared debt drifted 176/47/47 → 213/67/40 unseen. |
| **Coverage of `src/` as a whole** | **31.74 %** over **61** files; **22 of 52** modules with statements sit at exactly 0 % (was 42) | The 98.56 % in §3 is real but covers **99 statements in two files**. This row exists so the scoped figure can never be read as the unscoped one. **This figure was first published as 13 % and was wrong** — coverage only enumerates unexecuted files inside importable packages, and seven directories under `src/` had no `__init__.py`, so the report covered **25 of 54** files. With the markers added it covers **61 of 61** and the true figure is **6 %**. The gate now **fails** (not "unknown") when report and disk disagree: a percentage over a partial denominator is not unknown, it is wrong. **Moved 6 % -> 9 % on 2026-09-05** when the four parser contract tests landed; three of those four do not catch a planted defect, so this rise is executed lines and not verification. **Moved 12.63 % -> 29.90 % on 2026-09-07, and NOT ONE TEST WAS WRITTEN TO MOVE IT.** The coverage command was `pytest tests/analysis --cov`, and 24 further Python test files were run by nothing, so the 17.27 points they already exercised were never counted. This rise is neither executed lines nor verification — it is **arithmetic that was always true and never performed**, which is the worst of the three, because a wrong denominator makes every ratio above it wrong too. |
| **Modules that cannot be imported in the declared environment** | **3 of 53** — `BulkScraper`, `CurateNatureDataset`, `grn_data_pipeline` | All three need `requests`, which `requirements.txt` deliberately does **not** pin because they are orphaned scrapers reaching external services. They therefore sit at 0 % and no test can reach them until that is resolved — a Phase 3 decision, recorded here rather than discovered later. |
| **Where the remaining 154 F401 live** | replication packages **85** · `index-deconvolution/level*` **33** · `tests/` Lev4–7 runners **12** · `audit/` scripts **9** · frozen `workspaces/` **6** · `doc/` archives **6** · `experiments/` **3** | Every one is a replication package with its own pinned environment, a **dated experiment record**, or a provenance archive. Editing those rewrites history rather than fixing code, which is why they are declared instead of cleared. |
| ~~**`Trajectory_LZ.py` `k_max`**~~ **RESOLVED — and it was the other file that was wrong** | `Trajectory_LZ` agrees with published LZ76 on **255/300**; `Scaling_LZ_Tools` on **6/300** | See below. The unused `k_max` was a real signal, but it pointed at a different defect from the one I first recorded. |
| ~~**Test membership covers all of `tests/`**~~ **FALSE UNTIL 2026-09-07 — the manifest was Wolfram-only** | **85 of 119** files declared; the missing **34** were the entire Python test tree | `check_test_manifest.sh` scanned `-name '*.m'`, so its denominator was 85 while CLAUDE.md, `CORE.md` and this page's own **85 / 85** all asserted it covered every file under `tests/`. The tell was in this very table: the F401 row counted *"`tests/` Lev4–7 runners 12"*, so **one ledger had been counting files the other could not see**. They were also run by nothing — `pytest.ini` set `testpaths = tests/analysis`, and the `TSK-…-Test.py` naming matches neither `test_*.py` nor `*_test.py`, so pointing pytest at those directories collected **zero**. Each was then run individually to classify it by measurement: **16 test / 2 producer / 6 quarantine**, later **14 / 2 / 8**. The scan now covers both languages and **refuses (exit 2) if either language scans 0 files**, because a per-language zero is exactly how this hid. `conftest.py` derives pytest's `collect_ignore` **from the manifest**, so declared and collected cannot drift. Verified by planting five defects: a new undeclared `.py` → red; a declared test that cannot be collected → red **by two independent checks**; the original Wolfram-only scan → **refused**; a quarantined file promoted to `test` → **the suite goes red, not the guard**, which is the correct split of duties; and the language filter removed from the runner → red, naming all 24 files. **That fifth plant exists because the defect happened.** Making the manifest bilingual did not make its Wolfram runner bilingual: `run-tests.sh` fed 24 Python files to the WolframKernel and scored `OK=72 FAIL=24 TOTAL=96`. The **pre-push hook refused the push**, which is the gate working exactly where it should — in the tier CI cannot run. But the only artefact that could contradict the runner was the **rollup**, which costs a 40-minute suite run, so the first line of defence was far too slow. `run-tests.sh --list` now prints its selection and executes nothing, and the guard compares that against the manifest in about a second. It asks the runner rather than re-deriving the filter, because a second copy of a selection rule agrees with the first only until one of them changes. |
| **A cross-repository `sys.path` leak in this project's own venv** | **83** foreign names injected; **1 of 14** collides — `data` | `venv/…/site-packages/deconv_lab_paths.pth` appends `deconv-lab/src`, `deconv-lab/experiments` and `decon-fin/src`. `import data` inside CausalBool was resolving to **`decon-fin/src/data.py`**, killing two `tests/Nature` files at collection. Controlled check — strip the two entries and rerun the same files unchanged: **1 collection error → 3 passed**. So the **developer machine was the broken environment and a clean checkout would have passed**, which is the reverse of the usual failure and why nobody suspected the venv. The `.pth` belongs to a sibling project and is **not touched**; the root `conftest.py` puts this repository's `src/` first instead. **Still open**: nothing prevents a future collision, and the blast radius is only small because `src/` has 14 top-level names today. |
| **Tests that were green because they tested a mock of the code** | **2 of 24**, both in `tests/Nature` | `TSK-NATURE-LEV3-TRADEOFF-001` and `-002` walked **three** directory levels up from a directory **two** below the root, so `sys.path` pointed outside the repository, every import raised `ImportError`, and a `try/except` installed a stub defined in the test file itself. TRADEOFF-001's mock scored genes by `delta_d*0.7 + degree*0.3`, so its AUC assertion checked a formula written eleven lines above it. Coverage had been reporting both subject modules at **0 %** all along — the two facts were visible together and never read together. Path and fallback both removed, so an `ImportError` is now an error; both files are **RED against the real modules** and quarantined as open items. |
| ~~**`D_v2` was a complexity measure**~~ **RETIRED 2026-09-07 — it was measuring complexity BACKWARDS** | random ranked simpler-or-equal than a chain: **`D_v2` 195/200 (97.5 %)** · BDM **0/200** · index-set **14/200 (7.0 %)** | `UniversalDv2Encoder._block_complexity` was Shannon binary entropy over block densities, and `_block_key` was `(size, ones)` — blocks keyed by density with the arrangement discarded. Binary entropy is **maximised at density one half**, the reverse of a program length, so every claim of the form "the real network is simpler than its randomised nulls" computed through it read the opposite of what it stated. It also gave a network and its transpose **identical** lengths (difference exactly 0.0), so "the hub drives everyone" and "everyone drives the hub" scored the same in a causality-first programme. Author directive: no Shannon quantity may be one of our measures; the two comparison measures are the **index-set program length** and **BDM**. `D_v2` now forwards to `row_run_index_set_length` — a forwarder, not a deletion, because 13 production files call it and one change site cannot drift. Over 210 corpus networks the median moves **106.32 → 334.43 bits**, all 210 changed, and the forwarder equals the owner exactly on every one. **No number in either active manuscript is affected**; `D_v2` appears in neither manuscript. |
| **Shannon quantities that remain, and why** | **2 declared baselines** | `H_total` and ZIP in comp_paper Table 2 are the **statistical baselines our measure is compared against and beats** (BDM 580.01 vs ZIP 10,016 vs `H_total` 10,229.61) — deleting them would remove the comparison that demonstrates the algorithmic approach. `Basin_Entropy` keeps the Krawitz–Shmulevich basin entropy, **demoted**: isolated in `_basin_entropy_shannon_baseline`, reported under a name that says what it is, and no longer the primary return — which is now `basin_partition_bits`, enumerative. Every baseline is named with its reason in `test_complexity_measures_are_algorithmic.py`; an undeclared one fails. |
| **The guard that would have caught this, and did not exist** | census: **80 sites over 626 files** — ours 28 · sibling 7 · replication 41 · archive 4 | `test_description_length_is_algorithmic.py` matched ENSEMBLE VOCABULARY, so it caught entropy that was **labelled** and missed entropy that was **computed**: `"h = -sum(p*log2(p))  # entropy"` → caught **via the comment**; the same line without the comment → **missed**; `D_v2`'s actual line → **missed**. Its own positive control passed because of a code comment, so it never exercised what it claimed to detect. The replacement has two arms — a **shape** scan for `p·log(p)` in any spelling, and the **ordering property**, which no source scan can give because it does not care how the number is produced. Replication packages are **excluded on purpose**: reproducing another author's published table with our measure would make the replication unfaithful. |
| **Mutation kill rate** | in progress | See §5. |
| **Files implementing an owned concept without loading the owner** | **0**, over **413 scanned / 75 matched / 54 referencing an owner / 21 excepted**. Detector specificity and sensitivity re-measured before every scan: **8/8 negative, 5/5 positive** | `tools/check_core_loading.py` (Phase C, anchored AUDIT04-D). **Now a member of `closure-pure`** — it was red by design while 8 accusations awaited adjudication, and **7 of those proved to be its own false positives**, so it is admitted only now that its matches mean something. The old rules matched bare words: `range(n)` plus *free*/*subset*/*sum*; `"AND"`/`"OR"`/`"XOR"` plus `def `; and `"ws"`, which matches **`rows`**. Two ledger defects surfaced in the same pass — `repertoire` declared only Wolfram owners, so no Python file could ever satisfy it, and anchoring introduced a **false negative of my own** (uppercase-only gate literals hid a real lowercase dispatch), caught by the positive controls. The two genuine findings were resolved by measurement, not argument: `imp-pathinfo`'s `wiring_description_length` is the index-set term alone (**45 of 45 cases disagree**, gap exactly `log2(12)` plus the parameter payload) and is declared and pinned; `imp-causal-paper`'s private gate copy agreed on **72/72 repertoire rows and 92/93 gate cases**, so it was drift and was **collapsed onto the owner**, which corrected a real defect. |
| ~~**Suite reproducibility under concurrent load**~~ **RESOLVED 2026-09-06 — and both my earlier readings were wrong** | **3 crashes in ~9 full-suite runs, on 3 different tests**; every one died AFTER writing its verdict | `TSK-ARCH-006`, `NANDTests.m` and `TSK-GATES-001` each crashed the kernel with **exit 139**; each is clean 3/3 standalone; crashes occurred with and without competing load. I first blamed one test on a single observation, then blamed concurrent load — **both withdrawn**. The kernel dies at SHUTDOWN, after the science is done. **A fresh verdict does not prove completion**: `Status.txt` is followed by further exports in most tests, so a kernel dying between them leaves a plausible `OK` beside incomplete artefacts. Every test now writes a **completion sentinel as its last expression**, deleted by the runner before each run, so its presence proves every line above it evaluated. The sentinel is **required in all cases, not only on a crash** — which closes the AUDIT03 hole from the other side, where a kernel that skipped a malformed expression and exited 0 was scored by whatever status was on disk. Verified by planting all three: death BEFORE the sentinel with a written PASS → **FAIL**; death AFTER it → **OK, reported loudly and recorded in the rollup**; no sentinel on a clean exit 0 → **FAIL**. |
| **An owned concept mirrored in a frozen archive producer** | `TSK-EXPER-005-NoiseRobustness.m`: **0 disagreements over 34 cases**, measured 2026-09-05 | **Accepted exposure, not a clean pass.** Its private `applyGate` agrees with the owner today at the arities used, and nothing keeps it agreeing: the archive policy forbids editing the file, so there is no pin. One latent condition is already visible — `"MAJORITY", Boole[Total[xs] >= 2]` hardcodes the arity-3 threshold, so at 5 inputs `{1,1,0,0,0}` returns 1 where the owner returns 0. Harmless while the file only uses arity 3; wrong the moment it does not. |
| **Modules with a declared coverage floor** | **30 of 61** — 31 carry no floor at all | `tools/check_coverage_ratchet.py` (AUDIT04-P4f) enforces a global floor and a per-module floor together, because `fail_under` is global only and a global pass hides a module at 0 %. The ratchet is seeded at the current measurement (global floor 9.18 %, measured 9.19 %), so it catches regression from day one while Phase B raises it tier by tier. Verified by planting: hiding the description-length tests drops that module to 0 % and fails BOTH floors; restoring returns it to green. The unfloored modules are printed on every run — the guard states the size of its own gap rather than reporting `6 measured`. **This row itself was stale (`2 of 61`) until AUDIT04 gated it**, which is the same failure it describes: a number with no producer drifts, and this page's own NOT-CHECKED list is where that happens. |
| ~~**Coverage that is not verification**~~ **CLOSED 2026-09-06 — 4 of 4 parser floors now bite** | was **3 of 4** with tests that did not bite; now **0 of 4** | Planted 2026-09-05: `SBMLParser` truncated to one node, `GINMLParser` with every edge dropped, `LogicParser` with the input bit ordering reversed — **all three left the suite green**; only `BNetParser` caught its plant. Re-planted 2026-09-06 after the tests were rewritten: **SBML RED (1 test), GINML RED (1), Logic reversal RED (3), Logic functional-`NOT` inverted RED (1)**, restored GREEN with no diff left in `src/`. **Two corrections were needed, and both were errors in the prescription, not the parsers.** Turning `>= 1` into an exact count was not enough: the SBML fixture held ONE node, so `== 1` also survives truncation-to-one-node — the *fixture* had to grow before any assertion over it could bite. And "`LogicParser` needs an asymmetric gate" was **wrong**: reversal keeps each row internally consistent and only permutes row ORDER, and `classify_truth_table` recomputes from the input columns it is handed, so `A AND NOT B` reads `CANALISING` with and without the defect. Only an elementwise assertion on the input enumeration catches it. Coverage moved **9.19 % → 11.05 %** globally as a side effect; the point was the bite, not the percentage. |
| **A latent SBML defect with zero measured impact** | **0 of 76** corpus files affected | Writing the new SBML fixture without namespaces made every node return `INPUT`, silently. The namespaced lookup for `functionTerm` is a descendant search (`.//`) but the non-namespaced fallback iterates only DIRECT children of the transition, and `functionTerm` sits inside `listOfFunctionTerms` — so a non-namespaced SBML-qual file yields a plausible all-inputs network rather than a refusal. Measured over `data/bio/raw`: of 160 SBML/XML files, **76 declare the qual namespace and all 76 parse with logic recovered, 0 all-INPUT**; the other 84 are not SBML-qual and are refused for having no qualitative species. **Deliberately not pinned** — a test asserting the all-INPUT output would freeze the wrong behaviour as the contract. |
| **GINML multi-valued nodes** | **582 / 5882 nodes (9.9 %)**, in **108 / 178 files**, of which **304** lose level rules | Binarised to the `val="1"` rule. No longer silent: `GINMLParser` records `node_max_values`, `is_multivalued` and `discarded_value_rules`, and warns once per file. Whether these models belong in a Boolean corpus at all is a scientific question, not a parsing one. |
| **Bio regeneration, R4.2–R4.5, R5** | blocked, but **`917 / 5,204` = 17.6 %**, not the 76.4 % previously recorded | The aggregate `3,977 of 5,204` reproduces exactly, but **48.9 % of those nodes are derivable today** — 1,181 truth tables were built by evaluation and 762 are `y = x`. The genuine blocker splits cleanly by source: **510 multi-valued, all GINML** (the binarisation defect fixed in AUDIT03-C) and **407 free-threshold, all BioModels**. Two more findings were not being counted at all: 578 nodes absent from `gates`, and 294 whose formula names variables outside their own `inputs`. Producer and full decomposition: `audit/AUDIT04_corpus_diagnostic/`. `Q2.2` remains an unresolved measurement conflict. |

### Declared deltas from the AUDIT03-C defect triage

Three defects were found by triaging `ruff F841` rather than deleting it — an
unused variable was, in each case, the only visible trace of a dropped result.
All three are fixed; the numbers they moved are recorded here so that a reader
meeting an older figure knows it was changed deliberately.

| what was wrong | measured effect | conclusion changed? |
|---|---|---|
| `Bayesian_Meta_Analysis.py` called itself adaptive above a fixed `prop_sd = [0.5, 0.5]` | acceptance **0.19 → 0.39–0.47** (optimum ≈0.44); ESS *σ* **2289 → 3104 (+36 %)**; *μ* **1.713 → 1.713** | **no** — HDI narrowed from `[1.280, 2.151]` to `[1.297, 2.132]` |
| `c29_density_matched_null.py` re-seeded inside the `k` loop | Bernoulli null: k=17 draw nested in k=23 in **100 % of draws**, *r* = **+0.724** → **0 %**, *r* = −0.025. Exact-*k* samplers measurably unaffected (2.11 shared edges vs **2.15** expected) | **no** — Bernoulli share 72.1 → 70.9 %, all verdicts held |
| `GINMLParser.py` discarded `maxvalue` | see the row above | not yet assessed |

**The old HDI `[+1.280, +2.151]` is still quoted in three files under `doc/`**
(`finalpaper/together_full.tex`, `finalpaper/sections/results_structural.tex`,
`newIntPaper/bioProcessLev3.tex`). Those are provenance archives under the
policy in `CLAUDE.md` and are **deliberately not rewritten** — an archive edited
to match a later run stops being provenance. The active manuscripts under
`papers/method/` do not quote this quantity.

### Two measures wearing one label (AUDIT03-C)

Chasing the unused `k_max` led to a second LZ implementation and then to a
mislabelled measure. Measured over 300 random binary strings of length 8–80,
against the published Kaspar & Schuster (1987) LZ76:

| implementation | agrees with LZ76 | what it actually computes |
|---|---|---|
| `src/complexity/Trajectory_LZ.py` | **255 / 300** | LZ76. All 45 misses are **exactly +1**, never another value — the trailing-phrase convention, which differs between published implementations. Structured cases agree exactly. |
| `src/complexity/Scaling_LZ_Tools.py` | **6 / 300** | **LZ78 phrase-dictionary size**, while its docstring claimed LZ76 and cited Kaspar & Schuster. |

The two agree with each other on **10 / 300**. The diagnostic case: for `"0"*32`
LZ76 returns **2** and the LZ78 parse returns **7**, because a constant string
forces a new phrase every time the run lengthens — LZ78 dictionary size grows
like √n there, LZ76 does not grow at all.

What was in `Scaling_LZ_Tools` was **an abandoned attempt, not a variant**: the
Kaspar–Schuster loop it opened contained `pass` followed by
`break  # Re-implementing below`, so it never executed one iteration, and `l`
and `k_max` were its leftovers. **My first record of this was wrong** — I called
both files "simplified variants of the same algorithm"; they are two different
measures, and only one file was mislabelled.

Resolved under the `monolithic-code` law rather than by collapsing: 2 %
elementwise agreement is not drift between copies, it is **two concepts wearing
one label**, so they get two names. `compute_lz78_dictionary_size` is the honest
name; `compute_lz_complexity` remains as a **forwarder** (verified identical on
300/300) so the provenance of earlier results survives.

**Impact is small, and stated rather than implied.** `compute_scaling_exponent`
— the only path into the Nature-track experiment — does **not** use LZ at all;
it uses `UniversalDv2Encoder`. The mislabelled function's sole consumer is one
Lev4 test, which asserts only the ordering *simple < periodic < random*. That
ordering holds for both measures, **so the test passes either way and could
never have detected the mislabel** — a weak assertion validating the wrong
quantity. No published number is affected.

One gate was also fixed rather than a defect: `datasaurus_gates_c18_c29.py` G4
asserted a Monte Carlo `z` to **±0.01** while declaring a sampling SE of ~0.16
three lines above, so an honest re-run turned it red. It now asserts the
*separation* the claim rests on — triangular null within 1.5 of zero, every
density-matched null beyond −2.0 (worst −2.41).

### The 6 quarantined Python files — quarantine never means passing

Made visible on 2026-09-07; **two were released on the same date** — one was already green and one had a mis-stated invariant. One of the rest is **red against real code** and is
open scientific questions, not tidy-ups. Listing them here is the point: a file
excluded without its reason on the page is indistinguishable from one that passes.

| file | verdict | why it is open |
|---|---|---|
| ~~`Lev4/TSK-LEV4-INTEGRATION-001`~~ | **RELEASED 2026-09-07 — it was green** | Declared RED as "3 failed, 2 passed", the monitor returning `PUBLISH_EMERGENCE` where the test expected the cell-line switch once and `CONTINUE` twice. **Measured at HEAD before any change in the AUDIT04-F commit: 5 passed, 0 failed.** AUDIT04-E's replacement of the z-score falsification branch had fixed the cause and the ledger was never updated, so a passing file sat excluded from collection behind a false failure claim — and a quarantine entry that is wrong in the safe-sounding direction is worse than none, because the tests were running for nobody. Now classified `test`, 8 tests including the two-measure agreement rule. Action codes renamed in the same commit (`PIVOT_CELL` → `SWITCH_TO_CELL_LINES`, `PIVOT_HYBRID` → `SWITCH_TO_HYBRID_ENCODING`, GLOSSARY §1e). |
| ~~`Nature/TSK-NATURE-SETUP-002`~~ | **RELEASED 2026-09-07 — mis-stated invariant** | `test_pure_dag` asserted a pure DAG costs **0** on `hierarchy_cost` and measured **4.754887502163468 bits**. The adjudication is that the TEST was wrong, and the mistake is a category error: `feedback_edges` is a COUNT and is correctly zero for an acyclic graph, while `hierarchy_cost` is a DESCRIPTION LENGTH and cannot be zero for a structured object — zero would say a decoder reconstructs a three-node chain from nothing. The value is exactly **3·log2(3)**, derived from the cost model rather than read off the output: layer assignment charges `n·log2(num_layers)`, and the edge term vanishes because every layer holds one node, so each block has `max_edges = 1` and `log2(C(1,k)) = 0`. 3 passed. |
| `Nature/TSK-NATURE-LEV3-TRADEOFF-001` | **2 failed** | Was green only against a stub (see §4). The real `EssentialityPredictor.__init__` requires `data_dir` and `metadata_path`, which the test does not supply. |
| `Nature/TSK-NATURE-LEV3-TRADEOFF-002` | **1 failed, 1 passed** | Was green only against a stub. The real `run_sweep` returns a **DataFrame**; the test indexes `results[0]` as a list of dicts. |
| `Nature/TSK-NATURE-LEV3-CANCER-002` | **1 failed, 1 passed** | sklearn: `Expected n_neighbors < n_samples_fit, but n_neighbors = 3, n_samples_fit = 3`. The fixture supplies 3 samples and the code asks for 3 neighbours, so the imputation path cannot execute at this fixture size. |
| `Bio/TSK-BIO-DATA-001`, `Bio/TSK-BIO-DATA-002`, `tests/TSK-NATURE-LEV3-DATA-001` | **collection error** | `requests`, deliberately unpinned. Consistent with the *"3 of 53 modules cannot be imported"* row above — the same decision, now with its test-side cost visible. |

Two further files are declared `producer` because measurement said so, not
convenience: `Nature/TSK-NATURE-LEV3-DATA-001` has **0 assertions** and reports
by `sys.exit`, which pytest scores as a **failure on success** (`SystemExit: 0`);
`Nature/TSK-NATURE-LEV3-SETUP-001` collects **zero** tests, writes
`results/lev3/setup001.json` and prints PASS/FAIL, so it is a producer whose
verdict **no gate reads** — recorded as an open item.

One hazard worth naming: `Nature/TSK-NATURE-LEV3-STATS-001` writes the **tracked**
`results/bio/null_stats.json` in place and restores it in a `finally`. The
restore is guarded by `if backup:`, so an empty original is falsy and the file is
**deleted** instead; an interrupted run leaves dummy content in a tracked
artefact. It passes, and it is declared `test`, but that pattern is a defect
waiting for the wrong day.

---

## 5. Does green mean anything? The mutation measure

A test count is not a measure of test quality. This programme has already found
a parity harness printing `cases matched: 0/0 / all match: True`, a verifier
reading a key one level too deep, eleven files exporting a literal `"OK"`, and
three files reported green while syntactically broken.

`audit/AUDIT03_R2_collapse/mutation_harness.py` plants **28 declared mutants**
across the owners in `CORE.md` — inverted comparisons, off-by-ones, dropped
branches, swapped constants — and reports how many the verification set kills.

Design constraints, each earned from a defect already seen here:

- **Runs in a git worktree.** The hand-run mutation restored `Gates.m` but not
  the artefacts, leaving five `FAIL` status files in the working tree — the
  stale-artefact class this audit removed, reintroduced by the tool built to
  test for it.
- **No routing.** Every mutant faces the whole suite, both pytest sets and both
  closure tiers. The first version routed by owner language and produced a
  *false* coverage gap.
- **Segfaults are not kills.** `run-tests.sh` prints `FAIL: X -> PASS (kernel
  exit=139)` under memory pressure — the test passed, the kernel died. Counting
  it would inflate the one number this exists to get right.
- **The baseline must be green, or it refuses.** It did refuse, and that refusal
  found a real defect: see below.
- **Survivors are adjudicated, never scored.** A survivor is a **coverage gap**
  or an **equivalent mutant**; conflating them is the classic error.

### The result, 2026-09-05 — and why one rate is not enough

Two runs, and the second is the one that matters. Regenerate with
`venv/bin/python audit/AUDIT03_R2_collapse/mutation_harness.py --report`, which
refuses on an absent, empty or incomplete results file.

| rate | value at `f2c2f77` | was, at `c9bc412` |
|---|---|---|
| **semantic kill rate** (headline; reachability probes excluded) | **30/30 = 100.0%** | 23/25 = 92.0% |
| **unit-test kill rate** (of those, caught by an MUnit or pytest test) | **30/30 = 100.0%** | 19/25 = 76.0% |

**READ THE DENOMINATOR BEFORE READING THE RATE.** The catalogue grew from 25
semantic mutants to 30 because Phase A *added five*, for `deconvolution`, which
previously had none at all. So `100%` is scored over a catalogue extended by the
person who knew where the gaps were. That was the plan's instruction, not a
liberty, but it makes the two columns not like-for-like and the honest
comparison is the narrower one: **on the original 25, the unit-test rate moved
19/25 -> 25/25.** Five mutants that no test could see now have tests that kill
them, and the five new ones were killed on their first run.

**The 16-point gap was the finding, and it is closed.** Four semantic mutants
were previously killed *only* by a governance gate, with no unit test detecting
them; a closure-gate kill means the programme notices, not that the suite checks
the answer. Every owner is now unit-killed and **no owner reads `NOT MEASURED`**.

What `100%` does NOT mean: that the code is correct, or that the suite would
catch a defect nobody thought to write as a mutant. It means every defect in
this catalogue is caught by a test rather than by a gate. The catalogue is the
measure, and it is 33 mutants over 8 owners — not the space of possible defects.

| owner | killed | semantic | unit-killed |
|---|---|---|---|
| `Gates` | 11/11 | 11 | 11/11 |
| `deconvolution` | 7/7 | 5 | 5/5 |
| `description_lengths` | 5/5 | 4 | 4/4 |
| `BioMetrics` | 3/3 | 3 | 3/3 |
| `CausalBoolCore` | 3/3 | 3 | 3/3 |
| `causalbool_paths` | 2/2 | 2 | 2/2 |
| `IndexAlgebra` | 1/1 | 1 | 1/1 |
| `NetworkIO` | 1/1 | 1 | 1/1 |

The three owners the FIRST run named, and what closed each:

- **`NetworkIO` — zero kills of any kind.** Its mutant makes the corpus loader
  read the classification **label** instead of the authoritative formula, and
  nothing caught it. This is the AUDIT02/H defect that two of five collapsed
  copies carried; the owner was fixed, the test that would keep it fixed was
  never written. **The AUDIT04 Phase 5 diagnostic reached the same defect
  independently**, measuring that 1,943 of 3,977 corpus nodes were recorded as
  having no derivable truth table when they have one, precisely because a label
  was read as a statement about evaluability.
- **`CausalBoolCore` — zero unit-test kills**, 3/3 caught by the cross-language
  parity gate alone. Its self-containment is a declared exception in `CORE.md`
  justified by exactly that parity, so the exception is holding as declared —
  but nothing else watches it, and that cost is now measured rather than assumed.
- **`deconvolution` — not measured.** Both its mutants are reachability probes,
  so its semantic denominator is **zero**. `minimal_dnf` and
  `essential_variables` are declared owners and no mutant has ever tested
  whether the suite checks their answers. The reporter prints `NOT MEASURED`
  rather than `0/0`, because a zero denominator reading as a clean sheet is the
  vacuous pass this page exists to prevent.

Both survivors are adjudicated **coverage gaps, not equivalent mutants**, in
`audit/AUDIT03_R2_collapse/MUTATION.md`, together with one **failed**
pre-registered prediction (`py-paths-root` was predicted to survive and was
killed — by a closure gate only, so the coverage gap it named is still real and
is carried forward regardless of the kill).

**Earlier, superseded:** one hand-run mutant (`MAJORITY` tie threshold, breaking
declared convention D-3) killed by 5 tests across 4 sections.

### What the harness found before it ran a single mutant

`TSK-NATURE-LEV3-SETUP-002` **passed in the working tree and failed in a clean
worktree**. Root cause, measured:

```
repo root      python3 -> ~/.pyenv/versions/3.13.12/bin/python3   (has numpy)
/tmp/worktree  python3 -> ~/.pyenv/versions/3.11.10/bin/python3   (does not)
```

`BioBridge_v2.m` shelled out to a bare `python3`, and pyenv resolves the shim
per directory — so the same test gave a different verdict depending on where it
ran. The interpreter is now declared. **A test that is not hermetic is not a
test of this repository.**

---

## 5a. Every non-algorithmic site under our own trees, adjudicated (AUDIT04-F)

The author's directive of 2026-09-07 removes Shannon from our **measures**. It
does not remove arithmetic, and the difference has to be decided site by site or
the census number means nothing. `audit/AUDIT04_E_measures/census_shannon.py`
reports **86 sites over 628 files** (was 83; see the recall hole below). The
**34 sites in 19 files** under OURS adjudicate as follows.

Four verdicts. **Measure** — forbidden, must be removed. **Baseline** — a
Shannon or compression quantity our measure is compared *against*, permitted
only where its output names it as a baseline. **Statistic** — a quantity about
two variables rather than about one object's complexity; permitted, same rule as
a correlation. **False positive** — the pattern matched something that is not
the shape it looks for.

| site | verdict | why |
|---|---|---|
| `src/stats/Mutual_Information_Analyzer.py` (3) | **statistic** | MI between a complexity score and a clinical outcome, sitting beside `pearson_rho`. Now labelled in the payload: `kind='statistic'`, `is_complexity_measure=False` |
| `src/complexity/Basin_Entropy.py` (1) | **baseline** | Krawitz–Shmulevich basin entropy, already isolated in `_basin_entropy_shannon_baseline` and emitted under `basin_entropy_shannon_baseline` |
| `papers/method/code/complexity_analysis/complexity_analysis.py` (1) | **baseline** | binary entropy for `H_total`, the comp-paper Table 2 baseline our measure beats |
| `experiments/bio/ZenilTruthTableCompression.py` (4) | **baseline** | entropy of truth tables reported *beside* BDM, which is what the experiment compares |
| `src/integration/MotifEncoder.py` (3) | **false positive** | the entropy term was removed in AUDIT04-E; the hits are the docstring **quoting the retired code** so the defect stays legible. Verified by reading `compute_cost`: it is `count + location + catalogue-index`, all enumerative |
| `src/integration/HierarchyEncoder.py` (1) | **false positive** | `log2(comb(...))` is an **enumerative** code length — bits to name one object among a counted set — not a distributional quantity |
| `papers/method/code/complexity_analysis/bdm_comparison.py` (1) | **false positive** | same shape: `log2(comb(n, deg))` per row |
| `audit/AUDIT03_R3_*` (8) | **false positive** | same shape, in audit probes |
| `src/analysis/Phase_Transition_Bio_Overlay.py` (1) | **false positive** | `p_xor = xor_count / n_nodes` is a **fraction of nodes**, never used as a probability in a code length |
| `src/experiments/SimplicityV2_Nature.py` (1) | **false positive** | `aer = mean_d_null / mean_d_bio` is a ratio of two lengths |
| `papers/.../dynamical_landscape_10node.py`, `audit/AUDIT04_corpus_diagnostic/classify_corpus_nodes.py`, `audit/AUDIT03_R2_collapse/mutation_harness.py` (3) | **false positive** | `Counter` used to tally basins and categories, not to build a distribution |
| `src/scripts/test_bdm_10digits.py` (1) | **false positive** | matched a `print("Computing Entropy(X)...")` string in a scratch script |
| `tests/analysis/test_*_is_algorithmic.py` (8) | **false positive** | the guards themselves, which must contain the shapes they forbid |

**Verdict: zero forbidden measures remain under OURS.** Three baselines, one
statistic, thirty false positives — so the census's raw count overstates by an
order of magnitude and must never be quoted without this table.

### The census had a recall hole and it was not academic

`Mutual_Information_Analyzer` was **invisible** to the census until 2026-09-07.
The scan works by SHAPE — `p·log p`, frequency tables, count-to-probability —
and none of those appears in that file, because the Kraskov estimator hides all
of them behind `sklearn.feature_selection.mutual_info_regression`. The quantity
is Shannon mutual information, converted from nats to bits, and it reaches a
live decision branch: `mi_depmap_bits` travels through `DepMap_Validation` into
`Contingency_Monitor`'s switch-to-cell-lines test.

A shape-based scan sees only the shapes it was taught, and **a library estimator
is a shape too**. A `library_entropy_estimator` detector now covers
`mutual_info_regression` / `mutual_info_classif` / `mutual_info_score` /
`differential_entropy`; the count moved 83 → 86.

---

## 5b. The bio artefacts, regenerated — and the claim does not survive (AUDIT04-F)

`results/bio/null_stats.json` was still **entirely** in the pre-AUDIT04-E format:
`z`, `mu`, `sd` over the retired Shannon `D_v2`. It postdated both the measure
change and the operator change and had been touched by neither. Regenerated
2026-09-07 over the same **231** networks, 1000 nulls of each of three kinds.

| | before — retired `D_v2`, z-score | after — index-set | after — BDM |
|---|---|---|---|
| median `D_bio` | 109.77 bits | 395.31 bits | 415.19 bits |
| ER null | median z 1.77, z ≥ 2 in **111/231** | median gap **−27.68** bits, beats every null **53/231** | median gap **−59.20** bits, **14/231** |
| degree-preserving | median z 0.80, z ≥ 2 in **72/231** | median gap **−31.26** bits, **34/231** | median gap **−53.12** bits, **7/231** |
| gate-preserving | median z 1.47, z ≥ 2 in **97/231** | median gap **−38.05** bits, **39/231** | median gap **−68.45** bits, **10/231** |

**A negative gap means the real network is LONGER than the best of its 1000
nulls.** The median is negative under both measures and all three nulls, so the
median biological network in this corpus **is not simpler than its randomised
controls**, and the headline "biological networks are algorithmically simple"
does not hold as stated over this corpus with these nulls.

The old z-score read 72–111 of 231 as separating at two sigma. That figure was
never evidence: it was computed from a measure that ranked a random graph
simpler than a chain in 195 of 200 draws, with an operator that discarded the
bits, over an artefact regenerated by nothing.

**The two measures disagree on roughly a third of the corpus** — 87/231 (ER),
77/231 (degree), 77/231 (gate). That disagreement is the reason both are
reported and the reason `Contingency_Monitor` returns `UNDECIDED` rather than
picking one: on a third of these networks, which measure you choose decides the
verdict, and nothing in the directive privileges either.

The 30-network Level-4 checkpoint agrees: median exceed 0.65 (index-set) and
0.30 (BDM), both far above the 0.05 threshold, the measures agreeing on 23 of
30, and `SWITCH_TO_HYBRID_ENCODING` returned for the stated reason.

`results/lev3/setup001.json` reproduces the declared index-set inversion at
three sizes independently of the n = 16 measurement above: the checkerboard
costs **5170.5 / 12941.9 / 24673.6** bits against a random matrix of the same
density at **2683.6 / 6642.2 / 12562.7**, while BDM gives **36.3 / 37.4 / 38.3**
against **1935.6 / 4374.4 / 7759.9**.

**What this does not say.** It does not say the method is wrong; it says this
particular claim, over this corpus and these three nulls, is not supported. The
`imp-*` replication packages and the manuscripts are untouched — `D_v2` appears
in neither `method_paper.tex` nor `comp_paper.tex`.

---

## 6. Related

`CORE.md` (owners and guards) · `BASELINE.md` (the test ledger and every
declared delta) · `DESCRIPTION_LENGTHS.md` (variants A–E) · `GLOSSARY.md`
(definitions) · `LARGE_BINARIES.md` · `audit/AUDIT03_R2_collapse/DUPLICATION.md`
and `ORPHANS.md` (the censuses).
