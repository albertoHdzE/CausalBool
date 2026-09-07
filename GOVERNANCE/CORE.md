# The core — one owner per concept

**Status:** normative. **Established:** 2026-09-04 (AUDIT03), under the
`monolithic-code` law: *one concept, one owner, one file — and you find the
owner before you write the code, not after.*

This is the index a reader needs in order to answer "which code computed this
number". If that question requires a `grep`, the published artefact has failed.
Every entry below is a path that exists; the list is checked by
`tools/check_core_index.sh`.

---

## 1. Why this file exists

Copies do not stay copies. Each one receives a fix the others do not, and from
that moment the programme holds two different answers to the same question with
no way to tell which one produced a given result. Measured instances from this
repository, all of them found *after* the copies had already diverged:

| concept | copies | what the divergence was |
|---|---|---|
| the repertoire engine | 2 | ~6,300 lines, shared ancestry, **different later fixes** — neither was a superset |
| per-node description length | 8 | 4 charged the `log2(n+1)` in-degree field, 4 did not — so `D` named **two different quantities**, only one decodable |
| `C_formula` | 6 | two had lost `KOFN` and `CANALISING` and silently fell back to `1+d`; **20 of 72 `(gate, d)` cells disagreed** |
| corpus loader `LoadJSONNetwork` | 5 | two read only the classification label, two read the authoritative `logic` formula |
| `weights` / `allOffsets` / `givePlaces` | 3 | one lacked the empty-`ws` guard |
| repo/paper path helpers | 4 | `_paper_figures_dir` returned `str` in two files and `Path` in two others |

**The recurring lesson: a census finds identical copies, a guard finds copies
that have drifted — and the drifted ones are the dangerous ones.** The census
missed a third `givePlaces`, a sixth `compressionWeight`, three of the five
`LoadJSONNetwork`, and the fourth path helper. Every one was found by a guard or
by searching for a distinctive **body fragment** rather than for the name.

---

## 2. Wolfram core

| concept | owner |
|---|---|
| repertoire construction, one-step dynamics (`createRepertoires`, `runDynamic`) | `src/integration/Alpha.m` |
| gate semantics, truth tables, dispatch for the twelve families (`ApplyGate`, `IndexSet`) | `src/Packages/Integration/Gates.m` |
| end-to-end smoke check of the packaged core (`SelfTestRun`) | `src/Packages/Integration/SelfTest.m` — **delegates**; it was a fourth private engine until AUDIT03-B |
| index-set algebra: complement, union, intersection, `Phi` bit-reversal, bands | `src/Packages/Integration/IndexAlgebra.m` |
| description length `D`, `D_v2`, `C_formula` (`ComputeDescriptionLength`, `FormulaComponentWeight`, `ComputeFormulaComponents`) | `src/Packages/Integration/BioMetrics.m` |
| corpus reader `LoadJSONNetwork` | `src/scripts/NetworkIO.m` |
| degree-preserving randomisation, knockout deltas, attractors, essentiality | `src/Packages/Integration/BioExperiments.m` |
| repertoire creation / dynamic update API surface | `src/Packages/Integration/Alpha.m`, `Experiments.m` (delegate to the engine) |

### The standalone companion core

`papers/method/code/lib/CausalBoolCore.wl` owns `weights`, `allOffsets`,
`givePlaces`, `composedUpdate6Node`, `ApplyGate` and
`CreateRepertoiresDispatch` **for the published companion code**.

This is a **declared exception, not a duplicate**: the file states "No external
packages required" and a reader reproducing the paper must be able to run it
from a clean checkout without the engine. Collapsing it into `src/` would
destroy the self-containment that is its purpose. It is kept honest by the
135/135 cross-language parity run (`tools/run_crosscheck_parity.sh`), not by
sharing code.

> **`composedUpdate6Node` must not be replaced by `CreateRepertoiresDispatch`.**
> It is the *composed* reading (convention D-2d) and differs from the
> synchronous dispatch on **32 of 64 rows**, on node 6 only, by feeding the
> newly computed `y5` rather than the input `x5`. This is the case that proves
> deduplication can damage science: collapsing the two would have silently
> changed the flagship by half its rows.

---

## 3. Python core

| concept | owner |
|---|---|
| all description-length variants A–E, `bdm_2d`, the `pybdm` pin | `src/description_lengths.py` |
| repository / paper / figures path resolution | `src/causalbool_paths.py` |
| index-set deconvolution, `minimal_dnf` (Quine–McCluskey) | `index-deconvolution/src/deconvolution.py` |
| **LZ76** complexity (Kaspar & Schuster) | `src/complexity/Trajectory_LZ.py` |
| **LZ78** phrase-dictionary size | `src/complexity/Scaling_LZ_Tools.py` (`compute_lz78_dictionary_size`) |

> **These two are deliberately NOT one owner.** Both were labelled "LZ76,
> Kaspar & Schuster (1987)"; measured over 300 random strings they agree with
> each other on **10** and with the published LZ76 on **255** and **6**
> respectively. Non-zero elementwise disagreement means two concepts, so the
> rule in §6 step 3 applies: give them two names rather than collapse them.
> `compute_lz_complexity` survives as a forwarder, verified identical on 300/300.

### Declared Python exceptions

| site | reason | how it is pinned |
|---|---|---|
| `imp-pathinfo-paper/src/imp_pathinfo/causalbool_mirror.py` | omits the in-degree field; its **published tables depend on that** | T4.5 fixture asserts the gap is exactly `n·log2(n+1)` |
| `imp-causalNet-paper/src/imp_causalnet_paper/causalbool_mirror.py` | declared canonical for **variant A**; the root module now delegates to it | proven equal on 300 random adjacency matrices |
| `workspaces/claude-nature/paper/code/` path helpers | frozen Level 8 reproducibility artefact, at a different directory depth | not edited; excluded by the guard with this reason inline |
| `index-deconvolution/level*/` helpers | each level is a **dated experiment record**; collapsing rewrites history | left as-is, recorded in `DUPLICATION.md` |
| `index-deconvolution/crosscheck/` vs `index-deconvolution/experiments/DemoLibrary.wl` | the cross-check must be **independent** of what it checks — that independence is what makes 135/135 mean anything | deliberate; exempt in the guard |
| `imp-prices/vendor` | two-copies rule, pinned byte-identical to `index-deconvolution/src/` | `imp-prices/tests/test_vendor_parity.py`, an md5 gate in CI that **loudly skips** rather than passing if the canonical is absent |
| `src/external/ccapi` | vendored third party | dependency boundary, never modified |
| `papers/method/code/complexity_analysis/bdm_comparison.py` | **UNKNOWN** — divergence reason not determined; script uses its own gate-catalogue / D_formula computation rather than the core | **no pin** — must be reviewed before any pin is declared |
| `papers/method/code/corroboration_6node/ordering_invariance_6node.py` | **UNKNOWN** — divergence reason not determined; ordering-invariance corroboration script does not load the core owner | **no pin** — must be reviewed |
| `papers/method/code/mixed_interaction_10node/dynamical_landscape_10node.py` | **UNKNOWN** — divergence reason not determined; landscape-analysis script defines its own gate-family list | **no pin** — must be reviewed |
| `papers/method/code/scalability_resource_envelope/scalability_resource_envelope.py` | **UNKNOWN** — divergence reason not determined; scalability-analysis script defines its own gate-catalogue | **no pin** — must be reviewed |
| `papers/method/code/complexity_analysis/complexity_analysis.py` | the companion must run from a clean checkout, so it may not import the packaged core — the same reason `CausalBoolCore.wl` is exempt | `tests/analysis/test_companion_python_parity.py`: `_eval_gate` equals the owner on **0 disagreements over 310 (gate, input) cases**, `build_output_table` on 16/16 rows |
| `papers/method/code/worked_example_7node/worked_example_7node.py` | same reason; the offset family is rebuilt in Python for the reader | same fixture: Ω is the exact subset-sum set over **every connected set for n = 3…7**, plus the empty-free-set guard |

### Declared exceptions in the test suites

A test that validates an owner must not compute its expected value **with** that
owner, or it asserts `owner === owner`. Where the private copy is the
independent derivation and the assertion compares it against the owner, the
**assertion is the pin**: the test goes red the moment the two diverge. This is
the same independence that makes the 135/135 cross-check mean anything.

| site | reason | how it is pinned |
|---|---|---|
| `tests/MUnit/Analysis/ANDTests.m`, `ORTests.m`, `AnalyticVsExhaustiveQueryTests.m`, `tests/MUnit/Theory/TSK-THEORY-005-Tests.m` | each defines a private `phi[j_, n_]` and compares it against `Integration\`Gates\`IndexSetNetwork`; importing `IndexAlgebra\`Phi` would make the test a tautology | the file's own equality assertion — it fails if the private transport and the owner disagree |
| `tests/MUnit/Exper/TSK-EXPER-002-GateMixtures.m`, `TSK-EXPER-002-GateMixtures2.m` | **not a mirror — a guard false positive.** These hold closed-form bias and slope formulae (`andBias[p_] := p^2`, `xorSlope[p_] := 2 - 4 p`), not gate application. The detector fires on gate names beside a `:=`. All seven biases and six slopes re-derived by hand and correct | no pin needed; the concept is not owned by `Gates.m` |
| `tests/MUnit/Exper/TSK-EXPER-005-NoiseRobustness.m` | **declared, not defended, but measured.** A genuine private `applyGate` Switch. Frozen archive producer; the archive policy forbids rewriting it | **no pin.** Measured 2026-09-05: **0 disagreements over 34 cases** against the owner at the arities used. **Latent condition:** `"MAJORITY", Boole[Total[xs] >= 2]` hardcodes the arity-3 threshold, so it diverges at any wider arity — at 5 inputs `{1,1,0,0,0}` gives 1 where the owner gives 0. Accepted exposure, recorded in `VERIFICATION.md` |

---

## 4. The guards

A guard is the durable defence; a census is a snapshot. Each guard asserts the
**owner's path**, not merely that the count is one — `count == 1` passes when
the single survivor is the wrong file.

| guard | what it protects |
|---|---|
| `tools/check_single_engine.sh` | every owner in §2 and §3; keyed on **body signatures** so a renamed copy is still caught |
| `tools/check_core_index.sh` | every path named in this file still exists |
| `tools/run_crosscheck_parity.sh` | the Python↔Wolfram 135/135 parity, which **refuses** rather than passing on zero cases |
| `tools/test_description_length_parity.py` | executes the Wolfram producer; a stale stored value yields `WOLFRAM DRIFT` |
| `tools/verify_paper_artefacts.py` | produced values against declared expectations; every bit-count names its language and decodability proof |
| `tools/snapshot_paper_numbers.py` | keyed by **content**, so a moved line is not reported as a changed number |
| `tools/check_glossary_sync.sh` | `GOVERNANCE/GLOSSARY.md` against the sibling programme |
| `tools/check_wolfram_syntax.wl` | every `.m`/`.wl` parses — the suite could not see a syntax error, and three broken files sat behind a green run |
| `tools/check_test_manifest.sh` | every `.m` **and `.py`** file under `tests/` is classified in `MANIFEST.tsv`, and every declared Python test is actually collected by pytest; refuses if either language scans zero files. **This row claimed "every file" from AUDIT03-B until 2026-09-07 while the scan was `-name '*.m'`, hiding 34 Python files** |
| `tools/enumerate_paper_tables.py` | the honest table-coverage fraction of the active manuscripts (measured **5/34**, not the 7/8 the old summary implied) |
| `tools/check_import_safety.py` | no module under `src/` does work when imported — two reseeded the **global** RNG on import (measured: a caller seeding 12345 got a different stream purely from the import) and two created output directories. A necessary-not-sufficient static screen, and it says so |
| `tools/check_verification_numbers.py` | `VERIFICATION.md` against the **live output of the tools it names** — the page claimed `36/36` owners while its own guard printed `40/40`. Distinct from `snapshot_paper_numbers.py`, which detects *change* against a stored baseline and would have passed the stale claim forever |
| `tools/run_closure.sh` | runs every gate and **can actually fail** — the Makefile's `-@` prefixes meant `make closure` exited 0 even if all members failed |
| `.github/workflows/ci.yml` | the pure tier on every push; states plainly that the Wolfram tier is **not** covered |
| `githooks/pre-push` (via `tools/install_hooks.sh`) | refuses a push whose Wolfram tier or MUnit suite is red |
| `.coveragerc` + `pytest.ini` | owner coverage floor, **95%** (measured 98.56%) |
| `audit/AUDIT03_R2_collapse/mutation_harness.py` | whether the suite can actually catch a defect, not merely run. Measured `23/25` semantic kills but only `19/25` by a unit test — four mutants were caught by a governance gate alone. `NetworkIO` has **zero** kills, `CausalBoolCore` zero *unit-test* kills, and `deconvolution` is **not measured** (probes only). `--report` refuses on a partial run |

**Every guard must, without exception:** refuse on empty input, print its
denominator, exit non-zero on failure, and have been verified by planting the
defect and watching it fail.

### An exemption on one side of a pinned pair is a defect in the pin

Drift is normally assumed to arrive as a fix applied to one copy and not the
other. **It also arrives as a policy exemption applied asymmetrically**, and
that route is invisible because nobody edits the copy at all.

Measured here on 2026-09-05. `imp-prices/vendor` is pinned byte-identical to
`index-deconvolution/src`, and the pin has a gate. But `ruff.toml` excluded the
vendored side from lint while the canonical side was linted, so when the
AUDIT03-C F401 sweep removed an unused `from typing import Callable` from the
canonical, the exempt copy kept it. **The pin broke with no edit to the vendored
file, no semantic change and no intent**, and stayed broken because the pin's
own gate was not re-run after the sweep.

Two rules follow, both now in force:

1. **A per-file exemption — lint, formatter, type checker, coverage — covers
   every copy of a pinned pair, or none of them.** `imp-prices` is therefore
   listed in `ruff.toml` by subdirectory rather than by a single wildcard, so
   that the vendored tree is deliberately *not* exempt. Both files are clean
   under the full enforced set, so the exemption was never needed.
2. **Any sweep that edits many files re-runs the gate of every pinned pair it
   touches, in the same commit.**

Verified by planting: reintroducing the unused import into the vendored copy now
turns `ruff check` red, where previously it was invisible.

---

## 5. Adding code

Answer these before opening an editor. They are the `monolithic-code` skill's
pre-flight, and they are not rhetorical.

1. **Where is the core?** Find the owner in §2/§3. If none exists, ask the
   author; do not silently elect one.
2. **Does it already exist under another name?** Search by **body fragment** and
   by behaviour, not by the name you were about to use.
3. **Why does a new definition beat enriching the owner?** Default answer: it
   does not. "It was easier" and "I did not want to break the other caller" are
   not reasons — the second is an argument *for* touching the owner.
4. **What guard keeps it single?** It ships in the same commit and is verified
   by planting a copy.

## 6. Collapsing an existing duplicate

1. List every copy **via the guard**, not from memory.
2. **Diff them all pairwise.** The owner is the **superset**, even if no
   existing copy is the superset — then the owner is new code. *A deficient copy
   was promoted once in this audit and had to be corrected; that is why this
   step is written down.*
3. Measure disagreement **elementwise** first. Zero → drift, collapse. Non-zero
   → **stop**: they may be two concepts, and collapsing them would be worse than
   the duplication.
4. Commit the parity evidence **before** removing anything.
5. Forwarders or `archive/`, never deletion — provenance of past results.
6. Re-run every consumer, diff artefacts elementwise, declare any moved number
   in `tests/MUnit/BASELINE.md`.

---

## Related

**`GOVERNANCE/VERIFICATION.md` — what is verified, how, and how well, with every number regenerable by `make ci-local`.**

`GOVERNANCE/DESCRIPTION_LENGTHS.md` (variants A–E and their owners) ·
`GOVERNANCE/GLOSSARY.md` (definitions) ·
`GOVERNANCE/LARGE_BINARIES.md` (binary policy) ·
`tests/MUnit/BASELINE.md` (test truth and declared deltas) ·
`audit/AUDIT03_R2_collapse/DUPLICATION.md` (the census and its adjudication).
