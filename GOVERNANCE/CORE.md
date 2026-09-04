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

### Declared Python exceptions

| site | reason | how it is pinned |
|---|---|---|
| `imp-pathinfo-paper/src/imp_pathinfo/causalbool_mirror.py` | omits the in-degree field; its **published tables depend on that** | T4.5 fixture asserts the gap is exactly `n·log2(n+1)` |
| `imp-causalNet-paper/src/imp_causalnet_paper/causalbool_mirror.py` | declared canonical for **variant A**; the root module now delegates to it | proven equal on 300 random adjacency matrices |
| `workspaces/claude-nature/paper/code/` path helpers | frozen Level 8 reproducibility artefact, at a different directory depth | not edited; excluded by the guard with this reason inline |
| `index-deconvolution/level*/` helpers | each level is a **dated experiment record**; collapsing rewrites history | left as-is, recorded in `DUPLICATION.md` |
| `index-deconvolution/crosscheck/` vs `index-deconvolution/experiments/DemoLibrary.wl` | the cross-check must be **independent** of what it checks — that independence is what makes 135/135 mean anything | deliberate; exempt in the guard |
| `imp-prices/vendor` | two-copies rule, pinned byte-identical | vendored boundary |
| `src/external/ccapi` | vendored third party | dependency boundary, never modified |

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
| `tools/check_test_manifest.sh` | every file under `tests/MUnit` is classified in `MANIFEST.tsv`; no file can be silently excluded again |

**Every guard must, without exception:** refuse on empty input, print its
denominator, exit non-zero on failure, and have been verified by planting the
defect and watching it fail.

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

`GOVERNANCE/DESCRIPTION_LENGTHS.md` (variants A–E and their owners) ·
`GOVERNANCE/GLOSSARY.md` (definitions) ·
`GOVERNANCE/LARGE_BINARIES.md` (binary policy) ·
`tests/MUnit/BASELINE.md` (test truth and declared deltas) ·
`audit/AUDIT03_R2_collapse/DUPLICATION.md` (the census and its adjudication).
